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

**Cada caja es un encabezado y una señal** desde el hito 51, como en el
prototipo: arriba el número, la fase y los eventos con su nombre; abajo la
señal de esa ventana, con la misma escala que el visualizador. Hasta entonces
la caja tenía el número en el medio, el chip de la fase y una franja de color
por evento, y ninguna señal: el panel no dejaba ver lo que pasaba justo antes
o justo después, que es para lo que existe. **Un clic en una caja lleva a esa
ventana**, que tampoco hacía.

Cubre del pliego: V1_F, V2_F, V3_F de "Übersicht (panel de contexto)".
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QFont,
    QColor,
    QFontMetricsF,
    QMouseEvent,
    QPaintEvent,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from psglab.core.nomenclature import SleepStage, stage_label
from psglab.tools.overview import OverviewWindow
from psglab.ui import theme
from psglab.ui.fonts import font_for
from psglab.ui.panel_header import chip_font, chip_width, draw_chip

#: Separación entre rectángulos, en píxeles. Sin ella las ventanas se leen como
#: una sola barra continua y se pierde justamente lo que el panel muestra.
_SEPARACION_PX: int = 4

#: El aire del encabezado de cada caja, y entre sus piezas.
_MARGEN_DEL_CHIP: float = 4.0

#: Qué parte del alto de la caja ocupa una señal que llega a su escala. Es la
#: misma proporción que el visualizador le da a cada carril
#: (`signal_view._LLENADO_DEL_CARRIL`), para que la miniatura se lea igual.
_LLENADO: float = 0.45

#: Color de una clase de anotación que el conjunto no supo colorear. Es gris a
#: propósito: un color de la paleta haría creer que la clase tiene uno asignado.
_SIN_COLOR = "#999999"

#: Hasta dónde se deja angostar el panel, en píxeles. Con tres ventanas son
#: unos 37 px cada una, que todavía alcanzan para leer el número. Ver
#: `OverviewPanel.set_panel_size()`.
ANCHO_MINIMO: int = 120


def accessible_summary(windows: tuple[OverviewWindow, ...]) -> str:
    """Lo que muestran las cajas, en palabras, para un lector de pantalla.

    **El panel es sólo dibujo** y un lector no lee ningún número de él (hito
    63): esto es lo mismo que dicen las cabeceras —número base 1, fase y
    eventos—, con la actual marcada.
    """
    partes = []
    for ventana in windows:
        texto = f"ventana {ventana.index + 1}"
        if ventana.is_current:
            texto += " (actual)"
        texto += ": " + (
            "sin scorear"
            if ventana.stage is SleepStage.UNSCORED
            else stage_label(ventana.stage)
        )
        if ventana.annotation_labels:
            texto += ", " + ", ".join(ventana.annotation_labels)
        partes.append(texto)
    if not partes:
        return "Sin registro abierto"
    # Sólo la primera letra: `capitalize()` pasa el resto a minúscula, y «N1»
    # salía «n1».
    texto = "; ".join(partes)
    return texto[0].upper() + texto[1:]


