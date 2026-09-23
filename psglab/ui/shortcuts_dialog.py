"""La ayuda de atajos de teclado, en una tabla agrupada.

**Era un `QMessageBox` con texto plano** hasta el hito 54: las columnas se
alineaban rellenando con espacios, y en la letra proporcional del cartel la
tecla y lo que hace quedaban corridas en cada línea. El prototipo la dibujaba
como una tabla con grupos —navegación, scoring, visualización, archivo— y la
tecla en la letra de las lecturas, y eso es lo que arma este módulo.

Qué atajos hay y en qué grupo va cada uno no se decide acá: lo dice
`shortcuts.shortcut_groups()`, que es la fuente única de verdad de las teclas.

Cubre del pliego: ningún ID. Es la ayuda de los atajos, que no pide el pliego.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psglab.core.nomenclature import Nomenclature
from psglab.ui.fonts import font_for
from psglab.ui.shortcuts import shortcut_groups


class ShortcutsDialog(QDialog):
    """Los atajos de teclado, agrupados, en dos columnas: qué hace y la tecla."""

    def __init__(self, nomenclature: Nomenclature, parent: QWidget | None = None) -> None:
        """Arma la tabla con los atajos de la nomenclatura activa."""
        super().__init__(parent)
        self.setWindowTitle("Atajos de teclado")

        self.tabla = QTableWidget(0, 2)
        self.tabla.horizontalHeader().hide()
        self.tabla.verticalHeader().hide()
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tabla.setShowGrid(False)
        self.tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )

        self._filas: list[tuple[str | None, str, str]] = []
        rotulo = font_for("rotulo", self.font())
        tecla = font_for("lectura", self.font())
        for grupo, atajos in shortcut_groups(nomenclature):
            # **El rótulo del grupo en mayúsculas escritas**, como el de los
            # paneles: la hoja de estilo de Qt no sabe hacer `text-transform`.
            fila = self._agregar_fila()
            titulo = QTableWidgetItem(grupo.upper())
            titulo.setFont(rotulo)
            self.tabla.setItem(fila, 0, titulo)
            self.tabla.setSpan(fila, 0, 1, 2)
            for combinacion, accion in atajos:
                fila = self._agregar_fila()
                self.tabla.setItem(fila, 0, QTableWidgetItem(accion))
                celda = QTableWidgetItem(combinacion)
                celda.setFont(tecla)
                self.tabla.setItem(fila, 1, celda)
                self._filas.append((grupo, accion, combinacion))

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botones.rejected.connect(self.reject)

        columna = QVBoxLayout(self)
        columna.addWidget(self.tabla)
        columna.addWidget(botones)
        self.resize(460, 520)

    def _agregar_fila(self) -> int:
        fila = self.tabla.rowCount()
        self.tabla.insertRow(fila)
        return fila

    def rows(self) -> list[tuple[str | None, str, str]]:
        """Cada atajo como (grupo, qué hace, tecla), en el orden de la tabla.

        Es lo que se puede afirmar sin mirar la pantalla.
        """
        return list(self._filas)
