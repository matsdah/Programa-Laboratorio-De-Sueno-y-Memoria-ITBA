"""Selector de los canales que se muestran.

El usuario elige cuántos y cuáles canales ver, agrupados por clase para que
la lista siga siendo manejable en registros con muchos electrodos: en un
montaje de alta densidad, una lista plana de 64 canales es inusable.

Cubre del pliego: V3_P, V4_F de "Visualización de la señal"; alimenta la
selección de canales de V5_F (cambio de amplitud por canal).
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

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
        raise NotImplementedError("Pendiente: construir el panel del selector.")

    def set_recording(self, recording: Recording) -> None:
        """Carga la lista de canales del registro, agrupados por clase."""
        raise NotImplementedError("Pendiente: poblar la lista agrupada por clase.")

    def set_visible(self, channel_names: list[str]) -> None:
        """Marca qué canales están visibles."""
        raise NotImplementedError("Pendiente: actualizar las marcas de visibilidad.")

    def toggle_kind(self, kind: ChannelKind, visible: bool) -> None:
        """Muestra u oculta todos los canales de una clase de una vez.

        Es el atajo que pide el pliego para decidir "si quiero o no visualizar
        los canales de EOG, EMG" sin marcarlos uno por uno.
        """
        raise NotImplementedError("Pendiente: cambiar la visibilidad de la clase completa.")

    def visible_channels(self) -> list[str]:
        """Canales marcados como visibles, en orden de presentación."""
        raise NotImplementedError("Pendiente: devolver los canales visibles.")

    def selected_channels(self) -> list[str]:
        """Canales seleccionados para aplicarles cambios de amplitud."""
        raise NotImplementedError("Pendiente: devolver los canales seleccionados.")