class OverviewPanel(QWidget):
    """Dibuja las ventanas vecinas que publica `OverviewTool`."""

    #: Se hizo clic en una caja: lleva el número de su ventana, base 0.
    window_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ningún registro abierto."""
        super().__init__(parent)
        self._windows: tuple[OverviewWindow, ...] = ()
        #: Colores por clase de evento, que los pide la ventana principal al
        #: `AnnotationSet`: la herramienta manda los nombres, no los colores.
        self._colors: dict[str, str] = {}
        #: El color de la señal de las miniaturas: el que tiene su canal en el
        #: visualizador. Lo pone la ventana, que sabe en qué carril está.
        self._trace_color: str | None = None
        #: El ancho que pidió el usuario (V2_F). Es el preferido, no el mínimo.
        self._ancho_preferido = ANCHO_MINIMO
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.set_panel_size(480, 90)
        self.setToolTip(
            "Contexto: la ventana actual junto a las anteriores y las siguientes. "
            "Un clic lleva la señal a esa ventana."
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # **Se alcanza con el teclado** (hito 63): con Tab o F6, y entonces
        # dibuja el anillo de foco. Las flechas ya mueven la ventana actual en
        # toda la ventana, así que no hace falta manejarlas acá.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Übersicht")

    # -- Lo que le da la ventana principal ----------------------------------

    def set_windows(
        self,
        windows: tuple[OverviewWindow, ...],
        colors: dict[str, str] | None = None,
        trace_color: str | None = None,
    ) -> None:
        """Recibe qué ventanas mostrar y con qué color cada clase de evento.

        Args:
            windows: lo que publica `OverviewTool.windows()`, en su orden.
            colors: color por clase de evento. La herramienta manda los nombres
                de las clases y no sus colores, porque los colores viven en
                `AnnotationSet`, que es de `core/`.
            trace_color: color de la señal. `None` conserva el anterior; sin
                ninguno, se usa la tinta del esquema.
        """
        self._windows = tuple(windows)
        if colors is not None:
            self._colors = dict(colors)
        if trace_color is not None:
            self._trace_color = trace_color
        self.setAccessibleDescription(accessible_summary(self._windows))
        self.update()

    def set_panel_size(self, width_px: int, height_px: int) -> None:
        """Fija el tamaño del panel (V2_F).

        La validación vive en `OverviewTool.set_size()`, que es donde está la
        regla; acá sólo se obedece. El alto se fija.

        **El ancho es el preferido, no el mínimo.** Como mínimo, los 480 px
        con que se arma el panel —240 con los de la herramienta— no dejaban
        lugar al hipnograma cuando se abrían los tres paneles de abajo. Ahora
        el panel empieza con el ancho pedido, crece si la ventana se agranda y
        se deja angostar hasta `ANCHO_MINIMO` si hace falta.
        """
        self._ancho_preferido = int(width_px)
        self.setMinimumWidth(min(ANCHO_MINIMO, self._ancho_preferido))
        self.setFixedHeight(int(height_px))
        self.updateGeometry()

    def sizeHint(self) -> QSize:
        """El ancho que pidió el usuario y el alto fijado."""
        return QSize(self._ancho_preferido, self.height())

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

    def _ventana_en(self, punto: QPointF) -> int | None:
        """El número de la ventana cuya caja contiene el punto, o None."""
        for ventana, caja in self.rectangles():
            if caja.contains(punto):
                return ventana.index
        return None

    def _partes(self, caja: QRectF) -> tuple[QRectF, QRectF]:
        """El encabezado de una caja y lo que queda debajo para la señal.

        El encabezado mide una línea —la más alta entre el número y un chip—
        más su aire, así que crece con el tamaño de letra que elige el usuario
        y la señal se queda con el resto.
        """
        alto = self._alto_de_la_fila(self.font()) + 2 * _MARGEN_DEL_CHIP
        alto = min(alto, caja.height())
        cabecera = QRectF(caja.left(), caja.top(), caja.width(), alto)
        senal = QRectF(caja.left(), caja.top() + alto, caja.width(), caja.height() - alto)
        return cabecera, senal

    @staticmethod
    def _alto_de_la_fila(base: QFont) -> float:
        """El alto de la línea del encabezado: el número o un chip, el mayor."""
        return max(
            QFontMetricsF(font_for("lectura", base)).height(),
            QFontMetricsF(chip_font(base)).height(),
        )

    # -- El mouse -----------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Un clic izquierdo en una caja pide ir a esa ventana."""
        if event.button() == Qt.MouseButton.LeftButton:
            indice = self._ventana_en(event.position())
            if indice is not None:
                self.window_clicked.emit(indice)
                return
        super().mousePressEvent(event)

    # -- El dibujo ----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        """Pinta las cajas. Lo único de este módulo que no se testea."""
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        esquema = theme.current()
        for ventana, caja in self.rectangles():
            actual = ventana.is_current
            fondo = esquema.overview_current if actual else esquema.overview_background
            borde = esquema.overview_current_border if actual else esquema.overview_border
            pintor.setBrush(QBrush(QColor(fondo)))
            pintor.setPen(QPen(QColor(borde), 2 if actual else 1))
            pintor.drawRect(caja)

            cabecera, senal = self._partes(caja)
            pintor.setPen(QPen(QColor(esquema.overview_border), 1))
            pintor.drawLine(cabecera.bottomLeft(), cabecera.bottomRight())
            self._pintar_la_senal(pintor, ventana, senal)
            self._pintar_la_cabecera(pintor, ventana, cabecera)
        if self.hasFocus():
            # El mismo anillo que la hoja de estilo le pone a los controles:
            # este panel se pinta a mano y la hoja no lo alcanza.
            mitad = theme.ANILLO_DE_FOCO / 2
            pintor.setBrush(Qt.BrushStyle.NoBrush)
            pintor.setPen(QPen(QColor(esquema.accent), theme.ANILLO_DE_FOCO))
            pintor.drawRect(QRectF(self.rect()).adjusted(mitad, mitad, -mitad, -mitad))
        pintor.end()

    def _pintar_la_cabecera(
        self, pintor: QPainter, ventana: OverviewWindow, cabecera: QRectF
    ) -> None:
        """El número, la fase y, a la derecha, los eventos con su nombre.

        **La fase** es la mitad del contexto —que la de al lado ya está
        puesta— y se dibuja con el color de la escala del esquema, el mismo del
        hipnograma, la franja de posición y el botón de scoring. Un esquema sin
        escala no lleva chip: sería una cápsula del color del acento en todas
        las ventanas, que no distingue nada.

        **Los eventos llevan su nombre** (V3_F): hasta el hito 51 eran franjas
        de color sin rótulo, y había que saber de memoria qué color era cada
        clase. Van una vez por clase, y los que no entran no se dibujan en vez
        de pisar la fase.
        """
        fila = self._alto_de_la_fila(pintor.font())
        fuente = chip_font(pintor.font())
        alto = QFontMetricsF(fuente).height()
        # Los chips, centrados en la línea: el número es más alto que ellos.
        arriba = cabecera.top() + _MARGEN_DEL_CHIP + (fila - alto) / 2
        x = cabecera.left() + _MARGEN_DEL_CHIP

        # Base 1 al mostrar, como en la barra de estado y en los archivos de
        # salida. **Con la letra de las lecturas y no la del chip**: con la del
        # chip el número quedaba más chico y más apagado que la fase de al
        # lado, y es lo primero que se busca en la caja.
        numero = str(ventana.index + 1)
        de_numero = font_for("lectura", pintor.font())
        pintor.setFont(de_numero)
        pintor.setPen(QPen(QColor(theme.current().overview_text)))
        ancho_del_numero = QFontMetricsF(de_numero).horizontalAdvance(numero)
        pintor.drawText(
            QRectF(x, cabecera.top() + _MARGEN_DEL_CHIP, ancho_del_numero, fila),
            Qt.AlignmentFlag.AlignCenter,
            numero,
        )
        x += ancho_del_numero + _MARGEN_DEL_CHIP

        if ventana.stage is not SleepStage.UNSCORED:
            color = theme.current().color_for_stage(ventana.stage.value)
            if color is not None:
                texto = stage_label(ventana.stage)
                ancho = chip_width(texto, fuente)
                draw_chip(pintor, QRectF(x, arriba, ancho, alto), texto, color, fuente)
                x += ancho + _MARGEN_DEL_CHIP

        # **De qué canal es la señal**, en la actual y no en todas: es el mismo
        # canal en cada caja. Va en el encabezado y no sobre la señal, por la
        # misma regla que llevó los nombres al canalón en el hito 37: lo que se
        # escribe encima de una onda queda tapado por ella.
        if ventana.is_current and ventana.trace is not None:
            de_canal = font_for("lectura_secundaria", pintor.font())
            pintor.setFont(de_canal)
            pintor.setPen(QPen(QColor(theme.current().overview_text)))
            ancho = QFontMetricsF(de_canal).horizontalAdvance(ventana.trace.channel_name)
            pintor.drawText(
                QRectF(x, cabecera.top() + _MARGEN_DEL_CHIP, ancho, fila),
                Qt.AlignmentFlag.AlignCenter,
                ventana.trace.channel_name,
            )
            x += ancho + _MARGEN_DEL_CHIP

        derecha = cabecera.right() - _MARGEN_DEL_CHIP
        for clase in reversed(list(dict.fromkeys(ventana.annotation_labels))):
            ancho = chip_width(clase, fuente)
            if derecha - ancho < x:
                break
            derecha -= ancho
            draw_chip(
                pintor,
                QRectF(derecha, arriba, ancho, alto),
                clase,
                self._colors.get(clase, _SIN_COLOR),
                fuente,
            )
            derecha -= _MARGEN_DEL_CHIP

    def _pintar_la_senal(
        self, pintor: QPainter, ventana: OverviewWindow, zona: QRectF
    ) -> None:
        """La señal de la ventana, con la escala del visualizador.

        Se recorta a la caja: un pico que pasa de la escala se corta en el
        borde, como en el visualizador se sale de su carril, en vez de
        dibujarse encima de la caja vecina.
        """
        trazo = ventana.trace
        if trazo is None or zona.height() <= 0 or len(trazo.positions) == 0:
            return
        esquema = theme.current()
        centro = zona.center().y()
        pintor.save()
        pintor.setClipRect(zona)
        pintor.setPen(QPen(QColor(esquema.overview_border), 1))
        pintor.drawLine(QPointF(zona.left(), centro), QPointF(zona.right(), centro))

        xs = zona.left() + trazo.positions * zona.width()
        ys = centro - ((trazo.microvolts - trazo.offset_uv) / trazo.scale_uv) * (
            _LLENADO * zona.height()
        )
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pintor.setPen(QPen(QColor(self._trace_color or esquema.foreground), 1))
        pintor.drawPolyline(
            QPolygonF([QPointF(float(x), float(y)) for x, y in zip(xs, ys)])
        )

        pintor.restore()
