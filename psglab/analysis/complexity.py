"""Medidas de complejidad de la señal.

Cuantifican qué tan irregular o impredecible es la señal. En sueño se usan
porque bajan de forma sistemática al profundizarse el sueño y al perderse la
conciencia, y captan cosas que el análisis espectral no ve.

Se ofrecen varias medidas porque no hay una sola definición de "complejidad" y
cada una responde una pregunta distinta.

Las funciones que reciben `window_index` tienen que traducirlo a muestras con
`psglab.core.windows.window_to_samples()`, que es el único lugar del programa
donde se hace esa conversión. No escribir la cuenta `* 30 * fs` acá: si la
ventana deja de ser de 30 s, este módulo quedaría desincronizado en silencio.

Cubre del pliego: sección "Complejidad".
"""

import numpy as np

from psglab.core.recording import Recording


def sample_entropy(signal: np.ndarray, m: int = 2, r: float | None = None) -> float:
    """Entropía de muestra: probabilidad de que patrones parecidos sigan parecidos.

    Args:
        m: longitud de los patrones comparados.
        r: tolerancia. Si es None, se usa 0,2 veces el desvío estándar de la
            señal, que es la convención habitual.
    """
    raise NotImplementedError("Pendiente: calcular la entropía de muestra.")


def permutation_entropy(signal: np.ndarray, order: int = 3) -> float:
    """Entropía de permutación: complejidad según el orden relativo de las muestras.

    Es rápida y robusta al ruido, lo que la hace práctica para recorrer una
    noche entera ventana por ventana.
    """
    raise NotImplementedError("Pendiente: calcular la entropía de permutación.")


def lempel_ziv_complexity(signal: np.ndarray) -> float:
    """Complejidad de Lempel-Ziv sobre la señal binarizada.

    Cuenta patrones distintos en la señal. Es la medida más usada en los
    trabajos sobre niveles de conciencia.
    """
    raise NotImplementedError("Pendiente: binarizar la señal y contar los patrones.")


def higuchi_fractal_dimension(signal: np.ndarray, k_max: int = 10) -> float:
    """Dimensión fractal de Higuchi: complejidad geométrica de la curva."""
    raise NotImplementedError("Pendiente: calcular la dimensión fractal.")


def complexity_by_window(
    recording: Recording,
    channels: list[str],
    measure: str = "permutation_entropy",
) -> dict[str, np.ndarray]:
    """Aplica una medida de complejidad a cada ventana de 30 segundos.

    Returns:
        Diccionario canal -> array con un valor por ventana, para poder
        cruzarlo con el hipnograma.
    """
    raise NotImplementedError("Pendiente: recorrer las ventanas aplicando la medida elegida.")
