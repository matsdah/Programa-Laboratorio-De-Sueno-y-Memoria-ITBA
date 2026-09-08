"""Fixtures compartidas por todos los tests.

Los tests usan **registros sintéticos generados en el momento**, nunca
registros reales de participantes: no se suben datos de personas al
repositorio.

Un registro sintético además es mejor para testear, porque se conoce de
antemano el resultado correcto. Si se genera una onda de 10 Hz, la PSD tiene
que dar un pico en 10 Hz, y eso se puede afirmar en un test.
"""

# **Antes de importar nada de Qt.** El plugin de plataforma se elige al crear la
# `QApplication`, y "offscreen" es lo que permite que los tests de `ui/` corran
# sin pantalla: en el CI no hay ninguna, y en una máquina de trabajo evita que
# la suite abra ventanas por sorpresa.
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pathlib

import numpy as np
import pytest

from datetime import datetime
from pathlib import Path

from psglab.config import WINDOW_SECONDS
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.units import MICROVOLT

#: Ventanas que dura la señal sintética. Se multiplica por `WINDOW_SECONDS` en
#: vez de escribir los 600 segundos a mano: `config.py` promete que cambiar la
#: duración de la ventana se hace en un solo lugar, y con el 600 escrito acá esa
#: promesa era falsa.
VENTANAS_SINTETICAS = 20


@pytest.fixture
def sampling_rate() -> float:
    """Frecuencia de muestreo típica de un registro de polisomnografía."""
    return 256.0


@pytest.fixture
def synthetic_signal(sampling_rate: float) -> np.ndarray:
    """Diez minutos de señal sintética de cuatro canales, en microvoltios.

    Cada canal lleva una frecuencia coherente con el tipo de señal que
    representa, para que los tests de análisis espectral sean a la vez
    verificables y plausibles:

        C3          ->  1 Hz   (delta, sueño lento)
        C4          -> 10 Hz   (alfa)
        EOG-izq     ->  0,5 Hz (movimientos oculares lentos)
        EMG-menton  -> 30 Hz   (actividad muscular)

    El orden coincide con el de la fixture `channel_names`.

    Son exactamente `VENTANAS_SINTETICAS` ventanas completas, un número cómodo
    para verificar los cálculos a mano. La duración sale de
    `config.WINDOW_SECONDS`, así que cambiar la ventana del pliego no rompe
    ningún test.
    """
    duration_seconds = VENTANAS_SINTETICAS * WINDOW_SECONDS
    n_samples = int(duration_seconds * sampling_rate)
    t = np.arange(n_samples) / sampling_rate
    frequencies = [1.0, 10.0, 0.5, 30.0]
    return np.vstack([50.0 * np.sin(2 * np.pi * f * t) for f in frequencies])


@pytest.fixture
def channel_names() -> list[str]:
    """Nombres de canal del registro sintético, uno por clase de señal.

    Cubren las cuatro clases que el pliego nombra en V1_P: EEG (C3 y C4),
    EOG y EMG. Sirven además para testear la detección automática de clase
    (V4_F): "C3" tiene que detectarse como EEG por su nombre 10-20, y
    "EMG-menton" como EMG por su prefijo.
    """
    return ["C3", "C4", "EOG-izq", "EMG-menton"]


@pytest.fixture(scope="session")
def qt_app():
    """Una única `QApplication` para toda la suite.

    **`ui/` no lleva tests unitarios de sus widgets**, y eso no cambia: la regla
    mantiene la capa delgada y empuja la lógica a `core/`. Lo que sí se verifica
    son las piezas que no dibujan —los conversores entre píxeles y unidades, y
    la grilla— porque ahí vive el riesgo de confundir unidades que todo el
    proyecto viene señalando, y porque son las únicas de `ui/` que se pueden
    afirmar sin mirar una pantalla.

    Es de alcance de sesión porque Qt no admite más de una `QApplication` por
    proceso, y se reutiliza la que exista para no chocar con nada.
    """
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


