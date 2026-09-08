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

from psglab.analysis.derivation import derive, derive_montage
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
