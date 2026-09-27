"""Las herramientas de la ventana: cuáles hay, quién tiene el mouse y qué dibujan.

Todo lo que va y viene entre `SignalView` y las herramientas de `tools/`:
crearlas desde el registro y ponerlas en el menú, prenderlas y apagarlas
respetando la exclusividad, el filtro de eventos que traduce píxeles a segundos
y µV, los overlays que dibujan, la Übersicht y la lectura de la barra de
estado.

**Es una pieza con estado propio** (hito 79), y no un pedazo de `MainWindow`
como lo era `window_tools.py`. Aquél compartía con los otros seis mixins el
estado de `__init__` —qué herramientas había, cuál tenía el mouse, qué se
había dibujado—, y cualquier método de la ventana lo tocaba. Ahora ese estado
vive acá y la ventana lo pide por su nombre: `tools`, `actions`,
`mouse_tool`, `drawn_overlays`.

**No conoce la ventana.** Recibe los cuatro widgets que usa y le avisa lo
demás con señales de Qt:

- `window_requested`: un clic en el hipnograma pidió ir a una ventana.
- `histogram_changed`: el hipnograma cambió; dibujarlo es de
  `window_scoring.py`, que conoce los colores de las fases y el eje.
- `annotation_released` y `annotation_menu_requested`: el anotador soltó un
  tramo, o pidió su menú con el clic derecho. Lo que sigue —preguntar la
  clase, ofrecer cambiarla o borrarla— son carteles, y los carteles son de la
  ventana.

Por eso se puede armar y testear sin `MainWindow`, que es lo que hace
`tests/test_tool_controller.py`.

**La rueda no está acá**: no es de ninguna herramienta sino de la página, y
vive en `window_view.py`. Lo que se comparte es `scene_position()`.

Cubre del pliego: V3_F de "Ocupación de la página" (`update_readout` muestra
el porcentaje) y V2_F de "Herramienta Lupa" (el contador de picos, también en
`update_readout`). El cálculo está en `tools/`; lo que vive acá es la mitad que
lo lleva a la pantalla.
"""

from collections.abc import Mapping
from types import MappingProxyType

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QAction, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QLabel, QMenu

from psglab.core.session import Session
from psglab.tools.annotator import AnnotatorTool, annotation_bands
from psglab.tools.base import Overlay, Tool, ViewerTool
from psglab.tools.histogram import HistogramTool
from psglab.tools.magnifier import MagnifierTool
from psglab.tools.occupancy import OccupancyTool
from psglab.tools.overview import OverviewTool
from psglab.tools.registry import available_tools
from psglab.ui import theme
from psglab.ui.overview_panel import OverviewPanel
from psglab.ui.signal_view import SignalView
from psglab.utils.formatting import number

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

#: Los eventos del visualizador que le interesan a una herramienta.
_EVENTOS_DEL_MOUSE = (
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseMove,
    QEvent.Type.MouseButtonRelease,
)


