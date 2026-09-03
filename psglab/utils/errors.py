"""Excepciones propias del programa.

Todas heredan de `PsgLabError`, así que la interfaz puede capturar esa sola
clase y mostrar un cartel legible en vez de dejar caer una traza de Python.

Los mensajes van en español y dirigidos al usuario, no al programador: el
pliego dice que los usuarios son investigadores con o sin experiencia en
informática, y un `KeyError: 'C3'` no le sirve a nadie. La causa técnica se
guarda aparte, en `details`, para el diagnóstico.
"""


class PsgLabError(Exception):
    """Error base del programa.

    Attributes:
        message: texto que se le muestra al usuario, en español.
        details: información técnica para el diagnóstico. No se muestra en el
            cartel principal, pero se registra y se puede desplegar.
    """

    def __init__(self, message: str, details: str | None = None) -> None:
        # Implementado y no pendiente: es la base de todas las excepciones del
        # programa. Si el constructor fallara, ninguna de las clases de abajo
        # podría siquiera construirse para ser elevada.
        super().__init__(message)
        self.message = message
        self.details = details


# -- Importación de archivos -----------------------------------------------


class UnsupportedFormatError(PsgLabError):
    """El archivo no corresponde a ningún formato conocido."""


class UnreadableFileError(PsgLabError):
    """El archivo existe pero no se puede leer: está corrupto o incompleto."""


class MixedSamplingRateError(PsgLabError):
    """Los canales tienen frecuencias de muestreo distintas e incompatibles."""


class ScoringMismatchError(PsgLabError):
    """El archivo de scoring no corresponde al registro abierto."""


# -- Canales ----------------------------------------------------------------


class ChannelNotFoundError(PsgLabError):
    """Se pidió un canal que el registro no tiene."""


class DuplicateChannelError(PsgLabError):
    """Ya existe un canal con ese nombre."""


class UnknownUnitError(PsgLabError):
    """La unidad declarada en el archivo no se reconoce."""


# -- Scoring y anotaciones --------------------------------------------------


class WindowOutOfRangeError(PsgLabError):
    """Se pidió una ventana que está fuera del registro."""


class InvalidStageError(PsgLabError):
    """La fase no pertenece a la nomenclatura activa."""


class UnknownAnnotationLabelError(PsgLabError):
    """Se usó una clase de anotación que no está registrada."""


# -- Herramientas -----------------------------------------------------------


class DuplicateToolError(PsgLabError):
    """Se registraron dos herramientas con el mismo nombre."""


class UnknownToolError(PsgLabError):
    """Se pidió una herramienta que no está registrada."""


# -- Análisis ---------------------------------------------------------------


class InvalidFilterError(PsgLabError):
    """Los parámetros del filtro no son aplicables a este registro."""
