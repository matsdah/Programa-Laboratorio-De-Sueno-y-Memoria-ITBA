"""El análisis: la ICA, la señal original y el cálculo en segundo plano.

Tres cosas que los análisis de la Parte 2 comparten y que no son de ningún
panel:

- **La señal original.** Los análisis devuelven un registro nuevo —la regla 1
  de `analysis/`— y la sesión se queda con el procesado; el que se leyó del
  archivo se guarda acá, y «Montaje › Volver a la señal original» vuelve a él.
  Es lo que hace reversible todo el menú.
- **La descomposición ICA**, entre el ajuste y el «Aplicar». Se olvida en
  cuanto la señal deja de ser la suya: ver `forget_ica()`.
- **El único cálculo largo que puede estar corriendo** en otro hilo, con su
  barra de espera, y las acciones del menú que se apagan mientras dura.

**Es una pieza con estado propio** (hito 79). Hasta ahí esto era
`MainWindow._registro_original`, `_ica` y `_tarea`, repartidos entre
`main_window.py` y el mixin `window_analysis.py`. Qué análisis pedir, con qué
parámetros y cómo mostrar su resultado sigue en ese mixin: es presentación, y
cada panel es distinto. Lo que la ventana tiene que hacer le llega por señales
de Qt:

- `failed`: un cálculo no se pudo hacer. El cartel es de la ventana.
- `ica_forgotten`: la descomposición se descartó, y su panel se vacía.
- `restorable_changed`: si hay una señal original a la que volver, que es lo
  que prende o apaga su entrada del menú.

Por eso se testea sin `MainWindow`, en `tests/test_analysis_controller.py`.

Cubre del pliego: V5_F de "Filtración" (`forget_ica`, que descarta la
descomposición cuando la señal deja de ser la suya). El cálculo está en
`analysis/`; lo que vive acá es el ciclo de vida de la ICA entre el ajuste y el
«Aplicar».
"""

from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QProgressBar, QStatusBar

from psglab.core.recording import Recording
from psglab.core.session import Session
from psglab.ui.background import BackgroundTask
from psglab.utils.errors import PsgLabError

#: Cuánto mide la barra que dice que el programa está trabajando, en píxeles.
#: Corta: es una señal de vida, no una lectura.
ANCHO_DE_LA_BARRA_DE_ESPERA: int = 90


