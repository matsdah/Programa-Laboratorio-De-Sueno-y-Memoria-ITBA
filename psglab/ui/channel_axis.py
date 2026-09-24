"""El canalón: el nombre, la clase y la escala de cada canal, a la izquierda.

## Por qué existe

Hasta el hito 36 el nombre de cada canal era un `pg.TextItem` apoyado sobre el
carril, **dentro del área de trazo**. La captura de la ventana entera lo mostró
sin lugar a dudas: «C3 (EEG) — 100 µV» quedaba cruzado por su propia onda y no
se leía. El diseño de la pantalla principal nunca lo puso ahí: tiene una
columna propia a la izquierda, fuera del gráfico, con el nombre arriba y la
escala debajo.

Una columna así no se consigue moviendo el texto: mientras el rótulo sea un
ítem de la escena, vive en coordenadas del gráfico y la señal se dibuja encima.
Lo que la reserva de verdad es un eje, porque el eje es lo único a lo que
pyqtgraph le descuenta ancho al `ViewBox`. Por eso esto es un `AxisItem` y no
un widget al costado: un widget aparte tendría que mantener su alineación
vertical con los carriles a mano, y se desalinearía con cada cambio de rango.

## Qué dibuja, y qué no

Dibuja sus propios rótulos y **ninguna marca ni número**: `tickValues()`
devuelve una lista vacía y el estilo trae `showValues` apagado, así que lo que
pinta pyqtgraph es nada más la línea del eje —que el esquema deja sin pluma— y
todo el resto sale de `drawPicture()`. La cuenta de dónde cae cada carril no se
reimplementa: se le pregunta al `ViewBox` con `mapViewToScene()`, que es el
mismo que ubica las curvas.

**El nombre va en la tinta del texto y el color del canal va en una muestra**,
una barrita al borde del canalón. Es la diferencia con el rótulo viejo, que
escribía el nombre entero en el color del canal, y no es estética: la paleta de
canales está verificada contra `MIN_GRAPHIC_CONTRAST` —3,0— porque son trazos,
y el color 3 de Sereno da 3,89 sobre el fondo. Como texto habría quedado por
debajo de los 4,5 que pide WCAG 2.1. La muestra sigue siendo un gráfico y
mantiene la identificación por color, que es para lo que el color estaba.

**El ancho es fijo y los nombres largos se recortan con puntos suspensivos.**
Un canal llamado «EEG Fpz-Cz-A2-referenciado» no puede decidir cuánta pantalla
le queda a la señal. El nombre completo se sigue viendo en el selector de
canales.

Cubre del pliego: V1_P, V4_F, V5_F de "Visualización de la señal".
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

import pyqtgraph as pg
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter

from psglab.ui import theme
from psglab.ui.fonts import font_for

#: Cuánto ancho se reserva a la izquierda del gráfico, en píxeles. Es el de la
#: columna del diseño. Fijo y no calculado a partir de los nombres: con un
#: nombre largo, un ancho calculado se comería la señal.
ANCHO_DEL_CANALON: Final[int] = 108

#: Cuánto respira el texto contra el borde izquierdo de la ventana.
_MARGEN: Final[float] = 6.0

#: La barrita de color del canal: ancho, alto y cuánto la separa del gráfico.
_ANCHO_DE_LA_MUESTRA: Final[float] = 3.0
_ALTO_DE_LA_MUESTRA: Final[float] = 15.0
_MARGEN_DE_LA_MUESTRA: Final[float] = 5.0

#: Cuánto separa el texto de la muestra de color.
_SEPARACION: Final[float] = 7.0


@dataclass(frozen=True)
class ChannelLane:
    """Un renglón del canalón: qué dice y a qué altura del gráfico va.

    Es un valor y no un objeto de la escena, como `grid.GridLine`: lo que se
    puede afirmar en un test es qué rótulos hay y contra qué carril van, no los
    píxeles que salen de dibujarlos.

    Attributes:
        name: el nombre del canal, tal como lo trae el registro.
        detail: la segunda línea, que es la clase y la escala («EEG · 100 µV»).
        color: el color con que se dibuja la señal de ese canal, para la
            muestra. No se usa para el texto; ver el docstring del módulo.
        position: el centro de su carril, en unidades del gráfico.
    """

    name: str
    detail: str
    color: str
    position: float


class ChannelAxis(pg.AxisItem):
    """El eje izquierdo del visualizador, que dibuja un rótulo por canal."""

    def __init__(self) -> None:
        """Crea el canalón vacío, con su ancho reservado."""
        super().__init__(orientation="left")
        self._carriles: tuple[ChannelLane, ...] = ()
        self._fuente: QFont | None = None
        self._fuente_numerica: QFont | None = None
        self._tinta: str = theme.current().foreground
        self._tinta_secundaria: str = theme.current().overview_text
        self.setWidth(ANCHO_DEL_CANALON)
        # Sin marcas y sin números: todo lo que se ve lo dibuja `drawPicture()`.
        self.setStyle(tickLength=0, showValues=False)

    # -- Lo que le dice el visualizador -------------------------------------

    def set_lanes(self, lanes: Sequence[ChannelLane]) -> None:
        """Reemplaza los rótulos. Recibe estado completo, no un delta.

        **Si son los mismos, no repinta**, y eso no es una optimización
        prematura: el visualizador los rearma en cada dibujo, o sea veinticinco
        veces por segundo mientras se reproduce, y repintar el canalón en cada
        cuadro sería exactamente lo que el hito 25 le sacó a la grilla. Los
        rótulos cambian al elegir canales y al cambiar la amplitud, no al
        moverse la página.
        """
        nuevos = tuple(lanes)
        if nuevos == self._carriles:
            return
        self._carriles = nuevos
        self._repintar()

    def lanes(self) -> tuple[ChannelLane, ...]:
        """Los rótulos que está dibujando, en el orden en que se apilan."""
        return self._carriles

    def set_fonts(self, font: QFont) -> None:
        """Cambia la tipografía de las dos líneas del rótulo.

        Hace falta aparte, igual que en el visualizador: un `AxisItem` no sigue
        solo a la tipografía de la aplicación.

        **Las dos salen de la escala** (hito 43) y no de una cuenta de acá: el
        nombre es «cuerpo» y la escala es «lectura secundaria». Antes este
        módulo achicaba un punto y el chip achicaba dos, que eran dos
        respuestas a la misma pregunta.

        Args:
            font: la de la aplicación, de la que sale el tamaño base.
        """
        self._fuente = font_for("cuerpo", font)
        self._fuente_numerica = font_for("lectura_secundaria", font)
        self._repintar()

    def apply_scheme(self, scheme: theme.ColorScheme) -> None:
        """Toma las dos tintas del esquema y deja el eje sin línea.

        **Sin línea a propósito**: el diseño no separa el canalón del gráfico
        con una regla, y la separación ya la hace el espacio en blanco.
        """
        self._tinta = scheme.foreground
        self._tinta_secundaria = scheme.overview_text
        self.setPen(pg.mkPen(None))
        self._repintar()

    # -- Dibujo -------------------------------------------------------------

    def tickValues(self, *_: object) -> list[tuple[float, list[float]]]:
        """Ninguna marca: los carriles no son una escala numérica.

        Sin esto pyqtgraph elegiría marcas redondas sobre el eje de carriles
        —0, −1, −2…— que no significan nada para quien mira.
        """
        return []

    def drawPicture(self, p: QPainter, *specs: object) -> None:
        """Dibuja el eje como cualquiera y encima los rótulos de los canales."""
        super().drawPicture(p, *specs)
        vista = self.linkedView()
        if vista is None or not self._carriles:
            return
        derecha = self.mapRectFromParent(self.geometry()).right()
        if self._fuente is not None:
            p.setFont(self._fuente)
        for carril in self._carriles:
            escena = vista.mapViewToScene(QPointF(0.0, carril.position))
            self._dibujar_carril(p, carril, derecha, self.mapFromScene(escena).y())

    def _dibujar_carril(
        self, p: QPainter, carril: ChannelLane, derecha: float, y: float
    ) -> None:
        """Un rótulo: la muestra de color y las dos líneas de texto a su izquierda."""
        borde = derecha - _MARGEN_DE_LA_MUESTRA
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(carril.color)))
        p.drawRect(
            QRectF(
                borde - _ANCHO_DE_LA_MUESTRA,
                y - _ALTO_DE_LA_MUESTRA / 2.0,
                _ANCHO_DE_LA_MUESTRA,
                _ALTO_DE_LA_MUESTRA,
            )
        )
        p.setBrush(Qt.BrushStyle.NoBrush)

        izquierda = _MARGEN
        ancho = borde - _ANCHO_DE_LA_MUESTRA - _SEPARACION - izquierda
        if ancho <= 0.0:
            return

        del_nombre = QFontMetricsF(self._fuente) if self._fuente else QFontMetricsF(p.font())
        del_detalle = (
            QFontMetricsF(self._fuente_numerica) if self._fuente_numerica else del_nombre
        )
        alto = del_nombre.height() + del_detalle.height()
        arriba = y - alto / 2.0
        bandera = int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        if self._fuente is not None:
            p.setFont(self._fuente)
        p.setPen(QColor(self._tinta))
        p.drawText(
            QRectF(izquierda, arriba, ancho, del_nombre.height()),
            bandera,
            del_nombre.elidedText(carril.name, Qt.TextElideMode.ElideRight, ancho),
        )

        if self._fuente_numerica is not None:
            p.setFont(self._fuente_numerica)
        p.setPen(QColor(self._tinta_secundaria))
        p.drawText(
            QRectF(izquierda, arriba + del_nombre.height(), ancho, del_detalle.height()),
            bandera,
            del_detalle.elidedText(carril.detail, Qt.TextElideMode.ElideRight, ancho),
        )

    def _repintar(self) -> None:
        """Tira el dibujo cacheado y pide otro.

        `AxisItem` guarda lo que pintó en un `QPicture` y sólo lo rehace cuando
        cambia el rango o la geometría. Cambiar un rótulo no es ninguna de las
        dos cosas, así que hay que invalidarlo a mano o el canalón seguiría
        mostrando la escala vieja.
        """
        self.picture = None
        self.update()
