"""Panel de impedancias: la tabla editable y el informe.

Es donde viven **las tres vías** que plantea `analysis/impedance.py`. Dos de
ellas llegan de afuera —del archivo abierto y de un archivo aparte— y la
tercera es este panel: `analysis/` no conoce Qt, así que cargar valores a mano
sólo puede vivir acá.

**El estado "sin medir" se muestra distinto de "0 kΩ", y es la razón de ser de
todo el módulo.** Un electrodo suelto que nadie midió es el caso peligroso: si
apareciera como cero pasaría por perfecto, porque cero es el mejor valor
posible. La celda vacía dice "sin medir" con todas las letras.

Como los demás paneles, lo que se puede afirmar sin mirar una pantalla está
separado del dibujo.

Cubre del pliego: ningún ID propio. Es la mitad que se ve de V1_F de
"Impedancia de los electrodos".
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

#: Lo que dice una celda sin valor. **No es "0" ni está vacía**: un cero
#: pasaría por el mejor valor posible y una celda vacía se lee como un olvido
#: de la pantalla, no del electrodo.
SIN_MEDIR: str = "sin medir"


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

        self.tabla = QTreeWidget()
        self.tabla.setHeaderLabels(["Canal", "Impedancia (kΩ)"])
        self.tabla.setRootIsDecorated(False)
        self.tabla.itemChanged.connect(self._al_editar)

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

        fila = QHBoxLayout(self)
        fila.addLayout(izquierda, stretch=1)
        fila.addWidget(self.informe, stretch=1)

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
                entrada = QTreeWidgetItem(
                    [nombre, self._texto(medidas.get(nombre))]
                )
                entrada.setFlags(entrada.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabla.addTopLevelItem(entrada)
        finally:
            self._reflejando = False

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
        if self._reflejando or self.on_changed is None:
            return
        self.on_changed()
