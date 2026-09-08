"""Panel del espectro: dibuja lo que calcula `analysis/psd.py`.

`compute_psd()` devuelve frecuencias y potencias y **no dibuja nada**, porque
`analysis/` no conoce Qt. Este módulo es la otra mitad.

**Acá sí se usa pyqtgraph**, a diferencia del panel de la Übersicht, que se
pinta con `QPainter`. La diferencia no es de gusto: un espectro es una curva
sobre ejes con escala, con un eje de frecuencia que hay que poder leer y un eje
de potencia que conviene en logarítmico. La Übersicht son rectángulos sin
sistema de coordenadas. Cada uno usa la herramienta que corresponde a lo que
dibuja.

**El eje de potencia va en logarítmico**, y no es una preferencia: la potencia
delta de una ventana de sueño lento es de dos a tres órdenes de magnitud mayor
que la gamma de la misma ventana. En lineal, todo lo que no es delta queda
aplastado contra el eje y el espectro no se puede leer.

Como en `overview_panel.py`, lo que se puede afirmar sin mirar una pantalla
—qué curvas hay, qué bandas se sombrean y dónde caen— está separado del dibujo.

Cubre del pliego: V1_F de "Power Spectral Density (PSD)", la mitad que se ve.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget

from psglab.analysis.psd import DEFAULT_BANDS

#: Colores de las bandas sombreadas, en orden. No salen de `config.py` porque
#: el pliego no fija ninguno: pide mostrar la PSD por banda, y con qué color se
#: distinguen es del programa.
_COLORES = (
    "#4a90e6",  # delta
    "#6cb04a",  # theta
    "#e6c04a",  # alpha
    "#e6754a",  # sigma
    "#b04ae6",  # beta
    "#4ab0a8",  # gamma
)

#: Transparencia del sombreado, en hexadecimal sobre el color. Bajo a propósito:
#: la banda tiene que ubicar la mirada, no tapar la curva.
_ALPHA = "33"


class PsdPanel(pg.PlotWidget):
    """Dibuja el espectro de uno o varios canales, con sus bandas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ningún espectro calculado."""
        super().__init__(parent)
        self._curvas: dict[str, pg.PlotDataItem] = {}
        #: Los valores tal como se los pasaron, en µV²/Hz. **No se leen de la
        #: curva.** Con el eje en logarítmico, `PlotDataItem.getData()` devuelve
        #: lo que se dibuja —el log₁₀— y no lo que se pidió dibujar: una
        #: potencia de 1e-6 vuelve como -6. Es la misma confusión de unidades
        #: que el proyecto persigue en `signal_view.py` con los píxeles, y se
        #: resuelve igual: guardando la magnitud en su unidad.
        self._datos: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._bandas: list[tuple[str, pg.LinearRegionItem]] = []

        item = self.getPlotItem()
        item.setLogMode(x=False, y=True)
        item.setLabel("bottom", "Frecuencia", units="Hz")
        item.setLabel("left", "Potencia", units="µV²/Hz")
        item.showGrid(x=True, y=True, alpha=0.3)
        item.addLegend(offset=(-10, 10))
        item.setMenuEnabled(False)

    # -- Lo que le da la ventana principal ----------------------------------

    def set_spectrum(
        self,
        frequencies: np.ndarray,
        powers: np.ndarray,
        channel_names: list[str],
        bands: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        """Dibuja el espectro que devolvió `compute_psd()`.

        Args:
            frequencies: eje de frecuencias, de forma (n_frecuencias,).
            powers: potencias, de forma (n_canales, n_frecuencias).
            channel_names: un nombre por fila de `powers`, para la leyenda.
            bands: bandas a sombrear. Sin ellas, las convencionales.

        Redibujar **reemplaza**: pedir el espectro de otra ventana no puede
        dejar encima la curva de la anterior, que es el error que haría creer
        que el espectro cambió menos de lo que cambió.
        """
        item = self.getPlotItem()
        for curva in self._curvas.values():
            item.removeItem(curva)
        self._curvas.clear()
        self._datos.clear()
        for _, region in self._bandas:
            item.removeItem(region)
        self._bandas.clear()

        frecuencias = np.asarray(frequencies, dtype=float)
        potencias = np.atleast_2d(np.asarray(powers, dtype=float))

        definiciones = dict(bands) if bands is not None else dict(DEFAULT_BANDS)
        for posicion, (nombre, (desde, hasta)) in enumerate(definiciones.items()):
            color = _COLORES[posicion % len(_COLORES)]
            region = pg.LinearRegionItem(
                values=(desde, hasta), movable=False, brush=pg.mkBrush(color + _ALPHA)
            )
            # Detrás de las curvas: la banda ubica la mirada, no tapa el dato.
            region.setZValue(-10)
            item.addItem(region)
            self._bandas.append((nombre, region))

        for posicion, nombre in enumerate(channel_names):
            if posicion >= potencias.shape[0]:
                break
            curva = item.plot(
                frecuencias,
                potencias[posicion],
                pen=pg.mkPen(_COLORES[posicion % len(_COLORES)], width=2),
                name=nombre,
            )
            self._curvas[nombre] = curva
            self._datos[nombre] = (frecuencias, potencias[posicion])

        if frecuencias.size:
            item.setXRange(float(frecuencias[0]), float(frecuencias[-1]), padding=0.02)

    def clear_spectrum(self) -> None:
        """Deja el panel vacío, como antes del primer cálculo."""
        self.set_spectrum(np.array([]), np.empty((0, 0)), [])

    # -- Lo que se puede afirmar sin mirar ----------------------------------

    def channels(self) -> list[str]:
        """Los canales que hay dibujados, en orden."""
        return list(self._curvas)

    def band_ranges(self) -> dict[str, tuple[float, float]]:
        """Qué banda está sombreada y entre qué frecuencias.

        Está separado del dibujo por el mismo motivo que `rectangles()` en el
        panel de la Übersicht: **dónde cae cada banda es una decisión y se
        testea**; los píxeles no.
        """
        return {
            nombre: (float(region.getRegion()[0]), float(region.getRegion()[1]))
            for nombre, region in self._bandas
        }

    def curve_data(self, channel_name: str) -> tuple[np.ndarray, np.ndarray] | None:
        """Los puntos de un canal **en µV²/Hz**, o None si no está.

        Devuelve lo que se pasó y no lo que pyqtgraph tiene guardado: con el eje
        en logarítmico, `getData()` entrega el log₁₀ de la potencia, así que una
        de 1e-6 volvería como -6. Quien pregunte por el espectro está pensando
        en potencia, no en su logaritmo.
        """
        return self._datos.get(channel_name)

    @property
    def uses_log_power(self) -> bool:
        """Si el eje de potencia está en logarítmico.

        Lo está, y es lo que hace legible el espectro: en lineal, todo lo que
        no es delta queda aplastado contra el eje.
        """
        return bool(self.getPlotItem().ctrl.logYCheck.isChecked())
