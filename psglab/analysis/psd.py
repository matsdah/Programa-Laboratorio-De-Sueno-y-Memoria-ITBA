"""Densidad espectral de potencia (PSD).

Calcula cuánta potencia tiene la señal en cada banda de frecuencia. Es la
métrica más usada del análisis de sueño: la potencia delta cuantifica la
profundidad del sueño lento y la potencia sigma sigue a los husos.

El usuario elige las bandas. Las de abajo son las convencionales y sirven de
punto de partida, pero los límites varían entre laboratorios y entre trabajos
publicados, así que son editables.

Cubre del pliego: V1_F de "Power Spectral Density (PSD)".
"""

from typing import Final

import numpy as np

from psglab.core.recording import Recording

#: Bandas de frecuencia convencionales, en Hz.
DEFAULT_BANDS: Final[dict[str, tuple[float, float]]] = {
    "Delta": (0.5, 4.0),
    "Theta": (4.0, 8.0),
    "Alpha": (8.0, 12.0),
    "Sigma": (12.0, 16.0),
    "Beta": (16.0, 30.0),
    "Gamma": (30.0, 45.0),
}


def compute_psd(
    recording: Recording,
    channels: list[str] | None = None,
    window_index: int | None = None,
    method: str = "welch",
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula la PSD de uno o varios canales.

    Args:
        channels: canales a analizar. None significa todos.
        window_index: ventana de 30 s a analizar. None analiza el registro
            completo.
        method: "welch" o "multitaper".

    Returns:
        Tupla (frecuencias, potencias), con potencias de forma
        (n_canales, n_frecuencias).
    """
    raise NotImplementedError("Pendiente: calcular la PSD con el método pedido.")


def band_power(
    frequencies: np.ndarray,
    psd: np.ndarray,
    band: tuple[float, float],
    relative: bool = False,
) -> np.ndarray:
    """Potencia dentro de una banda de frecuencia.

    Args:
        relative: si es True, devuelve la fracción de la potencia total en vez
            del valor absoluto. La potencia relativa es la que permite
            comparar entre participantes: la absoluta depende del grosor del
            cráneo y de la impedancia, que varían de persona a persona.
    """
    raise NotImplementedError("Pendiente: integrar la PSD dentro de la banda.")


def band_powers_by_window(
    recording: Recording,
    channels: list[str],
    bands: dict[str, tuple[float, float]] | None = None,
) -> dict[str, dict[str, np.ndarray]]:
    """Potencia por banda para cada ventana de 30 segundos del registro.

    Es lo que permite ver la evolución del espectro a lo largo de la noche y
    cruzarla con el hipnograma.

    Returns:
        Diccionario canal -> banda -> array con un valor por ventana.
    """
    raise NotImplementedError("Pendiente: recorrer las ventanas y calcular la potencia por banda.")
