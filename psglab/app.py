"""Construcción de la aplicación y de la ventana principal.

Es la única pieza que `main.py` conoce. Su tarea es armar los objetos de Qt y
devolverlos ya cableados, para que el punto de entrada se mantenga mínimo
(requisito del pliego, sección 7).

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura de arranque;
sostiene el requisito técnico de "main.py lo más simple posible" (sección 7).
"""

from PySide6.QtWidgets import QApplication

from psglab.ui.main_window import MainWindow


def create_application(argv: list[str]) -> QApplication:
    """Crea la QApplication y aplica la configuración global.

    Acá va el nombre de la aplicación, el estilo, el idioma y todo lo que
    valga para el programa entero y no para una ventana en particular.

    Args:
        argv: argumentos de línea de comandos recibidos por `main.py`.

    Returns:
        La aplicación de Qt lista para usar.
    """
    raise NotImplementedError("Pendiente: crear la QApplication y su configuración global.")


def create_main_window() -> MainWindow:
    """Crea la ventana principal con todos sus paneles y herramientas.

    No hay que enumerar acá ni las herramientas ni los formatos: cada registro
    se puebla solo, con `tools.registry.load_all_tools()` y
    `readers.base.load_all_readers()`, que recorren su paquete e importan lo que
    encuentran. Por eso agregar una herramienta o un formato nuevo no obliga a
    tocar ni este archivo ni `main.py`.

    Returns:
        La ventana principal, todavía sin mostrar.
    """
    raise NotImplementedError("Pendiente: construir la ventana principal.")
