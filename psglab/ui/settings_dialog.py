"""La ventana de configuración: lo que el usuario puede elegir y el programa recuerda.

Se inspira en la de EDFbrowser, que tiene siete solapas. **Ésta tiene cinco**, y
las dos que faltan faltan a propósito:

- **Cursores** configura los colores y el comportamiento de las reglas que miden
  sobre la señal, y el programa todavía no tiene reglas.
- **Calibración** hace que un milímetro de pantalla sea un milímetro de papel, y
  nada del programa convierte todavía a milímetros.

Una solapa que no configura nada es una promesa que el programa no cumple: es
el mismo criterio que deja fuera de `ColorScheme` los colores de las reglas.
Entran cuando entre lo que configuran, cada una en su propia fase.

**Todo se aplica en el momento**, como en la referencia: no hay "Aceptar" ni
"Cancelar", sólo "Cerrar". Cada cambio construye unas `Preferences` nuevas —que
se comprueban al construirse— y se las pasa a la ventana principal por
`on_change`. Este módulo no aplica nada ni escribe ningún archivo salvo los
esquemas que el usuario pide guardar.

Avisa por callbacks y no por señales de Qt, igual que los paneles de análisis y
las herramientas: la ventana principal los cablea.

Cubre del pliego: V3_F de "Herramienta Übersicht", que es donde se elige cuántas
ventanas vecinas muestra el panel de contexto. Lo demás es infraestructura de
presentación que agregó el refactor de la interfaz.
"""

from collections.abc import Callable

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDoubleSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from psglab.analysis.psd import METHODS
from psglab.config import VIEW_TIMESCALE_PRESETS
from psglab.core.annotations import PALETTE
from psglab.core.nomenclature import Nomenclature
from psglab.ui import fonts, theme
from psglab.ui.menus import duration_text
from psglab.ui.preferences import (
    MAX_AMPLITUDE_BAND_UV,
    MAX_FONT_SIZE,
    MAX_MAGNIFIER_RADIUS_SECONDS,
    MAX_MAGNIFIER_ZOOM,
    MAX_OVERVIEW_WINDOWS,
    MIN_AMPLITUDE_BAND_UV,
    MIN_FONT_SIZE,
    MIN_MAGNIFIER_RADIUS_SECONDS,
    MIN_MAGNIFIER_ZOOM,
    Preferences,
)
from psglab.utils.errors import InvalidPreferencesError, PsgLabError
from psglab.utils.units import MICROVOLT

#: Las cuatro solapas, en el orden en que aparecen. **Eran cinco hasta el hito
#: 35**: la de Colores se fue entera con la edición de esquemas, y elegir entre
#: los dos que quedan pasó al menú «Ver», que es donde ya viven los tres fondos
#: de grilla.
TAB_TITLES: tuple[str, ...] = (
    "Editor de anotaciones",
    "Espectro de potencia",
    "Otras",
    "Tipografía",
)

#: Cómo se muestra cada método de estimación del espectro.
METHOD_NAMES: dict[str, str] = {"welch": "Welch", "multitaper": "Multitaper"}

def _numero(texto: str) -> float:
    """Lee un número escrito como lo escribiría un investigador: con coma o punto.

    Raises:
        ValueError: si no es un número.
    """
    return float(texto.strip().replace(",", "."))


def _texto(numero: float) -> str:
    """Escribe un número con coma decimal y sin ceros de más."""
    return f"{numero:g}".replace(".", ",")


class ColorButton(QPushButton):
    """Un botón que muestra un color y deja elegir otro.

    Avisa por `on_chosen` sólo cuando el usuario elige, no cuando el programa
    le fija un color para reflejar las preferencias: sin esa diferencia, abrir
    la ventana de configuración volvería a aplicar todo lo que muestra.
    """

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.on_chosen: Callable[[str], None] | None = None
        self._color = color
        self.setFixedSize(52, 22)
        self.clicked.connect(self._elegir)
        self._pintar()

    def color(self) -> str:
        """El color que muestra."""
        return self._color

    def set_color(self, color: str) -> None:
        """Muestra otro color, **sin avisar**. Es para reflejar, no para elegir."""
        self._color = color
        self._pintar()

    def choose(self, color: str) -> None:
        """Hace lo mismo que el diálogo de colores cuando el usuario elige uno.

        Un color que no se puede dibujar se ignora: el diálogo de Qt no los
        produce, y este método no puede ser la puerta por la que entren.
        """
        if not theme.is_valid_color(color):
            return
        self.set_color(color)
        if self.on_chosen is not None:
            self.on_chosen(color)

    def _elegir(self) -> None:
        elegido = QColorDialog.getColor(QColor(self._normalizado()), self, "Elegir un color")
        if elegido.isValid():
            self.choose(elegido.name())

    def _normalizado(self) -> str:
        """El color en `#rrggbb`, que es lo que entiende la hoja de estilo.

        pyqtgraph acepta además letras sueltas como "w", que Qt no.
        """
        return pg.mkColor(self._color).name()

    def _pintar(self) -> None:
        self.setStyleSheet(
            f"QPushButton {{ background-color: {self._normalizado()};"
            " border: 1px solid #808080; }"
        )
        self.setToolTip(self._normalizado())


