"""Herramienta Übersicht: la ventana actual en su contexto.

Muestra un panel chico con la ventana anterior, la actual y la siguiente
alineadas en la misma línea, con la actual pintada más oscura para
distinguirla. Permite ver si hay eventos justo antes o justo después sin
perder la posición.

Responde a un problema real del scoring: la ventana de 30 segundos es una
grilla arbitraria y los eventos no la respetan. Un huso que arranca en el
segundo 29 se ve cortado, y sin contexto es difícil decidir.

Cubre del pliego: V1_F, V2_F, V3_F de "Herramienta Übersicht".
"""

from dataclasses import dataclass, field

from psglab.config import OVERVIEW_WINDOWS_AFTER, OVERVIEW_WINDOWS_BEFORE
from psglab.core.session import Session
from psglab.core.windows import window_to_samples
from psglab.tools.base import Tool
from psglab.tools.registry import register_tool
from psglab.utils.errors import InvalidScaleError
from psglab.utils.validation import check_index


@dataclass(frozen=True)
class OverviewWindow:
    """Una de las ventanas que el panel tiene que mostrar.

    **Es dato, no dibujo**, por el mismo motivo que `Overlay`: `tools/` no
    conoce Qt, así que la herramienta describe qué hay que pintar y la interfaz
    lo pinta. Sin algo así el panel sería de sólo escritura y no habría con qué
    dibujarlo.

    Attributes:
        index: número de ventana, base 0 como en todo el programa.
        is_current: si es la que el usuario está scoreando. Se pinta con un
            fondo más oscuro (V1_F).
        annotation_labels: clases de los eventos que caen dentro. Es lo que
            permite ver que hay un huso justo antes o justo después.
    """

    index: int
    is_current: bool
    annotation_labels: tuple[str, ...] = field(default_factory=tuple)


