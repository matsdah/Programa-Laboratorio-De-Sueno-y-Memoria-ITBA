"""Mapa de calor de una matriz de conectividad.

`compute_connectivity()` devuelve una matriz cuadrada y simétrica con la
diagonal en cero, y **la matriz es la salida real del requisito**: mostrar sólo
su promedio —que es lo que hace el panel de métrica a lo largo de la noche—
diría cuánta conectividad hay pero no entre qué canales, que es la mitad
interesante.

**Los ejes llevan los nombres de los canales**, no números. Una matriz de
conectividad sin saber qué fila es qué electrodo no se puede leer, y ése es el
motivo por el que este panel existe en vez de imprimir el array.

**La escala de color va de 0 a 1 y está fija**, no ajustada a los valores de
cada matriz. Es deliberado: con la escala automática, dos ventanas con
conectividades muy distintas se verían iguales —cada una normalizada contra sí
misma— y comparar ventanas es justamente lo que el investigador va a hacer.

Como los demás paneles, lo que se puede afirmar sin mirar una pantalla está
separado del dibujo.

Cubre del pliego: ningún ID propio. Es la mitad que se ve de la sección
"Conectividad de la señal".
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget

#: Extremos de la escala de color. Las cinco medidas de `METHODS` están
#: acotadas a este rango, así que la escala fija es correcta para todas.
_MINIMO: float = 0.0
_MAXIMO: float = 1.0


class ConnectivityPanel(pg.PlotWidget):
    """Dibuja una matriz de conectividad como mapa de calor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ninguna matriz calculada."""
        super().__init__(parent)
        self._matriz: np.ndarray | None = None
        self._canales: list[str] = []

        self._imagen = pg.ImageItem()
        item = self.getPlotItem()
        item.addItem(self._imagen)
        item.setMenuEnabled(False)
        item.setMouseEnabled(x=False, y=False)
        item.invertY(True)
        # La barra de color explica qué significa cada tono. Sin ella el mapa
        # es bonito y no dice nada.
        self._barra = pg.ColorBarItem(
            values=(_MINIMO, _MAXIMO), colorMap=pg.colormap.get("viridis")
        )
        self._barra.setImageItem(self._imagen, insert_in=item)

    # -- Lo que le da la ventana principal ----------------------------------

    def set_matrix(self, matrix: np.ndarray, channel_names: list[str]) -> None:
        """Dibuja la matriz con los nombres de canal en los dos ejes.

        Args:
            matrix: matriz cuadrada, tal como la devuelve
                `compute_connectivity()`.
            channel_names: un nombre por fila, en el mismo orden.
        """
        datos = np.asarray(matrix, dtype=float)
        self._matriz = datos
        self._canales = list(channel_names)

        self._imagen.setImage(datos, levels=(_MINIMO, _MAXIMO))
        item = self.getPlotItem()
        # Los ticks van en el centro de cada celda, que es donde el usuario
        # espera leerlos: en el borde, un nombre queda entre dos filas.
        marcas = [
            (posicion + 0.5, nombre) for posicion, nombre in enumerate(self._canales)
        ]
        item.getAxis("bottom").setTicks([marcas])
        item.getAxis("left").setTicks([marcas])

    def clear_matrix(self) -> None:
        """Deja el panel vacío."""
        self._matriz = None
        self._canales = []
        self._imagen.clear()
        self.getPlotItem().getAxis("bottom").setTicks(None)
        self.getPlotItem().getAxis("left").setTicks(None)

    # -- Lo que se puede afirmar sin mirar ----------------------------------

    def channels(self) -> list[str]:
        """Los canales dibujados, en el orden de las filas."""
        return list(self._canales)

    def matrix(self) -> np.ndarray | None:
        """La matriz dibujada, o None si no hay ninguna."""
        return self._matriz

    def axis_labels(self) -> list[str]:
        """Los rótulos del eje horizontal, en orden.

        Está expuesto porque es la decisión que hace legible el panel: una
        matriz de conectividad sin saber qué fila es qué electrodo no se puede
        leer.
        """
        marcas = self.getPlotItem().getAxis("bottom")._tickLevels
        if not marcas:
            return []
        return [texto for _, texto in marcas[0]]

    @property
    def color_range(self) -> tuple[float, float]:
        """Los extremos de la escala de color.

        Fijos y no ajustados a cada matriz: con la escala automática, dos
        ventanas con conectividades muy distintas se verían iguales.
        """
        return (_MINIMO, _MAXIMO)
