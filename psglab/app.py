"""Construcción de la aplicación y de la ventana principal.

Es la única pieza que `main.py` conoce. Su tarea es armar los objetos de Qt y
devolverlos ya cableados, para que el punto de entrada se mantenga mínimo
(requisito del pliego, sección 7).

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura de arranque;
sostiene el requisito técnico de "main.py lo más simple posible" (sección 7).
"""

import pyqtgraph as pg
from PySide6.QtWidgets import QApplication

from psglab.readers.base import load_all_readers
from psglab.tools.registry import load_all_tools
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
    aplicacion = QApplication(argv)
    aplicacion.setApplicationName("PSGLab")
    aplicacion.setOrganizationName("Laboratorio de Sueño y Memoria — ITBA")
    # Los fondos de pyqtgraph se fijan acá, para todo el programa: la señal se
    # lee mejor oscura sobre claro, y el criterio visual del scoring tiene que
    # ser el mismo en cualquier computadora del laboratorio.
    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")
    # **El suavizado de curvas queda apagado a propósito**, que es el valor por
    # omisión de pyqtgraph y conviene dejar dicho por qué. Redibujar decenas de
    # canales a cientos de hercios por cada pulsación de flecha es exactamente
    # el motivo por el que se eligió pyqtgraph sobre matplotlib
    # (`docs/ARQUITECTURA.md`), y el antialiasing es lo más caro que se le puede
    # pedir: media noche son cientos de ventanas y media décima de segundo de
    # más por ventana ya se siente. Si alguna vez se enciende, medirlo antes con
    # un registro real de siete canales, no con señal sintética corta.
    pg.setConfigOption("antialias", False)
    return aplicacion


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
    # Los dos registros se pueblan solos recorriendo su paquete. Se los carga
    # antes de construir la ventana porque la barra de herramientas y el filtro
    # del diálogo de apertura se arman recorriéndolos.
    load_all_tools()
    load_all_readers()
    return MainWindow()
