"""Correr algo largo sin congelar la ventana.

## Qué problema resuelve

La auditoría del 19 de septiembre lo dejó anotado con números: la conectividad
de la noche tarda **entre 15 y 18 s** sobre ocho horas, la ICA 9 s y filtrar
2,5 s, y los tres corrían en el hilo de la interfaz. Mientras duraban, la
ventana no repintaba: arrastrarla no la movía, y Windows la marcaba como «no
responde». `MainWindow._trabajando()` ponía el cursor de espera y un mensaje
antes de bloquear, que es todo lo que se puede hacer **desde adentro** del
hilo bloqueado; no acortaba la espera ni la hacía menos parecida a un cuelgue.

## Lo que sí y lo que no

- **El resultado vuelve al hilo de la interfaz.** Un `QThread` que vive en el
  hilo de la ventana entrega su `finished` por la cola de eventos de ese hilo,
  así que quien lo reciba puede tocar widgets. Tocarlos desde el otro hilo es
  un cuelgue o una corrupción, no un error que se vea.
- **No hay cancelar.** Ni MNE ni numpy interrumpen un cálculo empezado, así que
  un botón «Cancelar» sólo podría dejar de mirar el resultado: seguiría
  ocupando un núcleo hasta terminar. Ofrecerlo sería mentir sobre lo que hace.
- **Un error inesperado sigue rompiendo fuerte.** Lo que hereda de
  `PsgLabError` sale por `failed`, que es el contrato de todo el programa; lo
  que no —un `AttributeError`, un `KeyError`— se **vuelve a elevar en el hilo
  de la interfaz**, igual que antes de que esto existiera. Atraparlo y
  mostrarlo como un cartel convertiría un bug en un mensaje para el
  investigador, y hacerlo desaparecer en el hilo sería peor todavía.

Cubre del pliego: ningún ID. Es infraestructura de la interfaz; lo que se
calcula vive en `analysis/`.
"""

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal

from psglab.utils.errors import AlreadyRunningError, PsgLabError


class _Hilo(QThread):
    """El hilo que corre el trabajo y se guarda lo que salió."""

    def __init__(self, work: Callable[[], object], parent: QObject | None = None) -> None:
        """Recibe la función a correr, que **no puede tocar ningún widget**."""
        super().__init__(parent)
        self._trabajo = work
        self.resultado: object = None
        self.error: BaseException | None = None

    def run(self) -> None:
        """Corre el trabajo y guarda el resultado o la excepción.

        **Atrapa cualquier excepción y no sólo `PsgLabError`.** Una que se
        escape de `run()` no llega a ningún lado: Python la imprime por consola
        y el hilo muere, así que la ventana se quedaría esperando un resultado
        que nunca llega. Quién la ve y cómo lo decide `BackgroundTask`, en el
        hilo de la interfaz.
        """
        try:
            self.resultado = self._trabajo()
        except BaseException as error:  # noqa: BLE001 - se re-eleva o se emite
            self.error = error


class BackgroundTask(QObject):
    """Corre una función en otro hilo y avisa en el de la interfaz."""

    #: El trabajo terminó bien. Lleva lo que devolvió.
    finished = Signal(object)

    #: El trabajo elevó un error de los que ve el investigador.
    failed = Signal(object)  # PsgLabError

    def __init__(self, parent: QObject | None = None) -> None:
        """Crea la tarea sin nada corriendo."""
        super().__init__(parent)
        self._hilo: _Hilo | None = None

    def start(self, work: Callable[[], object]) -> None:
        """Arranca el trabajo en otro hilo.

        Args:
            work: lo que hay que calcular. **No puede tocar widgets ni la
                sesión**: corre en otro hilo, y Qt no soporta que se le dibuje
                desde afuera del de la interfaz.

        Raises:
            AlreadyRunningError: si ya hay algo corriendo. Dos cálculos a la vez
                sobre la misma sesión se pisarían el resultado, y cuál gana
                dependería de cuál termine primero.
        """
        if self.is_running():
            raise AlreadyRunningError(
                "Ya hay un cálculo en curso; esperá a que termine.",
                details="BackgroundTask.start() con un hilo todavía vivo.",
            )
        self._hilo = _Hilo(work, self)
        self._hilo.finished.connect(self._al_terminar)
        self._hilo.start()

    def is_running(self) -> bool:
        """Si hay un trabajo corriendo ahora."""
        return self._hilo is not None and self._hilo.isRunning()

    def wait(self) -> None:
        """Se queda hasta que el trabajo termine y entrega su resultado.

        **La usa el cierre de la ventana**: soltar la sesión con un cálculo
        todavía leyendo el registro deja a otro hilo trabajando sobre memoria
        que ya nadie tiene. Y la usa cualquier test que necesite el resultado,
        que es lo mismo que necesita quien cierra: saber que terminó.

        Con nada corriendo no hace nada.
        """
        if self._hilo is None:
            return
        self._hilo.wait()
        # **La entrega se fuerza acá.** `QThread.finished` viaja por la cola de
        # eventos del hilo de la interfaz, y quien llamó a `wait()` la está
        # bloqueando: sin esto, el resultado llegaría recién cuando el bucle de
        # eventos volviera a correr, que al cerrar el programa es nunca.
        self._al_terminar()

    def _al_terminar(self) -> None:
        """Ya en el hilo de la interfaz: entrega el resultado o el error."""
        hilo = self._hilo
        if hilo is None:
            return
        self._hilo = None
        hilo.deleteLater()

        error = hilo.error
        if error is None:
            self.finished.emit(hilo.resultado)
            return
        if isinstance(error, PsgLabError):
            self.failed.emit(error)
            return
        # Ver el docstring del módulo: un error inesperado rompe igual que
        # antes de que esto existiera, y en el hilo donde se puede depurar.
        raise error
