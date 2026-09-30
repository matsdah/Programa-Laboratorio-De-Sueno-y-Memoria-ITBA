"""El trabajo del investigador: exportarlo y no perderlo.

Cuatro cosas que van juntas porque las tres últimas cuidan lo mismo que la
primera escribe:

- **Exportar** los tres archivos de salida, con su diálogo de guardado, que
  arranca en la carpeta del registro y propone el nombre del pliego.
- **El trabajo sin exportar** (hito 33): antes de soltar la sesión —cerrar,
  abrir otro registro, importar un scoring encima— se pregunta si hay scoring
  o anotaciones que no están en ningún archivo, y se ofrece exportarlos.
- **La copia de recuperación** (hito 79): mientras haya trabajo sin exportar,
  cada `SEGUNDOS_ENTRE_COPIAS` se deja una copia en el perfil del usuario; al
  reabrir el mismo registro después de un cierre inesperado, se ofrece volver
  a ella. Ver «La copia de recuperación», más abajo.
- **Deshacer y rehacer** (hito 79): el historial de la sesión, que es
  `core/history.py`. La ventana llama a `record()` después de cada cambio, y
  `history` es de donde deshace y rehace.

**Es una pieza con estado propio** (hito 79). Hasta ahí era la mitad del mixin
`window_files.py`, que compartía con los demás el estado de la ventana. La
ventana lo guarda en `work_guard`, le pregunta `can_discard()` antes de soltar
la sesión, y conserva `export()` y `export_scoring_dialog()` porque los piden
el menú, Ctrl+S y los scripts por su nombre. Lo que es de ella le llega por
señales o por lo que le pasa al construirlo:

- `failed`: no se pudo exportar. El cartel es de la ventana.
- `confirm`: la pregunta de sí o no de la ventana, para reemplazar un archivo.

## La copia de recuperación

**El programa no autoguarda**, por decisión del usuario en el hito 33: guardar
a escondidas obliga a elegir dónde y en qué formato por él. La copia que el
usuario decidió el 26 de septiembre de 2026 no es un autoguardado: no es un
archivo de salida, no aparece en ninguna carpeta del usuario y no elige ningún
formato. Qué guarda y cómo se vuelve a ella es de `core/recovery.py`; acá se
decide cuándo:

- **Se escribe** cada `SEGUNDOS_ENTRE_COPIAS`, sólo si hay trabajo sin
  exportar y cambió algo desde la anterior. Es lo más que se pierde con un
  corte de luz.
- **Se borra** cuando ya no hace falta: al exportar todo, y cada vez que
  `can_discard()` deja seguir —cerrar normalmente, abrir otro registro,
  importar un scoring encima—, porque ahí el usuario ya decidió qué hacer con
  su trabajo. Lo que sobrevive es lo de un cierre que nadie decidió.
- **Se ofrece** al abrir un registro que tiene una copia, con `offer_recovery()`.
  Si el usuario la descarta, se borra: no se vuelve a preguntar.
- **Se aparta sin destruirla** si es de una versión anterior, no coincide con
  la señal original o falla la recuperación. Así no se aplica a otra noche ni
  se pierde la única copia por un error.

**Sólo la ventana del usuario la escribe** (`enable_recovery()`, que llama
`apply_saved_preferences()`): la de los tests no escribe en el perfil de quien
corre la suite, por la misma regla que las preferencias.

Se testea sin `MainWindow`, en `tests/test_work_guard.py`.

Cubre del pliego: V4_F de "Archivo de salida" (`export()` elige cuál de los
tres archivos escribir, aunque desde el hito 23 la ventana sólo ofrece el
scoring).
"""

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QStatusBar, QWidget

from psglab.core import recovery
from psglab.core.history import History
from psglab.core.recording import Recording
from psglab.core.session import Session
from psglab.exporters import DEFAULT_FILENAMES
from psglab.exporters.atomic import write_text_atomically
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.information_txt import export_information
from psglab.exporters.scoring_formats import SCORING_FORMATS, export_scoring_as
from psglab.ui import theme
from psglab.utils.errors import PsgLabError

#: La pregunta de sí o no de la ventana: título, pregunta, qué dice el botón
#: que acepta y el texto de abajo. Ver `MainWindow._confirmar()`.
Confirmar = Callable[[str, str, str, str], bool]

#: Cada cuántos segundos se escribe la copia de recuperación, si cambió algo.
#: **Es lo más que se pierde con un corte de luz.** Escribirla cuesta unos
#: milisegundos: son las fases de una noche y sus anotaciones, en texto.
SEGUNDOS_ENTRE_COPIAS: int = 10

