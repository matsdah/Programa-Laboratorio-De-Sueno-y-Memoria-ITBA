"""Selector de los canales que se muestran.

El usuario elige cuántos y cuáles canales ver. Cada fila lleva el nombre del
canal y un chip con su clase detectada, que es lo que el pliego pide mostrar
junto al nombre (V4_F).

## Por qué es una lista y no un árbol

**Era un árbol agrupado por clase**, y los nodos de primer nivel servían de
atajo para mostrar u ocultar todo el EOG de una vez. Funcionaba, pero costaba
dos renglones por clase y una sangría en una lista que ya es angosta, y el
nombre de la clase aparecía una vez por grupo en vez de una vez por canal:
mirando un canal suelto había que subir la vista hasta su encabezado para saber
de qué clase era.

**El atajo por clase no se perdió**: está en el pie del panel, un botón por
clase presente en el registro, y es lo que sigue cubriendo "si quiero o no
visualizar los canales de EOG, EMG" (V3_P).

Cubre del pliego: V3_P, V4_F de "Visualización de la señal"; alimenta la
selección de canales de V5_F (cambio de amplitud por canal).
"""

from typing import Final

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from psglab.core.recording import ChannelKind, Recording
from psglab.ui import theme

#: Cuánto respira el texto del chip dentro de su cápsula, a cada lado.
_PADDING_DEL_CHIP: Final[int] = 5

#: El radio de la cápsula y cuánto la separa del borde derecho de la fila.
_RADIO_DEL_CHIP: Final[int] = 4
_MARGEN_DEL_CHIP: Final[int] = 6

#: Cuánto más chica es la letra del chip que la de la fila, en puntos.
_PUNTOS_MENOS: Final[int] = 2

#: El alto de una fila. Es el del diseño, y da lugar a la cápsula sin que el
#: panel se vuelva una lista de botones.
ALTO_DE_FILA: Final[int] = 26

#: Cuántos atajos entran por fila en el pie, y hasta dónde se achica cada
#: uno. Tres por fila es lo que hace que el mínimo del pie no le gane al de la
#: lista con las seis clases que el programa reconoce.
ATAJOS_POR_FILA: Final[int] = 3
ANCHO_MINIMO_DEL_ATAJO: Final[int] = 46

#: Qué dato de la fila lleva la clase del canal, para que el delegado la lea
#: sin tener que volver a buscar el canal en el registro.
ROL_DE_LA_CLASE: Final[int] = int(Qt.ItemDataRole.UserRole) + 1


def color_de_la_clase(kind: ChannelKind) -> str:
    """El color del chip de una clase, sacado de la paleta del esquema.

    **Por posición en `ChannelKind` y no por una tabla propia**: una tabla sería
    un juego de colores más que mantener en los dos esquemas y verificar contra
    WCAG por separado. La paleta ya está verificada, y el chip la usa de
    relleno, que es como está medida —3,0 contra el fondo, por ser un gráfico—.
    La tinta del texto la elige `theme.ink_over()` midiendo contra ese relleno.
    """
    posicion = list(ChannelKind).index(kind)
    return theme.current().color_for_channel(posicion)


