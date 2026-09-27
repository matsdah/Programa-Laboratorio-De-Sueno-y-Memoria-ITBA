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
from pathlib import Path

import numpy as np
import pytest

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


def test_el_resumen_cuenta_ventanas_scoreadas_y_anotaciones():
    assert recovery.summary(recovery.snapshot(_con_trabajo())) == (2, 2)


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


def test_lo_que_falla_al_aplicarse_deshace_lo_ya_puesto():
    """Un color de clase inválido sólo lo rechaza `add_label()`, y para
    entonces las fases ya se habían puesto."""
    copia = recovery.snapshot(_con_trabajo())
    copia["clases"].append(["Nueva", "rojo"])
    nueva = _sesion()

    with pytest.raises(UnreadableRecoveryError):
        recovery.restore(nueva, copia)

    assert nueva.scoring.scored_windows() == 0
    assert not any(nueva.scoring.get(i).arousal for i in range(VENTANAS))
    assert nueva.annotations.all() == []
