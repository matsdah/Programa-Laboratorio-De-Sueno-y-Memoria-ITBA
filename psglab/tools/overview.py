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

from psglab.config import OVERVIEW_WINDOWS_AFTER, OVERVIEW_WINDOWS_BEFORE
from psglab.core.session import Session
from psglab.tools.base import Tool
from psglab.tools.registry import register_tool


@register_tool
class OverviewTool(Tool):
    """Panel de contexto con las ventanas vecinas."""

    name = "overview"
    label = "Übersicht"
    description = "Ver la ventana actual junto a las anteriores y las siguientes"
    exclusive = False  # Es un panel: no compite por el clic del mouse.

    def activate(self, session: Session) -> None:
        """Abre el panel de contexto.

        A diferencia de las herramientas del visualizador, un panel tiene su
        propia zona de pantalla y no publica `Overlay`: avisa de que hay que
        repintarlo con `notify_changed()`.
        """
        raise NotImplementedError("Pendiente: preparar el panel y avisar.")

    def deactivate(self) -> None:
        """Cierra el panel."""
        raise NotImplementedError("Pendiente: cerrar el panel y avisar.")

    def on_window_changed(self, window_index: int) -> None:
        """Recentra el contexto alrededor de la ventana nueva."""
        raise NotImplementedError("Pendiente: recentrar el panel y avisar.")

    def set_span(
        self,
        before: int = OVERVIEW_WINDOWS_BEFORE,
        after: int = OVERVIEW_WINDOWS_AFTER,
    ) -> None:
        """Cambia cuántas ventanas se muestran a cada lado (V3_F).

        Las cantidades son independientes: se pueden pedir dos ventanas antes
        y una después, que es lo que pide el pliego.
        """
        raise NotImplementedError("Pendiente: cambiar el alcance y redibujar.")

    def set_size(self, width_px: int, height_px: int) -> None:
        """Cambia el tamaño del panel (V2_F)."""
        raise NotImplementedError("Pendiente: redimensionar el panel.")

    def _draw_window(self, window_index: int, is_current: bool) -> None:
        """Dibuja una de las ventanas del panel.

        La ventana actual se pinta con un fondo más oscuro (V1_F), y sobre
        todas se marcan las anotaciones que caigan dentro, que es lo que
        permite ver los eventos vecinos.
        """
        raise NotImplementedError("Pendiente: dibujar la ventana con sus eventos.")
