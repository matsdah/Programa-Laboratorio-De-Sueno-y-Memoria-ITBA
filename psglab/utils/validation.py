"""Comprobaciones numéricas que se repiten en todo el modelo.

Existe por un descuido que ya apareció **cuatro veces** en módulos distintos:
escribir una guarda como `if valor < 0` o `if valor < 1` y dar por sentado que
rechaza cualquier número inválido. No lo hace, porque **toda comparación con NaN
es falsa**:

    >>> float("nan") < 1
    False

Así que un NaN atraviesa la guarda y sigue viaje. Y lo que hace después es
peor que fallar: no rompe nada de forma visible. Una anotación con duración NaN
se cuenta en el informe y no se dibuja en ninguna ventana; una escala NaN deja
el canal en blanco y la escala de la izquierda anunciando "nan µV".

`core/windows.py` y `core/recording.py` lo arreglaron cada uno por su cuenta, y
`core/annotations.py` y `core/session.py` quedaron sin arreglar. Este módulo
existe para que la próxima guarda no vuelva a nacer con el mismo agujero.

Cubre del pliego: ningún ID. Es infraestructura del modelo.
"""

import math

from psglab.utils.errors import PsgLabError


def check_finite(
    value: float,
    *,
    error: type[PsgLabError],
    message: str,
    details: str,
    minimum: float | None = None,
) -> None:
    """Rechaza lo que no sea un número finito, y opcionalmente lo que no llegue
    a un mínimo.

    Args:
        value: el número a comprobar. Un `bool` es un `int` para Python y pasa;
            no se rechaza porque ningún llamador lo recibe de un archivo.
        error: qué excepción elevar. La elige quien llama, porque el error que
            le sirve al investigador depende de qué se estaba haciendo: un
            registro incoherente y una anotación mal formada no se explican
            igual.
        message: texto en español para el usuario.
        details: causa técnica, que se completa con el valor recibido.
        minimum: si se da, `value` tiene que ser mayor o igual.

    Raises:
        El `error` que se le pasó, si `value` no es un número, no es finito, o
        queda por debajo de `minimum`.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise error(message, details=f"{details} Se recibió {type(value).__name__}.")
    if not math.isfinite(value):
        raise error(message, details=f"{details} Se recibió {value}.")
    if minimum is not None and value < minimum:
        raise error(message, details=f"{details} Se recibió {value}.")


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Recorta un número finito al rango permitido.

    `min(max(nan, lo), hi)` devuelve **NaN**, así que la forma corta no sirve
    para recortar de verdad: el NaN sale intacto por el otro lado. Acá se lo
    rechaza antes.

    Raises:
        ValueError: si `value` no es finito. Es un error de programación, no
            algo que el usuario pueda provocar: quien llama tiene que haber
            validado antes con `check_finite`.
    """
    if not math.isfinite(value):
        raise ValueError(f"no se puede recortar un valor que no es finito: {value}")
    return min(max(value, minimum), maximum)