class ToolController(QObject):
    """Las herramientas de la ventana y el camino del mouse hasta ellas."""

    #: Un clic en el hipnograma pidió ir a esa ventana (base 0).
    window_requested = Signal(int)
    #: El hipnograma tiene algo nuevo que mostrar.
    histogram_changed = Signal()
    #: El anotador soltó el botón: puede haber un tramo que espera su clase o
    #: un borde corrido. Lleva la herramienta y **si Mayúsculas estaba
    #: apretada al soltar**, que pide preguntar la clase aunque haya una
    #: activa (hito 79).
    annotation_released = Signal(object, bool)
    #: Clic derecho con el anotador: la herramienta, en qué segundo y en qué
    #: punto de la pantalla abrir el menú.
    annotation_menu_requested = Signal(object, float, QPoint)

    def __init__(
        self,
        signal_view: SignalView,
        histogram_view: pg.PlotWidget,
        overview_panel: OverviewPanel,
        readout: QLabel,
        panel_names: frozenset[str],
        parent: QObject | None = None,
    ) -> None:
        """Crea una herramienta por cada una del registro y escucha el mouse.

        Args:
            signal_view: el visualizador, cuyo mouse se traduce y en el que se
                dibujan los overlays.
            histogram_view: el gráfico del hipnograma, cuyos clics son una
                posición de la noche.
            overview_panel: donde se dibuja lo que publica la Übersicht.
            readout: el rótulo de la barra de estado con el número que calcula
                la herramienta activa.
            panel_names: las herramientas que son un panel y no un modo del
                mouse: se prenden solas al abrir un registro y no llevan
                entrada propia en el menú (hito 28).
        """
        super().__init__(parent)
        self._signal_view = signal_view
        self._histogram_view = histogram_view
        self._overview_panel = overview_panel
        self._readout = readout
        self._paneles = panel_names
        self._session: Session | None = None
        self._tools: dict[str, Tool] = {}
        #: La entrada de menú de cada modo del mouse, para poder destildarla al
        #: apagarlo. Las herramientas que son un panel no la tienen.
        self._actions: dict[str, QAction] = {}
        #: **Quién se queda con los clics**, o None. Es la exclusiva activa.
        self._mouse_tool: ViewerTool | None = None
        #: **Quiénes tienen algo que dibujar**, en el orden del registro.
        #:
        #: Son dos campos y no uno desde el hito 45. Con uno solo, una
        #: herramienta que dibuja sin quedarse con el clic —la banda de
        #: amplitud, que declara `exclusive = False` con razón— no entraba en
        #: él, así que su `overlays()` no lo llamaba nadie y tildarla no hacía
        #: nada. Son dos preguntas distintas y tienen dos respuestas.
        self._drawing_tools: list[ViewerTool] = []
        #: Lo último que se le pasó a `signal_view.set_overlays()`. Ver
        #: `_al_cambiar_la_pagina()`.
        self._overlays_dibujados: tuple[Overlay, ...] = ()

        # **Los callbacks se asignan sobre la instancia, nunca sobre la
        # clase**: asignados en la clase quedarían como método ligado y la
        # llamada pasaría un argumento de más.
        for cls in available_tools():
            herramienta = cls()
            herramienta.on_changed = self._on_tool_changed
            if isinstance(herramienta, HistogramTool):
                herramienta.on_window_requested = self.window_requested.emit
            self._tools[cls.name] = herramienta

        # **Se guardan los viewports y no se les pregunta en cada evento**: al
        # cerrarse la ventana, Qt le sigue mandando eventos a este filtro
        # mientras destruye los gráficos, y preguntarle algo a uno a medio
        # destruir es un error de C++.
        self._viewport_de_la_senal = signal_view.viewport()
        self._viewport_del_hipnograma = histogram_view.viewport()
        self._viewport_de_la_senal.installEventFilter(self)
        self._viewport_del_hipnograma.installEventFilter(self)

    # -- Lo que la ventana consulta ------------------------------------------

    @property
    def tools(self) -> Mapping[str, Tool]:
        """Las herramientas por nombre, de sólo lectura."""
        return MappingProxyType(self._tools)

    @property
    def actions(self) -> Mapping[str, QAction]:
        """La entrada de menú de cada modo del mouse, de sólo lectura."""
        return MappingProxyType(self._actions)

    @property
    def mouse_tool(self) -> ViewerTool | None:
        """La herramienta que recibe los clics, o None."""
        return self._mouse_tool

    @property
    def drawn_overlays(self) -> tuple[Overlay, ...]:
        """Lo que está dibujado sobre la señal."""
        return self._overlays_dibujados

    # -- El menú ------------------------------------------------------------

    def build_menu(self, menu: QMenu) -> None:
        """Pone un modo del mouse por herramienta arriba del menú.

        **Es la única vía para activarlas.** Hasta el hito 23 las mismas
        acciones iban también en una barra horizontal debajo del menú, que
        repetía lo mismo y se confundía con él.

        **Una herramienta que tiene panel no recibe entrada propia** (hito 28):
        la que cuenta es la del panel, que `menus._herramientas()` ya puso.
        Con las dos entradas, un menú las mostraba tildadas y el otro no, y
        apagar la herramienta con el panel a la vista lo dejaba vacío.

        Los modos se insertan **antes de la primera entrada** que ya tenga el
        menú, y en el orden del registro.
        """
        primera = menu.actions()[0] if menu.actions() else None
        for nombre, herramienta in self._tools.items():
            if nombre in self._paneles:
                continue
            accion = QAction(herramienta.label, menu)
            accion.setCheckable(True)
            accion.setToolTip(herramienta.description)
            # El menú no muestra tooltips; la barra de estado sí muestra esto
            # mientras el mouse pasa por la entrada.
            accion.setStatusTip(herramienta.description)
            accion.toggled.connect(lambda activa, n=nombre: self.toggle(n, activa))
            menu.insertAction(primera, accion)
            self._actions[nombre] = accion

    # -- El registro --------------------------------------------------------

    def attach(self, session: Session) -> None:
        """Toma la sesión de un registro recién abierto y la escucha.

        Hay que llamar antes a `deactivate_all()`: las herramientas activas
        guardan la sesión que recibieron en `activate()`, y sin soltarlas la
        ocupación seguiría midiendo sobre el registro anterior.

        Las herramientas se enteran solas de los cambios de época y de página:
        es la decisión del hito 6, y por eso nadie tiene que acordarse de
        avisarles.
        """
        self._session = session
        for herramienta in self._tools.values():
            session.add_window_listener(herramienta.on_window_changed)
            session.add_view_listener(herramienta.on_view_changed)
        # **Después de las herramientas**: la ocupación se reancla en su
        # `on_view_changed()`, y las bandas se comparan contra lo ya reanclado.
        session.add_view_listener(self._al_cambiar_la_pagina)

    def activate_panel_tools(self) -> None:
        """Enciende las herramientas que son paneles, no modos del mouse.

        Un panel permanente que arranca apagado es un hueco en la pantalla
        esperando que alguien adivine que hay que apretar un botón. Los modos
        del mouse sí arrancan apagados: sólo puede haber uno y elegirlo es del
        usuario.

        **La pregunta es si tiene panel, no si es exclusiva** (hito 45). Con
        `not exclusive` acá, la banda de amplitud —que no compite por el clic
        pero tampoco es un panel— se tildaba sola al abrir cada registro, y
        como además no se dibujaba, el usuario encontraba una opción encendida
        que no hacía nada.
        """
        if self._session is None:
            return
        for nombre, herramienta in self._tools.items():
            if nombre in self._paneles:
                herramienta.activate(self._session)
                if isinstance(herramienta, ViewerTool) and herramienta not in self._drawing_tools:
                    self._drawing_tools.append(herramienta)
                accion = self._actions.get(nombre)
                if accion is not None:
                    accion.setChecked(True)

    def deactivate_all(self) -> None:
        """Apaga las herramientas y destilda sus entradas.

        El menú tiene que quedar diciendo la verdad: una entrada tildada sobre
        una herramienta apagada es peor que ninguna.
        """
        for accion in self._actions.values():
            accion.setChecked(False)
        for herramienta in self._tools.values():
            herramienta.deactivate()
        self._mouse_tool = None
        self._drawing_tools.clear()
        if self._session is not None:
            self._session.set_active_tool(None)
        self.redraw_overlays()

    def toggle(self, name: str, active: bool) -> None:
        """Activa o desactiva una herramienta, respetando la exclusividad.

        Sin registro no hace nada: una herramienta necesita una sesión.
        """
        herramienta = self._tools.get(name)
        if herramienta is None or self._session is None:
            return

        if active and herramienta.exclusive:
            for otra in self._tools.values():
                if otra is not herramienta and otra.exclusive:
                    otra.deactivate()
                    self._deja_de_dibujar(otra)
                    accion = self._actions.get(otra.name)
                    if accion is not None and accion.isChecked():
                        # **Destildarla también**, o el menú muestra dos modos
                        # del mouse encendidos y sólo uno recibe eventos.
                        accion.setChecked(False)
            self._mouse_tool = (
                herramienta if isinstance(herramienta, ViewerTool) else None
            )

        if active:
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
            self._session.set_active_tool(name if active else None)
        # La herramienta avisó mientras todavía figuraba como activa: sin esto
        # quedaría dibujado lo suyo con ella ya apagada.
        self.redraw_overlays()
        self.update_readout()

    def reset_magnifier_count(self) -> None:
        """Pone en cero el contador de picos de la lupa (V2_F de la Lupa).

        `MagnifierTool.reset_count()` existía y ningún menú lo llamaba, aunque
        la lupa prometía que para eso estaba: la cuenta sólo se podía perder
        cerrando el programa (hito 32).
        """
        lupa = self._tools.get("magnifier")
        if isinstance(lupa, MagnifierTool):
            lupa.reset_count()
            self.update_readout()

    def _deja_de_dibujar(self, herramienta: Tool) -> None:
        """La saca de las que dibujan, si estaba."""
        if isinstance(herramienta, ViewerTool) and herramienta in self._drawing_tools:
            self._drawing_tools.remove(herramienta)

    # -- Lo que se dibuja ---------------------------------------------------

    def redraw_overlays(self) -> None:
        """Dibuja las anotaciones de la página y lo de las herramientas.

        **Las anotaciones se dibujan siempre**, esté activa la herramienta que
        esté: son datos del registro. Hasta que se decidió así, el visualizador
        mostraba lo de **la última herramienta que avisó**, aunque estuviera
        apagada, y las bandas desaparecían al activar la lupa o cuando la
        ocupación se reanclaba al desplazar la página.

        Con «Anotar» activo se dibuja su `overlays()`, que ya trae las bandas
        más la selección en curso.
        """
        self._overlays_dibujados = self._overlays_a_dibujar()
        self._signal_view.set_overlays(self._overlays_dibujados)

    def _overlays_a_dibujar(self) -> tuple[Overlay, ...]:
        """Lo que `redraw_overlays()` dibuja, sin dibujarlo."""
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
            self.redraw_overlays()

    def _on_tool_changed(self, tool: Tool) -> None:
        """Una herramienta avisó de que cambió lo que quiere mostrar."""
        if isinstance(tool, ViewerTool):
            self.redraw_overlays()
        elif isinstance(tool, HistogramTool):
            self.histogram_changed.emit()
        elif isinstance(tool, OverviewTool):
            self._redraw_overview(tool)
        self.update_readout()

    def refresh_overview(self) -> None:
        """Rehace la Übersicht sin que el usuario haya cambiado de ventana.

        **Desde el hito 51 la Übersicht dibuja señal**, así que depende de más
        cosas que la época: de qué canal está seleccionado, de cuáles se ven, de
        su amplitud y de la señal misma, que filtrar reemplaza. Ninguna de esas
        cosas le llega por `on_window_changed()`, y tampoco lo que se scorea o
        se anota, que marca sus ventanas.
        """
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()

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
        self._overview_panel.set_windows(
            herramienta.windows(), colores, self._color_del_contexto(herramienta)
        )
        ancho, alto = herramienta.size_px
        self._overview_panel.set_panel_size(ancho, alto)

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

    def update_readout(self) -> None:
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
                total = number(herramienta.total_percentage(), 1)
                cuantas = f"{len(lineas)} línea" + ("s" if len(lineas) != 1 else "")
                self._readout.setText(f"Ocupación: {cuantas} — {total} % del ancho")
            else:
                self._readout.setText("Ocupación: sin líneas")
            return
        if isinstance(herramienta, MagnifierTool):
            self._readout.setText(f"Picos contados: {herramienta.click_count}")
            return
        if isinstance(herramienta, AnnotatorTool):
            # **Con qué clase se está anotando** (hito 79): sin cartel, es lo
            # único que dice qué va a pasar al soltar.
            clase = herramienta.active_label
            self._readout.setText(
                f"Anotar como «{clase}» · Mayús al soltar para elegir otra"
                if clase is not None
                else "Anotar: se pregunta la clase de cada evento"
            )
            return
        self._readout.setText("")

    # -- El mouse -----------------------------------------------------------

    def eventFilter(self, objeto: QObject, evento: QEvent) -> bool:
        """Traduce los eventos de mouse al vocabulario de las herramientas.

        **Es el único lugar donde un píxel se convierte antes de salir de
        `ui/`.** `ViewerTool` recibe segundos y microvoltios; el histograma
        recibe una fracción de la noche. Ninguna herramienta ve un píxel.

        Nunca se queda con el evento: después sigue a pyqtgraph y al filtro de
        la ventana, que es el que atiende la rueda.
        """
        if objeto is self._viewport_del_hipnograma:
            self._filtrar_histograma(evento)
        elif objeto is self._viewport_de_la_senal and evento.type() in _EVENTOS_DEL_MOUSE:
            self._llevar_el_mouse(evento)
        return False

    def _llevar_el_mouse(self, evento: QMouseEvent) -> None:
        """Un evento de mouse sobre la señal, a las herramientas que lo usan.

        **El movimiento es de todas las que dibujan; los clics, de una sola**
        (hito 79). La banda de amplitud no es exclusiva —no compite por el
        clic— y por eso nunca era `mouse_tool`: sin recibir el movimiento
        quedaba fija en el cero del primer canal.
        """
        herramienta = self._mouse_tool
        siguen_al_mouse = [t for t in self._drawing_tools if t is not herramienta]
        es_movimiento = evento.type() == QEvent.Type.MouseMove
        if herramienta is None and not (siguen_al_mouse and es_movimiento):
            return

        # **En coordenadas de escena, y convertidas por la vista.** Ver
        # `scene_position()`: `scenePosition()` no es la escena de pyqtgraph.
        punto = scene_position(self._signal_view, evento)
        segundos = self._signal_view.seconds_at_pixel(punto.x())
        # **En microvoltios y contra el canal bajo el cursor** (hitos 9 y 45).
        # Hasta el 9 iba la coordenada cruda del gráfico, y la ocupación
        # comparaba su tolerancia de 10 µV contra un rango de 0 a 1; hasta el
        # 45 se medía todo contra el primer canal visible, y la lupa ampliaba
        # siempre ése.
        canal = self._signal_view.channel_at_pixel(punto.y())
        y = self._signal_view.microvolts_at_pixel(punto.y(), canal)

        if isinstance(herramienta, AnnotatorTool):
            # **Un borde se agarra a unos píxeles, no a unos segundos** (hito
            # 52): un segundo son cientos de píxeles con una página de 5 s y
            # ninguno con la noche entera. La herramienta no conoce la
            # pantalla, así que se lo dice este filtro en cada evento.
            segundos_por_pixel = self._signal_view.getPlotItem().vb.viewPixelSize()[0]
            herramienta.set_edge_tolerance(segundos_por_pixel * _PIXELES_DEL_BORDE)

        if es_movimiento:
            for otra in siguen_al_mouse:
                otra.on_mouse_move(segundos, y, canal)
            if herramienta is not None:
                herramienta.on_mouse_move(segundos, y, canal)
            if isinstance(herramienta, AnnotatorTool):
                self._cursor_del_anotador(herramienta, segundos, evento)
            return
        if herramienta is None:
            return
        boton = _BOTONES.get(evento.button(), "left")
        if evento.type() == QEvent.Type.MouseButtonPress:
            herramienta.on_mouse_press(segundos, y, boton, canal)
            if isinstance(herramienta, AnnotatorTool) and boton == "right":
                self.annotation_menu_requested.emit(
                    herramienta, segundos, evento.globalPosition().toPoint()
                )
        else:
            herramienta.on_mouse_release(segundos, y, boton, canal)
            # **Acá se cierra el lazo de V1_F de "Anotación".** La herramienta
            # deja el tramo pendiente y espera que alguien pregunte la clase;
            # hasta el hito 9 no lo hacía nadie, así que se podía arrastrar una
            # selección y no pasaba nada.
            if isinstance(herramienta, AnnotatorTool):
                mayusculas = bool(evento.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.annotation_released.emit(herramienta, mayusculas)

    def _cursor_del_anotador(
        self, herramienta: AnnotatorTool, segundos: float, evento: QMouseEvent
    ) -> None:
        """↔ sobre el borde de una banda, que es lo único que dice que se puede
        arrastrar. Mientras se arrastra, el cursor no cambia."""
        if evento.buttons() != Qt.MouseButton.NoButton:
            return
        if herramienta.edge_at(segundos) is not None:
            self._viewport_de_la_senal.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self._viewport_de_la_senal.unsetCursor()

    def _filtrar_histograma(self, evento: QEvent) -> None:
        """Un clic en el hipnograma es una posición de la noche, no un segundo."""
        if evento.type() != QEvent.Type.MouseButtonPress:
            return
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool):
            return
        caja = self._histogram_view.getPlotItem().vb.sceneBoundingRect()
        if caja.width() <= 0:
            return
        # De escena, igual que `caja`, que es un `sceneBoundingRect()`.
        fraccion = (
            scene_position(self._histogram_view, evento).x() - caja.left()
        ) / caja.width()
        herramienta.on_click(min(1.0, max(0.0, fraccion)))


def scene_position(vista: pg.PlotWidget, evento: QMouseEvent | QWheelEvent) -> QPointF:
    """La posición de un evento de mouse del viewport, en la escena de la vista.

    **No es `evento.scenePosition()`.** En un `QMouseEvent` de widget, Qt llama
    "escena" a la ventana de primer nivel, no a la `QGraphicsScene` de
    pyqtgraph: el valor trae sumado todo lo que hay a la izquierda y arriba del
    gráfico. Con el selector de canales abierto eran 280 px, y la selección del
    anotador arrancaba varios segundos a la derecha del mouse. Los tests no lo
    veían porque armaban el evento con las tres posiciones iguales.
    """
    return vista.mapToScene(evento.position().toPoint())
