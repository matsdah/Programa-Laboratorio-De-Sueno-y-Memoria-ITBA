"""Ventana principal: arma el layout y conecta las piezas entre sí.

Distribución general, pensada para el rol UX/UI del pliego (sección 15):

    +---------------------------------------------------------------+
    | [abrir] Scoring | Escala de tiempo | Amplitud | Ver | Paneles  |
    |   Montaje | Filtrar | Analizar | Herramientas | Configuración  |
    |   Ayuda                                                        |
    +----------+-----------------------------------------+----------+
    | Canales  |                                         | Espectro |
    |  (dock)  |   Visualizador de la señal (central)    | Métrica  |
    |          |                                         | ICA...   |
    |          |                                         | (solapas)|
    +----------+-----------------------------------------+----------+
    |  Übersicht | Scoring | Hipnograma  (docks de abajo, ocultos)   |
    +---------------------------------------------------------------+
    |  Navegación: época ⏮◀▶⏭ | página ≪‹⏯›≫ 1× | amplitud | franja |
    +---------------------------------------------------------------+
    |  Barra de estado: ventana 42 / 960 - 00:21:00                  |
    +---------------------------------------------------------------+

**La señal es el widget central y todo lo demás es un `QDockWidget`**: se
mueve, se apila en solapas, se cierra y se saca a otra pantalla. Los seis
paneles de análisis arrancan ocultos y los abre la acción que los calcula.

**No hay barra de herramientas.** Las herramientas se activan desde su menú,
que es la única vía: la barra horizontal que lo repetía debajo de la barra de
menú se quitó por confusa.

**El programa abre sólo con la señal y el selector de canales**, y no
recuerda la disposición de una apertura a otra (hito 24). Los demás paneles
se abren desde «Herramientas», que desde el hito 28 lleva también los paneles.

Cubre del pliego: V4_F de "Archivo de salida" (`export()` elige cuál de los tres
archivos escribir, aunque desde el hito 23 la ventana sólo ofrece el scoring),
V3_F de "Ocupación de la página" (mostrar el porcentaje), V2_F de
"Herramienta Lupa" (el contador de picos), V2_F del "Histograma" (el eje
horizontal, en hora real o de 1 a VENMAX) y V5_F de "Filtración" (`_olvidar_ica`,
que descarta la descomposición cuando la señal deja de ser la suya).

Los cuatro últimos son **la mitad que vive acá y no en el módulo**: el cálculo
está en `tools/` y en `analysis/`, y lo que faltaba era llevarlo a la pantalla
—o, en el caso de la ICA, sostener su ciclo de vida entre el ajuste y el
"Aplicar"—. Por eso tocar `_update_tool_readout()`, `_marcas_del_histograma()`
o `_olvidar_ica()` rompe un requisito del pliego. El resto sigue siendo lo de
siempre: este archivo es el contenedor que reúne las demás funcionalidades sin
implementar ninguna, y cada una vive en su módulo.
"""

import threading
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import timedelta
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QFont, QFontMetrics, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QToolBar,
    QWidget,
)

from psglab.config import (
    MAX_SCALE_UV,
    MIN_SCALE_UV,
    MIN_VIEW_SECONDS,
    VIEW_PAN_FRACTION,
    VIEW_ZOOM_FACTOR,
)
from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import (
    Nomenclature,
    SleepStage,
    stage_label,
    stages_of,
)
from psglab.core.recording import Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.analysis.derivation import derive
from psglab.analysis.complexity import MEASURES, complexity_by_window, warm_up
from psglab.analysis.connectivity import (
    METHOD_LABELS,
    average_connectivity,
    compute_connectivity,
    connectivity_by_window,
)
from psglab.analysis.ica import (
    apply_ica,
    component_time_course,
    component_topography,
    explained_variance,
    fit_ica,
)
from psglab.analysis.impedance import (
    DEFAULT_LIMIT_KOHM,
    impedance_report,
    load_impedances_from_file,
    read_impedances,
)
from psglab.analysis.filters import apply_filters, settings_for_kinds
from psglab.analysis.psd import band_power, compute_psd, describe_method
from psglab.analysis.reference import average_reference, rereference
from psglab.core.windows import (
    count_windows,
    epoch_to_seconds,
    window_to_clock_time,
    window_to_samples,
)
from psglab.exporters import DEFAULT_FILENAMES
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.information_txt import export_information
from psglab.exporters.scoring_formats import SCORING_FORMATS, export_scoring_as
from psglab.readers.base import (
    IMPORT_WARNINGS_KEY,
    file_dialog_filter,
    read_recording,
    warm_up_readers,
)
from psglab.readers.scoring_reader import read_scoring
from psglab.tools.amplitude_band import AmplitudeBandTool
from psglab.tools.annotator import AnnotatorTool, annotation_bands
from psglab.tools.base import Overlay, Tool, ViewerTool
from psglab.tools.histogram import HistogramTool
from psglab.tools.magnifier import MagnifierTool
from psglab.tools.occupancy import OccupancyTool
from psglab.tools.overview import OverviewTool
from psglab.tools.registry import available_tools
from psglab.ui import fonts, preferences, theme
from psglab.ui.channel_selector import ChannelSelector
from psglab.ui.docks import build_docks
from psglab.ui.icons import icon
from psglab.ui.menus import (
    build_menus,
    duration_text,
    menu_path,
    rebuild_recent_menu,
    rebuild_views_menu,
)
from psglab.ui.navigation import NavigationBar
from psglab.ui.overview_panel import OverviewPanel
from psglab.ui.panel_header import SIN_REGISTRO
from psglab.ui.playback import PlaybackClock
from psglab.ui.connectivity_panel import ConnectivityPanel
from psglab.ui.ica_panel import IcaPanel
from psglab.ui.filter_panel import FilterPanel
from psglab.ui.background import BackgroundTask
from psglab.ui.impedance_panel import ImpedancePanel
from psglab.ui.metric_panel import MetricPanel
from psglab.ui.psd_panel import PsdPanel
from psglab.ui.scoring_panel import ScoringPanel
from psglab.ui.settings_dialog import SettingsDialog
from psglab.ui.shortcuts import install_shortcuts
from psglab.ui.shortcuts_dialog import ShortcutsDialog
from psglab.ui.signal_view import SignalView
from psglab.utils.errors import PsgLabError, UndeclaredNomenclatureError

#: Lo que se le suma al ancho del identificador del registro para que no quede
#: pegado al borde de la ventana ni a la última entrada del menú.
_MARGEN_DEL_IDENTIFICADOR: int = 18

#: El título de los carteles de error y de aviso. **No dice nada que haya que
#: leer** (hito 66): macOS no muestra el título de un `QMessageBox` —lo pide la
#: guía de Apple—, así que lo que el usuario tiene que saber va en el texto. El
#: hito 65 había puesto qué falló en el título, y en una Mac no se veía.
_TITULO_DE_LOS_CARTELES: str = "PSGLab"

#: Qué parte de la separación entre dos filas del hipnograma ocupa la barra de
#: color de una fase. Menos de la mitad a propósito: la barra tiene que leerse
#: como una marca sobre su fila y no como un bloque que tape la curva.
_GROSOR_DE_LA_FASE: float = 0.34

#: Medidas de complejidad que la interfaz ofrece para recorrer la noche.
#:
#: **Son las de `MEASURES` menos la entropía de muestra**, y la exclusión está
#: medida, no supuesta: sobre una ventana de 30 s a 256 Hz tarda 124 ms contra
#: 0,07–1,7 ms de las otras tres, así que sobre las 2650 ventanas de un
#: registro real son más de cinco minutos con la ventana congelada.
#:
#: `complexity_by_window()` la acepta igual: es una función de biblioteca y
#: quien la llama desde un script puede esperar. La política es de la interfaz.
MEDIDAS_RAPIDAS = tuple(m for m in MEASURES if m != "sample_entropy")

#: Con qué método se mide la conectividad. **Se pide explícito** y no por el
#: valor por omisión de `compute_connectivity()`: el rótulo de la escala de
#: color sale de acá, y con el método implícito los dos podían separarse sin
#: que nada fallara.
METODO_DE_CONECTIVIDAD: str = "wpli"

#: Cuánto mide la barra que dice que el programa está trabajando, en píxeles.
#: Corta: es una señal de vida, no una lectura.
ANCHO_DE_LA_BARRA_DE_ESPERA: int = 90

#: Qué botón del mouse llegó, traducido al vocabulario de `ViewerTool`, que no
#: conoce Qt.
_BOTONES = {
    Qt.MouseButton.LeftButton: "left",
    Qt.MouseButton.RightButton: "right",
    Qt.MouseButton.MiddleButton: "middle",
}

#: A cuántos píxeles del borde de una banda el anotador lo toma por ese borde
#: (hito 52). Cinco es lo que un mouse acierta sin tener que apuntar; más, y
#: una anotación corta no deja lugar para empezar otra adentro.
_PIXELES_DEL_BORDE: int = 5

#: Las entradas del menú del clic derecho sobre una banda.
_CAMBIAR_CLASE = "Cambiar clase…"
_BORRAR = "Borrar"

#: Cuánto mide una muesca de la rueda en `QWheelEvent.angleDelta()`, que viene
#: en octavos de grado: una muesca son 15°. Un panel táctil manda pedazos más
#: chicos, y la cuenta de `_girar_la_rueda()` los suma sin redondear.
_DELTA_POR_MUESCA = 120

#: Qué fracción de la página corre una muesca de desplazamiento (hito 56).
#: **En fracciones de la página**, por lo mismo que `_desplazar()`: en segundos
#: fijos, con una página de 200 ms saltaría fuera de lo que se ve y con una de
#: cuatro horas no se notaría. Un décimo deja seguir un huso con la vista.
_PAGINA_POR_MUESCA = 0.1

#: Cuántas muescas de la rueda duplican la página (hito 56). Con una sola, cada
#: muesca sería un «×2» del menú y de 30 s a la noche entera habría diez
#: saltos que no dejan elegir nada en el medio; con dos, veinte.
_MUESCAS_POR_DUPLICAR = 2


def _en_escena(vista: pg.PlotWidget, evento: QMouseEvent | QWheelEvent) -> QPointF:
    """La posición de un evento de mouse del viewport, en la escena de la vista.

    **No es `evento.scenePosition()`.** En un `QMouseEvent` de widget, Qt llama
    "escena" a la ventana de primer nivel, no a la `QGraphicsScene` de
    pyqtgraph: el valor trae sumado todo lo que hay a la izquierda y arriba del
    gráfico. Con el selector de canales abierto eran 280 px, y la selección del
    anotador arrancaba varios segundos a la derecha del mouse. Los tests no lo
    veían porque armaban el evento con las tres posiciones iguales.
    """
    return vista.mapToScene(evento.position().toPoint())



#: Cuántas muestras tiene que abarcar una página, sumando los canales visibles,
#: para que dibujarla muestre el cursor de espera. Veinte millones son unos
#: 250 ms sobre la máquina de desarrollo: por debajo la espera no se nota, y
#: mostrar el cursor por un parpadeo es peor que no mostrarlo.
_MUESTRAS_PARA_AVISAR = 20_000_000


def _primero_que_toma_foco(widget: QWidget | None) -> QWidget | None:
    """El primer widget, empezando por él mismo, que se puede enfocar con el
    teclado. None si no hay ninguno."""
    if widget is None:
        return None
    for candidato in [widget, *widget.findChildren(QWidget)]:
        if candidato.focusPolicy() & Qt.FocusPolicy.TabFocus and candidato.isEnabled():
            return candidato
    return None


def _precalentar() -> None:
    """Lo que corre el hilo de `MainWindow.warm_up_in_background()`, en orden.

    Está suelto y no adentro de la ventana porque no la toca: si tocara algo de
    Qt desde otro hilo habría que pensarlo mucho más.
    """
    warm_up_readers()
    warm_up()


