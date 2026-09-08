"""Tests del puente entre `Recording` y `mne.io.Raw`.

**La propiedad que importa es que ida y vuelta devuelva lo mismo.** Todo lo que
se apoye en este módulo —los filtros, la ICA, el re-referenciado— hereda su
corrección, y un error de escala acá se manifiesta tres capas más arriba como
una señal un millón de veces más chica.

Ese factor de un millón no es una exageración retórica: es exactamente lo que
separa un volt de un microvoltio, y es el error que este módulo existe para no
cometer. MNE trabaja en volts y el `Recording` en microvoltios.

El caso que más fácil se rompe no es el del EEG sino el del canal que **no** es
eléctrico: un termómetro escalado por un millón no da un error visible, da una
temperatura absurda que alguien va a interpretar como señal.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.mne_bridge import (
    UNIDAD_DE_MNE,
    from_raw,
    to_raw,
    unidad_de_salida,
)
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import InvalidRecordingError, PsgLabError
from psglab.utils.units import MICROVOLT


@pytest.fixture
def mixto(sampling_rate: float) -> Recording:
    """Un registro con un canal eléctrico y uno que no lo es.

    Es el caso que separa las dos reglas de escalado, y el que un registro
    puramente de EEG no ejercita.
    """
    muestras = int(sampling_rate * 4)
    tiempos = np.arange(muestras) / sampling_rate
    datos = np.vstack(
        [
            50.0 * np.sin(2 * np.pi * 10 * tiempos),  # C3, en µV
            36.5 + 0.1 * np.sin(2 * np.pi * 0.01 * tiempos),  # temperatura, en °C
        ]
    )
    return Recording(
        file_path=Path("mixto.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, MICROVOLT, 0),
            Channel("Temp rectal", ChannelKind.OTHER, "DegC", 1),
        ],
        data=datos,
        sampling_rate=sampling_rate,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


# -- Ida y vuelta ------------------------------------------------------------


def test_ida_y_vuelta_devuelve_la_misma_señal(registro_sintetico: Recording):
    """**La propiedad central.** Si esto falla, todo lo que use el puente miente."""
    vuelta = from_raw(to_raw(registro_sintetico), registro_sintetico)

    assert np.allclose(vuelta.data, registro_sintetico.data)


def test_ida_y_vuelta_conserva_lo_que_mne_no_sabe(registro_sintetico: Recording):
    """MNE no lleva la ruta del archivo, ni la hora de inicio, ni la clase de
    canal, ni la unidad. Se toman del original o se pierden."""
    vuelta = from_raw(to_raw(registro_sintetico), registro_sintetico)

    assert vuelta.file_path == registro_sintetico.file_path
    assert vuelta.start_time == registro_sintetico.start_time
    assert vuelta.sampling_rate == registro_sintetico.sampling_rate
    assert [c.kind for c in vuelta.channels] == [
        c.kind for c in registro_sintetico.channels
    ]
    assert [c.unit for c in vuelta.channels] == [
        c.unit for c in registro_sintetico.channels
    ]


def test_ida_y_vuelta_no_toca_el_original(registro_sintetico: Recording):
    """Es la regla 1 de la carpeta: el usuario tiene que poder comparar la señal
    procesada con la cruda, y volver atrás."""
    antes = registro_sintetico.data.copy()
    from_raw(to_raw(registro_sintetico), registro_sintetico)

    assert np.array_equal(registro_sintetico.data, antes)


def test_el_original_no_se_toca_ni_siquiera_al_ir(registro_sintetico: Recording):
    """`to_raw()` escala los datos, y hacerlo sobre el array del registro los
    dejaría en volts sin que nadie lo pidiera."""
    antes = registro_sintetico.data.copy()
    to_raw(registro_sintetico)

    assert np.array_equal(registro_sintetico.data, antes)


# -- La unidad, que es lo delicado -------------------------------------------


def test_lo_electrico_sale_en_volts(registro_sintetico: Recording):
    """El registro está en µV y MNE espera volts: un pico de 50 µV tiene que
    llegarle como 5e-5."""
    raw = to_raw(registro_sintetico)
    pico = float(np.max(np.abs(raw.get_data()[0])))

    assert pico == pytest.approx(50e-6, rel=1e-6)
    assert UNIDAD_DE_MNE == "V"


def test_lo_que_no_es_electrico_no_se_escala(mixto: Recording):
    """**El caso que un registro de puro EEG no ejercita.**

    Una temperatura de 36,5 °C escalada por un millón no da un error visible:
    da 36 500 000, que alguien va a leer como señal.
    """
    raw = to_raw(mixto)
    temperatura = raw.get_data()[1]

    assert float(np.mean(temperatura)) == pytest.approx(36.5, abs=0.2)


def test_la_temperatura_sobrevive_la_ida_y_vuelta(mixto: Recording):
    vuelta = from_raw(to_raw(mixto), mixto)

    assert np.allclose(vuelta.data[1], mixto.data[1])
    assert vuelta.channels[1].unit == "DegC"


def test_la_unidad_de_salida_dice_la_regla(mixto: Recording):
    """Existe para que cada análisis no vuelva a razonarla."""
    assert unidad_de_salida(mixto.channels[0]) == MICROVOLT
    assert unidad_de_salida(mixto.channels[1]) == "DegC"


# -- Lo que MNE necesita saber -----------------------------------------------


def test_cada_canal_declara_su_tipo(registro_sintetico: Recording):
    """MNE decide con el tipo qué canales filtra y cuáles entran en una ICA.
    Declararlos todos como "misc" haría que ignorara justo los que interesan."""
    raw = to_raw(registro_sintetico)
    tipos = raw.get_channel_types()

    assert tipos == ["eeg", "eeg", "eog", "emg"]


def test_los_nombres_y_el_orden_se_conservan(registro_sintetico: Recording):
    raw = to_raw(registro_sintetico)

    assert raw.ch_names == [c.name for c in registro_sintetico.channels]


def test_la_frecuencia_llega_intacta(registro_sintetico: Recording):
    raw = to_raw(registro_sintetico)

    assert float(raw.info["sfreq"]) == registro_sintetico.sampling_rate


# -- Los rechazos ------------------------------------------------------------


def test_el_puente_no_necesita_guarda_contra_un_registro_vacio(
    sampling_rate: float,
):
    """**El puente no valida que haya canales, y está bien que no lo haga.**

    Se escribió esa guarda y este test la encontró muerta: `Recording` rechaza
    un registro sin canales **al construirse**, así que a `to_raw()` no puede
    llegarle uno vacío. Queda el test, que documenta dónde ocurre de verdad el
    rechazo, y se fue la guarda.
    """
    with pytest.raises(PsgLabError):
        Recording(
            file_path=Path("vacio.edf"),
            channels=[],
            data=np.zeros((0, 10)),
            sampling_rate=sampling_rate,
        )


def test_un_canal_que_mne_invento_se_rechaza(registro_sintetico: Recording):
    """**No se puede adivinar.** Un canal que no estaba en el original no tiene
    clase ni unidad conocidas, y ponerle una por defecto lo haría pasar por
    microvoltios sin que nadie lo haya decidido.
    """
    raw = to_raw(registro_sintetico)
    raw.rename_channels({"C3": "C3-inventado"})

    with pytest.raises(InvalidRecordingError):
        from_raw(raw, registro_sintetico)


# -- El array de sólo lectura ------------------------------------------------


def test_se_puede_convertir_un_tramo_de_get_segment(registro_sintetico: Recording):
    """**El caso que rompía sin la copia explícita.**

    `Recording.get_segment()` devuelve un array de sólo lectura, y MNE escribe
    sobre el buffer que recibe. Sin copiar, esto reventaba con un error de
    numpy tres capas más abajo, hablando de un array no escribible.
    """
    tramo = registro_sintetico.get_segment(0, 1000)
    assert not tramo.flags.writeable

    recorte = Recording(
        file_path=registro_sintetico.file_path,
        channels=registro_sintetico.channels,
        data=tramo,
        sampling_rate=registro_sintetico.sampling_rate,
    )
    raw = to_raw(recorte)

    assert raw.n_times == 1000
