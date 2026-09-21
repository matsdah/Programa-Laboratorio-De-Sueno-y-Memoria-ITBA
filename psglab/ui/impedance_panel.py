"""Panel de impedancias: la tabla editable y el informe.

Es donde viven **las tres vías** que plantea `analysis/impedance.py`. Dos de
ellas llegan de afuera —del archivo abierto y de un archivo aparte— y la
tercera es este panel: `analysis/` no conoce Qt, así que cargar valores a mano
sólo puede vivir acá.

**El estado "sin medir" se muestra distinto de "0 kΩ", y es la razón de ser de
todo el módulo.** Un electrodo suelto que nadie midió es el caso peligroso: si
apareciera como cero pasaría por perfecto, porque cero es el mejor valor
posible. La celda vacía dice "sin medir" con todas las letras.

**La columna de estado dice si cada canal pasa el límite, y son dos estados y
no tres.** `analysis/impedance.py` define un solo umbral —`channels_above_limit()`,
inclusive— y no una escala de semáforo: un «aceptable» intermedio sería un
criterio clínico que el programa no tiene y que el informe no comparte. El
límite es el mismo con el que se arma el informe, así que los dos no se pueden
contradecir.

Como los demás paneles, lo que se puede afirmar sin mirar una pantalla está
separado del dibujo.

Cubre del pliego: ningún ID propio. Es la mitad que se ve de V1_F de
"Impedancia de los electrodos".
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psglab.analysis.impedance import DEFAULT_LIMIT_KOHM
from psglab.ui import theme
from psglab.ui.panel_header import ROL_DEL_COLOR, ChipDelegate, PanelHeader

#: Lo que dice una celda sin valor. **No es "0" ni está vacía**: un cero
#: pasaría por el mejor valor posible y una celda vacía se lee como un olvido
#: de la pantalla, no del electrodo.
SIN_MEDIR: str = "sin medir"

#: Las columnas de la tabla, en orden.
COLUMNAS: Final[list[str]] = ["Canal", "Impedancia (kΩ)", "Estado"]

#: Cuál de ellas lleva el chip.
COLUMNA_DEL_ESTADO: Final[int] = 2

#: Qué dice el chip. **Son dos estados y no tres**: el módulo de impedancia
#: define un solo umbral y no una escala de semáforo, así que un «aceptable»
#: intermedio sería un criterio clínico que el programa no tiene.
PASA: Final[str] = "pasa"
SUPERA: Final[str] = "supera"


def _kohm(valor: float) -> str:
    """Un límite en kΩ, con la coma decimal del idioma del programa."""
    return f"{valor:g} kΩ".replace(".", ",")


class FixedColumnDelegate(QStyledItemDelegate):
    """Una columna que se ve y no se edita: la del nombre de cada fila.

    **`QTreeWidgetItem` no tiene permisos por columna**: marcar una fila
    editable deja editar todas sus celdas, también el nombre. Acá eso era un
    bug y no un detalle: `values()` usa el texto de la primera columna como
    nombre del canal, así que renombrar una fila asignaba la impedancia a un
    canal inexistente y dejaba el verdadero «sin medir». El panel de filtros lo
    usa por lo mismo, para la clase de canal (hito 31).
    """

    def createEditor(
        self,
        parent: QWidget,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QWidget | None:
        """Ningún editor: la celda no se puede cambiar."""
        return None


class ImpedancePanel(QWidget):
    """Tabla editable de impedancias por canal, y el informe."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ningún registro abierto."""
        super().__init__(parent)
        self._canales: list[str] = []
        #: Guard contra reentrada: rellenar la tabla dispara `itemChanged`, y
        #: sin esto cada carga se avisaría a sí misma como si el usuario
        #: hubiera escrito. Es el mismo patrón que `channel_selector.py`.
        self._reflejando = False
        #: A quién avisarle cuando el usuario edita un valor.
        self.on_changed: Callable[[], None] | None = None

        #: Contra qué límite se decide si una impedancia pasa. Es el mismo con
        #: el que `impedance_report()` arma el informe, así que la columna y el
        #: informe no se pueden contradecir.
        self._limite: float = DEFAULT_LIMIT_KOHM

        self.tabla = QTreeWidget()
        self.tabla.setHeaderLabels(COLUMNAS)
        self.tabla.setRootIsDecorated(False)
        self.tabla.setItemDelegateForColumn(0, FixedColumnDelegate(self.tabla))
        # **El estado tampoco se edita**: sale del valor, no se escribe.
        self.tabla.setItemDelegateForColumn(COLUMNA_DEL_ESTADO, ChipDelegate(self.tabla))
        self.tabla.itemChanged.connect(self._al_editar)

        #: El encabezado, con cuántos canales están medidos. Ver `PanelHeader`.
        self.header = PanelHeader("Impedancia")

        self.boton_archivo = QPushButton("Importar de un archivo…")
        self.boton_limpiar = QPushButton("Borrar todas")

        self.informe = QPlainTextEdit()
        self.informe.setReadOnly(True)

        botones = QHBoxLayout()
        botones.addWidget(self.boton_archivo)
        botones.addWidget(self.boton_limpiar)
        botones.addStretch()

        izquierda = QVBoxLayout()
        izquierda.addWidget(
            QLabel("Escribí el valor en la columna de la derecha, o importalo:")
        )
        izquierda.addWidget(self.tabla)
        izquierda.addLayout(botones)

        fila = QHBoxLayout()
        fila.setContentsMargins(8, 8, 8, 8)
        fila.addLayout(izquierda, stretch=1)
        fila.addWidget(self.informe, stretch=1)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self.header)
        columna.addLayout(fila)

    # -- Lo que le da la ventana principal ----------------------------------

    def set_channels(
        self, channel_names: list[str], impedances: dict[str, float] | None = None
    ) -> None:
        """Arma la tabla con los canales del registro.

        Args:
            channel_names: todos los canales, **en el orden del archivo**. No se
                ordenan alfabéticamente: el investigador los busca donde los vio
                en la pantalla de la señal.
            impedances: las que ya se conozcan. Los canales que no estén quedan
                marcados como sin medir.
        """
        self._canales = list(channel_names)
        medidas = dict(impedances or {})

        self._reflejando = True
        try:
            self.tabla.clear()
            for nombre in self._canales:
                valor = medidas.get(nombre)
                entrada = QTreeWidgetItem(
                    [nombre, self._texto(valor), self._estado(valor)]
                )
                entrada.setFlags(entrada.flags() | Qt.ItemFlag.ItemIsEditable)
                entrada.setData(
                    COLUMNA_DEL_ESTADO, ROL_DEL_COLOR, self._color_del_estado(valor)
                )
                self.tabla.addTopLevelItem(entrada)
        finally:
            self._reflejando = False
        self._reflejar_el_encabezado()

    def _estado(self, valor: float | None) -> str:
        """Qué dice el chip de un canal: si pasa el límite, o que no se midió.

        **Son dos estados y no tres.** El módulo de impedancia define un solo
        umbral —`channels_above_limit()`, inclusivo— y no una escala de
        semáforo: inventarle un «aceptable» acá sería un criterio clínico que
        el programa no tiene y que el informe no comparte.
        """
        if valor is None:
            return SIN_MEDIR
        return PASA if valor <= self._limite else SUPERA

    def _color_del_estado(self, valor: float | None) -> str | None:
        """El relleno del chip, o `None` para que no haya cápsula.

        Un canal sin medir se queda como texto: una cápsula gris parecería
        estar afirmando algo sobre una medición que no existe.
        """
        if valor is None:
            return None
        esquema = theme.current()
        return esquema.accent if valor <= self._limite else (esquema.danger or esquema.accent)

    def _reflejar_el_encabezado(self) -> None:
        """Cuántos canales están medidos, que es lo primero que se pregunta."""
        medidos = len(self.values())
        self.header.set_caption(f"{medidos} de {len(self._canales)} medidos")
        self.header.set_detail(f"límite {_kohm(self._limite)}")

    def set_report(self, text: str) -> None:
        """Muestra el informe que armó `analysis/impedance.py`."""
        self.informe.setPlainText(text)

    def clear_all(self) -> None:
        """Deja todos los canales sin medir, sin sacarlos de la tabla."""
        self.set_channels(self._canales, {})

    # -- Lo que se puede afirmar sin mirar ----------------------------------

    def channels(self) -> list[str]:
        """Los canales de la tabla, en orden."""
        return list(self._canales)

    def values(self) -> dict[str, float]:
        """Lo que hay cargado, en kΩ.

        **Los canales sin medir no aparecen**, igual que en
        `analysis.impedance.read_impedances()`: es el mismo contrato, y ponerlos
        en cero acá desharía todo el cuidado del módulo.

        Lo que el usuario escriba y no sea un número tampoco aparece: se
        descarta en silencio y la celda se corrige sola al recargar. Es una
        celda de texto, no un formulario, y elevar un error por cada tecla
        sería insufrible.
        """
        cargadas: dict[str, float] = {}
        for fila in range(self.tabla.topLevelItemCount()):
            entrada = self.tabla.topLevelItem(fila)
            texto = entrada.text(1).strip().replace(",", ".")
            if not texto or texto == SIN_MEDIR:
                continue
            try:
                valor = float(texto)
            except ValueError:
                continue
            if valor >= 0:
                cargadas[entrada.text(0)] = valor
        return cargadas

    def unmeasured(self) -> list[str]:
        """Qué canales quedaron sin medir.

        Se expone porque es **la distinción que sostiene el módulo**: hay que
        poder afirmar que un canal sin dato no se confunde con uno de 0 kΩ.
        """
        cargadas = self.values()
        return [nombre for nombre in self._canales if nombre not in cargadas]

    def displayed_value(self, channel_name: str) -> str:
        """Qué dice la celda de un canal, tal como se lee en pantalla."""
        for fila in range(self.tabla.topLevelItemCount()):
            entrada = self.tabla.topLevelItem(fila)
            if entrada.text(0) == channel_name:
                return entrada.text(1)
        return ""

    def displayed_state(self, channel_name: str) -> str:
        """Qué dice el chip de un canal, tal como se lee en pantalla."""
        for fila in range(self.tabla.topLevelItemCount()):
            entrada = self.tabla.topLevelItem(fila)
            if entrada.text(0) == channel_name:
                return entrada.text(COLUMNA_DEL_ESTADO)
        return ""

    def state_color(self, channel_name: str) -> str | None:
        """Con qué color se rellena ese chip, o `None` si no lleva cápsula.

        Se expone por la misma razón que `unmeasured()`: la distinción entre
        «no se midió» y «se midió y da algo» es la que sostiene el módulo, y
        acá se ve como la diferencia entre texto suelto y cápsula.
        """
        for fila in range(self.tabla.topLevelItemCount()):
            entrada = self.tabla.topLevelItem(fila)
            if entrada.text(0) == channel_name:
                return entrada.data(COLUMNA_DEL_ESTADO, ROL_DEL_COLOR)
        return None

    @property
    def report_text(self) -> str:
        """El informe que se está mostrando."""
        return self.informe.toPlainText()

    # -- Adentro -------------------------------------------------------------

    def _texto(self, valor: float | None) -> str:
        """Cómo se escribe un valor en la celda, con la coma del idioma."""
        if valor is None:
            return SIN_MEDIR
        return f"{valor:g}".replace(".", ",")

    def _al_editar(self, *_args: object) -> None:
        """El usuario escribió en una celda."""
        if self._reflejando:
            return
        self._refrescar_los_estados()
        if self.on_changed is not None:
            self.on_changed()

    def _refrescar_los_estados(self) -> None:
        """Vuelve a decidir el chip de cada fila con lo que hay escrito ahora.

        **Se rehacen todos y no sólo el editado**: el límite es uno solo, así
        que si alguna vez cambia, una fila con el chip viejo diría lo contrario
        que su vecina sin que nada fallara.
        """
        cargadas = self.values()
        self._reflejando = True
        try:
            for fila in range(self.tabla.topLevelItemCount()):
                entrada = self.tabla.topLevelItem(fila)
                valor = cargadas.get(entrada.text(0))
                entrada.setText(COLUMNA_DEL_ESTADO, self._estado(valor))
                entrada.setData(
                    COLUMNA_DEL_ESTADO, ROL_DEL_COLOR, self._color_del_estado(valor)
                )
        finally:
            self._reflejando = False
        self._reflejar_el_encabezado()
