"""Panel de scoring: elegir la fase de la ventana actual y marcar arousal.

Los botones se generan a partir de la nomenclatura activa, no están escritos
a mano: cambiar de Rechtschaffen y Kales a AASM reemplaza los botones solo
(V3_F). Eso evita que las dos nomenclaturas se desincronicen con el tiempo.

Cubre del pliego: V1_F, V2_F, V3_F de "Scoring de la señal".
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from psglab.core.nomenclature import Nomenclature, SleepStage, stage_label, stages_of


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
        super().__init__()
        #: Mientras está en True, los cambios de estado de los controles vienen
        #: del programa y no del usuario, así que **no se re-emiten**. Sin esto,
        #: reflejar la ventana a la que se acaba de navegar dispararía un
        #: "el usuario eligió esta fase" y volvería a scorearla.
        self._reflejando = False

        self._botones: dict[SleepStage, QPushButton] = {}
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)

        self._nomenclaturas = QComboBox()
        for nomenclatura in Nomenclature:
            self._nomenclaturas.addItem(nomenclatura.value, nomenclatura)
        self._nomenclaturas.currentIndexChanged.connect(self._on_nomenclature)

        self._arousal = QCheckBox("Arousal")
        self._arousal.toggled.connect(self._on_arousal)

        self._fila = QHBoxLayout(self)
        self._fila.addWidget(self._nomenclaturas)
        self._fila.addStretch(1)
        self._fila.addWidget(self._arousal)

        self.set_nomenclature(Nomenclature.AASM)

    def _on_nomenclature(self) -> None:
        if self._reflejando:
            return
        self.nomenclature_changed.emit(self._nomenclaturas.currentData())

    def _on_arousal(self, marcado: bool) -> None:
        if self._reflejando:
            return
        self.arousal_toggled.emit(marcado)

    def _on_stage(self, stage: SleepStage) -> None:
        if self._reflejando:
            return
        self.stage_selected.emit(stage)

    def set_nomenclature(self, nomenclature: Nomenclature) -> None:
        """Reconstruye los botones para la nomenclatura elegida (V3_F).

        Antes de aplicar el cambio sobre un registro ya scoreado hay que
        avisarle al usuario: la conversión entre nomenclaturas pierde
        información (ver `psglab.core.nomenclature.convert`).

        **El aviso no se da acá.** Este panel emite `nomenclature_changed` y la
        ventana principal decide si pregunta: el panel no conoce el scoring ni
        sabe si hay ventanas ya marcadas.

        Los botones salen de `stages_of()`, no de una lista a mano: es lo mismo
        que hacen los atajos de teclado, y por el mismo motivo.
        """
        for boton in self._botones.values():
            self._grupo.removeButton(boton)
            self._fila.removeWidget(boton)
            boton.deleteLater()
        self._botones.clear()

        for posicion, fase in enumerate(stages_of(nomenclature)):
            boton = QPushButton(stage_label(fase))
            boton.setCheckable(True)
            boton.clicked.connect(lambda _=False, f=fase: self._on_stage(f))
            self._grupo.addButton(boton)
            # Después del combo y antes del espaciador, que es el índice 1.
            self._fila.insertWidget(1 + posicion, boton)
            self._botones[fase] = boton

        self._reflejando = True
        self._nomenclaturas.setCurrentText(nomenclature.value)
        self._reflejando = False

    def set_current(self, stage: SleepStage, arousal: bool) -> None:
        """Refleja el scoring de la ventana actual en los botones.

        Se llama al navegar, para que el usuario vea de inmediato en qué fase
        está la ventana a la que llegó.

        Reflejar **no es elegir**: mientras dura, los controles no emiten. Si lo
        hicieran, navegar a una ventana ya scoreada la volvería a scorear, y
        llegar a una sin scorear borraría lo que hubiera.
        """
        self._reflejando = True
        try:
            self._grupo.setExclusive(False)
            for fase, boton in self._botones.items():
                boton.setChecked(fase is stage)
            self._grupo.setExclusive(True)
            self._arousal.setChecked(arousal)
        finally:
            self._reflejando = False
