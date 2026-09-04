"""Conversión entre ventanas de scoring, muestras y tiempo.

Todo el programa habla en tres unidades distintas: el usuario piensa en
ventanas de 30 segundos, el archivo guarda muestras ("puntos") y el
histograma muestra la hora de la noche. Este módulo es el único lugar donde
se hacen esas conversiones, para que no aparezcan cuentas de `* 30 * fs`
repartidas por todo el código.

**Los bordes se calculan siempre desde el índice de la ventana, nunca
acumulando un paso fijo.** La diferencia sólo aparece cuando la cantidad de
muestras por ventana no es entera, que pasa en EDF cuando la frecuencia
efectiva no es redonda: con 256,125 Hz, `30 * fs` da 7683,75. Acumular
`int(30 * fs)` ventana a ventana desplaza la número 960 casi tres segundos
respecto de su lugar real. No rompe nada de forma visible: corre el scoring de
toda la segunda mitad de la noche.

**Precondiciones.** Las funciones de este módulo son aritmética pura y no
validan sus argumentos: esperan `sampling_rate` mayor que cero e índices de
ventana y muestra no negativos. Quien llama ya validó —`Session.go_to_window()`
eleva `WindowOutOfRangeError` antes de llegar acá— y repetir la comprobación en
el camino caliente, que se recorre en cada pulsación de flecha, no aporta nada.
Con un índice negativo devuelven números negativos en silencio; con frecuencia
cero, elevan `ZeroDivisionError`.

Cubre del pliego: sostiene V1_P de "Visualización" (número de ventana actual
y total), V1_F de "Navegación" y V2_F del histograma.
"""

import math
from datetime import datetime, timedelta

from psglab.config import WINDOW_SECONDS


def count_windows(
    n_samples: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> int:
    """Cantidad total de ventanas del registro (el VENMAX del pliego).

    Si el registro no termina en un múltiplo exacto de 30 segundos, la última
    ventana queda incompleta. Se la cuenta igual, porque el usuario tiene que
    poder scorearla o ver que está incompleta.
    """
    if n_samples <= 0:
        return 0
    # Se define en función de `sample_to_window` en vez de redondear hacia
    # arriba por separado: así las dos funciones no pueden discrepar sobre
    # dónde termina la última ventana, que es de donde salen los errores de
    # una unidad.
    return sample_to_window(n_samples - 1, sampling_rate, window_seconds) + 1


def window_to_samples(
    window_index: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> tuple[int, int]:
    """Rango de muestras que abarca una ventana.

    Args:
        window_index: índice de la ventana, empezando en 0. Ojo: la interfaz y
            los archivos de salida numeran desde 1; la conversión se hace al
            mostrar, no acá.

    Returns:
        Tupla (primera muestra incluida, primera muestra excluida).
    """
    samples_per_window = window_seconds * sampling_rate
    # Cada borde se calcula desde su propio índice. Ver la nota del docstring
    # del módulo: multiplicar un paso ya redondeado acumula la deriva.
    start = math.floor(window_index * samples_per_window)
    stop = math.floor((window_index + 1) * samples_per_window)
    return start, stop


def sample_to_window(
    sample: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> int:
    """Ventana (base 0) a la que pertenece una muestra.

    Lo usa el anotador para saber en qué ventana cae un evento, y el
    histograma para saltar a la ventana del punto donde se hizo clic (V4_F).
    """
    samples_per_window = window_seconds * sampling_rate
    index = math.floor(sample / samples_per_window)
    # Los bordes de `window_to_samples` están redondeados hacia abajo, así que
    # el borde real y el borde entero no coinciden cuando las muestras por
    # ventana no son enteras. La corrección devuelve la ventana a la que la
    # muestra pertenece de verdad, para que la ida y vuelta sea exacta.
    if math.floor((index + 1) * samples_per_window) <= sample:
        index += 1
    return index


def window_to_clock_time(
    window_index: int,
    start_time: datetime | None,
    window_seconds: float = WINDOW_SECONDS,
) -> datetime | None:
    """Horario real de inicio de una ventana.

    El histograma lo usa para poner el eje horizontal en hora de la noche
    (V2_F). Devuelve None si el archivo no informó el horario de inicio, y en
    ese caso el eje se numera de 1 a VENMAX.
    """
    if start_time is None:
        return None
    return start_time + timedelta(seconds=window_index * window_seconds)


def window_duration(
    window_index: int,
    n_samples: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> timedelta:
    """Duración real de una ventana.

    Es `window_seconds` salvo en la última ventana del registro, que puede
    estar incompleta.
    """
    start, stop = window_to_samples(window_index, sampling_rate, window_seconds)
    # La ventana no puede pasarse del final del registro. Una ventana que
    # arranca más allá del final dura cero: no existe, pero preguntar por ella
    # no debería romper el programa.
    last_sample = min(stop, n_samples)
    if last_sample <= start:
        return timedelta(0)
    return timedelta(seconds=(last_sample - start) / sampling_rate)
