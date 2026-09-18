"""Estado de la sesión de trabajo del usuario.

Reúne todo lo que el usuario tiene abierto y configurado en un momento dado:
qué registro, qué scoring, qué anotaciones, en qué ventana está parado, qué
canales ve y con qué amplitud.

Este objeto es el que la interfaz consulta para dibujarse y el que modifica
cuando el usuario hace algo. Mantenerlo fuera de `psglab.ui` es lo que permite
testear la navegación y el manejo de amplitudes sin abrir una ventana.

Cubre del pliego: V1_F de "Navegación en la señal"; V2_P, V3_P y V5_F de
"Visualización de la señal"; V4_F del histograma (`go_to_window`, que es a
donde llega el clic sobre el hipnograma).
"""

from collections.abc import Callable

import numpy as np

from psglab.config import (
    AMPLITUDE_STEP_FACTOR,
    DEFAULT_VIEW_SECONDS,
    DEFAULT_SCALE_UV,
    MAX_SCALE_UV,
    MIN_SCALE_UV,
)
from psglab.core.annotations import AnnotationSet
from psglab.core.recording import Recording
from psglab.core.scoring import Scoring
from psglab.core.viewport import Viewport
from psglab.core.windows import (
    count_windows,
    epoch_to_seconds,
    sample_to_window,
    seconds_to_sample_absolute,
    window_to_samples,
)
from psglab.utils.errors import (
    PsgLabError,
    InvalidViewportError,
    InvalidAnnotationError,
    InvalidRecordingError,
    InvalidScaleError,
    ScoringMismatchError,
    WindowOutOfRangeError,
)
from psglab.utils.validation import check_finite, check_index, clamp


