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
from datetime import datetime

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from psglab.ui import theme
from psglab.ui.panel_header import EmptyState, PanelHeader, plain_axes
from psglab.ui.signal_view import TimeAxis

#: Color de las barras de la topografía.
# El color de las dos curvas sale del esquema en uso: es una sola serie por
# gráfico, así que le toca el color de acento y no la paleta de canales.


def _porcentaje(fraccion: float) -> str:
    """Una fracción como porcentaje entero, con «<1 %» para lo que no llega.

    **Entero a propósito**: la varianza se estima sobre una muestra de la
    noche, y un decimal diría una precisión que no tiene. Menos de uno no se
    escribe «0 %», que se leería como un componente vacío.
    """
    porcentaje = 100.0 * fraccion
    if porcentaje < 1.0:
        return "<1 %"
    return f"{round(porcentaje)} %"


class IcaPanel(QWidget):
    """Lista de componentes, topografía del elegido, y qué excluir."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ninguna descomposición."""
        super().__init__(parent)
        #: Desde qué menú se pide lo que muestra este panel. Ver `set_hint()`.
        self._pista: str = ""
        self._pista_visible: bool = False
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
        self.lista.itemChanged.connect(self._reflejar_el_boton)

        self.grafico = pg.PlotWidget()
        item = self.grafico.getPlotItem()
        plain_axes(item)
        item.setLabel("left", "Peso en el componente")
        item.setMenuEnabled(False)
        item.showGrid(y=True, alpha=0.3)

        # **La otra mitad del criterio.** La topografía dice *dónde* pesa el
        # componente y esta curva dice *cuándo* ocurre: un parpadeo son picos
        # aislados y el ruido de línea una oscilación constante. Con una sola de
        # las dos, el investigador decide a ciegas sobre una operación que no se
        # puede deshacer. Hasta el hito 19 `component_time_course()` calculaba
        # esto y no lo dibujaba nadie.
        # **El eje de abajo es el del visualizador** (hito 54): hora de la noche
        # si el archivo la informa, segundos si no. Decía «Segundos de la
        # ventana» y contaba desde cero, así que no había cómo ubicar un pico
        # de la curva en la señal de arriba.
        self._eje_de_tiempo = TimeAxis()
        self.curva = pg.PlotWidget(axisItems={"bottom": self._eje_de_tiempo})
        curva = self.curva.getPlotItem()
        plain_axes(curva)
        curva.setLabel("left", "Componente")
        curva.setMenuEnabled(False)
        curva.showGrid(x=True, y=True, alpha=0.3)

        self.aviso = QLabel(
            "Quitar un componente no se puede deshacer sobre la señal ya "
            "transformada. Se guarda el registro original."
        )
        self.aviso.setWordWrap(True)

        self.boton = QPushButton("Aplicar y quitar los marcados")
        # El principal del panel, relleno del acento (hito 55).
        self.boton.setProperty(theme.PRIMARIO_PROPERTY, True)
        self.boton.clicked.connect(self._aplicar)
        self.boton.setEnabled(False)

        #: El encabezado, con cuántos componentes salieron. Ver `PanelHeader`.
        self.header = PanelHeader("ICA")

        #: Lo que se ve mientras no hay ninguna descomposición. Ver `EmptyState`.
        self.vacio = EmptyState()

        izquierda = QVBoxLayout()
        izquierda.addWidget(QLabel("Componentes (marcar los que se quitan):"))
        izquierda.addWidget(self.lista)
        izquierda.addWidget(self.aviso)
        izquierda.addWidget(self.boton)

        derecha = QVBoxLayout()
        derecha.addWidget(self.grafico, stretch=3)
        derecha.addWidget(self.curva, stretch=2)

        cuerpo = QWidget()
        fila = QHBoxLayout(cuerpo)
        fila.setContentsMargins(8, 8, 8, 8)
        fila.addLayout(izquierda, stretch=1)
        fila.addLayout(derecha, stretch=2)

        #: El cuerpo o el cartel de panel vacío, nunca los dos.
        #:
        #: **Acá el cartel reemplaza las dos columnas y no sólo los gráficos**:
        #: sin descomposición, la lista de componentes está vacía y el botón de
        #: aplicar, apagado. Media pantalla de controles muertos al lado de una
        #: frase se lee como un panel roto.
        self._pila = QStackedWidget()
        self._pila.addWidget(cuerpo)
        self._pila.addWidget(self.vacio)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self.header)
        columna.addWidget(self._pila)
        self._reflejar_pista()

    # -- Lo que le da la ventana principal ----------------------------------

    def set_components(
        self,
        topographies: list[dict[str, float]],
        variances: list[float] | None = None,
    ) -> None:
        """Carga las topografías de todos los componentes.

        Args:
            topographies: una por componente, en orden, tal como las devuelve
                `analysis.ica.component_topography()`.
            variances: la fracción de la varianza que explica cada uno, como
                la devuelve `analysis.ica.explained_variance()`. Se escribe al
                lado del nombre (hito 54): es la pista de cuál pesa más.

        **Ninguno queda marcado**: elegir por el usuario sobre una operación
        irreversible sería decidir por él.
        """
        self._topografias = [dict(t) for t in topographies]
        self._varianzas = list(variances) if variances is not None else []
        self.lista.clear()
        for numero in range(len(self._topografias)):
            # Base 1 al mostrar, como todo lo que el usuario numera.
            texto = f"Componente {numero + 1}"
            if numero < len(self._varianzas):
                texto = f"{texto} · {_porcentaje(self._varianzas[numero])}"
            entrada = QListWidgetItem(texto)
            entrada.setFlags(entrada.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            entrada.setCheckState(Qt.CheckState.Unchecked)
            self.lista.addItem(entrada)

        self.boton.setEnabled(bool(self._topografias))
        if self._topografias:
            self.lista.setCurrentRow(0)
        else:
            self.grafico.getPlotItem().clear()
        self._reflejar_el_boton()
        self._reflejar_pista()

    def set_start_time(self, start_time: datetime | None) -> None:
        """A qué hora empezó el registro, para numerar la curva en hora real.

        `None` si el archivo no lo informa: la curva vuelve a los segundos, en
        vez de inventar una hora.
        """
        self._eje_de_tiempo.set_start_time(start_time)

    def _reflejar_el_boton(self, *_args: object) -> None:
        """El botón dice cuántos va a quitar (hito 54).

        Decía «Aplicar y quitar los marcados» con uno, con cinco y con ninguno:
        sobre una operación que no se puede deshacer, el número es lo último
        que se lee antes de apretar.
        """
        cuantos = len(self.excluded())
        if cuantos == 0:
            texto = "Aplicar y quitar los marcados"
        elif cuantos == 1:
            texto = "Aplicar y quitar el marcado"
        else:
            texto = f"Aplicar y quitar los {cuantos} marcados"
        self.boton.setText(texto)

    def clear_components(self) -> None:
        """Deja el panel vacío."""
        self.set_components([])

    # -- Con el panel vacío ---------------------------------------------------

    def set_hint(self, text: str) -> None:
        """Lo que se lee mientras el panel está vacío: desde qué menú se pide.

        **Existe porque el panel se puede mostrar sin resultado**: desde
        «Herramientas», o después de que cambió la señal y el resultado se
        descartó. Un gráfico en blanco no dice qué hacer con él. El texto lo
        arma la ventana principal con `menus.menu_path()`, así que sigue al
        menú si alguien lo renombra.
        """
        self._pista = text
        self._reflejar_pista()

    def visible_hint(self) -> str:
        """La pista que se lee hoy, o vacío si el panel tiene un resultado."""
        return self._pista if self._pista_visible else ""

    def _reflejar_pista(self) -> None:
        """Pone el encabezado y decide si se ve el cuerpo o el cartel de vacío.

        **La pista iba al título del gráfico** hasta el hito 41, con la lista de
        componentes vacía y el botón apagado a su lado: media pantalla de
        controles muertos junto a una frase.
        """
        self._pista_visible = bool(self._pista) and not self._topografias
        self.header.set_caption(self._describirse())
        self.vacio.set_text(self._pista)
        self._pila.setCurrentWidget(
            self.vacio if self._pista_visible else self._pila.widget(0)
        )

    def _describirse(self) -> str:
        """Cuántos componentes salieron, que es lo primero que se mira."""
        cuantos = len(self._topografias)
        if not cuantos:
            return ""
        canales = len(self._topografias[0])
        return f"{cuantos} componentes · {canales} canales"

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
            seconds: segundos **desde el inicio del registro** (hito 54), que es
                lo que numera el eje del visualizador. Eran segundos desde el
                inicio de la ventana.
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
        item.plot(x, y, pen=pg.mkPen(theme.current().accent, width=1))

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
                x=posiciones,
                height=alturas,
                width=0.6,
                brush=pg.mkBrush(theme.current().accent),
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
