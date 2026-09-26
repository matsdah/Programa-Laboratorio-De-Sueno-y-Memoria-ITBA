"""La ventana y lo que se ve: época, página, reproducción, amplitud y foco.

Moverse de ventana, cambiar la escala de tiempo y desplazar la página,
reproducir, ajustar la amplitud, pasar el foco de un panel a otro y las vistas
de canales. Casi todo delega en `Session` y en `SignalView`; lo que queda acá es
elegir qué pedirles y avisar cuando no se puede.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: ningún ID. La navegación y la amplitud tienen su fila en
`core/session.py`, `ui/navigation.py` y `ui/signal_view.py`, que son las que
las implementan.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QInputDialog, QWidget

from psglab.config import (
    MAX_SCALE_UV,
    MIN_SCALE_UV,
    MIN_VIEW_SECONDS,
    VIEW_PAN_FRACTION,
    VIEW_ZOOM_FACTOR,
)
from psglab.core.windows import epoch_to_seconds
from psglab.ui.menus import duration_text, rebuild_views_menu
from psglab.utils.errors import PsgLabError

#: Cuántas muestras tiene que abarcar una página, sumando los canales visibles,
#: para que dibujarla muestre el cursor de espera. Veinte millones son unos
#: 250 ms sobre la máquina de desarrollo: por debajo la espera no se nota, y
#: mostrar el cursor por un parpadeo es peor que no mostrarlo.
_MUESTRAS_PARA_AVISAR = 20_000_000


class ViewMixin:
    """Lo de `MainWindow` que mueve lo que se ve: época, página, amplitud y foco.
    """

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


def _primero_que_toma_foco(widget: QWidget | None) -> QWidget | None:
    """El primer widget, empezando por él mismo, que se puede enfocar con el
    teclado. None si no hay ninguno."""
    if widget is None:
        return None
    for candidato in [widget, *widget.findChildren(QWidget)]:
        if candidato.focusPolicy() & Qt.FocusPolicy.TabFocus and candidato.isEnabled():
            return candidato
    return None
