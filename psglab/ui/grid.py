"""Grilla de fondo del visualizador.

El pliego define dos densidades de línea sobre la ventana de 30 segundos:

    - línea visible cada 3 s   -> 10 fragmentos
    - línea discreta cada 0,5 s -> 60 fragmentos

y tres fondos elegibles por el usuario (V2_F): blanco, sólo las líneas de
3 segundos, o las dos densidades juntas.

Cubre del pliego: V1_P, V2_F de "Diseño de la interfaz de visualización".
"""

import math
from enum import Enum

import pyqtgraph as pg

from psglab.config import COARSE_GRID_SECONDS, FINE_GRID_SECONDS, MAX_GRID_LINES
from psglab.ui import theme

#: Cada cuántos carriles va una línea horizontal visible con la grilla ECG.
#: Cuatro por carril, como los cuadros grandes del papel.
COARSE_LANE_FRACTION: float = 0.25

#: Y cada cuántos una discreta: cinco por cada visible, como los cuadros chicos.
FINE_LANE_FRACTION: float = 0.05

#: En qué capa se dibuja cada serie. Ver `GridBackground._aplicar()`.
_Z_VISIBLE: float = -10.0
_Z_FINA: float = -11.0


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
        self._lines: list[pg.InfiniteLine] = []
        #: Con qué ángulo y color está cada línea de `_lines`, para no volver a
        #: fijarle la pluma si no cambió.
        self._claves: list[tuple[int, str]] = []
        #: La última ventana dibujada, para poder redibujar al cambiar de
        #: fondo sin que quien llama tenga que repetir la duración.
        self._window_seconds: float | None = None
        #: Dónde empezaba esa página, por el mismo motivo.
        self._origin_seconds: float = 0.0

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
        """Redibuja las líneas para una página de la duración indicada.

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

        **Las líneas se reusan, no se recrean.** Hasta el hito 24 cada redibujo
        borraba las setenta de una página de 30 s y creaba otras setenta, y eso
        era casi todo lo que tardaba en moverse la página: 45 de 52 ms sobre el
        registro de prueba. Con la reproducción, que mueve la página
        veinticinco veces por segundo, dejó de ser tolerable.
        """
        self._window_seconds = window_seconds
        self._origin_seconds = origin_seconds
        if self._style is BackgroundStyle.BLANK:
            self.clear()
            return

        # Los colores se leen **en cada redibujo** y no se guardan: así cambiar
        # de esquema y pedir un redibujo alcanza para que la grilla cambie, sin
        # que este objeto tenga que enterarse de nada.
        esquema = theme.current()
        pedidas: list[tuple[float, int, str]] = []

        # Las finas van primero y las visibles después. El orden de dibujo no
        # depende de eso sino del `zValue` de cada serie: una línea de 3 s
        # coincide con una de 0,5 s y tiene que quedar arriba la que más se
        # tiene que ver, aunque se haya reusado una línea creada antes.
        if self._style is BackgroundStyle.FULL:
            pedidas += self._verticales(
                window_seconds, fine_seconds, esquema.fine_grid, origin_seconds
            )
        pedidas += self._verticales(
            window_seconds, coarse_seconds, esquema.coarse_grid, origin_seconds
        )

        # **La cuadrícula del esquema ECG.** Las líneas horizontales respetan el
        # mismo estilo de fondo que las verticales —ninguna con "sin líneas",
        # sólo las visibles con la grilla gruesa—, así que los tres fondos del
        # pliego siguen siendo tres y el ECG es otra dimensión, no un cuarto.
        if esquema.ecg_grid:
            if self._style is BackgroundStyle.FULL:
                pedidas += self._horizontales(FINE_LANE_FRACTION, esquema.fine_grid)
            pedidas += self._horizontales(COARSE_LANE_FRACTION, esquema.coarse_grid)

        self._aplicar(pedidas, esquema.coarse_grid)

    def _verticales(
        self,
        window_seconds: float,
        cada: float,
        color: str,
        origin_seconds: float = 0.0,
    ) -> list[tuple[float, int, str]]:
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
            pedidas.append((posicion, 90, color))
        return pedidas

    def _horizontales(self, cada: float, color: str) -> list[tuple[float, int, str]]:
        """Una línea horizontal cada `cada` carriles, sobre lo que se ve.

        **En fracciones de carril y no en microvoltios.** Cada canal tiene su
        propia escala, así que una línea a 50 µV caería a una altura distinta
        en cada carril y la cuadrícula dejaría de ser una cuadrícula. Como en
        el papel de un electrocardiograma, lo que importa es que las líneas
        sean regulares; la amplitud se lee en la escala de cada canal.

        Se dibujan sobre el rango vertical que el gráfico ya tiene fijado, que
        es el de los canales visibles, y con el mismo techo que las verticales.
        """
        abajo, arriba = self._plot.vb.viewRange()[1]
        if cada <= 0 or arriba <= abajo:
            return []
        cantidad = int((arriba - abajo) / cada)
        if cantidad > MAX_GRID_LINES:
            return []
        primera = math.ceil(abajo / cada)
        pedidas = []
        for paso in range(cantidad + 2):
            posicion = (primera + paso) * cada
            if posicion > arriba:
                break
            pedidas.append((posicion, 0, color))
        return pedidas

    def _aplicar(self, pedidas: list[tuple[float, int, str]], visible: str) -> None:
        """Deja en pantalla exactamente las líneas pedidas, reusando las que hay.

        Sobran: se sacan del gráfico. Faltan: se crean. Las demás sólo cambian
        de lugar, y de pluma si hace falta. Al desplazar una página de ancho
        fijo la cantidad cambia en una a lo sumo, así que casi siempre no se
        crea ni se borra nada.

        **El `zValue` separa las dos series**, las dos por debajo de la señal y
        por encima de la banda de la época actual (−20): las visibles en −10 y
        las finas en −11. Sin eso, una fina reusada podía quedar encima de una
        visible en el mismo lugar y taparla.
        """
        while len(self._lines) > len(pedidas):
            self._plot.removeItem(self._lines.pop())
            self._claves.pop()

        for indice, (posicion, angulo, color) in enumerate(pedidas):
            clave = (angulo, color)
            if indice == len(self._lines):
                linea = pg.InfiniteLine(
                    pos=posicion, angle=angulo, pen=pg.mkPen(color=color, width=1)
                )
                self._plot.addItem(linea)
                self._lines.append(linea)
                self._claves.append(clave)
            else:
                linea = self._lines[indice]
                if self._claves[indice] != clave:
                    linea.setAngle(angulo)
                    linea.setPen(pg.mkPen(color=color, width=1))
                    self._claves[indice] = clave
                linea.setValue(posicion)
            linea.setZValue(_Z_VISIBLE if color == visible else _Z_FINA)

    def clear(self) -> None:
        """Borra todas las líneas de la grilla."""
        for linea in self._lines:
            self._plot.removeItem(linea)
        self._lines.clear()
        self._claves.clear()

    def lines(self) -> list[pg.InfiniteLine]:
        """Las líneas dibujadas ahora mismo.

        Existe para poder afirmar sobre la grilla en un test sin mirar píxeles:
        cuántas líneas hay y dónde están es lo que define el fondo.
        """
        return list(self._lines)
