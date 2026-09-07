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
