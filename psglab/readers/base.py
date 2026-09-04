"""Interfaz común de los lectores de archivos y su registro.

Todo lector recibe una ruta y devuelve un `Recording`. El resto del programa
sólo llama a `read_recording()` y nunca sabe de qué formato vino la señal.

Para agregar un formato:

    1. Crear `psglab/readers/mi_formato.py`.
    2. Definir una clase que herede de `Reader`.
    3. Decorarla con `@register_reader`.

No hace falta modificar ningún archivo existente.

Importar un scoring ya existente **no** pasa por acá: `read_scoring()` es una
función suelta de `scoring_reader.py` y no un `Reader`, porque un scoring no
produce un `Recording`.

Cubre del pliego: es la base de V1_F y V2_F de "Importación de archivos".
"""

import importlib
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path

from psglab.core.recording import Recording
from psglab.utils.errors import UnsupportedFormatError

#: Lectores registrados, en orden de registro. Se llena solo a medida que se
#: importan los módulos de formato.
_REGISTRY: list[type["Reader"]] = []

#: Si `load_all_readers()` ya recorrió el paquete. Evita releer el directorio
#: en cada apertura de archivo.
_REGISTRY_CARGADO: bool = False


class Reader(ABC):
    """Lector de un formato de registro.

    Attributes:
        format_name: nombre del formato tal como se le muestra al usuario en
            el diálogo de apertura de archivos.
        extensions: extensiones que maneja, en minúscula y con punto.
    """

    format_name: str = ""
    extensions: tuple[str, ...] = ()

    def can_read(self, path: Path) -> bool:
        """Indica si este lector puede abrir el archivo.

        La implementación por defecto compara la extensión contra
        `extensions`. Un lector la sobrescribe sólo si necesita inspeccionar
        el contenido del archivo para decidir.

        Está implementada y no pendiente, a diferencia del resto del
        esqueleto, porque es infraestructura de despacho: sin ella
        `read_recording()` no puede elegir lector y el registro de formatos no
        funciona ni con un solo lector terminado.
        """
        return path.suffix.lower() in self.extensions

    @abstractmethod
    def read(self, path: Path) -> Recording:
        """Carga el archivo y devuelve el registro.

        La señal se devuelve siempre en microvoltios y con la clase de cada
        canal ya detectada (ver `channel_types.detect_channel_kind`).

        Raises:
            UnreadableFileError: si el archivo está corrupto o incompleto.
        """


def register_reader(reader_cls: type[Reader]) -> type[Reader]:
    """Decorador que registra un lector para que el programa lo descubra.

    Implementado y no pendiente por la misma razón que `Reader.can_read`: es un
    decorador y se ejecuta al importar cada módulo de formato. Si elevara
    NotImplementedError, ningún lector podría importarse.

    Uso:
        @register_reader
        class EdfReader(Reader):
            ...
    """
    _REGISTRY.append(reader_cls)
    return reader_cls


def load_all_readers() -> None:
    """Importa todos los módulos de formato para que se registren.

    Una clase sólo se registra cuando su módulo se importa, y `__init__.py` no
    importa ninguno a propósito: mantener ahí una lista de importaciones sería
    justo el archivo que hay que tocar para agregar un formato, que es lo que
    este mecanismo evita. Sin esta función el registro quedaba vacío y
    `read_recording()` no encontraba **ningún** lector nunca.

    Implementada y no pendiente por la misma razón que `register_reader`: si
    fallara, el punto de extensión de formatos no existiría.

    Llamarla más de una vez no duplica nada ni vuelve a recorrer el paquete: la
    primera vez deja marcado que ya se hizo. Sin esa marca tampoco habría
    duplicados —importar un módulo ya importado no vuelve a ejecutar el
    decorador— pero cada llamada leería el directorio de nuevo, y
    `read_recording()` la llama en cada apertura de archivo.
    """
    global _REGISTRY_CARGADO
    if _REGISTRY_CARGADO:
        return

    import psglab.readers

    for module in pkgutil.iter_modules(psglab.readers.__path__):
        if module.name not in ("base", "channel_types", "scoring_reader"):
            importlib.import_module(f"psglab.readers.{module.name}")
    _REGISTRY_CARGADO = True


def available_readers() -> list[type[Reader]]:
    """Todos los lectores registrados, en orden de registro.

    Devuelve las **clases**, igual que `tools.registry.available_tools()`. Los
    dos son los puntos de extensión del proyecto y conviene que se consuman de
    la misma forma; antes uno devolvía instancias y el otro clases, y la
    ventana principal iba a tener que tratarlos distinto sin motivo.
    """
    load_all_readers()
    return list(_REGISTRY)


def file_dialog_filter() -> str:
    """Filtro de formatos para el diálogo de apertura de archivos de Qt.

    Se construye a partir de los lectores registrados, así que un formato
    nuevo aparece solo en el diálogo sin tocar la interfaz.
    """
    raise NotImplementedError("Pendiente: armar el filtro a partir de los lectores.")


def read_recording(path: Path) -> Recording:
    """Carga un registro eligiendo automáticamente el lector adecuado.

    Es la única función que el resto del programa necesita conocer para
    importar un archivo. El despacho está implementado; lo que falta es el
    `read()` de cada formato.

    Raises:
        UnsupportedFormatError: si ningún lector registrado maneja el archivo.
    """
    for reader_cls in available_readers():
        reader = reader_cls()
        if reader.can_read(path):
            return reader.read(path)
    known_extensions = sorted({ext for cls in _REGISTRY for ext in cls.extensions})
    raise UnsupportedFormatError(
        f"No se puede abrir '{path.name}': el formato no está soportado.",
        details=f"Extensiones conocidas: {', '.join(known_extensions) or 'ninguna'}",
    )
