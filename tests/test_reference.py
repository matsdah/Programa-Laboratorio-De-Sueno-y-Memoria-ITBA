"""Tests de la re-referenciación.

Como la derivación, es aritmética exacta y se afirma sin tolerancia. Las dos
propiedades que definen cada variante son afirmables de una línea:

- Re-referenciar a un canal deja **ese canal idénticamente en cero**, porque un
  canal leído contra sí mismo es cero por definición.
- La referencia promedio hace que **la suma de los canales promediados dé cero**
  en cada muestra.

Lo que el esqueleto no decidía —qué pasa con lo que no es eléctrico— se afirma
con un termómetro: tiene que salir intacto. Restarle un promedio de
microvoltios no falla, produce una temperatura falsa.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.reference import average_reference, rereference
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidRecordingError,
    PsgLabError,
)
from psglab.utils.units import MICROVOLT


def registro(canales: list[tuple[str, ChannelKind, str]], fs: float = 256.0):
    """Un registro con los canales pedidos y una señal distinta en cada uno."""
    muestras = int(fs * 4)
    tiempos = np.arange(muestras) / fs
    datos = np.vstack(
        [
            (10.0 * (posicion + 1)) * np.sin(2 * np.pi * (posicion + 1) * tiempos)
            for posicion in range(len(canales))
        ]
    )
    return Recording(
        file_path=Path("mixto.edf"),
        channels=[
            Channel(nombre, clase, unidad, posicion)
            for posicion, (nombre, clase, unidad) in enumerate(canales)
        ],
        data=datos,
        sampling_rate=fs,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


@pytest.fixture
def con_mastoides() -> Recording:
    """Dos EEG y los dos mastoides, que es el caso clásico del pliego."""
    return registro(
        [
            ("C3", ChannelKind.EEG, MICROVOLT),
            ("C4", ChannelKind.EEG, MICROVOLT),
            ("A1", ChannelKind.EEG, MICROVOLT),
            ("A2", ChannelKind.EEG, MICROVOLT),
        ]
    )


@pytest.fixture
def con_termometro() -> Recording:
    return registro(
        [
            ("C3", ChannelKind.EEG, MICROVOLT),
            ("C4", ChannelKind.EEG, MICROVOLT),
            ("Temp rectal", ChannelKind.OTHER, "DegC"),
        ]
    )


# -- Re-referenciar a un canal -----------------------------------------------


def test_el_canal_de_referencia_queda_en_cero(con_mastoides: Recording):
    """**La propiedad que define la operación.** Un canal leído contra sí mismo
    es cero, y si no da cero es que la resta se hizo mal."""
    nuevo = rereference(con_mastoides, ["A2"])
    a2 = nuevo.channel_by_name("A2")

    assert np.allclose(nuevo.data[a2.index], 0.0)


def test_los_demas_quedan_leidos_contra_esa_referencia(con_mastoides: Recording):
    nuevo = rereference(con_mastoides, ["A2"])

    esperado = con_mastoides.data[0] - con_mastoides.data[3]
    assert np.allclose(nuevo.data[0], esperado)


def test_con_dos_canales_se_usa_el_promedio(con_mastoides: Recording):
    """El caso de los mastoides A1+A2, que es el que nombra el docstring."""
    nuevo = rereference(con_mastoides, ["A1", "A2"])

    promedio = (con_mastoides.data[2] + con_mastoides.data[3]) / 2
    assert np.allclose(nuevo.data[0], con_mastoides.data[0] - promedio)


def test_el_original_no_se_toca(con_mastoides: Recording):
    antes = con_mastoides.data.copy()
    rereference(con_mastoides, ["A2"])

    assert np.array_equal(con_mastoides.data, antes)


def test_la_lista_de_canales_no_cambia(con_mastoides: Recording):
    """El canal de referencia se conserva, aunque quede plano: borrarlo en
    silencio le cambiaría al usuario la lista de canales sin avisarle."""
    nuevo = rereference(con_mastoides, ["A2"])

    assert nuevo.channel_names() == con_mastoides.channel_names()


# -- Lo que no es eléctrico --------------------------------------------------


def test_el_termometro_sale_intacto(con_termometro: Recording):
    """**No falla solo.** Restarle a 36,5 °C un promedio de microvoltios da un
    número plausible que no es una temperatura."""
    nuevo = rereference(con_termometro, ["C4"])
    temperatura = nuevo.channel_by_name("Temp rectal")

    assert np.array_equal(
        nuevo.data[temperatura.index], con_termometro.data[temperatura.index]
    )


def test_no_se_puede_referenciar_contra_un_termometro(con_termometro: Recording):
    with pytest.raises(InvalidRecordingError):
        rereference(con_termometro, ["Temp rectal"])


# -- La referencia promedio --------------------------------------------------


def test_la_suma_de_los_eeg_da_cero(con_mastoides: Recording):
    """**La propiedad que define la referencia promedio.**"""
    nuevo = average_reference(con_mastoides)
    eeg = [c.index for c in nuevo.channels if c.kind is ChannelKind.EEG]

    assert np.allclose(nuevo.data[eeg].sum(axis=0), 0.0)


def test_un_emg_no_cambia_el_promedio_de_los_eeg():
    """**La razón de ser del flag `kind_only`.**

    Si el EMG entrara en el promedio, los EEG saldrían distintos. Que salgan
    iguales con y sin él es lo que demuestra que el flag hace lo que dice.
    """
    solo_eeg = registro(
        [("C3", ChannelKind.EEG, MICROVOLT), ("C4", ChannelKind.EEG, MICROVOLT)]
    )
    con_emg = registro(
        [
            ("C3", ChannelKind.EEG, MICROVOLT),
            ("C4", ChannelKind.EEG, MICROVOLT),
            ("EMG-menton", ChannelKind.EMG, MICROVOLT),
        ]
    )

    sin = average_reference(solo_eeg)
    con = average_reference(con_emg)

    assert np.allclose(sin.data[:2], con.data[:2])


def test_sin_el_flag_el_emg_si_entra():
    """La otra mitad de la afirmación anterior: con `kind_only=False` el
    resultado **tiene** que cambiar, o el flag no estaría haciendo nada."""
    solo_eeg = registro(
        [("C3", ChannelKind.EEG, MICROVOLT), ("C4", ChannelKind.EEG, MICROVOLT)]
    )
    con_emg = registro(
        [
            ("C3", ChannelKind.EEG, MICROVOLT),
            ("C4", ChannelKind.EEG, MICROVOLT),
            ("EMG-menton", ChannelKind.EMG, MICROVOLT),
        ]
    )

    sin = average_reference(solo_eeg)
    con = average_reference(con_emg, kind_only=False)

    assert not np.allclose(sin.data[:2], con.data[:2])


def test_el_termometro_tampoco_entra_en_el_promedio(con_termometro: Recording):
    nuevo = average_reference(con_termometro, kind_only=False)
    temperatura = nuevo.channel_by_name("Temp rectal")

    assert np.array_equal(
        nuevo.data[temperatura.index], con_termometro.data[temperatura.index]
    )


def test_sin_canales_eeg_se_rechaza():
    """Devolver la señal sin tocar sería peor: el usuario creería que
    re-referenció."""
    sin_eeg = registro(
        [
            ("EMG-menton", ChannelKind.EMG, MICROVOLT),
            ("ECG", ChannelKind.ECG, MICROVOLT),
        ]
    )

    with pytest.raises(InvalidRecordingError):
        average_reference(sin_eeg)


def test_sin_eeg_pero_con_el_flag_apagado_funciona():
    """La salida que el mensaje de error deja abierta."""
    sin_eeg = registro(
        [
            ("EMG-menton", ChannelKind.EMG, MICROVOLT),
            ("ECG", ChannelKind.ECG, MICROVOLT),
        ]
    )
    nuevo = average_reference(sin_eeg, kind_only=False)

    assert np.allclose(nuevo.data.sum(axis=0), 0.0)


# -- Los rechazos ------------------------------------------------------------


def test_un_canal_de_referencia_que_no_existe_se_rechaza(con_mastoides: Recording):
    with pytest.raises(ChannelNotFoundError):
        rereference(con_mastoides, ["no_existe"])


def test_una_lista_vacia_se_rechaza(con_mastoides: Recording):
    with pytest.raises(InvalidRecordingError):
        rereference(con_mastoides, [])


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        rereference(hostil, ["C3"])
    with pytest.raises(PsgLabError):
        average_reference(hostil)