class _DelegadoDelChip(QStyledItemDelegate):
    """Dibuja la cápsula con la clase, a la derecha de cada fila."""

    def _fuente_del_chip(self, base: QFont) -> QFont:
        """La del chip: la de la fila, dos puntos más chica."""
        chica = QFont(base)
        if base.pointSize() > 0:
            chica.setPointSize(max(6, base.pointSize() - _PUNTOS_MENOS))
        return chica

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: object
    ) -> None:
        """La fila como cualquier otra, y encima el chip a la derecha."""
        clase = index.data(ROL_DE_LA_CLASE)
        if not clase:
            super().paint(painter, option, index)
            return

        fuente = self._fuente_del_chip(option.font)
        ancho = QFontMetrics(fuente).horizontalAdvance(clase) + 2 * _PADDING_DEL_CHIP

        # **El nombre se dibuja en lo que queda**, no debajo del chip: sin
        # esto, un canal de nombre largo se metía por atrás de la cápsula.
        recortada = QStyleOptionViewItem(option)
        recortada.rect = option.rect.adjusted(
            0, 0, -(ancho + 2 * _MARGEN_DEL_CHIP), 0
        )
        super().paint(painter, recortada, index)

        relleno = QColor(color_de_la_clase(ChannelKind(clase)))
        caja = QRectF(
            option.rect.right() - ancho - _MARGEN_DEL_CHIP,
            option.rect.center().y() - QFontMetrics(fuente).height() / 2.0,
            float(ancho),
            float(QFontMetrics(fuente).height()),
        )
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(relleno)
        painter.drawRoundedRect(caja, _RADIO_DEL_CHIP, _RADIO_DEL_CHIP)
        painter.setFont(fuente)
        painter.setPen(QColor(theme.ink_over(theme.current(), relleno.name())))
        painter.drawText(caja, int(Qt.AlignmentFlag.AlignCenter), clase)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: object) -> QSize:
        """Un alto fijo: el chip necesita lugar y las filas quedan parejas."""
        medida = super().sizeHint(option, index)
        return QSize(medida.width(), max(medida.height(), ALTO_DE_FILA))


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
        self._clases: dict[str, ChannelKind] = {}
        self._atajos: dict[ChannelKind, QPushButton] = {}

        self._lista = QListWidget()
        self._lista.setItemDelegate(_DelegadoDelChip(self._lista))
        self._lista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._lista.setUniformItemSizes(True)
        self._lista.itemChanged.connect(self._on_item_changed)
        self._lista.itemSelectionChanged.connect(self._on_selection_changed)

        self._todos = QPushButton("Mostrar todo")
        self._todos.clicked.connect(self._mostrar_todo)

        #: El pie con los atajos por clase. Ver el docstring del módulo: es lo
        #: que reemplaza a los nodos de grupo del árbol.
        #:
        #: **En una grilla que dobla y no en una fila.** En una sola fila el
        #: mínimo del pie era la suma de todos los botones, y con eso el panel
        #: abría en 327 px en vez de los 212 del diseño: el ancho lo decidía el
        #: pie y no la lista de canales. Con siete clases sería peor.
        self._pie = QGridLayout()
        self._pie.setSpacing(4)
        self._pie.setContentsMargins(0, 0, 0, 0)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(4, 4, 4, 4)
        caja.setSpacing(4)
        caja.addWidget(self._lista)
        caja.addWidget(self._todos)
        caja.addLayout(self._pie)

    # -- Lo que pasa cuando el usuario toca algo ----------------------------

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        if self._reflejando:
            return
        self._reflejar_los_atajos()
        self.visible_changed.emit(self.visible_channels())

    def _on_selection_changed(self) -> None:
        if self._reflejando:
            return
        self.selection_changed.emit(self.selected_channels())

    def _mostrar_todo(self) -> None:
        """Vuelve a mostrar todos los canales del registro."""
        self.set_visible(list(self._orden))
        self._reflejar_los_atajos()
        self.visible_changed.emit(self.visible_channels())

    def _on_atajo(self, kind: ChannelKind) -> None:
        """Muestra u oculta una clase entera desde su botón del pie."""
        self.toggle_kind(kind, self._atajos[kind].isChecked())

    # -- Cargar el registro -------------------------------------------------

    def set_recording(self, recording: Recording) -> None:
        """Carga la lista de canales del registro, cada uno con su clase.

        El orden de presentación es el del archivo, no alfabético ni por clase:
        es el que el equipo grabó, el que el investigador reconoce y el mismo
        con el que el visualizador los apila.
        """
        self._reflejando = True
        try:
            self._lista.clear()
            self._orden = recording.channel_names()
            self._clases = {canal.name: canal.kind for canal in recording.channels}

            for canal in recording.channels:
                fila = QListWidgetItem(canal.name, self._lista)
                fila.setFlags(fila.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                fila.setCheckState(Qt.CheckState.Checked)
                fila.setData(ROL_DE_LA_CLASE, canal.kind.value)
                fila.setToolTip(f"{canal.name} · {canal.kind.value}")
            self._armar_los_atajos(recording)
        finally:
            self._reflejando = False

    def _armar_los_atajos(self, recording: Recording) -> None:
        """Un botón por clase presente, en el orden en que aparecen.

        **Sólo las presentes.** Un botón «ECG» en un registro sin ECG sería un
        control que no hace nada, que es lo mismo que la ventana de
        configuración evita con sus solapas.
        """
        for boton in self._atajos.values():
            self._pie.removeWidget(boton)
            boton.hide()
            boton.deleteLater()
        self._atajos.clear()

        for clase in ChannelKind:
            if not any(canal.kind is clase for canal in recording.channels):
                continue
            boton = QPushButton(clase.value)
            boton.setCheckable(True)
            boton.setChecked(True)
            boton.setMinimumWidth(ANCHO_MINIMO_DEL_ATAJO)
            boton.setToolTip(f"Mostrar u ocultar los canales de {clase.value}")
            boton.clicked.connect(lambda _=False, c=clase: self._on_atajo(c))
            posicion = len(self._atajos)
            self._pie.addWidget(
                boton, posicion // ATAJOS_POR_FILA, posicion % ATAJOS_POR_FILA
            )
            self._atajos[clase] = boton

    # -- Reflejar lo que decidió otro ---------------------------------------

    def set_visible(self, channel_names: list[str]) -> None:
        """Marca qué canales están visibles."""
        visibles = set(channel_names)
        self._reflejando = True
        try:
            for fila in self._filas():
                fila.setCheckState(
                    Qt.CheckState.Checked
                    if fila.text() in visibles
                    else Qt.CheckState.Unchecked
                )
        finally:
            self._reflejando = False
        self._reflejar_los_atajos()

    def _reflejar_los_atajos(self) -> None:
        """Deja cada botón del pie marcado si toda su clase se está viendo.

        Destildar un canal a mano tiene que apagar el botón de su clase: si no,
        el botón diría que la clase se ve entera y el siguiente clic la
        ocultaría en vez de completarla.
        """
        visibles = set(self.visible_channels())
        for clase, boton in self._atajos.items():
            de_la_clase = [n for n, k in self._clases.items() if k is clase]
            boton.setChecked(bool(de_la_clase) and visibles.issuperset(de_la_clase))

    def toggle_kind(self, kind: ChannelKind, visible: bool) -> None:
        """Muestra u oculta todos los canales de una clase de una vez.

        Es el atajo que pide el pliego para decidir "si quiero o no visualizar
        los canales de EOG, EMG" sin marcarlos uno por uno.
        """
        estado = Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
        self._reflejando = True
        try:
            for fila in self._filas():
                if self._clases.get(fila.text()) is kind:
                    fila.setCheckState(estado)
        finally:
            self._reflejando = False
        self._reflejar_los_atajos()
        self.visible_changed.emit(self.visible_channels())

    # -- Lo que el panel sabe -----------------------------------------------

    def _filas(self) -> list[QListWidgetItem]:
        """Todas las filas, que son los canales del registro."""
        return [self._lista.item(i) for i in range(self._lista.count())]

    def visible_channels(self) -> list[str]:
        """Canales marcados como visibles, en orden de presentación."""
        marcados = {
            fila.text()
            for fila in self._filas()
            if fila.checkState() == Qt.CheckState.Checked
        }
        return [nombre for nombre in self._orden if nombre in marcados]

    def selected_channels(self) -> list[str]:
        """Canales seleccionados para aplicarles cambios de amplitud.

        La selección es un eje **independiente** de la visibilidad: `Session` no
        exige que lo seleccionado esté visible, y el pliego tampoco los ata.
        """
        seleccionados = {fila.text() for fila in self._lista.selectedItems()}
        return [nombre for nombre in self._orden if nombre in seleccionados]
