"""Estado de la sesión de trabajo del usuario.

Reúne todo lo que el usuario tiene abierto y configurado en un momento dado:
qué registro, qué scoring, qué anotaciones, en qué ventana está parado, qué
canales ve y con qué amplitud.

Este objeto es el que la interfaz consulta para dibujarse y el que modifica
cuando el usuario hace algo. Mantenerlo fuera de `psglab.ui` es lo que permite
testear la navegación y el manejo de amplitudes sin abrir una ventana.

Cubre del pliego: V1_F de "Navegación en la señal"; V2_P, V3_P, V5_F de
"Visualización de la señal".
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
        """
        raise NotImplementedError("Pendiente: inicializar el estado de la sesión.")

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
        raise NotImplementedError("Pendiente: devolver el registro abierto.")

    @property
    def scoring(self) -> Scoring:
        """Scoring del registro abierto."""
        raise NotImplementedError("Pendiente: devolver el scoring.")

    @property
    def annotations(self) -> AnnotationSet:
        """Anotaciones del registro abierto."""
        raise NotImplementedError("Pendiente: devolver el conjunto de anotaciones.")

    # -- Navegación entre ventanas (V1_F de "Navegación") -------------------

    @property
    def current_window(self) -> int:
        """Ventana actual, índice base 0."""
        raise NotImplementedError("Pendiente: devolver la ventana actual.")

    @property
    def n_windows(self) -> int:
        """Cantidad total de ventanas del registro (VENMAX)."""
        raise NotImplementedError("Pendiente: devolver la cantidad de ventanas.")

    def go_to_window(self, window_index: int) -> None:
        """Salta a una ventana concreta.

        Lo usa el clic sobre el histograma (V4_F del histograma).

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro.
        """
        raise NotImplementedError("Pendiente: validar el índice y saltar a la ventana.")

    def next_window(self) -> None:
        """Avanza una ventana. En la última no hace nada."""
        raise NotImplementedError("Pendiente: avanzar una ventana.")

    def previous_window(self) -> None:
        """Retrocede una ventana. En la primera no hace nada."""
        raise NotImplementedError("Pendiente: retroceder una ventana.")

    # -- Canales visibles (V3_P, V4_F de "Visualización") -------------------

    @property
    def visible_channels(self) -> list[str]:
        """Nombres de los canales que se están mostrando, en orden."""
        raise NotImplementedError("Pendiente: devolver los canales visibles.")

    def set_visible_channels(self, channel_names: list[str]) -> None:
        """Define qué canales se muestran y en qué orden."""
        raise NotImplementedError("Pendiente: validar y asignar los canales visibles.")

    @property
    def selected_channels(self) -> list[str]:
        """Canales seleccionados por el usuario.

        Si hay canales seleccionados, los cambios de amplitud se aplican sólo
        a ellos; si no hay ninguno, se aplican a todos los visibles (V5_F).
        """
        raise NotImplementedError("Pendiente: devolver los canales seleccionados.")

    def set_selected_channels(self, channel_names: list[str]) -> None:
        """Define los canales sobre los que actúan los cambios de amplitud."""
        raise NotImplementedError("Pendiente: asignar los canales seleccionados.")

    # -- Amplitud (V2_P, V5_F de "Visualización") ---------------------------

    def scale_uv(self, channel_name: str) -> float:
        """Escala vertical de un canal, en microvoltios.

        Es el número que se muestra en la escala de la izquierda del
        visualizador (V1_P).
        """
        raise NotImplementedError("Pendiente: devolver la escala del canal.")

    def increase_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Aumenta la amplitud (flecha "Arriba").

        Se aplica a los canales seleccionados, o a todos los visibles si no
        hay ninguno seleccionado.

        Args:
            factor: cuánto se multiplica la amplitud por cada pulsación. Por
                defecto, el paso de `config`.
        """
        raise NotImplementedError("Pendiente: aumentar la amplitud de los canales afectados.")

    def decrease_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Reduce la amplitud (flecha "Abajo"). Mismo criterio de alcance."""
        raise NotImplementedError("Pendiente: reducir la amplitud de los canales afectados.")

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
        """
        raise NotImplementedError("Pendiente: validar y asignar la escala del canal.")

    # -- Herramienta activa -------------------------------------------------

    @property
    def active_tool(self) -> str | None:
        """Nombre de la herramienta activa, o None si no hay ninguna."""
        raise NotImplementedError("Pendiente: devolver la herramienta activa.")

    def set_active_tool(self, tool_name: str | None) -> None:
        """Activa una herramienta y desactiva la anterior."""
        raise NotImplementedError("Pendiente: cambiar la herramienta activa.")
