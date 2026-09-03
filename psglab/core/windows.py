"""Conversión entre ventanas de scoring, muestras y tiempo.

Todo el programa habla en tres unidades distintas: el usuario piensa en
ventanas de 30 segundos, el archivo guarda muestras ("puntos") y el
histograma muestra la hora de la noche. Este módulo es el único lugar donde
se hacen esas conversiones, para que no aparezcan cuentas de `* 30 * fs`
repartidas por todo el código.

Cubre del pliego: sostiene V1_P de "Visualización" (número de ventana actual
y total), V1_F de "Navegación" y V2_F del histograma.
"""

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
    raise NotImplementedError("Pendiente: calcular la cantidad de ventanas.")


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
    raise NotImplementedError("Pendiente: convertir ventana a rango de muestras.")


def sample_to_window(
    sample: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> int:
    """Ventana (base 0) a la que pertenece una muestra.

    Lo usa el anotador para saber en qué ventana cae un evento, y el
    histograma para saltar a la ventana del punto donde se hizo clic (V4_F).
    """
    raise NotImplementedError("Pendiente: convertir muestra a índice de ventana.")


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
    raise NotImplementedError("Pendiente: sumar el desplazamiento al horario de inicio.")


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
    raise NotImplementedError("Pendiente: calcular la duración real de la ventana.")
