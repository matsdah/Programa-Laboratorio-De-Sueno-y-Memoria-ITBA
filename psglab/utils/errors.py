"""Excepciones propias del programa.

Todas heredan de `PsgLabError`, así que la interfaz puede capturar esa sola
clase y mostrar un cartel legible en vez de dejar caer una traza de Python.

Los mensajes van en español y dirigidos al usuario, no al programador: el
pliego dice que los usuarios son investigadores con o sin experiencia en
informática, y un `KeyError: 'C3'` no le sirve a nadie. La causa técnica se
guarda aparte, en `details`, para el diagnóstico.

Cubre del pliego: ningún ID de funcionalidad. Sostiene el requisito de que el
programa lo pueda usar un investigador sin experiencia informática (sección 3).
"""

from collections.abc import Iterator
from contextlib import contextmanager


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


class InvalidRecordingError(PsgLabError):
    """El registro que se armó es incoherente consigo mismo.

    No es lo mismo que `UnreadableFileError`, que habla del archivo: acá el
    archivo se leyó bien y lo que quedó mal es el `Recording` resultante —tantos
    canales declarados como filas no tiene la matriz, una frecuencia de muestreo
    que no es positiva, una matriz que no es de dos dimensiones—.

    Existe para que ese error salte **en el lector, que es donde está el bug**, y
    no tres capas más arriba con una traza de numpy que no dice de dónde vino.
    """


# -- Canales ----------------------------------------------------------------


class ChannelNotFoundError(PsgLabError):
    """Se pidió un canal que el registro no tiene."""


class DuplicateChannelError(PsgLabError):
    """Ya existe un canal con ese nombre."""


class UnknownUnitError(PsgLabError):
    """La unidad declarada en el archivo no se reconoce."""


class InvalidScaleError(PsgLabError):
    """La escala vertical pedida no es un número con el que se pueda dibujar.

    Los valores fuera de los topes de `config` **no** llegan acá: se recortan en
    silencio, que es lo que corresponde a alguien apretando una flecha. Esto es
    para lo que no se puede recortar —NaN, infinito, algo que no es un número—,
    que suele venir de un autoescalado calculado sobre una señal con huecos.
    """


# -- Scoring y anotaciones --------------------------------------------------


class WindowOutOfRangeError(PsgLabError):
    """Se pidió una ventana que está fuera del registro."""


class InvalidStageError(PsgLabError):
    """La fase no pertenece a la nomenclatura activa."""


class InvalidNomenclatureError(PsgLabError):
    """Se pidió una nomenclatura de scoring que no existe."""


class UnknownAnnotationLabelError(PsgLabError):
    """Se usó una clase de anotación que no está registrada."""


class InvalidAnnotationError(PsgLabError):
    """La anotación está mal formada y no se puede guardar.

    No es lo mismo que `UnknownAnnotationLabelError`, que habla de la **clase**
    del evento: acá la clase puede estar bien y lo que no cierra es el evento
    —una posición negativa, una duración que no cubre ninguna muestra, una
    etiqueta vacía—.

    Existe por el mismo motivo que `InvalidRecordingError`: que el error salte
    donde está el bug, que es el anotador armando la anotación, y no al
    exportar `Anotaciones.txt` con una línea que nadie puede interpretar.
    """


# -- Herramientas -----------------------------------------------------------


class DuplicateToolError(PsgLabError):
    """Se registraron dos herramientas con el mismo nombre."""


class UnknownToolError(PsgLabError):
    """Se pidió una herramienta que no está registrada."""


class RecordingTooLargeError(PsgLabError):
    """No entró en memoria lo que hacía falta para procesar el registro.

    **Existe porque `MemoryError` no hereda de `PsgLabError`**, así que
    atravesaba el `except` de la ventana principal y le llegaba al investigador
    como traza de Python: el único error del programa que rompía la promesa de
    `psglab/utils/errors.py`. Y es de los que más probablemente se vea, porque
    la señal vive entera en memoria.

    El mensaje dice qué se estaba haciendo, porque no es lo mismo quedarse sin
    memoria abriendo el archivo que filtrándolo: en el segundo caso el registro
    ya está en pantalla y se puede seguir trabajando sin filtrar.
    """


# -- Análisis ---------------------------------------------------------------


class InvalidFilterError(PsgLabError):
    """Los parámetros del filtro no son aplicables a este registro."""


class UnknownPsdMethodError(PsgLabError):
    """Se pidió estimar la PSD con un método que el programa no conoce.

    Elegir uno por defecto en silencio le daría al investigador un resultado
    que no pidió y que no puede distinguir del que pidió: Welch y multitaper no
    dan lo mismo.
    """


class InvalidBandError(PsgLabError):
    """La banda de frecuencia no se puede integrar.

    Invertida, con un extremo negativo, o que no es un par de números. Una banda
    de 12 a 8 Hz no contiene nada, y devolver cero para ella escondería el error
    de tipeo detrás de un resultado plausible.
    """


class UnknownMeasureError(PsgLabError):
    """Se pidió una medida de complejidad que el programa no conoce.

    Sin esta comprobación el módulo aceptaba cualquier cadena y fallaba tarde,
    con un `KeyError` en vez de un mensaje que diga cuáles hay.
    """


class UnknownConnectivityMethodError(PsgLabError):
    """Se pidió un método de conectividad que el programa no conoce.

    Importa más que en otros casos: la coherencia común y los métodos basados
    en la parte imaginaria responden preguntas distintas —los segundos son
    inmunes al volume conduction y los primeros no—, así que elegir uno por
    omisión daría un resultado que se interpreta al revés.
    """


# -- Quedarse sin memoria ---------------------------------------------------


@contextmanager
def memoria_suficiente(que_se_estaba_haciendo: str) -> Iterator[None]:
    """Convierte un `MemoryError` en un error que el investigador pueda leer.

    Se usa alrededor de las asignaciones grandes de `psglab/analysis/`, que son
    las únicas del programa que reservan una copia completa de la señal. Una
    noche de 32 canales a 256 Hz son 1,9 GB por copia, y filtrar necesita dos
    además de la que está en pantalla.

    Args:
        que_se_estaba_haciendo: en infinitivo y en español, porque va dentro de
            la frase que ve el usuario: "filtrar la señal", "calcular la ICA".

    Raises:
        RecordingTooLargeError: en lugar del `MemoryError`, que la ventana
            principal no atrapa.

    **Atrapar `MemoryError` y seguir es seguro acá**, y no siempre lo es: lo que
    falla es una sola reserva grande de numpy, que se libera al fallar, así que
    el proceso queda en el mismo estado que antes de intentarla. El registro que
    el investigador está viendo sigue intacto —ninguna función de `analysis/`
    modifica su entrada— y puede seguir trabajando.
    """
    try:
        yield
    except MemoryError as error:
        raise RecordingTooLargeError(
            f"No hay memoria suficiente para {que_se_estaba_haciendo} en esta "
            "computadora. El registro sigue abierto y sin cambios.",
            details=(
                "La señal se procesa entera en memoria y hace falta más de una "
                "copia a la vez. Puede ayudar cerrar otros programas, o trabajar "
                "con menos canales a la vez."
            ),
        ) from error
