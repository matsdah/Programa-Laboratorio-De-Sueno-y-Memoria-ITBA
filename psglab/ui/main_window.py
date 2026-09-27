"""Ventana principal: arma el layout y conecta las piezas entre sí.

Distribución general, pensada para el rol UX/UI del pliego (sección 15):

    +---------------------------------------------------------------+
    | [Abrir] Archivo | Ver | Scoring | Montaje | Filtrar | Analizar |
    |   Herramientas | Ayuda                                         |
    +----------+-----------------------------------------+----------+
    | Canales  |                                         | Espectro |
    |  (dock)  |   Visualizador de la señal (central)    | Métrica  |
    |          |                                         | ICA...   |
    |          |                                         | (solapas)|
    +----------+-----------------------------------------+----------+
    |  Scoring e hipnograma (a la vista) · Contexto (oculto)        |
    +---------------------------------------------------------------+
    |  Navegación: ⏮ ◀ ⏯ ▶ ⏭  1×  | franja | amplitud               |
    +---------------------------------------------------------------+
    |  Barra de estado: ventana 42 / 960 - 00:21:00                  |
    +---------------------------------------------------------------+

**La señal es el widget central y todo lo demás es un `QDockWidget`**: se
mueve, se apila en solapas, se cierra y se saca a otra pantalla. Los seis
paneles de análisis arrancan ocultos y los abre la acción que los calcula.

**No hay barra de herramientas.** Las herramientas se activan desde su menú,
que es la única vía: la barra horizontal que lo repetía debajo de la barra de
menú se quitó por confusa.

**El programa abre con la señal, el selector de canales, el scoring y el
hipnograma** (el hipnograma desde el hito 64, el scoring compacto desde el
79), y no recuerda la disposición de una apertura a otra (hito 24). Los demás paneles se abren desde «Herramientas»,
que desde el hito 28 lleva también los paneles.

**Este archivo arma la ventana y nada más** desde el hito 76. Hasta ahí tenía
170 métodos en 4300 líneas, y cada hito le sumaba los suyos. Ahora lo que la
ventana **hace** vive en módulos de esta carpeta, uno por tema. Seis son
mixins que `MainWindow` hereda:

    window_annotation.py   anotar con el mouse, con el teclado o desde el archivo
    window_files.py        abrir, importar, exportar y el trabajo sin exportar
    window_view.py         época, página, rueda, reproducción, amplitud y foco
    window_preferences.py  esquema, letra, colores de clase y configuración
    window_scoring.py      scorear, las fases sugeridas y el hipnograma
    window_analysis.py     los análisis de la Parte 2 y sus paneles

Acá quedan la construcción, las esperas largas, lo que se muestra de la época
actual y los carteles. **Los mixins son una partición por tema, no un
desacople**: comparten el estado de `__init__`, y un método de uno puede llamar
a otro de cualquier otro. Lo que se ganó es encontrar las cosas y que un cambio
toque un archivo de cientos de líneas y no uno de miles.

**El desacople empezó en el hito 79**, con controladores que tienen su estado
propio y la ventana guarda como atributo:

    tool_controller        las herramientas, quién tiene el mouse y lo que dibujan
    playback_controller    el cursor de la reproducción y cómo mueve la página
    analysis_controller    la señal original, la ICA y el cálculo en otro hilo
    work_guard             exportar, y preguntar antes de perder trabajo

La ventana les pide lo que necesita por su nombre y ellos le avisan con
señales de Qt; ver el docstring de cada uno.

**Los métodos siguen siendo de `MainWindow`**: los menús, los atajos y la
suite los llaman por su nombre en la ventana, y `monkeypatch.setattr(MainWindow,
...)` sigue reemplazándolos. Lo que cambió de lugar son los nombres de módulo:
un test que reemplace `fit_ica` tiene que hacerlo en `window_analysis`, que es
donde se lo busca ahora.

Los cinco requisitos que este archivo declaraba cubrir se fueron con los
métodos que los implementan: `export()` a `window_files.py`,
`_update_tool_readout()` —que cubría dos— a `window_tools.py`, y de ahí a
`ToolController.update_readout()` en el hito 79,
`_marcas_del_histograma()` a `window_scoring.py` y `_olvidar_ica()` a
`window_analysis.py`, y de ahí a `AnalysisController.forget_ica()` en el hito
79. Cada uno los declara en su docstring.

Cubre del pliego: ningún ID; es infraestructura.
"""

from collections.abc import Iterator
from datetime import timedelta
from contextlib import contextmanager

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QToolBar,
)

