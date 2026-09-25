"""Panel de filtros: una fila por clase de canal, con sus tres cortes.

**Se ofrece por clase de canal y no por canal**, porque es lo que pide V1_F y
porque es lo que un investigador quiere: en un montaje de veinte canales, poner
el mismo pasa-bajos veinte veces es una invitación a equivocarse en uno solo y
no notarlo. El reparto de la clase a sus canales lo hace
`analysis.filters.settings_for_kinds()`, que es donde va la regla.

**La celda vacía desactiva el filtro**, y es la única forma de desactivarlo: el
cero está rechazado río abajo justamente para que no haya dos maneras de
escribir lo mismo, una de las cuales MNE interpreta como "sin filtro".

Sólo aparecen las clases que el registro tiene. Ofrecer una fila de ECG en un
registro sin ECG es pedirle al usuario que decida sobre algo que no existe.

Como los demás paneles, lo que se puede afirmar sin mirar una pantalla está
separado del dibujo.

Cubre del pliego: ningún ID propio. Es la mitad que se ve de V1_F de
"Filtración de la señal".
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from psglab.analysis.filters import FilterSettings, default_for
from psglab.core.recording import ChannelKind, Recording
from psglab.ui.impedance_panel import FixedColumnDelegate
from psglab.ui import theme
from psglab.ui.channel_selector import color_de_la_clase
from psglab.ui.panel_header import PanelHeader

#: Cómo se llama cada clase de canal en la pantalla. El enum está en inglés
#: —convención del proyecto— y todo lo que ve el usuario, en español.
NOMBRE_DE_CLASE: dict[ChannelKind, str] = {
    ChannelKind.EEG: "EEG",
    ChannelKind.EOG: "EOG (ocular)",
    ChannelKind.EMG: "EMG (muscular)",
    ChannelKind.ECG: "ECG (cardíaco)",
    ChannelKind.RESPIRATORY: "Respiratorio",
    ChannelKind.OTHER: "Otros",
}

#: Las tres columnas editables, en orden, con el atributo que llenan.
CAMPOS: tuple[tuple[str, str], ...] = (
    ("Pasa-altos (Hz)", "highpass_hz"),
    ("Pasa-bajos (Hz)", "lowpass_hz"),
    ("Notch (Hz)", "notch_hz"),
)


class FilterPanel(QWidget):
    """Los filtros de cada clase de canal presente en el registro."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el panel vacío, antes de que haya ningún registro abierto."""
        super().__init__(parent)
        self._clases: list[ChannelKind] = []
        #: La del registro abierto. Es lo que le permite a `default_for()`
        #: descartar los cortes que el registro no admite.
        self._frecuencia: float | None = None
        #: Los canales que se grabaron más lento que el registro, con su
        #: frecuencia de origen (hito 67). Ver `_explicar_el_tope()`.
        self._lentos: dict[str, float] = {}
        #: A quién avisarle cuando el usuario pide aplicar.
        self.on_apply: Callable[[], None] | None = None

        self._cuantos: dict[ChannelKind, int] = {}
        self.tabla = QTreeWidget()
        self.tabla.setHeaderLabels(["Canales", *(rotulo for rotulo, _ in CAMPOS)])
        self.tabla.setRootIsDecorated(False)
        # Tipear un corte empieza a editarlo, y con eso las teclas que escriben
        # son de la tabla y no de los atajos de fase (hito 67): ver
        # `ui/shortcuts.py`.
        self.tabla.setEditTriggers(
            self.tabla.editTriggers() | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        # La clase de canal es la fila, no un dato: se ve y no se edita.
        self.tabla.setItemDelegateForColumn(0, FixedColumnDelegate(self.tabla))

        self.boton_aplicar = QPushButton("Aplicar")
        # El principal del panel, relleno del acento (hito 55).
        self.boton_aplicar.setProperty(theme.PRIMARIO_PROPERTY, True)
        self.boton_sugeridos = QPushButton("Restaurar sugeridos")
        self.boton_aplicar.clicked.connect(self._al_aplicar)
        self.boton_sugeridos.clicked.connect(self.restore_defaults)

        botones = QHBoxLayout()
        botones.addStretch()
        botones.addWidget(self.boton_sugeridos)
        botones.addWidget(self.boton_aplicar)

        #: El encabezado, con cuántas clases tiene el registro y contra qué
        #: frecuencia se sugirieron los cortes. Ver `PanelHeader`.
        self.header = PanelHeader("Filtros")

        self.rotulo = QLabel(
            "Dejá la celda vacía para desactivar ese filtro. Los valores "
            "sugeridos son los habituales en polisomnografía, no una "
            "imposición."
        )
        self.rotulo.setWordWrap(True)

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(8, 8, 8, 8)
        cuerpo.addWidget(self.rotulo)
        cuerpo.addWidget(self.tabla)
        cuerpo.addLayout(botones)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)
        columna.addWidget(self.header)
        columna.addLayout(cuerpo)

    # -- Lo que le da la ventana principal ----------------------------------

    def set_recording(self, recording: Recording) -> None:
        """Arma una fila por clase de canal presente, con los sugeridos.

        Las clases se ordenan como aparecen en el registro y no
        alfabéticamente, por lo mismo que la tabla de impedancias respeta el
        orden del archivo: el investigador las busca donde las vio.
        """
        vistas: list[ChannelKind] = []
        cuantos: dict[ChannelKind, int] = {}
        for canal in recording.channels:
            if canal.kind not in vistas:
                vistas.append(canal.kind)
            cuantos[canal.kind] = cuantos.get(canal.kind, 0) + 1
        self._clases = vistas
        self._cuantos = cuantos
        self._frecuencia = recording.sampling_rate
        self._lentos = {
            canal.name: canal.original_sampling_rate
            for canal in recording.channels
            if canal.original_sampling_rate is not None
            and canal.original_sampling_rate < recording.sampling_rate
        }
        self._explicar_el_tope()
        self._reflejar_el_encabezado()
        self.restore_defaults()

    def _reflejar_el_encabezado(self) -> None:
        """Cuántas clases hay que filtrar, y contra qué frecuencia.

        **La frecuencia va en el encabezado y el tope de Nyquist en el
        rótulo**, que son dos cosas distintas: la primera dice de dónde salen
        los sugeridos y la segunda por qué algunos vienen vacíos.
        """
        cuantas = len(self._clases)
        plural = "clase" if cuantas == 1 else "clases"
        self.header.set_caption(f"{cuantas} {plural} de canal")
        if self._frecuencia is not None:
            self.header.set_detail(f"sugeridos para {self._frecuencia:g} Hz")

    def restore_defaults(self) -> None:
        """Vuelve a los valores sugeridos para cada clase.

        **Sugeridos para este registro**, no los de la tabla: `default_for()`
        descarta los cortes que caen en Nyquist o por encima. En un registro de
        100 Hz eso saca el notch de 50, que si no haría que apretar Aplicar sin
        tocar nada terminara en un cartel de error.
        """
        self._reflejar(
            {clase: default_for(clase, self._frecuencia) for clase in self._clases}
        )

    def _explicar_el_tope(self) -> None:
        """Dice hasta qué frecuencia llega el registro.

        Sin esto, una celda que quedó vacía porque el registro no la admite se
        lee igual que una que el usuario borró: como un olvido y no como una
        imposibilidad. Es la misma distinción que el panel de impedancias hace
        con "sin medir".
        """
        if self._frecuencia is None:
            return
        texto = (
            "Dejá la celda vacía para desactivar ese filtro. Los valores "
            "sugeridos son los habituales en polisomnografía, no una "
            "imposición.\n"
            f"Este registro se muestreó a {self._frecuencia:g} Hz, así que la "
            f"frecuencia más alta que contiene es {self._frecuencia / 2:g} Hz: "
            "los cortes que no entran vienen vacíos."
        )
        # **Y los canales que se grabaron más lento** (hito 67): el archivo los
        # trae a la frecuencia del registro, pero no tienen nada por encima de
        # la mitad de la suya, y un pasa-altos más alto los dejaría planos.
        # `settings_for_kinds()` no se lo da; acá se dice antes de aplicar.
        for frecuencia in sorted(set(self._lentos.values())):
            nombres = [f"«{n}»" for n, f in self._lentos.items() if f == frecuencia]
            quienes = (
                nombres[0]
                if len(nombres) == 1
                else ", ".join(nombres[:-1]) + " y " + nombres[-1]
            )
            uno = len(nombres) == 1
            texto += (
                f"\n{quienes} {'se grabó' if uno else 'se grabaron'} a "
                f"{self._texto(frecuencia)} Hz: no se {'le' if uno else 'les'} aplica un "
                f"pasa-altos de {self._texto(frecuencia / 2)} Hz o más, que "
                f"{'lo dejaría plano' if uno else 'los dejaría planos'}."
            )
        self.rotulo.setText(texto)

    # -- Lo que se puede afirmar sin mirar ----------------------------------

    def kinds(self) -> list[ChannelKind]:
        """Las clases que tienen fila, en orden."""
        return list(self._clases)

    def settings(self) -> dict[ChannelKind, FilterSettings]:
        """Lo que hay escrito, listo para `settings_for_kinds()`.

        Una celda vacía deja ese filtro en `None`, que es como se desactiva.
        Lo que no sea un número también: es una celda de texto y no un
        formulario, así que se descarta en silencio y se corrige sola al
        recargar, igual que en el panel de impedancias.
        """
        elegidos: dict[ChannelKind, FilterSettings] = {}
        for fila in range(self.tabla.topLevelItemCount()):
            entrada = self.tabla.topLevelItem(fila)
            filtros = FilterSettings()
            for columna, (_, atributo) in enumerate(CAMPOS, start=1):
                setattr(filtros, atributo, self._numero(entrada.text(columna)))
            elegidos[self._clases[fila]] = filtros
        return elegidos

    def displayed_value(self, kind: ChannelKind, field: str) -> str:
        """Qué dice una celda, tal como se lee en pantalla."""
        if kind not in self._clases:
            return ""
        entrada = self.tabla.topLevelItem(self._clases.index(kind))
        for columna, (_, atributo) in enumerate(CAMPOS, start=1):
            if atributo == field:
                return entrada.text(columna)
        return ""

    # -- Adentro -------------------------------------------------------------

    def _reflejar(self, por_clase: dict[ChannelKind, FilterSettings]) -> None:
        """Vuelca los filtros a la tabla."""
        self.tabla.clear()
        for clase in self._clases:
            filtros = por_clase.get(clase, FilterSettings())
            entrada = QTreeWidgetItem(
                [
                    self._rotulo_de(clase),
                    *(self._texto(getattr(filtros, atributo)) for _, atributo in CAMPOS),
                ]
            )
            entrada.setFlags(entrada.flags() | Qt.ItemFlag.ItemIsEditable)
            entrada.setIcon(0, self._muestra_de(clase))
            self.tabla.addTopLevelItem(entrada)
        # La columna de la clase, del ancho de su texto: con la cantidad de
        # canales, «EOG (ocular) · 1 canal» se cortaba en «EOG (ocular)…» y
        # se perdía justo lo que se había agregado.
        self.tabla.resizeColumnToContents(0)

    def _rotulo_de(self, clase: ChannelKind) -> str:
        """La clase y cuántos canales tiene (hito 55).

        **Un filtro de la fila vale para todos sus canales**, y la tabla no
        decía cuántos eran: «EEG» con dos canales y con veinte se leían igual.
        El prototipo lo escribía debajo; va al lado, que en una tabla no cabe
        una segunda línea.
        """
        cuantos = self._cuantos.get(clase, 0)
        plural = "canal" if cuantos == 1 else "canales"
        return f"{NOMBRE_DE_CLASE[clase]} · {cuantos} {plural}"

    def _muestra_de(self, clase: ChannelKind) -> QIcon:
        """El cuadradito del color de la clase, el mismo del selector de canales.

        Se rearma cada vez que se vuelca la tabla, así que sigue al esquema.
        """
        lienzo = QPixmap(10, 10)
        lienzo.fill(QColor(color_de_la_clase(clase)))
        return QIcon(lienzo)

    def _texto(self, valor: float | None) -> str:
        """Cómo se escribe un corte en la celda, con la coma del idioma."""
        if valor is None:
            return ""
        return f"{valor:g}".replace(".", ",")

    def _numero(self, texto: str) -> float | None:
        """Lo que dice una celda, como número. Vacío o ilegible es `None`."""
        limpio = texto.strip().replace(",", ".")
        if not limpio:
            return None
        try:
            return float(limpio)
        except ValueError:
            return None

    def _al_aplicar(self) -> None:
        """El usuario apretó Aplicar."""
        if self.on_apply is not None:
            self.on_apply()
