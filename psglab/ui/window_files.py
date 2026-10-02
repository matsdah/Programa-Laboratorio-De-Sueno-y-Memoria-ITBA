"""La ventana y los archivos: abrir un registro e importar un scoring.

Abrir un registro —y los recientes— e importar un scoring, con la pregunta por
el trabajo sin exportar antes de soltar la sesión y al cerrar. **Exportar y esa
pregunta son de `work_guard`** desde el hito 79 (`ui/work_guard.py`); acá
quedan `export()` y los tres diálogos de exportar —el del scoring, el de
Anotaciones.txt y el de Informacion.txt—, que el menú, Ctrl+S y los scripts
piden por su nombre, y `closeEvent()`, que es de Qt.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Elegir cuál de los tres archivos de salida escribir se fue con `export()` a
`work_guard.py`, y con él el requisito que este módulo cubría.

Cubre del pliego: ningún ID; es infraestructura.
"""

from pathlib import Path

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog

from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.core.windows import count_windows
from psglab.core import recovery
from psglab.analysis.derivation import derive_montage
from psglab.exporters.scoring_formats import SCORING_FORMATS
from psglab.readers.base import IMPORT_WARNINGS_KEY, file_dialog_filter, read_recording
from psglab.readers.scoring_reader import read_scoring
from psglab.ui.menus import rebuild_recent_menu
from psglab.ui.shortcuts import install_shortcuts
from psglab.utils.errors import PsgLabError, UndeclaredNomenclatureError


