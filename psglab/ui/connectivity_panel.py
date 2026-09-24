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

**Dejó de ser un `PlotWidget` y pasó a contener uno** en el hito 39, con la
carrocería que comparten los seis paneles: el encabezado de
`psglab/ui/panel_header.py` y el cartel que **reemplaza** al gráfico mientras
no hay resultado. Antes las dos cosas iban al título del gráfico, así que un
panel vacío seguía mostrando ejes, grilla y leyenda detrás de la frase.

Cubre del pliego: ningún ID propio. Es la mitad que se ve de la sección
"Conectividad de la señal".
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsRectItem, QStackedWidget, QVBoxLayout, QWidget

from psglab.ui import theme
from psglab.ui.fonts import font_for
from psglab.ui.panel_header import EmptyState, PanelHeader

#: Hasta cuántos canales se escribe el valor dentro de cada celda (hito 55).
#: Con más, la celda es más chica que el número y los textos se pisan.
MAXIMO_DE_CANALES_CON_VALORES: int = 12

#: Extremos de la escala de color. Las cinco medidas de `METHODS` están
#: acotadas a este rango, así que la escala fija es correcta para todas.
_MINIMO: float = 0.0
_MAXIMO: float = 1.0


class ConnectivityPanel(QWidget):
    """Dibuja una matriz de conectividad como mapa de calor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ninguna matriz calculada."""
        super().__init__(parent)
        self.grafico = pg.PlotWidget()
        #: Desde qué menú se pide lo que muestra este panel. Ver `set_hint()`.
        self._pista: str = ""
        self._pista_visible: bool = False
        #: Qué es el resultado que se muestra. Ver `set_caption()`.
        self._titulo: str = ""
        self._matriz: np.ndarray | None = None
        self._canales: list[str] = []
        #: Qué mide la escala de color. Ver `set_measure()`.
        self._medida: str = ""

        #: Los valores escritos en las celdas y el gris de la diagonal.
        #: Se rehacen con cada matriz.
        self._rotulos: list[object] = []
        self._imagen = pg.ImageItem()
        item = self.grafico.getPlotItem()
        item.addItem(self._imagen)
        item.setMenuEnabled(False)
        item.setMouseEnabled(x=False, y=False)
        item.invertY(True)
        # La barra de color explica qué significa cada tono. Sin ella el mapa
        # es bonito y no dice nada.
        #
        # **Se arrastra de a centésimos y sin salir de 0 a 1.** Por omisión
        # `ColorBarItem` redondea los extremos a enteros, y sobre esta escala
        # eso hacía que cualquier arrastre volviera a su lugar o saltara al
        # otro extremo. Arrastrarla sirve para resaltar diferencias chicas
        # entre pares de canales.
        self._barra = pg.ColorBarItem(
            values=(_MINIMO, _MAXIMO),
            colorMap=pg.colormap.get("viridis"),
            limits=(_MINIMO, _MAXIMO),
            rounding=0.01,
        )
        self._barra.setImageItem(self._imagen, insert_in=item)

        #: El encabezado, con qué se está mirando. Ver `PanelHeader`.
        self.header = PanelHeader("Conectividad")

        #: Lo que se ve mientras no hay ninguna matriz. Ver `EmptyState`.
        self.vacio = EmptyState()

        #: El gráfico o el cartel de panel vacío, nunca los dos: un mapa con
        #: ejes y barra de color detrás de una frase se lee como una matriz
        #: que dio cero.
        self._pila = QStackedWidget()
        self._pila.addWidget(self.grafico)
        self._pila.addWidget(self.vacio)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self.header)
        columna.addWidget(self._pila)
        self._reflejar_titulo()

    # -- Lo que le da la ventana principal ----------------------------------

    def set_matrix(
        self,
        matrix: np.ndarray,
        channel_names: list[str],
        measure: str = "",
    ) -> None:
        """Dibuja la matriz con los nombres de canal en los dos ejes.

        Args:
            matrix: matriz cuadrada, tal como la devuelve
                `compute_connectivity()`.
            channel_names: un nombre por fila, en el mismo orden.
            measure: qué mide la escala de color —«wPLI», «PLI», «Coherencia»—.
                **La barra decía de 0 a 1 y no de qué**: un mapa de colores sin
                la unidad se puede leer de izquierda a derecha, pero no se
                puede comparar con el de otra medida.
        """
        datos = np.asarray(matrix, dtype=float)
        self._matriz = datos
        self._canales = list(channel_names)

        # Con los niveles que tenga la barra y no con 0 a 1: si el usuario la
        # ajustó, la matriz nueva se ve con el mismo contraste que la anterior,
        # y la barra no queda diciendo otra cosa que la imagen.
        self._imagen.setImage(datos, levels=self._barra.levels())
        self.set_measure(measure)
        item = self.grafico.getPlotItem()
        # Los ticks van en el centro de cada celda, que es donde el usuario
        # espera leerlos: en el borde, un nombre queda entre dos filas.
        marcas = [
            (posicion + 0.5, nombre) for posicion, nombre in enumerate(self._canales)
        ]
        item.getAxis("bottom").setTicks([marcas])
        item.getAxis("left").setTicks([marcas])
        self._escribir_las_celdas()
        self._reflejar_titulo()

    def _escribir_las_celdas(self) -> None:
        """El valor de cada celda y la diagonal marcada «—» (hito 55).

        **El mapa sólo tenía color**, y un tono de viridis no se lee como un
        número: el prototipo escribía el valor en cada celda. La tinta se
        elige contra el color de esa celda, con la misma función que los
        chips. Sólo hasta `MAXIMO_DE_CANALES_CON_VALORES`: con más, la celda es
        más chica que el número.

        **La diagonal no se calcula**: un canal contra sí mismo daría siempre
        1, y `compute_connectivity()` la deja en cero. Pintada como cero se
        leía como «estos canales no se parecen», que es falso; va en gris.
        """
        item = self.grafico.getPlotItem()
        for rotulo in self._rotulos:
            item.removeItem(rotulo)
        self._rotulos.clear()
        if self._matriz is None:
            return
        esquema = theme.current()
        mapa = self._barra.colorMap()
        cuantos = len(self._canales)
        for fila in range(cuantos):
            celda = QGraphicsRectItem(QRectF(fila, fila, 1.0, 1.0))
            celda.setBrush(QBrush(QColor(esquema.overview_background)))
            # **Cosmética**: sin eso el grosor de 1 es de una celda entera, en
            # las unidades del gráfico, y la diagonal salía como una mancha.
            borde = QPen(QColor(esquema.overview_border))
            borde.setCosmetic(True)
            celda.setPen(borde)
            item.addItem(celda)
            self._rotulos.append(celda)
        if cuantos > MAXIMO_DE_CANALES_CON_VALORES:
            return
        bajo, alto = self._barra.levels()
        fuente = font_for("chip", self.font())
        for fila in range(cuantos):
            for columna in range(cuantos):
                valor = float(self._matriz[fila, columna])
                if fila == columna:
                    texto, fondo = "—", esquema.overview_background
                elif np.isnan(valor):
                    continue
                else:
                    texto = f"{valor:.2f}".replace(".", ",")
                    posicion = 0.0 if alto <= bajo else (valor - bajo) / (alto - bajo)
                    fondo = mapa.map(min(max(posicion, 0.0), 1.0), mode="qcolor").name()
                rotulo = pg.TextItem(
                    texto, color=theme.ink_over(esquema, fondo), anchor=(0.5, 0.5)
                )
                rotulo.setFont(fuente)
                rotulo.setPos(fila + 0.5, columna + 0.5)
                item.addItem(rotulo)
                self._rotulos.append(rotulo)

    def cell_labels(self) -> list[str]:
        """Los textos escritos en las celdas, en orden: lo que se afirma sin mirar."""
        return [r.toPlainText() for r in self._rotulos if isinstance(r, pg.TextItem)]

    def set_measure(self, text: str) -> None:
        """Rotula la escala de color con lo que mide."""
        self._medida = text
        self._barra.setLabel("right", text or None)

    def measure(self) -> str:
        """Lo que dice hoy el rótulo de la escala, o vacío."""
        return self._medida

    def clear_matrix(self) -> None:
        """Deja el panel vacío."""
        self._titulo = ""
        self._matriz = None
        self._canales = []
        self._imagen.clear()
        self._escribir_las_celdas()
        # Sin matriz no hay contraste que conservar: la próxima arranca de 0 a 1.
        self._barra.setLevels((_MINIMO, _MAXIMO))
        self.set_measure("")
        self.grafico.getPlotItem().getAxis("bottom").setTicks(None)
        self.grafico.getPlotItem().getAxis("left").setTicks(None)
        self._reflejar_titulo()

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
        self._reflejar_titulo()

    def visible_hint(self) -> str:
        """La pista que se lee hoy, o vacío si el panel tiene un resultado."""
        return self._pista if self._pista_visible else ""

    def set_caption(self, text: str) -> None:
        """Qué es el resultado que se muestra: el canal, la ventana, la banda.

        **Va en el gráfico y no en el título del panel.** Hasta el hito 31 la
        ventana principal se lo ponía al dock con `setWindowTitle()`, y Qt usa
        ese título como texto de la entrada del panel en «Herramientas»: el
        menú se renombraba con cada cálculo.
        """
        self._titulo = text
        self._reflejar_titulo()

    def caption(self) -> str:
        """La descripción del resultado que se muestra, o vacío."""
        return self._titulo

    def _reflejar_titulo(self) -> None:
        """Pone el encabezado y decide si se ve el gráfico o el cartel de vacío.

        **El cartel reemplaza al gráfico, no lo tapa.** Hasta el hito 39 las
        dos cosas iban al título del gráfico, así que el panel vacío seguía
        mostrando ejes, grilla y leyenda detrás de la frase: se leía como un
        resultado que dio cero.
        """
        vacio = self._matriz is None
        self._pista_visible = bool(self._pista) and vacio
        self.header.set_caption("" if vacio else self._titulo)
        self.vacio.set_text(self._pista)
        self._pila.setCurrentWidget(self.vacio if self._pista_visible else self.grafico)

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
        marcas = self.grafico.getPlotItem().getAxis("bottom")._tickLevels
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
