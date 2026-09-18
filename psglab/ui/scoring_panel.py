"""Panel de scoring: elegir la fase de la ventana actual y marcar arousal.

Los botones se generan a partir de la nomenclatura activa, no están escritos
a mano: cambiar de Rechtschaffen y Kales a AASM reemplaza los botones solo
(V3_F). Eso evita que las dos nomenclaturas se desincronicen con el tiempo.

**El panel se puede angostar.** Con los anchos que Qt les da por omisión, el
combo y los siete botones de Rechtschaffen y Kales no bajaban de 868 px, y
al abrirlo junto al hipnograma le dejaban a éste unos 230: la curva de la
noche no se leía. Cada control tiene ahora un mínimo propio, chico, y crece
si hay lugar. El selector muestra la abreviatura de la nomenclatura, que es
como se la nombra en el laboratorio, y el nombre completo en el tooltip.

**Y va en tres filas, no en una.** Arriba el selector y el arousal, en el medio
las fases y abajo el pie con la ventana y su fase. En una sola fila el mínimo
era la suma de todo —464 px con Rechtschaffen y Kales—, y eso era más que lo
que la proporción de `docks.ANCHOS_DE_ABAJO` le pedía: el scoring se quedaba
siempre en su mínimo y el hipnograma pagaba la diferencia. Apilado, el mínimo
es el de la fila más ancha, que es la de las fases.

**El pie repite la ventana a propósito.** La barra de navegación y la de estado
ya la dicen, pero el panel se puede sacar a otra pantalla, y ahí no se ve
ninguna de las dos. Además es la fase en texto, que un lector de pantalla lee
y un botón marcado no siempre comunica.

Cubre del pliego: V1_F, V2_F, V3_F de "Scoring de la señal".
"""

from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from psglab.core.nomenclature import Nomenclature, SleepStage, stage_label, stages_of

#: Hasta dónde se achica un botón de fase. Alcanza para «REM», la etiqueta
#: más larga, con el margen del estilo.
ANCHO_MINIMO_DE_BOTON: Final[int] = 40

#: Hasta dónde se achica el selector de nomenclatura. Alcanza para «AASM».
ANCHO_MINIMO_DEL_SELECTOR: Final[int] = 72

#: Cómo se muestra cada nomenclatura en el selector. «Rechtschaffen y Kales»
#: entero hacía que el selector solo ocupara 160 px. Una nomenclatura que no
#: esté acá se muestra con su nombre completo, que es largo pero correcto.
ABREVIATURAS: Final[dict[Nomenclature, str]] = {
    Nomenclature.RK: "R&K",
    Nomenclature.AASM: "AASM",
}

#: Lo que dice el pie antes de que haya un registro abierto. Es lo mismo que
#: dice la barra de navegación en ese momento.
PIE_SIN_REGISTRO: Final[str] = "Sin registro"


def status_text(window_index: int, stage: SleepStage, arousal: bool) -> str:
    """El pie del panel: la ventana, su fase y el arousal si lo hay.

    La ventana va en base 1, como en la barra de estado y en los archivos de
    salida. Una ventana sin scorear dice «sin scorear» y no el «-» con que se
    guarda: en un texto suelto, un guion no se lee como nada.

    Args:
        window_index: la ventana actual, en base 0.
        stage: su fase, `SleepStage.UNSCORED` si todavía no se scoreó.
        arousal: si la ventana tiene arousal marcado.
    """
    fase = "sin scorear" if stage is SleepStage.UNSCORED else stage_label(stage)
    texto = f"Ventana {window_index + 1} · {fase}"
    return f"{texto} · arousal" if arousal else texto


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
        self._nomenclaturas.setMinimumWidth(ANCHO_MINIMO_DEL_SELECTOR)
        for posicion, nomenclatura in enumerate(Nomenclature):
            self._nomenclaturas.addItem(
                ABREVIATURAS.get(nomenclatura, nomenclatura.value), nomenclatura
            )
            self._nomenclaturas.setItemData(
                posicion, nomenclatura.value, Qt.ItemDataRole.ToolTipRole
            )
        self._nomenclaturas.currentIndexChanged.connect(self._on_nomenclature)

        self._arousal = QCheckBox("Arousal")
        self._arousal.toggled.connect(self._on_arousal)

        # **El pie parte las palabras** en vez de exigir su ancho entero: con
        # AASM la fila de las fases es la más angosta, y «Ventana 2650 · sin
        # scorear · arousal» en una sola línea pasaba a ser el mínimo del panel.
        self._pie = QLabel(PIE_SIN_REGISTRO)
        self._pie.setWordWrap(True)
        self._pie.setAccessibleName("Ventana actual y su fase")

        self._columna = QVBoxLayout(self)
        # Los márgenes de fábrica son 11 px por lado: en un panel que se
        # quiere angosto, son dos botones.
        self._columna.setContentsMargins(4, 2, 4, 2)
        self._columna.setSpacing(4)

        self._controles = QHBoxLayout()
        self._controles.setSpacing(4)
        self._controles.addWidget(self._nomenclaturas)
        self._controles.addStretch(1)
        self._controles.addWidget(self._arousal)

        #: La fila de las fases. Sin espaciador: los botones se reparten lo que
        #: sobra, y un botón más ancho es más fácil de acertar.
        self._fila = QHBoxLayout()
        self._fila.setSpacing(4)

        self._columna.addLayout(self._controles)
        self._columna.addLayout(self._fila)
        self._columna.addWidget(self._pie)
        self._columna.addStretch(1)

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

    def status(self) -> str:
        """Lo que dice el pie ahora."""
        return self._pie.text()

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
            # `deleteLater()` espera al ciclo de eventos, y dentro de un diálogo
            # modal puede no llegar: sin ocultarlo, el botón viejo queda
            # dibujado debajo del nuevo.
            boton.hide()
            boton.deleteLater()
        self._botones.clear()

        for fase in stages_of(nomenclature):
            boton = QPushButton(stage_label(fase))
            boton.setCheckable(True)
            # Un mínimo explícito es lo que le gana al de Qt, que en Windows
            # es de 75 px por botón aunque diga «W».
            boton.setMinimumWidth(ANCHO_MINIMO_DE_BOTON)
            boton.clicked.connect(lambda _=False, f=fase: self._on_stage(f))
            self._grupo.addButton(boton)
            self._fila.addWidget(boton)
            self._botones[fase] = boton

        self._reflejando = True
        self._nomenclaturas.setCurrentIndex(self._nomenclaturas.findData(nomenclature))
        self._reflejando = False
        self._nomenclaturas.setToolTip(f"Nomenclatura: {nomenclature.value}")

    def set_current(self, stage: SleepStage, arousal: bool, window_index: int) -> None:
        """Refleja el scoring de la ventana actual en los botones y en el pie.

        Se llama al navegar, para que el usuario vea de inmediato en qué fase
        está la ventana a la que llegó.

        Reflejar **no es elegir**: mientras dura, los controles no emiten. Si lo
        hicieran, navegar a una ventana ya scoreada la volvería a scorear, y
        llegar a una sin scorear borraría lo que hubiera.

        Args:
            stage: la fase de la ventana actual.
            arousal: si tiene arousal marcado.
            window_index: cuál es, en base 0; el pie la muestra en base 1.
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
        self._pie.setText(status_text(window_index, stage, arousal))
