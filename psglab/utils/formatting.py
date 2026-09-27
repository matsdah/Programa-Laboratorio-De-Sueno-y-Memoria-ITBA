"""Cómo se escribe un número para el investigador, y cómo se lee el que escribe.

**Todo número que ve el usuario sale de acá** (hito 79). Con coma decimal,
que es la convención del idioma del programa: «0,5 Hz» y no «0.5 Hz».

Hasta el hito 79 cada módulo lo resolvía por su cuenta, con un
`.replace(".", ",")` al final de un f-string: estaba escrito veinticinco veces,
con tres `_numero()`, dos `_texto()` y dos `_kohm()`. Y como nadie lo exigía,
**unos veinte mensajes lo olvidaban**: «El pasa-altos de 0.3 Hz no se puede
aplicar…», «La banda de 0.5 a 4 Hz…», la frecuencia de muestreo en la barra de
estado. `tests/test_consistencia.py` rechaza ahora un formato de número en un
f-string fuera de este módulo.

**Lo que no pasa por acá, a propósito:**

- `details` de un error: es la causa técnica para quien programa, y ahí un
  punto decimal es lo esperable.
- Los formatos de máquina, como el XML de scoring
  (`exporters/scoring_formats.py`), que otro programa tiene que leer con punto.

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura: la usan
todas las capas que le escriben al usuario.
"""

import math
from numbers import Real

from psglab.utils.errors import InvalidNumberError

#: Lo que se escribe en lugar de un número que no existe: un NaN o un infinito.
#: «nan Hz» no le dice nada a un investigador, y un cartel de error por algo que
#: sólo se iba a mostrar sería peor.
SIN_VALOR = "—"


def _exigir_numero(value: object, que: str) -> float:
    """El valor como `float`, o un `InvalidNumberError` que dice qué se iba a escribir.

    Un booleano no pasa, aunque Python lo cuente como entero: `True` escrito
    como «1» es un error del programa, no un número.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise InvalidNumberError(
            "No se pudo escribir un número que se iba a mostrar.",
            details=f"{que} = {value!r} ({type(value).__name__}); se esperaba un número.",
        )
    return float(value)


def _exigir_cifras(valor: object, que: str, minimo: int) -> None:
    """Rechaza una cantidad de decimales o de cifras que no se puede pedir."""
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < minimo:
        raise InvalidNumberError(
            "No se pudo escribir un número que se iba a mostrar.",
            details=f"{que} = {valor!r}; se esperaba un entero de {minimo} o más.",
        )


def number(
    value: float, decimals: int | None = None, *, significant: int | None = None
) -> str:
    """Un número con coma decimal: 0,5 · 30 · 12,35.

    Args:
        value: el número.
        decimals: cuántos decimales, fijos: `number(2, 1)` es «2,0». Sin
            decimales ni cifras, se escribe sin ceros de más —«30», «0,5»—,
            que es `f"{value:g}"`: la forma que usaban casi todos los módulos.
        significant: cuántas cifras significativas, en vez de decimales. Es
            para magnitudes de cualquier orden, como una potencia espectral.
            No se puede pedir con `decimals`.

    Un NaN o un infinito se escriben `SIN_VALOR`.

    Raises:
        InvalidNumberError: si `value` no es un número, o si las cifras
            pedidas no son un entero válido.
    """
    numero = _exigir_numero(value, "value")
    if decimals is not None and significant is not None:
        raise InvalidNumberError(
            "No se pudo escribir un número que se iba a mostrar.",
            details="Se pidieron decimales y cifras significativas a la vez.",
        )
    if decimals is not None:
        _exigir_cifras(decimals, "decimals", 0)
        formato = f".{decimals}f"
    elif significant is not None:
        _exigir_cifras(significant, "significant", 1)
        formato = f".{significant}g"
    else:
        formato = "g"
    if not math.isfinite(numero):
        return SIN_VALOR
    return format(numero, formato).replace(".", ",")


def quantity(
    value: float,
    unit: str,
    decimals: int | None = None,
    *,
    significant: int | None = None,
) -> str:
    """Un número con su unidad, separados por un espacio: «0,5 Hz», «75 µV».

    Las cifras se piden como en `number()`.

    Raises:
        InvalidNumberError: si `value` no es un número, si las cifras no son
            válidas o si `unit` no es texto.
    """
    if not isinstance(unit, str):
        raise InvalidNumberError(
            "No se pudo escribir un número que se iba a mostrar.",
            details=f"unit = {unit!r} ({type(unit).__name__}); se esperaba texto.",
        )
    return f"{number(value, decimals, significant=significant)} {unit}".strip()


def duration(seconds: float) -> str:
    """Una duración como la leería un investigador: 200 ms, 30 s, 5 min, 1 h.

    **Es el único formateador de duraciones de la interfaz.** Hubo dos —uno
    para el menú y otro en la ventana principal para la barra de estado— y no
    coincidían: la misma página de 0,2 s era "0,2 s por página" en el menú y
    "Página: 200 ms" abajo. Vivía en `ui/menus.py` hasta el hito 79; bajó acá
    para que cualquier capa lo pueda usar.

    No es el de `Informacion.txt` (`exporters/information_txt.format_duration`),
    que escribe horas, minutos y segundos con centésimas porque es un informe
    que se compara columna contra columna.

    Raises:
        InvalidNumberError: si no es un número.
    """
    segundos = _exigir_numero(seconds, "seconds")
    if not math.isfinite(segundos):
        return SIN_VALOR
    if segundos < 1.0:
        return quantity(segundos * 1000, "ms")
    if segundos < 60.0:
        return quantity(segundos, "s")
    if segundos < 3600.0:
        return quantity(segundos / 60, "min")
    return quantity(segundos / 3600, "h")


def parse_number(text: str) -> float | None:
    """Lee un número como lo escribe un investigador: con coma o con punto.

    Returns:
        El número, o `None` si el texto está vacío, no se entiende o no es un
        número finito. **«nan» e «inf» no son números para esto**: `float()`
        los acepta, y un corte de filtro de «inf» Hz se leería como uno de
        verdad.

    Raises:
        InvalidNumberError: si no se le pasa texto.
    """
    if not isinstance(text, str):
        raise InvalidNumberError(
            "No se pudo leer un número.",
            details=f"text = {text!r} ({type(text).__name__}); se esperaba texto.",
        )
    limpio = text.strip().replace(",", ".")
    if not limpio:
        return None
    try:
        numero = float(limpio)
    except ValueError:
        return None
    return numero if math.isfinite(numero) else None
