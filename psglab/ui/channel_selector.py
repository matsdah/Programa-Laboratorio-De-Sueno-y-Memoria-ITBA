"""Selector de los canales que se muestran.

El usuario elige cuántos y cuáles canales ver, agrupados por clase para que
la lista siga siendo manejable en registros con muchos electrodos: en un
montaje de alta densidad, una lista plana de 64 canales es inusable.

Cubre del pliego: V3_P, V4_F de "Visualización de la señal"; alimenta la
selección de canales de V5_F (cambio de amplitud por canal).
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from psglab.core.recording import ChannelKind, Recording


class ChannelSelector(QWidget):
    """Panel para elegir los canales visibles y los seleccionados."""

    #: Cambió la lista de canales que se muestran.
    visible_changed = Signal(list)

    #: Cambió la lista de canales seleccionados (los que reciben los cambios
    #: de amplitud cuando hay una selección activa).
    selection_changed = Signal(list)

    def __init__(self) -> None:
        """Crea el panel vacío, sin registro cargado."""
        super().__init__()
        self._reflejando = False
        self._orden: list[str] = []

        self._arbol = QTreeWidget()
        self._arbol.setHeaderLabels(["Canal"])
        self._arbol.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._arbol.itemChanged.connect(self._on_item_changed)
        self._arbol.itemSelectionChanged.connect(self._on_selection_changed)

        caja = QVBoxLayout(self)
        caja.addWidget(self._arbol)

    def _items_de_canal(self) -> list[QTreeWidgetItem]:
        """Todas las hojas del árbol, que son los canales.

        Los nodos de primer nivel son las clases y no representan un canal: son
        el atajo para mostrar u ocultar EOG o EMG de una vez.
        """
        hojas = []
        for indice in range(self._arbol.topLevelItemCount()):
            grupo = self._arbol.topLevelItem(indice)
            hojas += [grupo.child(i) for i in range(grupo.childCount())]
        return hojas

    def _on_item_changed(self, item: QTreeWidgetItem, _columna: int) -> None:
        if self._reflejando:
            return
        if item.parent() is None:
            self._reflejando = True
            for indice in range(item.childCount()):
                item.child(indice).setCheckState(0, item.checkState(0))
            self._reflejando = False
        self.visible_changed.emit(self.visible_channels())

    def _on_selection_changed(self) -> None:
        if self._reflejando:
            return
        self.selection_changed.emit(self.selected_channels())

    def set_recording(self, recording: Recording) -> None:
        """Carga la lista de canales del registro, agrupados por clase.

        El orden de presentación es el del archivo, no alfabético: es el que el
        equipo grabó y el que el investigador reconoce.
        """
        self._reflejando = True
        try:
            self._arbol.clear()
            self._orden = registro_en_orden = recording.channel_names()

            for clase in ChannelKind:
                canales = [c for c in recording.channels if c.kind is clase]
                if not canales:
                    continue
                grupo = QTreeWidgetItem(self._arbol, [clase.value])
                grupo.setFlags(grupo.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                grupo.setCheckState(0, Qt.CheckState.Checked)
                for canal in canales:
                    hoja = QTreeWidgetItem(grupo, [canal.name])
                    hoja.setFlags(hoja.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    hoja.setCheckState(0, Qt.CheckState.Checked)
            self._arbol.expandAll()
            assert registro_en_orden is not None
        finally:
            self._reflejando = False

    def set_visible(self, channel_names: list[str]) -> None:
        """Marca qué canales están visibles."""
        visibles = set(channel_names)
        self._reflejando = True
        try:
            for hoja in self._items_de_canal():
                marcado = (
                    Qt.CheckState.Checked
                    if hoja.text(0) in visibles
                    else Qt.CheckState.Unchecked
                )
                hoja.setCheckState(0, marcado)
        finally:
            self._reflejando = False

    def toggle_kind(self, kind: ChannelKind, visible: bool) -> None:
        """Muestra u oculta todos los canales de una clase de una vez.

        Es el atajo que pide el pliego para decidir "si quiero o no visualizar
        los canales de EOG, EMG" sin marcarlos uno por uno.
        """
        estado = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
        for indice in range(self._arbol.topLevelItemCount()):
            grupo = self._arbol.topLevelItem(indice)
            if grupo.text(0) != kind.value:
                continue
            grupo.setCheckState(0, estado)
            return

    def visible_channels(self) -> list[str]:
        """Canales marcados como visibles, en orden de presentación.

        Se devuelven en el orden del archivo y no en el del árbol: el árbol los
        agrupa por clase, y el visualizador los apila de arriba abajo como
        estaban grabados.
        """
        marcados = {
            hoja.text(0)
            for hoja in self._items_de_canal()
            if hoja.checkState(0) == Qt.CheckState.Checked
        }
        return [nombre for nombre in self._orden if nombre in marcados]

    def selected_channels(self) -> list[str]:
        """Canales seleccionados para aplicarles cambios de amplitud.

        La selección es la del árbol, y es un eje **independiente** de la
        visibilidad: `Session` no exige que lo seleccionado esté visible, y el
        pliego tampoco los ata.
        """
        seleccionados = {
            item.text(0) for item in self._arbol.selectedItems() if item.parent() is not None
        }
        return [nombre for nombre in self._orden if nombre in seleccionados]
