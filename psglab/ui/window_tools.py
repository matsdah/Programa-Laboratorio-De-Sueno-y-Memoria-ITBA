"""La ventana y sus herramientas: el mouse, lo que dibujan y lo que informan.

Todo lo que va y viene entre `SignalView` y las herramientas de `tools/`: el
filtro de eventos que traduce píxeles a segundos y µV, la rueda que acerca y
desplaza la página, qué herramientas están encendidas y cuál se queda con el
mouse, los overlays que dibujan y la lectura de la barra de estado.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: V3_F de "Ocupación de la página" (`_update_tool_readout`
muestra el porcentaje) y V2_F de "Herramienta Lupa" (el contador de picos,
también en `_update_tool_readout`). El cálculo está en `tools/`; lo que vive
acá es la mitad que lo lleva a la pantalla.
"""

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from psglab.config import VIEW_ZOOM_FACTOR
from psglab.tools.annotator import AnnotatorTool, annotation_bands
from psglab.tools.base import Overlay, Tool, ViewerTool
from psglab.tools.histogram import HistogramTool
from psglab.tools.magnifier import MagnifierTool
from psglab.tools.occupancy import OccupancyTool
from psglab.tools.overview import OverviewTool
from psglab.ui import theme

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


class ToolsMixin:
    """Lo de `MainWindow` que conecta el mouse y las herramientas.
    
    Usa de la ventana: `_tools`, `_tool_actions`, `_mouse_tool`, `_drawing_tools`,
    `_overlays_dibujados`, `signal_view`, `overview_panel` y la sesión.
    """

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