class MainWindow(QMainWindow):
    """Ventana principal del programa."""

    def __init__(self) -> None:
        """Crea la ventana con todos sus paneles, todavía sin registro abierto."""
        super().__init__()
        self.setWindowTitle("PSGLab — Laboratorio de Sueño y Memoria, ITBA")
        self._session: Session | None = None
        #: El registro tal como se leyó, para poder deshacer los análisis.
        self._registro_original: Recording | None = None
        self._tools: dict[str, Tool] = {}
        #: La entrada de menú de cada herramienta, para poder destildarla al
        #: apagarla.
        self._tool_actions: dict[str, QAction] = {}
        #: **Quién se queda con el mouse**, o None. Es la exclusiva activa, y
        #: es lo único que mira `eventFilter()`.
        self._mouse_tool: ViewerTool | None = None
        #: **Quiénes tienen algo que dibujar**, en el orden del registro.
        #:
        #: Son dos campos y no uno desde el hito 45. Con uno solo, una
        #: herramienta que dibuja sin quedarse con el clic —la banda de
        #: amplitud, que declara `exclusive = False` con razón— no entraba en
        #: él, así que su `overlays()` no lo llamaba nadie y tildarla no hacía
        #: nada. Son dos preguntas distintas y ahora tienen dos respuestas.
        self._drawing_tools: list[ViewerTool] = []
        #: Lo último que se le pasó a `signal_view.set_overlays()`. Ver
        #: `_al_cambiar_la_pagina()`.
        self._overlays_dibujados: tuple[Overlay, ...] = ()
        #: La descomposición ICA ajustada, mientras el panel está abierto.
        self._ica: object | None = None
        #: Las preferencias vigentes. **Arrancan en los valores de fábrica y no
        #: se leen del disco acá**: sólo `apply_saved_preferences()` las lee, y sólo
        #: la llama `main.py`. Si el constructor las leyera, la suite de tests
        #: dependería de lo que cada quien tenga configurado en su máquina.
        self._preferencias = preferences.Preferences()
        #: La tipografía con la que arrancó el programa, para poder volver a
        #: ella cuando el usuario elige «la del sistema».
        self._fuente_del_sistema = QFont(QApplication.font())
        #: La ventana de configuración. Se arma la primera vez que se pide.
        self.settings_dialog: SettingsDialog | None = None
        #: Qué panel tiene el foco en el recorrido con F6, como posición en
        #: `focusable_panes()`. Arranca en la señal.
        self._panel_actual = 0

        self._build_layout()
        self._build_menus()
        self._build_tools_menu()
        self._connect_signals()
        install_shortcuts(self, None)
        # El esquema ya está elegido —`create_application()` lo leyó de las
        # preferencias antes de construir nada—, pero la hoja de estilo se
        # aplica sobre la ventana, que recién existe ahora.
        self.setStyleSheet(theme.stylesheet(theme.current()))
        #: La disposición de fábrica, capturada con todos los paneles y la barra
        #: de navegación ya puestos. Es a lo que vuelve «Paneles ▸ Restaurar
        #: la disposición», y tiene que guardarse acá y no antes: `saveState()`
        #: sólo serializa lo que ya existe.
        self._layout_por_defecto = self.saveState()
        #: Si esta ventana es la del usuario, y por lo tanto la que escribe sus
        #: preferencias. Lo prende `create_main_window(saved_preferences=True)`,
        #: que sólo llama `main.py`: así la suite de tests no escribe en el
        #: archivo de quien la corre.
        self._es_la_ventana_del_usuario = False

    # -- Construcción -------------------------------------------------------

    def _build_layout(self) -> None:
        """Crea los paneles y los reparte alrededor de la señal.

        Acá sólo se los construye y se los cablea; **dónde va cada uno lo
        decide `psglab/ui/docks.py`**, por el mismo motivo por el que el menú se
        mudó a `menus.py`: la disposición cambia cuando se reorganiza la
        interfaz, y los paneles cuando cambia lo que el programa hace.
        """
        self.signal_view = SignalView()
        self.channel_selector = ChannelSelector()
        self.scoring_panel = ScoringPanel()
        self.navigation = NavigationBar()
        self.overview_panel = OverviewPanel()
        self.histogram_view = pg.PlotWidget()
        self.histogram_view.getPlotItem().setMenuEnabled(False)
        self.histogram_view.getPlotItem().setMouseEnabled(x=False, y=False)

        self.psd_panel = PsdPanel()
        self.metric_panel = MetricPanel()
        self.connectivity_panel = ConnectivityPanel()

        self.impedance_panel = ImpedancePanel()
        self.impedance_panel.on_changed = self._refrescar_informe_de_impedancia
        self.impedance_panel.boton_archivo.clicked.connect(self.load_impedances_dialog)
        self.impedance_panel.boton_limpiar.clicked.connect(self._limpiar_impedancias)

        self.filter_panel = FilterPanel()
        self.filter_panel.on_apply = self.apply_filters_from_panel

        self.ica_panel = IcaPanel()
        self.ica_panel.on_apply = self._apply_ica
        self.ica_panel.on_component_shown = self._mostrar_curva_del_componente

        build_docks(self)

        # **La navegación no es un panel acoplable.** Es la única vía de
        # navegación con el mouse, así que poder cerrarla dejaría al usuario
        # sin salida si no conoce las flechas del teclado. Va como barra fija
        # abajo, que además es donde la pone la referencia.
        self.navigation_bar = QToolBar("Navegación")
        self.navigation_bar.setObjectName("barra-de-navegacion")
        self.navigation_bar.setMovable(False)
        self.navigation_bar.addWidget(self.navigation)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.navigation_bar)

        #: El reloj de la reproducción. Sólo dice cuánto avanzar; mover el
        #: cursor es de `_avanzar_reproduccion()`.
        self.playback = PlaybackClock(self)
        #: El instante que se está reproduciendo, en segundos desde el inicio
        #: del registro, o None en pausa. Ver `_llevar_el_cursor()`.
        self._cabezal: float | None = None

        # Lo que la herramienta activa quiere informar: el porcentaje de la
        # ocupación (V3_F) y los picos que lleva contados la lupa (V2_F). Va a
        # la derecha, permanente, para que no lo pise el mensaje de navegación.
        self.tool_readout = QLabel("")
        self.statusBar().addPermanentWidget(self.tool_readout)
        #: Cuánto dura la página visible. Va aparte del mensaje de navegación,
        #: que habla de la época: son dos datos distintos.
        self.page_readout = QLabel("")
        self.statusBar().addPermanentWidget(self.page_readout)
        # Las dos son lecturas: el esquema puede darles una tipografía numérica.
        for lectura in (self.tool_readout, self.page_readout):
            lectura.setProperty(theme.READOUT_PROPERTY, True)

        #: Que algo largo está corriendo. **Indeterminada a propósito**: ni la
        #: conectividad de la noche ni la ICA informan cuánto llevan hechas, así
        #: que un porcentaje sería inventado. Ver `_en_segundo_plano()`.
        self._barra_de_espera = QProgressBar()
        self._barra_de_espera.setRange(0, 0)
        self._barra_de_espera.setTextVisible(False)
        self._barra_de_espera.setFixedWidth(ANCHO_DE_LA_BARRA_DE_ESPERA)
        self._barra_de_espera.setAccessibleName("El programa está trabajando")
        self._barra_de_espera.hide()
        self.statusBar().addPermanentWidget(self._barra_de_espera)

        #: El único cálculo largo que puede estar corriendo. Ver
        #: `psglab/ui/background.py`.
        self._tarea = BackgroundTask(self)

        #: Las acciones que arrancan un cálculo largo, para poder apagarlas
        #: mientras dura. Las llena `_build_menus()`.
        self._acciones_largas: tuple[QAction, ...] = ()

        self.statusBar().showMessage(SIN_REGISTRO)

    def _build_menus(self) -> None:
        """Arma la barra de menú.

        El contenido vive en `psglab/ui/menus.py`, que además de las acciones
        deja en la ventana los dos `QAction` que el resto del programa toca
        —`accion_eje_en_hora` y `accion_señal_original`—, el botón de abrir un
        registro y el menú vacío de herramientas que puebla
        `_build_tools_menu()`.
        """
        build_menus(self)
        # **Lo que no se puede pedir con un cálculo en curso.** Los dos menús
        # enteros porque las cuatro operaciones que llevan adentro sustituyen
        # el registro —o, en el caso de la ICA, arrancan otro cálculo—, y la
        # acción de conectividad porque es la otra que corre en otro hilo.
        self._acciones_largas = (
            self.accion_conectividad_de_la_noche,
            self.menu_montaje.menuAction(),
            self.menu_filtrar.menuAction(),
        )
        self._poner_pistas()

    def _poner_pistas(self) -> None:
        """Les dice a los paneles de resultados qué les falta y desde qué menú
        se pide.

        Se ven con el panel vacío: al mostrarlo desde «Herramientas», o después
        de que un cambio de la señal descartó el resultado. Las rutas salen del
        menú armado con `menu_path()`, así que siguen al menú si se lo renombra.

        **Primero qué falta** (hito 65): decía sólo «Se pide desde…», y un
        panel vacío que no dice qué muestra obliga a adivinarlo por el menú.
        La frase vale en los dos casos —nunca se calculó, o se descartó—, y
        por eso no dice «todavía».
        """
        pistas = (
            (self.psd_panel, "No hay ningún espectro calculado.", ("show_psd_dialog",)),
            (
                self.metric_panel,
                "No hay ninguna métrica de la noche calculada.",
                ("show_complexity_dialog", "show_connectivity_night_dialog"),
            ),
            (
                self.connectivity_panel,
                "No hay ninguna conectividad medida.",
                ("show_connectivity_dialog",),
            ),
            (
                self.ica_panel,
                "La señal no está descompuesta en componentes.",
                ("show_ica_dialog",),
            ),
        )
        for panel, que_falta, metodos in pistas:
            rutas = [ruta for ruta in (menu_path(self, m) for m in metodos) if ruta]
            if rutas:
                # **Una ruta por renglón.** El título de pyqtgraph no corta
                # líneas, y las dos de la métrica juntas no entran en el ancho
                # de la pila de análisis.
                panel.set_hint(
                    f"{que_falta}<br>Se pide desde " + "<br>o desde ".join(rutas)
                )

    def _build_tools_menu(self) -> None:
        """Crea las herramientas y sus entradas en el menú Herramientas.

        Se arma recorriendo `psglab.tools.registry`, así que una herramienta
        nueva aparece sola sin tocar este archivo.

        **El menú es la única vía para activarlas.** Hasta el hito 23 las
        mismas acciones iban también en una barra horizontal debajo del menú,
        que repetía lo mismo y se confundía con él.

        **Una herramienta que tiene panel no recibe entrada propia** (hito 28):
        la que cuenta es la del panel, que `menus._herramientas()` ya puso. Son
        las que se llaman igual que una clave de `self.docks` —hoy la Übersicht
        y el hipnograma—, y se prenden solas al abrir un registro
        (`_activate_panel_tools()`), así que lo único que el usuario decide es
        si el panel se ve. Con las dos entradas, un menú las mostraba tildadas
        y el otro no, y apagar la herramienta con el panel a la vista lo dejaba
        vacío.

        Las demás, los modos del mouse, se insertan **arriba del menú**, antes
        de la primera entrada que dejó `menus._herramientas()`, y en el orden
        del registro.
        """
        primera = self.tools_menu.actions()[0] if self.tools_menu.actions() else None
        for cls in available_tools():
            herramienta = cls()
            self._tools[cls.name] = herramienta
            if cls.name in self.docks:
                continue

            accion = QAction(cls.label, self)
            accion.setCheckable(True)
            accion.setToolTip(cls.description)
            # El menú no muestra tooltips; la barra de estado sí muestra esto
            # mientras el mouse pasa por la entrada.
            accion.setStatusTip(cls.description)
            self._tool_actions[cls.name] = accion
            accion.toggled.connect(
                lambda activa, n=cls.name: self._toggle_tool(n, activa)
            )
            self.tools_menu.insertAction(primera, accion)

    def _connect_signals(self) -> None:
        """Conecta las señales de los paneles entre sí.

        Es el único lugar donde los paneles se enteran unos de otros: el
        visualizador no conoce al histograma, los dos pasan por acá.

        Acá se cablean también los callbacks de las herramientas, que no son
        señales de Qt porque `Tool` no hereda de `QObject`:

        - `tool.on_changed`, que dispara
          `signal_view.set_overlays(tool.overlays())`. Es el camino por el que
          una herramienta hace aparecer algo en pantalla sin conocer Qt.
        - `histogram.on_window_requested`, que lleva el clic del hipnograma a
          `session.go_to_window()`.

        **Los dos se asignan sobre la instancia de la herramienta, nunca sobre
        su clase**: asignados en la clase quedarían como método ligado y la
        llamada pasaría un argumento de más.

        Las coordenadas de los eventos de mouse se convierten acá, con
        `signal_view.seconds_at_pixel()`, antes de avisarle a la herramienta
        activa: `ViewerTool` recibe segundos, nunca píxeles.
        """
        self.navigation.window_requested.connect(self._go_to_window)
        # Hito 51: un clic en una caja de la Übersicht va a esa ventana, igual
        # que un clic en la franja de posición.
        self.overview_panel.window_clicked.connect(self._go_to_window)
        self.navigation.amplitude_up_requested.connect(self.increase_amplitude)
        self.navigation.amplitude_down_requested.connect(self.decrease_amplitude)
        self.navigation.playback_toggle_requested.connect(self.toggle_playback)
        self.navigation.playback_speed_changed.connect(self._cambiar_velocidad)
        self.playback.advanced.connect(self._avanzar_reproduccion)
        self.playback.playing_changed.connect(self._al_cambiar_la_reproduccion)
        self.scoring_panel.stage_selected.connect(self.score_current_window)
        self.scoring_panel.arousal_toggled.connect(self._set_arousal)
        self.scoring_panel.nomenclature_changed.connect(self._change_nomenclature)
        self.channel_selector.visible_changed.connect(self._set_visible_channels)
        self.channel_selector.selection_changed.connect(self._set_selected_channels)

        for herramienta in self._tools.values():
            herramienta.on_changed = self._on_tool_changed
            if isinstance(herramienta, HistogramTool):
                herramienta.on_window_requested = self._go_to_window

        # Los eventos de mouse del visualizador se filtran acá para poder
        # convertirlos de píxeles a segundos antes de dárselos a la herramienta.
        self.signal_view.viewport().installEventFilter(self)
        self.histogram_view.viewport().installEventFilter(self)

    # -- El puente entre el mouse y las herramientas ------------------------

    def eventFilter(self, objeto: QObject, evento: QEvent) -> bool:
        """Traduce los eventos de mouse al vocabulario de las herramientas.

        **Es el único lugar donde un píxel se convierte antes de salir de
        `ui/`.** `ViewerTool` recibe segundos y microvoltios; el histograma
        recibe una fracción de la noche. Ninguna herramienta ve un píxel.
        """
        if objeto is self.histogram_view.viewport():
            self._filtrar_histograma(evento)
            return False
        if objeto is not self.signal_view.viewport():
            return False
        if evento.type() == QEvent.Type.Wheel:
            return self._girar_la_rueda(evento)

        herramienta = self._mouse_tool
        if herramienta is None or evento.type() not in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            return False

        # **En coordenadas de escena, y convertidas por la vista.** Ver
        # `_en_escena()`: `scenePosition()` no es la escena de pyqtgraph.
        punto = _en_escena(self.signal_view, evento)
        segundos = self.signal_view.seconds_at_pixel(punto.x())
        # **En microvoltios, que es lo que `ViewerTool` documenta recibir.**
        # Hasta el hito 9 acá iba la coordenada cruda del gráfico, con un
        # comentario que afirmaba que ninguna herramienta usaba la `y`. La usan
        # tres, y la peor consecuencia era que la ocupación borraba una línea
        # con cualquier clic, porque comparaba su tolerancia de 10 µV contra un
        # rango de 0 a 1.
        #
        # **Y contra el canal bajo el cursor**, desde el hito 45. El conversor
        # acepta el canal desde el hito 9 y nadie se lo pasaba, así que medía
        # todo contra el primero visible: sobre tres canales, el centro del
        # tercer carril llegaba como −444 µV en vez de 0. La lupa ampliaba
        # siempre el primero por la misma razón.
        canal = self.signal_view.channel_at_pixel(punto.y())
        y = self.signal_view.microvolts_at_pixel(punto.y(), canal)

        if isinstance(herramienta, AnnotatorTool):
            # **Un borde se agarra a unos píxeles, no a unos segundos** (hito
            # 52): un segundo son cientos de píxeles con una página de 5 s y
            # ninguno con la noche entera. La herramienta no conoce la
            # pantalla, así que se lo dice la ventana en cada evento.
            segundos_por_pixel = self.signal_view.getPlotItem().vb.viewPixelSize()[0]
            herramienta.set_edge_tolerance(segundos_por_pixel * _PIXELES_DEL_BORDE)

        if evento.type() == QEvent.Type.MouseMove:
            herramienta.on_mouse_move(segundos, y, canal)
            if isinstance(herramienta, AnnotatorTool):
                self._cursor_del_anotador(herramienta, segundos, evento)
        else:
            boton = _BOTONES.get(evento.button(), "left")
            if evento.type() == QEvent.Type.MouseButtonPress:
                herramienta.on_mouse_press(segundos, y, boton, canal)
                if isinstance(herramienta, AnnotatorTool) and boton == "right":
                    self._menu_de_anotacion(
                        herramienta, segundos, evento.globalPosition().toPoint()
                    )
            else:
                herramienta.on_mouse_release(segundos, y, boton, canal)
                # **Acá se cierra el lazo de V1_F de "Anotación".** La
                # herramienta deja el tramo pendiente y espera que alguien
                # pregunte la clase; hasta el hito 9 no lo hacía nadie, así que
                # se podía arrastrar una selección y no pasaba nada.
                if isinstance(herramienta, AnnotatorTool):
                    self._finish_annotation(herramienta)
                    self._avisar_borde_movido(herramienta)
        return False

    def _girar_la_rueda(self, evento: QWheelEvent) -> bool:
        """La rueda sobre la señal: escala o desplazamiento (hito 56).

        - **Vertical, cambia la escala**; ver `_escala_con_la_rueda()`.
        - **Horizontal, desplaza la página**: es lo que manda un panel táctil
          al deslizar de costado, y una rueda con inclinación.
        - **Con Mayúsculas, la vertical también desplaza**, que es la
          convención de casi todo programa con un eje horizontal largo. macOS
          ya la entrega convertida en horizontal y Windows no, así que se
          acepta de las dos formas.

        Un panel táctil casi nunca desliza derecho: **manda el eje que más se
        movió**, y no los dos, o cada gesto de costado cambiaría un poco la
        escala.

        Returns:
            Si la rueda se usó. Usada, no sigue a pyqtgraph ni al panel de
            desplazamiento que haya afuera.
        """
        if self._session is None:
            return False
        delta = evento.angleDelta()
        if evento.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Hacia atrás —hacia el usuario— es hacia adelante en el
            # registro, como bajar en un documento.
            horizontal = delta.x() or delta.y()
            return self._desplazar_con_la_rueda(horizontal / _DELTA_POR_MUESCA)
        if abs(delta.x()) > abs(delta.y()):
            return self._desplazar_con_la_rueda(delta.x() / _DELTA_POR_MUESCA)
        return self._escala_con_la_rueda(evento, delta.y() / _DELTA_POR_MUESCA)

    def _desplazar_con_la_rueda(self, muescas: float) -> bool:
        """Corre la página una fracción de sí misma por muesca.

        **Positivo es hacia atrás en el registro**: deslizar hacia la derecha
        en un panel táctil trae lo que estaba a la izquierda, igual que
        arrastrar un papel. Pasa por `_desplazar()`, así que reproduciendo
        mueve el cursor y no sólo la página.
        """
        if muescas == 0:
            return False
        self._desplazar(-muescas * _PAGINA_POR_MUESCA)
        return True

    def _escala_con_la_rueda(self, evento: QWheelEvent, muescas: float) -> bool:
        """Acerca o aleja la página con la rueda.

        **Queda quieto el instante bajo el mouse**, como en un mapa: para mirar
        de cerca un huso se apunta y se gira, sin tener que centrarlo antes.
        Hacia adelante acerca y hacia atrás aleja.

        **Reproduciendo, el ancla es el cursor** y no el mouse: la página es
        suya y el paso siguiente la volvería a centrar, así que anclar en el
        mouse haría saltar el dibujo de un cuadro al otro.
        """
        if self._session is None or muescas == 0:
            return False
        factor = VIEW_ZOOM_FACTOR ** (-muescas / _MUESCAS_POR_DUPLICAR)
        pagina = self._session.viewport
        if self._cabezal is not None:
            nueva = pagina.zoomed(factor)
        else:
            instante = self.signal_view.seconds_at_pixel(
                _en_escena(self.signal_view, evento).x()
            )
            nueva = pagina.zoomed_at(factor, instante)
        # En los topes —la página mínima, el registro entero— la rueda no
        # cambia nada, y redibujar lo mismo en cada muesca sería puro costo.
        if nueva != pagina:
            self._cambiar_pagina(nueva)
        return True

    def _filtrar_histograma(self, evento: QEvent) -> None:
        """Un clic en el hipnograma es una posición de la noche, no un segundo."""
        if evento.type() != QEvent.Type.MouseButtonPress:
            return
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool):
            return
        caja = self.histogram_view.getPlotItem().vb.sceneBoundingRect()
        if caja.width() <= 0:
            return
        # De escena, igual que `caja`, que es un `sceneBoundingRect()`.
        fraccion = (_en_escena(self.histogram_view, evento).x() - caja.left()) / caja.width()
        herramienta.on_click(min(1.0, max(0.0, fraccion)))

    def _finish_annotation(self, herramienta: AnnotatorTool) -> None:
        """Pregunta la clase del evento recién seleccionado y lo anota (V1_F).

        El pliego pide **asignarle o crear una clase**, así que el diálogo es
        editable: la lista ofrece las que ya existen y el usuario puede escribir
        una nueva, que se registra con su color antes de anotar.

        Cancelar deja el tramo pendiente sin anotar, que es lo que espera quien
        se arrepiente a mitad del gesto. No se lo borra: volver a soltar el
        mouse lo reemplaza.
        """
        if self._session is None:
            return
        pendiente = herramienta.pending_selection_samples
        if pendiente is None:
            return
        self._preguntar_clase_y_anotar(herramienta, *pendiente)

    def _preguntar_clase_y_anotar(
        self, herramienta: AnnotatorTool, inicio: int, duracion: int
    ) -> None:
        """Pregunta la clase de un tramo y lo anota.

        Es el final común del arrastre con el mouse y de «Anotar la ventana
        actual» con el teclado (hito 62): los dos llegan con un tramo en
        muestras y lo demás es igual.
        """
        if self._session is None:
            return
        clases = self._session.annotations.labels()
        clase, acepto = QInputDialog.getItem(
            self,
            "Anotar evento",
            "Clase del evento (se puede escribir una nueva):",
            clases,
            0,
            True,
        )
        if not acepto or not clase.strip():
            return
        clase = clase.strip()

        try:
            if clase not in clases:
                herramienta.add_label(clase)
            herramienta.create_annotation(clase, inicio, duracion)
        except PsgLabError as error:
            self._show_error(error, "anotar el evento")
            return
        # El panel de contexto marca los eventos que caen en cada ventana
        # (V3_F), y anotar no mueve de ventana: hay que pedirle que se
        # rederive o el evento recién creado no aparece hasta la próxima flecha.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        self.statusBar().showMessage(f"Se anotó «{clase}»", 5000)

    def _menu_de_anotacion(
        self, herramienta: AnnotatorTool, segundos: float, donde: QPoint
    ) -> None:
        """El clic derecho sobre una banda: cambiarle la clase o borrarla.

        **Hasta el hito 52 el clic derecho borraba**, con confirmación, y era lo
        único que se podía hacer con una anotación hecha. Un clic derecho donde
        no hay nada no hace nada.
        """
        anotacion = herramienta.annotation_at(segundos)
        if anotacion is None:
            return
        self._ofrecer_cambios(herramienta, anotacion, donde)

    def _ofrecer_cambios(
        self, herramienta: AnnotatorTool, anotacion: Annotation, donde: QPoint
    ) -> None:
        """El menú de una anotación: cambiarle la clase o borrarla."""
        eleccion = self._elegir_en_un_menu(
            [_CAMBIAR_CLASE, _BORRAR], donde
        )
        if eleccion == _CAMBIAR_CLASE:
            self._cambiar_clase(herramienta, anotacion)
        elif eleccion == _BORRAR:
            self._borrar_anotacion(herramienta, anotacion)

    # -- Anotar con el teclado (hito 62) ------------------------------------
    #
    # **Anotar era lo único del pliego que exigía mouse**: arrastrar sobre la
    # señal para crear, clic derecho para corregir. WCAG 2.1.1 pide que todo
    # se pueda con el teclado, y la unidad natural del teclado es la época,
    # que es lo que mueven las flechas.

    def annotate_current_window(self) -> None:
        """E: anota la ventana actual entera y pregunta su clase.

        **Enciende el modo «Anotar»** si no lo estaba, igual que elegirlo del
        menú: la herramienta es la que sabe anotar, y dejarla encendida es lo
        que permite después corregir con Mayús+F10 o con el mouse.
        """
        herramienta = self._anotador_encendido()
        if herramienta is None or self._session is None:
            return
        inicio, fin = self._muestras_de_la_ventana_actual()
        self._preguntar_clase_y_anotar(herramienta, inicio, fin - inicio)

    def annotation_menu_for_current_window(self) -> None:
        """Mayús+F10 o la tecla Menú, con el foco en la señal: el menú del
        clic derecho para la anotación de la ventana actual.

        Si hay varias se elige **la más corta**, con la misma regla que el
        clic derecho: la larga se puede alcanzar desde otra ventana, la corta
        no. Sin ninguna, la barra de estado lo dice en vez de no hacer nada.
        """
        herramienta = self._anotador_encendido()
        if herramienta is None or self._session is None:
            return
        inicio, fin = self._muestras_de_la_ventana_actual()
        en_la_ventana = self._session.annotations.in_range(inicio, fin)
        if not en_la_ventana:
            self.statusBar().showMessage("No hay ninguna anotación en esta ventana", 5000)
            return
        anotacion = min(en_la_ventana, key=lambda candidata: candidata.duration_samples)
        vista = self.signal_view.viewport()
        self._ofrecer_cambios(herramienta, anotacion, vista.mapToGlobal(vista.rect().center()))

    def _anotador_encendido(self) -> AnnotatorTool | None:
        """La herramienta de anotar, encendida por el mismo camino que el menú."""
        herramienta = self._tools.get("annotator")
        accion = self._tool_actions.get("annotator")
        if not isinstance(herramienta, AnnotatorTool) or accion is None:
            return None
        if not accion.isChecked():
            accion.setChecked(True)
        return herramienta

    def _muestras_de_la_ventana_actual(self) -> tuple[int, int]:
        """Dónde empieza y termina la ventana actual, recortada al registro."""
        registro = self._session.recording
        inicio, fin = window_to_samples(self._session.current_window, registro.sampling_rate)
        return inicio, min(fin, registro.n_samples)

    def _elegir_en_un_menu(self, opciones: list[str], donde: QPoint) -> str | None:
        """Muestra un menú contextual y devuelve lo que se eligió, o `None`.

        Aparte para que los tests lo contesten sin abrirlo: es modal, y sin
        nadie que elija la suite se colgaría.
        """
        menu = QMenu(self)
        for opcion in opciones:
            menu.addAction(opcion)
        elegida = menu.exec(donde)
        return elegida.text() if elegida is not None else None

    def _cambiar_clase(self, herramienta: AnnotatorTool, anotacion: Annotation) -> None:
        """Pregunta la clase nueva de una anotación hecha y se la cambia.

        El diálogo es el mismo que al anotar —editable, así que una clase nueva
        se puede escribir— pero arranca en la clase que tiene. Elegir la misma
        no hace nada.
        """
        if self._session is None:
            return
        clases = self._session.annotations.labels()
        actual = clases.index(anotacion.label) if anotacion.label in clases else 0
        clase, acepto = QInputDialog.getItem(
            self,
            "Cambiar la clase",
            "Clase del evento (se puede escribir una nueva):",
            clases,
            actual,
            True,
        )
        clase = clase.strip()
        if not acepto or not clase or clase == anotacion.label:
            return
        try:
            if clase not in clases:
                herramienta.add_label(clase)
            herramienta.change_label(anotacion, clase)
        except PsgLabError as error:
            self._show_error(error, "cambiar la clase")
            return
        self._refrescar_contexto()
        self.statusBar().showMessage(
            f"«{anotacion.label}» pasó a ser «{clase}»", 5000
        )

    def _avisar_borde_movido(self, herramienta: AnnotatorTool) -> None:
        """Después de soltar un borde arrastrado: la Übersicht y el aviso."""
        movida = herramienta.moved_annotation
        if movida is None:
            return
        self._refrescar_contexto()
        self.statusBar().showMessage(f"Se corrigió el tramo de «{movida.label}»", 5000)

    def _cursor_del_anotador(
        self, herramienta: AnnotatorTool, segundos: float, evento: QMouseEvent
    ) -> None:
        """↔ sobre el borde de una banda, que es lo único que dice que se puede
        arrastrar. Mientras se arrastra, el cursor no cambia."""
        if evento.buttons() != Qt.MouseButton.NoButton:
            return
        viewport = self.signal_view.viewport()
        if herramienta.edge_at(segundos) is not None:
            viewport.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            viewport.unsetCursor()

    def _borrar_anotacion(self, herramienta: AnnotatorTool, anotacion: Annotation) -> None:
        """Borra una anotación, confirmándolo antes.

        **Pregunta** porque no hay deshacer, y una anotación es trabajo del
        investigador. Desde el hito 52 se llega eligiendo «Borrar» en el menú
        del clic derecho, así que un clic de más ya no borra solo; la pregunta
        se conservó igual, porque elegir mal en un menú también es un clic.
        """
        if not self._confirmar(
            "Borrar la anotación",
            f"¿Borrar la anotación «{anotacion.label}»?",
            "Borrar",
            informativo="No se puede deshacer.",
            destructivo=True,
        ):
            return
        try:
            herramienta.delete_annotation(anotacion)
        except PsgLabError as error:
            self._show_error(error, "borrar la anotación")
            return
        # Igual que al anotar: la Übersicht marca qué ventanas tienen eventos.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        self.statusBar().showMessage(f"Se borró «{anotacion.label}»", 5000)

    def _redibujar_overlays(self) -> None:
        """Dibuja las anotaciones de la página y lo de la herramienta activa.

        **Las anotaciones se dibujan siempre**, esté activa la herramienta que
        esté: son datos del registro. Hasta que se decidió así, el visualizador
        mostraba lo de **la última herramienta que avisó**, aunque estuviera
        apagada, y las bandas desaparecían al activar la lupa o cuando la
        ocupación se reanclaba al desplazar la página.

        Con «Anotar» activo se dibuja su `overlays()`, que ya trae las bandas
        más la selección en curso.
        """
        self._overlays_dibujados = self._overlays_a_dibujar()
        self.signal_view.set_overlays(self._overlays_dibujados)

    def _overlays_a_dibujar(self) -> tuple[Overlay, ...]:
        """Lo que `_redibujar_overlays()` dibuja, sin dibujarlo."""
        if self._session is None:
            return ()
        # **El anotador reemplaza a las bandas, no se suma a ellas**: sus
        # `overlays()` ya traen las anotaciones de la página más la selección
        # en curso, así que dibujar las dos cosas las duplicaría.
        anotador = next(
            (t for t in self._drawing_tools if isinstance(t, AnnotatorTool)), None
        )
        overlays: tuple[Overlay, ...] = (
            tuple(anotador.overlays()) if anotador is not None
            else annotation_bands(self._session)
        )
        for herramienta in self._drawing_tools:
            if herramienta is not anotador:
                overlays += tuple(herramienta.overlays())
        return overlays

    def _al_cambiar_la_pagina(self, _viewport: object) -> None:
        """Las bandas son de la página, así que moverla puede cambiar cuáles van.

        **Sólo redibuja si cambió algo**: la reproducción mueve la página en
        cada cuadro, con 40 ms de presupuesto, y las bandas están en segundos
        absolutos, así que desplazarse no las mueve. Rehacerlas en cada cuadro
        sería gastar el presupuesto en dibujar lo mismo.
        """
        if self._overlays_a_dibujar() != self._overlays_dibujados:
            self._redibujar_overlays()

    def _on_tool_changed(self, tool: Tool) -> None:
        """Una herramienta avisó de que cambió lo que quiere mostrar."""
        if isinstance(tool, ViewerTool):
            self._redibujar_overlays()
        elif isinstance(tool, HistogramTool):
            self._redraw_histogram()
        elif isinstance(tool, OverviewTool):
            self._redraw_overview(tool)
        self._update_tool_readout()

    def _redraw_overview(self, herramienta: OverviewTool) -> None:
        """Lleva al panel lo que publica la Übersicht (V1_F, V2_F, V3_F).

        Los colores de las clases de evento se le agregan acá y no los manda la
        herramienta: viven en `AnnotationSet`, que es de `core/`, y `tools/`
        publica los nombres de las clases, no cómo se ven.

        El tamaño (V2_F) también viaja en este camino, porque `set_size()`
        avisa por `on_changed` como cualquier otro cambio.
        """
        colores = None
        if self._session is not None:
            anotaciones = self._session.annotations
            colores = {
                clase: anotaciones.color_of(clase) for clase in anotaciones.labels()
            }
        self.overview_panel.set_windows(
            herramienta.windows(), colores, self._color_del_contexto(herramienta)
        )
        ancho, alto = herramienta.size_px
        self.overview_panel.set_panel_size(ancho, alto)

    def _color_del_contexto(self, herramienta: OverviewTool) -> str | None:
        """El color con que la Übersicht dibuja su señal: el de su canal.

        Es el que el canal tiene en el visualizador, que depende de en qué
        carril está (`ColorScheme.color_for_channel()`). Así la miniatura se
        reconoce como el mismo canal de arriba sin leer el nombre.
        """
        if self._session is None:
            return None
        for ventana in herramienta.windows():
            if ventana.trace is None:
                continue
            visibles = self._session.visible_channels
            if ventana.trace.channel_name in visibles:
                posicion = visibles.index(ventana.trace.channel_name)
                return theme.current().color_for_channel(posicion)
        return None

    def _refrescar_contexto(self) -> None:
        """Rehace la Übersicht sin que el usuario haya cambiado de ventana.

        **Desde el hito 51 la Übersicht dibuja señal**, así que depende de más
        cosas que la época: de qué canal está seleccionado, de cuáles se ven, de
        su amplitud y de la señal misma, que filtrar reemplaza. Ninguna de esas
        cosas le llega por `on_window_changed()`.
        """
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()

    def _update_tool_readout(self) -> None:
        """Escribe en la barra de estado el número que la herramienta calcula.

        **Es lo que faltaba para cerrar V3_F de "Ocupación" y V2_F de la
        lupa.** Las dos herramientas calculaban bien y nadie las leía: el
        porcentaje y el contador de picos existían sólo para sus tests.

        No lo dibuja la herramienta porque no conoce Qt, y no puede hacerlo con
        un `Overlay` porque no hay variante de texto: los overlays son
        coordenadas de señal, no leyendas. Por eso el número cruza acá.

        El total de ocupación **puede pasar del 100 %** cuando dos líneas se
        pisan, y es lo buscado: el criterio lo fija
        `config.OCCUPANCY_COUNTS_OVERLAP_ONCE` y quedó confirmado con el
        cliente. Se muestra tal cual, sin recortarlo.
        """
        herramienta = self._mouse_tool
        if isinstance(herramienta, OccupancyTool):
            lineas = herramienta.lines()
            if lineas:
                # La coma se aplica **al número y no a la frase**: con un
                # `replace` sobre el texto entero, cualquier punto que se
                # agregue después al mensaje se convertiría en coma.
                total = f"{herramienta.total_percentage():.1f}".replace(".", ",")
                cuantas = f"{len(lineas)} línea" + ("s" if len(lineas) != 1 else "")
                self.tool_readout.setText(
                    f"Ocupación: {cuantas} — {total} % del ancho"
                )
            else:
                self.tool_readout.setText("Ocupación: sin líneas")
            return
        if isinstance(herramienta, MagnifierTool):
            self.tool_readout.setText(f"Picos contados: {herramienta.click_count}")
            return
        self.tool_readout.setText("")

    def _deja_de_dibujar(self, herramienta: Tool) -> None:
        """La saca de las que dibujan, si estaba."""
        if isinstance(herramienta, ViewerTool) and herramienta in self._drawing_tools:
            self._drawing_tools.remove(herramienta)

    def _deactivate_all_tools(self) -> None:
        """Apaga las herramientas y destilda sus botones.

        La barra tiene que quedar diciendo la verdad: un botón hundido sobre
        una herramienta apagada es peor que ninguno.
        """
        for accion in self._tool_actions.values():
            accion.setChecked(False)
        for herramienta in self._tools.values():
            herramienta.deactivate()
        self._mouse_tool = None
        self._drawing_tools.clear()
        if self._session is not None:
            self._session.set_active_tool(None)
        self._redibujar_overlays()

    def _activate_panel_tools(self) -> None:
        """Enciende las herramientas que son paneles, no modos del mouse.

        Un panel permanente que arranca apagado es un hueco en la pantalla
        esperando que alguien adivine que hay que apretar un botón. Los modos
        del mouse sí arrancan apagados: sólo puede haber uno y elegirlo es del
        usuario.

        **La pregunta es si tiene dock, no si es exclusiva** (hito 45). Con
        `not exclusive` acá, la banda de amplitud —que no compite por el clic
        pero tampoco es un panel— se tildaba sola al abrir cada registro, y
        como además no se dibujaba, el usuario encontraba una opción encendida
        que no hacía nada. Hoy los únicos no exclusivos son la banda, el
        histograma y la Übersicht, y los dos últimos son los que tienen dock.
        """
        if self._session is None:
            return
        for nombre, herramienta in self._tools.items():
            if nombre in self.docks:
                herramienta.activate(self._session)
                if isinstance(herramienta, ViewerTool) and herramienta not in self._drawing_tools:
                    self._drawing_tools.append(herramienta)
                accion = self._tool_actions.get(nombre)
                if accion is not None:
                    accion.setChecked(True)

    def _reload_histogram(self) -> None:
        """Vuelve a leer la noche entera desde el scoring.

        Después de importar, el histograma tiene guardadas las barras del
        scoring anterior: `update_window()` sirve para una tecla, no para
        cambiar el archivo debajo."""
        herramienta = self._tools.get("histogram")
        if isinstance(herramienta, HistogramTool) and self._session is not None:
            herramienta.activate(self._session)

    def _toggle_tool(self, name: str, activa: bool) -> None:
        """Activa o desactiva una herramienta, respetando la exclusividad."""
        herramienta = self._tools.get(name)
        if herramienta is None or self._session is None:
            return

        if activa and herramienta.exclusive:
            for otro in self._tools.values():
                if otro is not herramienta and otro.exclusive:
                    otro.deactivate()
                    self._deja_de_dibujar(otro)
                    accion = self._tool_actions.get(otro.name)
                    if accion is not None and accion.isChecked():
                        # **Destildarla también**, o el menú muestra dos modos
                        # del mouse encendidos y sólo uno recibe eventos.
                        accion.setChecked(False)
            self._mouse_tool = (
                herramienta if isinstance(herramienta, ViewerTool) else None
            )

        if activa:
            herramienta.activate(self._session)
            if isinstance(herramienta, ViewerTool) and herramienta not in self._drawing_tools:
                self._drawing_tools.append(herramienta)
        else:
            herramienta.deactivate()
            self._deja_de_dibujar(herramienta)
            if herramienta is self._mouse_tool:
                self._mouse_tool = None
        # **La sesión lleva cuál es la exclusiva activa** y hasta el hito 33 no
        # se lo decía nadie: `Session.active_tool` era siempre None, con su
        # docstring explicando un estado que no existía.
        if herramienta.exclusive:
            self._session.set_active_tool(name if activa else None)
        # La herramienta avisó mientras todavía figuraba como activa: sin esto
        # quedaría dibujado lo suyo con ella ya apagada.
        self._redibujar_overlays()
        self._update_tool_readout()

    # -- Acciones del usuario -----------------------------------------------

    def open_recording(self, path: Path) -> None:
        """Abre un registro y prepara la sesión de trabajo.

        Muestra un error legible si el archivo no se puede leer, en vez de
        dejar caer una excepción: los usuarios no necesariamente tienen
        experiencia informática (pliego, sección 3).

        **Avisa mientras lee.** Una noche entera son varios segundos —4,3 s el
        registro de prueba, de los cuales 2,6 los tarda MNE— y todo corre en el
        hilo de la interfaz, así que la ventana queda congelada. Sin cursor de
        espera ni mensaje, eso se lee como que el programa se colgó justo
        cuando el usuario hizo lo primero que hace.
        """
        try:
            with self._trabajando(f"Leyendo «{path.name}»"):
                registro = read_recording(path)
            ventanas = count_windows(registro.n_samples, registro.sampling_rate)
            sesion = Session(
                registro,
                # La nomenclatura con que arranca un scoring nuevo. Uno
                # importado trae la suya y ésta no la pisa.
                Scoring(ventanas, self._preferencias.nomenclature()),
                AnnotationSet(),
            )
            # La página con que se abre. Se fija antes de dibujar para no
            # dibujar dos veces.
            sesion.set_viewport(
                sesion.viewport.with_span(self._preferencias.open_view_seconds)
            )
        except PsgLabError as error:
            self._show_error(error, f"abrir «{path.name}»")
            return

        # **Lo que se perdería con la sesión anterior, antes de soltarla**
        # (hito 33). Va después de leer y no antes: si el archivo nuevo no se
        # puede abrir, la sesión anterior sigue y no hay nada que preguntar.
        if not self._puede_descartarse_el_trabajo(f"abrir «{path.name}»"):
            return

        # Las herramientas activas siguen guardando la sesión que recibieron
        # en `activate()`: si no se las suelta, la ocupación seguiría midiendo
        # sobre el registro anterior y el histograma dibujaría su scoring.
        self._deactivate_all_tools()
        # Y por el mismo motivo, la descomposición ICA del registro anterior: es
        # de otra señal y de otros canales.
        self._olvidar_ica()
        # La reproducción avanzaba sobre la página del registro anterior.
        self.playback.stop()

        self._session = sesion
        # **El registro tal como se leyó.** Los análisis de la Parte 2 devuelven
        # un registro nuevo, y sin guardar éste un filtro mal elegido obligaría
        # a reabrir el archivo. Es la regla 1 de `analysis/` vista desde la
        # interfaz: el usuario tiene que poder volver atrás.
        self._registro_original = registro
        self.accion_señal_original.setEnabled(False)
        # Las herramientas se enteran solas de los cambios de ventana: es la
        # decisión del hito 6, y por eso acá no hay que acordarse de avisarles.
        for herramienta in self._tools.values():
            sesion.add_window_listener(herramienta.on_window_changed)
            sesion.add_view_listener(herramienta.on_view_changed)
        # **Después de las herramientas**: la ocupación se reancla en su
        # `on_view_changed()`, y las bandas se comparan contra lo ya reanclado.
        sesion.add_view_listener(self._al_cambiar_la_pagina)

        self._aplicar_colores_de_clase(sesion)
        self.signal_view.set_session(sesion)
        self._reiniciar_paneles_de_analisis()
        self.channel_selector.set_recording(registro)
        self.scoring_panel.set_nomenclature(sesion.scoring.nomenclature)
        install_shortcuts(self, sesion)
        self._activate_panel_tools()
        # El eje del histograma en hora real sólo se puede pedir si el archivo
        # informó cuándo empezó: pedirlo igual sería un cartel de error cada
        # vez que se abre un registro sin hora, por una preferencia que el
        # usuario eligió para otros archivos.
        if self._preferencias.open_clock_axis and registro.start_time is not None:
            self.accion_eje_en_hora.setChecked(True)
        self.refresh()
        self._recordar_reciente(path)
        # **Lo que el lector pudo leer con reservas**, después de dibujar: el
        # registro ya está abierto y el cartel explica lo que se ve (hito 33).
        avisos = registro.metadata.get(IMPORT_WARNINGS_KEY)
        if avisos:
            self._mostrar_avisos_de_lectura([str(aviso) for aviso in avisos])

    def _recordar_reciente(self, path: Path) -> None:
        """Pone el registro recién abierto al frente de «Abrir reciente»."""
        try:
            ruta = str(Path(path).resolve())
        except OSError:
            ruta = str(path)
        self._preferencias = self._preferencias.with_recent_file(ruta)
        self._guardar_preferencias()
        rebuild_recent_menu(self)

    def open_recent_file(self, path: str) -> None:
        """Abre uno de «Abrir reciente».

        **Si ya no está, se lo saca de la lista** y se avisa: una entrada que
        falla cada vez que se elige no sirve de nada.
        """
        if not Path(path).exists():
            self._preferencias = self._preferencias.without_recent_file(path)
            self._guardar_preferencias()
            rebuild_recent_menu(self)
            self._show_error(
                PsgLabError(
                    f"«{Path(path).name}» ya no está donde se abrió la última vez, "
                    "así que se lo quitó de los recientes.",
                    details=f"No existe {path}.",
                ),
                f"abrir «{Path(path).name}»",
            )
            return
        self.open_recording(Path(path))

    # -- Vistas de canales (hito 64) ------------------------------------------

    def save_channel_view(self) -> None:
        """Guarda con un nombre los canales que se ven, su orden y su escala.

        Un nombre que ya existe se reemplaza: es «guardar», y volver a guardar
        la misma vista después de ajustarla es el uso normal.
        """
        if self._session is None:
            return
        visibles = self._session.visible_channels
        if not visibles:
            self._show_error(
                PsgLabError(
                    "No hay canales a la vista para guardar.",
                    details="La sesión no tiene canales visibles.",
                ),
                "guardar la vista",
            )
            return
        nombre, acepto = QInputDialog.getText(
            self, "Guardar la vista de canales", "Nombre de la vista:"
        )
        nombre = nombre.strip()
        if not acepto or not nombre:
            return
        canales = tuple((canal, self._session.scale_uv(canal)) for canal in visibles)
        try:
            self._preferencias = self._preferencias.with_channel_view(nombre, canales)
        except PsgLabError as error:
            self._show_error(error, "guardar la vista")
            return
        self._guardar_preferencias()
        rebuild_views_menu(self)
        self.statusBar().showMessage(f"Se guardó la vista «{nombre}»", 5000)

    def apply_channel_view(self, name: str) -> None:
        """Muestra los canales de una vista, en su orden y con su escala.

        **Los que este registro no tiene se saltean**, y se dice cuántos: una
        vista armada con otro montaje sirve igual para lo que coincide. Si no
        coincide ninguno, no se toca nada.
        """
        if self._session is None:
            return
        canales = self._preferencias.channel_view(name)
        if canales is None:
            return
        presentes = set(self._session.recording.channel_names())
        a_mostrar = [(canal, escala) for canal, escala in canales if canal in presentes]
        if not a_mostrar:
            self._show_error(
                PsgLabError(
                    f"Ninguno de los canales de la vista «{name}» está en este registro.",
                    details=f"canales de la vista: {[canal for canal, _ in canales]}",
                ),
                f"aplicar la vista «{name}»",
            )
            return
        nombres = [canal for canal, _ in a_mostrar]
        try:
            self._session.set_visible_channels(nombres)
            for canal, escala in a_mostrar:
                self._session.set_scale_uv(canal, escala)
        except PsgLabError as error:
            self._show_error(error, f"aplicar la vista «{name}»")
            return
        self.channel_selector.set_visible(nombres)
        self.signal_view.set_visible_channels(nombres)
        self._refrescar_contexto()
        self.refresh()
        faltan = len(canales) - len(a_mostrar)
        if faltan == 0:
            aviso = f"Vista «{name}»"
        elif faltan == 1:
            aviso = f"Vista «{name}»: un canal no está en este registro"
        else:
            aviso = f"Vista «{name}»: {faltan} canales no están en este registro"
        self.statusBar().showMessage(aviso, 5000)

    def delete_channel_view(self) -> None:
        """Pregunta qué vista borrar y la borra."""
        nombres = [nombre for nombre, _ in self._preferencias.channel_views]
        if not nombres:
            return
        nombre, acepto = QInputDialog.getItem(
            self, "Borrar una vista", "Vista a borrar:", nombres, 0, False
        )
        if not acepto or nombre not in nombres:
            return
        self._preferencias = self._preferencias.without_channel_view(nombre)
        self._guardar_preferencias()
        rebuild_views_menu(self)
        self.statusBar().showMessage(f"Se borró la vista «{nombre}»", 5000)

    def _mostrar_avisos_de_lectura(self, avisos: list[str]) -> None:
        """Muestra lo que el investigador tiene que saber del archivo que abrió.

        **No es `_show_error()`**: el registro se abrió y se puede trabajar con
        él, así que el cartel no dice "No se pudo completar la operación". Está
        aparte para que los tests lo contesten, porque es modal.

        **Que se abrió lo dice el texto y no el título** (hito 66): en macOS el
        título no se ve, y el aviso de las muestras sin valor no lo dice solo.
        """
        nombre = self._session.recording.file_path.name if self._session else ""
        cartel = QMessageBox(self)
        cartel.setIcon(QMessageBox.Icon.Warning)
        cartel.setWindowTitle(_TITULO_DE_LOS_CARTELES)
        cartel.setText(f"«{nombre}» se abrió, con avisos.")
        cartel.setInformativeText("\n\n".join(avisos))
        cartel.exec()

    def _reiniciar_paneles_de_analisis(self) -> None:
        """Deja los paneles de análisis como corresponden al registro recién abierto.

        **Seguían mostrando el anterior.** El espectro decía «Espectro de «C3»»
        sobre un registro sin C3; la métrica y la conectividad eran de otra
        señal; la tabla de impedancias listaba los canales viejos con el informe
        de los nuevos; y el panel de filtros conservaba los sugeridos del otro
        registro, así que en uno de 100 Hz «Aplicar» pedía el notch de 50 Hz.

        Los que muestran un resultado se vacían, porque recalcularlos es
        trabajo que nadie pidió. Los que muestran una configuración —filtros e
        impedancias— se cargan con la del registro nuevo, que no calcula nada.
        La ICA la olvida `_olvidar_ica()`.
        """
        self._olvidar_resultados()
        if self._session is not None:
            self.filter_panel.set_recording(self._session.recording)
        self._cargar_impedancias()

    def _olvidar_resultados(self) -> None:
        """Vacía el espectro, la métrica y la conectividad, con sus títulos.

        Se llama al abrir un registro y **cada vez que cambia la señal**:
        filtrar, derivar, re-referenciar, aplicar la ICA o volver a la
        original. Hasta el hito 30, después de filtrar el espectro seguía
        mostrando el de la señal sin filtrar, con el mismo título y sin decir
        nada. Es la misma regla que `_olvidar_ica()` aplica a la descomposición:
        un resultado de una señal que ya no está no se muestra como si fuera de
        ésta. Se vacía en vez de recalcularlo porque recalcular es trabajo que
        nadie pidió; el panel vacío dice desde dónde se vuelve a pedir.
        """
        self.psd_panel.clear_spectrum()
        self.psd_panel.clear_band_powers()
        self.metric_panel.clear_metric()
        self.connectivity_panel.clear_matrix()

    def open_scoring(self, path: Path) -> None:
        """Importa un scoring existente sobre el registro abierto (V3_F).

        Acepta los cuatro formatos de `SCORING_FORMATS`. **Si el archivo no
        dice con qué nomenclatura se scoreó, se le pregunta al usuario** y se
        vuelve a leer con la que elija; si cancela, no se importa nada.

        **Y si el scoring que está en pantalla no se exportó, se pregunta antes
        de pisarlo**, con el mismo cartel que al cerrar o abrir otro registro:
        importar lo reemplaza entero.
        """
        if self._session is None:
            self._show_error(
                PsgLabError(
                    "Hay que abrir un registro antes de importarle un scoring.",
                    details="No hay ninguna sesión abierta.",
                ),
                "importar el scoring",
            )
            return
        inicio = self._session.recording.start_time
        try:
            try:
                scoring = read_scoring(path, self._session.n_windows, start_time=inicio)
            except UndeclaredNomenclatureError:
                elegida = self._elegir_nomenclatura(path)
                if elegida is None:
                    return
                scoring = read_scoring(
                    path, self._session.n_windows, elegida, start_time=inicio
                )
            # **Lo que se perdería, antes de pisarlo** (hito 33). Importar
            # reemplaza el scoring entero, así que es la misma pérdida que
            # abrir otro registro por otro camino, y se pregunta igual:
            # después de leer, porque un archivo que no se puede importar no
            # pisa nada. Nada de lo que hace el cartel eleva hacia afuera
            # —`export()` atrapa lo suyo—, así que vive adentro de este `try`
            # sin cambiarle el sentido.
            if not self._puede_descartarse_el_trabajo(f"importar «{path.name}»"):
                return
            # **Se sustituye adentro de la sesión, no se arma otra.** Importar
            # un scoring no es abrir otro registro: el usuario sigue parado en
            # su ventana, con sus canales y sus amplitudes, y las herramientas
            # ya activadas siguen apuntando a la sesión correcta. El motivo
            # completo está en `Session.set_scoring()`.
            self._session.set_scoring(scoring)
        except PsgLabError as error:
            self._show_error(error, "importar el scoring")
            return

        self.scoring_panel.set_nomenclature(scoring.nomenclature)
        self._reload_histogram()
        self.refresh()

    def export(self, kind: str, path: Path) -> None:
        """Exporta uno de los tres archivos de salida (V4_F).

        El diálogo de guardado propone el nombre de archivo que fija el pliego,
        tomándolo de `psglab.exporters.DEFAULT_FILENAMES`.

        **Del menú sólo se pide el scoring**: Anotaciones.txt e
        Informacion.txt salieron de ahí el 16 de septiembre de 2026, pero este
        método los sigue escribiendo, y es la vía para pedirlos desde un
        script. Anotaciones.txt tiene además una puerta más en la ventana
        desde el cierre del hito 33: el cartel del trabajo sin exportar, que
        ofrece guardarlas antes de perderlas.

        Args:
            kind: "scoring", "annotations" o "information".
            path: el destino. Para el scoring, su extensión elige el formato:
                `.txt`, `.csv`, `.edf` o `.xml`.
        """
        if self._session is None:
            return
        try:
            if kind == "scoring":
                export_scoring_as(
                    self._session.scoring, path, self._session.recording.start_time
                )
                # Después de escribir y no antes: si falló, el trabajo sigue sin
                # estar en ningún archivo y cerrar tiene que seguir preguntando.
                self._session.mark_scoring_exported()
            elif kind == "annotations":
                export_annotations(self._session.annotations, path)
                # Por el mismo motivo que el scoring: recién cuando se escribió.
                self._session.mark_annotations_exported()
            elif kind == "information":
                export_information(
                    self._session.recording,
                    self._session.scoring,
                    self._session.annotations,
                    path,
                )
            else:
                raise PsgLabError(
                    "No se pudo exportar: no se reconoce ese archivo de salida.",
                    details=f"kind = {kind!r}, se esperaba uno de {sorted(DEFAULT_FILENAMES)}.",
                )
        except PsgLabError as error:
            self._show_error(error, f"exportar «{path.name}»")
            return
        except OSError as error:
            # **El disco no es un `PsgLabError`.** Los exportadores validan lo
            # suyo y elevan errores del programa, pero la carpeta que eligió el
            # usuario puede no existir, estar llena o ser de sólo lectura, y eso
            # sale como `OSError` crudo. Sin esta rama atraviesa el `except` de
            # arriba y el investigador ve una traza de Python en vez de un
            # cartel. Lo encontró `tests/test_entrega.py` exportando a una
            # carpeta inexistente.
            self._show_error(
                PsgLabError(
                    f"No se pudo escribir «{path.name}». Revisá que la carpeta "
                    "exista y que tengas permiso para escribir en ella.",
                    details=f"{type(error).__name__}: {error}",
                ),
                f"exportar «{path.name}»",
            )
            return
        self.statusBar().showMessage(f"Se exportó {path.name}", 5000)

    # -- El trabajo sin exportar (hito 33) ---------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cerrar la ventana es cerrar el programa: antes, el scoring sin exportar.

        Hasta el hito 33 no había este método y la ventana se cerraba sin
        preguntar nada, con la noche scoreada adentro. Si el usuario cancela,
        la ventana queda abierta como estaba, reproducción incluida.
        """
        if not self._puede_descartarse_el_trabajo("cerrar el programa"):
            event.ignore()
            return
        self.playback.stop()
        # **Antes de soltar la sesión.** Un cálculo largo todavía leyendo el
        # registro se quedaría trabajando sobre memoria que ya nadie tiene.
        self.wait_for_background()
        super().closeEvent(event)

    def _lo_que_se_perderia(self) -> list[str]:
        """Qué archivos de salida tienen trabajo que no está en ningún lado.

        Devuelve claves de `export()`, en el orden en que se ofrecen: primero
        el scoring, que es el trabajo principal.
        """
        if self._session is None:
            return []
        en_juego: list[str] = []
        if self._session.has_unexported_scoring():
            en_juego.append("scoring")
        if self._session.has_unexported_annotations():
            en_juego.append("annotations")
        return en_juego

    def _puede_descartarse_el_trabajo(self, al_hacer: str) -> bool:
        """Si se puede seguir sin perder trabajo que el usuario no exportó.

        **El programa no autoguarda**, por decisión del usuario en el hito 33:
        guardar a escondidas obliga a elegir dónde y en qué formato por él. Así
        que cuando algo va a soltar la sesión —cerrar, abrir otro registro,
        importar un scoring encima— y quedó trabajo fuera de todo archivo, se
        pregunta con tres salidas:

        - **Exportar…** abre el diálogo de guardado de **cada cosa en juego** y
          sigue sólo si no quedó nada sin exportar. Cancelar un diálogo, o que
          escribir falle, deja todo como estaba.
        - **Descartar** sigue y lo pierde, que es lo que el usuario eligió.
        - **Cancelar**, o cerrar el cartel, no hace nada.

        **Las anotaciones cuentan desde el cierre del hito 33.** El cartel
        miraba sólo el scoring, que es lo único que la ventana ofrece exportar
        desde el menú, así que una sesión con eventos anotados y ninguna fase
        puesta se cerraba sin preguntar. Que Anotaciones.txt no esté en el menú
        —decisión del hito 23, sin confirmar con el cliente— no puede
        significar que se pierda en silencio: el cartel las exporta, con el
        mismo diálogo que el scoring, porque avisar de una pérdida sin ofrecer
        cómo evitarla es peor que no avisar.

        Args:
            al_hacer: lo que se está por hacer, para el texto del cartel:
                "cerrar el programa", "abrir «noche.edf»",
                "importar «Scoring.txt»".
        """
        en_juego = self._lo_que_se_perderia()
        if not en_juego:
            return True
        respuesta = self._preguntar_por_el_trabajo(al_hacer, en_juego)
        if respuesta == "descartar":
            return True
        if respuesta == "exportar":
            for que in en_juego:
                self._export_dialog(que)
            return not self._lo_que_se_perderia()
        return False

    def _preguntar_por_el_trabajo(self, al_hacer: str, en_juego: list[str]) -> str:
        """Muestra el cartel y devuelve "exportar", "descartar" o "cancelar".

        Está aparte de la decisión para que los tests puedan contestarlo: el
        cartel es modal y, sin nadie que lo cierre, colgaría la suite.

        **Exportar es el botón por omisión y Escape es cancelar**: un Enter
        apurado no puede costar la noche, y apretar Escape es arrepentirse de
        cerrar, no de haber scoreado.

        **El texto nombra lo que está en juego**, que no siempre es lo mismo:
        decir "el scoring" sobre una sesión que sólo tiene anotaciones manda a
        buscar al lugar equivocado lo que se va a perder.
        """
        nombre = self._session.recording.file_path.name if self._session else ""
        anotaciones = len(self._session.annotations.all()) if self._session else 0
        que_hay = {
            ("scoring",): "El scoring",
            ("annotations",): f"Las {anotaciones} anotaciones",
            ("scoring", "annotations"): f"El scoring y las {anotaciones} anotaciones",
        }[tuple(en_juego)]
        cartel = QMessageBox(self)
        cartel.setIcon(QMessageBox.Icon.Warning)
        cartel.setWindowTitle("Trabajo sin exportar")
        cartel.setText(f"{que_hay} de «{nombre}» no se exportaron.")
        cartel.setInformativeText(
            f"Si no los exportás, se pierden al {al_hacer}. ¿Exportarlos antes?"
        )
        exportar = cartel.addButton("Exportar…", QMessageBox.ButtonRole.AcceptRole)
        # Lo que el cartel recomienda, relleno del acento (hito 55).
        exportar.setProperty(theme.PRIMARIO_PROPERTY, True)
        descartar = cartel.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        # **El rol no alcanza para que se vea distinto.** `DestructiveRole` le
        # dice a Qt dónde ubicar el botón y con qué tecla responde, no de qué
        # color pintarlo: en Windows sale idéntico a «Cancelar». La tinta la
        # pone el esquema por esta propiedad. La llevan sólo los dos controles
        # que pierden trabajo: éste y «Borrar» una anotación (`_confirmar()`).
        descartar.setProperty(theme.DESTRUCTIVO_PROPERTY, True)
        cancelar = cartel.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cartel.setDefaultButton(exportar)
        cartel.setEscapeButton(cancelar)
        cartel.exec()
        elegido = cartel.clickedButton()
        if elegido is exportar:
            return "exportar"
        if elegido is descartar:
            return "descartar"
        return "cancelar"

    def refresh(self) -> None:
        """Redibuja todos los paneles a partir del estado de la sesión.

        Se llama después de cualquier cambio: navegar, scorear, anotar o
        cambiar la amplitud.
        """
        if self._session is None:
            return
        self.signal_view.show_window(self._session.current_window)
        self.channel_selector.set_visible(self._session.visible_channels)
        self._refrescar_contexto()
        self._reflejar_epoca()
        # Cambiar de época puede mover la página, así que el cartel de la
        # página se recalcula también acá y no sólo al desplazar.
        self._actualizar_cartel_de_pagina()

    def _reflejar_epoca(self) -> None:
        """Pone al día todo lo que depende de la época actual, **sin mover la
        página**: la banda, la posición y la hora de la barra, el pie del
        scoring, el hipnograma y la barra de estado.

        Es la mitad de `refresh()` que la reproducción necesita sola. Desde el
        hito 27 la época cambia mientras se reproduce —es la que pasa por el
        medio del gráfico—, y el paso ya dibujó la página: llamar a `refresh()`
        la dibujaría otra vez.
        """
        if self._session is None:
            return
        sesion = self._session
        ventana = sesion.current_window

        self.signal_view.mark_window(ventana)
        self.navigation.set_position(ventana, sesion.n_windows)
        self.navigation.set_clock_time(self._clock_label(ventana))
        # Los extremos no cambian con la época, pero esto es lo que corre
        # después de abrir un registro **y** después de cambiar de canales
        # visibles, que es cuando pueden dejar de ser ciertos.
        self.navigation.set_span(*self._horas_del_registro())
        self._escribir_el_identificador()
        epoca = sesion.scoring.get(ventana)
        self.scoring_panel.set_current(epoca.stage, epoca.arousal, ventana)
        self._redraw_histogram()
        # La época actual, también sobre la curva de la métrica (hito 54).
        self.metric_panel.set_current_window(ventana)
        self.statusBar().showMessage(
            f"Ventana {ventana + 1} de {sesion.n_windows}"
            + (f" — {self._clock_label(ventana)}" if self._clock_label(ventana) else "")
        )

    # -- Escala de tiempo ---------------------------------------------------
    #
    # Todas cambian la página visible y ninguna toca la época: el scoring sigue
    # siendo por ventana de 30 s. Las seis pasan por `Session.set_viewport()`,
    # que es el único lugar que avisa a las herramientas.

    def _cambiar_pagina(self, nueva: object, avisar: bool = True) -> bool:
        """Aplica una página nueva y redibuja, o avisa si no se puede.

        Está separado porque las seis operaciones de abajo hacen exactamente lo
        mismo con una transformación distinta, y repetir el `try` en cada una
        garantiza que alguna se olvide de atraparlo.

        Args:
            avisar: si una página grande muestra el cursor de espera. La
                reproducción lo apaga: veinticinco pasos por segundo lo harían
                parpadear.

        Returns:
            Si la página se pudo aplicar.
        """
        if self._session is None:
            return False
        try:
            self._session.set_viewport(nueva)
        except PsgLabError as error:
            self._show_error(error, "cambiar la escala de tiempo")
            return False
        # **Una página larga se calcula una vez y después vuelve de la caché.**
        # Sobre el registro de prueba de 22 horas el primer dibujo del registro
        # entero tarda 444 ms y los siguientes 14 ms; con 32 canales a 1000 Hz
        # el primero se va a varios segundos. Esa espera no se acorta acá: se
        # vuelve legible, que es lo que hace el cursor.
        muestras = (
            self._session.viewport.span_seconds
            * self._session.recording.sampling_rate
            * len(self._session.visible_channels)
        )
        if avisar and muestras > _MUESTRAS_PARA_AVISAR:
            with self._trabajando("Dibujando la página"):
                self.signal_view.draw_viewport()
        else:
            self.signal_view.draw_viewport()
        self._actualizar_cartel_de_pagina()
        return True

    def set_timescale(self, seconds: float) -> None:
        """Le da a la página una duración concreta, conservando el centro."""
        if self._session is None:
            return
        self._cambiar_pagina(self._session.viewport.with_span(seconds))

    def halve_timescale(self) -> None:
        """Acerca: la página pasa a durar la mitad."""
        if self._session is None:
            return
        self._cambiar_pagina(self._session.viewport.zoomed(1 / VIEW_ZOOM_FACTOR))

    def double_timescale(self) -> None:
        """Aleja: la página pasa a durar el doble."""
        if self._session is None:
            return
        self._cambiar_pagina(self._session.viewport.zoomed(VIEW_ZOOM_FACTOR))

    def show_whole_recording(self) -> None:
        """Muestra el registro entero de una vez."""
        if self._session is None:
            return
        self._cambiar_pagina(self._session.viewport.whole_recording())

    def ask_timescale(self) -> None:
        """Pregunta cuántos segundos por página. Es «Escala de tiempo ▸ Personalizado…»."""
        if self._session is None:
            return
        actual = self._session.viewport.span_seconds
        valor, aceptado = QInputDialog.getDouble(
            self,
            "Escala de tiempo",
            "Segundos por página:",
            actual,
            MIN_VIEW_SECONDS,
            self._session.recording.duration_seconds,
            3,
        )
        if aceptado:
            self.set_timescale(valor)

    def pan_view_left(self) -> None:
        """Desplaza media página hacia atrás."""
        self._desplazar(-VIEW_PAN_FRACTION)

    def pan_view_right(self) -> None:
        """Desplaza media página hacia adelante."""
        self._desplazar(VIEW_PAN_FRACTION)

    def pan_view_page_left(self) -> None:
        """Desplaza una página entera hacia atrás."""
        self._desplazar(-1.0)

    def pan_view_page_right(self) -> None:
        """Desplaza una página entera hacia adelante."""
        self._desplazar(1.0)

    def _desplazar(self, fraccion_de_pagina: float) -> None:
        """Mueve la página esa fracción de su propio ancho.

        **En fracciones y no en segundos fijos**: con una página de 200 ms un
        salto de 15 s la sacaría del registro visible, y con una de cuatro horas
        no se notaría. Lo que el usuario espera es avanzar "un pedazo de lo que
        estoy viendo".
        """
        if self._session is None:
            return
        pagina = self._session.viewport
        desplazamiento = fraccion_de_pagina * pagina.span_seconds
        # **Reproduciendo se mueve el cursor**, lo mismo que se movería la
        # página: si se moviera sólo la página, el paso siguiente la devolvería
        # al cursor. Así la vista y el cursor van juntos y la reproducción
        # sigue desde ahí.
        if self._cabezal is not None:
            self._llevar_el_cursor(self._cabezal + desplazamiento)
            return
        self._cambiar_pagina(pagina.panned(desplazamiento))

    def _actualizar_cartel_de_pagina(self) -> None:
        """Escribe en la barra de estado cuánto dura la página.

        **La barra sigue diciendo "Ventana N de M", que habla de la época.** El
        cartel de la página es un widget aparte: son dos datos distintos y
        mezclarlos haría ilegible el único que el pliego pide.
        """
        if self._session is None:
            self.page_readout.setText("")
            return
        pagina = self._session.viewport
        if pagina.shows_whole_recording:
            self.page_readout.setText("Página: registro entero")
            return
        self.page_readout.setText(f"Página: {duration_text(pagina.span_seconds)}")

    # -- Reproducción (hitos 24 y 27) ----------------------------------------
    #
    # La página avanza sola, como en EDFbrowser. **Desde el hito 27 el recorrido
    # se cuenta desde el medio del gráfico**: un cursor, `_cabezal`, marca el
    # instante que se está reproduciendo, la página se centra en él y la época
    # actual es la suya. Al pausar, el usuario queda parado en la época que
    # estaba mirando y la scorea ahí.
    #
    # Hasta ese hito era al revés, por decisión del hito 24: reproducir sólo
    # movía la vista, igual que Mayús+→, y la época no se tocaba. El usuario la
    # revisó el 18 de septiembre de 2026. En pausa todo sigue como antes: las
    # flechas mueven la página lo mínimo (`Session._seguir_a_la_epoca()`).

    def toggle_playback(self) -> None:
        """Reproduce o pausa. Es el botón ⏯ y Espacio con el foco en la señal.

        **Arranca desde el centro de la época actual**, que es la que se está
        scoreando. Con la página de 30 s ya está centrada, así que no hay
        salto; después de «Primera ventana» el cursor arranca cerca del borde
        izquierdo y la página no se mueve hasta que el cursor llega al medio.

        Ya no se niega con la página al final ni con el registro entero en
        pantalla, como hasta el hito 27: el cursor avanza adentro de la página
        cuando ésta no se puede mover, así que siempre hay por dónde seguir.
        """
        if self.playback.is_playing:
            self.playback.stop()
            return
        if self._session is None:
            return
        inicio, fin = epoch_to_seconds(
            self._session.current_window, self._session.recording.sampling_rate
        )
        if not self._llevar_el_cursor((inicio + fin) / 2):
            return
        self.playback.start()

    def _avanzar_reproduccion(self, segundos: float) -> None:
        """Un paso de la reproducción: el cursor avanza esos segundos.

        Se detiene al llegar al final **del registro**, no de la página: en el
        último tramo la página ya no se mueve y el cursor sigue hasta el borde,
        que es lo que recorre las últimas épocas. También se detiene si el
        cursor no se pudo ubicar: un error repetido veinticinco veces por
        segundo sería un cartel tras otro.
        """
        if self._session is None:
            self.playback.stop()
            return
        # Un paso sin cursor —el banco de medición los pide sin arrancar la
        # reproducción— parte del medio de lo que se ve.
        desde = (
            self._cabezal
            if self._cabezal is not None
            else self._session.viewport.center_seconds
        )
        if not self._llevar_el_cursor(desde + segundos):
            self.playback.stop()
            return
        if self._cabezal is not None and (
            self._cabezal >= self._session.recording.duration_seconds
        ):
            self.playback.stop()
            self.statusBar().showMessage("Fin del registro", 5000)

    def _llevar_el_cursor(self, segundos: float) -> bool:
        """Pone el cursor en ese instante y deja la pantalla al día.

        La regla —la página centrada en el cursor, la época la del cursor— es
        de `Session.move_playhead()`. Acá sólo se redibuja lo que cambió: la
        página si se movió, la línea siempre, y lo que depende de la época si la
        época cambió, que pasa una vez cada 30 s de registro.

        Returns:
            Si el cursor se pudo ubicar.
        """
        if self._session is None:
            return False
        pagina = self._session.viewport
        epoca = self._session.current_window
        try:
            self._cabezal = self._session.move_playhead(segundos)
        except PsgLabError as error:
            self._show_error(error, "mover la reproducción")
            return False
        if self._session.viewport != pagina:
            self.signal_view.draw_viewport()
        self.signal_view.set_playhead(self._cabezal)
        if self._session.current_window != epoca:
            self._reflejar_epoca()
        return True

    def _saltar_con_el_cursor(self, window_index: int) -> None:
        """Reproduciendo, ir a una época es llevar el cursor a su centro, y la
        reproducción sigue desde ahí (hito 27).

        Una época que no existe se ignora, como la flecha en los bordes: la
        piden los botones, la franja y el hipnograma, que ya recortan contra el
        registro, y llevar el cursor al final por un índice de más detendría la
        reproducción sin que el usuario lo hubiera pedido.
        """
        if self._session is None or not 0 <= window_index < self._session.n_windows:
            return
        inicio, fin = epoch_to_seconds(window_index, self._session.recording.sampling_rate)
        self._llevar_el_cursor((inicio + fin) / 2)

    def _al_cambiar_la_reproduccion(self, reproduciendo: bool) -> None:
        """El botón muestra reproducir o pausar, y al pausar se va el cursor.

        La banda de la época queda como referencia: es lo que se scorea, y
        desde el hito 27 es la época que pasaba por el medio al pausar.
        """
        self.navigation.set_playing(reproduciendo)
        if not reproduciendo:
            self._cabezal = None
            self.signal_view.set_playhead(None)

    def _cambiar_velocidad(self, velocidad: float) -> None:
        """Lo que pide el selector de velocidad. Vale también reproduciendo."""
        try:
            self.playback.speed = velocidad
        except PsgLabError as error:
            self._show_error(error, "cambiar la velocidad")

    # -- Amplitud (V2_P, V5_F) ----------------------------------------------
    #
    # Las cinco entran por el menú «Amplitud» y todas comparten el alcance que
    # ya resolvía `Session._channels_under_amplitude()`: los canales
    # seleccionados, o todos los visibles si no hay ninguno seleccionado. No se
    # reimplementa acá, que es lo que haría que las flechas y el menú pudieran
    # discrepar.

    def fit_amplitude_to_pane(self) -> None:
        """Ajusta la escala para que la señal de cada canal entre en su carril."""
        if self._session is None:
            return
        try:
            self._session.fit_to_pane()
        except PsgLabError as error:
            self._show_error(error, "cambiar la amplitud")
            return
        self.refresh()

    def center_amplitude_offsets(self) -> None:
        """Apoya cada canal en el centro de su carril."""
        if self._session is None:
            return
        try:
            self._session.center_offsets()
        except PsgLabError as error:
            self._show_error(error, "cambiar la amplitud")
            return
        self.refresh()

    def reset_amplitude_offsets(self) -> None:
        """Devuelve al cero el desplazamiento vertical de los canales."""
        if self._session is None:
            return
        try:
            self._session.reset_offsets()
        except PsgLabError as error:
            self._show_error(error, "cambiar la amplitud")
            return
        self.refresh()

    def set_amplitude_scale(self, scale_uv: float) -> None:
        """Le da la misma escala a todos los canales bajo amplitud.

        **El menú habla de µV por carril y no de "amplitud"**, que es el número
        que `Session` guarda. Decir "amplitud 100" y escribir `scale_uv = 100`
        haría lo contrario de lo que el usuario espera la mitad de las veces:
        subir `scale_uv` **achica** la onda, porque es cuántos µV representa la
        altura del carril.
        """
        if self._session is None:
            return
        try:
            for nombre in self._session.visible_channels:
                if nombre in self._session.selected_channels or not self._session.selected_channels:
                    self._session.set_scale_uv(nombre, scale_uv)
        except PsgLabError as error:
            self._show_error(error, "cambiar la amplitud")
            return
        self.refresh()

    def ask_amplitude_scale(self) -> None:
        """Pregunta la escala y la aplica. Es «Amplitud ▸ Personalizado…»."""
        if self._session is None:
            return
        actual = self._session.scale_uv(self._session.visible_channels[0])
        valor, aceptado = QInputDialog.getDouble(
            self,
            "Amplitud",
            "Microvoltios por carril:",
            actual,
            MIN_SCALE_UV,
            MAX_SCALE_UV,
            1,
        )
        if not aceptado:
            return
        self.set_amplitude_scale(valor)

    def reset_magnifier_count(self) -> None:
        """Pone en cero el contador de picos de la lupa (V2_F de la Lupa).

        `MagnifierTool.reset_count()` existía y ningún menú lo llamaba, aunque
        la lupa prometía que para eso estaba: la cuenta sólo se podía perder
        cerrando el programa (hito 32).
        """
        lupa = self._tools.get("magnifier")
        if isinstance(lupa, MagnifierTool):
            lupa.reset_count()
            self._update_tool_readout()

    def restore_default_layout(self) -> None:
        """Vuelve a la disposición de paneles con la que el programa abre.

        Es la salida cuando alguien arrastró un panel a un lugar del que no
        sabe cómo sacarlo, que con nueve paneles acoplables deja de ser
        hipotético. Es la misma vista de cada apertura: la señal y el selector
        de canales.
        """
        self.restoreState(self._layout_por_defecto)

    def apply_saved_preferences(self) -> None:
        """Aplica las preferencias que el usuario dejó la última vez.

        **Sólo la llama `create_main_window(saved_preferences=True)`**, que
        sólo llama `main.py`. Si la llamara el constructor, la suite de tests
        leería —y después escribiría— el archivo real de quien la corre, y
        dejaría de ser reproducible. Por el mismo motivo marca la ventana como
        la del usuario, que es la única que escribe el archivo.

        **La disposición de paneles no se restaura.** Hasta el hito 24 se
        guardaba al cerrar y volvía al abrir; desde entonces el programa abre
        siempre con la vista de fábrica, por decisión del usuario.

        No eleva: unas preferencias que no se pueden leer se descartan y la
        ventana abre con las de fábrica. **Pero lo dice** (hito 33): `load()`
        arma el mensaje para el investigador y hasta ahí nadie lo mostraba, así
        que un archivo roto se perdía sin aviso la primera vez que se cambiaba
        algo. El cartel sale en la vuelta siguiente del ciclo de eventos, con la
        ventana ya a la vista y no delante de una ventana que todavía no existe.
        """
        self._es_la_ventana_del_usuario = True
        try:
            guardadas = preferences.load()
        except PsgLabError as error:
            # En otra variable: Python borra `error` al salir del `except`, y el
            # cartel se arma recién en la vuelta siguiente del ciclo de eventos.
            aviso = error
            QTimer.singleShot(
                0, lambda: self._show_error(aviso, "leer la configuración guardada")
            )
            return
        # El esquema ya lo aplicó `create_application()`; lo demás de la
        # ventana de configuración se aplica acá, que es el único lugar donde
        # las preferencias del disco entran a la ventana.
        self._preferencias = guardadas
        self._aplicar_preferencias(guardadas)
        # Los recientes y las vistas salen de las preferencias: el menú se armó
        # con las de fábrica, antes de leer el archivo.
        rebuild_recent_menu(self)
        rebuild_views_menu(self)

    def set_color_scheme(self, scheme: theme.ColorScheme, remember: bool = True) -> None:
        """Cambia el esquema de color de todo el programa y lo deja repintado.

        `pg.setConfigOption()` sólo alcanza a los `PlotWidget` que se creen
        después, así que hay que recorrer los que ya existen. Se los busca con
        `findChildren()` y no con una lista escrita a mano **por la misma razón
        de siempre**: un panel nuevo se agregaría a la lista sólo si alguien se
        acuerda, y el síntoma de olvidarse sería un panel con el fondo del
        esquema anterior, que nadie va a asociar con este método.

        Args:
            scheme: el esquema a aplicar.
            remember: si se guarda como preferencia del usuario. Los tests lo
                apagan para no escribir en el archivo real de quien los corre,
                que los volvería dependientes de la máquina.

        No eleva: si las preferencias no se pueden guardar, el esquema se aplica
        igual y el problema sale como cartel. Perder la preferencia es molesto;
        no poder cambiar de colores porque el disco está lleno, absurdo.
        """
        theme.set_current(scheme)

        # La hoja de estilo alcanza a los widgets de Qt —menús, botones, el
        # árbol de canales, las tablas—, que los `PlotWidget` no tocan. Sin
        # esto, un esquema oscuro deja la ventana a dos colores.
        self.setStyleSheet(theme.stylesheet(scheme))

        for grafico in self.findChildren(pg.PlotWidget):
            grafico.setBackground(scheme.background)
        self.signal_view.apply_scheme()
        self.navigation.apply_scheme()
        self.open_button.setIcon(icon("abrir", theme.icon_ink(scheme)))
        # La señal de la Übersicht toma el color de su canal, que cambia con el
        # esquema: no alcanza con repintar.
        self._refrescar_contexto()
        self.overview_panel.update()
        self._redraw_histogram()
        # **La tilde del menú, cuando el esquema no vino del menú**: lo elige
        # también el archivo de preferencias al arrancar, y desde el hito 35 el
        # menú «Ver» es el único lugar donde se ve cuál está puesto.
        accion = self.acciones_de_esquema.get(scheme.name)
        if accion is not None and not accion.isChecked():
            accion.setChecked(True)

        self._preferencias = self._preferencias.with_scheme(scheme)
        if remember:
            self._guardar_preferencias()

    def _guardar_preferencias(self) -> None:
        """Escribe las preferencias vigentes, si esta ventana es la del usuario.

        **Sólo escribe si la ventana la abrió `main.py`**, que es lo que marca
        `apply_saved_preferences()`. Antes cada cambio de esquema leía el archivo,
        lo modificaba y lo volvía a escribir, sin mirar quién había creado la
        ventana: un test que eligiera un esquema desde el menú pisaba las
        preferencias reales de quien corría la suite.

        No eleva: si no se puede escribir, el cambio se aplica igual y el
        problema sale como cartel.
        """
        if not self._es_la_ventana_del_usuario:
            return
        try:
            preferences.save(self._preferencias)
        except PsgLabError as error:
            self._show_error(error, "guardar la configuración")

    @property
    def current_preferences(self) -> preferences.Preferences:
        """Las preferencias con las que está funcionando la ventana."""
        return self._preferencias

    def apply_preferences(self, prefs: preferences.Preferences) -> None:
        """Aplica unas preferencias nuevas a todo el programa y las recuerda.

        Es lo que llama la ventana de configuración en cada cambio. **Aplica
        todo sin reabrir el registro**: colores, grilla, tipografía, espectro y
        colores de las clases de evento se ven enseguida. Lo de la solapa
        «Otras» se guarda para el próximo registro que se abra.

        Muestra un cartel en vez de elevar si lo que llega no son preferencias:
        esto lo llama un panel, y una traza ahí es lo que el programa promete
        no mostrar nunca.
        """
        if not isinstance(prefs, preferences.Preferences):
            self._show_error(
                PsgLabError(
                    "No se pudo aplicar la configuración.",
                    details=f"Se recibió {type(prefs).__name__} en vez de preferencias.",
                ),
                "aplicar la configuración",
            )
            return
        esquema = prefs.scheme()
        if esquema != theme.current():
            self.set_color_scheme(esquema, remember=False)
        self._preferencias = prefs
        self._aplicar_preferencias(prefs)
        if self._session is not None:
            self._aplicar_colores_de_clase(self._session)
            self._repintar_anotaciones()
        self._guardar_preferencias()

    def focusable_panes(self) -> list[QWidget]:
        """Lo que se recorre con F6: la señal y los paneles abiertos que pueden
        recibir el foco.

        En el orden en que se arman los paneles, que es el de la pantalla: el
        trabajo de scoring primero y los análisis después.

        **Un panel que no tiene nada que pueda recibir el foco no se recorre.**
        El de contexto se pinta a mano y no tiene controles: incluirlo hacía que
        F6 lo diera por visitado mientras el foco seguía en el panel anterior,
        que es la peor combinación para quien navega sin mouse.
        """
        paneles: list[QWidget] = [self.signal_view]
        paneles += [
            dock
            for dock in self.docks.values()
            if not dock.isHidden() and _primero_que_toma_foco(dock.widget()) is not None
        ]
        return paneles

    def current_pane(self) -> QWidget:
        """El panel que tiene el foco del recorrido con F6."""
        paneles = self.focusable_panes()
        return paneles[self._panel_actual % len(paneles)]

    def focus_next_pane(self) -> None:
        """F6: pasa el foco al panel siguiente."""
        self._pasar_de_panel(1)

    def focus_previous_pane(self) -> None:
        """Mayús+F6: vuelve al panel anterior."""
        self._pasar_de_panel(-1)

    def _pasar_de_panel(self, paso: int) -> None:
        """Mueve el foco al panel que está `paso` lugares más allá, en círculo.

        Si el panel está apilado detrás de otro en solapas, se lo trae adelante:
        dejar el foco en algo que no se ve es peor que no moverlo.
        """
        paneles = self.focusable_panes()
        actual = self._panel_actual % len(paneles)
        self._panel_actual = (actual + paso) % len(paneles)
        panel = paneles[self._panel_actual]
        panel.raise_()
        destino = panel.widget() if isinstance(panel, QDockWidget) else panel
        candidato = _primero_que_toma_foco(destino)
        if candidato is not None:
            candidato.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def show_settings_dialog(self) -> None:
        """Abre la ventana de configuración, mostrando lo que está vigente.

        Se arma una sola vez y se la vuelve a llenar en cada apertura: lo que
        muestra tiene que ser lo que el programa está usando, que puede haber
        cambiado desde otro lado desde la última vez que se abrió.

        **Es modal pero no bloquea**: se muestra con `show()` y no con
        `exec()`, así que los cambios se ven detrás mientras se eligen, que es
        lo que hace útil aplicar en el momento.
        """
        colores = self._colores_de_clase_vigentes()
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self._preferencias, colores, self)
            self.settings_dialog.setModal(True)
            self.settings_dialog.on_change = self.apply_preferences
            self.settings_dialog.on_error = lambda error: self._show_error(
                error, "aplicar la configuración"
            )
        else:
            self.settings_dialog.set_preferences(self._preferencias, colores)
        self.settings_dialog.show()
        self.settings_dialog.raise_()

    def _colores_de_clase_vigentes(self) -> dict[str, str]:
        """Las clases de evento que hay para configurar, con su color de hoy.

        Con un registro abierto son las de su sesión, incluidas las que creó el
        usuario; sin él, las de fábrica, con los colores que tendrían.
        """
        conjunto = (
            self._session.annotations if self._session is not None else AnnotationSet()
        )
        return {clase: conjunto.color_of(clase) for clase in conjunto.labels()}

    def _aplicar_preferencias(self, prefs: preferences.Preferences) -> None:
        """Lo que se aplica enseguida y no depende de un registro abierto."""
        fuente = QFont(self._fuente_del_sistema)
        # **La familia ya no se elige** (hito 43): es la del programa y nada
        # más. Se pide sólo si Qt la tiene, porque un archivo que falta o que
        # no se pudo registrar dejaría a `setFamily()` sustituyendo en silencio
        # por lo que a Qt le parezca, que suele ser peor que la del sistema.
        elegida = fonts.available_family()
        if elegida is not None:
            fuente.setFamily(elegida)
        if prefs.font_size is not None:
            fuente.setPointSize(prefs.font_size)
        # **Sólo si cambió.** Cambiar la tipografía de la aplicación le avisa a
        # cada widget de cada ventana abierta, y la configuración se aplica
        # entera en cada cambio: sin esta guarda, tocar el color de una clase
        # le pediría al programa entero que volviera a maquetarse.
        if fuente != QApplication.font():
            QApplication.setFont(fuente)
        # Los nombres de canal son ítems de pyqtgraph, que no siguen a la
        # tipografía de la aplicación: hay que avisarles.
        self.signal_view.apply_font(fuente)
        self.psd_panel.set_log_power(prefs.psd_log_power)
        # V3_F de la Übersicht. `set_span()` estuvo sin ningún camino desde la
        # ventana hasta el hito 30: la cantidad sólo se cambiaba en `config.py`.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.set_span(prefs.overview_before, prefs.overview_after)
        # Hito 32: los tres `set_*` tampoco tenían ningún camino desde la ventana.
        banda = self._tools.get("amplitude_band")
        if isinstance(banda, AmplitudeBandTool):
            banda.set_height_uv(prefs.amplitude_band_uv)
        lupa = self._tools.get("magnifier")
        if isinstance(lupa, MagnifierTool):
            lupa.set_radius_seconds(prefs.magnifier_radius_seconds)
            lupa.set_zoom(prefs.magnifier_zoom)

    def _aplicar_colores_de_clase(self, sesion: Session) -> None:
        """Pone en la sesión los colores que el usuario eligió por clase.

        **Una clase con color guardado queda disponible en cualquier
        registro**, aunque ese registro todavía no la tenga: `add_label()` la
        registra si no existía. Es lo que el usuario espera de una clase que
        definió una vez; no cambia ningún archivo de salida, porque los
        exportadores escriben anotaciones y no clases.
        """
        for clase, color in self._preferencias.annotation_colors:
            try:
                sesion.annotations.add_label(clase, color)
            except PsgLabError as error:
                self._show_error(error, "aplicar los colores de las clases")
                return

    def _repintar_anotaciones(self) -> None:
        """Vuelve a dibujar lo que muestra el color de una clase."""
        #  le avisa a la ventana por su callback, que es el que
        # repinta el panel: no hace falta llamarlo a mano.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        # Las bandas llevan el color de su clase.
        self._redibujar_overlays()

    @property
    def session(self) -> Session | None:
        """Sesión de trabajo actual, o None si no hay registro abierto."""
        return self._session

    # -- Lo que ejecutan los atajos de teclado ------------------------------

    def go_to_next_window(self) -> None:
        """Flecha derecha. Reproduciendo, lleva el cursor a la época siguiente."""
        if self._session is None:
            return
        if self._cabezal is not None:
            self._saltar_con_el_cursor(self._session.current_window + 1)
            return
        self._session.next_window()
        self.refresh()

    def go_to_previous_window(self) -> None:
        """Flecha izquierda. Reproduciendo, lleva el cursor a la época anterior."""
        if self._session is None:
            return
        if self._cabezal is not None:
            self._saltar_con_el_cursor(self._session.current_window - 1)
            return
        self._session.previous_window()
        self.refresh()

    # **Llegar a cualquier ventana sin mouse** (hito 62). Hasta acá sólo lo
    # hacían los clics en la franja, el hipnograma y la Übersicht, y con el
    # teclado la ventana 500 de una noche eran 500 flechas.

    def go_to_first_window(self) -> None:
        """Inicio: la primera ventana."""
        if self._session is not None:
            self._go_to_window(0)

    def go_to_last_window(self) -> None:
        """Fin: la última ventana."""
        if self._session is not None:
            self._go_to_window(self._session.n_windows - 1)

    def ask_window(self) -> None:
        """Ctrl+G: pregunta a qué ventana ir, contando desde uno como la
        barra de estado."""
        if self._session is None:
            return
        total = self._session.n_windows
        numero, acepto = QInputDialog.getInt(
            self,
            "Ir a una ventana",
            f"Ventana (1 a {total}):",
            self._session.current_window + 1,
            1,
            total,
        )
        if acepto:
            self._go_to_window(numero - 1)

    def increase_amplitude(self) -> None:
        """Flecha arriba. La cuenta la hace `Session`."""
        self.signal_view.increase_amplitude()
        self._refrescar_contexto()

    def decrease_amplitude(self) -> None:
        """Flecha abajo."""
        self.signal_view.decrease_amplitude()
        self._refrescar_contexto()

    def toggle_arousal(self) -> None:
        """Tecla A: marca o desmarca el arousal de la ventana actual (V2_F)."""
        if self._session is None:
            return
        ventana = self._session.current_window
        actual = self._session.scoring.get(ventana).arousal
        self._set_arousal(not actual)

    def score_current_window(self, stage: SleepStage) -> None:
        """Asigna una fase a la ventana actual (V1_F de "Scoring")."""
        if self._session is None:
            return
        try:
            self._session.scoring.set_stage(self._session.current_window, stage)
        except PsgLabError as error:
            self._show_error(error, "scorear la ventana")
            return
        self._update_histogram_window(self._session.current_window)
        # **La Übersicht cachea sus ventanas** y las rearma al cambiar de
        # época, no al scorear: sin esto, el chip de la fase recién puesta no
        # aparecía hasta la próxima flecha. Es lo mismo que ya hacía anotar, y
        # por el mismo motivo.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        # **Pasa sola a la ventana siguiente** (hito 64), salvo en la última y
        # mientras se reproduce: ahí la época la lleva el cursor, y saltar
        # adelantaría la reproducción una ventana por cada tecla.
        if (
            self._preferencias.advance_after_scoring
            and self._cabezal is None
            and self._session.current_window < self._session.n_windows - 1
        ):
            self.go_to_next_window()
            return
        self.refresh()

    # -- Las esperas largas --------------------------------------------------

    def _en_segundo_plano(
        self,
        que_hace: str,
        trabajo: "Callable[[], object]",
        al_terminar: "Callable[[object], None]",
        accion: str | None = None,
    ) -> None:
        """Corre algo largo en otro hilo y dibuja el resultado cuando vuelve.

        Es la versión que no congela la ventana de `_trabajando()`, y la
        diferencia que se ve es que **la barra de progreso se mueve**: mientras
        el cálculo dura, el programa repinta, se puede arrastrar y el sistema
        no lo marca como «no responde».

        **La barra es indeterminada a propósito.** Ni `connectivity_by_window()`
        ni la ICA informan cuánto llevan hechas, así que un porcentaje sería
        inventado. Una barra que se mueve sin decir cuánto falta es honesta;
        una que dice 62 % sin saberlo, no.

        Args:
            que_hace: lo que se lee en la barra de estado, sin los puntos
                suspensivos.
            trabajo: lo que se calcula. **Corre en otro hilo**, así que no
                puede tocar widgets ni `Session`: lo que necesite de la sesión
                hay que resolverlo antes de llamar acá.
            al_terminar: qué hacer con el resultado. Corre en el hilo de la
                interfaz y sí puede dibujar.
            accion: qué no se pudo hacer si falla, para la primera línea del
                cartel; ver `_show_error()`.
        """
        self.statusBar().showMessage(f"{que_hace}…")
        self._barra_de_espera.show()

        # **La señal sobre la que se pidió** (hito 67). «Abrir» sigue
        # habilitado mientras el otro hilo trabaja, y lo que vuelve después de
        # abrir otro registro es de la señal anterior: la ICA de la noche A se
        # mostraba como la de B, y «Aplicar y quitar» la usaba sobre B sin
        # avisar cuando los dos tenían los mismos canales, que es lo normal
        # entre dos noches del mismo laboratorio. Se compara por identidad, como
        # `signal_view` con sus envolventes: un filtro o una derivación también
        # son otra señal.
        pedido_sobre = self._session.recording if self._session is not None else None

        def de_otra_senal() -> bool:
            if self._session is not None and self._session.recording is pedido_sobre:
                return False
            self.statusBar().showMessage(
                "Se descartó un cálculo que era de la señal anterior.", 8000
            )
            return True

        def listo(resultado: object) -> None:
            self._terminar_la_espera(que_hace)
            if de_otra_senal():
                return
            al_terminar(resultado)

        def falló(error: object) -> None:
            self._terminar_la_espera(que_hace)
            # Un error de la señal anterior tampoco se muestra: habla de algo
            # que ya no está en pantalla.
            if de_otra_senal():
                return
            if isinstance(error, PsgLabError):
                self._show_error(error, accion)

        self._tarea.finished.connect(listo)
        self._tarea.failed.connect(falló)
        try:
            self._tarea.start(trabajo)
        except PsgLabError as error:
            self._terminar_la_espera(que_hace)
            self._show_error(error, accion)
            return
        # **Después de arrancar y no antes.** Lo que decide qué se puede pedir
        # es `BackgroundTask.is_running()`, que con el hilo sin arrancar
        # todavía dice que no: llamado antes, esto no apagaba nada.
        self._reflejar_lo_que_se_puede_pedir()

    def _terminar_la_espera(self, que_hace: str) -> None:
        """Saca la barra y desconecta lo que quedó de este cálculo.

        **Se desconecta y no se deja conectado**: los `connect()` de
        `_en_segundo_plano()` son closures de *este* pedido, y dejarlos puestos
        haría que el siguiente cálculo dibujara también el resultado del
        anterior.
        """
        self._barra_de_espera.hide()
        if self.statusBar().currentMessage() == f"{que_hace}…":
            self.statusBar().clearMessage()
        for señal in (self._tarea.finished, self._tarea.failed):
            try:
                señal.disconnect()
            except RuntimeError:
                # No había nadie conectado. Qt lo considera un error; acá es
                # el caso normal de llamar dos veces.
                pass
        self._reflejar_lo_que_se_puede_pedir()

    def _reflejar_lo_que_se_puede_pedir(self) -> None:
        """Apaga lo que no se puede pedir con un cálculo en curso.

        **Dos cálculos a la vez sobre la misma sesión se pisan el resultado**, y
        cuál gana depende de cuál termine primero. `BackgroundTask` lo rechaza
        igual, pero un menú que deja pedir algo que va a fallar es peor que uno
        que lo muestra apagado.
        """
        ocupado = self._tarea.is_running()
        for accion in self._acciones_largas:
            accion.setEnabled(not ocupado)

    def wait_for_background(self) -> None:
        """Se queda hasta que termine el cálculo que esté corriendo.

        La llama el cierre de la ventana: soltar la sesión con otro hilo
        todavía leyendo el registro lo deja trabajando sobre memoria que ya
        nadie tiene.
        """
        self._tarea.wait()

    def warm_up_in_background(self) -> None:
        """Paga en otro hilo las dos esperas que se cobraban a la primera vez.

        **Los lectores primero**, porque abrir un registro es lo primero que
        hace el usuario: `mne.io` carga el módulo de cada formato recién al
        usarlo, y eso eran 8,65 de los 9,2 s de la primera lectura de cada
        sesión del programa, con la ventana congelada (hito 33). La segunda
        lectura del mismo archivo tardaba 18 ms.

        **Después `antropy`**, que compila con `numba` al importarse: 7 s en
        esta máquina, 21 s en la del hito 17, y los pagaba la primera medida de
        complejidad. En otro hilo no congela la ventana: medido en el hito 31,
        la interfaz sigue respondiendo con algún tirón de hasta 65 ms.

        Si el usuario llega antes que el hilo, el lock de importación de Python
        lo hace esperar lo que falte y nada se importa dos veces.

        `daemon` para que cerrar el programa no espere a que termine. **Lo
        lanza sólo `main.py`**, por `create_main_window(warm_up=True)`: cada
        ventana de la suite de tests lanzaría un hilo.
        """
        threading.Thread(target=_precalentar, name="precalentar-analisis", daemon=True).start()

    @contextmanager
    def _trabajando(self, que_hace: str) -> Iterator[None]:
        """Avisa que el programa está trabajando durante una espera larga.

        **No acorta la espera: la hace legible.** Todo corre en el hilo de la
        interfaz, así que la ventana queda congelada mientras dura el cálculo, y
        sin ninguna señal eso se lee como que el programa se colgó. Es la razón
        por la que `MEDIDAS_RAPIDAS` deja afuera la entropía de muestra.

        Y no alcanzaba con elegir medidas rápidas: el hito 17 midió que **la
        primera llamada de complejidad de cada sesión se lleva unos 21 s
        compilando**, cualquiera sea la medida, porque `antropy` arrastra
        `numba` y compila al importarse. Desde el hito 31 esa compilación se
        adelanta en otro hilo al arrancar: ver `warm_up_in_background()`.

        El cursor se pone antes de bloquear y Qt lo aplica en el acto; la barra
        de estado queda con el aviso **hasta que el cálculo termina, y no
        después** (hito 33): el mensaje no vencía y nadie lo borraba, así que la
        barra seguía diciendo «Calculando…» con el resultado ya en pantalla.
        Sólo se borra si sigue siendo el suyo: el que termina bien deja el
        propio, como «Se filtró la señal».
        """
        aviso = f"{que_hace}…"
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.statusBar().showMessage(aviso)
        # `processEvents` una sola vez, para que el cursor y el mensaje lleguen
        # a la pantalla antes de que el hilo se bloquee. No es un bucle de
        # eventos: no se procesa nada más hasta que el cálculo termina.
        QApplication.processEvents()
        try:
            yield
        finally:
            QApplication.restoreOverrideCursor()
            if self.statusBar().currentMessage() == aviso:
                self.statusBar().clearMessage()

    # -- Análisis (Parte 2) --------------------------------------------------

    def _aplicar_analisis(
        self,
        que_hace: str,
        calcular: Callable[[Recording], Recording],
        mostrar: str | None = None,
        accion: str | None = None,
    ) -> None:
        """Corre un análisis y lleva su resultado a la pantalla.

        Es el camino único de todo el menú Análisis: los módulos devuelven un
        `Recording` nuevo —no tocan el original, que es la regla 1 de la
        carpeta— y acá se lo entrega a la sesión con `set_recording()`, que
        conserva la ventana, los canales y las amplitudes.

        Un error del análisis sale como cartel y **no cambia nada**: la señal
        que el investigador está mirando sigue siendo la de antes.

        Args:
            mostrar: canal que hay que hacer visible además de los que ya
                estaban. `Session.set_recording()` conserva los visibles que
                sobreviven y **un canal nuevo no sobrevive: nace**, así que sin
                esto una derivación se creaba y no se veía. Mostrarlo es una
                decisión de presentación —el usuario acaba de pedirlo— y por eso
                vive acá y no en `core/`.
            accion: qué no se pudo hacer si falla, para la primera línea del
                cartel; ver `_show_error()`.
        """
        if self._session is None:
            return
        try:
            with self._trabajando(que_hace.replace("Se ", "").capitalize()):
                procesado = calcular(self._session.recording)
            self._session.set_recording(procesado)
        except PsgLabError as error:
            self._show_error(error, accion)
            return
        if mostrar is not None and mostrar not in self._session.visible_channels:
            self._session.set_visible_channels(
                [*self._session.visible_channels, mostrar]
            )
        self.signal_view.set_session(self._session)
        self.channel_selector.set_recording(procesado)
        # La señal cambió, así que la descomposición que hubiera dejó de ser de
        # este registro. Va **después** del `except`: si el análisis falló, la
        # señal es la de antes y la ICA sigue siendo válida. La reproducción
        # se detiene por lo mismo: la página puede haber cambiado de largo.
        self._olvidar_ica()
        self._olvidar_resultados()
        self.playback.stop()
        self.accion_señal_original.setEnabled(True)
        self.refresh()
        self.statusBar().showMessage(que_hace, 5000)

    def _olvidar_ica(self) -> None:
        """Descarta la descomposición ICA porque la señal dejó de ser la suya.

        **Es la única guarda que hay contra el error más caro del menú Análisis.**
        `fit_ica()` se ajusta sobre la señal que había en ese momento, y el panel
        se queda abierto esperando que el usuario elija qué quitar. Si entre el
        ajuste y el "Aplicar" la señal cambió —se filtró, se derivó, se
        re-referenció, se volvió a la original, o se abrió otro registro—, la
        matriz de desmezclado ya no corresponde.

        **Y no falla sola.** Filtrar no cambia los nombres de los canales, así que
        MNE acepta el pedido sin protestar y devuelve una señal reconstruida con
        una descomposición ajena. El resultado es plausible, irreversible y
        equivocado, que es exactamente lo que `analysis/ica.py` dice querer
        evitar cuando advierte que "el usuario puede no darse cuenta".

        Olvidar es lo correcto y no una molestia: volver a ajustar es un clic, y
        la alternativa —conservarla y avisar— le pide al investigador que decida
        sobre algo que no puede ver. `apply_ica()` tiene además su propia guarda
        para el caso en que los canales sí cambien.

        No hace nada si no hay ninguna descomposición cargada, así que se la
        puede llamar desde cualquier camino sin preguntar antes.
        """
        if self._ica is None:
            return
        self._ica = None
        self.ica_panel.clear_components()
        self.ica_dialog.hide()

    def _elegir_canal(self, titulo: str, etiqueta: str) -> str | None:
        """Pregunta un canal de los que hay. `None` si el usuario cancela."""
        if self._session is None:
            return None
        nombres = self._session.recording.channel_names()
        elegido, acepto = QInputDialog.getItem(self, titulo, etiqueta, nombres, 0, False)
        return elegido if acepto else None

    def _elegir_nomenclatura(self, path: Path) -> Nomenclature | None:
        """Pregunta con qué nomenclatura se scoreó un archivo que no lo dice.

        Arranca en la del registro abierto, que es la respuesta más probable:
        quien importa un scoring suele haberlo hecho con la misma que usa acá.
        `None` si el usuario cancela.
        """
        opciones = [n.value for n in Nomenclature]
        actual = self._session.scoring.nomenclature if self._session else None
        inicial = opciones.index(actual.value) if actual is not None else 0
        elegida, acepto = QInputDialog.getItem(
            self,
            "Importar scoring",
            f"«{path.name}» no dice con qué nomenclatura se scoreó.\n"
            "¿Con cuál se hizo?",
            opciones,
            inicial,
            False,
        )
        if not acepto:
            return None
        return next(n for n in Nomenclature if n.value == elegida)

    def derive_dialog(self) -> None:
        """Pregunta los dos canales y agrega la derivación (sección "Derivar").

        Se pregunta de a uno y no con un diálogo propio porque son dos listas
        de lo mismo: un formulario para eso sería más código y no más claro.
        """
        if self._session is None:
            return
        canal = self._elegir_canal("Derivar", "Canal:")
        if canal is None:
            return
        referencia = self._elegir_canal("Derivar", f"«{canal}» menos:")
        if referencia is None:
            return
        self._aplicar_analisis(
            f"Se agregó la derivación «{canal}-{referencia}»",
            lambda registro: derive(registro, canal, referencia),
            mostrar=f"{canal}-{referencia}",
            accion=f"derivar «{canal}-{referencia}»",
        )

    def rereference_dialog(self) -> None:
        """Pregunta la referencia nueva y re-referencia (sección "Rereferenciar")."""
        referencia = self._elegir_canal("Re-referenciar", "Referencia nueva:")
        if referencia is None:
            return
        self._aplicar_analisis(
            f"Se re-referenció a «{referencia}»",
            lambda registro: rereference(registro, [referencia]),
            accion="re-referenciar la señal",
        )

    def apply_average_reference(self) -> None:
        """Re-referencia al promedio de los EEG.

        No pregunta nada: `kind_only=True` es el valor seguro y el que el
        docstring del módulo defiende. Si el registro no tiene EEG, el módulo se
        niega y acá eso se convierte en un cartel.
        """
        self._aplicar_analisis(
            "Se re-referenció al promedio de los canales EEG",
            lambda registro: average_reference(registro),
            accion="re-referenciar la señal",
        )

    # -- El canal plano (hito 32) -------------------------------------------
    #
    # Con un canal plano el espectro sale en cero, la dimensión de Higuchi no
    # existe y la conectividad cuenta 0: las tres respuestas son correctas, y sin
    # explicarlas parecen un error del programa. Los números no cambian; la
    # regla de qué es plano es `Recording.flat_channels()`.

    def _planos_en_la_ventana(self, ventana: int, canales: list[str]) -> list[str]:
        """Cuáles de esos canales están planos en una época."""
        if self._session is None:
            return []
        registro = self._session.recording
        inicio, fin = window_to_samples(ventana, registro.sampling_rate)
        return registro.flat_channels(inicio, fin, canales)

    def _ventanas_planas(self, canales: list[str]) -> Counter[str]:
        """En cuántas épocas de la noche está plano cada canal que lo esté alguna vez.

        Recorre la noche una sola vez con todos los canales: con el registro de
        prueba son 2650 épocas, y cada una es un recorte sin copia.
        """
        planas: Counter[str] = Counter()
        if self._session is None:
            return planas
        registro = self._session.recording
        for ventana in range(count_windows(registro.n_samples, registro.sampling_rate)):
            planas.update(self._planos_en_la_ventana(ventana, canales))
        return planas

    def _nota_de_la_noche(self, series: dict[str, np.ndarray]) -> str:
        """El renglón que explica los ceros y los huecos de una medida de la noche."""
        total = max((len(v) for v in series.values()), default=0)
        planas = self._ventanas_planas(list(series))
        if planas:
            canal, cuantas = planas.most_common(1)[0]
            return (
                f"<br>«{canal}» está plano en {cuantas} de {total} ventanas: ahí la "
                "medida vale 0 o no existe."
            )
        huecos = max((int(np.isnan(v).sum()) for v in series.values()), default=0)
        if huecos:
            return f"<br>{huecos} de {total} ventanas sin valor: son demasiado cortas para medir."
        return ""

    @staticmethod
    def _nombrar(canales: list[str]) -> str:
        """«C3», «C4» y «O1», como se nombran los canales en el resto del programa."""
        nombres = [f"«{canal}»" for canal in canales]
        return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]

    def show_psd_dialog(self) -> None:
        """Calcula el espectro de la ventana actual y lo muestra (V1_F de PSD).

        **De la ventana actual y no del registro entero**, porque es lo que el
        investigador está mirando: el espectro de las ocho horas promedia el
        sueño lento con la vigilia y no dice nada de la época que se está
        scoreando. El título del panel lleva el número de ventana para que no
        haya duda de cuál es.

        Se abre en una ventana aparte y no como panel fijo: un espectro se mira
        cuando hace falta, y la pantalla principal ya tiene la señal, el
        scoring, la navegación, el histograma y el contexto.
        """
        if self._session is None:
            return
        canal = self._elegir_canal("Espectro", "Canal:")
        if canal is None:
            return
        ventana = self._session.current_window
        try:
            frecuencias, potencias = compute_psd(
                self._session.recording,
                channels=[canal],
                window_index=ventana,
                method=self._preferencias.psd_method,
            )
            bandas = self._preferencias.bands()
            potencias_por_banda = {
                nombre: (
                    float(np.ravel(band_power(frecuencias, potencias, extremos))[0]),
                    float(
                        np.ravel(
                            band_power(frecuencias, potencias, extremos, relative=True)
                        )[0]
                    ),
                )
                for nombre, extremos in bandas.items()
            }
        except PsgLabError as error:
            self._show_error(error, "calcular el espectro")
            return

        self.psd_panel.set_spectrum(frecuencias, potencias, [canal], bands=bandas)
        # Con qué se estimó: el método se elige en la configuración, y sin esta
        # línea dos espectros de la misma ventana podían no coincidir sin que
        # el panel dijera por qué. `compute_psd()` ya aceptó el método, así que
        # describirlo no puede fallar.
        self.psd_panel.set_method_description(
            describe_method(self._preferencias.psd_method)
        )
        # **La potencia de cada banda, que es la otra mitad de V1_F.** El panel
        # sombreaba las bandas y nunca decía cuánta potencia tenía cada una;
        # `band_power()` la calculaba desde el hito 13 y no la leía nadie.
        # Se pasan las dos: la absoluta y la relativa, que es la que
        # `analysis/psd.py` documenta como la que permite comparar entre
        # participantes, porque la absoluta depende del cráneo y la impedancia.
        # Las bandas son las de la configuración: las convencionales mientras el
        # usuario no las cambie.
        self.psd_panel.set_band_powers(potencias_por_banda)
        # **La descripción va en el panel y no en el título del dock**, que Qt
        # usa como texto de la entrada en «Herramientas»: el menú se renombraba
        # con cada cálculo (hito 31).
        descripcion = f"Espectro de «{canal}» — ventana {ventana + 1}"
        if self._planos_en_la_ventana(ventana, [canal]):
            descripcion += "<br>El canal está plano en esta ventana: no hay potencia que medir."
        # **Una banda por encima de lo que el registro alcanza da cero**, y un
        # cero no se distingue de un cero real: se dice cuáles y hasta dónde
        # llega el archivo (hito 33). La regla es la misma que usa `band_power`:
        # la banda es semiabierta, `[desde, hasta)`.
        sin_medir = [
            nombre
            for nombre, (desde, hasta) in bandas.items()
            if not ((frecuencias >= desde) & (frecuencias < hasta)).any()
        ]
        if sin_medir:
            tope = self._session.recording.sampling_rate / 2
            descripcion += (
                f"<br>{self._nombrar(sin_medir)} "
                f"{'queda' if len(sin_medir) == 1 else 'quedan'} fuera de lo que este "
                f"registro puede medir, que llega hasta {tope:g} Hz: su potencia sale "
                "en cero."
            )
        self.psd_panel.set_caption(descripcion)
        self.psd_dialog.show()
        self.psd_dialog.raise_()

    def show_complexity_dialog(self) -> None:
        """Recorre la noche con una medida de complejidad y la grafica.

        **La lista no ofrece la entropía de muestra**, y es una decisión de la
        interfaz y no del módulo: medida sobre el registro real tarda más de
        cinco minutos, contra menos de cinco segundos las otras tres. Con la
        ventana congelada ese rato, el investigador no sabe si el programa
        está trabajando o se colgó.

        `complexity_by_window()` sí la acepta: es una función de biblioteca y
        quien la llama desde un script puede esperar. La política es de acá.
        """
        if self._session is None:
            return
        canal = self._elegir_canal("Complejidad", "Canal:")
        if canal is None:
            return
        medida, acepto = QInputDialog.getItem(
            self, "Complejidad", "Medida:", list(MEDIDAS_RAPIDAS), 0, False
        )
        if not acepto:
            return
        try:
            with self._trabajando(f"Calculando {medida} sobre toda la noche"):
                series = complexity_by_window(
                    self._session.recording, [canal], measure=medida
                )
        except PsgLabError as error:
            self._show_error(error, "calcular la complejidad")
            return

        self._preparar_el_eje_de_la_metrica()
        self.metric_panel.set_metric(medida, series)
        self.metric_panel.set_caption(
            f"{medida} — «{canal}»" + self._nota_de_la_noche(series)
        )
        self.metric_dialog.show()
        self.metric_dialog.raise_()

    def show_connectivity_dialog(self) -> None:
        """Calcula la conectividad de la ventana actual y la muestra.

        **De la ventana actual**, por el mismo motivo que el espectro: la
        conectividad de las ocho horas promedia el sueño lento con la vigilia,
        y en sueño lo que interesa es cómo cambia entre fases.
        """
        if self._session is None:
            return
        canales = self._session.visible_channels
        if len(canales) < 2:
            self._show_error(
                PsgLabError(
                    "La conectividad se mide entre canales, así que hacen falta "
                    "al menos dos visibles.",
                    details=f"canales visibles: {canales}.",
                ),
                "medir la conectividad",
            )
            return
        # **Las mismas bandas que el espectro.** Dos definiciones distintas de
        # «sigma» en el mismo programa serían una trampa: el usuario que
        # corrigió una en la configuración espera verla corregida acá también.
        bandas = self._preferencias.bands()
        banda, acepto = QInputDialog.getItem(
            self, "Conectividad", "Banda:", list(bandas), 0, False
        )
        if not acepto:
            return

        ventana = self._session.current_window
        try:
            with self._trabajando(f"Midiendo la conectividad en {banda}"):
                matriz = compute_connectivity(
                    self._session.recording,
                    channels=canales,
                    band=bandas[banda],
                    method=METODO_DE_CONECTIVIDAD,
                    window_index=ventana,
                )
        except PsgLabError as error:
            self._show_error(error, "medir la conectividad")
            return

        self.connectivity_panel.set_matrix(
            matriz, canales, measure=METHOD_LABELS[METODO_DE_CONECTIVIDAD]
        )
        promedio = average_connectivity(matriz)
        descripcion = (
            f"Conectividad en {banda} — ventana {ventana + 1} — "
            f"promedio {promedio:.3f}".replace(".", ",", 1)
        )
        planos = self._planos_en_la_ventana(ventana, canales)
        if planos:
            descripcion += (
                f"<br>{'Plano' if len(planos) == 1 else 'Planos'} en esta ventana: "
                f"{self._nombrar(planos)}. Su conectividad cuenta 0 y baja el promedio."
            )
        self.connectivity_panel.set_caption(descripcion)
        self.connectivity_dialog.show()
        self.connectivity_dialog.raise_()

    def show_connectivity_night_dialog(self) -> None:
        """Mide la conectividad época por época y la grafica a lo largo de la noche.

        **Era un hueco declarado**, no una decisión: `connectivity_by_window()`
        existía desde el hito 14 y `MetricPanel` desde el hito 19, que lo dice
        en su propio docstring, y no había ningún camino que los juntara. El
        hito 20 lo dejó anotado como pregunta de producto. Se ofrece al cerrar
        el refactor de la interfaz.

        Lo que se grafica es **el promedio de cada matriz**, sin la diagonal:
        una matriz por época no se puede mirar a lo largo de ochocientas
        épocas, y un número por época sí se compara contra el hipnograma, que
        es para lo que sirve ver la noche entera.

        Es la operación más cara del menú después de la ICA: medido en el hito
        14, entre 0,3 y 0,5 minutos por noche con cuatro canales. Por eso va con
        el cursor de espera.
        """
        if self._session is None:
            return
        canales = self._session.visible_channels
        if len(canales) < 2:
            self._show_error(
                PsgLabError(
                    "La conectividad se mide entre canales, así que hacen falta "
                    "al menos dos visibles.",
                    details=f"canales visibles: {canales}.",
                ),
                "medir la conectividad de la noche",
            )
            return
        bandas = self._preferencias.bands()
        banda, acepto = QInputDialog.getItem(
            self, "Conectividad de la noche", "Banda:", list(bandas), 0, False
        )
        if not acepto:
            return

        # **Lo único que se lee de la sesión se lee acá**, en el hilo de la
        # interfaz: el otro hilo recibe el registro y los nombres ya resueltos y
        # no vuelve a preguntarle nada a `Session`.
        registro = self._session.recording
        limites = bandas[banda]

        def medir() -> object:
            matrices = connectivity_by_window(registro, canales, band=limites)
            return np.array([average_connectivity(matriz) for matriz in matrices])

        self._en_segundo_plano(
            f"Midiendo la conectividad en {banda} a lo largo de la noche",
            medir,
            lambda promedios: self._mostrar_la_conectividad_de_la_noche(
                banda, canales, promedios
            ),
            accion="medir la conectividad de la noche",
        )

    def _mostrar_la_conectividad_de_la_noche(
        self, banda: str, canales: list[str], promedios: object
    ) -> None:
        """Dibuja lo que midió el otro hilo. **Acá sí se tocan widgets.**"""
        etiqueta = f"Conectividad en {banda}"
        self._preparar_el_eje_de_la_metrica()
        self.metric_panel.set_metric(
            etiqueta, {f"Promedio de {len(canales)} canales": promedios}
        )
        # Los canales van en su renglón, y con más de seis se cuentan en vez de
        # nombrarse: treinta y dos nombres no entran en el ancho del gráfico.
        promediados = (
            ", ".join(canales) if len(canales) <= 6 else f"{len(canales)} canales visibles"
        )
        planos = self._ventanas_planas(canales)
        nota = ""
        if planos:
            nota = (
                f"<br>Con tramos planos: {self._nombrar(list(planos))}. Ahí su "
                "conectividad cuenta 0 y baja el promedio."
            )
        self.metric_panel.set_caption(
            f"{etiqueta} a lo largo de la noche<br>{promediados}{nota}"
        )
        self.metric_dialog.show()
        self.metric_dialog.raise_()

    def show_filter_dialog(self) -> None:
        """Abre el panel de filtros (V1_F de "Filtración").

        Arranca con los sugeridos de cada clase de canal presente. **Abrirlo no
        filtra nada**: hay que apretar Aplicar. Un menú que filtre con sólo
        abrirse le cambiaría la señal a alguien que entró a mirar qué había.
        """
        if self._session is None:
            return
        self.filter_panel.set_recording(self._session.recording)
        self.filter_dialog.show()
        self.filter_dialog.raise_()

    def apply_filters_from_panel(self) -> None:
        """Aplica lo que el panel tenga escrito.

        Se filtra **la señal que se está viendo**, no la original: así se puede
        filtrar después de derivar o de re-referenciar, que es el orden en que
        se trabaja. Y como todo el menú Análisis pasa por `_aplicar_analisis`,
        "Volver a la señal original" deshace también esto: un filtro mal
        elegido no obliga a reabrir el archivo.
        """
        if self._session is None:
            return
        por_clase = self.filter_panel.settings()
        # **Sin ningún filtro escrito no se toca la señal.** Antes se la
        # reemplazaba por una copia idéntica: la barra decía «Se filtró la
        # señal», se habilitaba volver a la original y se descartaba la ICA ya
        # ajustada, todo por un filtrado que no filtró nada.
        if all(filtros.is_empty for filtros in por_clase.values()):
            self._show_error(
                PsgLabError(
                    "No hay ningún filtro escrito, así que la señal no cambió. "
                    "Para quitar un filtro ya aplicado está «Montaje › Volver a "
                    "la señal original».",
                    details=f"filtros por clase: {por_clase}",
                ),
                "filtrar la señal",
            )
            return
        antes = self._session.recording
        self._aplicar_analisis(
            "Se filtró la señal",
            lambda registro: apply_filters(
                registro, settings_for_kinds(registro, por_clase)
            ),
            accion="filtrar la señal",
        )
        if self._session is None or self._session.recording is antes:
            return
        # **Qué canales quedaron sin pasa-altos** (hito 67). `settings_for_kinds()`
        # no se lo da a un canal grabado más lento que el registro, porque lo
        # dejaría plano; el panel lo avisa antes, y acá se confirma después: el
        # EMG del EDF del laboratorio quedaba con el 0,0 % de su señal y la barra
        # decía sólo «Se filtró la señal».
        sin_pasa_altos = [
            nombre
            for nombre, filtros in settings_for_kinds(antes, por_clase).items()
            if filtros.highpass_hz is None
            and por_clase[antes.channel_by_name(nombre).kind].highpass_hz is not None
        ]
        if sin_pasa_altos:
            uno = len(sin_pasa_altos) == 1
            self.statusBar().showMessage(
                f"Se filtró la señal, sin pasa-altos en {self._nombrar(sin_pasa_altos)}: "
                f"{'se grabó' if uno else 'se grabaron'} más lento que el registro, "
                f"y {'lo' if uno else 'los'} habría dejado "
                f"{'plano' if uno else 'planos'}.",
                15000,
            )

    def show_impedance_dialog(self) -> None:
        """Abre el control de impedancia (V1_F de "Impedancia").

        Arranca con lo que traiga el archivo. **En un EDF eso es siempre nada**,
        y no es un fallo: el estándar no tiene ningún campo de impedancia. Ahí
        el investigador las importa de un archivo del equipo o las escribe.
        """
        if self._session is None:
            return
        self._cargar_impedancias()
        self.impedance_dialog.show()
        self.impedance_dialog.raise_()

    def _cargar_impedancias(self) -> None:
        """Llena el panel con los canales del registro y lo que traiga el archivo."""
        if self._session is None:
            return
        self.impedance_panel.set_channels(
            self._session.recording.channel_names(),
            read_impedances(self._session.recording),
        )
        self._refrescar_informe_de_impedancia()

    def load_impedances_dialog(self) -> None:
        """Importa las impedancias de un archivo del equipo de adquisición."""
        if self._session is None:
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Importar impedancias",
            "",
            "Archivos de texto (*.txt *.csv);;Todos los archivos (*)",
        )
        if not ruta:
            return
        try:
            cargadas = load_impedances_from_file(Path(ruta))
        except PsgLabError as error:
            self._show_error(error, "importar las impedancias")
            return
        # **Un archivo sin impedancias no es un error de la biblioteca**, que
        # devuelve un diccionario vacío, pero sí una sorpresa: sin este aviso
        # importarlo no hacía nada y no decía nada (hito 32).
        if not cargadas:
            self._show_error(
                PsgLabError(
                    f"«{Path(ruta).name}» no trae ninguna impedancia, así que no se "
                    "cambió nada.",
                    details="El archivo está vacío o sólo tiene comentarios.",
                ),
                "importar las impedancias",
            )
            return

        # Se conserva lo que ya estaba escrito a mano: el archivo agrega, no
        # reemplaza. Un laboratorio puede tener medido medio montaje.
        combinadas = {**self.impedance_panel.values(), **cargadas}
        self.impedance_panel.set_channels(
            self._session.recording.channel_names(), combinadas
        )
        self._refrescar_informe_de_impedancia()

    def _limpiar_impedancias(self) -> None:
        """Deja todos los canales sin medir."""
        self.impedance_panel.clear_all()
        self._refrescar_informe_de_impedancia()

    def _refrescar_informe_de_impedancia(self) -> None:
        """Rearma el informe con lo que haya cargado.

        Se le pasa **la lista de canales**, que es lo que le permite distinguir
        el tercer estado: sin ella, el informe no puede saber cuáles faltan,
        porque los canales sin medir no están en el diccionario a propósito.
        """
        if self._session is None:
            return
        self.impedance_panel.set_report(
            impedance_report(
                self.impedance_panel.values(),
                DEFAULT_LIMIT_KOHM,
                channels=self._session.recording.channel_names(),
            )
        )

    def show_ica_dialog(self) -> None:
        """Ajusta la ICA y abre el panel para inspeccionarla (V5_F).

        **No aplica nada.** Ajustar e inspeccionar son dos pasos separados de
        aplicar, justamente porque quitar el componente equivocado modifica la
        señal de forma irreversible. El panel muestra las topografías y espera.

        **Corre en otro hilo desde el hito 47**, que es lo que quedaba del
        [hito 33](../../docs/TODO.md#hito-33-la-auditoría-del-19-de-septiembre).
        Es con diferencia lo más caro del programa —la auditoría midió 9 s sobre
        un registro real, y sobre ruido blanco, que es el peor caso para que
        FastICA converja, se midieron 345 s—, y **no cambia la señal**: por eso
        es el mismo trabajo que la conectividad de la noche y no necesitó
        ninguna decisión nueva. Las dos que sí la cambian —aplicar la ICA y
        filtrar— resultaron costar décimas de segundo; ver el hito 47.
        """
        if self._session is None:
            return
        # **Lo único que se lee de la sesión se lee acá**, en el hilo de la
        # interfaz: el otro recibe el registro ya resuelto y no vuelve a
        # preguntarle nada a `Session`.
        registro = self._session.recording

        def descomponer() -> object:
            descomposicion = fit_ica(registro)
            # **Las topografías se calculan adentro del hilo.** Son parte del
            # costo y tampoco tocan widgets; dejarlas afuera devolvería el
            # trabajo a medio hacer al hilo que se quiso liberar.
            topografias = [
                component_topography(descomposicion, numero)
                for numero in range(int(descomposicion.n_components_))
            ]
            # La varianza de cada componente también (hito 54): reconstruye la
            # señal desde cada uno, sobre una muestra de la noche.
            return descomposicion, topografias, explained_variance(descomposicion, registro)

        self._en_segundo_plano(
            "Descomponiendo la señal en componentes",
            descomponer,
            self._mostrar_la_ica,
            accion="calcular la ICA",
        )

    def _mostrar_la_ica(self, resultado: object) -> None:
        """Guarda la descomposición y abre el panel. **Acá sí se tocan widgets.**"""
        descomposicion, topografias, varianzas = resultado
        self._ica = descomposicion
        if self._session is not None:
            self.ica_panel.set_start_time(self._session.recording.start_time)
        self.ica_panel.set_components(topografias, varianzas)
        self.ica_dialog.show()
        self.ica_dialog.raise_()

    def _mostrar_curva_del_componente(self, component: int) -> None:
        """Reconstruye la serie del componente elegido y se la da al panel.

        **De la ventana actual**, por el mismo motivo que el espectro y la
        conectividad: la serie de las ocho horas no se puede mirar, y
        reconstruirla entera cuesta una copia completa de la señal.

        Es la mitad que faltaba de V5_F: `component_time_course()` existía desde
        el hito 15 con la promesa, en su propio docstring, de ser "lo que se
        dibuja debajo de la señal para ver **cuándo** ocurre el artefacto", y
        hasta el hito 19 no la llamaba nadie.
        """
        if self._session is None or self._ica is None:
            return
        ventana = self._session.current_window
        try:
            valores = component_time_course(
                self._ica, component, self._session.recording, window_index=ventana
            )
        except PsgLabError as error:
            # El panel ya dibujó la topografía y dejó la curva vacía, así que el
            # investigador conserva la mitad del criterio que sí se pudo dar.
            self._show_error(error, "mostrar el componente")
            return
        # **En segundos del registro** (hito 54), que es lo que numera el eje del
        # visualizador: así la curva se lee en la misma hora que la señal.
        frecuencia = self._session.recording.sampling_rate
        inicio, _ = window_to_samples(ventana, frecuencia)
        segundos = (inicio + np.arange(len(valores))) / frecuencia
        self.ica_panel.set_time_course(segundos, valores)

    def _apply_ica(self, exclude: list[int]) -> None:
        """Reconstruye la señal sin los componentes que el usuario marcó.

        **Pasa por `_aplicar_analisis()`**, que es el camino único del menú
        Análisis: así se puede volver a la señal original desde el menú, que es
        la única red que hay contra una exclusión equivocada — y quitar un
        componente no se puede deshacer sobre los datos ya transformados.
        """
        if self._session is None or self._ica is None:
            return
        cuantos = len(exclude)
        que_hizo = (
            "Se quitó 1 componente independiente"
            if cuantos == 1
            else f"Se quitaron {cuantos} componentes independientes"
        )
        # **Se toma la descomposición en una variable local antes de aplicar.**
        # `_aplicar_analisis()` llama a `_olvidar_ica()` al terminar bien, así que
        # una lambda que leyera `self._ica` la encontraría en `None` la próxima
        # vez que alguien la invocara.
        descomposicion = self._ica
        self._aplicar_analisis(
            que_hizo,
            lambda registro: apply_ica(registro, descomposicion, exclude),
            accion="quitar los componentes",
        )
        self.ica_dialog.hide()

    def restore_original_recording(self) -> None:
        """Vuelve a la señal tal como se leyó del archivo.

        **Es lo que hace reversible todo el menú.** Sin esto, un filtro o una
        referencia mal elegidos obligarían a cerrar y reabrir el registro,
        perdiendo el scoring que el usuario venía haciendo.
        """
        if self._session is None or self._registro_original is None:
            return
        try:
            self._session.set_recording(self._registro_original)
        except PsgLabError as error:
            self._show_error(error, "volver a la señal original")
            return
        self.signal_view.set_session(self._session)
        self.channel_selector.set_recording(self._registro_original)
        # Deshacer también cambia la señal, así que la descomposición que hubiera
        # se ajustó sobre la procesada y ya no corresponde. Lo mismo los
        # resultados de análisis.
        self._olvidar_ica()
        self._olvidar_resultados()
        self.playback.stop()
        self.accion_señal_original.setEnabled(False)
        self.refresh()
        self.statusBar().showMessage("Se volvió a la señal original", 5000)

    def open_recording_dialog(self) -> None:
        """Ctrl+O. El filtro se arma solo desde los lectores registrados."""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir registro", "", file_dialog_filter()
        )
        if ruta:
            self.open_recording(Path(ruta))

    def open_scoring_dialog(self) -> None:
        """El scoring entra por su **propia** opción, decidido en el hito 4.

        No es un formato más: `read_scoring()` no produce un `Recording`, así
        que no pasa por el despacho de `read_recording()`.

        El filtro se arma recorriendo `SCORING_FORMATS`: el primero junta los
        cuatro, que es lo que se busca casi siempre.
        """
        patrones = " ".join(f"*.{extension}" for extension in SCORING_FORMATS)
        filtros = [f"Scoring ({patrones})"]
        filtros += [f"{nombre} (*.{ext})" for ext, nombre in SCORING_FORMATS.items()]
        filtros.append("Todos los archivos (*)")
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar scoring", "", ";;".join(filtros)
        )
        if ruta:
            self.open_scoring(Path(ruta))

    def export_scoring_dialog(self, fmt: str = "txt") -> None:
        """Exporta el scoring en el formato pedido.

        Ctrl+S la llama sin argumento, así que el atajo exporta en `.txt`, que
        es el formato del pliego. Las cuatro entradas de «Scoring» pasan su
        extensión.
        """
        self._export_dialog("scoring", fmt)

    # -- Ayudantes privados -------------------------------------------------

    def _export_dialog(self, kind: str, fmt: str = "txt") -> None:
        """Pregunta dónde guardar y exporta.

        Propone el nombre del pliego con la extensión del formato elegido.
        **Si el usuario escribe un nombre sin esa extensión, se le agrega**: el
        diálogo de Qt no lo hace en todas las plataformas, y sin ella
        `export()` no sabría en qué formato escribir. Se agrega en vez de
        reemplazar para no convertir «noche.v2» en «noche.csv».
        """
        propuesto = Path(DEFAULT_FILENAMES[kind]).with_suffix(f".{fmt}").name
        filtro = f"{SCORING_FORMATS.get(fmt, fmt.upper())} (*.{fmt})"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", propuesto, filtro)
        if not ruta:
            return
        destino = Path(ruta)
        if destino.suffix.lower() != f".{fmt}":
            destino = destino.with_name(f"{destino.name}.{fmt}")
            # **La extensión se agrega después de que el diálogo confirmó**, así
            # que el archivo que se va a pisar no es el que el usuario vio: con
            # «noche» escrito a mano, el diálogo pregunta por «noche» y el que
            # se escribe es «noche.txt». Se pregunta de nuevo (hito 33).
            if destino.exists():
                if not self._confirmar(
                    "Reemplazar el archivo",
                    f"«{destino.name}» ya existe. ¿Reemplazarlo?",
                    "Reemplazar",
                    informativo="Se pierde lo que tenía.",
                ):
                    return
        self.export(kind, destino)

    def _go_to_window(self, window_index: int) -> None:
        if self._session is None:
            return
        # Reproduciendo, los botones, la franja y el hipnograma llevan el
        # cursor, y la reproducción sigue desde la época pedida (hito 27).
        if self._cabezal is not None:
            self._saltar_con_el_cursor(window_index)
            return
        try:
            self._session.go_to_window(window_index)
        except PsgLabError as error:
            self._show_error(error, "ir a esa ventana")
            return
        self.refresh()

    def _set_arousal(self, arousal: bool) -> None:
        """Marca o desmarca el arousal de la ventana actual (V2_F).

        **Con su `except`, como los otros catorce.** Una excepción que sale de
        un slot de Qt no cierra el programa: la imprime en la consola y el
        usuario no ve nada, que es peor que un cartel. Hoy los datos que llegan
        acá los arma la propia interfaz, pero eso deja de ser cierto en cuanto
        un panel se desincroniza del registro después de `set_recording()`.
        """
        if self._session is None:
            return
        try:
            self._session.scoring.set_arousal(self._session.current_window, arousal)
        except PsgLabError as error:
            self._show_error(error, "marcar el arousal")
            return
        self.refresh()

    def _change_nomenclature(self, nomenclature: Nomenclature) -> None:
        """Cambiar de nomenclatura sobre un registro ya scoreado pierde
        información, así que **se pregunta antes**.

        El panel no puede preguntarlo: no conoce el scoring y no sabe si hay
        algo que perder. Acá sí.
        """
        if self._session is None:
            return
        if self._session.scoring.scored_windows() > 0:
            if not self._confirmar(
                "Cambiar de nomenclatura",
                "¿Convertir el scoring que ya hiciste?",
                "Convertir",
                informativo="La conversión entre nomenclaturas pierde información: "
                "S3 y S4 se funden en N3, y volver atrás no puede distinguirlas.",
            ):
                self.scoring_panel.set_nomenclature(self._session.scoring.nomenclature)
                return
        self._session.scoring.change_nomenclature(nomenclature)
        self.scoring_panel.set_nomenclature(nomenclature)
        install_shortcuts(self, self._session)
        self.refresh()

    def _set_visible_channels(self, channel_names: list[str]) -> None:
        """Qué canales se dibujan (V3_P).

        El `except` es el mismo caso que `_set_arousal()`: `set_visible_channels`
        eleva `ChannelNotFoundError` si el selector nombra un canal que el
        registro ya no tiene, y desde un slot de Qt eso sale por consola.
        """
        if self._session is None:
            return
        try:
            self._session.set_visible_channels(channel_names)
        except PsgLabError as error:
            self._show_error(error, "cambiar los canales visibles")
            return
        self.signal_view.set_visible_channels(channel_names)
        self._refrescar_contexto()

    def _set_selected_channels(self, channel_names: list[str]) -> None:
        """Sobre qué canales actúan los cambios de amplitud (V5_F)."""
        if self._session is None:
            return
        try:
            self._session.set_selected_channels(channel_names)
        except PsgLabError as error:
            self._show_error(error, "seleccionar los canales")
            return
        self._refrescar_contexto()

    def _escribir_el_identificador(self) -> None:
        """Pone el identificador del registro y **lo deja del ancho que necesita**.

        `QMenuBar` le da a su widget de esquina el ancho que ese widget pide, y
        una vez: sin esto se queda con el de «Sin registro» y el identificador
        sale cortado. **El mínimo se calcula con las métricas de la fuente que
        el rótulo tiene puesta** y no con `sizeHint()`, que se resuelve antes
        de que la hoja de estilo le dé la tipografía numérica y devuelve un
        ancho de otra tipografía.

        Se vio en una captura de la barra; desde el código no se nota.
        """
        texto = self._describir_el_registro()
        if texto == self.recording_summary.text():
            return
        self.recording_summary.setText(texto)
        ancho = QFontMetrics(self.recording_summary.font()).horizontalAdvance(texto)
        self.recording_summary.setFixedWidth(ancho + _MARGEN_DEL_IDENTIFICADOR)
        # **Se lo vuelve a colgar**, que es lo único que le hace recalcular al
        # `QMenuBar` dónde empieza su esquina: `updateGeometry()` no alcanza y
        # el rótulo queda dibujado a partir del borde derecho de la ventana,
        # con casi todo afuera.
        self.menuBar().setCornerWidget(
            self.recording_summary, Qt.Corner.TopRightCorner
        )

    def _describir_el_registro(self) -> str:
        """Qué registro está abierto, para la esquina de la barra de menú.

        Nombre del archivo, frecuencia, cuántos canales y de qué hora a qué
        hora. Las horas sólo si el archivo las informa: un EDF puede no
        traerlas, y un guion en su lugar se lee como un dato.
        """
        if self._session is None:
            return SIN_REGISTRO
        registro = self._session.recording
        partes = [
            registro.file_path.name,
            f"{registro.sampling_rate:g} Hz",
            f"{registro.n_channels} canales",
        ]
        desde, hasta = self._horas_del_registro()
        if desde is not None and hasta is not None:
            partes.append(f"{desde} → {hasta}")
        return "  ·  ".join(partes)

    def _horas_del_registro(self) -> tuple[str | None, str | None]:
        """Cuándo empieza y cuándo termina el registro, para los costados de la
        franja. Las dos son None si el archivo no informa su hora de inicio."""
        if self._session is None:
            return (None, None)
        inicio = self._session.recording.start_time
        if inicio is None:
            return (None, None)
        fin = inicio + timedelta(seconds=self._session.recording.duration_seconds)
        return (inicio.strftime("%H:%M"), fin.strftime("%H:%M"))

    def _clock_label(self, window_index: int) -> str | None:
        """La hora real de una ventana, si el registro informa cuándo empezó."""
        if self._session is None:
            return None
        momento = window_to_clock_time(
            window_index, self._session.recording.start_time
        )
        return None if momento is None else momento.strftime("%H:%M:%S")

    def _update_histogram_window(self, window_index: int) -> None:
        herramienta = self._tools.get("histogram")
        if isinstance(herramienta, HistogramTool):
            herramienta.update_window(window_index)

    def _redraw_histogram(self) -> None:
        """Dibuja el hipnograma a partir de lo que publica su herramienta.

        La herramienta no dibuja —no conoce Qt— y devuelve una fase por
        ventana; acá se convierte en barras. El orden vertical lo fija
        `stages_of()`, así que cambiar de nomenclatura reordena el eje solo
        (V3_F del histograma).

        **Lo no scoreado queda en blanco, que es lo que pide V1_P.** Se dibuja
        como `NaN` y no como cero, y ésa es toda la diferencia: `connect="finite"`
        omite los puntos que no son finitos, así que el trazo se corta y la
        ventana sin scorear no deja marca.

        Hasta acá se mapeaba a **cero**, con lo cual `connect="finite"` no podía
        hacer nada —ningún valor era no finito— y lo no anotado se dibujaba como
        una línea en la base, por debajo de la fase más baja. Un tramo sin mirar
        se leía como una fase más, que es justo lo que el pliego no quiere: el
        histograma tiene el tamaño de la noche desde el arranque y hay que poder
        ver qué falta.
        """
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool) or self._session is None:
            return
        barras = herramienta.bars()
        if not barras:
            return

        orden = list(stages_of(self._session.scoring.nomenclature))
        altura = {fase: float(len(orden) - posicion) for posicion, fase in enumerate(orden)}
        item = self.histogram_view.getPlotItem()
        item.clear()
        item.plot(
            range(len(barras)),
            # `nan` para lo que no es una fila del histograma: `UNSCORED` no
            # tiene altura porque `stages_of()` no la incluye, y ésa es
            # exactamente la ausencia que hay que dibujar.
            [altura.get(fase, float("nan")) for fase in barras],
            stepMode="right",
            connect="finite",
        )
        self._pintar_las_fases(herramienta, altura)
        # La franja de posición se pinta con lo mismo: una fase tiene que verse
        # igual en los dos lugares, y las dos salen de `bars()`.
        self.navigation.set_scoring(
            [esquema.color_for_stage(fase.value) for fase in barras]
            if (esquema := theme.current()).stage_colors
            else []
        )
        item.setYRange(0, len(orden) + 0.5, padding=0)
        # `stage_label()` y no `str(fase)`: el segundo da "SleepStage.WAKE".
        # Es el mismo nombre que usan el panel de scoring y `Informacion.txt`.
        item.getAxis("left").setTicks(
            [[(altura[fase], stage_label(fase)) for fase in orden]]
        )
        item.getAxis("bottom").setTicks([self._marcas_del_histograma(len(barras))])

    def _pintar_las_fases(
        self, herramienta: HistogramTool, altura: dict[SleepStage, float]
    ) -> None:
        """Le pone a cada tramo del hipnograma el color de su fase (hito 34).

        **Sobre la curva y no en vez de ella.** La curva es la que resuelve lo
        no scoreado con `NaN`, que es V1_P, y la que deja ver de un vistazo la
        forma de la noche; el color es lo que deja reconocer una fase sin leer
        el eje. Un esquema sin escala de fases no pinta nada y el hipnograma se
        ve como antes.

        **Un solo ítem de escena para todos los tramos**, y tramos en vez de
        ventanas: es la misma cuenta del hito 25 con la grilla, sobre un panel
        que se redibuja en cada cambio de época.
        """
        esquema = theme.current()
        if not esquema.stage_colors:
            return
        tramos = [
            (inicio, cuantas, esquema.color_for_stage(fase.value), altura.get(fase))
            for inicio, cuantas, fase in herramienta.runs()
        ]
        # Una fase que el esquema no conoce, o que no es una fila del eje, no
        # se pinta: el color inventado sería peor que la curva sola.
        dibujables = [t for t in tramos if t[2] is not None and t[3] is not None]
        if not dibujables:
            return
        self.histogram_view.getPlotItem().addItem(
            pg.BarGraphItem(
                x0=[inicio for inicio, _, _, _ in dibujables],
                x1=[inicio + cuantas for inicio, cuantas, _, _ in dibujables],
                y0=[y - _GROSOR_DE_LA_FASE / 2 for _, _, _, y in dibujables],
                height=_GROSOR_DE_LA_FASE,
                pen=None,
                brushes=[color for _, _, color, _ in dibujables],
            )
        )

    def _preparar_el_eje_de_la_metrica(self) -> None:
        """Le da al eje de la métrica las marcas del hipnograma (hito 54).

        **Son los dos gráficos de la noche entera** y el de la métrica decía
        «Ventana» aunque el hipnograma estuviera en hora: se leían en unidades
        distintas. Salen de `_marcas_del_histograma()`, corridas a base 1, que
        es como la métrica numera sus ventanas. También le pone la marca de la
        época actual, que de otro modo aparecería recién con la próxima flecha.
        """
        if self._session is None:
            return
        herramienta = self._tools.get("histogram")
        en_hora = (
            isinstance(herramienta, HistogramTool)
            and herramienta.uses_clock_time
            and self._session.recording.start_time is not None
        )
        marcas = [
            (posicion + 1, texto)
            for posicion, texto in self._marcas_del_histograma(self._session.n_windows)
        ]
        self.metric_panel.set_time_ticks(marcas, en_hora)
        self.metric_panel.set_current_window(self._session.current_window)

    def _marcas_del_histograma(self, cuantas: int) -> list[tuple[float, str]]:
        """Las marcas del eje horizontal del hipnograma (V2_F).

        **Faltaba entero.** `set_time_axis()` prendía un booleano que no leía
        nadie y el eje se dibujaba con los índices crudos de `range()`, o sea
        base 0 y sin marcas: ni la hora real ni el 1 a VENMAX que pide el
        pliego.

        Las dos variantes salen del mismo lugar: `core.windows`. La hora real
        viene de `window_to_clock_time()`, que devuelve `None` si el archivo no
        informó a qué hora empezó, y ahí se cae al número de ventana en vez de
        inventar una hora.

        Los números de ventana van en **base 1**, que es la regla del proyecto
        para todo lo que se muestra.
        """
        herramienta = self._tools.get("histogram")
        if self._session is None or cuantas <= 0:
            return []
        en_hora = isinstance(herramienta, HistogramTool) and herramienta.uses_clock_time
        inicio = self._session.recording.start_time

        # Una decena de marcas alcanza para leer una noche entera sin que se
        # pisen los textos. Se calcula el paso en vez de fijarlo: un registro de
        # cinco ventanas y uno de tres mil necesitan cosas distintas.
        paso = max(1, cuantas // 10)
        marcas: list[tuple[float, str]] = []
        for ventana in range(0, cuantas, paso):
            if en_hora and inicio is not None:
                hora = window_to_clock_time(ventana, inicio)
                texto = hora.strftime("%H:%M") if hora is not None else str(ventana + 1)
            else:
                texto = str(ventana + 1)
            marcas.append((float(ventana), texto))
        return marcas

    def set_histogram_time_axis(self, use_clock_time: bool) -> None:
        """Cambia el eje del hipnograma entre hora real y número de ventana.

        La herramienta se niega a poner la hora real si el registro no informa
        a qué hora empezó, y tiene razón: un eje con una hora inventada se lee
        como si fuera cierta. Acá eso se convierte en un cartel.
        """
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool):
            return
        try:
            herramienta.set_time_axis(use_clock_time)
        except PsgLabError as error:
            self._show_error(error, "cambiar el eje del hipnograma")
            return
        self._redraw_histogram()
        self._preparar_el_eje_de_la_metrica()

    def _show_shortcuts(self) -> None:
        nomenclatura = (
            self._session.scoring.nomenclature
            if self._session is not None
            else Nomenclature.AASM
        )
        # Una tabla agrupada y no un cartel de texto (hito 54): ver
        # `ui/shortcuts_dialog.py`.
        ShortcutsDialog(nomenclatura, self).exec()

    def _confirmar(
        self,
        titulo: str,
        pregunta: str,
        accion: str,
        *,
        informativo: str = "",
        destructivo: bool = False,
    ) -> bool:
        """Pregunta antes de algo que no se deshace y dice si se confirmó.

        **Los botones dicen lo que hacen** (hito 65): «Borrar / Cancelar» y no
        «Sí / No», que obligaba a releer la pregunta para saber cuál era cuál.
        Es el mismo criterio del cartel del trabajo sin exportar.

        **Cancelar es el botón por omisión** cuando se pierde algo: un Enter
        apurado no puede borrar. Si no se pierde nada, lo es la acción.

        Está aparte para que los tests puedan contestarlo, igual que
        `_preguntar_por_el_trabajo()`: el cartel es modal.

        Args:
            titulo: el título del cartel, que nombra la acción.
            pregunta: la pregunta, con el nombre de lo que se toca.
            accion: el texto del botón que confirma, en infinitivo.
            informativo: la consecuencia, debajo de la pregunta.
            destructivo: si el botón lleva la tinta de lo que destruye.
        """
        cartel = QMessageBox(self)
        cartel.setIcon(QMessageBox.Icon.Question)
        cartel.setWindowTitle(titulo)
        cartel.setText(pregunta)
        if informativo:
            cartel.setInformativeText(informativo)
        confirmar = cartel.addButton(accion, QMessageBox.ButtonRole.AcceptRole)
        if destructivo:
            confirmar.setProperty(theme.DESTRUCTIVO_PROPERTY, True)
        cancelar = cartel.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cartel.setDefaultButton(cancelar if destructivo else confirmar)
        cartel.setEscapeButton(cancelar)
        cartel.exec()
        return cartel.clickedButton() is confirmar

    def _show_error(self, error: PsgLabError, accion: str | None = None) -> None:
        """Un solo lugar para los errores que ve el investigador.

        **El cartel empieza diciendo qué no se pudo hacer**: «No se pudo abrir
        «noche.edf».», y debajo el porqué. Era «No se pudo completar la
        operación» para todos, y después de un cálculo largo nadie recuerda qué
        había pedido. `accion` va en infinitivo, igual que en
        `memoria_suficiente()`; sin ella queda la frase genérica.

        **Va en el texto y no en el título** (hito 66). El hito 65 la había
        puesto en el título, y macOS no muestra el título de un `QMessageBox`:
        en una Mac el cartel seguía sin decir qué falló. Ver
        `_TITULO_DE_LOS_CARTELES`.

        `psglab/utils/errors.py` promete que todo lo que el programa eleva
        hereda de `PsgLabError` y trae el mensaje en español separado de la
        causa técnica. Acá se cobra esa promesa: el mensaje va al cartel y el
        detalle al desplegable, sin traza de Python a la vista.
        """
        cartel = QMessageBox(self)
        cartel.setIcon(QMessageBox.Icon.Warning)
        cartel.setWindowTitle(_TITULO_DE_LOS_CARTELES)
        cartel.setText(f"No se pudo {accion or 'completar la operación'}.")
        cartel.setInformativeText(str(error))
        detalle = getattr(error, "details", None)
        if detalle:
            cartel.setDetailedText(str(detalle))
        cartel.exec()
