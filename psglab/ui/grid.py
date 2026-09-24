"""Grilla de fondo del visualizador.

El pliego define dos densidades de línea sobre la ventana de 30 segundos:

    - línea visible cada 3 s   -> 10 fragmentos
    - línea discreta cada 0,5 s -> 60 fragmentos

y tres fondos elegibles por el usuario (V2_F): blanco, sólo las líneas de
3 segundos, o las dos densidades juntas.

## Todas las líneas son un solo objeto de la escena

Hasta el hito 25 cada línea era una `pg.InfiniteLine`, y **eso era la mitad de
lo que costaba mover la página**: cada objeto de pyqtgraph recalcula su
rectángulo, consulta la escala del gráfico y se pinta por separado. Medido
sobre el registro de prueba, con una página de 30 s y su grilla de 72 líneas:

    paso de reproducción con la grilla fina     113 ms
    el mismo paso sin ninguna línea              57 ms

o sea unos 0,8 ms por línea y por cuadro. En un banco aparte, mover 72 líneas y
el eje cuesta 67,5 ms como objetos sueltos y 22,1 ms dibujadas en uno solo.

Por eso `GridBackground` no crea objetos: arma una lista de `GridLine` —dónde
cae cada una, en qué sentido y de qué color— y un único `_LineasDeFondo` las
dibuja todas en su `paint()`. **Las líneas de base de los canales viven acá por
el mismo motivo**, aunque no sean parte de la grilla del pliego: eran otro
objeto por canal.

Cubre del pliego: V1_P, V2_F de "Diseño de la interfaz de visualización".
"""

import itertools
import math
from dataclasses import dataclass
from enum import Enum

import pyqtgraph as pg
from PySide6.QtCore import QLineF, QRectF
from PySide6.QtGui import QPainter

from psglab.config import COARSE_GRID_SECONDS, FINE_GRID_SECONDS, MAX_GRID_LINES
from psglab.ui import theme

#: En qué capa va la grilla: **debajo de la señal** y encima de la banda de la
#: época actual, que está en −20.
_Z_GRILLA: float = -10.0


@dataclass(frozen=True)
class GridLine:
    """Una línea de fondo: dónde cae, en qué sentido y de qué color.

    Es un valor y no un objeto de la escena. Las dibuja todas
    `_LineasDeFondo`, y esto es lo que se puede afirmar en un test sin mirar
    píxeles: cuántas hay y dónde caen es lo que define el fondo.

    Attributes:
        position: la coordenada donde cae, en el eje al que es perpendicular:
            segundos para una vertical, unidades del gráfico para una
            horizontal.
        angle: 90 si es vertical y 0 si es horizontal, como los llamaba
            `pg.InfiniteLine`.
        color: el color con que se dibuja, del esquema en uso.
    """

    position: float
    angle: int
    color: str


class _LineasDeFondo(pg.GraphicsObject):
    """El único objeto de la escena que dibuja la grilla y las líneas de base.

    **Se pinta en coordenadas del gráfico y con pluma cosmética**: así una línea
    mide un píxel cualquiera sea la escala de tiempo, que es lo que hacía
    `InfiniteLine` por su cuenta.
    """

    def __init__(self) -> None:
        """Crea el objeto sin ninguna línea."""
        super().__init__()
        self._lineas: tuple[GridLine, ...] = ()
        self.setZValue(_Z_GRILLA)

    def set_lines(self, lineas: tuple[GridLine, ...]) -> None:
        """Cambia las líneas y pide un repintado."""
        self._lineas = lineas
        self.update()

    def viewRangeChanged(self) -> None:
        """Al cambiar la vista, el rectángulo del objeto cambia con ella.

        pyqtgraph llama a este método cuando el `ViewBox` se mueve o se escala.
        Sin `prepareGeometryChange()`, la escena seguiría creyendo que el objeto
        ocupa el rectángulo anterior y dejaría las líneas a medio dibujar al
        desplazar la página.
        """
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self) -> QRectF:
        """Todo lo que se ve: las líneas llegan de borde a borde."""
        caja = self.getViewBox()
        return QRectF() if caja is None else QRectF(caja.viewRect())

    def paint(self, painter: QPainter, *_: object) -> None:
        """Dibuja las líneas agrupadas por color, en el orden en que llegaron.

        Agrupar ahorra cambios de pluma, y el orden es el que decide qué queda
        arriba: las finas primero y las visibles después, porque una línea de
        3 s coincide con una de 0,5 s y tiene que verse la que más importa.
        """
        caja = self.getViewBox()
        if caja is None or not self._lineas:
            return
        (x0, x1), (y0, y1) = caja.viewRange()
        for color, grupo in itertools.groupby(self._lineas, key=lambda linea: linea.color):
            pluma = pg.mkPen(color=color, width=1)
            pluma.setCosmetic(True)
            painter.setPen(pluma)
            painter.drawLines(
                [
                    QLineF(linea.position, y0, linea.position, y1)
                    if linea.angle == 90
                    else QLineF(x0, linea.position, x1, linea.position)
                    for linea in grupo
                ]
            )


