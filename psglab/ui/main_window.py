"""Ventana principal: arma el layout y conecta las piezas entre sí.

Distribución general, pensada para el rol UX/UI del pliego (sección 15):

    +--------------------------------------------------------------+
    |  Menú: Archivo | Ver | Herramientas | Ayuda   (Análisis: P2)  |
    +--------------------------------------------------------------+
    |  Barra de herramientas (lupa, amplitud, ocupación, anotar)    |
    +------------------+-------------------------------------------+
    |  Selector de     |                                           |
    |  canales         |     Visualizador de la señal (30 s)       |
    |                  |                                           |
    +------------------+-------------------------------------------+
    |  Panel de scoring (W / N1 / N2 / N3 / R ... + Arousal)        |
    +--------------------------------------------------------------+
    |  Histograma de la noche completa                              |
    +--------------------------------------------------------------+
    |  Barra de estado: ventana 42 / 960 - 00:21:00                 |
    +--------------------------------------------------------------+

Cubre del pliego: V4_F de "Archivo de salida" (elegir cuál de los tres
archivos exportar). Además es el contenedor que reúne todas las demás
funcionalidades de la Parte 1, pero sin implementar ninguna: cada una vive en
su módulo y acá sólo se las conecta entre sí.
"""

from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import (
    Nomenclature,
    SleepStage,
    stage_label,
    stages_of,
)
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.core.windows import count_windows, window_to_clock_time
from psglab.exporters import DEFAULT_FILENAMES
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.information_txt import export_information
from psglab.exporters.scoring_txt import export_scoring
from psglab.readers.base import file_dialog_filter, read_recording
from psglab.readers.scoring_reader import read_scoring
from psglab.tools.annotator import AnnotatorTool
from psglab.tools.base import Tool, ViewerTool
from psglab.tools.histogram import HistogramTool
from psglab.tools.magnifier import MagnifierTool
from psglab.tools.occupancy import OccupancyTool
from psglab.tools.registry import available_tools
from psglab.ui.channel_selector import ChannelSelector
from psglab.ui.grid import BackgroundStyle
from psglab.ui.navigation import NavigationBar
from psglab.ui.scoring_panel import ScoringPanel
from psglab.ui.shortcuts import install_shortcuts, shortcuts_help_text
from psglab.ui.signal_view import SignalView
from psglab.utils.errors import PsgLabError

#: Qué botón del mouse llegó, traducido al vocabulario de `ViewerTool`, que no
#: conoce Qt.
_BOTONES = {
    Qt.MouseButton.LeftButton: "left",
    Qt.MouseButton.RightButton: "right",
    Qt.MouseButton.MiddleButton: "middle",
}


