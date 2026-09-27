"""Tests de las derivaciones.

Una derivación es una resta, así que **todo lo que se afirma acá es exacto**: no
hay tolerancia, ni pico aproximado, ni orden de magnitud. Es la clase de test
que el proyecto prefiere y por eso este módulo va primero en la Parte 2.

Lo que no es exacto son las tres decisiones que el esqueleto dejaba abiertas —qué
clase, qué unidad y qué frecuencia original lleva el canal nuevo—, y ésas se
afirman porque son decisiones, no porque sean aritmética.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.derivation import (
    AASM_MONTAGE,
    derive,
    derive_montage,
    plan_aasm_montage,
)
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    ChannelNotFoundError,
    DuplicateChannelError,
    InvalidRecordingError,
    PsgLabError,
)
from psglab.utils.units import MICROVOLT


@pytest.fixture
def con_termometro(sampling_rate: float) -> Recording:
    """Dos EEG, un EMG y un termómetro.

    El termómetro es el que separa las reglas: derivar contra él no tiene
    sentido y tiene que rechazarse.
    """
    muestras = int(sampling_rate * 4)
    tiempos = np.arange(muestras) / sampling_rate
    datos = np.vstack(
        [
            50.0 * np.sin(2 * np.pi * 10 * tiempos),
            20.0 * np.sin(2 * np.pi * 10 * tiempos),
            15.0 * np.sin(2 * np.pi * 30 * tiempos),
            36.5 + np.zeros(muestras),
        ]
    )
    return Recording(
        file_path=Path("mixto.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, MICROVOLT, 0, 256.0),
            Channel("A2", ChannelKind.EEG, MICROVOLT, 1, 256.0),
            Channel("EMG-menton", ChannelKind.EMG, MICROVOLT, 2, 128.0),
            Channel("Temp rectal", ChannelKind.OTHER, "DegC", 3),
        ],
        data=datos,
        sampling_rate=sampling_rate,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


# -- La resta, que es exacta -------------------------------------------------


def test_el_canal_derivado_es_la_resta(registro_sintetico: Recording):
    derivado = derive(registro_sintetico, "C3", "C4")

    esperado = registro_sintetico.data[0] - registro_sintetico.data[1]
    assert np.array_equal(derivado.data[-1], esperado)


def test_se_agrega_al_final_sin_tocar_los_de_antes(registro_sintetico: Recording):
    derivado = derive(registro_sintetico, "C3", "C4")

    assert derivado.n_channels == registro_sintetico.n_channels + 1
    assert np.array_equal(
        derivado.data[: registro_sintetico.n_channels], registro_sintetico.data
    )


def test_el_original_no_se_toca(registro_sintetico: Recording):
    """Regla 1 de la carpeta: el usuario tiene que poder volver atrás."""
    antes = registro_sintetico.data.copy()
    canales_antes = list(registro_sintetico.channels)

    derive(registro_sintetico, "C3", "C4")

    assert np.array_equal(registro_sintetico.data, antes)
    assert registro_sintetico.channels == canales_antes


def test_el_nombre_por_defecto_es_el_del_montaje(registro_sintetico: Recording):
    """"C3-A2" es cómo se nombra un montaje de polisomnografía."""
    assert derive(registro_sintetico, "C3", "C4").channels[-1].name == "C3-C4"


def test_se_le_puede_dar_otro_nombre(registro_sintetico: Recording):
    derivado = derive(registro_sintetico, "C3", "C4", name="Central izquierda")

    assert derivado.channels[-1].name == "Central izquierda"


def test_derivar_dos_veces_encadena(registro_sintetico: Recording):
    """El resultado es un `Recording` como cualquier otro."""
    una = derive(registro_sintetico, "C3", "C4")
    dos = derive(una, "C4", "EOG-izq")

    assert dos.n_channels == registro_sintetico.n_channels + 2
    assert [c.name for c in dos.channels[-2:]] == ["C3-C4", "C4-EOG-izq"]


# -- Las tres decisiones del canal nuevo -------------------------------------


def test_dos_canales_de_la_misma_clase_dan_esa_clase(con_termometro: Recording):
    assert derive(con_termometro, "C3", "A2").channels[-1].kind is ChannelKind.EEG


def test_dos_clases_distintas_dan_OTHER(con_termometro: Recording):
    """Un "C3-EMG" no es un EEG ni un EMG. Decir que es cualquiera de los dos
    haría que después se lo filtrara con los parámetros equivocados."""
    derivado = derive(con_termometro, "C3", "EMG-menton")

    assert derivado.channels[-1].kind is ChannelKind.OTHER


def test_el_derivado_conserva_la_unidad(con_termometro: Recording):
    assert derive(con_termometro, "C3", "A2").channels[-1].unit == MICROVOLT


def test_la_frecuencia_original_se_conserva_si_coincide(con_termometro: Recording):
    assert derive(con_termometro, "C3", "A2").channels[-1].original_sampling_rate == 256.0


def test_si_las_frecuencias_originales_difieren_queda_en_none(
    con_termometro: Recording,
):
    """Un derivado de dos canales que venían a frecuencias distintas no vino a
    ninguna, y decir que vino a una de las dos sería inventar."""
    derivado = derive(con_termometro, "C3", "EMG-menton")

    assert derivado.channels[-1].original_sampling_rate is None


# -- Los rechazos ------------------------------------------------------------


def test_unidades_distintas_se_rechazan(con_termometro: Recording):
    """**El caso que no falla solo.** Restarle grados a microvoltios da un
    número perfectamente plausible que no significa nada."""
    with pytest.raises(InvalidRecordingError):
        derive(con_termometro, "C3", "Temp rectal")


def test_un_canal_que_no_existe_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(ChannelNotFoundError):
        derive(registro_sintetico, "C3", "no_existe")


def test_un_nombre_repetido_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(DuplicateChannelError):
        derive(registro_sintetico, "C3", "C4", name="EOG-izq")


def test_derivar_dos_veces_el_mismo_par_se_rechaza(registro_sintetico: Recording):
    """El nombre por defecto ya estaría tomado."""
    una = derive(registro_sintetico, "C3", "C4")

    with pytest.raises(DuplicateChannelError):
        derive(una, "C3", "C4")


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    """La ventana principal atrapa una sola clase: un `AttributeError` crudo le
    llegaría al investigador como traza."""
    with pytest.raises(PsgLabError):
        derive(hostil, "C3", "C4")


# -- El montaje completo -----------------------------------------------------


def test_el_montaje_agrega_un_canal_por_par(registro_sintetico: Recording):
    montado = derive_montage(
        registro_sintetico, [("C3", "C4"), ("EOG-izq", "EMG-menton")]
    )

    assert montado.n_channels == registro_sintetico.n_channels + 2
    assert [c.name for c in montado.channels[-2:]] == ["C3-C4", "EOG-izq-EMG-menton"]


def test_el_montaje_respeta_el_orden_de_los_pares(registro_sintetico: Recording):
    montado = derive_montage(
        registro_sintetico, [("EOG-izq", "C3"), ("C4", "EMG-menton")]
    )

    assert [c.name for c in montado.channels[-2:]] == ["EOG-izq-C3", "C4-EMG-menton"]


def test_un_montaje_vacio_no_cambia_nada(registro_sintetico: Recording):
    montado = derive_montage(registro_sintetico, [])

    assert montado.n_channels == registro_sintetico.n_channels


def test_el_montaje_es_atomico(registro_sintetico: Recording):
    """**Un montaje a medias es peor que ninguno.**

    El usuario vería algunos canales derivados y otros no, sin nada que le diga
    cuáles. Acá el segundo par nombra un canal que no existe, así que el primero
    tampoco tiene que quedar aplicado.
    """
    with pytest.raises(ChannelNotFoundError):
        derive_montage(registro_sintetico, [("C3", "C4"), ("no_existe", "C4")])

    assert "C3-C4" not in registro_sintetico.channel_names()


def test_el_montaje_es_atomico_tambien_ante_unidades_distintas(
    con_termometro: Recording,
):
    with pytest.raises(InvalidRecordingError):
        derive_montage(con_termometro, [("C3", "A2"), ("C3", "Temp rectal")])

    assert "C3-A2" not in con_termometro.channel_names()


def test_un_par_mal_formado_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(InvalidRecordingError):
        derive_montage(registro_sintetico, [("C3",)])


def test_un_montaje_que_no_es_lista_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(InvalidRecordingError):
        derive_montage(registro_sintetico, "C3-C4")


# -- Un montaje se arma de una sola vez (hito 18) ----------------------------


def test_una_derivacion_puede_partir_de_otra(registro_sintetico: Recording):
    """**El encadenado, que nadie testeaba y que el hito 18 tuvo que conservar.**

    `derive_montage()` dejó de llamar a `derive()` en cadena —cada llamada
    copiaba la matriz entera, así que un montaje de N pares copiaba el registro
    N veces— y pasó a acumular las filas y armar la matriz una sola vez. Eso
    podía haberse llevado por delante esta propiedad: que un par nombre un
    canal creado por un par anterior.
    """
    montado = derive_montage(
        registro_sintetico, [("C3", "C4"), ("C3-C4", "EOG-izq")]
    )

    assert [c.name for c in montado.channels[-2:]] == ["C3-C4", "C3-C4-EOG-izq"]


def test_la_derivacion_encadenada_da_el_numero_correcto(
    registro_sintetico: Recording,
):
    """Y que el resultado sea el de la cuenta, no sólo que exista el canal."""
    montado = derive_montage(
        registro_sintetico, [("C3", "C4"), ("C3-C4", "EOG-izq")]
    )

    datos = np.asarray(montado.data)
    c3 = datos[montado.channel_by_name("C3").index]
    c4 = datos[montado.channel_by_name("C4").index]
    eog = datos[montado.channel_by_name("EOG-izq").index]

    assert datos[montado.channel_by_name("C3-C4").index] == pytest.approx(c3 - c4)
    assert datos[montado.channel_by_name("C3-C4-EOG-izq").index] == pytest.approx(
        c3 - c4 - eog
    )


# -- El nombre y la clase de cada derivado del montaje -----------------------


def test_el_montaje_puede_nombrar_cada_derivado(registro_sintetico: Recording):
    montado = derive_montage(
        registro_sintetico, [("C3", "C4"), ("EOG-izq", "C4")], names=["A", "B"]
    )

    assert [c.name for c in montado.channels[-2:]] == ["A", "B"]


def test_el_montaje_puede_declarar_la_clase(registro_sintetico: Recording):
    """«E1-M2» es un EOG aunque M2 sea un electrodo de EEG: la regla de
    `derive()` le daría OTHER, y el montaje sabe más que ella."""
    montado = derive_montage(
        registro_sintetico, [("EOG-izq", "C4")], channel_kinds=[ChannelKind.EOG]
    )

    assert montado.channels[-1].kind is ChannelKind.EOG


def test_sin_clase_declarada_vale_la_regla_de_siempre(registro_sintetico: Recording):
    montado = derive_montage(registro_sintetico, [("EOG-izq", "C4")])

    assert montado.channels[-1].kind is ChannelKind.OTHER


@pytest.mark.parametrize(
    ("names", "channel_kinds"),
    [
        (["uno"], None),
        (["uno", "dos", "tres"], None),
        (None, [ChannelKind.EEG]),
        ("uno-dos", None),
        (None, ["EEG", "EEG"]),
    ],
)
def test_nombres_o_clases_que_no_acompanan_a_los_pares_se_rechazan(
    registro_sintetico: Recording, names, channel_kinds
):
    """Uno por par, ni más ni menos: una lista corta dejaría un derivado sin
    nombre y una larga hablaría de un par que no está."""
    with pytest.raises(InvalidRecordingError):
        derive_montage(
            registro_sintetico, [("C3", "C4"), ("EOG-izq", "C4")], names=names, channel_kinds=channel_kinds
        )


def test_un_nombre_repetido_dentro_del_montaje_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(DuplicateChannelError):
        derive_montage(
            registro_sintetico, [("C3", "C4"), ("EOG-izq", "C4")], names=["X", "X"]
        )


# -- El montaje de la AASM ---------------------------------------------------


def _registro_con(nombres: list[str], clases: list[ChannelKind] | None = None) -> Recording:
    """Un registro con esos canales; la fila i vale i en todas sus muestras,
    así que la resta de un derivado se lee directo."""
    clases = clases or [ChannelKind.EEG] * len(nombres)
    return Recording(
        file_path=Path("aasm.edf"),
        channels=[
            Channel(nombre, clase, MICROVOLT, i)
            for i, (nombre, clase) in enumerate(zip(nombres, clases))
        ],
        data=np.arange(len(nombres), dtype=float)[:, None] * np.ones((1, 256)),
        sampling_rate=256.0,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


def test_el_montaje_aasm_completo():
    registro = _registro_con(
        ["F4", "C4", "O2", "F3", "C3", "O1", "E1", "E2", "M1", "M2", "Chin"]
    )

    plan = plan_aasm_montage(registro)

    assert plan.names == [f"{a}-{r}" for a, r, _ in AASM_MONTAGE]
    assert plan.channel_kinds == [c for _, _, c in AASM_MONTAGE]
    assert plan.missing == []
    assert plan.already_present == []


def test_los_eeg_van_contra_la_mastoides_del_otro_lado():
    """F4, C4 y O2 contra M1; F3, C3 y O1 contra M2; los dos ojos contra M2."""
    plan = plan_aasm_montage(
        _registro_con(["F4", "C4", "O2", "F3", "C3", "O1", "E1", "E2", "M1", "M2"])
    )

    assert dict(zip(plan.names, plan.pairs))["C4-M1"] == ("C4", "M1")
    assert dict(zip(plan.names, plan.pairs))["C3-M2"] == ("C3", "M2")
    assert dict(zip(plan.names, plan.pairs))["E1-M2"] == ("E1", "M2")
    assert dict(zip(plan.names, plan.pairs))["E2-M2"] == ("E2", "M2")


def test_el_montaje_aplicado_da_la_resta_y_la_clase():
    registro = _registro_con(["C4", "E1", "M1", "M2"])
    plan = plan_aasm_montage(registro)

    montado = derive_montage(registro, plan.pairs, names=plan.names, channel_kinds=plan.channel_kinds)

    c4_m1 = montado.channel_by_name("C4-M1")
    e1_m2 = montado.channel_by_name("E1-M2")
    assert np.asarray(montado.data)[c4_m1.index] == pytest.approx(0.0 - 2.0)
    assert np.asarray(montado.data)[e1_m2.index] == pytest.approx(1.0 - 3.0)
    assert c4_m1.kind is ChannelKind.EEG
    assert e1_m2.kind is ChannelKind.EOG


def test_los_nombres_con_adornos_de_los_equipos():
    """«EEG C4-REF» es el C4: los equipos le agregan la clase y la referencia
    de grabación, y el derivado se llama como lo llama la AASM."""
    plan = plan_aasm_montage(_registro_con(["EEG C4-REF", "EEG M1-REF"]))

    assert plan.pairs == [("EEG C4-REF", "EEG M1-REF")]
    assert plan.names == ["C4-M1"]


def test_loc_y_roc_son_e1_y_e2():
    plan = plan_aasm_montage(_registro_con(["LOC", "ROC", "M2"]))

    assert plan.pairs == [("LOC", "M2"), ("ROC", "M2")]
    assert plan.names == ["E1-M2", "E2-M2"]


def test_sin_mastoides_usa_los_lobulos_y_lo_dice_en_el_nombre():
    """A1 y A2 no son las mastoides: si se usan, el derivado se llama «C4-A1»
    para que el nombre no diga algo que no se registró."""
    plan = plan_aasm_montage(_registro_con(["C4", "C3", "A1", "A2"]))

    assert plan.names == ["C4-A1", "C3-A2"]


def test_la_mastoides_gana_al_lobulo():
    plan = plan_aasm_montage(_registro_con(["C4", "A1", "M1"]))

    assert plan.pairs == [("C4", "M1")]


def test_lo_que_falta_se_informa_con_el_electrodo():
    plan = plan_aasm_montage(_registro_con(["C4", "M1", "E1"]))

    assert plan.names == ["C4-M1"]
    assert "O2-M1 (falta O2)" in plan.missing
    assert "E1-M2 (falta M2)" in plan.missing
    assert "O1-M2 (falta O1 y M2)" in plan.missing


def test_lo_ya_derivado_no_se_repite():
    """Un registro que ya trae «C4-M1» —o «LOC-M2», que es «E1-M2»— no la
    vuelve a derivar: `derive_montage()` la rechazaría como repetida."""
    plan = plan_aasm_montage(
        _registro_con(["C4", "M1", "M2", "LOC", "C4-M1", "LOC-M2"])
    )

    assert plan.pairs == []
    assert plan.already_present == ["C4-M1", "E1-M2"]


def test_un_registro_sin_electrodos_da_un_plan_vacio(registro_sintetico: Recording):
    """Los nombres del registro sintético no son del montaje: no es un error,
    es un plan sin nada que derivar."""
    plan = plan_aasm_montage(registro_sintetico)

    assert plan.pairs == []
    assert len(plan.missing) == len(AASM_MONTAGE)


def test_un_bipolar_no_es_un_electrodo():
    """«Fpz-Cz» nombra dos electrodos: no sirve de Cz ni de Fpz."""
    plan = plan_aasm_montage(_registro_con(["F4-C4", "M1"]))

    assert plan.pairs == []


@pytest.mark.parametrize("hostil", [None, "registro", 3])
def test_el_plan_de_algo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        plan_aasm_montage(hostil)
