"""Panel para inspeccionar una descomposición ICA y elegir qué quitar.

`analysis/ica.py` separa el flujo en tres pasos —ajustar, inspeccionar,
aplicar— justamente porque **quitar el componente equivocado modifica la señal
de forma irreversible**. Este panel es el paso del medio, y está diseñado
alrededor de esa advertencia:

- Nada se aplica solo. El usuario marca los componentes y aprieta un botón.
- **Ninguno viene marcado de fábrica.** Sugerir cuál quitar sería adivinar por
  él sobre una operación que no se puede deshacer.
- La topografía se muestra **antes** de poder marcar nada.

**La topografía son los pesos por canal, no un mapa del cuero cabelludo.** El
motivo está en `analysis/ica.py`: dibujar un mapa necesitaría las coordenadas de
cada electrodo, que `Channel` no lleva. Los pesos alcanzan para lo que la vista
existe: un parpadeo se reconoce porque los frontales tienen barras altas y los
occipitales bajas, y eso se ve igual en un gráfico de barras.

Como los demás paneles, lo que se puede afirmar sin mirar una pantalla está
separado del dibujo.

Cubre del pliego: ningún ID propio. Es la mitad que se ve de V5_F de
"Filtración de la señal".
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

#: Color de las barras de la topografía.
_COLOR = "#4a90e6"


class IcaPanel(QWidget):
    """Lista de componentes, topografía del elegido, y qué excluir."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ninguna descomposición."""
        super().__init__(parent)
        self._topografias: list[dict[str, float]] = []
        self._curva: tuple[np.ndarray, np.ndarray] | None = None
        #: A quién avisarle cuando el usuario aprieta "Aplicar". Lo cablea la
        #: ventana principal, igual que los callbacks de las herramientas.
        self.on_apply: Callable[[list[int]], None] | None = None
        #: A quién pedirle la curva temporal del componente que se muestra.
        #:
        #: **El panel no la calcula**: reconstruir las fuentes necesita
        #: `analysis/ica.py` y el registro abierto, y `ui/` no conoce ninguno de
        #: los dos por su cuenta. Avisa cuál se está mirando y espera que le
        #: pasen la curva con `set_time_course()`, que es el mismo reparto que
        #: usa `PsdPanel`: acá se dibuja, el cálculo es de otro.
        self.on_component_shown: Callable[[int], None] | None = None

        self.lista = QListWidget()
        self.lista.currentRowChanged.connect(self._mostrar)

        self.grafico = pg.PlotWidget()
        item = self.grafico.getPlotItem()
        item.setLabel("left", "Peso en el componente")
        item.setMenuEnabled(False)
        item.showGrid(y=True, alpha=0.3)

        # **La otra mitad del criterio.** La topografía dice *dónde* pesa el
        # componente y esta curva dice *cuándo* ocurre: un parpadeo son picos
        # aislados y el ruido de línea una oscilación constante. Con una sola de
        # las dos, el investigador decide a ciegas sobre una operación que no se
        # puede deshacer. Hasta el hito 19 `component_time_course()` calculaba
        # esto y no lo dibujaba nadie.
        self.curva = pg.PlotWidget()
        curva = self.curva.getPlotItem()
        curva.setLabel("left", "Componente")
        curva.setLabel("bottom", "Segundos de la ventana")
        curva.setMenuEnabled(False)
        curva.showGrid(x=True, y=True, alpha=0.3)

        self.aviso = QLabel(
            "Quitar un componente no se puede deshacer sobre la señal ya "
            "transformada. Se guarda el registro original."
        )
        self.aviso.setWordWrap(True)

        self.boton = QPushButton("Aplicar y quitar los marcados")
        self.boton.clicked.connect(self._aplicar)
        self.boton.setEnabled(False)

        izquierda = QVBoxLayout()
        izquierda.addWidget(QLabel("Componentes (marcar los que se quitan):"))
        izquierda.addWidget(self.lista)
        izquierda.addWidget(self.aviso)
        izquierda.addWidget(self.boton)

        derecha = QVBoxLayout()
        derecha.addWidget(self.grafico, stretch=3)
        derecha.addWidget(self.curva, stretch=2)

        fila = QHBoxLayout(self)
        fila.addLayout(izquierda, stretch=1)
        fila.addLayout(derecha, stretch=2)

    # -- Lo que le da la ventana principal ----------------------------------

    def set_components(self, topographies: list[dict[str, float]]) -> None:
        """Carga las topografías de todos los componentes.

        Args:
            topographies: una por componente, en orden, tal como las devuelve
                `analysis.ica.component_topography()`.

        **Ninguno queda marcado**: elegir por el usuario sobre una operación
        irreversible sería decidir por él.
        """
        self._topografias = [dict(t) for t in topographies]
        self.lista.clear()
        for numero in range(len(self._topografias)):
            # Base 1 al mostrar, como todo lo que el usuario numera.
            entrada = QListWidgetItem(f"Componente {numero + 1}")
            entrada.setFlags(entrada.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            entrada.setCheckState(Qt.CheckState.Unchecked)
            self.lista.addItem(entrada)

        self.boton.setEnabled(bool(self._topografias))
        if self._topografias:
            self.lista.setCurrentRow(0)
        else:
            self.grafico.getPlotItem().clear()

    def clear_components(self) -> None:
        """Deja el panel vacío."""
        self.set_components([])

    # -- Lo que se puede afirmar sin mirar ----------------------------------

    def component_count(self) -> int:
        """Cuántos componentes hay cargados."""
        return len(self._topografias)

    def excluded(self) -> list[int]:
        """Qué componentes marcó el usuario, **en base 0**.

        Base 0 porque es lo que `apply_ica()` espera: la conversión desde el
        "Componente 1" que se lee en pantalla se hace acá, que es el borde.
        """
        return [
            fila
            for fila in range(self.lista.count())
            if self.lista.item(fila).checkState() == Qt.CheckState.Checked
        ]

    def set_excluded(self, components: list[int]) -> None:
        """Marca los componentes indicados, en base 0."""
        marcados = set(components)
        for fila in range(self.lista.count()):
            self.lista.item(fila).setCheckState(
                Qt.CheckState.Checked if fila in marcados else Qt.CheckState.Unchecked
            )

    def shown_component(self) -> int | None:
        """Cuál se está mostrando, en base 0, o None si no hay ninguno."""
        fila = self.lista.currentRow()
        return fila if 0 <= fila < len(self._topografias) else None

    def topography_bars(self) -> dict[str, float]:
        """Las barras dibujadas del componente que se está mostrando.

        Está expuesto por el mismo motivo que `band_ranges()` en el panel del
        espectro: **qué se dibuja es una decisión y se testea**; los píxeles no.
        """
        numero = self.shown_component()
        return dict(self._topografias[numero]) if numero is not None else {}

    def set_time_course(self, seconds: np.ndarray, values: np.ndarray) -> None:
        """Dibuja la serie temporal del componente que se está mostrando.

        Args:
            seconds: segundos desde el inicio de la ventana.
            values: el componente, en sus unidades arbitrarias.

        El eje vertical **no se fija**, a diferencia del de la topografía: ahí la
        escala es comparable entre componentes porque los pesos vienen
        normalizados, y acá las unidades son arbitrarias y lo que se lee es la
        **forma** —picos aislados contra oscilación constante—, no la altura.
        """
        item = self.curva.getPlotItem()
        item.clear()
        x = np.asarray(seconds, dtype=float)
        y = np.asarray(values, dtype=float)
        self._curva = (x, y)
        item.plot(x, y, pen=pg.mkPen(_COLOR, width=1))

    def clear_time_course(self) -> None:
        """Deja el gráfico de abajo vacío."""
        self._curva = None
        self.curva.getPlotItem().clear()

    def time_course_data(self) -> tuple[np.ndarray, np.ndarray] | None:
        """La curva dibujada, o None si no hay ninguna.

        Mismo motivo que `topography_bars()`: qué se dibuja se testea.
        """
        return self._curva

    # -- Adentro -------------------------------------------------------------

    def _mostrar(self, fila: int) -> None:
        """Dibuja la topografía del componente elegido, y pide su curva.

        La curva se pide **al cambiar de componente y no al cargar la lista**:
        reconstruir las fuentes cuesta, y de otro modo se pagarían todas las de
        una descomposición para mirar una.
        """
        item = self.grafico.getPlotItem()
        item.clear()
        self.clear_time_course()
        if not 0 <= fila < len(self._topografias):
            return

        pesos = self._topografias[fila]
        nombres = list(pesos)
        alturas = [pesos[n] for n in nombres]
        posiciones = np.arange(len(nombres), dtype=float)

        item.addItem(
            pg.BarGraphItem(
                x=posiciones, height=alturas, width=0.6, brush=pg.mkBrush(_COLOR)
            )
        )
        item.getAxis("bottom").setTicks(
            [[(posicion, nombre) for posicion, nombre in zip(posiciones, nombres)]]
        )
        # Fijo de -1 a 1: los pesos vienen normalizados, y con escala automática
        # un componente plano se vería igual de marcado que uno concentrado.
        item.setYRange(-1.05, 1.05, padding=0)
        item.setTitle(f"Componente {fila + 1}")

        # **Al final, y no antes de dibujar la topografía.** Reconstruir las
        # fuentes puede fallar —un registro que ya no es el del ajuste— y si eso
        # ocurriera primero, el usuario se quedaría sin ver ni siquiera los
        # pesos, que es el dato que este panel siempre puede dar.
        if self.on_component_shown is not None:
            self.on_component_shown(fila)

    def _aplicar(self) -> None:
        """Avisa de qué componentes hay que quitar."""
        if self.on_apply is not None:
            self.on_apply(self.excluded())
