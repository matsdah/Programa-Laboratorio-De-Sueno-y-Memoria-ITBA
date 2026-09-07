"""Grilla de fondo del visualizador.

El pliego define dos densidades de línea sobre la ventana de 30 segundos:

    - línea visible cada 3 s   -> 10 fragmentos
    - línea discreta cada 0,5 s -> 60 fragmentos

y tres fondos elegibles por el usuario (V2_F): blanco, sólo las líneas de
3 segundos, o las dos densidades juntas.

Cubre del pliego: V1_P, V2_F de "Diseño de la interfaz de visualización".
"""

from enum import Enum

import pyqtgraph as pg

from psglab.config import COARSE_GRID_SECONDS, FINE_GRID_SECONDS

#: Las dos plumas de la grilla. La fina es más clara a propósito: el pliego la
#: llama "discreta", y una grilla que compite con la señal estorba el scoring.
_PLUMA_VISIBLE = pg.mkPen(color=(160, 160, 160), width=1)
_PLUMA_FINA = pg.mkPen(color=(220, 220, 220), width=1)


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

    BLANK = "Fondo blanco"
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
        #: La última ventana dibujada, para poder redibujar al cambiar de
        #: fondo sin que quien llama tenga que repetir la duración.
        self._window_seconds: float | None = None

    @property
    def style(self) -> BackgroundStyle:
        """El fondo elegido por el usuario (V2_F)."""
        return self._style

    def set_style(self, style: BackgroundStyle) -> None:
        """Cambia el fondo y redibuja las líneas (V2_F)."""
        self._style = style
        if self._window_seconds is not None:
            self.redraw(self._window_seconds)

    def redraw(
        self,
        window_seconds: float,
        coarse_seconds: float = COARSE_GRID_SECONDS,
        fine_seconds: float = FINE_GRID_SECONDS,
    ) -> None:
        """Redibuja las líneas para una ventana de la duración indicada.

        Recibe la duración por parámetro y no la lee de `config` para que la
        grilla siga siendo correcta si mañana el laboratorio trabaja con
        ventanas de otro tamaño.

        Args:
            coarse_seconds: separación de las líneas visibles (3 s en el
                pliego, que divide la ventana en 10 fragmentos).
            fine_seconds: separación de las líneas discretas (0,5 s, que la
                divide en 60).
        """
        self._window_seconds = window_seconds
        self.clear()
        if self._style is BackgroundStyle.BLANK:
            return

        # Las finas van primero para que las visibles queden encima: dibujadas
        # al revés, una línea de 3 s coincide con una de 0,5 s y la tapa la que
        # menos se tiene que ver.
        if self._style is BackgroundStyle.FULL:
            self._dibujar_serie(window_seconds, fine_seconds, _PLUMA_FINA)
        self._dibujar_serie(window_seconds, coarse_seconds, _PLUMA_VISIBLE)

    def _dibujar_serie(self, window_seconds: float, cada: float, pluma: object) -> None:
        """Una línea vertical cada `cada` segundos, sin pasarse del borde.

        Se cuenta con enteros y se multiplica, en vez de ir acumulando: sumar
        0,5 sesenta veces acumula error de punto flotante y la última línea
        queda corrida del borde.
        """
        if cada <= 0:
            return
        cantidad = int(window_seconds / cada)
        for paso in range(cantidad + 1):
            posicion = paso * cada
            if posicion > window_seconds:
                break
            linea = pg.InfiniteLine(pos=posicion, angle=90, pen=pluma)
            self._plot.addItem(linea)
            self._lines.append(linea)

    def clear(self) -> None:
        """Borra todas las líneas de la grilla."""
        for linea in self._lines:
            self._plot.removeItem(linea)
        self._lines.clear()

    def lines(self) -> list[pg.InfiniteLine]:
        """Las líneas dibujadas ahora mismo.

        Existe para poder afirmar sobre la grilla en un test sin mirar píxeles:
        cuántas líneas hay y dónde están es lo que define el fondo.
        """
        return list(self._lines)
