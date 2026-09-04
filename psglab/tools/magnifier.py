"""Herramienta Lupa: zoom circular y contador de picos.

Abre un círculo que sigue al mouse y amplía la porción de señal que queda
debajo, para mirar de cerca un detalle sin perder de vista la ventana
completa. Sirve para distinguir un huso de sueño de un artefacto, que a
escala de 30 segundos son casi indistinguibles.

La segunda función (V2_F) es un contador de clics: el usuario va marcando los
picos de la señal y la herramienta lleva la cuenta.

Cubre del pliego: V1_F, V2_F de "Herramienta Lupa".
"""

from collections.abc import Sequence

from psglab.core.session import Session
from psglab.tools.base import CircleOverlay, Overlay, ViewerTool
from psglab.tools.registry import register_tool


@register_tool
class MagnifierTool(ViewerTool):
    """Lupa circular con contador de clics."""

    name = "magnifier"
    label = "Lupa"
    description = "Ampliar una porción de la señal y contar picos con el mouse"

    def activate(self, session: Session) -> None:
        """Empieza a publicar la lupa y queda a la espera del mouse."""
        raise NotImplementedError("Pendiente: guardar la sesión y publicar la lupa.")

    def deactivate(self) -> None:
        """Deja de publicar la lupa. El contador queda como estaba."""
        raise NotImplementedError("Pendiente: dejar de publicar la lupa y avisar.")

    def on_mouse_move(self, x: float, y: float) -> None:
        """Mueve la lupa al punto donde está el mouse (V1_F)."""
        raise NotImplementedError("Pendiente: reposicionar la lupa y avisar.")

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Suma un pico al contador (V2_F).

        El botón derecho descuenta, para poder corregir un clic de más sin
        tener que reiniciar la cuenta.
        """
        raise NotImplementedError("Pendiente: incrementar o descontar el contador.")

    def set_radius_seconds(self, radius_seconds: float) -> None:
        """Cambia el tamaño del círculo de la lupa.

        En segundos y no en píxeles: `tools/base.py` declara que una herramienta
        nunca recibe píxeles, y esta no tiene forma de conocerlos. El
        visualizador sabe cuántos píxeles son.
        """
        raise NotImplementedError("Pendiente: cambiar el radio y avisar.")

    def set_zoom(self, factor: float) -> None:
        """Cambia el factor de ampliación."""
        raise NotImplementedError("Pendiente: cambiar el factor de zoom.")

    def overlays(self) -> Sequence[Overlay]:
        """El círculo de aumento donde está el mouse, o nada si está desactivada."""
        raise NotImplementedError("Pendiente: devolver la lupa como CircleOverlay.")

    @property
    def click_count(self) -> int:
        """Cantidad de picos contados hasta el momento."""
        raise NotImplementedError("Pendiente: devolver el contador.")

    def reset_count(self) -> None:
        """Pone el contador en cero."""
        raise NotImplementedError("Pendiente: reiniciar el contador.")
