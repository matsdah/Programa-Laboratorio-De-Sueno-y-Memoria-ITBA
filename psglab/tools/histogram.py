"""Histograma (hipnograma) de la noche completa.

Muestra la evolución de las fases a lo largo del registro. Es la vista que
resume una noche entera en una sola imagen, y la principal forma de navegar:
un clic en el histograma lleva a esa ventana (V4_F).

Dos detalles del pliego que condicionan la implementación:

    - El histograma tiene el tamaño total de la noche desde el arranque, y lo
      no anotado queda en blanco. Así el usuario puede scorear una parte
      alejada del registro sin haber pasado por las anteriores.
    - El orden vertical, de arriba hacia abajo, lo fija el pliego:
      W, REM, S1, S2, S3, S4, MT. Ese orden lo define
      `psglab.core.nomenclature.STAGES_BY_NOMENCLATURE`, para que cambiar de
      nomenclatura reordene el eje solo (V3_F).

Cubre del pliego: V1_P, V2_F, V3_F, V4_F de "Histograma".
"""

from collections.abc import Callable

from psglab.core.nomenclature import SleepStage
from psglab.core.session import Session
from psglab.tools.base import Tool
from psglab.tools.registry import register_tool
from psglab.utils.errors import InvalidScaleError, PsgLabError
from psglab.utils.validation import check_finite


@register_tool
class HistogramTool(Tool):
    """Hipnograma navegable de todo el registro."""

    name = "histogram"
    label = "Histograma"
    description = "Ver el hipnograma de la noche y navegar haciendo clic"
    exclusive = False  # Es un panel permanente, no un modo del mouse.

    #: Callback que la ventana principal conecta para enterarse de que el
    #: usuario hizo clic y quiere ir a otra ventana. Se usa un callback y no
    #: una señal de Qt porque `Tool` no hereda de QObject: las herramientas
    #: son objetos comunes, y así se las puede testear sin interfaz gráfica.
    #:
    #: **Se asigna sobre la instancia, nunca sobre la clase.** Asignado en la
    #: clase, el protocolo de descriptores lo convierte en método ligado y la
    #: llamada le pasaría `self` de más. Vale lo mismo para `Tool.on_changed`.
    on_window_requested: Callable[[int], None] | None = None

    def __init__(self) -> None:
        self._session: Session | None = None
        #: Una fase por ventana, en orden. Es lo que el panel dibuja.
        self._barras: tuple[SleepStage, ...] = ()
        self._ventana_actual: int = 0
        self._eje_en_hora: bool = False

    def activate(self, session: Session) -> None:
        """Muestra el histograma del registro abierto."""
        self._session = session
        self._ventana_actual = session.current_window
        self.redraw()

    def deactivate(self) -> None:
        """Oculta el histograma."""
        self._session = None
        self._barras = ()
        self.notify_changed()

    def bars(self) -> tuple[SleepStage, ...]:
        """La fase de cada ventana, en orden, para que el panel la dibuje.

        Es la contraparte de `ViewerTool.overlays()` para un panel: describe qué
        pintar sin pintarlo, porque `tools/` no conoce Qt.

        **Tiene el largo de la noche entera desde el arranque** y las ventanas
        sin scorear salen como `UNSCORED`, que el panel deja en blanco (V1_P).
        Es lo que permite scorear una parte alejada del registro sin haber
        pasado por las anteriores.
        """
        return self._barras

    @property
    def current_window(self) -> int:
        """La ventana marcada como actual en el histograma."""
        return self._ventana_actual

    @property
    def uses_clock_time(self) -> bool:
        """Si el eje horizontal está en hora real o en número de ventana."""
        return self._eje_en_hora

    def redraw(self) -> None:
        """Redibuja el histograma completo a partir del scoring actual.

        Las ventanas sin scorear se dejan en blanco (V1_P).
        """
        if self._session is None:
            self._barras = ()
        else:
            self._barras = tuple(self._session.scoring.stages())
        self.notify_changed()

    def update_window(self, window_index: int) -> None:
        """Actualiza una sola ventana del histograma.

        Se usa al scorear: redibujar la noche entera en cada tecla haría
        pesado el trabajo, que es justamente lo que el usuario hace cientos de
        veces seguidas.
        """
        if self._session is None:
            return
        fases = list(self._barras)
        if not 0 <= window_index < len(fases):
            return
        fases[window_index] = self._session.scoring.get(window_index).stage
        self._barras = tuple(fases)
        self.notify_changed()

    def set_time_axis(self, use_clock_time: bool) -> None:
        """Elige el eje horizontal (V2_F).

        Args:
            use_clock_time: True para mostrar la hora real de la noche, que
                sólo es posible si el registro informa su horario de inicio.
                False numera de la ventana 1 a VENMAX.

        Raises:
            PsgLabError: si se pide la hora real y el registro no informa su
                horario de inicio. Inventar una hora de comienzo sería peor que
                negarse: el investigador leería el eje como si fuera real.
        """
        if use_clock_time:
            if self._session is None or self._session.recording.start_time is None:
                raise InvalidScaleError(
                    "Este registro no informa a qué hora empezó, así que el eje no "
                    "puede mostrar la hora real de la noche.",
                    details="Recording.start_time es None.",
                )
        self._eje_en_hora = bool(use_clock_time)
        self.notify_changed()

    def on_window_changed(self, window_index: int) -> None:
        """El usuario navegó: se mueve el indicador de posición.

        `Tool` la declara sin hacer nada; el histograma la sobrescribe porque es
        de las que sí quieren enterarse.
        """
        self.mark_current_window(window_index)

    def on_click(self, x_fraction: float) -> None:
        """Salta a la ventana del punto donde se hizo clic (V4_F).

        No hereda los eventos de mouse de `ViewerTool` porque el histograma
        tiene su propio sistema de coordenadas: acá `x` no son segundos dentro
        de una ventana de 30 s, sino una posición dentro de la noche entera.

        Args:
            x_fraction: posición horizontal del clic, de 0 (inicio del
                registro) a 1 (final).
        """
        if self._session is None or not self._barras:
            return
        check_finite(
            x_fraction,
            error=InvalidScaleError,
            message="No se pudo interpretar el clic en el histograma.",
            details="x_fraction tiene que ser un número finito entre 0 y 1.",
        )
        total = len(self._barras)
        # Se recorta contra los bordes en vez de rechazar: un clic en el borde
        # derecho da exactamente 1.0, y `int(1.0 * total)` sería una ventana que
        # no existe.
        indice = min(total - 1, max(0, int(x_fraction * total)))
        if self.on_window_requested is not None:
            self.on_window_requested(indice)

    def mark_current_window(self, window_index: int) -> None:
        """Marca en el histograma la ventana que se está viendo."""
        self._ventana_actual = window_index
        self.notify_changed()
