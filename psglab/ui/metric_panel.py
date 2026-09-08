"""Panel de una métrica a lo largo de la noche, ventana por ventana.

**Sirve a los dos módulos del hito 14**, porque los dos producen la misma
forma: `complexity_by_window()` da un valor por ventana directamente, y
`connectivity_by_window()` da una matriz por ventana que
`average_connectivity()` resume en un número. Es lo que los dos docstrings
piden con todas las letras —"para poder cruzarlo con el hipnograma"— y por eso
comparte con él el eje horizontal.

**El eje horizontal va en base 1**, como el histograma y la barra de estado. Es
la regla del proyecto: base 0 adentro, base 1 al mostrar, y la conversión se
hace acá.

**Los NaN se dibujan como hueco, no como cero.** Es la decisión que hace
utilizable la convención de la ventana incompleta: un cero es un valor de
complejidad perfectamente plausible y bajo, indistinguible a ojo de una
medición real, así que pintarlo mentiría sobre una ventana que no se midió.

Como en `psd_panel.py` y en `overview_panel.py`, lo que se puede afirmar sin
mirar una pantalla está separado del dibujo.

Cubre del pliego: ningún ID de funcionalidad propio. Es la mitad que se ve de
las secciones "Complejidad" y "Conectividad de la señal".
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget

#: Color de la curva. No sale de `config.py` porque el pliego no fija ninguno.
_COLOR = "#4a90e6"


class MetricPanel(pg.PlotWidget):
    """Dibuja un valor por ventana a lo largo del registro."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ninguna métrica calculada."""
        super().__init__(parent)
        self._series: dict[str, np.ndarray] = {}
        self._curvas: dict[str, pg.PlotDataItem] = {}
        self._etiqueta: str = ""

        item = self.getPlotItem()
        item.setLabel("bottom", "Ventana")
        item.showGrid(x=True, y=True, alpha=0.3)
        item.addLegend(offset=(-10, 10))
        item.setMenuEnabled(False)

    # -- Lo que le da la ventana principal ----------------------------------

    def set_metric(self, label: str, series: dict[str, np.ndarray]) -> None:
        """Dibuja una métrica por canal.

        Args:
            label: cómo se llama lo que se está midiendo. Va al eje vertical,
                porque un número por ventana sin decir de qué es no sirve.
            series: canal -> array con un valor por ventana, tal como lo
                devuelven `complexity_by_window()` y el promedio de
                `connectivity_by_window()`.

        Redibujar **reemplaza**: pedir otra métrica no puede dejar encima la
        anterior, que quedarían superpuestas en escalas distintas.
        """
        item = self.getPlotItem()
        for curva in self._curvas.values():
            item.removeItem(curva)
        self._curvas.clear()
        self._series.clear()
        self._etiqueta = label
        item.setLabel("left", label)

        for posicion, (nombre, valores) in enumerate(series.items()):
            datos = np.asarray(valores, dtype=float)
            # **Base 1 al mostrar.** La ventana 0 del modelo es la 1 para el
            # usuario, igual que en el histograma y en la barra de estado.
            ventanas = np.arange(1, len(datos) + 1, dtype=float)
            curva = item.plot(
                ventanas,
                datos,
                # `connect="finite"` es lo que deja el hueco en los NaN en vez
                # de unir la curva por encima de ellos, que sugeriría una
                # continuidad que no se midió.
                connect="finite",
                pen=pg.mkPen(_COLOR if posicion == 0 else None, width=2),
                name=nombre,
            )
            self._curvas[nombre] = curva
            self._series[nombre] = datos

        if self._series:
            largo = max(len(v) for v in self._series.values())
            item.setXRange(1, max(largo, 1), padding=0.01)

    def clear_metric(self) -> None:
        """Deja el panel vacío."""
        self.set_metric("", {})

    # -- Lo que se puede afirmar sin mirar ----------------------------------

    def channels(self) -> list[str]:
        """Los canales dibujados, en orden."""
        return list(self._series)

    def series(self, channel_name: str) -> np.ndarray | None:
        """Los valores de un canal, tal como se los pasaron."""
        return self._series.get(channel_name)

    def window_positions(self, channel_name: str) -> np.ndarray | None:
        """Las posiciones del eje horizontal, **en base 1**.

        Está expuesto porque la conversión de base es una decisión y se testea:
        dibujar desde 0 desplazaría la curva una ventana respecto del
        histograma, que es el error que hace que dos gráficos alineados no lo
        estén.
        """
        if channel_name not in self._series:
            return None
        x, _ = self._curvas[channel_name].getData()
        return np.asarray(x)

    def gap_windows(self, channel_name: str) -> list[int]:
        """Qué ventanas quedaron sin medir, **en base 1**.

        Son las que llegaron como NaN. Se exponen para poder afirmar que se
        dibujan como hueco y no como cero.
        """
        valores = self._series.get(channel_name)
        if valores is None:
            return []
        return [int(posicion) + 1 for posicion in np.flatnonzero(np.isnan(valores))]

    @property
    def metric_label(self) -> str:
        """Qué se está midiendo, tal como se rotula el eje vertical."""
        return self._etiqueta