class FilesMixin:
    """Lo de `MainWindow` que abre, importa y exporta, y lo que cuida el trabajo.
    """

    # -- Acciones del usuario -----------------------------------------------

    def open_recording(self, path: Path) -> None:
        """Abre un registro y prepara la sesión de trabajo, sin soltar el hilo.

        Es la vía de los scripts y de los tests, que necesitan la sesión en
        cuanto vuelve. **El usuario abre por `open_recording_in_background()`**
        —el diálogo, los recientes—, que lee en otro hilo.

        Muestra un error legible si el archivo no se puede leer, en vez de
        dejar caer una excepción: los usuarios no necesariamente tienen
        experiencia informática (pliego, sección 3).
        """
        try:
            with self._trabajando(f"Leyendo «{path.name}»"):
                sesion = self._leer_la_sesion(
                    path,
                    self._preferencias.nomenclature(),
                    self._preferencias.open_view_seconds,
                )
        except PsgLabError as error:
            self._show_error(error, f"abrir «{path.name}»")
            return
        self._tomar_la_sesion(sesion, path, recovery.fingerprint(sesion.recording))

    def open_recording_in_background(self, path: Path) -> None:
        """Abre un registro leyéndolo en otro hilo (hito 79).

        **Es como abre el usuario.** Una noche entera son varios segundos
        —4,3 s el registro de prueba, de los cuales 2,6 los tarda MNE—, y en
        el hilo de la interfaz la ventana quedaba congelada y el sistema la
        marcaba como «no responde» justo en lo primero que hace el usuario.
        Mientras lee, la ventana repinta, la barra de espera se mueve y **el
        registro anterior se puede seguir usando**: la pregunta por el trabajo
        sin exportar llega después de leer, así que cuenta también lo que se
        hizo mientras tanto.

        Tiene su propia tarea y no la del análisis: abrir mientras se ajusta
        una ICA se podía antes y se sigue pudiendo. Lo que no se puede es
        abrir dos a la vez: el segundo pedido se ignora y se dice.
        """
        if self._lectura.is_running():
            self.statusBar().showMessage(
                "Todavía se está abriendo el registro anterior; esperá a que termine.", 5000
            )
            return
        nomenclatura = self._preferencias.nomenclature()
        pagina = self._preferencias.open_view_seconds
        aviso = f"Leyendo «{path.name}»…"

        def terminar() -> None:
            if not self.analysis_controller.is_busy:
                self.analysis_controller.wait_bar.hide()
            if self.statusBar().currentMessage() == aviso:
                self.statusBar().clearMessage()
            for señal in (self._lectura.finished, self._lectura.failed, self._lectura.stopped):
                try:
                    señal.disconnect()
                except RuntimeError:
                    pass

        def listo(resultado: object) -> None:
            terminar()
            if (
                isinstance(resultado, tuple)
                and len(resultado) == 2
                and isinstance(resultado[0], Session)
                and isinstance(resultado[1], dict)
                and not self._lectura_descartada
            ):
                self._tomar_la_sesion(resultado[0], path, resultado[1])

        def fallo(error: object) -> None:
            terminar()
            if isinstance(error, PsgLabError) and not self._lectura_descartada:
                self._show_error(error, f"abrir «{path.name}»")

        self._lectura_descartada = False
        self._lectura.finished.connect(listo)
        self._lectura.failed.connect(fallo)
        self._lectura.stopped.connect(terminar)
        self.statusBar().showMessage(aviso)
        self.analysis_controller.wait_bar.show()
        self._lectura.start(lambda: self._leer_sesion_con_huella(path, nomenclatura, pagina))

    @staticmethod
    def _leer_sesion_con_huella(
        path: Path, nomenclature: Nomenclature, view_seconds: float
    ) -> tuple[Session, dict[str, object]]:
        """Lee la señal y calcula su huella completa en el hilo de apertura."""
        sesion = FilesMixin._leer_la_sesion(path, nomenclature, view_seconds)
        return sesion, recovery.fingerprint(sesion.recording)

    @staticmethod
    def _leer_la_sesion(path: Path, nomenclature: Nomenclature, view_seconds: float) -> Session:
        """Lee el archivo y arma su sesión. **No toca ningún widget**: corre en
        otro hilo cuando abre el usuario, así que las preferencias le llegan
        ya leídas.

        Raises:
            PsgLabError: si el archivo no se puede leer.
        """
        registro = read_recording(path)
        ventanas = count_windows(registro.n_samples, registro.sampling_rate)
        sesion = Session(
            registro,
            # La nomenclatura con que arranca un scoring nuevo. Uno importado
            # trae la suya y ésta no la pisa.
            Scoring(ventanas, nomenclature),
            AnnotationSet(),
        )
        # La página con que se abre. Se fija antes de dibujar para no dibujar
        # dos veces.
        sesion.set_viewport(sesion.viewport.with_span(view_seconds))
        return sesion

    def _tomar_la_sesion(
        self, sesion: Session, path: Path, source_identity: dict[str, object] | None = None
    ) -> None:
        """Pone en la ventana la sesión de un registro recién leído."""
        registro = sesion.recording

        # **Lo que se perdería con la sesión anterior, antes de soltarla**
        # (hito 33). Va después de leer y no antes: si el archivo nuevo no se
        # puede abrir, la sesión anterior sigue y no hay nada que preguntar.
        if not self.work_guard.can_discard(f"abrir «{path.name}»"):
            return

        # Las herramientas activas siguen guardando la sesión que recibieron
        # en `activate()`: si no se las suelta, la ocupación seguiría midiendo
        # sobre el registro anterior y el histograma dibujaría su scoring.
        self.tool_controller.deactivate_all()
        # La reproducción avanzaba sobre la página del registro anterior, y
        # `attach()` la detiene antes de tomar la sesión nueva.
        self.playback_controller.attach(sesion)

        self._session = sesion
        self.work_guard.attach(
            sesion,
            source_identity if source_identity is not None else recovery.fingerprint(registro),
        )
        # **El registro tal como se leyó.** Los análisis de la Parte 2 devuelven
        # un registro nuevo, y sin guardar éste un filtro mal elegido obligaría
        # a reabrir el archivo. Es la regla 1 de `analysis/` vista desde la
        # interfaz: el usuario tiene que poder volver atrás. Y la ICA del
        # registro anterior se olvida: es de otra señal y de otros canales.
        self.analysis_controller.attach(sesion)
        # Las herramientas se enteran solas de los cambios de ventana: es la
        # decisión del hito 6, y por eso acá no hay que acordarse de avisarles.
        self.tool_controller.attach(sesion)

        self._aplicar_colores_de_clase(sesion)
        self.signal_view.set_session(sesion)
        self._reiniciar_paneles_de_analisis()
        self.channel_selector.set_recording(registro)
        self.scoring_panel.set_nomenclature(sesion.scoring.nomenclature)
        install_shortcuts(self, sesion)
        self.tool_controller.activate_panel_tools()
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
        # **La copia de recuperación, al final** (hito 79): con el registro ya
        # dibujado y los avisos del archivo leídos, antes de que el usuario
        # haga nada. Si la hay, es porque la última vez se cerró sin decidir.
        if self.work_guard.offer_recovery(
            self._recovery_candidate,
            lambda candidato: self.analysis_controller.replace_recording(
                lambda _actual: candidato
            ),
            self.analysis_controller.restore_original,
        ):
            original = self.analysis_controller.original_recording
            if original is not None and sesion.recording is not original:
                self._mostrar_el_procesado(
                    sesion.recording,
                    "Se restauró el montaje derivado",
                    None,
                )
            self._al_recuperar_el_trabajo()

    def _recovery_candidate(self, copia: dict[str, object]) -> Recording | None:
        """Reconstruye, sin mutar la sesión, el montaje guardado en la copia."""
        derivaciones = copia.get("derivaciones", [])
        if not isinstance(derivaciones, list):
            raise PsgLabError("La copia de recuperación no se puede leer.")
        if not derivaciones:
            return None
        original = self.analysis_controller.original_recording
        if original is None:
            raise PsgLabError("No se pudo reconstruir el montaje de la copia.")
        try:
            if any(
                not isinstance(fila, list)
                or len(fila) != 4
                or any(not isinstance(valor, str) for valor in fila)
                for fila in derivaciones
            ):
                raise TypeError("La receta contiene filas inválidas.")
            pares = [(fila[0], fila[1]) for fila in derivaciones]
            nombres = [fila[2] for fila in derivaciones]
            clases = [ChannelKind[fila[3]] for fila in derivaciones]
            return derive_montage(
                original, pares, names=nombres, channel_kinds=clases
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise PsgLabError(
                "La copia de recuperación no se puede leer.", details=str(error)
            ) from error

    def _al_recuperar_el_trabajo(self) -> None:
        """Redibuja lo que depende del scoring y las anotaciones recuperados.

        La copia puede traer otra nomenclatura, así que cambian también los
        botones del panel y las teclas de las fases.
        """
        if self._session is None:
            return
        self.scoring_panel.set_nomenclature(self._session.scoring.nomenclature)
        install_shortcuts(self, self._session)
        self._reload_histogram()
        self.tool_controller.redraw_overlays()
        self.refresh()
        self.statusBar().showMessage(
            "Se recuperó el trabajo que no se había exportado.", 8000
        )

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
        self.open_recording_in_background(Path(path))

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
            if not self.work_guard.can_discard(f"importar «{path.name}»"):
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

        Lo hace `work_guard` (hito 79); queda acá porque es la vía para
        pedirlo desde un script, que es como se piden Anotaciones.txt e
        Informacion.txt desde que salieron del menú.

        Args:
            kind: "scoring", "annotations" o "information".
            path: el destino. Para el scoring, su extensión elige el formato.
        """
        self.work_guard.export(kind, path)

    # -- El trabajo sin exportar (hito 33) ---------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cerrar la ventana es cerrar el programa: antes, el scoring sin exportar.

        Hasta el hito 33 no había este método y la ventana se cerraba sin
        preguntar nada, con la noche scoreada adentro. Si el usuario cancela,
        la ventana queda abierta como estaba, reproducción incluida.
        """
        if not self.work_guard.can_discard("cerrar el programa"):
            event.ignore()
            return
        self.playback_controller.stop()
        # **Un registro que se estaba leyendo ya no se abre** (hito 79): el
        # usuario decidió cerrar, y tomarlo al terminar la espera volvería a
        # preguntar por el trabajo y cambiaría la sesión mientras se cierra.
        self._lectura_descartada = True
        # **Antes de soltar la sesión.** Un cálculo largo todavía leyendo el
        # registro se quedaría trabajando sobre memoria que ya nadie tiene.
        self.wait_for_background()
        super().closeEvent(event)

    def open_recording_dialog(self) -> None:
        """Ctrl+O. El filtro se arma solo desde los lectores registrados."""
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Abrir registro", self.work_guard.working_folder(), file_dialog_filter()
        )
        if ruta:
            self.open_recording_in_background(Path(ruta))

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
            self, "Importar scoring", self.work_guard.working_folder(), ";;".join(filtros)
        )
        if ruta:
            self.open_scoring(Path(ruta))

    def export_scoring_dialog(self, fmt: str = "txt") -> None:
        """Exporta el scoring en el formato pedido.

        Ctrl+S la llama sin argumento, así que el atajo exporta en `.txt`, que
        es el formato del pliego. Las cuatro entradas de «Archivo» pasan su
        extensión. El diálogo es de `work_guard`.
        """
        self.work_guard.export_dialog("scoring", fmt)

    def export_annotations_dialog(self) -> None:
        """Exporta Anotaciones.txt desde «Archivo» (V4_F). El diálogo es de
        `work_guard`, como el del scoring."""
        self.work_guard.export_dialog("annotations")

    def export_information_dialog(self) -> None:
        """Exporta Informacion.txt desde «Archivo» (V4_F), con el informe de
        sueño al final."""
        self.work_guard.export_dialog("information")
