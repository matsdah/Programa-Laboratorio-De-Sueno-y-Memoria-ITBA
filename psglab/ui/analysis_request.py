"""La fila con que se pide un análisis desde su propio panel.

Un análisis que necesita parámetros —el canal del espectro, la medida de la
complejidad, la banda de la conectividad— los lleva **en su panel**, arriba,
con un botón «Calcular». El menú abre el panel y calcula en el acto con lo que
ya está elegido, y el usuario cambia la elección y vuelve a calcular sin
cerrar nada.

La alternativa era un cartel modal por parámetro antes de abrir el panel: para
ver el espectro de otro canal había que volver al menú y contestar el cartel
otra vez, y la complejidad eran dos seguidos. Un cartel tapa además la señal,
que es justo lo que se quiere mirar al lado del resultado.

**No sabe qué calcula.** Tiene campos —una clave, un rótulo y sus opciones— y
avisa con `requested` cuando se aprieta «Calcular»; qué hacer con los valores
lo decide la ventana. Así el mismo widget sirve a los tres paneles, y el panel
de la métrica cambia de campos según lo que muestre: canal y medida para la
complejidad, banda para la conectividad de la noche.

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura de los
paneles de análisis, que sí tienen los suyos.
"""

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from psglab.utils.errors import PsgLabError

#: El texto del botón. Un solo verbo para los tres paneles.
CALCULAR = "Calcular"


class AnalysisRequest(QWidget):
    """Campos de elección y un botón «Calcular», en una fila."""

    #: Se aprieta «Calcular». Los valores se leen con `value()`.
    requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Arranca sin campos y con el botón apagado: no hay nada que pedir."""
        super().__init__(parent)
        self._fila = QHBoxLayout(self)
        self._fila.setContentsMargins(8, 4, 8, 4)
        self._fila.setSpacing(6)
        self._campos: dict[str, tuple[QLabel, QComboBox]] = {}
        self.boton = QPushButton(CALCULAR)
        self.boton.setEnabled(False)
        self.boton.clicked.connect(self.requested.emit)
        self._fila.addStretch(1)
        self._fila.addWidget(self.boton)

    def set_fields(self, fields: Sequence[tuple[str, str, Sequence[str], str | None]]) -> None:
        """Define los campos, como (clave, rótulo, opciones, preferida).

        **Lo que el usuario ya eligió se conserva** mientras siga entre las
        opciones: volver a pedir el espectro no le cambia el canal. Si no está,
        va la preferida —el canal seleccionado, por ejemplo— y si tampoco, la
        primera. Un campo sin opciones deja el botón apagado, porque no hay
        qué pedir.
        """
        # Del selector y no de `value()`: preparar los campos no es leer lo que
        # el usuario pidió.
        anteriores = {clave: selector.currentText() for clave, (_, selector) in self._campos.items()}
        claves = [clave for clave, *_ in fields]
        if claves != list(self._campos):
            for rotulo, selector in self._campos.values():
                self._fila.removeWidget(rotulo)
                self._fila.removeWidget(selector)
                rotulo.deleteLater()
                selector.deleteLater()
            self._campos = {}
            for posicion, (clave, texto, _opciones, _preferida) in enumerate(fields):
                rotulo = QLabel(texto)
                selector = QComboBox()
                selector.setAccessibleName(texto.rstrip(":"))
                rotulo.setBuddy(selector)
                self._fila.insertWidget(2 * posicion, rotulo)
                self._fila.insertWidget(2 * posicion + 1, selector)
                self._campos[clave] = (rotulo, selector)
        for clave, texto, opciones, preferida in fields:
            rotulo, selector = self._campos[clave]
            rotulo.setText(texto)
            opciones = list(opciones)
            elegida = next(
                (o for o in (anteriores.get(clave), preferida) if o in opciones),
                opciones[0] if opciones else None,
            )
            selector.blockSignals(True)
            selector.clear()
            selector.addItems(opciones)
            if elegida is not None:
                selector.setCurrentText(elegida)
            selector.blockSignals(False)
        self.boton.setEnabled(bool(self._campos) and all(
            selector.count() for _, selector in self._campos.values()
        ))

    def keys(self) -> list[str]:
        """Las claves de los campos, en el orden en que se muestran."""
        return list(self._campos)

    def options(self, key: str) -> list[str]:
        """Lo que se puede elegir en un campo.

        Raises:
            PsgLabError: si el campo no existe.
        """
        _, selector = self._campo(key)
        return [selector.itemText(i) for i in range(selector.count())]

    def value(self, key: str) -> str:
        """Lo elegido en un campo, o `""` si no tiene opciones.

        Raises:
            PsgLabError: si el campo no existe.
        """
        _, selector = self._campo(key)
        return selector.currentText()

    def set_value(self, key: str, value: str) -> None:
        """Elige una opción, como si el usuario la hubiera elegido.

        Raises:
            PsgLabError: si el campo no existe o la opción no está entre las
                suyas. Elegir algo que no se ofrece dejaría el campo como
                estaba sin decirlo.
        """
        _, selector = self._campo(key)
        if value not in self.options(key):
            raise PsgLabError(
                f"«{value}» no es una de las opciones que se pueden elegir.",
                details=f"campo {key!r}, opciones {self.options(key)}.",
            )
        selector.setCurrentText(value)

    def _campo(self, key: str) -> tuple[QLabel, QComboBox]:
        """El rótulo y el selector de un campo, o un error que dice cuáles hay."""
        if key not in self._campos:
            raise PsgLabError(
                "Se pidió un parámetro que este análisis no tiene.",
                details=f"campo {key!r}; hay {list(self._campos)}.",
            )
        return self._campos[key]
