"""Conectividad entre canales.

Mide en qué grado la actividad de dos zonas del cerebro está relacionada. En
sueño interesa porque la conectividad cae en el sueño profundo y se
reorganiza en REM.

Sobre la elección del método, que no es un detalle técnico menor: la
coherencia común es sensible al volume conduction, es decir, dos electrodos
pueden parecer conectados simplemente porque están captando la misma fuente
eléctrica desde distintos lugares del cuero cabelludo. Los métodos basados en
la parte imaginaria (imaginary coherence, wPLI) son inmunes a ese artefacto y
son los recomendados por defecto.

Cubre del pliego: sección "Conectividad de la señal".
"""

from typing import Final

import numpy as np

from psglab.core.recording import Recording

#: Métodos disponibles, del más simple al más robusto frente a volume
#: conduction.
METHODS: Final[tuple[str, ...]] = (
    "coherence",
    "imaginary_coherence",
    "pli",
    "wpli",
    "plv",
)


def compute_connectivity(
    recording: Recording,
    channels: list[str] | None = None,
    band: tuple[float, float] = (0.5, 4.0),
    method: str = "wpli",
    window_index: int | None = None,
) -> np.ndarray:
    """Matriz de conectividad entre los canales pedidos.

    Args:
        band: banda de frecuencia en la que se mide.
        method: uno de `METHODS`.
        window_index: ventana de 30 s a analizar. None analiza todo el registro.

    Returns:
        Matriz cuadrada y simétrica de forma (n_canales, n_canales), con la
        diagonal en cero.
    """
    raise NotImplementedError("Pendiente: calcular la conectividad con mne-connectivity.")


def connectivity_by_window(
    recording: Recording,
    channels: list[str],
    band: tuple[float, float],
    method: str = "wpli",
) -> np.ndarray:
    """Conectividad ventana por ventana a lo largo del registro.

    Returns:
        Array de forma (n_ventanas, n_canales, n_canales).
    """
    raise NotImplementedError("Pendiente: recorrer las ventanas calculando la conectividad.")


def average_connectivity(matrix: np.ndarray) -> float:
    """Conectividad promedio de una matriz, ignorando la diagonal.

    Resume la matriz en un solo número para poder graficarlo contra el
    hipnograma.
    """
    raise NotImplementedError("Pendiente: promediar los valores fuera de la diagonal.")
