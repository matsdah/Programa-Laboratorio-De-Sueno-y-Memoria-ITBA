"""Construcción de la aplicación y de la ventana principal.

Es la única pieza que `main.py` conoce. Su tarea es armar los objetos de Qt y
devolverlos ya cableados, para que el punto de entrada se mantenga mínimo
(requisito del pliego, sección 7).

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura de arranque;
sostiene el requisito técnico de "main.py lo más simple posible" (sección 7).
"""

import sys
import traceback
from types import TracebackType

import pyqtgraph as pg
from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication, QMessageBox

from psglab.readers.base import load_all_readers
from psglab.tools.registry import load_all_tools
from psglab.ui import fonts, preferences, theme
from psglab.ui.main_window import MainWindow
from psglab.utils.errors import PsgLabError


def _esquema_guardado() -> theme.ColorScheme:
    """El esquema que el usuario eligió la última vez, o el de fábrica.

    **Un archivo de preferencias roto no puede impedir que el programa arranque**,
    así que el error se atrapa acá y se sigue con el esquema por omisión. Acá no
    llega a la pantalla porque todavía no hay ninguna: la `QApplication` recién
    se está construyendo y la ventana no existe. El cartel lo muestra después
    `MainWindow.apply_saved_preferences()`, que vuelve a leer el mismo archivo
    con la ventana ya armada (hito 33).

    **Hasta el hito 33 esta garantía tenía un agujero**: `load()` sólo elevaba
    `PsgLabError` para los errores del archivo entero, pero una banda mal
    escrita elevaba `IndexError`, que pasaba por acá y el programa no arrancaba.
    Ahora `load()` atrapa por campo todo lo que un valor de JSON puede provocar.

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
    install_qt_translations(aplicacion)
    aplicacion.setApplicationName("PSGLab")
    aplicacion.setOrganizationName("Laboratorio de Sueño y Memoria — ITBA")
    # **Los colores ya no se fijan acá.** Antes eran dos `setConfigOption` con
    # blanco y negro escritos a mano, y cambiar de aspecto obligaba a editar
    # este archivo. Ahora salen del esquema elegido por el usuario, que
    # `psglab/ui/theme.py` sabe aplicar.
    theme.set_current(_esquema_guardado())
    # La tipografía que el programa trae, IBM Plex Sans: es la de toda la
    # interfaz desde el hito 43, y la única desde el 77. **Sin registrarla la
    # ventana sale con la del sistema**, que es lo que le pasaba a la
    # herramienta de capturas hasta el hito 77. Si falta, el programa arranca
    # igual.
    fonts.register_bundled_fonts()
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


def install_qt_translations(application: QApplication) -> bool:
    """Pone en español los botones y textos que arma Qt, no el programa.

    **Hasta el hito 53 salían en inglés**: la pregunta antes de borrar una
    anotación decía «Yes / No», el cartel de error «Show Details... / OK» y el
    diálogo de la clase «OK / Cancel». Son los botones estándar de
    `QMessageBox`, `QInputDialog` y `QFileDialog`, que el programa no escribe:
    los trae Qt, en el idioma de la traducción que tenga cargada, y no tenía
    ninguna. Lo encontró la comparación con el prototipo, que los dibujaba en
    español; ningún test miraba el texto de un botón que no escribió el
    programa.

    La traducción viene con PySide6 (`qtbase_es.qm`), así que no agrega nada
    que empaquetar. **No se cambia el `QLocale`**: eso también cambiaría cómo
    se escriben los números en los campos de la configuración, que es otra
    decisión.

    Returns:
        Si se pudo cargar. Si falta —una instalación de PySide6 sin
        traducciones— el programa arranca igual, con los botones en inglés.
    """
    traductor = QTranslator(application)
    carpeta = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if not traductor.load("qtbase_es", carpeta):
        return False
    return application.installTranslator(traductor)


def create_main_window(
    saved_preferences: bool = False,
    warm_up: bool = False,
    report_unexpected_errors: bool = False,
) -> MainWindow:
    """Crea la ventana principal con todos sus paneles y herramientas.

    No hay que enumerar acá ni las herramientas ni los formatos: cada registro
    se puebla solo, con `tools.registry.load_all_tools()` y
    `readers.base.load_all_readers()`, que recorren su paquete e importan lo que
    encuentran. Por eso agregar una herramienta o un formato nuevo no obliga a
    tocar ni este archivo ni `main.py`.

    Args:
        saved_preferences: si se aplican las preferencias que el usuario
            dejó la última vez, y si los cambios se guardan. **Lo prende sólo
            `main.py`.** La disposición de paneles no es parte de ellas: el
            programa abre siempre con la vista de fábrica. Por omisión está apagado para que la suite
            de tests no lea ni escriba el archivo de preferencias de quien la
            corre, que la volvería dependiente de la máquina.
        warm_up: si se paga en segundo plano lo que se cobraba la primera vez:
            las importaciones perezosas que los lectores le pedían a MNE al
            abrir el primer registro, y la compilación que `antropy` hace al
            importarse. **También lo prende sólo `main.py`**: cada ventana de
            la suite lanzaría un hilo.
        report_unexpected_errors: si un error que no es `PsgLabError` se le
            muestra al usuario en un cartel, además de la consola; ver
            `_avisar_los_errores_inesperados()`. **También lo prende sólo
            `main.py`**: en la suite, un cartel modal la colgaría.

    Returns:
        La ventana principal, todavía sin mostrar.
    """
    # Los dos registros se pueblan solos recorriendo su paquete. Se los carga
    # antes de construir la ventana porque el menú Herramientas y el filtro del
    # diálogo de apertura se arman recorriéndolos.
    load_all_tools()
    load_all_readers()
    ventana = MainWindow()
    if saved_preferences:
        ventana.apply_saved_preferences()
    if warm_up:
        ventana.warm_up_in_background()
    if report_unexpected_errors:
        _avisar_los_errores_inesperados(ventana)
    return ventana


def _avisar_los_errores_inesperados(window: MainWindow) -> None:
    """Muestra en un cartel los errores que no son `PsgLabError` (hito 68).

    **Antes no los veía nadie.** PySide6 le pasa a `sys.excepthook` la
    excepción que sale de un slot, y de fábrica eso la imprime en la consola:
    abierto sin consola, el programa seguía como si nada, con lo que se
    estaba haciendo a medio hacer.

    **No los disfraza de mensaje para el investigador**, que es lo que
    `ui/background.py` decidió no hacer: el cartel dice que es un defecto del
    programa y no de sus datos, y trae la traza entera para poder avisarlo.
    La consola la sigue mostrando igual.

    **Un mismo error se muestra una sola vez.** Uno que salta al pintar se
    repetiría en cada cuadro, y un cartel por cuadro deja el programa
    inutilizable. Se reconoce por su clase y por la línea donde saltó.
    """
    anterior = sys.excepthook
    vistos: set[tuple[str, str, int | None]] = set()
    mostrando = False

    def avisar(
        tipo: type[BaseException], valor: BaseException, traza: TracebackType | None
    ) -> None:
        nonlocal mostrando
        try:
            anterior(tipo, valor, traza)
        except Exception:  # noqa: BLE001 - sin consola, stderr puede no existir
            pass
        if issubclass(tipo, KeyboardInterrupt) or mostrando:
            return
        cuadros = traceback.extract_tb(traza)
        donde = (cuadros[-1].filename, cuadros[-1].lineno) if cuadros else ("", None)
        firma = (tipo.__name__, *donde)
        if firma in vistos:
            return
        vistos.add(firma)
        mostrando = True
        try:
            cartel = QMessageBox(window)
            cartel.setIcon(QMessageBox.Icon.Critical)
            cartel.setWindowTitle(QApplication.applicationName() or "PSGLab")
            cartel.setText("Ocurrió un error del programa.")
            cartel.setInformativeText(
                "No es un problema de tus datos: es un defecto del programa, y lo "
                "que estabas haciendo puede no haberse completado. Conviene "
                "exportar el scoring y avisar, copiando lo que aparece en "
                "«Mostrar los detalles…»."
            )
            cartel.setDetailedText("".join(traceback.format_exception(tipo, valor, traza)))
            cartel.exec()
        except Exception:  # noqa: BLE001 - si el cartel falla, queda la consola
            pass
        finally:
            mostrando = False

    sys.excepthook = avisar