class Session:
    """Estado de trabajo sobre un registro abierto."""

    def __init__(
        self,
        recording: Recording,
        scoring: Scoring,
        annotations: AnnotationSet,
        default_scale_uv: float = DEFAULT_SCALE_UV,
    ) -> None:
        """Abre una sesión de trabajo sobre un registro ya cargado.

        Args:
            default_scale_uv: escala vertical inicial de todos los canales.
                Por defecto, la de `config`.

        Raises:
            ScoringMismatchError: si `scoring.n_windows` no coincide con las
                ventanas que tiene el registro. Las tres piezas llegan sueltas y
                nada garantiza que hablen del mismo archivo: un scoring
                importado de otro registro daría un histograma de largo
                equivocado y dejaría ventanas imposibles de scorear, sin ningún
                error visible. Se comprueba acá, que es donde se juntan por
                primera vez.

        La sesión arranca en la ventana 0, con **todos** los canales visibles en
        el orden del archivo y ninguno seleccionado. El pliego (V1_P) pide un
        subconjunto inicial —ojos, C3, C4 y EMG—, pero elegirlo necesita la
        detección de clase de canal, que vive en `readers/channel_types.py`: ese
        default es de la interfaz cuando exista, no de `core/`.
        """
        # Las tres piezas llegan sueltas desde la capa de carga. Sin esta
        # guarda, `recording.n_samples` y `scoring.n_windows` elevaban
        # `AttributeError` en la línea de abajo: el rechazo era correcto y la
        # explicación del rechazo, imposible.
        for nombre, valor, esperado, error in (
            ("recording", recording, Recording, InvalidRecordingError),
            ("scoring", scoring, Scoring, ScoringMismatchError),
            ("annotations", annotations, AnnotationSet, InvalidAnnotationError),
        ):
            if not isinstance(valor, esperado):
                raise error(
                    "No se pudo abrir la sesión de trabajo con lo que se le pasó.",
                    details=(
                        f"{nombre} es {type(valor).__name__}, "
                        f"se esperaba {esperado.__name__}."
                    ),
                )

        ventanas = count_windows(recording.n_samples, recording.sampling_rate)
        if scoring.n_windows != ventanas:
            raise ScoringMismatchError(
                f"El scoring es de {scoring.n_windows} ventanas y el registro tiene "
                f"{ventanas}, así que no corresponden al mismo archivo.",
                details=(
                    f"scoring.n_windows = {scoring.n_windows}, "
                    f"count_windows({recording.n_samples}, {recording.sampling_rate}) "
                    f"= {ventanas}."
                ),
            )

        self._recording = recording
        self._scoring = scoring
        self._annotations = annotations
        self._current_window = 0
        self._visible_channels: list[str] = recording.channel_names()
        self._selected_channels: list[str] = []
        # La escala inicial pasa por la misma guarda que `set_scale_uv`, que
        # declara ser el único lugar que recorta. Escribir el diccionario
        # directamente esquivaba el recorte entero: con `0.0` el visualizador
        # divide por cero, y con un valor negativo dibuja toda la señal
        # invertida mientras la escala de la izquierda anuncia "-50 µV".
        check_finite(
            default_scale_uv,
            error=InvalidScaleError,
            message="La escala vertical inicial no es un número válido.",
            details="Se esperaba un número finito.",
        )
        inicial = clamp(default_scale_uv, MIN_SCALE_UV, MAX_SCALE_UV)
        self._scales_uv: dict[str, float] = {
            nombre: inicial for nombre in recording.channel_names()
        }
        #: Cuántos µV se le restan a cada canal antes de dibujarlo. Arranca en
        #: cero para todos, que es el comportamiento que el programa tenía
        #: antes de que el desplazamiento existiera.
        self._offsets_uv: dict[str, float] = {
            nombre: 0.0 for nombre in recording.channel_names()
        }
        #: Qué tramo del registro se está mirando. Arranca en una época, que
        #: es la página que el programa tuvo siempre: abrir un registro da
        #: exactamente la misma pantalla que antes de que esto existiera.
        self._viewport = Viewport.clamped(
            0.0, DEFAULT_VIEW_SECONDS, recording.duration_seconds
        )
        self._active_tool: str | None = None
        #: A quién avisarle cuando cambia la ventana actual. Ver
        #: `add_window_listener()`.
        self._window_listeners: list[Callable[[int], None]] = []
        #: A quién avisarle cuando cambia la página visible. Ver
        #: `add_view_listener()`.
        self._view_listeners: list[Callable[[Viewport], None]] = []

    def _check_channels(self, channel_names: list[str]) -> None:
        """Rechaza cualquier nombre que el registro no tenga.

        Se apoya en `Recording.channel_by_name()`, que ya eleva el error con el
        mensaje correcto y la lista de canales disponibles en `details`.
        """
        for nombre in channel_names:
            self._recording.channel_by_name(nombre)

    # -- Lo que hay abierto -------------------------------------------------
    #
    # Las tres piezas que la sesión reúne se exponen de sólo lectura. Es el
    # único camino por el que la interfaz y las herramientas llegan a ellas:
    # el histograma necesita el scoring, el anotador el conjunto de
    # anotaciones y el visualizador el registro, y todos reciben nada más que
    # una `Session`. Sin estas propiedades cada uno inventaría su propio
    # acceso a un atributo no documentado.
    #
    # Son de sólo lectura a propósito: cambiar de registro no es mutar la
    # sesión, es abrir una nueva.

    @property
    def recording(self) -> Recording:
        """Registro abierto en esta sesión."""
        return self._recording

    @property
    def scoring(self) -> Scoring:
        """Scoring del registro abierto."""
        return self._scoring

    @property
    def annotations(self) -> AnnotationSet:
        """Anotaciones del registro abierto."""
        return self._annotations

    def set_scoring(self, scoring: Scoring) -> None:
        """Reemplaza el scoring por uno importado de archivo (V3_F).

        **Por qué existe, en vez de armar otra `Session`.** Importar un scoring
        no es abrir otro registro: el usuario sigue parado en la misma ventana,
        con los mismos canales visibles y las amplitudes que se acomodó. Una
        `Session` nueva los perdería todos, y además dejaría a las herramientas
        ya activadas apuntando a la sesión vieja —siguen guardando la que
        recibieron en `activate()`—, así que el histograma dibujaría el scoring
        anterior sin que nada fallara. Sustituir acá adentro conserva la
        identidad del objeto y no hay nada que volver a cablear.

        Se hace la misma comprobación que en `__init__`, y por el mismo motivo:
        el scoring llega suelto y nada garantiza que sea de este registro.

        Raises:
            ScoringMismatchError: si no es un `Scoring`, o si su cantidad de
                ventanas no es la del registro abierto.
        """
        if not isinstance(scoring, Scoring):
            raise ScoringMismatchError(
                "No se pudo importar el scoring con lo que se le pasó.",
                details=(
                    f"scoring es {type(scoring).__name__}, se esperaba Scoring."
                ),
            )
        if scoring.n_windows != self.n_windows:
            raise ScoringMismatchError(
                f"El scoring es de {scoring.n_windows} ventanas y el registro "
                f"tiene {self.n_windows}, así que no corresponden al mismo "
                "archivo.",
                details=(
                    f"scoring.n_windows = {scoring.n_windows}, "
                    f"session.n_windows = {self.n_windows}."
                ),
            )
        self._scoring = scoring

    def set_recording(self, recording: Recording) -> None:
        """Reemplaza el registro por uno procesado, sin perder la sesión.

        **Es lo que hace usable la Parte 2.** Filtrar, re-referenciar y derivar
        devuelven un `Recording` nuevo —es la regla 1 de `analysis/`: el
        original no se toca, para que el usuario pueda comparar y volver
        atrás—, y sin esto ese registro nuevo no tenía por dónde llegar a la
        pantalla.

        Vale acá el mismo argumento que en `set_scoring()`: procesar la señal
        no es abrir otro archivo. El usuario sigue parado en su ventana, y las
        herramientas activas siguen guardando la sesión que recibieron en
        `activate()`, así que sustituir adentro conserva la identidad del objeto
        y no hay nada que volver a cablear.

        **Pero tiene un caso que `set_scoring()` no tenía: los canales pueden
        cambiar.** Una derivación agrega `C3-A2`, y un montaje podría dejar
        afuera alguno de los que el usuario tenía visibles. La regla es
        conservar lo que sobrevive y no inventar:

        - Los **visibles** que sigan existiendo se conservan en su orden. Si no
          sobrevive ninguno se vuelve a mostrar todo, porque una pantalla vacía
          después de filtrar se lee como que el filtro borró la señal.
        - Los **seleccionados** que sigan existiendo se conservan; el resto se
          descarta en silencio, que es lo mismo que hace `set_visible_channels`
          con una selección que ya no aplica.
        - Las **escalas** se conservan por nombre de canal, y los canales nuevos
          arrancan con la de fábrica. Un derivado hereda la amplitud de nadie.

        Raises:
            InvalidRecordingError: si no es un `Recording`.
            ScoringMismatchError: si dura otra cantidad de ventanas. Procesar la
                señal no cambia su duración, así que si cambió es que el
                registro no es el mismo, y el scoring que el usuario ya hizo
                dejaría de corresponder.
        """
        if not isinstance(recording, Recording):
            raise InvalidRecordingError(
                "No se pudo reemplazar el registro con lo que se le pasó.",
                details=(
                    f"recording es {type(recording).__name__}, se esperaba Recording."
                ),
            )
        ventanas = count_windows(recording.n_samples, recording.sampling_rate)
        if ventanas != self.n_windows:
            raise ScoringMismatchError(
                f"El registro procesado dura {ventanas} ventanas y el original "
                f"{self.n_windows}, así que el scoring ya hecho dejaría de "
                "corresponder.",
                details=(
                    f"count_windows({recording.n_samples}, "
                    f"{recording.sampling_rate}) = {ventanas}, "
                    f"session.n_windows = {self.n_windows}."
                ),
            )

        nombres = recording.channel_names()
        sobreviven = [n for n in self._visible_channels if n in nombres]
        self._visible_channels = sobreviven if sobreviven else list(nombres)
        self._selected_channels = [
            n for n in self._selected_channels if n in nombres
        ]
        inicial = clamp(DEFAULT_SCALE_UV, MIN_SCALE_UV, MAX_SCALE_UV)
        self._scales_uv = {
            nombre: self._scales_uv.get(nombre, inicial) for nombre in nombres
        }
        # Los desplazamientos se conservan **por nombre**, igual que las
        # escalas: un canal que sobrevive a un filtrado sigue apoyado donde el
        # usuario lo dejó.
        self._offsets_uv = {
            nombre: self._offsets_uv.get(nombre, 0.0) for nombre in nombres
        }
        self._recording = recording
        # **La página se re-recorta y se avisa.** Filtrar o derivar puede
        # cambiar la duración por debajo de una época sin que `n_windows`
        # cambie, y una página que se pasa del final dibujaría un tramo que no
        # existe. Avisar acá además es lo que deja morir la caché de dibujo del
        # visualizador: hasta ahora eso dependía de que alguien se acordara de
        # llamar a `set_session()` después, que es la clase de olvido invisible
        # que `add_window_listener()` existe para impedir.
        self._viewport = self._viewport.for_duration(recording.duration_seconds)
        self._notify_view_changed(self._viewport)

    # -- Navegación entre ventanas (V1_F de "Navegación") -------------------

    @property
    def current_window(self) -> int:
        """Ventana actual, índice base 0."""
        return self._current_window

    @property
    def n_windows(self) -> int:
        """Cantidad total de ventanas del registro (VENMAX).

        Sale del registro y no del scoring: el archivo es la fuente de verdad de
        cuántas ventanas hay. El chequeo de `__init__` garantiza que los dos
        números coincidan, así que la propiedad no es ambigua.
        """
        return count_windows(self._recording.n_samples, self._recording.sampling_rate)

    def add_window_listener(self, callback: Callable[[int], None]) -> None:
        """Registra a quién avisarle cuando el usuario cambia de ventana.

        **Por qué `Session` avisa en vez de que lo haga la ventana principal.**
        Hay tres herramientas que dependen de enterarse: el medidor de ocupación
        borra sus líneas (V5_F de "Ocupación"), la Übersicht se recentra y el
        histograma mueve su indicador. Si la obligación de avisarles viviera en
        `ui/main_window.py`, dependería de que alguien se acuerde de llamarlas
        después de cada `go_to_window()`, `next_window()` y `previous_window()`
        —en la capa cuyo dibujo no lleva tests— y un olvido rompería las
        tres **sin que nada fallara de forma visible**: las líneas de la ventana
        anterior seguirían dibujadas sobre la siguiente como si midieran algo.

        Es un callback y no una señal de Qt por el mismo motivo que en
        `tools/base.py`: `core/` no conoce `ui/`, y así esto se testea sin abrir
        una ventana.

        No hay forma de desuscribirse y no hace falta: una herramienta
        desactivada ya ignora el aviso, porque lo primero que hace
        `on_window_changed()` es comprobar que tenga sesión.

        Raises:
            PsgLabError: si lo que se registra no se puede llamar. Se comprueba
                acá y no al avisar porque **acá está el bug**: guardado sin
                mirar, reventaría con un `TypeError` crudo la próxima vez que el
                usuario apretara una flecha, tres capas más arriba y sin
                ninguna pista de quién lo registró.
        """
        if not callable(callback):
            raise PsgLabError(
                "No se pudo preparar la sesión para avisar de los cambios de ventana.",
                details=(
                    f"Se registró un aviso de tipo {type(callback).__name__}, "
                    "que no se puede llamar."
                ),
            )
        self._window_listeners.append(callback)

    def _notify_window_changed(self, window_index: int) -> None:
        """Avisa a los suscriptos.

        **La guarda de "sólo si cambió de verdad" está en los tres llamadores**,
        no acá: `go_to_window()` vuelve temprano si el índice es el actual, y
        `next_window()` y `previous_window()` no se mueven en los bordes. Este
        método avisa siempre que se lo llame.

        La distinción importa porque avisar de más tiene consecuencia: llegar al
        final de la noche con la flecha derecha no es un cambio de ventana, y
        avisarlo le borraría al usuario las líneas de ocupación que acaba de
        dibujar sin que haya ido a ningún lado. Lo mismo vale para un clic del
        histograma sobre la ventana que ya se está viendo.
        """
        for avisar in self._window_listeners:
            avisar(window_index)

    def _seguir_a_la_epoca(self) -> None:
        """Mueve la página **lo mínimo** para que la época actual entre.

        Es lo que hace que la escala de tiempo libre conviva con el scoring:

        - con una página de 30 s la época nunca entra salvo alineada, así que
          la página salta a ella y el comportamiento es **el de siempre**;
        - con una página de cuatro horas la época ya está adentro,
          `Viewport.containing()` devuelve la misma página, `set_viewport()`
          vuelve temprano y **la pantalla no se mueve**. Apretar la flecha
          derecha cuatrocientas ochenta veces recorre las épocas sin sacudir el
          dibujo.

        No centra la época a propósito: centrar en cada flecha haría saltar la
        pantalla media página por vez, que es peor que no moverla.
        """
        inicio, fin = epoch_to_seconds(
            self._current_window, self._recording.sampling_rate
        )
        self.set_viewport(self._viewport.containing(inicio, fin))

    def _check_window(self, window_index: int) -> None:
        """Rechaza un índice de ventana que no existe en este registro.

        Está separado porque lo usan tres caminos —`go_to_window()` y los dos
        ajustes de amplitud, que miden sobre una ventana— y repetir la guarda
        en cada uno garantiza que tarde o temprano discrepen.

        Raises:
            WindowOutOfRangeError: si no es un entero, o si cae fuera del
                registro. **Se comprueba también el borde negativo**:
                `core.windows` documenta que sus conversiones devuelven números
                negativos en silencio y nombra a esta guarda como su defensa,
                así que un índice negativo que pasara de acá terminaría
                dibujando el final de la noche como si fuera el principio.
        """
        check_index(
            window_index,
            error=WindowOutOfRangeError,
            message="Se pidió una ventana que no se puede ubicar en el registro.",
            details="Se esperaba un número de ventana entero.",
        )
        if not 0 <= window_index < self.n_windows:
            raise WindowOutOfRangeError(
                f"La ventana {window_index + 1} no existe en este registro, que "
                f"tiene {self.n_windows}.",
                details=(
                    f"window_index = {window_index} (base 0), "
                    f"n_windows = {self.n_windows}."
                ),
            )

    def go_to_window(self, window_index: int) -> None:
        """Salta a una ventana concreta.

        Lo usa el clic sobre el histograma (V4_F del histograma).

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro. Se
                comprueba también el borde negativo: `core.windows` documenta
                que sus conversiones devuelven números negativos **en silencio**
                y nombra a este método como su guarda, así que un índice negativo
                que pasara de acá terminaría dibujando el final de la noche como
                si fuera el principio.
        """
        self._check_window(window_index)
        if window_index == self._current_window:
            return
        self._current_window = window_index
        self._seguir_a_la_epoca()
        self._notify_window_changed(window_index)

    def next_window(self) -> None:
        """Avanza una ventana. En la última no hace nada.

        No elevar en el borde es deliberado: quien mantiene apretada la flecha
        derecha llega al final y se queda ahí, no recibe un error.
        """
        if self._current_window < self.n_windows - 1:
            self._current_window += 1
            self._seguir_a_la_epoca()
            self._notify_window_changed(self._current_window)

    def previous_window(self) -> None:
        """Retrocede una ventana. En la primera no hace nada."""
        if self._current_window > 0:
            self._current_window -= 1
            self._seguir_a_la_epoca()
            self._notify_window_changed(self._current_window)

    def move_playhead(self, seconds: float) -> float:
        """Lleva la reproducción a un instante: la página se centra en él y la
        época actual pasa a ser la que lo contiene (hito 27).

        Es la gemela de `_seguir_a_la_epoca()`, con la regla opuesta a
        propósito. Aquélla mueve la página **lo mínimo** para que entre la
        época, y es lo que corresponde en pausa: con cuatro horas en pantalla la
        flecha mueve el resaltado y no la vista. Reproduciendo, lo que se sigue
        es el instante que pasa por el medio del gráfico, y la época es la de
        ese instante: al pausar, el usuario queda parado en la época que estaba
        mirando y la scorea ahí. **Hasta el hito 27 era al revés**: reproducir
        movía la página y la época se quedaba donde estaba.

        **En los bordes la página no se puede centrar, y no se fuerza.** La
        recorta `Viewport.clamped()`, y el instante queda adentro de la página
        pero fuera del medio. Así la reproducción pasa por todas las épocas,
        también por las del principio y las del final.

        **No llama a `_seguir_a_la_epoca()`**: con una página de menos de 30 s,
        `containing()` la llevaría al comienzo de la época y el instante dejaría
        de estar en el medio.

        Args:
            seconds: segundos desde el inicio del registro. Lo que cae fuera del
                registro se recorta a él.

        Returns:
            El instante que quedó, ya recortado. Lo devuelve para que la
            interfaz no repita el recorte: si lo hiciera por su cuenta, el
            cursor que dibuja y el que usa la sesión podrían discrepar.

        Raises:
            InvalidViewportError: si no es un número finito. Un NaN recortado
                con `min` y `max` seguiría siendo NaN, y la página también.
        """
        check_finite(
            seconds,
            error=InvalidViewportError,
            message="No se pudo ubicar la reproducción en el registro.",
            details="seconds tiene que ser un número finito.",
        )
        instante = clamp(float(seconds), 0.0, self._recording.duration_seconds)
        self.set_viewport(self._viewport.with_center(instante))

        frecuencia = self._recording.sampling_rate
        # El final exacto del registro cae en una ventana que no existe: es la
        # muestra siguiente a la última.
        epoca = min(
            sample_to_window(seconds_to_sample_absolute(instante, frecuencia), frecuencia),
            self.n_windows - 1,
        )
        if epoca != self._current_window:
            self._current_window = epoca
            self._notify_window_changed(epoca)
        return instante

    # -- Canales visibles (V3_P, V4_F de "Visualización") -------------------

    @property
    def visible_channels(self) -> list[str]:
        """Nombres de los canales que se están mostrando, en orden.

        Devuelve una copia: la interfaz sólo quiere recorrerla, y prestarle la
        interna la dejaría reordenar los canales sin pasar por el setter.
        """
        return list(self._visible_channels)

    def set_visible_channels(self, channel_names: list[str]) -> None:
        """Define qué canales se muestran y en qué orden.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
        """
        self._check_channels(channel_names)
        self._visible_channels = list(channel_names)

    @property
    def selected_channels(self) -> list[str]:
        """Canales seleccionados por el usuario.

        Si hay canales seleccionados, los cambios de amplitud se aplican sólo
        a ellos; si no hay ninguno, se aplican a todos los visibles (V5_F).

        Devuelve una copia, por el mismo motivo que `visible_channels`.
        """
        return list(self._selected_channels)

    def set_selected_channels(self, channel_names: list[str]) -> None:
        """Define los canales sobre los que actúan los cambios de amplitud.

        **No se exige que estén visibles.** Visibilidad y selección son ejes
        distintos —qué se dibuja y qué recibe los cambios de amplitud— y el
        pliego no los ata: seleccionar un canal y después ocultarlo deja su
        escala cambiando aunque no se vea, y eso es coherente con que al volver
        a mostrarlo aparezca como el usuario lo dejó.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
        """
        self._check_channels(channel_names)
        self._selected_channels = list(channel_names)

    # -- Amplitud (V2_P, V5_F de "Visualización") ---------------------------

    def scale_uv(self, channel_name: str) -> float:
        """Escala vertical de un canal, en microvoltios.

        Es el número que se muestra en la escala de la izquierda del
        visualizador (V1_P): **cuántos microvoltios representa la altura del
        canal**.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
        """
        self._recording.channel_by_name(channel_name)
        return self._scales_uv[channel_name]

    def _channels_under_amplitude(self) -> list[str]:
        """Canales a los que llega un cambio de amplitud (V5_F).

        Los seleccionados si hay alguno; si no, todos los visibles.

        **Sin repetidos.** Mostrar el mismo canal dos veces es un uso soportado
        —`get_segment` lo documenta— y sin esta deduplicación cada pulsación de
        flecha le aplicaba el paso dos veces: el canal se escapaba del resto y
        el usuario no tenía cómo entender por qué.
        """
        elegidos = self._selected_channels or self._visible_channels
        return list(dict.fromkeys(elegidos))

    def _check_amplitude_factor(self, factor: float) -> None:
        """Rechaza un paso de amplitud con el que no se puede escalar.

        Sin esta guarda, un factor que no sea número sale como `TypeError` y el
        cero como `ZeroDivisionError`. Los dos atraviesan el `except
        PsgLabError` de la ventana principal.
        """
        check_finite(
            factor,
            error=InvalidScaleError,
            message="El paso de amplitud no sirve para escalar la señal.",
            details="factor tiene que ser un número finito mayor que cero.",
        )
        if factor <= 0:
            raise InvalidScaleError(
                "El paso de amplitud no sirve para escalar la señal.",
                details=f"factor tiene que ser mayor que cero; se recibió {factor}.",
            )

    def increase_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Aumenta la amplitud (flecha "Arriba").

        Se aplica a los canales seleccionados, o a todos los visibles si no
        hay ninguno seleccionado.

        **Aumentar la amplitud baja el número de `scale_uv`, no lo sube**, y
        conviene tenerlo presente porque parece al revés. `scale_uv` es cuántos
        µV representa la altura del canal: para que la señal se dibuje más
        grande, esa misma altura tiene que representar **menos** µV. Subir el
        número achicaría la onda, que es lo contrario de lo que espera quien
        aprieta la flecha.

        Args:
            factor: cuánto se multiplica la amplitud por cada pulsación. Por
                defecto, el paso de `config`.
        """
        self._check_amplitude_factor(factor)
        for nombre in self._channels_under_amplitude():
            self.set_scale_uv(nombre, self._scales_uv[nombre] / factor)

    def decrease_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Reduce la amplitud (flecha "Abajo"). Mismo criterio de alcance."""
        self._check_amplitude_factor(factor)
        for nombre in self._channels_under_amplitude():
            self.set_scale_uv(nombre, self._scales_uv[nombre] * factor)

    def set_scale_uv(
        self,
        channel_name: str,
        scale_uv: float,
        minimum_uv: float = MIN_SCALE_UV,
        maximum_uv: float = MAX_SCALE_UV,
    ) -> None:
        """Fija la escala de un canal, recortada a los límites permitidos.

        Los límites existen para que el usuario no pueda dejar la pantalla
        inutilizable a fuerza de flechazos. Por defecto son los de `config`.

        Es el **único lugar que recorta**: las dos flechas y la escala inicial
        del constructor delegan acá en vez de repetir la comprobación, para que
        no puedan discrepar.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
            InvalidScaleError: si la escala no es un número finito. `min(max(nan,
                lo), hi)` devuelve **NaN**, así que la forma corta de recortar no
                recorta nada: el canal dejaría de dibujarse y la escala de la
                izquierda anunciaría "nan µV".
        """
        self._recording.channel_by_name(channel_name)
        check_finite(
            scale_uv,
            error=InvalidScaleError,
            message=f"La escala pedida para el canal '{channel_name}' no es un número válido.",
            details="Se esperaba un número finito.",
        )
        self._scales_uv[channel_name] = clamp(scale_uv, minimum_uv, maximum_uv)

    # -- Desplazamiento vertical --------------------------------------------

    def offset_uv(self, channel_name: str) -> float:
        """Cuántos microvoltios se le restan a un canal antes de dibujarlo.

        Es el equivalente vertical de la escala, y responde a otra pregunta:
        `scale_uv` dice **cuánto se agranda** la señal, y esto **dónde se apoya**
        dentro de su carril.

        Hace falta porque un canal puede tener una línea de base muy lejos del
        cero —un termómetro marca 36, un canal de continua puede quedar
        cientos de µV corrido— y entonces se dibuja pegado al borde de su
        carril o directamente fuera. Antes la única salida era achicar la
        escala hasta que entrara, y con eso se perdía la señal.

        Arranca en 0,0 para todos los canales, que es exactamente el
        comportamiento que tenía el programa antes de que esto existiera.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
        """
        self._recording.channel_by_name(channel_name)
        return self._offsets_uv.get(channel_name, 0.0)

    def set_offset_uv(self, channel_name: str, offset_uv: float) -> None:
        """Fija el desplazamiento vertical de un canal.

        **No se recorta**, a diferencia de la escala, y la asimetría es
        deliberada: un recorte de la escala impide dejar la pantalla
        inutilizable, pero un offset grande no rompe nada —la señal sale del
        carril y se la vuelve a traer con «Offset → 0»—, y cuál es el valor
        razonable depende del canal: para un EEG son decenas de µV y para un
        termómetro, decenas de miles.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
            InvalidScaleError: si el desplazamiento no es un número finito. Un
                NaN dejaría el canal sin dibujar y sin ningún cartel.
        """
        self._recording.channel_by_name(channel_name)
        check_finite(
            offset_uv,
            error=InvalidScaleError,
            message=(
                f"El desplazamiento pedido para el canal '{channel_name}' no es "
                "un número válido."
            ),
            details="Se esperaba un número finito.",
        )
        self._offsets_uv[channel_name] = float(offset_uv)

    def reset_offsets(self) -> None:
        """Devuelve al cero el desplazamiento de los canales bajo amplitud.

        Es «Offset → 0» de la referencia, y es la salida cuando el ajuste
        automático dejó un canal en un lugar raro. Mismo alcance que las
        flechas: los seleccionados, o todos los visibles si no hay selección.
        """
        for nombre in self._channels_under_amplitude():
            self._offsets_uv[nombre] = 0.0

    def center_offsets(self, window_index: int | None = None) -> None:
        """Apoya cada canal en el centro de su carril.

        Es «Ajustar offset». Le da a cada canal el desplazamiento que lleva su
        promedio a cero **en la ventana que se está mirando**, no en la noche
        entera: la línea de base de un EEG deriva a lo largo de ocho horas, y
        centrar contra el promedio global dejaría la ventana actual corrida.

        Args:
            window_index: qué ventana se usa para medir. Por omisión, la actual.

        Raises:
            WindowOutOfRangeError: si la ventana pedida no existe.
        """
        ventana = self._current_window if window_index is None else window_index
        self._check_window(ventana)
        inicio, fin = window_to_samples(ventana, self._recording.sampling_rate)
        for nombre in self._channels_under_amplitude():
            tramo = self._recording.get_segment(inicio, fin, [nombre])
            if tramo.size == 0:
                continue
            self._offsets_uv[nombre] = float(np.mean(tramo))

    def fit_to_pane(self, window_index: int | None = None) -> None:
        """Ajusta la escala de cada canal para que su señal entre en el carril.

        Es «Ajustar al panel». Toma el mayor apartamiento respecto del
        desplazamiento vigente en la ventana que se mira, y lo convierte en la
        escala del canal. Un canal plano no cambia de escala: dividir por cero
        daría infinito y dejaría el canal invisible, y además no hay ninguna
        escala "correcta" para una línea recta.

        **Se mide después de restar el offset**, no antes: si no, un canal
        corrido pediría una escala enorme para entrar y la señal quedaría
        aplastada contra el eje.

        Args:
            window_index: qué ventana se usa para medir. Por omisión, la actual.

        Raises:
            WindowOutOfRangeError: si la ventana pedida no existe.
        """
        ventana = self._current_window if window_index is None else window_index
        self._check_window(ventana)
        inicio, fin = window_to_samples(ventana, self._recording.sampling_rate)
        for nombre in self._channels_under_amplitude():
            tramo = self._recording.get_segment(inicio, fin, [nombre])
            if tramo.size == 0:
                continue
            apartamiento = float(np.max(np.abs(tramo - self.offset_uv(nombre))))
            if apartamiento <= 0.0 or not np.isfinite(apartamiento):
                continue
            self.set_scale_uv(nombre, apartamiento)

    # -- Página visible -----------------------------------------------------

    @property
    def viewport(self) -> Viewport:
        """El tramo del registro que se está mirando.

        **Devuelve el objeto y no una copia**, a diferencia de
        `visible_channels`. No es una inconsistencia: una lista prestada se
        puede reordenar sin pasar por el setter, y un `Viewport` es inmutable,
        así que la única forma de cambiar la página es `set_viewport()`, que es
        el único lugar que avisa.
        """
        return self._viewport

    def set_viewport(self, viewport: Viewport) -> None:
        """Reemplaza la página visible y avisa a los suscriptos.

        Es el **único** camino: todo el desplazamiento y el zoom del programa es
        `session.set_viewport(session.viewport.<transformación>())`.

        **Vuelve temprano si la página es la que ya estaba**, por el mismo
        motivo que `go_to_window()`: avisar de más le borraría al usuario las
        líneas de ocupación sin que haya cambiado nada en pantalla.

        Raises:
            InvalidViewportError: si no es un `Viewport`, o si su duración no es
                la del registro abierto. Una página armada contra otro archivo
                dibujaría un tramo que acá no existe.
        """
        if not isinstance(viewport, Viewport):
            raise InvalidViewportError(
                "No se pudo cambiar la porción de registro que se está mostrando.",
                details=(
                    f"Se esperaba un Viewport y se recibió {type(viewport).__name__}."
                ),
            )
        if viewport.duration_seconds != self._recording.duration_seconds:
            raise InvalidViewportError(
                "La porción que se pidió mostrar no corresponde a este registro.",
                details=(
                    f"El viewport dice que el registro dura "
                    f"{viewport.duration_seconds} s y dura "
                    f"{self._recording.duration_seconds} s."
                ),
            )
        if viewport == self._viewport:
            return
        self._viewport = viewport
        self._notify_view_changed(viewport)

    def add_view_listener(self, callback: Callable[[Viewport], None]) -> None:
        """Registra a quién avisarle cuando cambia la página visible.

        Existe por el mismo argumento que `add_window_listener()` y para el
        mismo riesgo. Hoy dependen de enterarse dos: el medidor de ocupación,
        que mide fracciones **de la página** y cuyas líneas dejan de valer
        cuando la página cambia de ancho, y el visualizador, que cachea la
        envolvente de lo que dibuja.

        Raises:
            PsgLabError: si lo que se registra no se puede llamar. Un callback
                que no es invocable falla recién la próxima vez que el usuario
                mueve la vista, lejos de donde está el error.
        """
        if not callable(callback):
            raise PsgLabError(
                "No se pudo registrar quién debe enterarse de los cambios de vista.",
                details=(
                    f"Se esperaba algo invocable y se recibió "
                    f"{type(callback).__name__}."
                ),
            )
        self._view_listeners.append(callback)

    def _notify_view_changed(self, viewport: Viewport) -> None:
        """Le avisa a todos los suscriptos que la página cambió."""
        for avisar in self._view_listeners:
            avisar(viewport)

    # -- Herramienta activa -------------------------------------------------

    @property
    def active_tool(self) -> str | None:
        """Nombre de la **herramienta exclusiva** activa, o None si no hay.

        Es un solo nombre a propósito, y por eso significa menos de lo que
        parece: `Tool.exclusive` documenta que sólo se excluyen entre sí las que
        se quedan con el clic del mouse —lupa, anotador y medidor de ocupación—,
        mientras que la banda de amplitud y los dos paneles declaran
        `exclusive = False` y están activos **a la vez** que una de aquellas. Un
        único `str` no puede representar ese conjunto, así que representa la
        exclusiva; los paneles los gestiona la ventana principal.
        """
        return self._active_tool

    def set_active_tool(self, tool_name: str | None) -> None:
        """Registra cuál es la herramienta exclusiva activa.

        **Sólo cambia el nombre.** `Session` no conoce instancias de
        herramientas, así que no puede llamar a `Tool.deactivate()`: la
        desactivación real la hace la ventana principal, que es quien las tiene.

        Tampoco valida el nombre contra el registro de herramientas: importar
        `psglab.tools.registry` desde `core/` cerraría un ciclo
        —`core.session` → `tools.registry` → `tools.base` → `core.session`—.
        Para `Session` el nombre es un texto opaco, y quien comprueba que exista
        es la ventana principal, que ya conoce el registro.
        """
        self._active_tool = tool_name
