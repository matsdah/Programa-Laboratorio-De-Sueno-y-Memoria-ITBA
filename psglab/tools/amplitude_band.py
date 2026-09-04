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
from psglab.utils.units import MICROVOLT


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

    def activate(self, session: Session) -> None:
        """Empieza a publicar la banda y queda a la espera del mouse."""
        raise NotImplementedError("Pendiente: guardar la sesión y publicar la banda.")

    def deactivate(self) -> None:
        """Deja de publicar la banda."""
        raise NotImplementedError("Pendiente: dejar de publicar la banda y avisar.")

    def on_mouse_move(self, x: float, y: float) -> None:
        """Mueve la banda para que siga al mouse en vertical."""
        raise NotImplementedError("Pendiente: reposicionar la banda y avisar.")

    def set_height_uv(self, height_uv: float) -> None:
        """Cambia la altura de la banda.

        Por defecto son 75 µV, pero se deja configurable: hay criterios que
        usan otros umbrales según el montaje y la edad del participante.
        """
        raise NotImplementedError("Pendiente: cambiar la altura de la banda.")

    def overlays(self) -> Sequence[Overlay]:
        """La banda, en microvoltios, centrada donde está el mouse.

        **En µV y no en píxeles.** La conversión a pantalla la hace el
        visualizador, que es el único que sabe con qué escala está dibujado cada
        canal; por eso la banda sigue midiendo 75 µV reales aunque el usuario
        cambie la amplitud, que es todo el sentido de la herramienta.
        """
        raise NotImplementedError("Pendiente: devolver la banda como BandOverlay.")
