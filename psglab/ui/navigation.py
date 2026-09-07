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
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class NavigationBar(QWidget):
    """Botones de navegación e indicador de posición en el registro."""

    #: Se emite cuando el usuario pide ir a una ventana concreta (base 0).
    window_requested = Signal(int)

    def __init__(self) -> None:
        """Crea los botones de avance y retroceso y el indicador."""
        super().__init__()
        self._window_index = 0
        self._n_windows = 0

        self._anterior = QPushButton("◀ Anterior")
        self._siguiente = QPushButton("Siguiente ▶")
        self._posicion = QLabel("Sin registro")
        self._horario = QLabel("")

        self._anterior.clicked.connect(self._on_previous)
        self._siguiente.clicked.connect(self._on_next)

        caja = QHBoxLayout(self)
        caja.addWidget(self._anterior)
        caja.addWidget(self._siguiente)
        caja.addStretch(1)
        caja.addWidget(self._posicion)
        caja.addWidget(self._horario)

    def set_position(self, window_index: int, n_windows: int) -> None:
        """Actualiza el indicador de posición.

        Se muestra en base 1, que es como cuenta el usuario: la ventana 0
        interna se muestra como "Ventana 1 de 960".

        **Es el único lugar donde se suma ese 1.** Adentro del programa las
        ventanas son base 0 de punta a punta; convertir al mostrar y no antes es
        lo que evita que la cuenta se corra en algún camino intermedio.
        """
        self._window_index = window_index
        self._n_windows = n_windows
        self._posicion.setText(f"Ventana {window_index + 1} de {n_windows}")
        self._anterior.setEnabled(window_index > 0)
        self._siguiente.setEnabled(window_index < n_windows - 1)

    def set_clock_time(self, label: str | None) -> None:
        """Muestra el horario real de la ventana actual, si se conoce.

        Args:
            label: horario ya formateado, o None si el registro no informa el
                horario de inicio.

        Con `None` se **oculta** en vez de mostrar un guión o un cero: un
        horario vacío en pantalla invita a leerlo como medianoche.
        """
        self._horario.setText(label or "")
        self._horario.setVisible(label is not None)

    def _on_next(self) -> None:
        """Botón de avance: pide la ventana siguiente.

        **Pide, no navega.** El panel no toca la sesión: emite la señal y quien
        la escucha decide. Es lo que mantiene la regla —qué ventana existe y
        cuál no— en `core/`.
        """
        if self._window_index < self._n_windows - 1:
            self.window_requested.emit(self._window_index + 1)

    def _on_previous(self) -> None:
        """Botón de retroceso: pide la ventana anterior."""
        if self._window_index > 0:
            self.window_requested.emit(self._window_index - 1)
