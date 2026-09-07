"""Herramienta de amplitud: banda de referencia de 75 µV.

El usuario pasa una banda horizontal por encima de la señal para saber de un
vistazo si la amplitud supera los 75 µV. Es el criterio clásico de las ondas
lentas, y hacerlo a ojo sin referencia es poco confiable.

La banda se dibuja en microvoltios, no en píxeles: si el usuario cambia la
amplitud de un canal, la banda se ajusta sola y sigue midiendo 75 µV reales.
Ese es todo el sentido de la herramienta, y es lo que el pliego pide cuando
dice que "debe adaptarse a la amplitud de la señal elegida por el usuario".

Cubre del pliego: V1_F de "Herramienta de amplitud".
"""

from collections.abc import Sequence

from psglab.config import AMPLITUDE_BAND_UV
from psglab.core.session import Session
from psglab.tools.base import BandOverlay, Overlay, ViewerTool
from psglab.tools.registry import register_tool
from psglab.utils.errors import InvalidScaleError
from psglab.utils.units import MICROVOLT
from psglab.utils.validation import check_finite


@register_tool
class AmplitudeBandTool(ViewerTool):
    """Banda horizontal de referencia de 75 µV."""

    name = "amplitude_band"
    label = "Banda de amplitud"
    #: El número y la unidad salen de `config` y de `utils.units`, no escritos a
    #: mano: este texto lo lee el usuario en la barra de herramientas, y si
    #: alguien cambiara la constante, un literal acá le mentiría.
    description = (
        f"Banda de {AMPLITUDE_BAND_UV:.0f} {MICROVOLT} "
        "para comparar la amplitud de la señal"
    )
    exclusive = False  # Sólo se dibuja: no compite por el clic del mouse.

    #: Altura actual de la banda, en microvoltios. Arranca en el valor del
    #: pliego y el usuario la puede cambiar con `set_height_uv`.
    height_uv: float = AMPLITUDE_BAND_UV

    def __init__(self) -> None:
        self._session: Session | None = None
        #: Dónde está centrada la banda, en µV. Arranca en la línea de base del
        #: canal, que es donde el usuario la va a encontrar antes de mover el
        #: mouse.
        self._y_center_uv: float = 0.0

    def activate(self, session: Session) -> None:
        """Empieza a publicar la banda y queda a la espera del mouse."""
        self._session = session
        self._y_center_uv = 0.0
        self.notify_changed()

    def deactivate(self) -> None:
        """Deja de publicar la banda."""
        self._session = None
        self.notify_changed()

    def on_mouse_move(self, x: float, y: float) -> None:
        """Mueve la banda para que siga al mouse en vertical.

        Sólo mira `y`: la banda cruza la ventana entera, así que la posición
        horizontal del mouse no la cambia.
        """
        if self._session is None:
            return
        self._y_center_uv = y
        self.notify_changed()

    def set_height_uv(self, height_uv: float) -> None:
        """Cambia la altura de la banda.

        Por defecto son 75 µV, pero se deja configurable: hay criterios que
        usan otros umbrales según el montaje y la edad del participante.

        Raises:
            InvalidScaleError: si la altura no es un número finito y positivo.
                Una banda de altura cero o negativa no se dibuja, y el usuario
                la buscaría en la pantalla sin encontrarla.
        """
        check_finite(
            height_uv,
            error=InvalidScaleError,
            message="La altura de la banda de amplitud no sirve para dibujarla.",
            details="Se esperaba un número finito y positivo de microvoltios.",
        )
        if height_uv <= 0:
            raise InvalidScaleError(
                "La altura de la banda de amplitud no sirve para dibujarla.",
                details=f"height_uv = {height_uv}, se esperaba un número positivo.",
            )
        self.height_uv = height_uv
        self.notify_changed()

    def _channel(self) -> str | None:
        """Sobre qué canal va la banda.

        El pliego pide que se adapte a la amplitud de **la señal elegida por el
        usuario**, así que es el canal seleccionado. Si no hay ninguno, cae al
        primero visible: la herramienta tiene que poder usarse apenas se abre un
        registro, antes de que el usuario elija nada.

        Hace falta porque `Session.scale_uv()` es por canal y `BandOverlay`
        tiene que decir a cuál se refiere; si no, 75 µV no tienen una única
        traducción a píxeles.
        """
        if self._session is None:
            return None
        elegidos = self._session.selected_channels or self._session.visible_channels
        return elegidos[0] if elegidos else None

    def overlays(self) -> Sequence[Overlay]:
        """La banda, en microvoltios, centrada donde está el mouse.

        **En µV y no en píxeles.** La conversión a pantalla la hace el
        visualizador, que es el único que sabe con qué escala está dibujado cada
        canal; por eso la banda sigue midiendo 75 µV reales aunque el usuario
        cambie la amplitud, que es todo el sentido de la herramienta.

        Devuelve la secuencia vacía si está desactivada o si el registro no
        tiene ningún canal que mostrar.
        """
        canal = self._channel()
        if canal is None:
            return ()
        return (
            BandOverlay(
                tool_name=self.name,
                y_center_uv=self._y_center_uv,
                height_uv=self.height_uv,
                channel_name=canal,
            ),
        )