from psglab.core.nomenclature import Nomenclature
from psglab.core.session import Session
from psglab.core.windows import window_to_clock_time
from psglab.ui import preferences, theme
from psglab.ui.channel_selector import ChannelSelector
from psglab.ui.docks import build_docks
from psglab.ui.menus import build_menus, menu_path
from psglab.ui.navigation import NavigationBar
from psglab.ui.overview_panel import OverviewPanel
from psglab.ui.panel_header import SIN_REGISTRO
from psglab.ui.playback_controller import PlaybackController
from psglab.ui.connectivity_panel import ConnectivityPanel
from psglab.ui.ica_panel import IcaPanel
from psglab.ui.filter_panel import FilterPanel
from psglab.ui.analysis_controller import AnalysisController
from psglab.ui.work_guard import WorkGuard
from psglab.ui.impedance_panel import ImpedancePanel
from psglab.ui.metric_panel import MetricPanel
from psglab.ui.psd_panel import PsdPanel
from psglab.ui.scoring_panel import ScoringPanel
from psglab.ui.settings_dialog import SettingsDialog
from psglab.ui.shortcuts import install_shortcuts
from psglab.ui.shortcuts_dialog import ShortcutsDialog
from psglab.ui.signal_view import SignalView
from psglab.ui.tool_controller import ToolController
from psglab.utils.errors import PsgLabError
# Lo que la ventana hace, por tema (hito 76). Ver el docstring del módulo.
from psglab.ui.window_annotation import AnnotationMixin
from psglab.ui.window_files import FilesMixin
from psglab.ui.window_view import ViewMixin
from psglab.ui.window_preferences import PreferencesMixin
from psglab.ui.window_scoring import ScoringMixin
from psglab.ui.window_analysis import AnalysisMixin

#: Lo que se le suma al ancho del identificador del registro para que no quede
#: pegado al borde de la ventana ni a la última entrada del menú.
_MARGEN_DEL_IDENTIFICADOR: int = 18

#: El título de los carteles de error y de aviso. **No dice nada que haya que
#: leer** (hito 66): macOS no muestra el título de un `QMessageBox` —lo pide la
#: guía de Apple—, así que lo que el usuario tiene que saber va en el texto. El
#: hito 65 había puesto qué falló en el título, y en una Mac no se veía.
_TITULO_DE_LOS_CARTELES: str = "PSGLab"


