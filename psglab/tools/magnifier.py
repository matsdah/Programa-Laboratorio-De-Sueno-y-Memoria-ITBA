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
from psglab.utils.errors import InvalidScaleError
from psglab.utils.validation import check_finite

#: Tamaño inicial de la lupa, en segundos de señal. Un segundo es el orden
#: de un huso de sueño, que es justamente lo que la herramienta existe para
#: mirar de cerca.
RADIO_INICIAL_SEGUNDOS: float = 1.0

#: Aumento inicial. Como el radio, se termina de afinar con la ventana
#: abierta (hito 6): acá vale un valor que ya sirve para distinguir un huso
#: de un artefacto.
ZOOM_INICIAL: float = 4.0


@register_tool
class MagnifierTool(ViewerTool):
    """Lupa circular con contador de clics."""

    name = "magnifier"
    label = "Lupa"
    description = "Ampliar una porción de la señal y contar picos con el mouse"

    def __init__(self) -> None:
        self._session: Session | None = None
        #: Dónde está la lupa. `None` mientras el mouse no entró en el
        #: visualizador: no hay que dibujar un círculo en una posición
        #: inventada.
        self._x_seconds: float | None = None
        self._y_uv: float = 0.0
        self._radius_seconds: float = RADIO_INICIAL_SEGUNDOS
        self._zoom: float = ZOOM_INICIAL
        self._clicks: int = 0

    def activate(self, session: Session) -> None:
        """Empieza a publicar la lupa y queda a la espera del mouse."""
        self._session = session
        self.notify_changed()

    def deactivate(self) -> None:
        """Deja de publicar la lupa. El contador queda como estaba.

        Conservar la cuenta es deliberado: el usuario cuenta picos, apaga la
        lupa para ver la señal sin el círculo encima, y vuelve. Reiniciarla al
        desactivar le perdería el trabajo sin avisar; para eso está
        `reset_count()`.
        """
        self._session = None
        self._x_seconds = None
        self.notify_changed()

    def on_mouse_move(self, x: float, y: float) -> None:
        """Mueve la lupa al punto donde está el mouse (V1_F)."""
        if self._session is None:
            return
        self._x_seconds, self._y_uv = x, y
        self.notify_changed()

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Suma un pico al contador (V2_F).

        El botón derecho descuenta, para poder corregir un clic de más sin
        tener que reiniciar la cuenta.
        """
        if self._session is None:
            return
        if button == "right":
            # No baja de cero: una cuenta de picos negativa no significa nada, y
            # el usuario que descuenta de más esperaría quedar en cero.
            self._clicks = max(0, self._clicks - 1)
        elif button == "left":
            self._clicks += 1
        else:
            return
        self.notify_changed()

    def set_radius_seconds(self, radius_seconds: float) -> None:
        """Cambia el tamaño del círculo de la lupa.

        En segundos y no en píxeles: `tools/base.py` declara que una herramienta
        nunca recibe píxeles, y esta no tiene forma de conocerlos. El
        visualizador sabe cuántos píxeles son.

        Raises:
            InvalidScaleError: si el radio no es un número finito y positivo.
                Un círculo de radio cero no se ve, y el usuario lo buscaría en
                la pantalla sin encontrarlo.
        """
        check_finite(
            radius_seconds,
            error=InvalidScaleError,
            message="El tamaño de la lupa no sirve para dibujarla.",
            details="Se esperaba un número finito y positivo de segundos.",
        )
        if radius_seconds <= 0:
            raise InvalidScaleError(
                "El tamaño de la lupa no sirve para dibujarla.",
                details=f"radius_seconds = {radius_seconds}, se esperaba un número positivo.",
            )
        self._radius_seconds = radius_seconds
        self.notify_changed()

    def set_zoom(self, factor: float) -> None:
        """Cambia el factor de ampliación.

        Raises:
            InvalidScaleError: si el factor no es finito y mayor que cero. Un
                factor de 1 es válido y significa "sin ampliar"; uno de 0
                colapsaría la señal y uno negativo la daría vuelta.
        """
        check_finite(
            factor,
            error=InvalidScaleError,
            message="El aumento de la lupa no sirve para dibujarla.",
            details="Se esperaba un número finito y positivo.",
        )
        if factor <= 0:
            raise InvalidScaleError(
                "El aumento de la lupa no sirve para dibujarla.",
                details=f"factor = {factor}, se esperaba un número positivo.",
            )
        self._zoom = factor
        self.notify_changed()

    def overlays(self) -> Sequence[Overlay]:
        """El círculo de aumento donde está el mouse, o nada si está desactivada.

        Tampoco dibuja nada antes de que el mouse haya entrado al visualizador:
        un círculo en una posición inventada aparecería solo al activar la
        herramienta, lejos de donde el usuario está mirando.
        """
        if self._session is None or self._x_seconds is None:
            return ()
        return (
            CircleOverlay(
                tool_name=self.name,
                x_seconds=self._x_seconds,
                y_uv=self._y_uv,
                radius_seconds=self._radius_seconds,
                zoom=self._zoom,
            ),
        )

    @property
    def click_count(self) -> int:
        """Cantidad de picos contados hasta el momento."""
        return self._clicks

    def reset_count(self) -> None:
        """Pone el contador en cero."""
        self._clicks = 0
        self.notify_changed()
