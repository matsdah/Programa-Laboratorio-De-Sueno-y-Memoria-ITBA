"""Navegación entre ventanas: botones y posición actual.

El pliego pide poder avanzar y retroceder tanto con las flechas del teclado
como con botones del mouse, y ver siempre en qué ventana se está y cuántas
hay en total.

Los atajos de teclado no se definen acá sino en `shortcuts.py`, para tener un
único lugar donde se sabe qué hace cada tecla.

Cubre del pliego: V1_F de "Navegación en la señal"; la parte de "número de
ventana actual y total" de V1_P de "Visualización".
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class NavigationBar(QWidget):
    """Botones de navegación e indicador de posición en el registro."""

    #: Se emite cuando el usuario pide ir a una ventana concreta (base 0).
    window_requested = Signal(int)

    def __init__(self) -> None:
        """Crea los botones de avance y retroceso y el indicador."""
        raise NotImplementedError("Pendiente: construir los botones y el indicador.")

    def set_position(self, window_index: int, n_windows: int) -> None:
        """Actualiza el indicador de posición.

        Se muestra en base 1, que es como cuenta el usuario: la ventana 0
        interna se muestra como "Ventana 1 de 960".
        """
        raise NotImplementedError("Pendiente: actualizar el texto del indicador.")

    def set_clock_time(self, label: str | None) -> None:
        """Muestra el horario real de la ventana actual, si se conoce.

        Args:
            label: horario ya formateado, o None si el registro no informa el
                horario de inicio.
        """
        raise NotImplementedError("Pendiente: actualizar el horario mostrado.")

    def _on_next(self) -> None:
        """Botón de avance: pide la ventana siguiente."""
        raise NotImplementedError("Pendiente: emitir window_requested con la siguiente.")

    def _on_previous(self) -> None:
        """Botón de retroceso: pide la ventana anterior."""
        raise NotImplementedError("Pendiente: emitir window_requested con la anterior.")