class AnalysisController(QObject):
    """La señal original, la ICA ajustada y el cálculo que corre en otro hilo."""

    #: Algo no se pudo hacer: el error y qué se intentaba —o None—, como lo
    #: espera `MainWindow._show_error()`.
    failed = Signal(object, object)
    #: La descomposición ICA se descartó: su panel tiene que vaciarse.
    ica_forgotten = Signal()
    #: Si la señal de la sesión ya no es la que se leyó, y se puede volver.
    restorable_changed = Signal(bool)

    def __init__(self, status_bar: QStatusBar, parent: QObject | None = None) -> None:
        """Arma la tarea y la barra de espera, que queda en `status_bar`.

        Args:
            status_bar: la barra de estado de la ventana, donde se dice qué se
                está calculando y se muestra la barra de espera.
        """
        super().__init__(parent)
        self._barra_de_estado = status_bar
        self._session: Session | None = None
        #: El registro tal como se leyó, para poder deshacer los análisis.
        self._registro_original: Recording | None = None
        #: La descomposición ICA ajustada, mientras el panel está abierto.
        self._ica: Any | None = None
        #: El único cálculo largo que puede estar corriendo. Ver
        #: `psglab/ui/background.py`.
        self._tarea = BackgroundTask(self)
        #: Las acciones que arrancan un cálculo largo o cambian la señal, para
        #: poder apagarlas mientras dura uno. Ver `set_long_actions()`.
        self._acciones_largas: tuple[QAction, ...] = ()

        #: Que algo largo está corriendo. **Indeterminada a propósito**: ni la
        #: conectividad de la noche ni la ICA informan cuánto llevan hechas, así
        #: que un porcentaje sería inventado.
        self._barra_de_espera = QProgressBar()
        self._barra_de_espera.setRange(0, 0)
        self._barra_de_espera.setTextVisible(False)
        self._barra_de_espera.setFixedWidth(ANCHO_DE_LA_BARRA_DE_ESPERA)
        self._barra_de_espera.setAccessibleName("El programa está trabajando")
        self._barra_de_espera.hide()
        status_bar.addPermanentWidget(self._barra_de_espera)

    # -- Lo que la ventana consulta ------------------------------------------

    @property
    def ica(self) -> Any | None:
        """La descomposición ajustada sobre la señal actual, o None."""
        return self._ica

    @property
    def original_recording(self) -> Recording | None:
        """El registro tal como se leyó del archivo, o None sin registro."""
        return self._registro_original

    @property
    def wait_bar(self) -> QProgressBar:
        """La barra que se mueve mientras corre un cálculo largo."""
        return self._barra_de_espera

    @property
    def is_busy(self) -> bool:
        """Si hay un cálculo corriendo en otro hilo."""
        return self._tarea.is_running()

    # -- El registro --------------------------------------------------------

    def attach(self, session: Session) -> None:
        """Toma la sesión de un registro recién abierto.

        Su registro pasa a ser el original, y la ICA del anterior se olvida: es
        de otra señal y de otros canales.
        """
        self._session = session
        self._registro_original = session.recording
        self.forget_ica()
        self.restorable_changed.emit(False)

    def replace_recording(self, calcular: Callable[[Recording], Recording]) -> Recording:
        """Corre un análisis sobre la señal actual y deja el resultado en la sesión.

        `Session.set_recording()` conserva la ventana, los canales y las
        amplitudes. **La ICA se olvida después, y sólo si todo salió bien**: si
        el análisis falló, la señal es la de antes y la descomposición sigue
        siendo válida.

        Returns:
            El registro procesado, que ya es el de la sesión.

        Raises:
            PsgLabError: si el análisis no se pudo hacer. **No cambia nada**: la
                señal que el investigador está mirando sigue siendo la de
                antes. Sin registro abierto, también.
        """
        if self._session is None:
            raise PsgLabError(
                "No hay ningún registro abierto.",
                details="AnalysisController.replace_recording sin sesión",
            )
        procesado = calcular(self._session.recording)
        self._session.set_recording(procesado)
        self.forget_ica()
        self.restorable_changed.emit(True)
        return procesado

    def restore_original(self) -> Recording | None:
        """Vuelve a la señal tal como se leyó del archivo.

        **Es lo que hace reversible todo el menú.** Sin esto, un filtro o una
        referencia mal elegidos obligarían a cerrar y reabrir el registro,
        perdiendo el scoring que el usuario venía haciendo. Volver también
        cambia la señal, así que la ICA se olvida.

        Returns:
            El registro original, ya en la sesión, o None si no hay registro.

        Raises:
            PsgLabError: si la sesión no lo aceptó. No cambia nada.
        """
        if self._session is None or self._registro_original is None:
            return None
        self._session.set_recording(self._registro_original)
        self.forget_ica()
        self.restorable_changed.emit(False)
        return self._registro_original

    # -- La ICA -------------------------------------------------------------

    def keep_ica(self, ica: Any) -> None:
        """Guarda la descomposición recién ajustada sobre la señal actual."""
        self._ica = ica

    def forget_ica(self) -> None:
        """Descarta la descomposición ICA porque la señal dejó de ser la suya.

        **Es la única guarda que hay contra el error más caro del menú Análisis.**
        `fit_ica()` se ajusta sobre la señal que había en ese momento, y el panel
        se queda abierto esperando que el usuario elija qué quitar. Si entre el
        ajuste y el "Aplicar" la señal cambió —se filtró, se derivó, se
        re-referenció, se volvió a la original, o se abrió otro registro—, la
        matriz de desmezclado ya no corresponde.

        **Y no falla sola.** Filtrar no cambia los nombres de los canales, así que
        MNE acepta el pedido sin protestar y devuelve una señal reconstruida con
        una descomposición ajena. El resultado es plausible, irreversible y
        equivocado, que es exactamente lo que `analysis/ica.py` dice querer
        evitar cuando advierte que "el usuario puede no darse cuenta".

        Olvidar es lo correcto y no una molestia: volver a ajustar es un clic, y
        la alternativa —conservarla y avisar— le pide al investigador que decida
        sobre algo que no puede ver. `apply_ica()` tiene además su propia guarda
        para el caso en que los canales sí cambien.

        No hace nada si no hay ninguna descomposición cargada, así que se la
        puede llamar desde cualquier camino sin preguntar antes.
        """
        if self._ica is None:
            return
        self._ica = None
        self.ica_forgotten.emit()

    # -- El cálculo en segundo plano ----------------------------------------

    def set_long_actions(self, actions: Iterable[QAction]) -> None:
        """Las acciones que no se pueden pedir con un cálculo en curso."""
        self._acciones_largas = tuple(actions)
        self._reflejar_lo_que_se_puede_pedir()

    def run_in_background(
        self,
        description: str,
        work: Callable[[], object],
        on_done: Callable[[object], None],
        action: str | None = None,
    ) -> None:
        """Corre algo largo en otro hilo y dibuja el resultado cuando vuelve.

        Es la versión que no congela la ventana de `MainWindow._trabajando()`,
        y la diferencia que se ve es que **la barra de progreso se mueve**:
        mientras el cálculo dura, el programa repinta, se puede arrastrar y el
        sistema no lo marca como «no responde».

        **La barra es indeterminada a propósito.** Ni `connectivity_by_window()`
        ni la ICA informan cuánto llevan hechas, así que un porcentaje sería
        inventado. Una barra que se mueve sin decir cuánto falta es honesta;
        una que dice 62 % sin saberlo, no.

        Args:
            description: lo que se lee en la barra de estado, sin los puntos
                suspensivos.
            work: lo que se calcula. **Corre en otro hilo**, así que no puede
                tocar widgets ni `Session`: lo que necesite de la sesión hay que
                resolverlo antes de llamar acá.
            on_done: qué hacer con el resultado. Corre en el hilo de la
                interfaz y sí puede dibujar.
            action: qué no se pudo hacer si falla, para la primera línea del
                cartel; ver `failed`.
        """
        self._barra_de_estado.showMessage(f"{description}…")
        self._barra_de_espera.show()

        # **La señal sobre la que se pidió** (hito 67). «Abrir» sigue
        # habilitado mientras el otro hilo trabaja, y lo que vuelve después de
        # abrir otro registro es de la señal anterior: la ICA de la noche A se
        # mostraba como la de B, y «Aplicar y quitar» la usaba sobre B sin
        # avisar cuando los dos tenían los mismos canales, que es lo normal
        # entre dos noches del mismo laboratorio. Se compara por identidad, como
        # `signal_view` con sus envolventes: un filtro o una derivación también
        # son otra señal.
        pedido_sobre = self._session.recording if self._session is not None else None

        def de_otra_senal() -> bool:
            if self._session is not None and self._session.recording is pedido_sobre:
                return False
            self._barra_de_estado.showMessage(
                "Se descartó un cálculo que era de la señal anterior.", 8000
            )
            return True

        def listo(resultado: object) -> None:
            self._terminar_la_espera(description)
            if de_otra_senal():
                return
            on_done(resultado)

        def fallo(error: object) -> None:
            self._terminar_la_espera(description)
            # Un error de la señal anterior tampoco se muestra: habla de algo
            # que ya no está en pantalla.
            if de_otra_senal():
                return
            if isinstance(error, PsgLabError):
                self.failed.emit(error, action)

        self._tarea.finished.connect(listo)
        self._tarea.failed.connect(fallo)
        # **Con cualquier final** (hito 68): un error que no es `PsgLabError`
        # no pasa por ninguna de las dos de arriba, y sin esto la barra seguía
        # girando y los menús largos quedaban apagados hasta cerrar el programa.
        self._tarea.stopped.connect(lambda: self._terminar_la_espera(description))
        try:
            self._tarea.start(work)
        except PsgLabError as error:
            self._terminar_la_espera(description)
            self.failed.emit(error, action)
            return
        # **Después de arrancar y no antes.** Lo que decide qué se puede pedir
        # es `BackgroundTask.is_running()`, que con el hilo sin arrancar
        # todavía dice que no: llamado antes, esto no apagaba nada.
        self._reflejar_lo_que_se_puede_pedir()

    def wait(self) -> None:
        """Se queda hasta que termine el cálculo que esté corriendo.

        La pide el cierre de la ventana: soltar la sesión con otro hilo
        todavía leyendo el registro lo deja trabajando sobre memoria que ya
        nadie tiene.
        """
        self._tarea.wait()

    def _terminar_la_espera(self, description: str) -> None:
        """Saca la barra y desconecta lo que quedó de este cálculo.

        **Se desconecta y no se deja conectado**: los `connect()` de
        `run_in_background()` son closures de *este* pedido, y dejarlos
        puestos haría que el siguiente cálculo dibujara también el resultado
        del anterior.
        """
        self._barra_de_espera.hide()
        if self._barra_de_estado.currentMessage() == f"{description}…":
            self._barra_de_estado.clearMessage()
        for señal in (self._tarea.finished, self._tarea.failed, self._tarea.stopped):
            try:
                señal.disconnect()
            except RuntimeError:
                # No había nadie conectado. Qt lo considera un error; acá es
                # el caso normal de llamar dos veces.
                pass
        self._reflejar_lo_que_se_puede_pedir()

    def _reflejar_lo_que_se_puede_pedir(self) -> None:
        """Apaga lo que no se puede pedir con un cálculo en curso.

        **Dos cálculos a la vez sobre la misma sesión se pisan el resultado**, y
        cuál gana depende de cuál termine primero. `BackgroundTask` lo rechaza
        igual, pero un menú que deja pedir algo que va a fallar es peor que uno
        que lo muestra apagado.
        """
        ocupado = self._tarea.is_running()
        for accion in self._acciones_largas:
            accion.setEnabled(not ocupado)
