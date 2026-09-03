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

from psglab.config import AMPLITUDE_BAND_UV
from psglab.core.session import Session
from psglab.tools.base import ViewerTool
from psglab.tools.registry import register_tool


@register_tool
class AmplitudeBandTool(ViewerTool):
    """Banda horizontal de referencia de 75 µV."""

    name = "amplitude_band"
    label = "Banda de amplitud"
    description = "Banda de 75 µV para comparar la amplitud de la señal"
    exclusive = False  # Sólo se dibuja: no compite por el clic del mouse.

    #: Altura actual de la banda, en microvoltios. Arranca en el valor del
    #: pliego y el usuario la puede cambiar con `set_height_uv`.
    height_uv: float = AMPLITUDE_BAND_UV

    def activate(self, session: Session) -> None:
        """Muestra la banda y la engancha al movimiento del mouse."""
        raise NotImplementedError("Pendiente: crear y mostrar la banda.")

    def deactivate(self) -> None:
        """Oculta la banda."""
        raise NotImplementedError("Pendiente: quitar la banda del visualizador.")

    def on_mouse_move(self, x: float, y: float) -> None:
        """Mueve la banda para que siga al mouse en vertical."""
        raise NotImplementedError("Pendiente: reposicionar la banda.")

    def set_height_uv(self, height_uv: float) -> None:
        """Cambia la altura de la banda.

        Por defecto son 75 µV, pero se deja configurable: hay criterios que
        usan otros umbrales según el montaje y la edad del participante.
        """
        raise NotImplementedError("Pendiente: cambiar la altura de la banda.")

    def band_height_pixels(self, scale_uv: float, plot_height_px: float) -> float:
        """Traduce la altura en µV a píxeles según la escala del canal.

        Es la cuenta que mantiene honesta a la herramienta cuando el usuario
        cambia la amplitud.
        """
        raise NotImplementedError("Pendiente: convertir microvoltios a píxeles.")
