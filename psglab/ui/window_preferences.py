"""La ventana y las preferencias: aplicar, guardar y la ventana de configuración.

El esquema de colores, el tamaño de letra, los colores de las clases de
anotación, la disposición de fábrica de los paneles y el diálogo que los
edita. Qué se recuerda entre sesiones lo decide `ui/preferences.py`.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: ningún ID; es infraestructura de la interfaz.
"""

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from psglab.core.annotations import AnnotationSet
from psglab.core.session import Session
from psglab.tools.amplitude_band import AmplitudeBandTool
from psglab.tools.magnifier import MagnifierTool
from psglab.tools.overview import OverviewTool
from psglab.ui import fonts, preferences, theme
from psglab.ui.icons import icon
from psglab.ui.menus import rebuild_recent_menu, rebuild_views_menu
from psglab.ui.settings_dialog import SettingsDialog
from psglab.utils.errors import PsgLabError


class PreferencesMixin:
    """Lo de `MainWindow` que aplica y guarda lo que elige el usuario.
    """

    def restore_default_layout(self) -> None:
        """Vuelve a la disposición de paneles con la que el programa abre.

        Es la salida cuando alguien arrastró un panel a un lugar del que no
        sabe cómo sacarlo, que con nueve paneles acoplables deja de ser
        hipotético. Es la misma vista de cada apertura: la señal y el selector
        de canales.
        """
        self.restoreState(self._layout_por_defecto)

    def apply_saved_preferences(self) -> None:
        """Aplica las preferencias que el usuario dejó la última vez.

        **Sólo la llama `create_main_window(saved_preferences=True)`**, que
        sólo llama `main.py`. Si la llamara el constructor, la suite de tests
        leería —y después escribiría— el archivo real de quien la corre, y
        dejaría de ser reproducible. Por el mismo motivo marca la ventana como
        la del usuario, que es la única que escribe el archivo.

        **La disposición de paneles no se restaura.** Hasta el hito 24 se
        guardaba al cerrar y volvía al abrir; desde entonces el programa abre
        siempre con la vista de fábrica, por decisión del usuario.

        No eleva: unas preferencias que no se pueden leer se descartan y la
        ventana abre con las de fábrica. **Pero lo dice** (hito 33): `load()`
        arma el mensaje para el investigador y hasta ahí nadie lo mostraba, así
        que un archivo roto se perdía sin aviso la primera vez que se cambiaba
        algo. El cartel sale en la vuelta siguiente del ciclo de eventos, con la
        ventana ya a la vista y no delante de una ventana que todavía no existe.
        """
        self._es_la_ventana_del_usuario = True
        try:
            guardadas = preferences.load()
        except PsgLabError as error:
            # En otra variable: Python borra `error` al salir del `except`, y el
            # cartel se arma recién en la vuelta siguiente del ciclo de eventos.
            aviso = error
            QTimer.singleShot(
                0, lambda: self._show_error(aviso, "leer la configuración guardada")
            )
            return
        # El esquema ya lo aplicó `create_application()`; lo demás de la
        # ventana de configuración se aplica acá, que es el único lugar donde
        # las preferencias del disco entran a la ventana.
        self._preferencias = guardadas
        self._aplicar_preferencias(guardadas)
        # Los recientes y las vistas salen de las preferencias: el menú se armó
        # con las de fábrica, antes de leer el archivo.
        rebuild_recent_menu(self)
        rebuild_views_menu(self)

    def set_color_scheme(self, scheme: theme.ColorScheme, remember: bool = True) -> None:
        """Cambia el esquema de color de todo el programa y lo deja repintado.

        `pg.setConfigOption()` sólo alcanza a los `PlotWidget` que se creen
        después, así que hay que recorrer los que ya existen. Se los busca con
        `findChildren()` y no con una lista escrita a mano **por la misma razón
        de siempre**: un panel nuevo se agregaría a la lista sólo si alguien se
        acuerda, y el síntoma de olvidarse sería un panel con el fondo del
        esquema anterior, que nadie va a asociar con este método.

        Args:
            scheme: el esquema a aplicar.
            remember: si se guarda como preferencia del usuario. Los tests lo
                apagan para no escribir en el archivo real de quien los corre,
                que los volvería dependientes de la máquina.

        No eleva: si las preferencias no se pueden guardar, el esquema se aplica
        igual y el problema sale como cartel. Perder la preferencia es molesto;
        no poder cambiar de colores porque el disco está lleno, absurdo.
        """
        theme.set_current(scheme)

        # La hoja de estilo alcanza a los widgets de Qt —menús, botones, el
        # árbol de canales, las tablas—, que los `PlotWidget` no tocan. Sin
        # esto, un esquema oscuro deja la ventana a dos colores.
        self.setStyleSheet(theme.stylesheet(scheme))

        for grafico in self.findChildren(pg.PlotWidget):
            grafico.setBackground(scheme.background)
        self.signal_view.apply_scheme()
        self.navigation.apply_scheme()
        self.open_button.setIcon(icon("abrir", theme.icon_ink(scheme)))
        # La señal de la Übersicht toma el color de su canal, que cambia con el
        # esquema: no alcanza con repintar.
        self._refrescar_contexto()
        self.overview_panel.update()
        self._redraw_histogram()
        # **La tilde del menú, cuando el esquema no vino del menú**: lo elige
        # también el archivo de preferencias al arrancar, y desde el hito 35 el
        # menú «Ver» es el único lugar donde se ve cuál está puesto.
        accion = self.acciones_de_esquema.get(scheme.name)
        if accion is not None and not accion.isChecked():
            accion.setChecked(True)

        self._preferencias = self._preferencias.with_scheme(scheme)
        if remember:
            self._guardar_preferencias()

    def _guardar_preferencias(self) -> None:
        """Escribe las preferencias vigentes, si esta ventana es la del usuario.

        **Sólo escribe si la ventana la abrió `main.py`**, que es lo que marca
        `apply_saved_preferences()`. Antes cada cambio de esquema leía el archivo,
        lo modificaba y lo volvía a escribir, sin mirar quién había creado la
        ventana: un test que eligiera un esquema desde el menú pisaba las
        preferencias reales de quien corría la suite.

        No eleva: si no se puede escribir, el cambio se aplica igual y el
        problema sale como cartel.
        """
        if not self._es_la_ventana_del_usuario:
            return
        try:
            preferences.save(self._preferencias)
        except PsgLabError as error:
            self._show_error(error, "guardar la configuración")

    @property
    def current_preferences(self) -> preferences.Preferences:
        """Las preferencias con las que está funcionando la ventana."""
        return self._preferencias

    def apply_preferences(self, prefs: preferences.Preferences) -> None:
        """Aplica unas preferencias nuevas a todo el programa y las recuerda.

        Es lo que llama la ventana de configuración en cada cambio. **Aplica
        todo sin reabrir el registro**: colores, grilla, tipografía, espectro y
        colores de las clases de evento se ven enseguida. Lo de la solapa
        «Otras» se guarda para el próximo registro que se abra.

        Muestra un cartel en vez de elevar si lo que llega no son preferencias:
        esto lo llama un panel, y una traza ahí es lo que el programa promete
        no mostrar nunca.
        """
        if not isinstance(prefs, preferences.Preferences):
            self._show_error(
                PsgLabError(
                    "No se pudo aplicar la configuración.",
                    details=f"Se recibió {type(prefs).__name__} en vez de preferencias.",
                ),
                "aplicar la configuración",
            )
            return
        esquema = prefs.scheme()
        if esquema != theme.current():
            self.set_color_scheme(esquema, remember=False)
        self._preferencias = prefs
        self._aplicar_preferencias(prefs)
        if self._session is not None:
            self._aplicar_colores_de_clase(self._session)
            self._repintar_anotaciones()
        self._guardar_preferencias()

    def show_settings_dialog(self) -> None:
        """Abre la ventana de configuración, mostrando lo que está vigente.

        Se arma una sola vez y se la vuelve a llenar en cada apertura: lo que
        muestra tiene que ser lo que el programa está usando, que puede haber
        cambiado desde otro lado desde la última vez que se abrió.

        **Es modal pero no bloquea**: se muestra con `show()` y no con
        `exec()`, así que los cambios se ven detrás mientras se eligen, que es
        lo que hace útil aplicar en el momento.
        """
        colores = self._colores_de_clase_vigentes()
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self._preferencias, colores, self)
            self.settings_dialog.setModal(True)
            self.settings_dialog.on_change = self.apply_preferences
            self.settings_dialog.on_error = lambda error: self._show_error(
                error, "aplicar la configuración"
            )
        else:
            self.settings_dialog.set_preferences(self._preferencias, colores)
        self.settings_dialog.show()
        self.settings_dialog.raise_()

    def _colores_de_clase_vigentes(self) -> dict[str, str]:
        """Las clases de evento que hay para configurar, con su color de hoy.

        Con un registro abierto son las de su sesión, incluidas las que creó el
        usuario; sin él, las de fábrica, con los colores que tendrían.
        """
        conjunto = (
            self._session.annotations if self._session is not None else AnnotationSet()
        )
        return {clase: conjunto.color_of(clase) for clase in conjunto.labels()}

    def _poner_la_tipografia(self, prefs: preferences.Preferences) -> QFont:
        """Pone la tipografía de la aplicación y la hace llegar a la ventana.

        **Separada de `_aplicar_preferencias()` desde el hito 78**, porque
        `MainWindow.__init__` la llama antes de construir nada: lo que se arma
        con la tipografía ya puesta nace con ella, que es lo único que funciona
        igual en todas las plataformas. Lo ya construido —cuando cambia desde
        Configuración, o con las preferencias guardadas— lo actualiza lo de
        abajo.

        Returns:
            La tipografía puesta, para los que no la siguen solos.
        """
        fuente = QFont(self._fuente_del_sistema)
        # **La familia ya no se elige** (hito 43): es la del programa y nada
        # más. Se pide sólo si Qt la tiene, porque un archivo que falta o que
        # no se pudo registrar dejaría a `setFamily()` sustituyendo en silencio
        # por lo que a Qt le parezca, que suele ser peor que la del sistema.
        elegida = fonts.available_family()
        if elegida is not None:
            fuente.setFamily(elegida)
        if prefs.font_size is not None:
            fuente.setPointSize(prefs.font_size)
        # **Sólo si cambió.** Cambiar la tipografía de la aplicación le avisa a
        # cada widget de cada ventana abierta, y la configuración se aplica
        # entera en cada cambio: sin esta guarda, tocar el color de una clase
        # le pediría al programa entero que volviera a maquetarse.
        if fuente == QApplication.font():
            return fuente
        QApplication.setFont(fuente)
        # **Y hacerla llegar a lo ya construido** (hito 78). Hasta ahí la
        # ventana quedaba con la tipografía del sistema —la barra de menú, la
        # de estado, los rótulos— con la aplicación en Plex, desde el hito 43;
        # lo encontró el CI de Linux, donde la del sistema no se parece. Son
        # dos huecos de Qt, medidos en Windows y en Linux:
        #
        # - el aviso de cambio de tipografía sólo se manda con el ciclo de
        #   eventos corriendo, y las preferencias se aplican antes de `exec()`;
        # - lo que está bajo una hoja de estilo no recibe ese aviso, a
        #   propósito, porque ahí manda la hoja: hay que volver a ponerla para
        #   que lo repula.
        #
        # Lo que tiene tipografía propia —los roles de `font_for()`— la
        # conserva. Con el ciclo corriendo, Qt ya manda el aviso y éste sobra
        # sin hacer daño.
        QApplication.sendEvent(self, QEvent(QEvent.Type.ApplicationFontChange))
        hoja = self.styleSheet()
        self.setStyleSheet("")
        self.setStyleSheet(hoja)
        return fuente

    def _aplicar_preferencias(self, prefs: preferences.Preferences) -> None:
        """Lo que se aplica enseguida y no depende de un registro abierto."""
        fuente = self._poner_la_tipografia(prefs)
        # Los nombres de canal son ítems de pyqtgraph, que no siguen a la
        # tipografía de la aplicación: hay que avisarles.
        self.signal_view.apply_font(fuente)
        self.psd_panel.set_log_power(prefs.psd_log_power)
        # V3_F de la Übersicht. `set_span()` estuvo sin ningún camino desde la
        # ventana hasta el hito 30: la cantidad sólo se cambiaba en `config.py`.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.set_span(prefs.overview_before, prefs.overview_after)
        # Hito 32: los tres `set_*` tampoco tenían ningún camino desde la ventana.
        banda = self._tools.get("amplitude_band")
        if isinstance(banda, AmplitudeBandTool):
            banda.set_height_uv(prefs.amplitude_band_uv)
        lupa = self._tools.get("magnifier")
        if isinstance(lupa, MagnifierTool):
            lupa.set_radius_seconds(prefs.magnifier_radius_seconds)
            lupa.set_zoom(prefs.magnifier_zoom)

    def _aplicar_colores_de_clase(self, sesion: Session) -> None:
        """Pone en la sesión los colores que el usuario eligió por clase.

        **Una clase con color guardado queda disponible en cualquier
        registro**, aunque ese registro todavía no la tenga: `add_label()` la
        registra si no existía. Es lo que el usuario espera de una clase que
        definió una vez; no cambia ningún archivo de salida, porque los
        exportadores escriben anotaciones y no clases.
        """
        for clase, color in self._preferencias.annotation_colors:
            try:
                sesion.annotations.add_label(clase, color)
            except PsgLabError as error:
                self._show_error(error, "aplicar los colores de las clases")
                return

    def _repintar_anotaciones(self) -> None:
        """Vuelve a dibujar lo que muestra el color de una clase."""
        #  le avisa a la ventana por su callback, que es el que
        # repinta el panel: no hace falta llamarlo a mano.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        # Las bandas llevan el color de su clase.
        self._redibujar_overlays()
