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

Cubre del pliego: ningún ID. Es infraestructura de presentación que agregó el
refactor de la interfaz.
"""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
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
from psglab.ui import theme
from psglab.ui.menus import duration_text
from psglab.ui.preferences import (
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    Preferences,
    load_scheme,
    save_scheme,
)
from psglab.utils.errors import InvalidPreferencesError, PsgLabError

#: Las cinco solapas, en el orden en que aparecen.
TAB_TITLES: tuple[str, ...] = (
    "Colores",
    "Editor de anotaciones",
    "Espectro de potencia",
    "Otras",
    "Tipografía",
)

#: Qué color del esquema se edita con cada botón, y cómo lo lee el usuario.
#: El orden es el de la pantalla: primero lo que se mira todo el tiempo.
COLOR_FIELDS: tuple[tuple[str, str], ...] = (
    ("background", "Fondo"),
    ("chrome", "Fondo de la ventana"),
    ("signals", "Señales"),
    ("foreground", "Ejes y texto"),
    ("coarse_grid", "Grilla visible"),
    ("fine_grid", "Grilla discreta"),
    ("accent", "Curva de los paneles"),
    ("overview_background", "Fondo del contexto"),
    ("overview_current", "Época actual en el contexto"),
    ("overview_border", "Borde del contexto"),
    ("overview_current_border", "Borde de la época actual"),
    ("overview_text", "Texto del contexto"),
)

#: Cómo se muestra cada método de estimación del espectro.
METHOD_NAMES: dict[str, str] = {"welch": "Welch", "multitaper": "Multitaper"}

#: Lo que se agrega al nombre de un esquema de fábrica cuando se lo modifica.
MODIFIED_SUFFIX: str = " (modificado)"


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
        self.tabs.addTab(self._armar_colores(), TAB_TITLES[0])
        self.tabs.addTab(self._armar_anotaciones(), TAB_TITLES[1])
        self.tabs.addTab(self._armar_espectro(), TAB_TITLES[2])
        self.tabs.addTab(self._armar_otras(), TAB_TITLES[3])
        self.tabs.addTab(self._armar_tipografia(), TAB_TITLES[4])

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
            self._reflejar_colores()
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

    # -- Colores ------------------------------------------------------------------

    def _armar_colores(self) -> QWidget:
        solapa = QWidget()
        izquierda = QGridLayout()

        #: Un botón por color del esquema, por nombre de campo.
        self.color_buttons: dict[str, ColorButton] = {}
        for fila, (campo, rotulo) in enumerate(COLOR_FIELDS):
            boton = ColorButton("#000000")
            boton.on_chosen = lambda color, c=campo: self._cambiar_esquema(**{c: color})
            izquierda.addWidget(QLabel(rotulo), fila, 0)
            izquierda.addWidget(boton, fila, 1)
            self.color_buttons[campo] = boton

        fila = len(COLOR_FIELDS)
        self.baseline_check = QCheckBox("Línea de base")
        self.baseline_check.toggled.connect(self._cambiar_linea_de_base)
        self.baseline_button = ColorButton("#808080")
        self.baseline_button.on_chosen = lambda _color: self._cambiar_linea_de_base(
            self.baseline_check.isChecked()
        )
        izquierda.addWidget(self.baseline_check, fila, 0)
        izquierda.addWidget(self.baseline_button, fila, 1)

        self.vary_colors = QCheckBox("Un color distinto por canal")
        self.vary_colors.toggled.connect(
            lambda activo: self._cambiar_esquema(vary_signal_colors=bool(activo))
        )
        izquierda.addWidget(self.vary_colors, fila + 1, 0, 1, 2)

        #: Qué no se va a distinguir del fondo con los colores elegidos. Es un
        #: aviso y no un rechazo: el usuario puede querer un esquema de poco
        #: contraste para imprimir, pero tiene que saberlo.
        self.contrast_notice = QLabel("")
        self.contrast_notice.setWordWrap(True)
        izquierda.addWidget(self.contrast_notice, fila + 3, 0, 1, 2)

        paleta = QGroupBox("Colores de los canales")
        self._fila_de_paleta = QHBoxLayout(paleta)
        #: Un botón por color de la paleta de canales. Se rearman al cambiar de
        #: esquema, porque no todos los esquemas tienen la misma cantidad.
        self.palette_buttons: list[ColorButton] = []
        izquierda.addWidget(paleta, fila + 2, 0, 1, 2)
        # El espacio que sobra va a una columna y una fila vacías: sin esto los
        # botones se alejaban de su rótulo y la paleta crecía hasta ocupar
        # media ventana.
        izquierda.setColumnStretch(2, 1)
        izquierda.setRowStretch(fila + 4, 1)
        self._fila_de_paleta.addStretch(1)

        derecha = QVBoxLayout()
        esquemas = QGroupBox("Esquema de color")
        lista = QVBoxLayout(esquemas)
        self.scheme_label = QLabel("")
        lista.addWidget(self.scheme_label)
        #: Un botón por esquema de fábrica. Se arman recorriendo
        #: `theme.SCHEMES`: un esquema nuevo aparece solo.
        self.scheme_buttons: dict[str, QPushButton] = {}
        for nombre in theme.SCHEMES:
            boton = QPushButton(nombre)
            boton.clicked.connect(lambda _=False, n=nombre: self.choose_scheme(n))
            lista.addWidget(boton)
            self.scheme_buttons[nombre] = boton
        lista.addSpacing(12)
        self.save_scheme_button = QPushButton("Guardar…")
        self.save_scheme_button.clicked.connect(self._guardar_esquema)
        self.load_scheme_button = QPushButton("Cargar…")
        self.load_scheme_button.clicked.connect(self._cargar_esquema)
        lista.addWidget(self.save_scheme_button)
        lista.addWidget(self.load_scheme_button)
        derecha.addWidget(esquemas)

        grilla = QGroupBox("Grilla")
        opciones = QVBoxLayout(grilla)
        self.grid_normal = QRadioButton("Normal")
        self.grid_ecg = QRadioButton("ECG (cuadriculada)")
        grupo = QButtonGroup(grilla)
        grupo.addButton(self.grid_normal)
        grupo.addButton(self.grid_ecg)
        self.grid_ecg.toggled.connect(
            lambda activo: self._cambiar_esquema(ecg_grid=bool(activo))
        )
        opciones.addWidget(self.grid_normal)
        opciones.addWidget(self.grid_ecg)
        derecha.addWidget(grilla)
        derecha.addStretch(1)

        fila_entera = QHBoxLayout(solapa)
        fila_entera.addLayout(izquierda, 3)
        fila_entera.addLayout(derecha, 1)
        return solapa

    def choose_scheme(self, name: str) -> None:
        """Elige uno de los esquemas de fábrica, como su botón."""
        try:
            esquema = theme.scheme_by_name(name)
        except PsgLabError as error:
            self._avisar(error)
            return
        self._cambiar(self._prefs.with_scheme(esquema))
        self._reflejar_solo_colores()

    def _cambiar_esquema(self, **cambios: object) -> None:
        """Cambia campos del esquema vigente.

        **Un esquema de fábrica modificado deja de llamarse igual**: pasa a
        llamarse "Oscuro (modificado)". Si conservara el nombre, el menú y esta
        ventana dirían "Oscuro" sobre algo que ya no es el oscuro. Y si el
        cambio lo devuelve exactamente al de fábrica, vuelve a ser ése.
        """
        # Mientras se reflejan las preferencias, marcar una casilla dispara este
        # método: sin la guarda, mostrar la solapa volvía a mostrarla.
        if self._reflejando:
            return
        esquema = self._prefs.scheme()
        cambiado = replace(esquema, **cambios)
        if cambiado == esquema:
            return
        base = esquema.name.removesuffix(MODIFIED_SUFFIX)
        de_fabrica = theme.SCHEMES.get(base)
        if de_fabrica is not None and replace(cambiado, name=base) == de_fabrica:
            cambiado = de_fabrica
        elif de_fabrica is not None:
            cambiado = replace(cambiado, name=base + MODIFIED_SUFFIX)
        self._cambiar(self._prefs.with_scheme(cambiado))
        self._reflejar_solo_colores()

    def _cambiar_linea_de_base(self, activa: bool) -> None:
        self.baseline_button.setEnabled(bool(activa))
        self._cambiar_esquema(
            baseline=self.baseline_button.color() if activa else None
        )

    def _cambiar_paleta(self, posicion: int, color: str) -> None:
        paleta = list(self._prefs.scheme().signal_palette)
        paleta[posicion] = color
        self._cambiar_esquema(signal_palette=tuple(paleta))

    def _guardar_esquema(self) -> None:
        esquema = self._prefs.scheme()
        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar el esquema de color",
            f"{esquema.name}.json",
            "Esquemas de color (*.json)",
        )
        if not ruta:
            return
        try:
            save_scheme(Path(ruta), esquema)
        except PsgLabError as error:
            self._avisar(error)

    def _cargar_esquema(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Cargar un esquema de color", "", "Esquemas de color (*.json)"
        )
        if not ruta:
            return
        try:
            esquema = load_scheme(Path(ruta))
        except PsgLabError as error:
            self._avisar(error)
            return
        self._cambiar(self._prefs.with_scheme(esquema))
        self._reflejar_solo_colores()

    def _reflejar_solo_colores(self) -> None:
        """Vuelve a mostrar la solapa de colores sin avisar."""
        anterior = self._reflejando
        self._reflejando = True
        try:
            self._reflejar_colores()
        finally:
            self._reflejando = anterior

    def _reflejar_colores(self) -> None:
        esquema = self._prefs.scheme()
        self.scheme_label.setText(f"En uso: {esquema.name}")
        bajos = theme.low_contrast_elements(esquema)
        self.contrast_notice.setText(
            ""
            if not bajos
            else "Poco contraste con el fondo: "
            + "; ".join(
                f"{que} ({_texto(contraste)} a 1)" for que, contraste in bajos
            )
        )
        for campo, boton in self.color_buttons.items():
            valor = getattr(esquema, campo)
            # Un fondo de ventana vacío es «el mismo que el fondo»: el botón
            # muestra ése, que es el que se ve.
            boton.set_color(valor if valor is not None else esquema.background)
        # El color del botón va antes que la casilla: marcarla lee el botón.
        if esquema.baseline is not None:
            self.baseline_button.set_color(esquema.baseline)
        self.baseline_check.setChecked(esquema.baseline is not None)
        self.baseline_button.setEnabled(esquema.baseline is not None)
        self.vary_colors.setChecked(esquema.vary_signal_colors)
        self.grid_ecg.setChecked(esquema.ecg_grid)
        self.grid_normal.setChecked(not esquema.ecg_grid)

        for boton in self.palette_buttons:
            self._fila_de_paleta.removeWidget(boton)
            boton.deleteLater()
        self.palette_buttons = []
        for posicion, color in enumerate(esquema.signal_palette):
            boton = ColorButton(color)
            boton.setFixedSize(28, 22)
            boton.on_chosen = lambda elegido, p=posicion: self._cambiar_paleta(p, elegido)
            # Antes del estiramiento del final, para que queden juntos.
            self._fila_de_paleta.insertWidget(posicion, boton)
            self.palette_buttons.append(boton)

    # -- Editor de anotaciones ---------------------------------------------------

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
        solapa = QWidget()
        formulario = QFormLayout(solapa)
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
            "Histograma en hora real, si el registro la informa"
        )
        self.open_clock_axis.toggled.connect(
            lambda activo: self._cambiar(
                self._prefs.with_changes(open_clock_axis=bool(activo))
            )
        )
        formulario.addRow("", self.open_clock_axis)
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

    # -- Tipografía ---------------------------------------------------------------

    def _armar_tipografia(self) -> QWidget:
        solapa = QWidget()
        formulario = QFormLayout(solapa)

        self.system_font = QCheckBox("Usar la tipografía del sistema")
        self.system_font.toggled.connect(self._cambiar_tipografia)
        formulario.addRow("", self.system_font)

        self.font_family = QFontComboBox()
        self.font_family.currentFontChanged.connect(
            lambda _fuente: self._cambiar_tipografia(self.system_font.isChecked())
        )
        formulario.addRow("Tipografía:", self.font_family)

        self.font_size = QSpinBox()
        self.font_size.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self.font_size.setSuffix(" pt")
        self.font_size.valueChanged.connect(
            lambda _valor: self._cambiar_tipografia(self.system_font.isChecked())
        )
        formulario.addRow("Tamaño:", self.font_size)

        self.font_preview = QLabel("Ventana 12 de 960 — C3 (EEG) — 100 µV")
        formulario.addRow("Muestra:", self.font_preview)
        return solapa

    def _cambiar_tipografia(self, del_sistema: bool) -> None:
        self.font_family.setEnabled(not del_sistema)
        self.font_size.setEnabled(not del_sistema)
        self._mostrar_muestra()
        if del_sistema:
            self._cambiar(self._prefs.with_changes(font_family=None, font_size=None))
            return
        self._cambiar(
            self._prefs.with_changes(
                font_family=self.font_family.currentFont().family(),
                font_size=self.font_size.value(),
            )
        )

    def _mostrar_muestra(self) -> None:
        fuente = QFont(self.font_family.currentFont())
        fuente.setPointSize(self.font_size.value())
        self.font_preview.setFont(fuente)

    def _reflejar_tipografia(self) -> None:
        del_sistema = self._prefs.font_family is None and self._prefs.font_size is None
        sistema = QFont()
        familia = self._prefs.font_family or sistema.family()
        tamano = self._prefs.font_size or max(sistema.pointSize(), MIN_FONT_SIZE)
        self.font_family.setCurrentFont(QFont(familia))
        self.font_size.setValue(tamano)
        self.system_font.setChecked(del_sistema)
        self.font_family.setEnabled(not del_sistema)
        self.font_size.setEnabled(not del_sistema)
        self._mostrar_muestra()