class MainWindow(QMainWindow):
    """Ventana principal del programa."""

    def __init__(self) -> None:
        """Crea la ventana con todos sus paneles, todavía sin registro abierto."""
        super().__init__()
        self.setWindowTitle("PSGLab — Laboratorio de Sueño y Memoria, ITBA")
        self._session: Session | None = None
        self._tools: dict[str, Tool] = {}
        #: El botón de cada herramienta, para poder destildarlo al apagarla.
        self._tool_actions: dict[str, QAction] = {}
        self._active_viewer_tool: ViewerTool | None = None

        self._build_layout()
        self._build_menus()
        self._build_toolbar()
        self._connect_signals()
        install_shortcuts(self, None)

    # -- Construcción -------------------------------------------------------

    def _build_layout(self) -> None:
        """Crea los paneles y los ubica según el esquema de arriba."""
        self.signal_view = SignalView()
        self.channel_selector = ChannelSelector()
        self.scoring_panel = ScoringPanel()
        self.navigation = NavigationBar()
        self.histogram_view = pg.PlotWidget()
        self.histogram_view.setMaximumHeight(140)
        self.histogram_view.getPlotItem().setMenuEnabled(False)
        self.histogram_view.getPlotItem().setMouseEnabled(x=False, y=False)

        arriba = QSplitter()
        arriba.addWidget(self.channel_selector)
        arriba.addWidget(self.signal_view)
        arriba.setStretchFactor(1, 4)

        centro = QWidget()
        columna = QVBoxLayout(centro)
        columna.addWidget(arriba, stretch=4)
        columna.addWidget(self.scoring_panel)
        columna.addWidget(self.navigation)
        columna.addWidget(self.histogram_view, stretch=1)
        self.setCentralWidget(centro)
        # Lo que la herramienta activa quiere informar: el porcentaje de la
        # ocupación (V3_F) y los picos que lleva contados la lupa (V2_F). Va a
        # la derecha, permanente, para que no lo pise el mensaje de navegación.
        self.tool_readout = QLabel("")
        self.statusBar().addPermanentWidget(self.tool_readout)
        self.statusBar().showMessage("Sin registro abierto")

    def _build_menus(self) -> None:
        """Crea la barra de menú y las acciones."""
        archivo = self.menuBar().addMenu("&Archivo")
        archivo.addAction("&Abrir registro…", self.open_recording_dialog)
        archivo.addAction("&Importar scoring…", self.open_scoring_dialog)
        archivo.addSeparator()
        # V4_F pide poder exportar **uno solo** de los tres, así que son tres
        # acciones y no un único "Exportar todo".
        for kind, nombre in DEFAULT_FILENAMES.items():
            archivo.addAction(
                f"Exportar {nombre}…", lambda _=False, k=kind: self._export_dialog(k)
            )
        archivo.addSeparator()
        archivo.addAction("&Salir", self.close)

        ver = self.menuBar().addMenu("&Ver")
        for estilo in BackgroundStyle:
            ver.addAction(
                estilo.value, lambda _=False, e=estilo: self.signal_view.grid.set_style(e)
            )

        ver.addSeparator()
        # V2_F del histograma: el pliego pide poder elegir el eje.
        self.accion_eje_en_hora = ver.addAction(
            "Histograma en hora real de la noche"
        )
        self.accion_eje_en_hora.setCheckable(True)
        self.accion_eje_en_hora.toggled.connect(self.set_histogram_time_axis)

        self.tools_menu = self.menuBar().addMenu("&Herramientas")

        ayuda = self.menuBar().addMenu("A&yuda")
        ayuda.addAction("&Atajos de teclado", self._show_shortcuts)

    def _build_toolbar(self) -> None:
        """Crea la barra de herramientas a partir del registro de herramientas.

        Se arma recorriendo `psglab.tools.registry`, así que una herramienta
        nueva aparece sola sin tocar este archivo.
        """
        barra = self.addToolBar("Herramientas")
        for cls in available_tools():
            herramienta = cls()
            self._tools[cls.name] = herramienta

            accion = barra.addAction(cls.label)
            accion.setCheckable(True)
            accion.setToolTip(cls.description)
            self._tool_actions[cls.name] = accion
            accion.toggled.connect(
                lambda activa, n=cls.name: self._toggle_tool(n, activa)
            )
            self.tools_menu.addAction(accion)

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

        herramienta = self._active_viewer_tool
        if herramienta is None or evento.type() not in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        ):
            return False

        # **En coordenadas de escena, no del viewport.** `seconds_at_pixel()`
        # resuelve con `mapSceneToView()`, así que darle un `position()` sería
        # mezclar dos sistemas que hoy coinciden y no tienen por qué.
        segundos = self.signal_view.seconds_at_pixel(evento.scenePosition().x())
        # **En microvoltios, que es lo que `ViewerTool` documenta recibir.**
        # Hasta el hito 9 acá iba la coordenada cruda del gráfico, con un
        # comentario que afirmaba que ninguna herramienta usaba la `y`. La usan
        # tres, y la peor consecuencia era que la ocupación borraba una línea
        # con cualquier clic, porque comparaba su tolerancia de 10 µV contra un
        # rango de 0 a 1.
        y = self.signal_view.microvolts_at_pixel(evento.scenePosition().y())

        if evento.type() == QEvent.Type.MouseMove:
            herramienta.on_mouse_move(segundos, y)
        else:
            boton = _BOTONES.get(evento.button(), "left")
            if evento.type() == QEvent.Type.MouseButtonPress:
                herramienta.on_mouse_press(segundos, y, boton)
            else:
                herramienta.on_mouse_release(segundos, y, boton)
                # **Acá se cierra el lazo de V1_F de "Anotación".** La
                # herramienta deja el tramo pendiente y espera que alguien
                # pregunte la clase; hasta el hito 9 no lo hacía nadie, así que
                # se podía arrastrar una selección y no pasaba nada.
                if isinstance(herramienta, AnnotatorTool):
                    self._finish_annotation(herramienta)
        return False

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
        fraccion = (evento.scenePosition().x() - caja.left()) / caja.width()
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
        inicio, duracion = pendiente

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
            self._show_error(error)
            return
        self.statusBar().showMessage(f"Se anotó «{clase}»", 5000)

    def _on_tool_changed(self, tool: Tool) -> None:
        """Una herramienta avisó de que cambió lo que quiere mostrar."""
        if isinstance(tool, ViewerTool):
            self.signal_view.set_overlays(tool.overlays())
        elif isinstance(tool, HistogramTool):
            self._redraw_histogram()
        self._update_tool_readout()

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
        herramienta = self._active_viewer_tool
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

    def _deactivate_all_tools(self) -> None:
        """Apaga las herramientas y destilda sus botones.

        La barra tiene que quedar diciendo la verdad: un botón hundido sobre
        una herramienta apagada es peor que ninguno.
        """
        for accion in self._tool_actions.values():
            accion.setChecked(False)
        for herramienta in self._tools.values():
            herramienta.deactivate()
        self._active_viewer_tool = None

    def _activate_panel_tools(self) -> None:
        """Enciende las herramientas que son paneles, no modos del mouse.

        `exclusive = False` significa justamente eso —lo declaran así el
        histograma y la Übersicht— y un panel permanente que arranca apagado es
        un hueco en la pantalla esperando que alguien adivine que hay que
        apretar un botón. Los modos del mouse sí arrancan apagados: sólo puede
        haber uno y elegirlo es del usuario.
        """
        if self._session is None:
            return
        for nombre, herramienta in self._tools.items():
            if not herramienta.exclusive:
                herramienta.activate(self._session)
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
            self._active_viewer_tool = (
                herramienta if isinstance(herramienta, ViewerTool) else None
            )

        if activa:
            herramienta.activate(self._session)
        else:
            herramienta.deactivate()
            if herramienta is self._active_viewer_tool:
                self._active_viewer_tool = None
        self._update_tool_readout()

    # -- Acciones del usuario -----------------------------------------------

    def open_recording(self, path: Path) -> None:
        """Abre un registro y prepara la sesión de trabajo.

        Muestra un error legible si el archivo no se puede leer, en vez de
        dejar caer una excepción: los usuarios no necesariamente tienen
        experiencia informática (pliego, sección 3).
        """
        try:
            registro = read_recording(path)
            ventanas = count_windows(registro.n_samples, registro.sampling_rate)
            sesion = Session(
                registro,
                Scoring(ventanas, Nomenclature.AASM),
                AnnotationSet(),
            )
        except PsgLabError as error:
            self._show_error(error)
            return

        # Las herramientas activas siguen guardando la sesión que recibieron
        # en `activate()`: si no se las suelta, la ocupación seguiría midiendo
        # sobre el registro anterior y el histograma dibujaría su scoring.
        self._deactivate_all_tools()

        self._session = sesion
        # Las herramientas se enteran solas de los cambios de ventana: es la
        # decisión del hito 6, y por eso acá no hay que acordarse de avisarles.
        for herramienta in self._tools.values():
            sesion.add_window_listener(herramienta.on_window_changed)

        self.signal_view.set_session(sesion)
        self.channel_selector.set_recording(registro)
        self.scoring_panel.set_nomenclature(sesion.scoring.nomenclature)
        install_shortcuts(self, sesion)
        self._activate_panel_tools()
        self.refresh()

    def open_scoring(self, path: Path) -> None:
        """Importa un scoring existente sobre el registro abierto (V3_F)."""
        if self._session is None:
            self._show_error(
                PsgLabError(
                    "Hay que abrir un registro antes de importarle un scoring.",
                    details="No hay ninguna sesión abierta.",
                )
            )
            return
        try:
            scoring = read_scoring(path, self._session.n_windows)
            # **Se sustituye adentro de la sesión, no se arma otra.** Importar
            # un scoring no es abrir otro registro: el usuario sigue parado en
            # su ventana, con sus canales y sus amplitudes, y las herramientas
            # ya activadas siguen apuntando a la sesión correcta. El motivo
            # completo está en `Session.set_scoring()`.
            self._session.set_scoring(scoring)
        except PsgLabError as error:
            self._show_error(error)
            return

        self.scoring_panel.set_nomenclature(scoring.nomenclature)
        self._reload_histogram()
        self.refresh()

    def export(self, kind: str, path: Path) -> None:
        """Exporta uno de los tres archivos de salida (V4_F).

        El diálogo de guardado propone el nombre de archivo que fija el pliego,
        tomándolo de `psglab.exporters.DEFAULT_FILENAMES`.

        Args:
            kind: "scoring", "annotations" o "information".
        """
        if self._session is None:
            return
        try:
            if kind == "scoring":
                export_scoring(self._session.scoring, path)
            elif kind == "annotations":
                export_annotations(self._session.annotations, path)
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
            self._show_error(error)
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
                )
            )
            return
        self.statusBar().showMessage(f"Se exportó {path.name}", 5000)

    def refresh(self) -> None:
        """Redibuja todos los paneles a partir del estado de la sesión.

        Se llama después de cualquier cambio: navegar, scorear, anotar o
        cambiar la amplitud.
        """
        if self._session is None:
            return
        sesion = self._session
        ventana = sesion.current_window

        self.signal_view.show_window(ventana)
        self.navigation.set_position(ventana, sesion.n_windows)
        self.navigation.set_clock_time(self._clock_label(ventana))
        epoca = sesion.scoring.get(ventana)
        self.scoring_panel.set_current(epoca.stage, epoca.arousal)
        self.channel_selector.set_visible(sesion.visible_channels)
        self._redraw_histogram()
        self.statusBar().showMessage(
            f"Ventana {ventana + 1} de {sesion.n_windows}"
            + (f" — {self._clock_label(ventana)}" if self._clock_label(ventana) else "")
        )

    @property
    def session(self) -> Session | None:
        """Sesión de trabajo actual, o None si no hay registro abierto."""
        return self._session

    # -- Lo que ejecutan los atajos de teclado ------------------------------

    def go_to_next_window(self) -> None:
        """Flecha derecha."""
        if self._session is not None:
            self._session.next_window()
            self.refresh()

    def go_to_previous_window(self) -> None:
        """Flecha izquierda."""
        if self._session is not None:
            self._session.previous_window()
            self.refresh()

    def increase_amplitude(self) -> None:
        """Flecha arriba. La cuenta la hace `Session`."""
        self.signal_view.increase_amplitude()

    def decrease_amplitude(self) -> None:
        """Flecha abajo."""
        self.signal_view.decrease_amplitude()

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
            self._show_error(error)
            return
        self._update_histogram_window(self._session.current_window)
        self.refresh()

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
        """
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar scoring", "", "Scoring (*.txt);;Todos los archivos (*)"
        )
        if ruta:
            self.open_scoring(Path(ruta))

    def export_scoring_dialog(self) -> None:
        """Ctrl+S."""
        self._export_dialog("scoring")

    # -- Ayudantes privados -------------------------------------------------

    def _export_dialog(self, kind: str) -> None:
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar", DEFAULT_FILENAMES[kind], "Texto (*.txt)"
        )
        if ruta:
            self.export(kind, Path(ruta))

    def _go_to_window(self, window_index: int) -> None:
        if self._session is None:
            return
        try:
            self._session.go_to_window(window_index)
        except PsgLabError as error:
            self._show_error(error)
            return
        self.refresh()

    def _set_arousal(self, arousal: bool) -> None:
        if self._session is None:
            return
        self._session.scoring.set_arousal(self._session.current_window, arousal)
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
            respuesta = QMessageBox.question(
                self,
                "Cambiar de nomenclatura",
                "La conversión entre nomenclaturas pierde información: S3 y S4 "
                "se funden en N3, y volver atrás no puede distinguirlas.\n\n"
                "¿Convertir el scoring que ya hiciste?",
            )
            if respuesta != QMessageBox.StandardButton.Yes:
                self.scoring_panel.set_nomenclature(self._session.scoring.nomenclature)
                return
        self._session.scoring.change_nomenclature(nomenclature)
        self.scoring_panel.set_nomenclature(nomenclature)
        install_shortcuts(self, self._session)
        self.refresh()

    def _set_visible_channels(self, channel_names: list[str]) -> None:
        if self._session is None:
            return
        self._session.set_visible_channels(channel_names)
        self.signal_view.set_visible_channels(channel_names)

    def _set_selected_channels(self, channel_names: list[str]) -> None:
        if self._session is not None:
            self._session.set_selected_channels(channel_names)

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
        """
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool) or self._session is None:
            return
        barras = herramienta.bars()
        if not barras:
            return

        orden = list(stages_of(self._session.scoring.nomenclature))
        altura = {fase: len(orden) - posicion for posicion, fase in enumerate(orden)}
        item = self.histogram_view.getPlotItem()
        item.clear()
        item.plot(
            range(len(barras)),
            [altura.get(fase, 0) for fase in barras],
            stepMode="right",
            connect="finite",
        )
        item.setYRange(0, len(orden) + 0.5, padding=0)
        # `stage_label()` y no `str(fase)`: el segundo da "SleepStage.WAKE".
        # Es el mismo nombre que usan el panel de scoring y `Informacion.txt`.
        item.getAxis("left").setTicks(
            [[(altura[fase], stage_label(fase)) for fase in orden]]
        )
        item.getAxis("bottom").setTicks([self._marcas_del_histograma(len(barras))])

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
            self._show_error(error)
            return
        self._redraw_histogram()

    def _show_shortcuts(self) -> None:
        nomenclatura = (
            self._session.scoring.nomenclature
            if self._session is not None
            else Nomenclature.AASM
        )
        QMessageBox.information(
            self, "Atajos de teclado", shortcuts_help_text(nomenclatura)
        )

    def _show_error(self, error: PsgLabError) -> None:
        """Un solo lugar para los errores que ve el investigador.

        `psglab/utils/errors.py` promete que todo lo que el programa eleva
        hereda de `PsgLabError` y trae el mensaje en español separado de la
        causa técnica. Acá se cobra esa promesa: el mensaje va al cartel y el
        detalle al desplegable, sin traza de Python a la vista.
        """
        cartel = QMessageBox(self)
        cartel.setIcon(QMessageBox.Icon.Warning)
        cartel.setWindowTitle("No se pudo completar la operación")
        cartel.setText(str(error))
        detalle = getattr(error, "details", None)
        if detalle:
            cartel.setDetailedText(str(detalle))
        cartel.exec()
