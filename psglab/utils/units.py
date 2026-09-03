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
"""

from typing import Final

#: Símbolo de la unidad que se muestra en la interfaz.
MICROVOLT: Final[str] = "µV"

#: Factores de conversión a microvoltios, por unidad declarada en el archivo.
#: Las claves se comparan en minúscula y sin espacios.
TO_MICROVOLTS: Final[dict[str, float]] = {
    "v": 1e6,
    "mv": 1e3,
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
    raise NotImplementedError("Pendiente: aplicar el factor de conversión.")


def conversion_factor(unit: str) -> float:
    """Factor por el que hay que multiplicar para pasar de `unit` a µV."""
    raise NotImplementedError("Pendiente: buscar el factor en la tabla.")


def format_amplitude(value_uv: float, decimals: int = 0) -> str:
    """Formatea una amplitud para mostrarla en la escala del visualizador.

    Ejemplo: 75.0 -> "75 µV".
    """
    raise NotImplementedError("Pendiente: formatear el valor con su unidad.")


def normalize_unit_name(unit: str) -> str:
    """Normaliza el nombre de una unidad para poder compararlo.

    Pasa a minúscula, quita espacios y unifica las variantes de "micro".
    """
    raise NotImplementedError("Pendiente: normalizar el nombre de la unidad.")