def _segundos(valor: float) -> str:
    """Formatea una cantidad de segundos como la escribiría un lector en español.

    3,0 se muestra como "3" y 0,5 como "0,5": el separador decimal es la coma,
    y un valor entero no arrastra un ".0" que nadie escribiría a mano.
    """
    entero = int(valor)
    return str(entero) if valor == entero else str(valor).replace(".", ",")


class BackgroundStyle(Enum):
    """Fondos disponibles para la ventana de visualización (V2_F).

    Las etiquetas se arman con los valores de `config` en vez de escribir los
    números a mano: si el laboratorio cambiara la grilla, un texto fijo acá
    seguiría prometiéndole al usuario la separación vieja.
    """

    # **Se llamaba "Fondo blanco"**, y dejó de ser cierto cuando el fondo pasó
    # a depender del esquema de color: sobre el esquema oscuro esta opción da un
    # fondo gris, no blanco. Lo que la opción hace es no dibujar ninguna línea,
    # y eso es lo que ahora dice.
    BLANK = "Sin líneas"
    COARSE = f"Líneas cada {_segundos(COARSE_GRID_SECONDS)} segundos"
    FULL = (
        f"Líneas cada {_segundos(COARSE_GRID_SECONDS)} "
        f"y {_segundos(FINE_GRID_SECONDS)} segundos"
    )


