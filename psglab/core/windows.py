"""Conversión entre ventanas de scoring, muestras y tiempo.

Todo el programa habla en varias unidades a la vez: el usuario piensa en
ventanas de 30 segundos, el archivo guarda muestras ("puntos"), las
herramientas reciben segundos desde el inicio de la ventana, el medidor de
ocupación trabaja en fracción de ventana y el histograma muestra la hora de la
noche.

**Este módulo es el único lugar donde se convierte entre unidades.** El
reparto con `psglab/ui/signal_view.py` es exacto y conviene tenerlo claro:

    unidad ←→ unidad     acá
    píxel  ←→ unidad     en `signal_view.py`, que es lo único que conoce el
                         ancho en píxeles del visualizador

Una herramienta que reciba segundos y necesite muestras o fracción de ventana
llama acá; no escribe la cuenta. Es lo que evita que aparezcan `* 30 * fs`
repartidos por el código.

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
Con un índice negativo devuelven números negativos en silencio.

**Con una frecuencia que no sea positiva, todas elevan `ZeroDivisionError`.**
Esa promesa era cierta a medias: `sample_to_window` y `count_windows` fallaban,
pero `window_to_samples` devolvía `(0, 0)` y `window_duration` devolvía cero, en
silencio. Una frecuencia corrupta leída de un EDF producía una ventana vacía en
vez de un error, que es la peor forma de fallar. Ahora las cuatro pasan por
`_samples_per_window()`, que es el único lugar donde se divide.

Cubre del pliego: sostiene V1_P de "Visualización" (número de ventana actual
y total), V1_F de "Navegación" y V2_F del histograma.
"""

import math
from datetime import datetime, timedelta

from psglab.config import WINDOW_SECONDS


def _samples_per_window(sampling_rate: float, window_seconds: float) -> float:
    """Muestras que entran en una ventana, con la frecuencia ya comprobada.

    Es el único punto del módulo donde se mira `sampling_rate`, y por eso el
    único lugar donde hace falta comprobarla. No es validación de argumentos en
    el sentido general —los índices siguen sin validarse a propósito— sino lo
    que hace cierta, para las cuatro funciones, la promesa del docstring del
    módulo.

    Raises:
        ZeroDivisionError: si la frecuencia no es positiva. Una frecuencia cero
            o negativa no describe ninguna señal, y devolver una ventana vacía
            en silencio esconde un archivo corrupto hasta mucho después.
    """
    if sampling_rate <= 0:
        raise ZeroDivisionError(
            f"la frecuencia de muestreo tiene que ser positiva, y es {sampling_rate}"
        )
    return window_seconds * sampling_rate


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
    # Antes del atajo de abajo: un registro vacío con una frecuencia corrupta
    # sigue siendo un archivo corrupto, y devolver 0 ventanas lo escondería.
    _samples_per_window(sampling_rate, window_seconds)
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
    samples_per_window = _samples_per_window(sampling_rate, window_seconds)
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
    samples_per_window = _samples_per_window(sampling_rate, window_seconds)
    index = math.floor(sample / samples_per_window)
    # Los bordes de `window_to_samples` están redondeados hacia abajo, así que
    # el borde real y el borde entero no coinciden cuando las muestras por
    # ventana no son enteras. La corrección devuelve la ventana a la que la
    # muestra pertenece de verdad, para que la ida y vuelta sea exacta.
    if math.floor((index + 1) * samples_per_window) <= sample:
        index += 1
    return index


def seconds_to_window_fraction(
    seconds: float,
    window_seconds: float = WINDOW_SECONDS,
) -> float:
    """De segundos desde el inicio de la ventana a fracción de ventana (0 a 1).

    La necesita el medidor de ocupación: `ViewerTool` le entrega segundos y
    `OccupancyLine` trabaja en fracción. Sin esta función la herramienta tendría
    que dividir por 30 a mano, y su propio docstring advierte lo que pasa si se
    saltea la conversión: informa 3000 % de ocupación.
    """
    return seconds / window_seconds


def window_fraction_to_seconds(
    fraction: float,
    window_seconds: float = WINDOW_SECONDS,
) -> float:
    """La inversa de `seconds_to_window_fraction`."""
    return fraction * window_seconds


def seconds_to_sample(
    window_index: int,
    offset_seconds: float,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> int:
    """De un punto dentro de una ventana a su muestra en el registro entero.

    La necesita el anotador: recibe el evento en segundos desde el inicio de la
    ventana y `Anotaciones.txt` guarda muestras.

    El desplazamiento se suma sobre el borde que devuelve `window_to_samples`,
    no sobre `window_index * 30 * fs`, para que la muestra caiga en la misma
    ventana de la que se dice que salió incluso con una frecuencia no redonda.
    """
    start, _ = window_to_samples(window_index, sampling_rate, window_seconds)
    return start + math.floor(offset_seconds * sampling_rate)


def sample_to_seconds(
    window_index: int,
    sample: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> float:
    """La inversa de `seconds_to_sample`: dónde cae una muestra dentro de su ventana.

    Devuelve segundos desde el inicio de la ventana. Es lo que necesita el
    visualizador para dibujar una anotación guardada, que viene en muestras,
    sobre la ventana que está mostrando.
    """
    # `window_to_samples` ya comprobó que la frecuencia sea positiva, así que
    # la división de abajo es segura.
    start, _ = window_to_samples(window_index, sampling_rate, window_seconds)
    return (sample - start) / sampling_rate


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
    # La comprobación de la frecuencia la hace `window_to_samples`, que la
    # necesita igual: repetirla acá sería calcular un valor para no usarlo.
    start, stop = window_to_samples(window_index, sampling_rate, window_seconds)
    # La ventana no puede pasarse del final del registro. Una ventana que
    # arranca más allá del final dura cero: no existe, pero preguntar por ella
    # no debería romper el programa.
    last_sample = min(stop, n_samples)
    if last_sample <= start:
        return timedelta(0)
    return timedelta(seconds=(last_sample - start) / sampling_rate)
