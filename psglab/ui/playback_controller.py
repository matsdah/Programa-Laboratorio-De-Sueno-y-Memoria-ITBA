"""La reproducción: el cursor, el reloj y cómo mueven la página y la época.

**Desde el hito 27 el recorrido se cuenta desde el medio del gráfico**: un
cursor marca el instante que se reproduce, la página se centra en él y la
época actual es la suya. Al pausar, el usuario queda parado en la época que
estaba mirando y la scorea ahí. Hasta ese hito era al revés, por decisión del
hito 24: reproducir sólo movía la vista, igual que Mayús+→, y la época no se
tocaba. El usuario la revisó el 18 de septiembre de 2026. En pausa todo sigue
como antes: las flechas mueven la página lo mínimo.

Las piezas son tres, y cada una en su lugar:

- **El reloj** (`ui/playback.py`) mide tiempo real y avisa cuántos segundos
  avanzar. No conoce la sesión.
- **La regla** —la página centrada en el cursor, la época la del cursor, qué
  pasa en los bordes— es de `Session.move_playhead()`, en `core/`.
- **Este controlador** junta las dos: lleva el cursor, redibuja lo que cambió
  y avisa cuando la época cambia o se llega al final.

**Es una pieza con estado propio** (hito 79). Hasta ahí vivía en el mixin
`window_view.py`, y el cursor era `MainWindow._cabezal`, que leían cinco
métodos de tres archivos. Ahora es `playhead`, y lo que es de la ventana le
llega por señales de Qt:

- `epoch_changed`: el cursor pasó a otra época, y la ventana refleja la época
  en la franja, el panel de scoring y la barra de estado.
- `reached_end`: el cursor llegó al final del registro.
- `failed`: no se pudo mover el cursor o cambiar la velocidad. El cartel es
  de la ventana.

Por eso se testea sin `MainWindow`, en `tests/test_playback_controller.py`.

Cubre del pliego: V1_F de "Navegación en la señal" (avanzar por el registro sin
apretar una tecla por página), junto con `ui/playback.py`.
"""

from PySide6.QtCore import QObject, Signal

from psglab.core.session import Session
from psglab.core.windows import epoch_to_seconds
from psglab.ui.playback import PlaybackClock
from psglab.ui.signal_view import SignalView
from psglab.utils.errors import PsgLabError


