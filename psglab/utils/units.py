"""Unidades de amplitud y conversiones.

**El programa trabaja internamente en microvoltios (µV).** Toda señal se
convierte a µV al importarla y ninguna otra capa vuelve a preguntarse por la
unidad.

Una aclaración sobre el pliego: el documento escribe "mV" pero el ejemplo dice
"75mv", y el criterio de 75 sobre EEG es el clásico de amplitud de ondas
lentas en **microvoltios**. En milivoltios sería mil veces la amplitud
fisiológica real del EEG. Confirmado con el cliente: la unidad es µV.

Los archivos declaran su unidad de formas variadas ("uV", "µV", "microvolt",
"V", "mV"), así que la normalización tiene que ser explícita y tolerante.

Cubre del pliego: V1_P de "Visualización de la señal", en su parte de escala en
µV, y V1_F de "Herramienta de amplitud", en su parte de banda de 75 µV. Los dos
requisitos hablan de una amplitud concreta, y es acá donde la señal queda
expresada en microvoltios: sin este módulo, ninguno de los dos números
significaría nada.
"""

from typing import Final

from psglab.utils.errors import UnknownUnitError

#: Los dos caracteres que se ven como "mu" y que aparecen en las cabeceras.
#: `normalize_unit_name()` reemplaza el primero por el segundo.
#:
#: En pantalla son indistinguibles, así que leer el código no alcanza para saber
#: cuál es cuál: si alguien los intercambiara sin querer, la normalización
#: dejaría de funcionar y nada se vería raro. Por eso `tests/test_units.py`
#: afirma sus puntos de código (U+03BC y U+00B5) en vez de confiar en la vista.
_MU_GRIEGA: Final[str] = "μ"
_SIGNO_MICRO: Final[str] = "µ"

#: Símbolo de la unidad que se muestra en la interfaz.
MICROVOLT: Final[str] = "µV"

#: Factores de conversión a microvoltios, por unidad declarada en el archivo.
#: Las claves se comparan **después de pasar por `normalize_unit_name()`**, que
#: baja a minúscula, saca espacios y unifica los dos caracteres "mu" en uno.
#:
#: Ese último punto no es cosmético: existen dos caracteres distintos que se ven
#: igual, el signo micro (U+00B5) y la letra griega mu (U+03BC), y las cabeceras
#: de EDF y BrainVision usan los dos. Comparar sin unificarlos hace que la mitad
#: de los archivos parezcan traer una unidad desconocida.
TO_MICROVOLTS: Final[dict[str, float]] = {
    "v": 1e6,
    "volt": 1e6,
    "volts": 1e6,
    "mv": 1e3,
    "millivolt": 1e3,
    "millivolts": 1e3,
    "uv": 1.0,
    "µv": 1.0,
    "microvolt": 1.0,
    "microvolts": 1.0,
}


def to_microvolts(value: float, unit: str) -> float:
    """Convierte un valor a microvoltios.

    Raises:
        UnknownUnitError: si la unidad no se reconoce. Se prefiere fallar a
            asumir un factor: escalar mal la señal produce un scoring incorrecto
            que nadie va a notar mirando la pantalla.
    """
    return value * conversion_factor(unit)


def conversion_factor(unit: str) -> float:
    """Factor por el que hay que multiplicar para pasar de `unit` a µV.

    Es el único lugar que consulta `TO_MICROVOLTS`: `to_microvolts()` delega
    acá para que no haya dos caminos que puedan discrepar.

    Raises:
        UnknownUnitError: si la unidad no está en la tabla.
    """
    normalizada = normalize_unit_name(unit)
    if normalizada not in TO_MICROVOLTS:
        raise UnknownUnitError(
            f"No se reconoce la unidad '{unit}' del archivo, así que no se puede "
            "convertir la señal a microvoltios.",
            details=(
                f"Unidad normalizada: '{normalizada}'. "
                f"Unidades conocidas: {', '.join(sorted(TO_MICROVOLTS))}."
            ),
        )
    return TO_MICROVOLTS[normalizada]


def format_amplitude(value_uv: float, decimals: int = 0) -> str:
    """Formatea una amplitud para mostrarla en la escala del visualizador.

    Ejemplo: 75.0 -> "75 µV".

    La unidad sale de `MICROVOLT` y no de un literal: es el símbolo que ve el
    usuario y tiene que salir de un solo lugar.
    """
    return f"{value_uv:.{decimals}f} {MICROVOLT}"


def normalize_unit_name(unit: str) -> str:
    """Normaliza el nombre de una unidad para poder compararlo.

    Pasa a minúscula, quita espacios y **unifica los dos caracteres "mu"**: la
    letra griega mu (U+03BC, `"\\u03bc"`) se reemplaza por el signo micro
    (U+00B5, `"\\u00b5"`), que es el que usa `TO_MICROVOLTS` y el que define
    `MICROVOLT`.

    Los dos se ven idénticos en pantalla y las cabeceras de EDF y BrainVision
    usan uno u otro según quién las haya escrito. Sin esta unificación, un
    archivo perfectamente válido elevaría `UnknownUnitError`, y el mensaje que
    vería el investigador diría que la unidad "µV" es desconocida mostrándole
    exactamente el texto que sí está en la tabla.

    **El orden de los tres pasos importa.** `lower()` va antes del reemplazo
    porque la mu griega mayúscula (U+039C) baja a U+03BC, y así el reemplazo
    también la alcanza; al revés, "ΜV" quedaría sin normalizar.
    """
    sin_espacios = "".join(unit.split())
    return sin_espacios.lower().replace(_MU_GRIEGA, _SIGNO_MICRO)
