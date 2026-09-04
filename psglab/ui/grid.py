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
        raise NotImplementedError("Pendiente: guardar la referencia al gráfico.")

    def set_style(self, style: BackgroundStyle) -> None:
        """Cambia el fondo y redibuja las líneas (V2_F)."""
        raise NotImplementedError("Pendiente: cambiar el estilo y redibujar.")

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
        raise NotImplementedError("Pendiente: dibujar las líneas de la grilla.")

    def clear(self) -> None:
        """Borra todas las líneas de la grilla."""
        raise NotImplementedError("Pendiente: quitar las líneas del gráfico.")
