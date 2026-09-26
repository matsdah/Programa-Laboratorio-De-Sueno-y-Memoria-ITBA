"""La ventana y los archivos: abrir, importar, exportar y no perder trabajo.

Abrir un registro —y los recientes—, importar un scoring, exportar los tres
archivos de salida y el cartel del trabajo sin exportar al cerrar (hito 33).

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: V4_F de "Archivo de salida" (`export()` elige cuál de los
tres archivos escribir, aunque desde el hito 23 la ventana sólo ofrece el
scoring).
"""

from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox

from psglab.core.annotations import AnnotationSet
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.core.windows import count_windows
from psglab.exporters import DEFAULT_FILENAMES
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.information_txt import export_information
from psglab.exporters.scoring_formats import SCORING_FORMATS, export_scoring_as
from psglab.readers.base import IMPORT_WARNINGS_KEY, file_dialog_filter, read_recording
from psglab.readers.scoring_reader import read_scoring
from psglab.ui import theme
from psglab.ui.menus import rebuild_recent_menu
from psglab.ui.shortcuts import install_shortcuts
from psglab.utils.errors import PsgLabError, UndeclaredNomenclatureError


class FilesMixin:
    """Lo de `MainWindow` que abre, importa y exporta, y lo que cuida el trabajo.
    """

    # -- Acciones del usuario -----------------------------------------------

    def open_recording(self, path: Path) -> None:
        """Abre un registro y prepara la sesión de trabajo.

        Muestra un error legible si el archivo no se puede leer, en vez de
        dejar caer una excepción: los usuarios no necesariamente tienen
        experiencia informática (pliego, sección 3).

        **Avisa mientras lee.** Una noche entera son varios segundos —4,3 s el
        registro de prueba, de los cuales 2,6 los tarda MNE— y todo corre en el
        hilo de la interfaz, así que la ventana queda congelada. Sin cursor de
        espera ni mensaje, eso se lee como que el programa se colgó justo
        cuando el usuario hizo lo primero que hace.
        """
        try:
            with self._trabajando(f"Leyendo «{path.name}»"):
                registro = read_recording(path)
            ventanas = count_windows(registro.n_samples, registro.sampling_rate)
            sesion = Session(
                registro,
                # La nomenclatura con que arranca un scoring nuevo. Uno
                # importado trae la suya y ésta no la pisa.
                Scoring(ventanas, self._preferencias.nomenclature()),
                AnnotationSet(),
            )
            # La página con que se abre. Se fija antes de dibujar para no
            # dibujar dos veces.
            sesion.set_viewport(
                sesion.viewport.with_span(self._preferencias.open_view_seconds)
            )
        except PsgLabError as error:
            self._show_error(error, f"abrir «{path.name}»")
            return

        # **Lo que se perdería con la sesión anterior, antes de soltarla**
        # (hito 33). Va después de leer y no antes: si el archivo nuevo no se
        # puede abrir, la sesión anterior sigue y no hay nada que preguntar.
        if not self._puede_descartarse_el_trabajo(f"abrir «{path.name}»"):
            return

        # Las herramientas activas siguen guardando la sesión que recibieron
        # en `activate()`: si no se las suelta, la ocupación seguiría midiendo
        # sobre el registro anterior y el histograma dibujaría su scoring.
        self._deactivate_all_tools()
        # Y por el mismo motivo, la descomposición ICA del registro anterior: es
        # de otra señal y de otros canales.
        self._olvidar_ica()
        # La reproducción avanzaba sobre la página del registro anterior.
        self.playback.stop()

        self._session = sesion
        # **El registro tal como se leyó.** Los análisis de la Parte 2 devuelven
        # un registro nuevo, y sin guardar éste un filtro mal elegido obligaría
        # a reabrir el archivo. Es la regla 1 de `analysis/` vista desde la
        # interfaz: el usuario tiene que poder volver atrás.
        self._registro_original = registro
        self.accion_señal_original.setEnabled(False)
        # Las herramientas se enteran solas de los cambios de ventana: es la
        # decisión del hito 6, y por eso acá no hay que acordarse de avisarles.
        for herramienta in self._tools.values():
            sesion.add_window_listener(herramienta.on_window_changed)
            sesion.add_view_listener(herramienta.on_view_changed)
        # **Después de las herramientas**: la ocupación se reancla en su
        # `on_view_changed()`, y las bandas se comparan contra lo ya reanclado.
        sesion.add_view_listener(self._al_cambiar_la_pagina)

        self._aplicar_colores_de_clase(sesion)
        self.signal_view.set_session(sesion)
        self._reiniciar_paneles_de_analisis()
        self.channel_selector.set_recording(registro)
        self.scoring_panel.set_nomenclature(sesion.scoring.nomenclature)
        install_shortcuts(self, sesion)
        self._activate_panel_tools()
        # El eje del histograma en hora real sólo se puede pedir si el archivo
        # informó cuándo empezó: pedirlo igual sería un cartel de error cada
        # vez que se abre un registro sin hora, por una preferencia que el
        # usuario eligió para otros archivos.
        if self._preferencias.open_clock_axis and registro.start_time is not None:
            self.accion_eje_en_hora.setChecked(True)
        self.refresh()
        self._recordar_reciente(path)
        # **Lo que el lector pudo leer con reservas**, después de dibujar: el
        # registro ya está abierto y el cartel explica lo que se ve (hito 33).
        avisos = registro.metadata.get(IMPORT_WARNINGS_KEY)
        if avisos:
            self._mostrar_avisos_de_lectura([str(aviso) for aviso in avisos])

    def _recordar_reciente(self, path: Path) -> None:
        """Pone el registro recién abierto al frente de «Abrir reciente»."""
        try:
            ruta = str(Path(path).resolve())
        except OSError:
            ruta = str(path)
        self._preferencias = self._preferencias.with_recent_file(ruta)
        self._guardar_preferencias()
        rebuild_recent_menu(self)

    def open_recent_file(self, path: str) -> None:
        """Abre uno de «Abrir reciente».

        **Si ya no está, se lo saca de la lista** y se avisa: una entrada que
        falla cada vez que se elige no sirve de nada.
        """
        if not Path(path).exists():
            self._preferencias = self._preferencias.without_recent_file(path)
            self._guardar_preferencias()
            rebuild_recent_menu(self)
            self._show_error(
                PsgLabError(
                    f"«{Path(path).name}» ya no está donde se abrió la última vez, "
                    "así que se lo quitó de los recientes.",
                    details=f"No existe {path}.",
                ),
                f"abrir «{Path(path).name}»",
            )
            return
        self.open_recording(Path(path))

    def open_scoring(self, path: Path) -> None:
        """Importa un scoring existente sobre el registro abierto (V3_F).

        Acepta los cuatro formatos de `SCORING_FORMATS`. **Si el archivo no
        dice con qué nomenclatura se scoreó, se le pregunta al usuario** y se
        vuelve a leer con la que elija; si cancela, no se importa nada.

        **Y si el scoring que está en pantalla no se exportó, se pregunta antes
        de pisarlo**, con el mismo cartel que al cerrar o abrir otro registro:
        importar lo reemplaza entero.
        """
        if self._session is None:
            self._show_error(
                PsgLabError(
                    "Hay que abrir un registro antes de importarle un scoring.",
                    details="No hay ninguna sesión abierta.",
                ),
                "importar el scoring",
            )
            return
        inicio = self._session.recording.start_time
        try:
            try:
                scoring = read_scoring(path, self._session.n_windows, start_time=inicio)
            except UndeclaredNomenclatureError:
                elegida = self._elegir_nomenclatura(path)
                if elegida is None:
                    return
                scoring = read_scoring(
                    path, self._session.n_windows, elegida, start_time=inicio
                )
            # **Lo que se perdería, antes de pisarlo** (hito 33). Importar
            # reemplaza el scoring entero, así que es la misma pérdida que
            # abrir otro registro por otro camino, y se pregunta igual:
            # después de leer, porque un archivo que no se puede importar no
            # pisa nada. Nada de lo que hace el cartel eleva hacia afuera
            # —`export()` atrapa lo suyo—, así que vive adentro de este `try`
            # sin cambiarle el sentido.
            if not self._puede_descartarse_el_trabajo(f"importar «{path.name}»"):
                return
            # **Se sustituye adentro de la sesión, no se arma otra.** Importar
            # un scoring no es abrir otro registro: el usuario sigue parado en
            # su ventana, con sus canales y sus amplitudes, y las herramientas
            # ya activadas siguen apuntando a la sesión correcta. El motivo
            # completo está en `Session.set_scoring()`.
            self._session.set_scoring(scoring)
        except PsgLabError as error:
            self._show_error(error, "importar el scoring")
            return

        self.scoring_panel.set_nomenclature(scoring.nomenclature)
        self._reload_histogram()
        self.refresh()

    def export(self, kind: str, path: Path) -> None:
        """Exporta uno de los tres archivos de salida (V4_F).

        El diálogo de guardado propone el nombre de archivo que fija el pliego,
        tomándolo de `psglab.exporters.DEFAULT_FILENAMES`.

        **Del menú sólo se pide el scoring**: Anotaciones.txt e
        Informacion.txt salieron de ahí el 16 de septiembre de 2026, pero este
        método los sigue escribiendo, y es la vía para pedirlos desde un
        script. Anotaciones.txt tiene además una puerta más en la ventana
        desde el cierre del hito 33: el cartel del trabajo sin exportar, que
        ofrece guardarlas antes de perderlas.

        Args:
            kind: "scoring", "annotations" o "information".
            path: el destino. Para el scoring, su extensión elige el formato:
                `.txt`, `.csv`, `.edf` o `.xml`.
        """
        if self._session is None:
            return
        try:
            if kind == "scoring":
                export_scoring_as(
                    self._session.scoring, path, self._session.recording.start_time
                )
                # Después de escribir y no antes: si falló, el trabajo sigue sin
                # estar en ningún archivo y cerrar tiene que seguir preguntando.
                self._session.mark_scoring_exported()
            elif kind == "annotations":
                export_annotations(self._session.annotations, path)
                # Por el mismo motivo que el scoring: recién cuando se escribió.
                self._session.mark_annotations_exported()
            elif kind == "information":
                export_information(
                    self._session.recording,
                    self._session.scoring,
                    self._session.annotations,
                    path,
                )
            else:
                raise PsgLabError(
                    "No se pudo exportar: no se reconoce ese archivo de salida.",
                    details=f"kind = {kind!r}, se esperaba uno de {sorted(DEFAULT_FILENAMES)}.",
                )
        except PsgLabError as error:
            self._show_error(error, f"exportar «{path.name}»")
            return
        except OSError as error:
            # **El disco no es un `PsgLabError`.** Los exportadores validan lo
            # suyo y elevan errores del programa, pero la carpeta que eligió el
            # usuario puede no existir, estar llena o ser de sólo lectura, y eso
            # sale como `OSError` crudo. Sin esta rama atraviesa el `except` de
            # arriba y el investigador ve una traza de Python en vez de un
            # cartel. Lo encontró `tests/test_entrega.py` exportando a una
            # carpeta inexistente.
            self._show_error(
                PsgLabError(
                    f"No se pudo escribir «{path.name}». Revisá que la carpeta "
                    "exista y que tengas permiso para escribir en ella.",
                    details=f"{type(error).__name__}: {error}",
                ),
                f"exportar «{path.name}»",
            )
            return
        self.statusBar().showMessage(f"Se exportó {path.name}", 5000)

    # -- El trabajo sin exportar (hito 33) ---------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cerrar la ventana es cerrar el programa: antes, el scoring sin exportar.

        Hasta el hito 33 no había este método y la ventana se cerraba sin
        preguntar nada, con la noche scoreada adentro. Si el usuario cancela,
        la ventana queda abierta como estaba, reproducción incluida.
        """
        if not self._puede_descartarse_el_trabajo("cerrar el programa"):
            event.ignore()
            return
        self.playback.stop()
        # **Antes de soltar la sesión.** Un cálculo largo todavía leyendo el
        # registro se quedaría trabajando sobre memoria que ya nadie tiene.
        self.wait_for_background()
        super().closeEvent(event)

    def _lo_que_se_perderia(self) -> list[str]:
        """Qué archivos de salida tienen trabajo que no está en ningún lado.

        Devuelve claves de `export()`, en el orden en que se ofrecen: primero
        el scoring, que es el trabajo principal.
        """
        if self._session is None:
            return []
        en_juego: list[str] = []
        if self._session.has_unexported_scoring():
            en_juego.append("scoring")
        if self._session.has_unexported_annotations():
            en_juego.append("annotations")
        return en_juego

    def _puede_descartarse_el_trabajo(self, al_hacer: str) -> bool:
        """Si se puede seguir sin perder trabajo que el usuario no exportó.

        **El programa no autoguarda**, por decisión del usuario en el hito 33:
        guardar a escondidas obliga a elegir dónde y en qué formato por él. Así
        que cuando algo va a soltar la sesión —cerrar, abrir otro registro,
        importar un scoring encima— y quedó trabajo fuera de todo archivo, se
        pregunta con tres salidas:

        - **Exportar…** abre el diálogo de guardado de **cada cosa en juego** y
          sigue sólo si no quedó nada sin exportar. Cancelar un diálogo, o que
          escribir falle, deja todo como estaba.
        - **Descartar** sigue y lo pierde, que es lo que el usuario eligió.
        - **Cancelar**, o cerrar el cartel, no hace nada.

        **Las anotaciones cuentan desde el cierre del hito 33.** El cartel
        miraba sólo el scoring, que es lo único que la ventana ofrece exportar
        desde el menú, así que una sesión con eventos anotados y ninguna fase
        puesta se cerraba sin preguntar. Que Anotaciones.txt no esté en el menú
        —decisión del hito 23, sin confirmar con el cliente— no puede
        significar que se pierda en silencio: el cartel las exporta, con el
        mismo diálogo que el scoring, porque avisar de una pérdida sin ofrecer
        cómo evitarla es peor que no avisar.

        Args:
            al_hacer: lo que se está por hacer, para el texto del cartel:
                "cerrar el programa", "abrir «noche.edf»",
                "importar «Scoring.txt»".
        """
        en_juego = self._lo_que_se_perderia()
        if not en_juego:
            return True
        respuesta = self._preguntar_por_el_trabajo(al_hacer, en_juego)
        if respuesta == "descartar":
            return True
        if respuesta == "exportar":
            for que in en_juego:
                self._export_dialog(que)
            return not self._lo_que_se_perderia()
        return False

    def _preguntar_por_el_trabajo(self, al_hacer: str, en_juego: list[str]) -> str:
        """Muestra el cartel y devuelve "exportar", "descartar" o "cancelar".

        Está aparte de la decisión para que los tests puedan contestarlo: el
        cartel es modal y, sin nadie que lo cierre, colgaría la suite.

        **Exportar es el botón por omisión y Escape es cancelar**: un Enter
        apurado no puede costar la noche, y apretar Escape es arrepentirse de
        cerrar, no de haber scoreado.

        **El texto nombra lo que está en juego**, que no siempre es lo mismo:
        decir "el scoring" sobre una sesión que sólo tiene anotaciones manda a
        buscar al lugar equivocado lo que se va a perder.
        """
        nombre = self._session.recording.file_path.name if self._session else ""
        anotaciones = len(self._session.annotations.all()) if self._session else 0
        que_hay = {
            ("scoring",): "El scoring",
            ("annotations",): f"Las {anotaciones} anotaciones",
            ("scoring", "annotations"): f"El scoring y las {anotaciones} anotaciones",
        }[tuple(en_juego)]
        cartel = QMessageBox(self)
        cartel.setIcon(QMessageBox.Icon.Warning)
        cartel.setWindowTitle("Trabajo sin exportar")
        cartel.setText(f"{que_hay} de «{nombre}» no se exportaron.")
        cartel.setInformativeText(
            f"Si no los exportás, se pierden al {al_hacer}. ¿Exportarlos antes?"
        )
        exportar = cartel.addButton("Exportar…", QMessageBox.ButtonRole.AcceptRole)
        # Lo que el cartel recomienda, relleno del acento (hito 55).
        exportar.setProperty(theme.PRIMARIO_PROPERTY, True)
        descartar = cartel.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        # **El rol no alcanza para que se vea distinto.** `DestructiveRole` le
        # dice a Qt dónde ubicar el botón y con qué tecla responde, no de qué
        # color pintarlo: en Windows sale idéntico a «Cancelar». La tinta la
        # pone el esquema por esta propiedad. La llevan sólo los dos controles
        # que pierden trabajo: éste y «Borrar» una anotación (`_confirmar()`).
        descartar.setProperty(theme.DESTRUCTIVO_PROPERTY, True)
        cancelar = cartel.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        cartel.setDefaultButton(exportar)
        cartel.setEscapeButton(cancelar)
        cartel.exec()
        elegido = cartel.clickedButton()
        if elegido is exportar:
            return "exportar"
        if elegido is descartar:
            return "descartar"
        return "cancelar"

    def open_recording_dialog(self) -> None:
        """Ctrl+O. El filtro se arma solo desde los lectores registrados."""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir registro", "", file_dialog_filter()
        )
        if ruta:
            self.open_recording(Path(ruta))

    def open_scoring_dialog(self) -> None:
        """El scoring entra por su **propia** opción, decidido en el hito 4.

        No es un formato más: `read_scoring()` no produce un `Recording`, así
        que no pasa por el despacho de `read_recording()`.

        El filtro se arma recorriendo `SCORING_FORMATS`: el primero junta los
        cuatro, que es lo que se busca casi siempre.
        """
        patrones = " ".join(f"*.{extension}" for extension in SCORING_FORMATS)
        filtros = [f"Scoring ({patrones})"]
        filtros += [f"{nombre} (*.{ext})" for ext, nombre in SCORING_FORMATS.items()]
        filtros.append("Todos los archivos (*)")
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar scoring", "", ";;".join(filtros)
        )
        if ruta:
            self.open_scoring(Path(ruta))

    def export_scoring_dialog(self, fmt: str = "txt") -> None:
        """Exporta el scoring en el formato pedido.

        Ctrl+S la llama sin argumento, así que el atajo exporta en `.txt`, que
        es el formato del pliego. Las cuatro entradas de «Scoring» pasan su
        extensión.
        """
        self._export_dialog("scoring", fmt)

    # -- Ayudantes privados -------------------------------------------------

    def _export_dialog(self, kind: str, fmt: str = "txt") -> None:
        """Pregunta dónde guardar y exporta.

        Propone el nombre del pliego con la extensión del formato elegido.
        **Si el usuario escribe un nombre sin esa extensión, se le agrega**: el
        diálogo de Qt no lo hace en todas las plataformas, y sin ella
        `export()` no sabría en qué formato escribir. Se agrega en vez de
        reemplazar para no convertir «noche.v2» en «noche.csv».
        """
        propuesto = Path(DEFAULT_FILENAMES[kind]).with_suffix(f".{fmt}").name
        filtro = f"{SCORING_FORMATS.get(fmt, fmt.upper())} (*.{fmt})"
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", propuesto, filtro)
        if not ruta:
            return
        destino = Path(ruta)
        if destino.suffix.lower() != f".{fmt}":
            destino = destino.with_name(f"{destino.name}.{fmt}")
            # **La extensión se agrega después de que el diálogo confirmó**, así
            # que el archivo que se va a pisar no es el que el usuario vio: con
            # «noche» escrito a mano, el diálogo pregunta por «noche» y el que
            # se escribe es «noche.txt». Se pregunta de nuevo (hito 33).
            if destino.exists():
                if not self._confirmar(
                    "Reemplazar el archivo",
                    f"«{destino.name}» ya existe. ¿Reemplazarlo?",
                    "Reemplazar",
                    informativo="Se pierde lo que tenía.",
                ):
                    return
        self.export(kind, destino)