#: Resolución del BrainVision sintético: cuántos µV vale una cuenta entera del
#: `int16` del archivo. Es el campo que el lector tiene que aplicar, y con 0,5
#: un error de escala se ve enseguida.
RESOLUCION_BV_UV = 0.5

#: Frecuencia del BrainVision sintético. **No usa la fixture `sampling_rate`, y
#: el motivo es del formato**: `SamplingInterval` se escribe en microsegundos
#: enteros, así que sólo son representables las frecuencias que dividen un
#: millón. Con los 256 Hz de `sampling_rate` el intervalo da 3906,25 µs, se
#: trunca a 3906 y el archivo termina declarando 256,016 Hz. 250 Hz da 4000 µs
#: exactos y deja que los tests afirmen la frecuencia sin tolerancia.
FRECUENCIA_BV = 250.0


def escribir_brainvision(
    carpeta: pathlib.Path,
    segundos: float,
    canales: list[tuple[str, str]] | None = None,
    impedancias: dict[str, float | None] | None = None,
) -> pathlib.Path:
    """Escribe un BrainVision completo y devuelve la ruta de su `.vhdr`.

    **Por qué existe.** Los quince tests que leen el registro de `data/` son los
    únicos que ejercitan el lector de punta a punta, y se saltean en el CI
    porque `data/` está en el `.gitignore`: son registros de participantes. El
    resultado era que el lector de BrainVision no se ejecutaba en ninguna de las
    seis combinaciones de sistema y versión de Python que corre el CI.

    El formato permite arreglarlo sin pedirle nada a nadie: son tres archivos y
    ninguno es opaco. El `.vhdr` y el `.vmrk` son texto tipo INI y el `.eeg` es
    un `int16` multiplexado crudo, así que se escriben con numpy y pathlib.

    **La cabecera declara `Codepage=UTF-8` y escribe la unidad en UTF-8 a
    propósito**, porque ahí estuvo un bug real: leerla como latin-1 parte el
    micro en dos caracteres, y con la unidad irreconocible veintitrés canales
    EEG quedaron sin convertir y mal clasificados. Es lo que
    `readers/brainvision.py::_decodificar_cabecera` arregla, y sin esto nada lo
    comprueba fuera de una máquina que tenga los registros.

    Es función y no sólo fixture porque la duración importa: los tests del
    lector alcanzan con tres segundos, y `test_entrega.py` necesita varias
    ventanas de 30 s para poder scorear y exportar.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    # Los tres por omisión cubren una clase de señal cada uno, que es lo que
    # necesitan los tests del lector. **Se pueden pedir otros**: la ICA, por
    # ejemplo, necesita dos canales EEG y con uno solo se niega, con razón.
    canales = canales or [("C3", "µV"), ("EOG-izq", "µV"), ("EMG-menton", "µV")]
    muestras = int(FRECUENCIA_BV * segundos)
    tiempos = np.arange(muestras) / FRECUENCIA_BV
    # Frecuencias distintas y conocidas por canal: una escala aplicada de más se
    # ve en los tres a la vez, y una permutación de canales, en uno solo.
    # Una frecuencia y una amplitud distintas por canal, cíclicas si se piden
    # más de tres: lo que importa es que ninguno sea igual a otro, para que una
    # permutación de canales se vea.
    formas = [(10.0, 50.0), (1.0, 30.0), (30.0, 20.0), (5.0, 40.0), (0.5, 60.0)]
    microvoltios = np.vstack(
        [
            amplitud * np.sin(2 * np.pi * frecuencia * tiempos)
            for frecuencia, amplitud in (
                formas[posicion % len(formas)] for posicion in range(len(canales))
            )
        ]
    )
    cuentas = np.round(microvoltios / RESOLUCION_BV_UV).astype("<i2")
    # MULTIPLEXED es canal por canal dentro de cada instante, así que se
    # transpone antes de volcar los bytes.
    (carpeta / "sintetico.eeg").write_bytes(cuentas.T.tobytes(order="C"))

    cabecera = [
        "Brain Vision Data Exchange Header File Version 1.0",
        "",
        "[Common Infos]",
        "Codepage=UTF-8",
        "DataFile=sintetico.eeg",
        "MarkerFile=sintetico.vmrk",
        "DataFormat=BINARY",
        "DataOrientation=MULTIPLEXED",
        f"NumberOfChannels={len(canales)}",
        f"SamplingInterval={int(1_000_000 / FRECUENCIA_BV)}",
        "",
        "[Binary Infos]",
        "BinaryFormat=INT_16",
        "",
        "[Channel Infos]",
    ]
    for numero, (nombre, unidad) in enumerate(canales, start=1):
        cabecera.append(f"Ch{numero}={nombre},,{RESOLUCION_BV_UV},{unidad}")
    # **La tabla de impedancias vive en `[Comment]`**, que es donde el formato
    # la pone y donde MNE la busca. `None` se escribe `???`, que es como el
    # `.vhdr` marca un electrodo que nadie midió: es el caso que separa "sin
    # medir" de "0 kΩ", y sin poder escribirlo no se podría testear.
    if impedancias:
        cabecera += ["", "[Comment]", "", "Impedance [kOhm] at 23:00:00 :"]
        for nombre, valor in impedancias.items():
            escrito = "???" if valor is None else f"{valor:g}"
            cabecera.append(f"{nombre}:{escrito:>12s}")

    vhdr = carpeta / "sintetico.vhdr"
    vhdr.write_text("\n".join(cabecera) + "\n", encoding="utf-8")

    marcadores = [
        "Brain Vision Data Exchange Marker File, Version 1.0",
        "",
        "[Common Infos]",
        "Codepage=UTF-8",
        "DataFile=sintetico.eeg",
        "",
        "[Marker Infos]",
        "Mk1=New Segment,,1,1,0,20260907130000000000",
    ]
    (carpeta / "sintetico.vmrk").write_text(
        "\n".join(marcadores) + "\n", encoding="utf-8"
    )
    return vhdr


@pytest.fixture
def brainvision_sintetico(tmp_path) -> pathlib.Path:
    """Tres segundos de BrainVision sintético: alcanza para el lector."""
    return escribir_brainvision(tmp_path / "brainvision", segundos=3)


#: Clase de cada canal de `channel_names`, en su mismo orden. Está acá y no en
#: cada test porque `registro_sintetico` la necesita y hasta el hito 10 cada
#: archivo se la escribía sola: diez de ellos arman un `Recording` a mano.
CLASES_SINTETICAS: tuple[ChannelKind, ...] = (
    ChannelKind.EEG,
    ChannelKind.EEG,
    ChannelKind.EOG,
    ChannelKind.EMG,
)


@pytest.fixture
def registro_sintetico(
    synthetic_signal: np.ndarray, channel_names: list[str], sampling_rate: float
) -> Recording:
    """Los diez minutos sintéticos, ya envueltos en un `Recording`.

    **Faltaba, y la Parte 2 la necesita entera.** `synthetic_signal` es un array
    pelado y **todas** las funciones de `psglab/analysis/` reciben un
    `Recording`, así que sin esto cada test de análisis se lo armaría solo —que
    es lo que vienen haciendo diez archivos de la Parte 1.

    Trae contenido espectral conocido de antemano, que es lo que hace
    verificable un test de análisis sin usar un registro real: C3 en 1 Hz, C4 en
    10 Hz, el EOG en 0,5 Hz y el EMG en 30 Hz, todos de 50 µV. Una PSD de C4
    tiene que dar su pico en 10 Hz, y eso se puede afirmar.

    Son `VENTANAS_SINTETICAS` ventanas **exactas**: no ejercita la última
    ventana incompleta, que es un caso aparte y hay que escribirlo a propósito.
    """
    canales = [
        Channel(name=nombre, kind=clase, unit=MICROVOLT, index=posicion)
        for posicion, (nombre, clase) in enumerate(zip(channel_names, CLASES_SINTETICAS))
    ]
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=canales,
        data=synthetic_signal,
        sampling_rate=sampling_rate,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )
