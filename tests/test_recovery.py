"""Tests de la copia de recuperación: qué guarda y cómo se vuelve a ella.

La copia se escribe como JSON en el perfil y se lee después de un cierre
inesperado —un corte de luz, el programa colgado—, así que acá se mira lo que
importa en ese momento:

- **Que vuelva todo**: las fases, los arousals, las anotaciones con sus canales
  y colores, y la ventana donde estaba parado el usuario, también después de
  pasar por texto.
- **Que lo recuperado siga sin exportar**: no está en ningún archivo de salida,
  así que cerrar tiene que seguir preguntando.
- **Que sea de este registro**: una copia de otra noche con el mismo nombre no
  se aplica.
- **Todo o nada**: una copia cortada o rota se rechaza sin tocar la sesión.

Cuándo se escribe, se borra y se ofrece lo verifica `test_work_guard.py`.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.derivation import derive_montage
import psglab.core.recovery as recovery
from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring, StageSuggestion
from psglab.core.session import Session
from psglab.utils.errors import PsgLabError, UnreadableRecoveryError

FRECUENCIA = 100.0
VENTANAS = 4


def _registro(nombre: str = "noche.edf", ventanas: int = VENTANAS, canales: int = 2) -> Recording:
    return Recording(
        file_path=Path("carpeta") / nombre,
        channels=[Channel(f"C{i}", ChannelKind.EEG, "µV", i) for i in range(canales)],
        data=np.zeros((canales, int(ventanas * 30 * FRECUENCIA))),
        sampling_rate=FRECUENCIA,
    )


def _sesion(registro: Recording | None = None, nomenclatura=Nomenclature.AASM) -> Session:
    registro = registro if registro is not None else _registro()
    ventanas = int(registro.n_samples // (30 * FRECUENCIA))
    return Session(registro, Scoring(ventanas, nomenclatura), AnnotationSet())


def _con_trabajo() -> Session:
    """Una sesión scoreada a medias, con dos anotaciones, parada en la ventana 3."""
    sesion = _sesion(nomenclatura=Nomenclature.RK)
    sesion.scoring.set_stage(0, SleepStage.WAKE)
    sesion.scoring.set_stage(1, SleepStage.S4)
    sesion.scoring.set_arousal(2, True)
    sesion.annotations.add_label("Mía", "#123456")
    sesion.annotations.add(Annotation("Mía", 100, 50, ("C1",)))
    sesion.annotations.add(Annotation("Arousal", 3000, 200, (), "#abcdef"))
    sesion.go_to_window(3)
    return sesion


def _por_texto(copia: dict) -> dict:
    """La copia como vuelve del disco."""
    return json.loads(json.dumps(copia))


# -- Que vuelva todo ------------------------------------------------------------


def test_vuelven_las_fases_los_arousals_y_la_nomenclatura():
    copia = _por_texto(recovery.snapshot(_con_trabajo()))
    nueva = _sesion()

    recovery.restore(nueva, copia)

    assert nueva.scoring.nomenclature is Nomenclature.RK
    assert [nueva.scoring.get(i).stage for i in range(VENTANAS)] == [
        SleepStage.WAKE, SleepStage.S4, SleepStage.UNSCORED, SleepStage.UNSCORED
    ]
    assert [nueva.scoring.get(i).arousal for i in range(VENTANAS)] == [
        False, False, True, False
    ]


def test_vuelven_las_anotaciones_con_sus_canales_y_colores():
    original = _con_trabajo()
    copia = _por_texto(recovery.snapshot(original))
    nueva = _sesion()

    recovery.restore(nueva, copia)

    assert nueva.annotations.all() == original.annotations.all()
    assert nueva.annotations.color_of("Mía") == "#123456"


def test_vuelve_a_la_ventana_donde_estaba():
    copia = _por_texto(recovery.snapshot(_con_trabajo()))
    nueva = _sesion()

    recovery.restore(nueva, copia)

    assert nueva.current_window == 3


def test_lo_recuperado_sigue_sin_exportar():
    """No está en ningún archivo de salida: cerrar tiene que seguir preguntando."""
    copia = recovery.snapshot(_con_trabajo())
    nueva = _sesion()

    recovery.restore(nueva, copia)

    assert nueva.has_unexported_scoring()
    assert nueva.has_unexported_annotations()


def test_las_sugeridas_no_se_guardan():
    """Son del clasificador y nadie las confirmó: se vuelven a pedir."""
    sesion = _sesion()
    sesion.scoring.set_suggestions([StageSuggestion(SleepStage.N2, 0.9)] * VENTANAS)

    copia = recovery.snapshot(sesion)
    nueva = _sesion()
    recovery.restore(nueva, copia)

    assert nueva.scoring.pending_suggestions() == 0
    assert recovery.summary(copia) == (0, 0)


def test_una_clase_que_ya_existe_conserva_su_color():
    """El color de las preferencias pudo cambiar desde que se escribió la copia."""
    copia = recovery.snapshot(_con_trabajo())
    nueva = _sesion()
    nueva.annotations.add_label("Mía", "#654321")

    recovery.restore(nueva, copia)

    assert nueva.annotations.color_of("Mía") == "#654321"


def test_el_resumen_cuenta_ventanas_con_trabajo_y_anotaciones():
    # Dos ventanas tienen fase y una tercera sólo tiene arousal.
    assert recovery.summary(recovery.snapshot(_con_trabajo())) == (3, 2)


def test_la_copia_guarda_derivaciones_encadenadas_en_orden_y_con_clase():
    original = _registro()
    montado = derive_montage(
        original,
        [("C0", "C1"), ("C0-C1", "C1")],
        names=["C0-C1", "doble"],
        channel_kinds=[ChannelKind.EEG, ChannelKind.OTHER],
    )

    copia = _por_texto(recovery.snapshot(_sesion(montado)))

    assert copia["derivaciones"] == [
        ["C0", "C1", "C0-C1", "EEG"],
        ["C0-C1", "C1", "doble", "OTHER"],
    ]


# -- Que sea de este registro -------------------------------------------------------


def test_la_copia_es_del_registro_del_que_se_hizo():
    registro = _registro()
    copia = _por_texto(recovery.snapshot(_sesion(registro)))

    assert recovery.matches(copia, registro)
    # La carpeta pudo cambiar de nombre: eso no cambia el registro.
    assert recovery.matches(copia, _registro())


@pytest.mark.parametrize(
    "otro",
    [
        _registro(nombre="otra.edf"),
        _registro(ventanas=VENTANAS + 1),
        _registro(canales=3),
    ],
    ids=["otro-nombre", "otro-largo", "otros-canales"],
)
def test_una_copia_de_otro_registro_no_coincide(otro: Recording):
    copia = recovery.snapshot(_sesion())

    assert not recovery.matches(copia, otro)
    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(_sesion(otro), copia)


def test_una_copia_de_otra_forma_no_coincide():
    copia = recovery.snapshot(_sesion())
    copia["formato"] = recovery.RECOVERY_FORMAT + 1

    assert not recovery.matches(copia, _registro())


def _identidad_v1(registro: Recording) -> dict[str, object]:
    """Los cuatro campos de `registro` que escribía el formato 1."""
    return {
        "archivo": registro.file_path.name,
        "frecuencia": float(registro.sampling_rate),
        "muestras": int(registro.n_samples),
        "canales": registro.channel_names(),
    }


def test_v1_coincide_solo_con_la_identidad_antigua_del_original():
    original = _registro()
    copia = {"formato": 1, "registro": _identidad_v1(original)}

    assert recovery.legacy_matches(copia, original)
    assert not recovery.legacy_matches(copia, _registro(nombre="otra.edf"))
    assert not recovery.legacy_matches(copia, _registro(ventanas=VENTANAS + 1))
    assert not recovery.legacy_matches(copia, _registro(canales=3))
    assert not recovery.legacy_matches(copia, _registro(canales=1))
    assert not recovery.matches(copia, original)


def test_v1_no_puede_distinguir_otra_senal_con_la_misma_forma():
    original = _registro()
    copia = {"formato": 1, "registro": _identidad_v1(original)}
    reemplazo = _registro()
    reemplazo.data[0, reemplazo.n_samples // 2] = 1.0

    assert recovery.legacy_matches(copia, reemplazo)


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("archivo", "otra.edf"),
        ("frecuencia", 99.0),
        ("muestras", 12001),
        ("canales", ["C1", "C0"]),
    ],
)
def test_v1_rechaza_cualquier_cambio_en_la_identidad(campo: str, valor: object):
    original = _registro()
    registro_v1 = _identidad_v1(original)
    registro_v1[campo] = valor

    assert not recovery.legacy_matches({"formato": 1, "registro": registro_v1}, original)


@pytest.mark.parametrize(
    "cambio",
    [
        {"formato": True},
        {"formato": 2},
        {"derivaciones": []},
        {"registro": {"archivo": "noche.edf", "frecuencia": 100.0,
                      "muestras": 12000, "canales": ["C0", "C1", "C0-M1"]}},
        {"registro": {"archivo": "noche.edf", "frecuencia": 100.0,
                      "muestras": True, "canales": ["C0", "C1"]}},
    ],
    ids=["formato-bool", "formato-nuevo", "receta-nueva", "canal-extra", "muestras-bool"],
)
def test_v1_rechaza_formas_o_canales_que_no_son_del_original(cambio: dict):
    original = _registro()
    copia = {"formato": 1, "registro": _identidad_v1(original), **cambio}

    assert not recovery.legacy_matches(copia, original)


def test_v1_se_convierte_solo_en_memoria_y_pasa_el_preflight_actual():
    original = _registro()
    copia_v1 = {
        "formato": 1,
        "registro": _identidad_v1(original),
        "ventana": 1,
        "nomenclatura": "AASM",
        "fases": ["N2", "UNSCORED", "UNSCORED", "UNSCORED"],
        "arousals": [],
        "clases": [["Spindle", "#123456"]],
        "anotaciones": [["Spindle", 100, 50, ["C0"], None]],
    }
    antes = _por_texto(copia_v1)
    identidad = recovery.fingerprint(original)

    convertida = recovery.upgrade_legacy(copia_v1, original, identidad)

    assert copia_v1 == antes
    assert convertida == {
        **copia_v1,
        "formato": recovery.RECOVERY_FORMAT,
        "registro": identidad,
        "derivaciones": [],
    }
    recovery.preflight(_sesion(original), convertida, identidad)


def test_misma_forma_con_senal_distinta_no_coincide():
    original = _registro()
    copia = recovery.snapshot(_sesion(original))
    reemplazo = _registro()
    reemplazo.data[0, reemplazo.n_samples // 2] = 1.0

    assert not recovery.matches(copia, reemplazo)


def test_fingerprint_identifica_el_contenido_completo_del_registro_original():
    original = _registro()
    identidad = recovery.fingerprint(original)
    distinta = _registro()
    distinta.data[0, distinta.n_samples // 2] = 1.0

    assert identidad["sha256"] == recovery.fingerprint(original)["sha256"]
    assert identidad["sha256"] != recovery.fingerprint(distinta)["sha256"]
    assert recovery.matches(
        recovery.snapshot(_sesion(original), identidad), identidad
    )
    assert not recovery.matches(
        recovery.snapshot(_sesion(original), identidad),
        recovery.fingerprint(distinta),
    )


def test_fingerprint_incluye_hora_de_inicio():
    base = _registro()
    con_inicio = Recording(
        base.file_path, base.channels, base.data, base.sampling_rate,
        start_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    assert recovery.fingerprint(base) != recovery.fingerprint(con_inicio)


def test_fingerprint_admite_matriz_no_contigua():
    base = _registro()
    almacen = np.arange(base.n_channels * base.n_samples * 2, dtype=float).reshape(
        base.n_channels, base.n_samples * 2
    )
    no_contigua = almacen[:, ::2]
    vista = Recording(base.file_path, base.channels, no_contigua, base.sampling_rate)
    compacta = Recording(base.file_path, base.channels, no_contigua.copy(), base.sampling_rate)

    assert not vista.data.flags.c_contiguous
    assert recovery.fingerprint(vista) == recovery.fingerprint(compacta)


def test_un_arousal_sin_fase_cuenta_como_trabajo_recuperable():
    sesion = _sesion()
    sesion.scoring.set_arousal(2, True)

    assert recovery.summary(recovery.snapshot(sesion)) == (1, 0)


def test_la_copia_corrupta_se_prevalida_sin_tocar_la_sesion():
    identidad = recovery.fingerprint(_registro())
    original = _con_trabajo()
    copia = _por_texto(recovery.snapshot(original, identidad))
    copia["anotaciones"][0][3] = ["canal-inexistente"]
    nueva = _sesion()
    antes = recovery.snapshot(nueva, identidad)

    with pytest.raises(UnreadableRecoveryError):
        recovery.preflight(nueva, copia, identidad)

    assert recovery.snapshot(nueva, identidad) == antes


def test_canales_anotacion_anidados_rechazan_copia_sin_error_crudo():
    identidad = recovery.fingerprint(_registro())
    copia = recovery.snapshot(_con_trabajo(), identidad)
    copia["anotaciones"][0][3] = [["C0"]]
    nueva = _sesion()

    with pytest.raises(UnreadableRecoveryError):
        recovery.preflight(nueva, copia, identidad)

    assert nueva.scoring.scored_windows() == 0
    assert nueva.annotations.all() == []


# -- Todo o nada ---------------------------------------------------------------


def test_sobre_una_sesion_con_trabajo_no_se_mezcla():
    copia = recovery.snapshot(_con_trabajo())
    nueva = _sesion()
    nueva.scoring.set_stage(0, SleepStage.N1)

    with pytest.raises(PsgLabError):
        recovery.restore(nueva, copia)

    assert nueva.scoring.get(0).stage is SleepStage.N1


def _rota(clave: str, valor: object) -> dict:
    copia = recovery.snapshot(_con_trabajo())
    copia[clave] = valor
    return copia


@pytest.mark.parametrize(
    "copia",
    [
        None,
        [],
        {"formato": 1},
        _rota("fases", ["N2"] * VENTANAS + ["N2"]),
        _rota("fases", ["NINGUNA"] * VENTANAS),
        _rota("nomenclatura", "OTRA"),
        _rota("arousals", [VENTANAS]),
        _rota("arousals", ["2"]),
        _rota("ventana", -1),
        _rota("ventana", "3"),
        _rota("anotaciones", [["Mía", 100, 50]]),
        _rota("anotaciones", [["Mía", 10**9, 50, [], None]]),
        _rota("anotaciones", [["Mía", 100, 50, ["C9"], None]]),
        _rota("clases", [["Mía"]]),
    ],
    ids=[
        "nada", "lista", "sin-partes", "una-fase-de-mas", "fase-desconocida",
        "nomenclatura-desconocida", "arousal-fuera", "arousal-texto",
        "ventana-negativa", "ventana-texto", "anotacion-corta",
        "anotacion-fuera-del-registro", "anotacion-en-otro-canal", "clase-corta",
    ],
)
def test_una_copia_rota_se_rechaza_sin_tocar_la_sesion(copia: object):
    nueva = _sesion()

    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(nueva, copia)

    assert nueva.scoring.scored_windows() == 0
    assert nueva.annotations.all() == []


def test_lo_que_falla_al_aplicarse_deshace_lo_ya_puesto(monkeypatch):
    """Un fallo en la segunda anotación revierte la primera y el scoring."""
    copia = recovery.snapshot(_con_trabajo())
    nueva = _sesion()
    nomenclatura_antes = nueva.scoring.nomenclature
    clases_antes = nueva.annotations.labels()
    agregar = nueva.annotations.add
    llamadas = 0

    def fallar_en_la_segunda(anotacion):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise PsgLabError("falló la segunda anotación")
        agregar(anotacion)

    monkeypatch.setattr(nueva.annotations, "add", fallar_en_la_segunda)

    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(nueva, copia)

    assert llamadas == 2
    assert nueva.scoring.scored_windows() == 0
    assert not any(nueva.scoring.get(i).arousal for i in range(VENTANAS))
    assert nueva.annotations.all() == []
    assert nueva.scoring.nomenclature is nomenclatura_antes
    assert nueva.annotations.labels() == clases_antes


# -- Copias rotas que ningún test probaba (hito 81) ----------------------------


def test_una_anotacion_con_un_color_que_no_es_un_color_rechaza_la_copia():
    """**Se aceptaba**: la copia es un JSON en el perfil y puede quedar dañada,
    y un color `7` llegaba hasta el dibujo. Ver
    `test_un_color_propio_que_no_es_rrggbb_se_rechaza`."""
    copia = _por_texto(recovery.snapshot(_con_trabajo()))
    copia["anotaciones"][0][4] = 7
    nueva = _sesion()

    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(nueva, copia)

    assert nueva.annotations.all() == []


def test_una_anotacion_con_los_canales_mal_escritos_rechaza_la_copia():
    copia = _por_texto(recovery.snapshot(_con_trabajo()))
    copia["anotaciones"][0][3] = 5
    nueva = _sesion()

    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(nueva, copia)

    assert nueva.annotations.all() == []


def test_una_copia_que_se_rompe_a_mitad_deshace_tambien_lo_que_ya_entro():
    """La primera anotación entra y la última no, porque su clase no está en
    la copia: **todo o nada** quiere decir que la primera también se va, y las
    fases con ella. Ningún test llegaba a una falla después de la primera
    anotación, así que el deshacer de las anotaciones no se ejecutaba nunca."""
    copia = _por_texto(recovery.snapshot(_con_trabajo()))
    copia["anotaciones"].append(["Fantasma", 10, 5, [], None])
    nueva = _sesion()

    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(nueva, copia)

    assert nueva.annotations.all() == []
    assert nueva.scoring.scored_windows() == 0
    assert not any(nueva.scoring.get(i).arousal for i in range(VENTANAS))
