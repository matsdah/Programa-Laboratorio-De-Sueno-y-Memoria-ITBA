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

import numpy as np
import pytest

from psglab.config import WINDOW_SECONDS

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


@pytest.fixture
def brainvision_sintetico(tmp_path):
    """Un BrainVision de verdad, escrito acá mismo, sin datos de nadie.

    **Por qué existe.** Los quince tests que leen el registro de `data/` son los
    únicos que ejercitan el lector de punta a punta, y se saltean en el CI
    porque `data/` está en el `.gitignore`: son registros de participantes. El
    resultado es que el lector de BrainVision no se ejecuta en ninguna de las
    seis combinaciones de sistema y versión de Python que corre el CI.

    El formato permite arreglarlo sin pedirle nada a nadie: son tres archivos y
    ninguno es opaco. El `.vhdr` y el `.vmrk` son texto tipo INI y el `.eeg` es
    un `int16` multiplexado crudo, así que se escriben con `numpy` y `pathlib`.

    **La cabecera declara `Codepage=UTF-8` y escribe la unidad en UTF-8 a
    propósito**, porque ahí estuvo un bug real: leerla como latin-1 parte el
    micro en dos caracteres, y con la unidad irreconocible veintitrés canales
    EEG quedaron sin convertir y mal clasificados. Es lo que
    `readers/brainvision.py::_decodificar_cabecera` arregla, y sin esta fixture
    nada lo comprueba fuera de una máquina que tenga los registros.

    Devuelve la ruta del `.vhdr`, que es el archivo que se abre.
    """
    carpeta = tmp_path / "brainvision"
    carpeta.mkdir()
    canales = [("C3", "µV"), ("EOG-izq", "µV"), ("EMG-menton", "µV")]
    muestras = int(FRECUENCIA_BV * 3)
    tiempos = np.arange(muestras) / FRECUENCIA_BV
    # Frecuencias distintas y conocidas por canal: una escala equivocada se ve
    # enseguida en el pico de amplitud de cada uno.
    microvoltios = np.vstack(
        [
            50.0 * np.sin(2 * np.pi * 10 * tiempos),
            30.0 * np.sin(2 * np.pi * 1 * tiempos),
            20.0 * np.sin(2 * np.pi * 30 * tiempos),
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
