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

from psglab.config import (
    AMPLITUDE_STEP_FACTOR,
    DEFAULT_SCALE_UV,
    MAX_SCALE_UV,
    MIN_SCALE_UV,
)
from psglab.core.annotations import AnnotationSet
from psglab.core.recording import Recording
from psglab.core.scoring import Scoring
from psglab.core.windows import count_windows
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidScaleError,
    ScoringMismatchError,
    WindowOutOfRangeError,
)
from psglab.utils.validation import check_finite, clamp


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
        self._active_tool: str | None = None

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
        if not 0 <= window_index < self.n_windows:
            raise WindowOutOfRangeError(
                f"La ventana {window_index + 1} no existe en este registro, que "
                f"tiene {self.n_windows}.",
                details=(
                    f"window_index = {window_index} (base 0), "
                    f"n_windows = {self.n_windows}."
                ),
            )
        self._current_window = window_index

    def next_window(self) -> None:
        """Avanza una ventana. En la última no hace nada.

        No elevar en el borde es deliberado: quien mantiene apretada la flecha
        derecha llega al final y se queda ahí, no recibe un error.
        """
        if self._current_window < self.n_windows - 1:
            self._current_window += 1

    def previous_window(self) -> None:
        """Retrocede una ventana. En la primera no hace nada."""
        if self._current_window > 0:
            self._current_window -= 1

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
        """
        return self._selected_channels or self._visible_channels

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
        for nombre in self._channels_under_amplitude():
            self.set_scale_uv(nombre, self._scales_uv[nombre] / factor)

    def decrease_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Reduce la amplitud (flecha "Abajo"). Mismo criterio de alcance."""
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