class GridBackground:
    """Dibuja la grilla detrás de las señales.

    Se mantiene separada de `SignalView` porque cambia por motivos distintos:
    la grilla depende de la preferencia visual del usuario, las curvas
    dependen de los datos.
    """

    def __init__(self, plot: pg.PlotItem) -> None:
        """Asocia la grilla al gráfico donde se dibujan las señales."""
        self._plot = plot
        self._style = BackgroundStyle.FULL
        self._lines: tuple[GridLine, ...] = ()
        #: Las líneas de cero de cada canal. No son parte de la grilla del
        #: pliego, pero las dibuja el mismo objeto: ver el docstring del módulo.
        self._baselines: tuple[GridLine, ...] = ()
        #: La última ventana dibujada, para poder redibujar al cambiar de
        #: fondo sin que quien llama tenga que repetir la duración.
        self._window_seconds: float | None = None
        #: Dónde empezaba esa página, por el mismo motivo.
        self._origin_seconds: float = 0.0
        self._item = _LineasDeFondo()
        # `ignoreBounds` porque el rectángulo del objeto **es** el de la vista:
        # dejarlo entrar en el autoajuste sería pedirle al gráfico que se
        # ajuste a sí mismo.
        plot.addItem(self._item, ignoreBounds=True)

    @property
    def style(self) -> BackgroundStyle:
        """El fondo elegido por el usuario (V2_F)."""
        return self._style

    def set_style(self, style: BackgroundStyle) -> None:
        """Cambia el fondo y redibuja las líneas (V2_F)."""
        self._style = style
        if self._window_seconds is not None:
            self.redraw(
                self._window_seconds, origin_seconds=self._origin_seconds
            )

    def redraw(
        self,
        window_seconds: float,
        coarse_seconds: float = COARSE_GRID_SECONDS,
        fine_seconds: float = FINE_GRID_SECONDS,
        origin_seconds: float = 0.0,
    ) -> None:
        """Rearma las líneas para una página de la duración indicada.

        Recibe la duración por parámetro y no la lee de `config` para que la
        grilla siga siendo correcta si mañana el laboratorio trabaja con
        ventanas de otro tamaño.

        Args:
            coarse_seconds: separación de las líneas visibles (3 s en el
                pliego, que divide la ventana de 30 s en 10 fragmentos).
            fine_seconds: separación de las líneas discretas (0,5 s, que la
                divide en 60).
            origin_seconds: dónde empieza la página, en segundos desde el
                inicio del registro. **Entró con la escala de tiempo libre**:
                el eje del visualizador pasó a estar en segundos absolutos, y
                sin esto las líneas de una página que empieza en el segundo 90
                se dibujarían sobre el segundo 0, o sea fuera de la pantalla.

        **Las series con demasiadas líneas no se dibujan.** Una página de
        cuatro horas pediría 28 800 líneas finas: no es lento, es una pantalla
        tapada de gris donde no se ve la señal. El techo es `MAX_GRID_LINES`.

        **No crea ni destruye nada de la escena**: arma la lista y se la pasa
        al único objeto que dibuja. Ver el docstring del módulo.
        """
        self._window_seconds = window_seconds
        self._origin_seconds = origin_seconds
        if self._style is BackgroundStyle.BLANK:
            self._lines = ()
            self._actualizar()
            return

        # Los colores se leen **en cada redibujo** y no se guardan: así cambiar
        # de esquema y pedir un redibujo alcanza para que la grilla cambie, sin
        # que este objeto tenga que enterarse de nada.
        esquema = theme.current()
        pedidas: list[GridLine] = []

        # Las finas van primero y las visibles después, que es el orden en que
        # se pintan: donde una de 3 s coincide con una de 0,5 s tiene que
        # quedar arriba la que más se tiene que ver.
        if self._style is BackgroundStyle.FULL:
            pedidas += self._verticales(
                window_seconds, fine_seconds, esquema.fine_grid, origin_seconds
            )
        pedidas += self._verticales(
            window_seconds, coarse_seconds, esquema.coarse_grid, origin_seconds
        )

        self._lines = tuple(pedidas)
        self._actualizar()

    def set_baselines(self, positions: list[float], color: str | None) -> None:
        """Fija las líneas de cero de los canales, que van debajo de la señal.

        Las dibuja este objeto y no `signal_view.py` porque eran una
        `InfiniteLine` por canal, con el mismo costo por cuadro que las de la
        grilla.

        Args:
            positions: la altura de cada línea, en unidades del gráfico.
            color: el del esquema en uso, o None si el esquema no dibuja línea
                de cero, que es como se apagan.
        """
        if color is None:
            self._baselines = ()
        else:
            self._baselines = tuple(
                GridLine(position=float(p), angle=0, color=color) for p in positions
            )
        self._actualizar()

    def _actualizar(self) -> None:
        """Le pasa al objeto de la escena todo lo que tiene que dibujar.

        Las líneas de base van primero: una línea de cero debajo de la grilla
        es lo que se veía hasta ahora, cuando las dibujaba `signal_view.py`
        antes que nada.
        """
        self._item.set_lines(self._baselines + self._lines)

    def _verticales(
        self,
        window_seconds: float,
        cada: float,
        color: str,
        origin_seconds: float = 0.0,
    ) -> list[GridLine]:
        """Una línea vertical cada `cada` segundos, sin pasarse del borde.

        Se cuenta con enteros y se multiplica, en vez de ir acumulando: sumar
        0,5 sesenta veces acumula error de punto flotante y la última línea
        queda corrida del borde.

        **Las líneas caen en múltiplos absolutos de `cada`**, no en múltiplos
        del comienzo de la página: así no se mueven bajo la señal cuando el
        usuario desplaza la vista, que es lo que las vuelve una referencia.
        """
        if cada <= 0:
            return []
        cantidad = int(window_seconds / cada)
        if cantidad > MAX_GRID_LINES:
            return []
        primera = math.ceil(origin_seconds / cada)
        pedidas = []
        for paso in range(cantidad + 2):
            posicion = (primera + paso) * cada
            if posicion > origin_seconds + window_seconds:
                break
            pedidas.append(GridLine(position=posicion, angle=90, color=color))
        return pedidas

    def clear(self) -> None:
        """Borra todas las líneas de la grilla. Las de base quedan."""
        self._lines = ()
        self._actualizar()

    def lines(self) -> list[GridLine]:
        """Las líneas de la grilla que están dibujadas ahora mismo.

        Existe para poder afirmar sobre la grilla en un test sin mirar píxeles:
        cuántas líneas hay y dónde están es lo que define el fondo. **No
        incluye las líneas de base**, que no son parte del fondo del pliego.
        """
        return list(self._lines)

    def baselines(self) -> list[GridLine]:
        """Las líneas de cero de los canales que están dibujadas ahora mismo."""
        return list(self._baselines)
