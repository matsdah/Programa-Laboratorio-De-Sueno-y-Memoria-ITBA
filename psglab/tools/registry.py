"""Registro de herramientas disponibles.

Es el mecanismo que hace enchufables a las herramientas. Para agregar una:

    1. Crear `psglab/tools/mi_herramienta.py`.
    2. Definir una clase que herede de `ViewerTool` si actúa con el mouse
       sobre la ventana de la señal, o de `Tool` si es un panel con su propia
       zona de pantalla.
    3. Decorarla con `@register_tool`.

La barra de herramientas de la ventana principal se arma recorriendo este
registro, así que la herramienta nueva aparece sola. No hay que modificar
ningún archivo existente.

Este módulo está implementado y no pendiente, a diferencia del resto del
esqueleto: `register_tool` es un decorador, o sea que **se ejecuta al importar
cada herramienta**. Si elevara NotImplementedError, ningún módulo de
`psglab.tools` podría importarse y el mecanismo enchufable no existiría.
"""

import importlib
import pkgutil

from psglab.tools.base import Tool
from psglab.utils.errors import DuplicateToolError, UnknownToolError

#: Herramientas registradas, por nombre interno. Se llena solo a medida que se
#: importan los módulos del paquete. Es privado: se consulta con las funciones
#: de abajo, no directamente.
_REGISTRY: dict[str, type[Tool]] = {}


def register_tool(tool_cls: type[Tool]) -> type[Tool]:
    """Decorador que registra una herramienta.

    Uso:
        @register_tool
        class MagnifierTool(ViewerTool):
            ...

    Devuelve la clase sin tocarla: decorar no cambia el comportamiento de la
    herramienta, sólo la hace visible para la interfaz.

    Raises:
        DuplicateToolError: si ya hay una herramienta registrada con ese
            nombre. Falla al importar y no en tiempo de ejecución, que es
            cuando conviene enterarse.
    """
    name = tool_cls.name
    if name in _REGISTRY:
        raise DuplicateToolError(
            f"Ya existe una herramienta llamada '{name}'.",
            details=f"{_REGISTRY[name].__module__} y {tool_cls.__module__}",
        )
    _REGISTRY[name] = tool_cls
    return tool_cls


def available_tools() -> list[type[Tool]]:
    """Todas las herramientas registradas, en orden de registro."""
    return list(_REGISTRY.values())


def get_tool(name: str) -> type[Tool]:
    """Busca una herramienta por su nombre interno.

    Raises:
        UnknownToolError: si no hay ninguna herramienta con ese nombre.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownToolError(
            f"No existe una herramienta llamada '{name}'.",
            details=f"Registradas: {', '.join(sorted(_REGISTRY))}",
        ) from None


def load_all_tools() -> None:
    """Importa todos los módulos de herramientas para que se registren.

    Una clase sólo se registra cuando su módulo se importa. Esta función
    recorre el paquete `psglab.tools` e importa lo que encuentra, de modo que
    nadie tenga que mantener a mano una lista de importaciones.
    """
    import psglab.tools

    for module in pkgutil.iter_modules(psglab.tools.__path__):
        if module.name not in ("base", "registry"):
            importlib.import_module(f"psglab.tools.{module.name}")