class SettingsDialog(QDialog):
    """La ventana de configuración, con sus cinco solapas."""

    def __init__(
        self,
        preferences: Preferences,
        annotation_colors: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Arma la ventana mostrando unas preferencias.

        Args:
            preferences: lo que se muestra al abrir.
            annotation_colors: las clases de evento que hay para configurar y el
                color con que se dibujan hoy. Lo arma la ventana principal: con
                un registro abierto son las de su sesión, y sin él las de
                fábrica.
        """
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        #: Se llama con las preferencias nuevas en cada cambio.
        self.on_change: Callable[[Preferences], None] | None = None
        #: Se llama cuando algo que el usuario pidió no se pudo hacer.
        self.on_error: Callable[[PsgLabError], None] | None = None
        self._prefs = preferences
        self._colores_de_clase: dict[str, str] = dict(annotation_colors or {})
        self._reflejando = False

        self.tabs = QTabWidget()
        self.tabs.addTab(self._armar_anotaciones(), TAB_TITLES[0])
        self.tabs.addTab(self._armar_espectro(), TAB_TITLES[1])
        self.tabs.addTab(self._armar_otras(), TAB_TITLES[2])
        self.tabs.addTab(self._armar_tipografia(), TAB_TITLES[3])

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botones.rejected.connect(self.close)

        columna = QVBoxLayout(self)
        columna.addWidget(self.tabs)
        columna.addWidget(botones)

        self.set_preferences(preferences, annotation_colors)

    # -- Lo que usa la ventana principal ------------------------------------

    @property
    def preferences(self) -> Preferences:
        """Las preferencias que muestra la ventana ahora."""
        return self._prefs

    def tab_titles(self) -> list[str]:
        """Los títulos de las solapas, en orden."""
        return [self.tabs.tabText(i) for i in range(self.tabs.count())]

    def set_preferences(
        self,
        preferences: Preferences,
        annotation_colors: dict[str, str] | None = None,
    ) -> None:
        """Muestra otras preferencias **sin avisar**.

        Es lo que hace la ventana principal cada vez que la abre: lo mostrado
        tiene que ser lo vigente, y reflejarlo no puede volver a aplicarlo.

        Raises:
            InvalidPreferencesError: si no son preferencias.
        """
        if not isinstance(preferences, Preferences):
            raise InvalidPreferencesError(
                "No se pudo mostrar la configuración.",
                details=f"Se recibió {type(preferences).__name__}.",
            )
        self._prefs = preferences
        if annotation_colors is not None:
            self._colores_de_clase = dict(annotation_colors)
        self._reflejando = True
        try:
            self._reflejar_anotaciones()
            self._reflejar_espectro()
            self._reflejar_otras()
            self._reflejar_tipografia()
        finally:
            self._reflejando = False

    # -- El canal hacia afuera ------------------------------------------------

    def _cambiar(self, nuevas: Preferences) -> None:
        """Toma unas preferencias nuevas y avisa, salvo que se esté reflejando."""
        # Lo que no cambia nada no se avisa: aplicar la configuración entera
        # por tocar un control que ya estaba así sería trabajo de más.
        if self._reflejando or nuevas == self._prefs:
            return
        self._prefs = nuevas
        if self.on_change is not None:
            self.on_change(nuevas)

    def _avisar(self, error: PsgLabError) -> None:
        if self.on_error is not None:
            self.on_error(error)

    def _armar_anotaciones(self) -> QWidget:
        solapa = QWidget()
        columna = QVBoxLayout(solapa)
        columna.addWidget(
            QLabel(
                "El color de cada clase de evento, en el visualizador y en el "
                "panel de contexto. Una clase con color elegido queda disponible "
                "en cualquier registro."
            )
        )
        self.annotation_table = QTableWidget(0, 2)
        self.annotation_table.setHorizontalHeaderLabels(["Clase", "Color"])
        self.annotation_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.annotation_table.verticalHeader().setVisible(False)
        columna.addWidget(self.annotation_table)
        #: Un botón por clase, por nombre de clase.
        self.annotation_buttons: dict[str, ColorButton] = {}
        return solapa

    def _reflejar_anotaciones(self) -> None:
        clases = list(self._colores_de_clase)
        for clase, _ in self._prefs.annotation_colors:
            if clase not in clases:
                clases.append(clase)

        self.annotation_table.setRowCount(0)
        self.annotation_buttons = {}
        for fila, clase in enumerate(clases):
            color = (
                self._prefs.annotation_color(clase)
                or self._colores_de_clase.get(clase)
                or PALETTE[fila % len(PALETTE)]
            )
            self.annotation_table.insertRow(fila)
            nombre = QTableWidgetItem(clase)
            nombre.setFlags(nombre.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.annotation_table.setItem(fila, 0, nombre)
            boton = ColorButton(color)
            boton.on_chosen = lambda elegido, c=clase: self._cambiar_color_de_clase(c, elegido)
            self.annotation_table.setCellWidget(fila, 1, boton)
            self.annotation_buttons[clase] = boton

    def _cambiar_color_de_clase(self, clase: str, color: str) -> None:
        try:
            nuevas = self._prefs.with_annotation_color(clase, color)
        except PsgLabError as error:
            self._avisar(error)
            return
        self._cambiar(nuevas)

    # -- Espectro de potencia ------------------------------------------------------

    def _armar_espectro(self) -> QWidget:
        solapa = QWidget()
        columna = QVBoxLayout(solapa)

        formulario = QFormLayout()
        self.psd_method = QComboBox()
        for metodo in METHODS:
            self.psd_method.addItem(METHOD_NAMES.get(metodo, metodo), metodo)
        self.psd_method.currentIndexChanged.connect(self._cambiar_metodo)
        formulario.addRow("Método:", self.psd_method)
        self.log_power = QCheckBox("Eje de potencia logarítmico")
        self.log_power.toggled.connect(
            lambda activo: self._cambiar(
                self._prefs.with_changes(psd_log_power=bool(activo))
            )
        )
        formulario.addRow("", self.log_power)
        columna.addLayout(formulario)

        columna.addWidget(QLabel("Bandas de frecuencia (también las usa la conectividad):"))
        self.bands_table = QTableWidget(0, 3)
        self.bands_table.setHorizontalHeaderLabels(["Banda", "Desde (Hz)", "Hasta (Hz)"])
        self.bands_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.bands_table.verticalHeader().setVisible(False)
        self.bands_table.itemChanged.connect(self._bandas_editadas)
        columna.addWidget(self.bands_table)

        #: Por qué las bandas escritas no se aplicaron. Vacío si se aplicaron.
        #: **No es un cartel**: se escribe en una tabla, y un diálogo modal por
        #: cada celda a medio escribir sería insoportable.
        self.bands_notice = QLabel("")
        self.bands_notice.setWordWrap(True)
        columna.addWidget(self.bands_notice)

        botones = QHBoxLayout()
        self.add_band_button = QPushButton("Agregar banda")
        self.add_band_button.clicked.connect(self.add_band)
        self.remove_band_button = QPushButton("Quitar banda")
        self.remove_band_button.clicked.connect(self.remove_band)
        self.restore_bands_button = QPushButton("Volver a las convencionales")
        self.restore_bands_button.clicked.connect(self.restore_bands)
        botones.addWidget(self.add_band_button)
        botones.addWidget(self.remove_band_button)
        botones.addStretch(1)
        botones.addWidget(self.restore_bands_button)
        columna.addLayout(botones)
        return solapa

    def _cambiar_metodo(self, _indice: int) -> None:
        metodo = self.psd_method.currentData()
        if metodo is None:
            return
        self._cambiar(self._prefs.with_changes(psd_method=metodo))

    def _reflejar_espectro(self) -> None:
        indice = self.psd_method.findData(self._prefs.psd_method)
        self.psd_method.setCurrentIndex(max(indice, 0))
        self.log_power.setChecked(self._prefs.psd_log_power)
        self._llenar_bandas(self._prefs.bands())

    def _llenar_bandas(self, bandas: dict[str, tuple[float, float]]) -> None:
        anterior = self._reflejando
        self._reflejando = True
        try:
            self.bands_table.setRowCount(0)
            for fila, (nombre, (desde, hasta)) in enumerate(bandas.items()):
                self.bands_table.insertRow(fila)
                self.bands_table.setItem(fila, 0, QTableWidgetItem(nombre))
                self.bands_table.setItem(fila, 1, QTableWidgetItem(_texto(desde)))
                self.bands_table.setItem(fila, 2, QTableWidgetItem(_texto(hasta)))
            self.bands_notice.setText("")
            self.remove_band_button.setEnabled(self.bands_table.rowCount() > 1)
        finally:
            self._reflejando = anterior

    def _leer_bandas(self) -> dict[str, tuple[float, float]]:
        """Lo que dice la tabla, como bandas.

        Raises:
            InvalidPreferencesError: si una celda está vacía, un número no se
                entiende o dos bandas se llaman igual. Que la banda se pueda
                integrar lo decide después `Preferences`, con la regla del
                análisis.
        """
        bandas: dict[str, tuple[float, float]] = {}
        for fila in range(self.bands_table.rowCount()):
            celdas = [self.bands_table.item(fila, col) for col in range(3)]
            textos = ["" if celda is None else celda.text() for celda in celdas]
            nombre = textos[0].strip()
            if not nombre:
                raise InvalidPreferencesError(
                    f"La banda de la fila {fila + 1} no tiene nombre.",
                    details="Cada banda necesita un nombre para la tabla del espectro.",
                )
            if nombre in bandas:
                raise InvalidPreferencesError(
                    f"Hay dos bandas que se llaman «{nombre}».",
                    details="Los nombres de las bandas no se pueden repetir.",
                )
            try:
                desde, hasta = _numero(textos[1]), _numero(textos[2])
            except ValueError as error:
                raise InvalidPreferencesError(
                    f"La banda «{nombre}» tiene un número que no se entiende.",
                    details=f"Se leyó desde = {textos[1]!r}, hasta = {textos[2]!r}.",
                ) from error
            bandas[nombre] = (desde, hasta)
        return bandas

    def _bandas_editadas(self, _celda: QTableWidgetItem) -> None:
        if self._reflejando:
            return
        self._aplicar_bandas()

    def _aplicar_bandas(self) -> None:
        """Aplica lo que dice la tabla, o explica por qué no."""
        try:
            nuevas = self._prefs.with_bands(self._leer_bandas())
        except PsgLabError as error:
            self.bands_notice.setText(f"No se aplicaron las bandas: {error}")
            return
        self.bands_notice.setText("")
        self.remove_band_button.setEnabled(self.bands_table.rowCount() > 1)
        self._cambiar(nuevas)

    def add_band(self) -> None:
        """Agrega una banda al final, ya válida, a continuación de la última."""
        existentes = {
            self.bands_table.item(fila, 0).text()
            for fila in range(self.bands_table.rowCount())
            if self.bands_table.item(fila, 0) is not None
        }
        numero = 1
        while f"Banda {numero}" in existentes:
            numero += 1
        desde = max((hasta for _, hasta in self._prefs.bands().values()), default=0.0)
        fila = self.bands_table.rowCount()
        anterior = self._reflejando
        self._reflejando = True
        try:
            self.bands_table.insertRow(fila)
            self.bands_table.setItem(fila, 0, QTableWidgetItem(f"Banda {numero}"))
            self.bands_table.setItem(fila, 1, QTableWidgetItem(_texto(desde)))
            self.bands_table.setItem(fila, 2, QTableWidgetItem(_texto(desde + 4.0)))
        finally:
            self._reflejando = anterior
        self._aplicar_bandas()

    def remove_band(self) -> None:
        """Quita la banda elegida, o la última. **Siempre queda una**: un
        espectro sin bandas no tiene tabla que mostrar."""
        if self.bands_table.rowCount() <= 1:
            return
        fila = self.bands_table.currentRow()
        if fila < 0:
            fila = self.bands_table.rowCount() - 1
        self.bands_table.removeRow(fila)
        self._aplicar_bandas()

    def restore_bands(self) -> None:
        """Vuelve a las bandas convencionales."""
        self._cambiar(self._prefs.with_bands(None))
        self._llenar_bandas(self._prefs.bands())

    # -- Otras ---------------------------------------------------------------------

    def _armar_otras(self) -> QWidget:
        """Dos grupos, porque se aplican en momentos distintos.

        Lo de abrir un registro espera al próximo; el panel de contexto cambia
        enseguida. Un solo cartel de «se aplican la próxima vez» sobre los dos
        habría mentido sobre el segundo.
        """
        solapa = QWidget()
        columna = QVBoxLayout(solapa)
        al_abrir = QGroupBox("Al abrir un registro")
        columna.addWidget(al_abrir)
        formulario = QFormLayout(al_abrir)
        formulario.addRow(
            QLabel("Se aplican la próxima vez que se abra un registro.")
        )

        self.open_view = QComboBox()
        self.open_view.currentIndexChanged.connect(self._cambiar_pagina)
        formulario.addRow("Página al abrir:", self.open_view)

        self.open_nomenclature = QComboBox()
        for miembro in Nomenclature:
            self.open_nomenclature.addItem(miembro.value, miembro.name)
        self.open_nomenclature.currentIndexChanged.connect(self._cambiar_nomenclatura)
        formulario.addRow("Nomenclatura de un scoring nuevo:", self.open_nomenclature)

        self.open_clock_axis = QCheckBox(
            "Hipnograma en hora real, si el registro la informa"
        )
        self.open_clock_axis.toggled.connect(
            lambda activo: self._cambiar(
                self._prefs.with_changes(open_clock_axis=bool(activo))
            )
        )
        formulario.addRow("", self.open_clock_axis)

        # Hito 64: como en los programas de scoring, se puede apagar.
        self.advance_after_scoring = QCheckBox(
            "Al scorear una ventana, pasar a la siguiente"
        )
        self.advance_after_scoring.toggled.connect(
            lambda activo: self._cambiar(
                self._prefs.with_changes(advance_after_scoring=bool(activo))
            )
        )
        formulario.addRow("", self.advance_after_scoring)

        # V3_F de la Übersicht: cuántas ventanas vecinas, de cada lado por
        # separado, porque el pliego la pide asimétrica.
        contexto = QGroupBox("Panel de contexto (Übersicht)")
        columna.addWidget(contexto)
        vecinas = QFormLayout(contexto)
        self.overview_before = QSpinBox()
        self.overview_after = QSpinBox()
        for campo, control, texto in (
            ("overview_before", self.overview_before, "Ventanas anteriores:"),
            ("overview_after", self.overview_after, "Ventanas posteriores:"),
        ):
            control.setRange(0, MAX_OVERVIEW_WINDOWS)
            control.valueChanged.connect(
                lambda valor, campo=campo: self._cambiar(
                    self._prefs.with_changes(**{campo: int(valor)})
                )
            )
            vecinas.addRow(texto, control)

        # Hito 32: tres ajustes que las herramientas tenían y la ventana no
        # ofrecía. Se aplican enseguida, como el panel de contexto.
        herramientas = QGroupBox("Herramientas")
        columna.addWidget(herramientas)
        ajustes = QFormLayout(herramientas)
        self.amplitude_band = QDoubleSpinBox()
        self.magnifier_radius = QDoubleSpinBox()
        self.magnifier_zoom = QDoubleSpinBox()
        for campo, control, texto, minimo, maximo, paso, decimales, sufijo in (
            ("amplitude_band_uv", self.amplitude_band, "Altura de la banda de amplitud:",
             MIN_AMPLITUDE_BAND_UV, MAX_AMPLITUDE_BAND_UV, 5.0, 0, f" {MICROVOLT}"),
            ("magnifier_radius_seconds", self.magnifier_radius, "Radio de la lupa:",
             MIN_MAGNIFIER_RADIUS_SECONDS, MAX_MAGNIFIER_RADIUS_SECONDS, 0.1, 1, " s"),
            ("magnifier_zoom", self.magnifier_zoom, "Aumento de la lupa:",
             MIN_MAGNIFIER_ZOOM, MAX_MAGNIFIER_ZOOM, 0.5, 1, " ×"),
        ):
            control.setRange(minimo, maximo)
            control.setSingleStep(paso)
            control.setDecimals(decimales)
            control.setSuffix(sufijo)
            control.valueChanged.connect(
                lambda valor, campo=campo: self._cambiar(
                    self._prefs.with_changes(**{campo: float(valor)})
                )
            )
            ajustes.addRow(texto, control)
        columna.addStretch(1)
        return solapa

    def _cambiar_pagina(self, _indice: int) -> None:
        segundos = self.open_view.currentData()
        if segundos is None:
            return
        self._cambiar(self._prefs.with_changes(open_view_seconds=float(segundos)))

    def _cambiar_nomenclatura(self, _indice: int) -> None:
        nombre = self.open_nomenclature.currentData()
        if nombre is None:
            return
        self._cambiar(self._prefs.with_changes(open_nomenclature=nombre))

    def _reflejar_otras(self) -> None:
        opciones = list(VIEW_TIMESCALE_PRESETS)
        # Una duración que no está entre las ofrecidas —porque se editó el
        # archivo a mano, o porque la lista cambió— se muestra igual: elegir
        # otra en silencio sería cambiar la preferencia sin que nadie lo pida.
        if self._prefs.open_view_seconds not in opciones:
            opciones.append(self._prefs.open_view_seconds)
            opciones.sort()
        self.open_view.clear()
        for segundos in opciones:
            self.open_view.addItem(duration_text(segundos), segundos)
        self.open_view.setCurrentIndex(
            self.open_view.findData(self._prefs.open_view_seconds)
        )
        self.open_nomenclature.setCurrentIndex(
            self.open_nomenclature.findData(self._prefs.open_nomenclature)
        )
        self.open_clock_axis.setChecked(self._prefs.open_clock_axis)
        self.advance_after_scoring.setChecked(self._prefs.advance_after_scoring)
        self.overview_before.setValue(self._prefs.overview_before)
        self.overview_after.setValue(self._prefs.overview_after)
        self.amplitude_band.setValue(self._prefs.amplitude_band_uv)
        self.magnifier_radius.setValue(self._prefs.magnifier_radius_seconds)
        self.magnifier_zoom.setValue(self._prefs.magnifier_zoom)

    # -- Tipografía ---------------------------------------------------------------

    def _armar_tipografia(self) -> QWidget:
        solapa = QWidget()
        formulario = QFormLayout(solapa)

        # **No hay lista de familias** desde el hito 43. La tipografía es la del
        # programa —IBM Plex Sans, y su hermana de ancho fijo para las
        # lecturas— por el mismo argumento que dejó los colores en dos
        # esquemas: una lista abierta son infinitos aspectos posibles y ninguno
        # garantizado. El tamaño sí se elige, que es lo que hace falta para ver
        # de lejos.
        self.system_font = QCheckBox("Usar el tamaño del sistema")
        self.system_font.toggled.connect(self._cambiar_tipografia)
        formulario.addRow("", self.system_font)

        self.font_size = QSpinBox()
        self.font_size.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.font_size.setSuffix(" pt")
        self.font_size.valueChanged.connect(
            lambda _valor: self._cambiar_tipografia(self.system_font.isChecked())
        )
        formulario.addRow("Tamaño:", self.font_size)

        # **La muestra lleva las tres voces**, no una: la de leer, la de medir y
        # la de lo que nadie midió. Con una sola, cambiar el tamaño no decía
        # nada de la escala.
        self.font_preview = QLabel("Ventana 12 de 960")
        self.numeric_preview = QLabel("01:50:00 · 100 µV")
        self.absent_preview = QLabel("sin medir")
        formulario.addRow("Muestra:", self.font_preview)
        formulario.addRow("", self.numeric_preview)
        formulario.addRow("", self.absent_preview)
        return solapa

    def _cambiar_tipografia(self, del_sistema: bool) -> None:
        self.font_size.setEnabled(not del_sistema)
        self._mostrar_muestra()
        if del_sistema:
            self._cambiar(self._prefs.with_changes(font_size=None))
            return
        self._cambiar(self._prefs.with_changes(font_size=self.font_size.value()))

    def _mostrar_muestra(self) -> None:
        """Las tres voces de la escala, al tamaño que se está eligiendo."""
        base = QFont()
        base.setPointSize(self.font_size.value())
        for etiqueta, rol in (
            (self.font_preview, "cuerpo"),
            (self.numeric_preview, "lectura"),
            (self.absent_preview, "ausente"),
        ):
            etiqueta.setFont(fonts.font_for(rol, base))

    def _reflejar_tipografia(self) -> None:
        del_sistema = self._prefs.font_size is None
        sistema = QFont()
        tamano = self._prefs.font_size or max(sistema.pointSize(), MIN_FONT_SIZE)
        self.font_size.setValue(tamano)
        self.system_font.setChecked(del_sistema)
        self.font_size.setEnabled(not del_sistema)
        self._mostrar_muestra()