#: La carpeta de las copias, adentro de la del perfil.
CARPETA_DE_RECUPERACION: str = "recuperacion"


class WorkGuard(QObject):
    """Exporta el trabajo y pregunta antes de perderlo."""

    #: No se pudo exportar: el error y qué se intentaba, como lo espera
    #: `MainWindow._show_error()`.
    failed = Signal(object, object)

    def __init__(
        self,
        window: QWidget,
        status_bar: QStatusBar,
        confirm: Confirmar,
        last_recent: Callable[[], str | None],
    ) -> None:
        """Queda colgado de la ventana, sin registro todavía.

        Args:
            window: la ventana, que es la dueña de los carteles y los
                diálogos que se abren desde acá, y el padre de este objeto.
            status_bar: donde se dice que se exportó algo.
            confirm: la pregunta de sí o no de la ventana.
            last_recent: el último registro que se abrió, o None. Es de dónde
                arrancan los diálogos cuando no hay un registro abierto.
        """
        super().__init__(window)
        self._ventana = window
        self._barra_de_estado = status_bar
        self._confirmar = confirm
        self._ultimo_reciente = last_recent
        self._session: Session | None = None
        self._source_identity: dict[str, object] | None = None
        self._preserved_path: Path | None = None
        self._preserved_reason: str | None = None
        self._historial: History | None = None
        #: Dónde van las copias, o None si esta ventana no las escribe.
        self._carpeta: Path | None = None
        #: El texto de la última copia escrita, para no reescribir lo mismo.
        self._ultima_copia: str | None = None
        #: Si ya se avisó que la copia no se pudo escribir: una vez alcanza.
        self._avisado = False
        self._pausado = False
        self._reloj = QTimer(self)
        self._reloj.setInterval(SEGUNDOS_ENTRE_COPIAS * 1000)
        self._reloj.timeout.connect(self.save_recovery)

    def attach(self, session: Session, source_identity: dict[str, object] | None = None) -> None:
        """Toma la sesión de un registro recién abierto.

        Hay que preguntar `can_discard()` antes, sobre la anterior: después ya
        no hay a quién preguntarle. La copia que tuviera el registro nuevo se
        ofrece aparte, con `offer_recovery()`, cuando la ventana ya lo dibujó.
        """
        self._session = session
        self._pausado = False
        # La ventana que lee en segundo plano pasa la huella calculada allí.
        # El argumento opcional conserva el contrato para clientes de prueba y
        # aperturas sin hilo.
        self._source_identity = (
            source_identity
            if source_identity is not None
            else recovery.fingerprint(session.recording)
        )
        self._ultima_copia = None
        # Deshacer no cruza de un registro a otro: el historial empieza acá.
        self._historial = History(session)

    @property
    def history(self) -> History | None:
        """Lo que se puede deshacer y rehacer del registro abierto, o None."""
        return self._historial

    def record(self) -> None:
        """Guarda en el historial cómo está el trabajo, si cambió.

        La ventana la llama después de cualquier cambio; si nada cambió no se
        guarda nada, así que llamarla de más no cuesta un paso de deshacer.
        """
        if self._historial is not None:
            self._historial.record()

    # -- Exportar -----------------------------------------------------------

    def export(self, kind: str, path: Path) -> bool:
        """Exporta uno de los tres archivos de salida (V4_F).

        Los tres se piden desde «Archivo»; Anotaciones.txt e Informacion.txt
        volvieron ahí en el hito 79. Anotaciones.txt tiene además otra
        puerta desde el hito 33: el cartel del trabajo sin exportar, que
        ofrece guardarlas antes de perderlas.

        Args:
            kind: "scoring", "annotations" o "information".
            path: el destino. Para el scoring, su extensión elige el formato:
                `.txt`, `.csv`, `.edf` o `.xml`.

        Returns:
            Si se escribió. Lo que falló sale por `failed`.
        """
        if self._session is None:
            return False
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
            self.failed.emit(error, f"exportar «{path.name}»")
            return False
        except OSError as error:
            # **El disco no es un `PsgLabError`.** Los exportadores validan lo
            # suyo y elevan errores del programa, pero la carpeta que eligió el
            # usuario puede no existir, estar llena o ser de sólo lectura, y eso
            # sale como `OSError` crudo. Sin esta rama atraviesa el `except` de
            # arriba y el investigador ve una traza de Python en vez de un
            # cartel. Lo encontró `tests/test_entrega.py` exportando a una
            # carpeta inexistente.
            self.failed.emit(
                PsgLabError(
                    f"No se pudo escribir «{path.name}». Revisá que la carpeta "
                    "exista y que tengas permiso para escribir en ella.",
                    details=f"{type(error).__name__}: {error}",
                ),
                f"exportar «{path.name}»",
            )
            return False
        self._barra_de_estado.showMessage(f"Se exportó {path.name}", 5000)
        return True

    def export_dialog(self, kind: str, fmt: str = "txt") -> None:
        """Pregunta dónde guardar y exporta.

        Propone el nombre del pliego con la extensión del formato elegido.
        **Si el usuario escribe un nombre sin esa extensión, se le agrega**: el
        diálogo de Qt no lo hace en todas las plataformas, y sin ella
        `export()` no sabría en qué formato escribir. Se agrega en vez de
        reemplazar para no convertir «noche.v2» en «noche.csv».
        """
        propuesto = Path(DEFAULT_FILENAMES[kind]).with_suffix(f".{fmt}").name
        carpeta = self.working_folder()
        if carpeta:
            propuesto = str(Path(carpeta) / propuesto)
        filtro = f"{SCORING_FORMATS.get(fmt, fmt.upper())} (*.{fmt})"
        ruta, _ = QFileDialog.getSaveFileName(self._ventana, "Exportar", propuesto, filtro)
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
                    "Se pierde lo que tenía.",
                ):
                    return
        self.export(kind, destino)

    def working_folder(self) -> str:
        """Dónde arrancan los diálogos de abrir, importar y exportar (hito 79).

        **La carpeta del registro abierto**, que es donde suelen estar su
        scoring y donde conviene dejar lo que se exporta. Sin registro, la del
        último que se abrió. Arrancaban en la carpeta desde donde se lanzó el
        programa, y como el nombre propuesto es siempre el del pliego
        —`Scoring.txt`—, dos participantes exportados sin mirar terminaban en
        la misma carpeta, uno encima del otro.

        Returns:
            La carpeta, o `""` —la que elija el sistema— si ninguna existe.
        """
        candidatas: list[Path] = []
        if self._session is not None:
            candidatas.append(self._session.recording.file_path.parent)
        ultimo = self._ultimo_reciente()
        if ultimo:
            candidatas.append(Path(ultimo).parent)
        for carpeta in candidatas:
            if carpeta.is_dir():
                return str(carpeta)
        return ""

    # -- El trabajo sin exportar (hito 33) ---------------------------------

    def unexported(self) -> list[str]:
        """Qué archivos de salida tienen trabajo que no está en ningún lado.

        Devuelve claves de `export()`, en el orden en que se ofrecen: primero
        el scoring, que es el trabajo principal. La regla de qué cuenta es de
        `Session`.
        """
        if self._session is None:
            return []
        en_juego: list[str] = []
        if self._session.has_unexported_scoring():
            en_juego.append("scoring")
        if self._session.has_unexported_annotations():
            en_juego.append("annotations")
        return en_juego

    def can_discard(self, doing: str) -> bool:
        """Si se puede seguir sin perder trabajo que el usuario no exportó.

        Cuando algo va a soltar la sesión y quedó trabajo fuera de todo
        archivo, se pregunta con tres salidas:

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
            doing: lo que se está por hacer, para el texto del cartel:
                "cerrar el programa", "abrir «noche.edf»",
                "importar «Scoring.txt»".
        """
        en_juego = self.unexported()
        if en_juego:
            respuesta = self.ask(doing, en_juego)
            if respuesta == "exportar":
                for que in en_juego:
                    self.export_dialog(que)
                if self.unexported():
                    return False
            elif respuesta != "descartar":
                return False
        # **El usuario ya decidió qué hacer con su trabajo**, así que la copia
        # de recuperación sobra: la que sobrevive es la de un cierre que nadie
        # decidió.
        self.discard_recovery()
        return True

    def ask(self, doing: str, at_stake: list[str]) -> str:
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
        }[tuple(at_stake)]
        cartel = QMessageBox(self._ventana)
        cartel.setIcon(QMessageBox.Icon.Warning)
        cartel.setWindowTitle("Trabajo sin exportar")
        cartel.setText(f"{que_hay} de «{nombre}» no se exportaron.")
        cartel.setInformativeText(
            f"Si no los exportás, se pierden al {doing}. ¿Exportarlos antes?"
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

    # -- La copia de recuperación (hito 79) ---------------------------------

    def enable_recovery(self, folder: Path) -> None:
        """Empieza a escribir copias de recuperación en esa carpeta.

        **Sólo para la ventana del usuario.** La llama
        `apply_saved_preferences()`, que sólo llama `main.py`: la ventana de
        los tests no escribe en el perfil de quien corre la suite.
        """
        self._carpeta = folder
        self._reloj.start()

    @property
    def source_identity(self) -> dict[str, object] | None:
        """Huella completa del registro original, calculada al abrirlo."""
        return self._source_identity

    def pause_recovery(self) -> None:
        """Suspende el reloj mientras un diálogo modal interrumpe el trabajo."""
        self._pausado = True
        self._reloj.stop()

    def resume_recovery(self) -> None:
        """Reanuda el reloj después del diálogo."""
        self._pausado = False
        if self._carpeta is not None:
            self._reloj.start()

    def recovery_path(self) -> Path | None:
        """El archivo de la copia del registro abierto, o None si no hay.

        Uno por registro, nombrado por un resumen de su ruta: el nombre del
        archivo solo no alcanza, porque dos noches de dos participantes suelen
        llamarse igual en carpetas distintas. Que la copia sea de ese registro
        lo confirma después `recovery.matches()`.
        """
        if self._carpeta is None or self._session is None:
            return None
        ruta = self._session.recording.file_path
        try:
            ruta = ruta.resolve()
        except OSError:
            pass
        resumen = hashlib.sha256(str(ruta).encode("utf-8")).hexdigest()[:16]
        return self._carpeta / f"{resumen}.json"

    def save_recovery(self) -> None:
        """Escribe la copia si hay trabajo sin exportar y cambió algo.

        La llama el reloj. **Sin trabajo en juego, la borra**: lo que se
        exportó ya está a salvo en su archivo.

        **Se escribe entera en un archivo aparte y después se renombra**, que
        es una operación de un paso: un corte de luz en el medio deja la copia
        anterior, no una a medias.

        Si el disco falla no se interrumpe el scoring con un cartel cada diez
        segundos: se avisa una vez en la barra de estado.
        """
        ruta = self.recovery_path()
        if ruta is None or self._session is None or self._pausado:
            return
        if self._preserved_path == ruta and ruta.exists():
            self._preserve_recovery(ruta, self._preserved_reason or "invalid")
            if self._preserved_path == ruta and ruta.exists():
                return
        if not self.unexported():
            self.discard_recovery()
            return
        if self._source_identity is None:
            return
        texto = json.dumps(
            recovery.snapshot(self._session, self._source_identity), ensure_ascii=False
        )
        if texto == self._ultima_copia:
            return
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            write_text_atomically(ruta, texto)
        except OSError:
            if not self._avisado:
                self._barra_de_estado.showMessage(
                    "No se pudo guardar la copia de recuperación en el perfil.", 8000
                )
                self._avisado = True
            return
        self._ultima_copia = texto

    def discard_recovery(self) -> None:
        """Borra la copia del registro abierto, si hay."""
        self._ultima_copia = None
        ruta = self.recovery_path()
        if ruta is None:
            return
        if self._preserved_path == ruta and ruta.exists():
            self._preserve_recovery(ruta, self._preserved_reason or "invalid")
            if self._preserved_path == ruta and ruta.exists():
                return
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            pass

    def offer_recovery(
        self,
        prepare_recording: Callable[[dict[str, object]], Recording | None] | None = None,
        apply_recording: Callable[[Recording], object] | None = None,
        rollback_recording: Callable[[], object] | None = None,
    ) -> bool:
        """Si el registro abierto tiene una copia, ofrece volver a ella.

        Se llama al abrir, con el registro ya dibujado y antes de que el
        usuario haga nada: `recovery.restore()` sólo acepta una sesión sin
        trabajo. Una copia que no se puede leer, que es de otro registro o que
        no trae nada se aparta para conservarla. Si el investigador elige
        «Descartar», sí se borra.

        Returns:
            Si se recuperó el trabajo. La ventana tiene que redibujar lo que
            depende del scoring y las anotaciones.
        """
        self.pause_recovery()
        try:
            return self._offer_recovery_paused(
                prepare_recording, apply_recording, rollback_recording
            )
        finally:
            self.resume_recovery()

    def _offer_recovery_paused(
        self,
        prepare_recording: Callable[[dict[str, object]], Recording | None] | None,
        apply_recording: Callable[[Recording], object] | None,
        rollback_recording: Callable[[], object] | None,
    ) -> bool:
        ruta = self.recovery_path()
        if ruta is None or self._session is None or not ruta.exists():
            return False
        try:
            copia = json.loads(ruta.read_text(encoding="utf-8"))
            escrita = datetime.fromtimestamp(ruta.stat().st_mtime)
            ventanas, anotaciones = recovery.summary(copia)
        except (OSError, ValueError, PsgLabError):
            self._preserve_recovery(ruta, "invalid")
            return False
        if self._source_identity is None or not recovery.matches(copia, self._source_identity):
            self._preserve_recovery(ruta, "mismatch")
            return False
        if not (ventanas or anotaciones):
            self._preserve_recovery(ruta, "empty")
            return False
        if not self.ask_recovery(escrita, ventanas, anotaciones):
            self.discard_recovery()
            return False
        previo = self._session.recording
        try:
            candidate = prepare_recording(copia) if prepare_recording is not None else None
            if candidate is not None:
                recovery.preflight(
                    self._session, copia, self._source_identity, recording=candidate
                )
                if apply_recording is None:
                    self._session.set_recording(candidate)
                else:
                    apply_recording(candidate)
            recovery.restore(self._session, copia, self._source_identity)
        except Exception as error:
            # Guardar primero la única copia: incluso volver al registro
            # original puede fallar, y el reloj se reanuda al salir.
            self._preserve_recovery(ruta, "restore-failed")
            rollback_error: Exception | None = None
            if self._session.recording is not previo:
                try:
                    if rollback_recording is None:
                        self._session.set_recording(previo)
                    else:
                        rollback_recording()
                except Exception as fallo:
                    rollback_error = fallo
            if rollback_error is not None:
                mostrado = PsgLabError(
                    "No se pudo recuperar el trabajo ni volver a la señal original. "
                    "La copia se conservó en el perfil.",
                    details=(
                        f"Recuperación: {type(error).__name__}: {error}; "
                        f"reversión: {type(rollback_error).__name__}: {rollback_error}"
                    ),
                )
            elif isinstance(error, PsgLabError):
                mostrado = error
            else:
                mostrado = PsgLabError(
                    "No se pudo recuperar el trabajo.",
                    details=f"{type(error).__name__}: {error}",
                )
            self.failed.emit(mostrado, "recuperar el trabajo")
            return False
        # **Lo recuperado no se deshace**: no es un cambio de esta sesión, y
        # deshacerlo sería perder lo que se acaba de recuperar.
        if self._historial is not None:
            self._historial.reset()
        return True

    def _preserve_recovery(self, path: Path, reason: str) -> None:
        """Aparta una copia que no se puede usar sin destruir la evidencia."""
        if not path.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = path.with_name(f"{path.stem}.{reason}-{stamp}{path.suffix}")
        ordinal = 1
        while target.exists():
            target = path.with_name(
                f"{path.stem}.{reason}-{stamp}-{ordinal}{path.suffix}"
            )
            ordinal += 1
        try:
            path.replace(target)
            self._preserved_path = None
            self._preserved_reason = None
        except OSError:
            # Si ni siquiera se puede renombrar, mantener el original es mejor
            # que intentar borrarlo.
            self._preserved_path = path
            self._preserved_reason = reason

    def ask_recovery(self, written: datetime, windows: int, annotations: int) -> bool:
        """Pregunta si se recupera la copia. Devuelve si el usuario aceptó.

        Aparte, como `ask()`, para que los tests lo contesten: es modal.

        **Recuperar es el botón por omisión**: es lo que se quiere casi
        siempre, y un Enter apurado no puede costar la noche. Descartar la
        borra, y el texto lo dice.
        """
        nombre = self._session.recording.file_path.name if self._session else ""
        partes = []
        if windows:
            trabajo = "ventana con trabajo" if windows == 1 else "ventanas con trabajo"
            partes.append(f"{windows} {trabajo}")
        if annotations:
            anotadas = "anotación" if annotations == 1 else "anotaciones"
            partes.append(f"{annotations} {anotadas}")
        cartel = QMessageBox(self._ventana)
        cartel.setIcon(QMessageBox.Icon.Question)
        cartel.setWindowTitle("Recuperar el trabajo")
        cartel.setText(f"«{nombre}» se cerró la última vez sin exportar su trabajo.")
        cartel.setInformativeText(
            f"Hay una copia del {written:%d/%m a las %H:%M} con "
            f"{' y '.join(partes)}. ¿Recuperarla? Si la descartás, se borra. "
            "Los filtros, la ICA y la re-referencia no se vuelven a aplicar."
        )
        recuperar = cartel.addButton("Recuperar", QMessageBox.ButtonRole.AcceptRole)
        recuperar.setProperty(theme.PRIMARIO_PROPERTY, True)
        descartar = cartel.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        descartar.setProperty(theme.DESTRUCTIVO_PROPERTY, True)
        cartel.setDefaultButton(recuperar)
        cartel.setEscapeButton(descartar)
        cartel.exec()
        return cartel.clickedButton() is recuperar
