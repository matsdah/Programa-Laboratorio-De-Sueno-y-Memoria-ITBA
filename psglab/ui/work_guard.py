"""El trabajo del investigador: exportarlo y no perderlo.

Dos cosas que van juntas porque la segunda usa a la primera:

- **Exportar** los tres archivos de salida, con su diálogo de guardado, que
  arranca en la carpeta del registro y propone el nombre del pliego.
- **El trabajo sin exportar** (hito 33): antes de soltar la sesión —cerrar,
  abrir otro registro, importar un scoring encima— se pregunta si hay scoring
  o anotaciones que no están en ningún archivo, y se ofrece exportarlos.

**Es una pieza con estado propio** (hito 79). Hasta ahí era la mitad del mixin
`window_files.py`, que compartía con los demás el estado de la ventana. La
ventana lo guarda en `work_guard`, le pregunta `can_discard()` antes de soltar
la sesión, y conserva `export()` y `export_scoring_dialog()` porque los piden
el menú, Ctrl+S y los scripts por su nombre. Lo que es de ella le llega por
señales o por lo que le pasa al construirlo:

- `failed`: no se pudo exportar. El cartel es de la ventana.
- `confirm`: la pregunta de sí o no de la ventana, para reemplazar un archivo.

**El programa no autoguarda**, por decisión del usuario en el hito 33: guardar
a escondidas obliga a elegir dónde y en qué formato por él. El archivo de
recuperación que el usuario decidió el 26 de septiembre de 2026 no es un
autoguardado —no exporta nada ni elige formato— y va a vivir acá.

Se testea sin `MainWindow`, en `tests/test_work_guard.py`.

Cubre del pliego: V4_F de "Archivo de salida" (`export()` elige cuál de los
tres archivos escribir, aunque desde el hito 23 la ventana sólo ofrece el
scoring).
"""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QStatusBar, QWidget

from psglab.core.session import Session
from psglab.exporters import DEFAULT_FILENAMES
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.information_txt import export_information
from psglab.exporters.scoring_formats import SCORING_FORMATS, export_scoring_as
from psglab.ui import theme
from psglab.utils.errors import PsgLabError

#: La pregunta de sí o no de la ventana: título, pregunta, qué dice el botón
#: que acepta y el texto de abajo. Ver `MainWindow._confirmar()`.
Confirmar = Callable[[str, str, str, str], bool]


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

    def attach(self, session: Session) -> None:
        """Toma la sesión de un registro recién abierto.

        Hay que preguntar `can_discard()` antes, sobre la anterior: después ya
        no hay a quién preguntarle.
        """
        self._session = session

    # -- Exportar -----------------------------------------------------------

    def export(self, kind: str, path: Path) -> bool:
        """Exporta uno de los tres archivos de salida (V4_F).

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
        if not en_juego:
            return True
        respuesta = self.ask(doing, en_juego)
        if respuesta == "descartar":
            return True
        if respuesta == "exportar":
            for que in en_juego:
                self.export_dialog(que)
            return not self.unexported()
        return False

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
