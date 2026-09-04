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

from psglab.core.session import Session
from psglab.tools.base import Tool
from psglab.tools.registry import register_tool


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

    def activate(self, session: Session) -> None:
        """Muestra el histograma del registro abierto."""
        raise NotImplementedError("Pendiente: crear el panel del histograma.")

    def deactivate(self) -> None:
        """Oculta el histograma."""
        raise NotImplementedError("Pendiente: ocultar el panel.")

    def redraw(self) -> None:
        """Redibuja el histograma completo a partir del scoring actual.

        Las ventanas sin scorear se dejan en blanco (V1_P).
        """
        raise NotImplementedError("Pendiente: dibujar las barras de cada ventana.")

    def update_window(self, window_index: int) -> None:
        """Actualiza una sola ventana del histograma.

        Se usa al scorear: redibujar la noche entera en cada tecla haría
        pesado el trabajo, que es justamente lo que el usuario hace cientos de
        veces seguidas.
        """
        raise NotImplementedError("Pendiente: redibujar sólo la barra de esa ventana.")

    def set_time_axis(self, use_clock_time: bool) -> None:
        """Elige el eje horizontal (V2_F).

        Args:
            use_clock_time: True para mostrar la hora real de la noche, que
                sólo es posible si el registro informa su horario de inicio.
                False numera de la ventana 1 a VENMAX.
        """
        raise NotImplementedError("Pendiente: cambiar el eje horizontal.")

    def on_click(self, x_fraction: float) -> None:
        """Salta a la ventana del punto donde se hizo clic (V4_F).

        No hereda los eventos de mouse de `ViewerTool` porque el histograma
        tiene su propio sistema de coordenadas: acá `x` no son segundos dentro
        de una ventana de 30 s, sino una posición dentro de la noche entera.

        Args:
            x_fraction: posición horizontal del clic, de 0 (inicio del
                registro) a 1 (final).
        """
        raise NotImplementedError("Pendiente: convertir la fracción a ventana y avisar por el callback.")

    def mark_current_window(self, window_index: int) -> None:
        """Marca en el histograma la ventana que se está viendo."""
        raise NotImplementedError("Pendiente: mover el indicador de posición.")