class MainWindow(
    AnnotationMixin,
    FilesMixin,
    ViewMixin,
    PreferencesMixin,
    ScoringMixin,
    AnalysisMixin,
    QMainWindow,
):
    """Ventana principal del programa."""

    def __init__(self) -> None:
        """Crea la ventana con todos sus paneles, todavía sin registro abierto."""
        super().__init__()
        self.setWindowTitle("PSGLab — Laboratorio de Sueño y Memoria, ITBA")
        self._session: Session | None = None
        #: Las preferencias vigentes. **Arrancan en los valores de fábrica y no
        #: se leen del disco acá**: sólo `apply_saved_preferences()` las lee, y sólo
        #: la llama `main.py`. Si el constructor las leyera, la suite de tests
        #: dependería de lo que cada quien tenga configurado en su máquina.
        self._preferencias = preferences.Preferences()
        #: La tipografía con la que arrancó el programa, para poder volver a
        #: ella cuando el usuario elige «la del sistema».
        self._fuente_del_sistema = QFont(QApplication.font())
        # **La tipografía del programa, antes de construir nada** (hito 78):
        # lo que nace con ella la tiene en todas las plataformas. Ponerla
        # después, sobre widgets ya hechos, no le llegaba a casi ninguno; ver
        # `_poner_la_tipografia()`.
        self._poner_la_tipografia(preferences.Preferences())
        #: La ventana de configuración. Se arma la primera vez que se pide.
        self.settings_dialog: SettingsDialog | None = None
        #: Qué panel tiene el foco en el recorrido con F6, como posición en
        #: `focusable_panes()`. Arranca en la señal.
        self._panel_actual = 0

        self._build_layout()
        #: Las herramientas, quién tiene el mouse y lo que dibujan (hito 79).
        #: Va antes que los menús: «Herramientas» lleva sus modos, y el
        #: contador de la lupa es suyo.
        self.tool_controller = ToolController(
            self.signal_view,
            self.histogram_view,
            self.overview_panel,
            self.tool_readout,
            frozenset(self.docks),
            parent=self,
        )
        self._build_menus()
        # Los modos del mouse, arriba de los paneles que ya puso `menus.py`.
        self.tool_controller.build_menu(self.tools_menu)
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
        # **Las de fábrica, aplicadas** (hito 78). Hasta ahí se guardaban en
        # `_preferencias` y nadie las aplicaba: sólo `main.py` pasaba por
        # `_aplicar_preferencias()`, con las del disco, y toda otra ventana —la
        # de los tests, la de las capturas, la de los bancos— arrancaba
        # distinta de la del usuario. La tipografía ya se puso al principio;
        # esto es el resto, y va al final porque toca paneles. No escribe
        # nada: la ventana todavía no es la del usuario.
        self._aplicar_preferencias(self._preferencias)

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

        #: La reproducción: el reloj, el cursor y cómo mueven la página y la
        #: época (hito 79). Ver `ui/playback_controller.py`.
        self.playback_controller = PlaybackController(self.signal_view, parent=self)

        # Lo que la herramienta activa quiere informar: el porcentaje de la
        # ocupación (V3_F) y los picos que lleva contados la lupa (V2_F). Va a
        # la derecha, permanente, para que no lo pise el mensaje de navegación.
        self.tool_readout = QLabel("")
        self.statusBar().addPermanentWidget(self.tool_readout)
        #: Cuánto dura la página visible. Va aparte del mensaje de navegación,
        #: que habla de la época: son dos datos distintos.
        self.page_readout = QLabel("")
        self.statusBar().addPermanentWidget(self.page_readout)

        #: La señal original, la ICA ajustada y el cálculo que corre en otro
        #: hilo, con su barra de espera, que va a la derecha de las dos lecturas
        #: (hito 79). Ver `ui/analysis_controller.py`.
        self.analysis_controller = AnalysisController(self.statusBar(), parent=self)
        #: Exportar y no perder el trabajo (hito 79). Ver `ui/work_guard.py`.
        #: **Las dos funciones van por lambda**: la suite reemplaza
        #: `_confirmar` y las preferencias después de armar la ventana.
        self.work_guard = WorkGuard(
            self,
            self.statusBar(),
            lambda titulo, pregunta, boton, informativo: self._confirmar(
                titulo, pregunta, boton, informativo=informativo
            ),
            lambda: next(iter(self._preferencias.recent_files), None),
        )

        self.statusBar().showMessage(SIN_REGISTRO)

    def _build_menus(self) -> None:
        """Arma la barra de menú.

        El contenido vive en `psglab/ui/menus.py`, que además de las acciones
        deja en la ventana los dos `QAction` que el resto del programa toca
        —`accion_eje_en_hora` y `accion_señal_original`—, el botón de abrir un
        registro y el menú vacío de herramientas que puebla
        `ToolController.build_menu()`.
        """
        build_menus(self)
        # **Lo que no se puede pedir con un cálculo en curso.** Los dos menús
        # enteros porque las cuatro operaciones que llevan adentro sustituyen
        # el registro —o, en el caso de la ICA, arrancan otro cálculo—, y la
        # acción de conectividad porque es la otra que corre en otro hilo.
        self.analysis_controller.set_long_actions(
            (
                self.accion_conectividad_de_la_noche,
                self.menu_montaje.menuAction(),
                self.menu_filtrar.menuAction(),
            )
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

    def _connect_signals(self) -> None:
        """Conecta las señales de los paneles entre sí.

        Es el único lugar donde los paneles se enteran unos de otros: el
        visualizador no conoce al histograma, los dos pasan por acá.

        Acá se conectan también las señales de `tool_controller`, que es el
        que habla con las herramientas: pide ir a una ventana desde el
        hipnograma, avisa que hay que redibujarlo y le pasa a la ventana lo
        que el anotador deja para preguntar. **Se conectan con una lambda y
        no con el método ligado**: la suite reemplaza `_go_to_window` y los
        carteles de la anotación después de armar la ventana, y un método
        ligado al conectar no se enteraría.
        """
        self.navigation.window_requested.connect(self._go_to_window)
        # Hito 51: un clic en una caja de la Übersicht va a esa ventana, igual
        # que un clic en la franja de posición.
        self.overview_panel.window_clicked.connect(self._go_to_window)
        self.navigation.amplitude_up_requested.connect(self.increase_amplitude)
        self.navigation.amplitude_down_requested.connect(self.decrease_amplitude)
        self.navigation.playback_toggle_requested.connect(self.toggle_playback)
        reproduccion = self.playback_controller
        self.navigation.playback_speed_changed.connect(reproduccion.set_speed)
        reproduccion.clock.playing_changed.connect(self.navigation.set_playing)
        reproduccion.epoch_changed.connect(lambda: self._reflejar_epoca())
        reproduccion.reached_end.connect(
            lambda: self.statusBar().showMessage("Fin del registro", 5000)
        )
        reproduccion.failed.connect(lambda error, que: self._show_error(error, que))
        self.scoring_panel.stage_selected.connect(self.score_current_window)
        self.scoring_panel.arousal_toggled.connect(self._set_arousal)
        self.scoring_panel.nomenclature_changed.connect(self._change_nomenclature)
        self.channel_selector.visible_changed.connect(self._set_visible_channels)
        self.channel_selector.selection_changed.connect(self._set_selected_channels)

        analisis = self.analysis_controller
        analisis.failed.connect(lambda error, que: self._show_error(error, que))
        self.work_guard.failed.connect(lambda error, que: self._show_error(error, que))
        analisis.ica_forgotten.connect(lambda: self._al_olvidar_la_ica())
        analisis.restorable_changed.connect(self.accion_señal_original.setEnabled)

        herramientas = self.tool_controller
        herramientas.window_requested.connect(lambda ventana: self._go_to_window(ventana))
        herramientas.histogram_changed.connect(lambda: self._redraw_histogram())
        herramientas.annotation_released.connect(
            lambda anotador, preguntar: self._al_soltar_el_anotador(anotador, preguntar)
        )
        herramientas.annotation_menu_requested.connect(
            lambda anotador, segundos, donde: self._menu_de_anotacion(
                anotador, segundos, donde
            )
        )

        # **La rueda la atiende la ventana** (`ViewMixin.eventFilter()`): es de
        # la página y no de una herramienta. El resto del mouse lo filtra
        # `tool_controller`, que se instaló antes.
        self.signal_view.viewport().installEventFilter(self)

    # -- La época en pantalla y los carteles ---------------------------------
    #
    # Lo que queda acá además de la construcción: lo que se ve de la época
    # actual, que tocan todos los mixins, y los tres carteles del programa, que
    # comparten su título. Ver `_TITULO_DE_LOS_CARTELES`.

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

    def refresh(self) -> None:
        """Redibuja todos los paneles a partir del estado de la sesión.

        Se llama después de cualquier cambio: navegar, scorear, anotar o
        cambiar la amplitud. **Por eso registra el historial de deshacer**
        (hito 79): es el único lugar por el que pasan todos los cambios del
        scoring. Si lo que cambió no es trabajo —navegar, la amplitud—, la
        foto es la misma y no se guarda nada.
        """
        if self._session is None:
            return
        self.work_guard.record()
        self.signal_view.show_window(self._session.current_window)
        self.channel_selector.set_visible(self._session.visible_channels)
        self.tool_controller.refresh_overview()
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
        self.scoring_panel.set_current(
            epoca.stage, epoca.arousal, ventana, sesion.scoring.suggestion(ventana)
        )
        self._redraw_histogram()
        # La época actual, también sobre la curva de la métrica (hito 54).
        self.metric_panel.set_current_window(ventana)
        self.statusBar().showMessage(
            f"Ventana {ventana + 1} de {sesion.n_windows}"
            + (f" — {self._clock_label(ventana)}" if self._clock_label(ventana) else "")
        )

    @property
    def session(self) -> Session | None:
        """Sesión de trabajo actual, o None si no hay registro abierto."""
        return self._session

    # **Llegar a cualquier ventana sin mouse** (hito 62). Hasta acá sólo lo
    # hacían los clics en la franja, el hipnograma y la Übersicht, y con el
    # teclado la ventana 500 de una noche eran 500 flechas.

    # -- Las esperas largas --------------------------------------------------

    def wait_for_background(self) -> None:
        """Se queda hasta que termine el cálculo que esté corriendo.

        La llama el cierre de la ventana: soltar la sesión con otro hilo
        todavía leyendo el registro lo deja trabajando sobre memoria que ya
        nadie tiene. El cálculo es de `analysis_controller` (hito 79).
        """
        self.analysis_controller.wait()

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

    def _escribir_el_identificador(self) -> None:
        """Pone el identificador del registro y **lo deja del ancho que necesita**.

        `QMenuBar` le da a su widget de esquina el ancho que ese widget pide, y
        una vez: sin esto se queda con el de «Sin registro» y el identificador
        sale cortado. **El mínimo se calcula con las métricas de la fuente que
        el rótulo tiene puesta** y no con `sizeHint()`, que se resolvía antes
        de que la hoja de estilo le diera la tipografía numérica y devolvía un
        ancho de otra tipografía. Desde el hito 77 hay una sola, pero la
        medida sigue siendo la del rótulo: es la única que no depende de
        cuándo se aplicó la hoja.

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
        `WorkGuard.ask()`: el cartel es modal.

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


