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
from psglab.ui import preferences, theme
from psglab.ui.main_window import MainWindow
from psglab.utils.errors import PsgLabError


def _esquema_guardado() -> theme.ColorScheme:
    """El esquema que el usuario eligió la última vez, o el de fábrica.

    **Un archivo de preferencias roto no puede impedir que el programa arranque**,
    así que el error se atrapa acá y se sigue con el esquema por omisión. Es la
    única vez en todo el proyecto que un `PsgLabError` no llega a la pantalla, y
    la razón es que en este momento todavía no hay ninguna: la `QApplication`
    recién se está construyendo y la ventana no existe.

    El usuario no se queda sin señal: ve el programa en los colores de fábrica,
    y elegir un esquema desde el menú vuelve a escribir el archivo, con lo que
    el problema se corrige solo. Preferir un cartel a esto costaría diferir el
    arranque de la ventana para poder mostrarlo.

    **Se llama sólo desde `create_application()`, que a su vez sólo se llama
    desde `main.py`.** Es deliberado: si lo hiciera `create_main_window()`, la
    suite de tests leería el archivo real de quien la corre y dejaría de ser
    reproducible.
    """
    try:
        return preferences.load().scheme()
    except PsgLabError:
        return theme.scheme_by_name(theme.DEFAULT_SCHEME_NAME)


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
    # **Los colores ya no se fijan acá.** Antes eran dos `setConfigOption` con
    # blanco y negro escritos a mano, y cambiar de aspecto obligaba a editar
    # este archivo. Ahora salen del esquema elegido por el usuario, que
    # `psglab/ui/theme.py` sabe aplicar.
    theme.set_current(_esquema_guardado())
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
