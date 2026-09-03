"""Herramienta de ocupación de la página.

El usuario dibuja líneas con el mouse sobre la ventana y la herramienta
calcula qué porcentaje del ancho de la pantalla ocupan, sumando el aporte de
todas.

La definición del pliego es una **proyección sobre el eje horizontal**, no el
largo de la línea:

    - una línea vertical ocupa 0 %
    - una línea de borde izquierdo a borde derecho ocupa 100 %
    - una línea horizontal de media pantalla ocupa 50 %
    - la misma línea en diagonal ocupa menos que 50 %, porque lo que cuenta
      es su sombra sobre el eje horizontal

Es decir: para una línea de extremos (x1, y1) y (x2, y2), el aporte es
|x2 - x1| dividido por el ancho de la ventana. El ángulo no entra en la
cuenta como tal; entra a través de la diferencia de las x.

Cubre del pliego: V1_F, V2_F, V3_F, V4_F, V5_F de "Herramienta de ocupación
de la página".
"""

from dataclasses import dataclass

from psglab.core.session import Session
from psglab.tools.base import ViewerTool
from psglab.tools.registry import register_tool


@dataclass
class OccupancyLine:
    """Una línea dibujada por el usuario.

    Las coordenadas se guardan en fracción del ancho y del alto de la ventana
    (de 0 a 1) y no en píxeles: así el porcentaje sigue siendo correcto si el
    usuario redimensiona la ventana del programa.
    """

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def horizontal_fraction(self) -> float:
        """Fracción del ancho que ocupa la proyección de la línea (0 a 1)."""
        raise NotImplementedError("Pendiente: devolver abs(x2 - x1).")


@register_tool
class OccupancyTool(ViewerTool):
    """Medidor de ocupación horizontal por líneas dibujadas a mano."""

    name = "occupancy"
    label = "Ocupación"
    description = "Dibujar líneas y medir qué porcentaje del ancho ocupan"

    def activate(self, session: Session) -> None:
        """Activa el modo de dibujo de líneas (V1_F)."""
        raise NotImplementedError("Pendiente: activar el modo de dibujo.")

    def deactivate(self) -> None:
        """Sale del modo de dibujo. Las líneas dibujadas se conservan."""
        raise NotImplementedError("Pendiente: salir del modo de dibujo.")

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Empieza una línea nueva, o borra una existente si se hizo clic encima.

        El pliego pide las dos cosas con el mismo gesto (V1_F y V5_F): si el
        clic cae sobre una línea ya dibujada, la borra; si no, empieza una
        línea nueva.
        """
        raise NotImplementedError("Pendiente: iniciar la línea o borrar la que está debajo.")

    def on_mouse_move(self, x: float, y: float) -> None:
        """Muestra la línea en curso mientras el usuario arrastra."""
        raise NotImplementedError("Pendiente: actualizar la vista previa de la línea.")

    def on_mouse_release(self, x: float, y: float, button: str) -> None:
        """Cierra la línea y actualiza el porcentaje mostrado (V3_F)."""
        raise NotImplementedError("Pendiente: guardar la línea y recalcular el total.")

    def on_window_changed(self, window_index: int) -> None:
        """Borra las líneas al cambiar de ventana (V5_F).

        Las líneas miden algo de la ventana que se estaba mirando, así que no
        tienen sentido en la siguiente.
        """
        raise NotImplementedError("Pendiente: limpiar las líneas de la ventana anterior.")

    def add_line(self, line: OccupancyLine) -> None:
        """Agrega una línea ya construida.

        Existe además del dibujo con el mouse para poder testear el cálculo del
        porcentaje sin simular gestos del mouse.
        """
        raise NotImplementedError("Pendiente: agregar la línea a la lista.")

    def lines(self) -> list[OccupancyLine]:
        """Líneas dibujadas en la ventana actual."""
        raise NotImplementedError("Pendiente: devolver las líneas.")

    def line_percentage(self, line: OccupancyLine) -> float:
        """Porcentaje de ocupación horizontal de una línea (V2_F)."""
        raise NotImplementedError("Pendiente: convertir la fracción horizontal a porcentaje.")

    def total_percentage(self) -> float:
        """Porcentaje sumado de todas las líneas de la ventana (V4_F).

        Ojo con un caso que hay que definir con el cliente: si dos líneas se
        superponen horizontalmente, ¿la zona compartida se cuenta una vez o
        dos? El pliego dice "sumar la distancia horizontal total", así que por
        ahora se suman los aportes sin descontar la superposición.
        """
        raise NotImplementedError("Pendiente: sumar los aportes de todas las líneas.")

    def clear(self) -> None:
        """Borra todas las líneas."""
        raise NotImplementedError("Pendiente: vaciar la lista de líneas.")
