"""Panel de scoring: elegir la fase de la ventana actual y marcar arousal.

Los botones se generan a partir de la nomenclatura activa, no están escritos
a mano: cambiar de Rechtschaffen y Kales a AASM reemplaza los botones solo
(V3_F). Eso evita que las dos nomenclaturas se desincronicen con el tiempo.

Cubre del pliego: V1_F, V2_F, V3_F de "Scoring de la señal".
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from psglab.core.nomenclature import Nomenclature, SleepStage


class ScoringPanel(QWidget):
    """Botones de fase de sueño y de arousal."""

    #: El usuario eligió una fase para la ventana actual.
    stage_selected = Signal(object)  # SleepStage

    #: El usuario marcó o desmarcó el arousal de la ventana actual.
    arousal_toggled = Signal(bool)

    #: El usuario cambió de nomenclatura.
    nomenclature_changed = Signal(object)  # Nomenclature

    def __init__(self) -> None:
        """Crea el panel con la nomenclatura por defecto."""
        raise NotImplementedError("Pendiente: construir el panel de scoring.")

    def set_nomenclature(self, nomenclature: Nomenclature) -> None:
        """Reconstruye los botones para la nomenclatura elegida (V3_F).

        Antes de aplicar el cambio sobre un registro ya scoreado hay que
        avisarle al usuario: la conversión entre nomenclaturas pierde
        información (ver `psglab.core.nomenclature.convert`).
        """
        raise NotImplementedError("Pendiente: regenerar los botones de fase.")

    def set_current(self, stage: SleepStage, arousal: bool) -> None:
        """Refleja el scoring de la ventana actual en los botones.

        Se llama al navegar, para que el usuario vea de inmediato en qué fase
        está la ventana a la que llegó.
        """
        raise NotImplementedError("Pendiente: marcar la fase y el arousal actuales.")
