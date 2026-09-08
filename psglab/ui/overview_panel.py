"""Panel de contexto: la ventana actual junto a sus vecinas (Übersicht).

`OverviewTool` describe qué hay que mostrar —una lista de `OverviewWindow` con
su número, si es la actual y qué eventos caen adentro— y **no dibuja nada**,
porque `tools/` no conoce Qt. Este módulo es la otra mitad: recibe esa lista y
la pinta.

Hasta el hito 9 esa otra mitad no existía. La herramienta estaba completa y
testeada, `OverviewTool` no se mencionaba en ninguna parte de `psglab/ui/`, y
el pliego pedía tres cosas que en el programa corriendo no se podían ver.

**Se dibuja con `QPainter` y no con pyqtgraph.** Son unos pocos rectángulos con
texto, sin ejes ni escalas ni zoom: un `PlotWidget` traería un sistema de
coordenadas que acá no significa nada. El visualizador y el histograma sí lo
necesitan, porque grafican señal.

El cálculo de dónde va cada rectángulo está separado del pintado, en
`rectangles()`, para poder afirmarlo sin mirar una pantalla: qué ventanas
entran, cuál está marcada como actual y en qué orden salen es una decisión, no
un dibujo.

Cubre del pliego: V1_F, V2_F, V3_F de "Übersicht (panel de contexto)".
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from psglab.tools.overview import OverviewWindow

#: Separación entre rectángulos, en píxeles. Sin ella las ventanas se leen como
#: una sola barra continua y se pierde justamente lo que el panel muestra.
_SEPARACION_PX: int = 4

#: Alto de la franja donde se marcan los eventos anotados, como fracción del
#: alto del rectángulo. Van abajo para no tapar el número de ventana.
_FRANJA_DE_EVENTOS: float = 0.25

#: Colores del panel. No salen de `config.py` porque el pliego no fija ninguno:
#: pide que la ventana actual se distinga, y elegir con qué es del programa.
_FONDO = QColor("#f2f2f2")
_FONDO_ACTUAL = QColor("#c8d8ec")
_BORDE = QColor("#8a8a8a")
_BORDE_ACTUAL = QColor("#2c5a8c")
_TEXTO = QColor("#333333")


class OverviewPanel(QWidget):
    """Dibuja las ventanas vecinas que publica `OverviewTool`."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ningún registro abierto."""
        super().__init__(parent)
        self._windows: tuple[OverviewWindow, ...] = ()
        #: Colores por clase de evento, que los pide la ventana principal al
        #: `AnnotationSet`: la herramienta manda los nombres, no los colores.
        self._colors: dict[str, str] = {}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.set_panel_size(480, 90)
        self.setToolTip(
            "Contexto: la ventana actual junto a las anteriores y las siguientes"
        )

    # -- Lo que le da la ventana principal ----------------------------------

    def set_windows(
        self,
        windows: tuple[OverviewWindow, ...],
        colors: dict[str, str] | None = None,
    ) -> None:
        """Recibe qué ventanas mostrar y con qué color cada clase de evento.

        Args:
            windows: lo que publica `OverviewTool.windows()`, en su orden.
            colors: color por clase de evento. La herramienta manda los nombres
                de las clases y no sus colores, porque los colores viven en
                `AnnotationSet`, que es de `core/`.
        """
        self._windows = tuple(windows)
        if colors is not None:
            self._colors = dict(colors)
        self.update()

    def set_panel_size(self, width_px: int, height_px: int) -> None:
        """Fija el tamaño del panel (V2_F).

        La validación vive en `OverviewTool.set_size()`, que es donde está la
        regla; acá sólo se obedece. Se fija el alto y se deja el ancho como
        mínimo, para que el panel siga acompañando a la ventana si el usuario
        la agranda.
        """
        self.setMinimumWidth(int(width_px))
        self.setFixedHeight(int(height_px))

    # -- Dónde va cada cosa, que sí se puede afirmar sin mirar --------------

    def rectangles(self) -> list[tuple[OverviewWindow, QRectF]]:
        """Cada ventana con el rectángulo que le toca, en orden.

        Está separado de `paintEvent()` a propósito: **cuántas ventanas entran,
        cuál es la actual y en qué orden van es una decisión y se testea**; los
        píxeles que salen por pantalla, no.

        Devuelve una lista vacía si no hay nada que mostrar, que es el estado
        antes de abrir un registro.
        """
        if not self._windows:
            return []
        cuantas = len(self._windows)
        total = self.width()
        ancho = (total - _SEPARACION_PX * (cuantas - 1)) / cuantas
        if ancho <= 0:
            return []
        alto = float(self.height())
        return [
            (
                ventana,
                QRectF(indice * (ancho + _SEPARACION_PX), 0.0, ancho, alto),
            )
            for indice, ventana in enumerate(self._windows)
        ]

    @property
    def current_index(self) -> int | None:
        """Número de la ventana marcada como actual, o None si no hay ninguna.

        Base 0, como en todo el programa. La conversión a base 1 se hace al
        escribirla en el rectángulo.
        """
        for ventana in self._windows:
            if ventana.is_current:
                return ventana.index
        return None

    # -- El dibujo ----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        """Pinta los rectángulos. Lo único de este módulo que no se testea."""
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        for ventana, caja in self.rectangles():
            actual = ventana.is_current
            pintor.setBrush(QBrush(_FONDO_ACTUAL if actual else _FONDO))
            pintor.setPen(QPen(_BORDE_ACTUAL if actual else _BORDE, 2 if actual else 1))
            pintor.drawRect(caja)

            pintor.setPen(QPen(_TEXTO))
            # Base 1 al mostrar, como en la barra de estado y en los archivos
            # de salida.
            pintor.drawText(
                caja,
                Qt.AlignmentFlag.AlignCenter,
                str(ventana.index + 1),
            )
            self._pintar_eventos(pintor, ventana, caja)
        pintor.end()

    def _pintar_eventos(
        self, pintor: QPainter, ventana: OverviewWindow, caja: QRectF
    ) -> None:
        """La franja de abajo, con una marca por clase de evento (V3_F).

        Es lo que permite ver que hay un huso justo antes o justo después sin
        navegar hasta ahí.
        """
        if not ventana.annotation_labels:
            return
        alto = caja.height() * _FRANJA_DE_EVENTOS
        ancho = caja.width() / len(ventana.annotation_labels)
        for posicion, clase in enumerate(ventana.annotation_labels):
            color = QColor(self._colors.get(clase, "#999999"))
            pintor.setBrush(QBrush(color))
            pintor.setPen(QPen(color))
            pintor.drawRect(
                QRectF(
                    caja.left() + posicion * ancho,
                    caja.bottom() - alto,
                    ancho,
                    alto,
                )
            )