@register_tool
class OverviewTool(Tool):
    """Panel de contexto con las ventanas vecinas."""

    name = "overview"
    label = "Übersicht"
    description = "Ver la ventana actual junto a las anteriores y las siguientes"
    exclusive = False  # Es un panel: no compite por el clic del mouse.

    def __init__(self) -> None:
        self._session: Session | None = None
        self._antes: int = OVERVIEW_WINDOWS_BEFORE
        self._despues: int = OVERVIEW_WINDOWS_AFTER
        self._ancho_px: int = 240
        self._alto_px: int = 120
        self._ventanas: tuple[OverviewWindow, ...] = ()

    def activate(self, session: Session) -> None:
        """Abre el panel de contexto.

        A diferencia de las herramientas del visualizador, un panel tiene su
        propia zona de pantalla y no publica `Overlay`: avisa de que hay que
        repintarlo con `notify_changed()`.
        """
        self._session = session
        self._recentrar(session.current_window)
        self.notify_changed()

    def deactivate(self) -> None:
        """Cierra el panel."""
        self._session = None
        self._ventanas = ()
        self.notify_changed()

    def on_window_changed(self, window_index: int) -> None:
        """Recentra el contexto alrededor de la ventana nueva."""
        if self._session is None:
            return
        self._recentrar(window_index)
        self.notify_changed()

    def refresh(self) -> None:
        """Vuelve a derivar las ventanas sin que el usuario haya navegado.

        Hace falta porque `_ventanas` es una caché y hasta acá sólo la
        invalidaban navegar, `set_span()` y `set_size()`. **Los eventos
        anotados también cambian lo que el panel muestra** (V3_F: ver que hay un
        huso justo antes), y anotar no mueve de ventana: sin esto, el evento
        recién creado no aparecía hasta la próxima flecha.

        Es la contraparte de `HistogramTool.redraw()`, que existe por el mismo
        motivo.
        """
        if self._session is None:
            return
        self._recentrar(self._session.current_window)
        self.notify_changed()

    def windows(self) -> tuple[OverviewWindow, ...]:
        """Las ventanas que el panel tiene que mostrar, en orden.

        Es la contraparte de `ViewerTool.overlays()` para un panel: describe qué
        dibujar sin dibujarlo. Devuelve la tupla vacía si el panel está cerrado.
        """
        return self._ventanas

    @property
    def size_px(self) -> tuple[int, int]:
        """Tamaño pedido para el panel, en píxeles (V2_F).

        Es lo único que esta herramienta cuenta en píxeles, y no es una
        coordenada de señal: es cuánto lugar ocupa el panel en la pantalla, que
        el usuario elige.
        """
        return (self._ancho_px, self._alto_px)

    def _recentrar(self, window_index: int) -> None:
        """Rearma la lista de ventanas alrededor de la actual.

        Recorta contra los bordes del registro: en la primera ventana no hay
        anterior, y pedirla daría un índice negativo que `Scoring` rechazaría.
        """
        if self._session is None:
            self._ventanas = ()
            return

        total = self._session.n_windows
        desde = max(0, window_index - self._antes)
        hasta = min(total - 1, window_index + self._despues)
        self._ventanas = tuple(
            self._describir(indice, indice == window_index)
            for indice in range(desde, hasta + 1)
        )

    def _describir(self, window_index: int, is_current: bool) -> OverviewWindow:
        """Arma la descripción de una ventana con los eventos que caen dentro."""
        assert self._session is not None
        frecuencia = self._session.recording.sampling_rate
        inicio, fin = window_to_samples(window_index, frecuencia)
        etiquetas = tuple(
            anotacion.label
            for anotacion in self._session.annotations.in_range(inicio, fin)
        )
        return OverviewWindow(
            index=window_index, is_current=is_current, annotation_labels=etiquetas
        )

    def set_span(
        self,
        before: int = OVERVIEW_WINDOWS_BEFORE,
        after: int = OVERVIEW_WINDOWS_AFTER,
    ) -> None:
        """Cambia cuántas ventanas se muestran a cada lado (V3_F).

        Las cantidades son independientes: se pueden pedir dos ventanas antes
        y una después, que es lo que pide el pliego.

        Raises:
            InvalidScaleError: si alguna de las dos es negativa. Cero es válido
                y significa "no mostrar ese lado".
        """
        for nombre, valor in (("before", before), ("after", after)):
            check_index(
                valor,
                error=InvalidScaleError,
                message="El alcance del panel de contexto no es válido.",
                details=f"{nombre} tiene que ser una cantidad de ventanas no negativa.",
            )
            # `check_index` sólo comprueba que sea entero; el rango va acá. Un
            # alcance negativo daría una lista de ventanas vacía o al revés, sin
            # que nada avisara.
            if valor < 0:
                raise InvalidScaleError(
                    "El alcance del panel de contexto no es válido.",
                    details=f"{nombre} = {valor}, se esperaba cero o más ventanas.",
                )
        self._antes, self._despues = int(before), int(after)
        if self._session is not None:
            self._recentrar(self._session.current_window)
        self.notify_changed()

    def set_size(self, width_px: int, height_px: int) -> None:
        """Cambia el tamaño del panel (V2_F).

        Raises:
            InvalidScaleError: si alguna medida no es positiva. Un panel de
                ancho o alto cero no se ve.
        """
        for nombre, valor in (("width_px", width_px), ("height_px", height_px)):
            check_index(
                valor,
                error=InvalidScaleError,
                message="El tamaño del panel de contexto no sirve para dibujarlo.",
                details=f"{nombre} tiene que ser un número entero de píxeles.",
            )
            if valor <= 0:
                raise InvalidScaleError(
                    "El tamaño del panel de contexto no sirve para dibujarlo.",
                    details=f"{nombre} = {valor}, se esperaba un número positivo.",
                )
        self._ancho_px, self._alto_px = int(width_px), int(height_px)
        self.notify_changed()

    def _draw_window(self, window_index: int, is_current: bool) -> None:
        """Dibuja una de las ventanas del panel.

        La ventana actual se pinta con un fondo más oscuro (V1_F), y sobre
        todas se marcan las anotaciones que caigan dentro, que es lo que
        permite ver los eventos vecinos.

        **No dibuja: describe.** `tools/` no conoce Qt, así que lo que arma es
        el dato que la interfaz va a pintar. El nombre quedó del esqueleto y se
        conserva para no romper la trazabilidad del pliego; lo que devuelve
        `windows()` es lo que se dibuja.
        """
        self._ventanas = (*self._ventanas, self._describir(window_index, is_current))
