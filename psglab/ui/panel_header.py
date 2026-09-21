"""La carrocería que comparten los paneles de análisis.

Dos piezas, y las dos existían repetidas en cada panel:

- `PanelHeader`, el encabezado: qué panel es, **qué se está mirando** y cómo se
  calculó, en una franja de alto fijo.
- `EmptyState`, lo que se lee mientras el panel no tiene ningún resultado.
- El **chip**: la cápsula con la que un panel dice de qué clase es algo —la
  clase de un canal, la fase de una época, si una impedancia pasa el
  límite—. Lo que se comparte es el radio, el aire y de qué color sale la
  tinta, que la elige `theme.ink_over()` midiendo contra el relleno.

## Por qué no seguía sirviendo el título del gráfico

Los tres paneles de curva ponían las dos cosas —la pista y la descripción del
resultado— en el **título del gráfico**, con un `_reflejar_titulo()` copiado
tres veces. Eso tenía tres problemas que se ven al abrir el programa:

- **Un título no es un encabezado.** El texto quedaba centrado sobre el
  dibujo, sin línea que lo separara, y con la pista del panel vacío ocupaba el
  lugar de un rótulo en un gráfico por lo demás en blanco.
- **La descripción y el método competían.** El método vivía en un `QLabel`
  suelto arriba del gráfico y la descripción adentro: dos renglones para dos
  datos del mismo cálculo.
- **El panel vacío no se distinguía de un espectro plano.** Ejes, grilla y
  leyenda seguían dibujados detrás del texto.

El encabezado junta el rótulo, la descripción y el método en una franja, y el
panel vacío reemplaza al gráfico entero en vez de escribirle encima.

## El rótulo va escrito en mayúsculas

No con `text-transform`, que la hoja de estilo de Qt no soporta —igual que
`letter-spacing`, que sí se puede pedir por `QFont`—. El diseño anterior lo
usaba y fue una de las cosas que no se pudieron llevar a la ventana; ver el
hito 36.

Cubre del pliego: ningún ID. Es presentación compartida; lo que cubre cada
panel está en su propio módulo.
"""

from typing import Final

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from psglab.ui import theme
from psglab.ui.icons import icon

#: Cuánto mide de alto el encabezado, en píxeles. Fijo: es la franja contra la
#: que se alinean los seis paneles, y uno más alto que otro se nota al cambiar
#: de solapa.
ALTO_DEL_ENCABEZADO: Final[int] = 34

#: La propiedad con que la hoja de estilo reconoce el rótulo de un panel.
ROTULO_PROPERTY: Final[str] = "rotulo"

#: La propiedad de un texto secundario: el método, la unidad, lo que se
#: consulta y no se busca.
SECUNDARIO_PROPERTY: Final[str] = "secundario"

#: Cuánto espaciado extra lleva el rótulo entre letras. `QFont` sí lo sabe
#: hacer, y es lo que le da a una palabra corta en mayúsculas el aire que en el
#: diseño viene de `letter-spacing`.
ESPACIADO_DEL_ROTULO: Final[float] = 1.4

#: El lado del icono del panel vacío, en píxeles.
LADO_DEL_ICONO: Final[int] = 26