class PlaybackController(QObject):
    """El cursor de la reproducción y lo que mueve."""

    #: El cursor pasó a otra época: hay que reflejarla fuera del gráfico.
    epoch_changed = Signal()
    #: El cursor llegó al final del registro y la reproducción se detuvo.
    reached_end = Signal()
    #: Algo no se pudo hacer: el error y qué se intentaba, como lo espera
    #: `MainWindow._show_error()`.
    failed = Signal(object, str)

    def __init__(self, signal_view: SignalView, parent: QObject | None = None) -> None:
        """Arma el reloj, todavía sin registro.

        Args:
            signal_view: el visualizador, que dibuja la página y la línea del
                cursor.
        """
        super().__init__(parent)
        self._signal_view = signal_view
        self._session: Session | None = None
        #: El instante que se está reproduciendo, en segundos desde el inicio
        #: del registro, o None en pausa.
        self._cabezal: float | None = None
        self._reloj = PlaybackClock(self)
        self._reloj.advanced.connect(self.step)
        self._reloj.playing_changed.connect(self._al_cambiar_la_reproduccion)

    # -- Lo que la ventana consulta ------------------------------------------

    @property
    def clock(self) -> PlaybackClock:
        """El reloj: su `playing_changed` es lo que sigue el botón ⏯."""
        return self._reloj

    @property
    def playhead(self) -> float | None:
        """El instante que se reproduce, o None en pausa.

        **Mientras hay cursor la página es suya**: moverse de época, desplazar
        o acercar tienen que pasar por acá (`jump_to_window()`, `move_to()`),
        o el paso siguiente del reloj deshace lo que hicieron.
        """
        return self._cabezal

    @property
    def is_playing(self) -> bool:
        """Si el reloj está corriendo."""
        return self._reloj.is_playing

    # -- El registro --------------------------------------------------------

    def attach(self, session: Session | None) -> None:
        """Toma la sesión de un registro recién abierto, o la suelta.

        **Detiene la reproducción antes**: avanzaba sobre la página del
        registro anterior.
        """
        self.stop()
        self._session = session

    # -- Reproducir y pausar ------------------------------------------------

    def toggle(self) -> None:
        """Reproduce o pausa. Sin registro no hace nada.

        **Arranca desde el centro de la época actual**, que es la que se está
        scoreando. Con la página de 30 s ya está centrada, así que no hay
        salto; después de «Primera ventana» el cursor arranca cerca del borde
        izquierdo y la página no se mueve hasta que el cursor llega al medio.

        Ya no se niega con la página al final ni con el registro entero en
        pantalla, como hasta el hito 27: el cursor avanza adentro de la página
        cuando ésta no se puede mover, así que siempre hay por dónde seguir.
        """
        if self._reloj.is_playing:
            self._reloj.stop()
            return
        if self._session is None:
            return
        if not self.jump_to_window(self._session.current_window):
            return
        self._reloj.start()

    def stop(self) -> None:
        """Detiene la reproducción, si estaba corriendo, y saca el cursor.

        **Saca el cursor aunque el reloj no corriera**: un paso pedido a mano
        —el banco de medición los pide sin arrancar la reproducción— deja un
        cursor puesto, y el reloj detenido no avisa nada al detenerse otra vez.
        """
        self._reloj.stop()
        self._al_cambiar_la_reproduccion(False)

    def set_speed(self, speed: float) -> None:
        """Lo que pide el selector de velocidad. Vale también reproduciendo."""
        try:
            self._reloj.speed = speed
        except PsgLabError as error:
            self.failed.emit(error, "cambiar la velocidad")

    def _al_cambiar_la_reproduccion(self, reproduciendo: bool) -> None:
        """Al pausar se va el cursor.

        La banda de la época queda como referencia: es lo que se scorea, y
        desde el hito 27 es la época que pasaba por el medio al pausar.
        """
        if not reproduciendo:
            self._cabezal = None
            self._signal_view.set_playhead(None)

    # -- El cursor ----------------------------------------------------------

    def step(self, seconds: float) -> None:
        """Un paso de la reproducción: el cursor avanza esos segundos.

        Se detiene al llegar al final **del registro**, no de la página: en el
        último tramo la página ya no se mueve y el cursor sigue hasta el borde,
        que es lo que recorre las últimas épocas. También se detiene si el
        cursor no se pudo ubicar: un error repetido veinticinco veces por
        segundo sería un cartel tras otro.

        Un paso sin cursor —el banco de medición los pide sin arrancar la
        reproducción— parte del medio de lo que se ve.
        """
        if self._session is None:
            self._reloj.stop()
            return
        desde = (
            self._cabezal
            if self._cabezal is not None
            else self._session.viewport.center_seconds
        )
        if not self.move_to(desde + seconds):
            self._reloj.stop()
            return
        if self._cabezal is not None and (
            self._cabezal >= self._session.recording.duration_seconds
        ):
            self._reloj.stop()
            self.reached_end.emit()

    def move_to(self, seconds: float) -> bool:
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
            self._cabezal = self._session.move_playhead(seconds)
        except PsgLabError as error:
            self.failed.emit(error, "mover la reproducción")
            return False
        if self._session.viewport != pagina:
            self._signal_view.draw_viewport()
        self._signal_view.set_playhead(self._cabezal)
        if self._session.current_window != epoca:
            self.epoch_changed.emit()
        return True

    def jump_to_window(self, window_index: int) -> bool:
        """Lleva el cursor al centro de esa época (hito 27).

        Es lo que hacen las flechas, los botones, la franja y el hipnograma
        mientras se reproduce: la reproducción sigue desde ahí.

        Una época que no existe se ignora, como la flecha en los bordes: la
        piden controles que ya recortan contra el registro, y llevar el cursor
        al final por un índice de más detendría la reproducción sin que el
        usuario lo hubiera pedido.

        Returns:
            Si el cursor se movió.
        """
        if self._session is None or not 0 <= window_index < self._session.n_windows:
            return False
        inicio, fin = epoch_to_seconds(window_index, self._session.recording.sampling_rate)
        return self.move_to((inicio + fin) / 2)
