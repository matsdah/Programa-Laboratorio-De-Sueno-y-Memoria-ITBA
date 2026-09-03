"""Fixtures compartidas por todos los tests.

Los tests usan **registros sintéticos generados en el momento**, nunca
registros reales de participantes: no se suben datos de personas al
repositorio.

Un registro sintético además es mejor para testear, porque se conoce de
antemano el resultado correcto. Si se genera una onda de 10 Hz, la PSD tiene
que dar un pico en 10 Hz, y eso se puede afirmar en un test.
"""

import numpy as np
import pytest


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

    Diez minutos son exactamente 20 ventanas de 30 segundos, un número
    cómodo para verificar los cálculos a mano.
    """
    duration_seconds = 600
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