class PanelHeader(QWidget):
    """La franja de arriba de un panel: qué es, qué muestra y cómo se calculó."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        """Crea el encabezado con su rótulo, sin descripción ni método.

        Args:
            label: el nombre del panel. Se muestra en mayúsculas.
        """
        super().__init__(parent)
        # Sin esto la hoja de estilo no le pinta ni el fondo ni la línea de
        # abajo: un `QWidget` pelado no dibuja su propio `background-color`.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(ALTO_DEL_ENCABEZADO)

        self._rotulo = QLabel(label.upper())
        self._rotulo.setProperty(ROTULO_PROPERTY, True)
        fuente = QFont(self._rotulo.font())
        fuente.setBold(True)
        fuente.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing, ESPACIADO_DEL_ROTULO
        )
        self._rotulo.setFont(fuente)

        self._descripcion = QLabel("")
        self._descripcion.setProperty(theme.READOUT_PROPERTY, True)
        self._descripcion.setAccessibleName("Qué se está mirando")

        self._detalle = QLabel("")
        self._detalle.setProperty(theme.READOUT_PROPERTY, True)
        self._detalle.setProperty(SECUNDARIO_PROPERTY, True)
        self._detalle.setAccessibleName("Cómo se calculó")

        fila = QHBoxLayout(self)
        fila.setContentsMargins(12, 0, 12, 0)
        fila.setSpacing(10)
        fila.addWidget(self._rotulo)
        fila.addWidget(self._descripcion)
        fila.addStretch(1)
        fila.addWidget(self._detalle)

    def label(self) -> str:
        """El rótulo del panel, como se lee: en mayúsculas."""
        return self._rotulo.text()

    def set_caption(self, text: str) -> None:
        """Qué se está mirando: la ventana, el canal, la banda."""
        self._descripcion.setText(text)

    def caption(self) -> str:
        """Lo que dice hoy la descripción, o vacío."""
        return self._descripcion.text()

    def set_detail(self, text: str) -> None:
        """Cómo se calculó: el método, el segmento, la ventana."""
        self._detalle.setText(text)

    def detail(self) -> str:
        """Lo que dice hoy el método, o vacío."""
        return self._detalle.text()


class EmptyState(QWidget):
    """Lo que ocupa el panel mientras no hay ningún resultado que mostrar.

    **Reemplaza al contenido, no lo tapa.** Un gráfico con ejes y grilla detrás
    de una frase se lee como un resultado que dio cero; sin él, como lo que es:
    todavía no se pidió nada.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el cartel vacío, sin texto."""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._icono = QLabel()
        self._icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icono.setPixmap(
            icon("grafico", theme.current().overview_border).pixmap(
                LADO_DEL_ICONO, LADO_DEL_ICONO
            )
        )

        self._texto = QLabel("")
        self._texto.setWordWrap(True)
        self._texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._texto.setProperty(SECUNDARIO_PROPERTY, True)
        self._texto.setAccessibleName("Por qué el panel está vacío")

        columna = QVBoxLayout(self)
        columna.setContentsMargins(28, 12, 28, 12)
        columna.setSpacing(8)
        columna.addStretch(1)
        columna.addWidget(self._icono)
        columna.addWidget(self._texto)
        columna.addStretch(1)

    def set_text(self, text: str) -> None:
        """Qué se lee: de dónde se pide lo que este panel muestra."""
        self._texto.setText(text)

    def text(self) -> str:
        """Lo que se lee hoy, o vacío."""
        return self._texto.text()

    def apply_scheme(self) -> None:
        """Vuelve a dibujar el icono con el esquema en uso.

        Hace falta aparte porque un `QPixmap` ya dibujado no cambia de color:
        es la misma razón por la que los botones de la barra de navegación
        rehacen su icono al cambiar de esquema.
        """
        self._icono.setPixmap(
            icon("grafico", theme.current().overview_border).pixmap(
                LADO_DEL_ICONO, LADO_DEL_ICONO
            )
        )


#: El radio de la cápsula de un chip y cuánto respira su texto a cada lado.
RADIO_DEL_CHIP: Final[int] = 4
PADDING_DEL_CHIP: Final[int] = 5

#: Cuánto más chica es la letra de un chip que la de su fila, en puntos.
PUNTOS_MENOS_DEL_CHIP: Final[int] = 2

#: Hasta dónde se achica. Por debajo de esto no se lee.
PUNTOS_MINIMOS_DEL_CHIP: Final[int] = 6

#: El rol del ítem que lleva el color de relleno de su chip.
ROL_DEL_COLOR: Final[int] = int(Qt.ItemDataRole.UserRole) + 2


def chip_font(base: QFont) -> QFont:
    """La tipografía de un chip: la de su fila, un par de puntos más chica."""
    chica = QFont(base)
    if base.pointSize() > 0:
        chica.setPointSize(
            max(PUNTOS_MINIMOS_DEL_CHIP, base.pointSize() - PUNTOS_MENOS_DEL_CHIP)
        )
    return chica


def chip_width(text: str, font: QFont) -> float:
    """Cuánto mide de ancho un chip con ese texto y esa tipografía."""
    return QFontMetricsF(font).horizontalAdvance(text) + 2 * PADDING_DEL_CHIP


def draw_chip(
    painter: QPainter, rect: QRectF, text: str, fill: str, font: QFont
) -> None:
    """Dibuja una cápsula con su texto adentro, centrado.

    **Está acá y no en cada panel** porque el radio, el aire y —sobre todo— de
    qué color sale la tinta son una sola decisión: `theme.ink_over()` la elige
    midiendo contra el relleno, que es lo mismo que hacen el botón de la fase
    marcada y el icono de reproducir. Dos paneles con su propia cuenta darían
    dos respuestas distintas sobre el mismo color.
    """
    relleno = QColor(fill)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(relleno))
    painter.drawRoundedRect(rect, RADIO_DEL_CHIP, RADIO_DEL_CHIP)
    painter.setFont(font)
    painter.setPen(QColor(theme.ink_over(theme.current(), relleno.name())))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.restore()


class ChipDelegate(QStyledItemDelegate):
    """Pinta una celda entera como un chip, centrado en su columna.

    El texto es el de la celda y el relleno sale de `ROL_DEL_COLOR`. Una celda
    sin color se dibuja como cualquier otra: es lo que deja el estado «sin
    medir» como texto y no como una cápsula gris que parece decir algo.
    """

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: object
    ) -> None:
        """La cápsula, o la celda de siempre si no hay color."""
        color = index.data(ROL_DEL_COLOR)
        texto = index.data(Qt.ItemDataRole.DisplayRole)
        if not color or not texto:
            super().paint(painter, option, index)
            return

        fuente = chip_font(option.font)
        ancho = chip_width(str(texto), fuente)
        alto = QFontMetricsF(fuente).height()
        caja = QRectF(
            option.rect.center().x() - ancho / 2.0,
            option.rect.center().y() - alto / 2.0,
            ancho,
            alto,
        )
        draw_chip(painter, caja, str(texto), str(color), fuente)
