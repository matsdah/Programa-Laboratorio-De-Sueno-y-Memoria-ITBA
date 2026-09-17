"""La reproducción: la página avanza sola, como en EDFbrowser.

Es un reloj y nada más. Cada 40 ms mira cuánto tiempo real pasó, lo multiplica
por la velocidad elegida y **avisa cuántos segundos de registro corresponde
avanzar**. Quien escucha —la ventana principal— mueve la página con
`Viewport.panned()`, que es el mismo camino que Mayús+→.

## Por qué no conoce la sesión

Por lo mismo que `Tool` no conoce Qt: así se testea sin armar un registro. La
regla de qué pasa al llegar al final, o con el registro entero en pantalla, es
de la ventana, que es la que tiene la página. Y la época **no se toca**: la
reproducción sólo mueve la vista, por decisión del usuario del hito 24.

## Por qué mide el tiempo en vez de contar pasos

Porque un paso no dura 40 ms: dura 40 ms **o lo que tarde en dibujarse la
página**, lo que sea más largo. Una página de cinco minutos con 32 canales a
1000 Hz puede tardar más que eso, y un reloj que sumara 40 ms por paso
reproduciría más lento de lo que dice, sin avisar. Midiendo, la velocidad es
la pedida y lo que se pierde es fluidez, que es lo que corresponde perder.

**El paso se limita a un segundo de tiempo real.** Si la máquina se detiene
—un diálogo modal, una suspensión—, el paso siguiente no puede traer media
hora de golpe y saltarse el registro.

Cubre del pliego: V1_F de "Navegación en la señal" (avanzar por el registro
sin apretar una tecla por página).
"""

import time
from collections.abc import Callable
from typing import Final

from PySide6.QtCore import QObject, QTimer, Signal

from psglab.utils.errors import InvalidPlaybackSpeedError

#: Las velocidades que se ofrecen, como múltiplos del tiempo real. 1× es la de
#: EDFbrowser: una página de 30 s tarda 30 s. Las rápidas son las de revisar
#: una noche: a 30× pasa una época por segundo.
PLAYBACK_SPEEDS: Final[tuple[float, ...]] = (0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)

#: Con qué velocidad arranca el programa.
DEFAULT_SPEED: Final[float] = 1.0

#: Cada cuánto se avanza, en milisegundos. 40 ms son 25 cuadros por segundo,
#: que es lo que se percibe como movimiento continuo.
TICK_MS: Final[int] = 40

#: El paso más largo, en segundos de tiempo real. Ver el docstring del módulo.
MAX_STEP_SECONDS: Final[float] = 1.0


def speed_text(speed: float) -> str:
    """Una velocidad como la lee el usuario: «1×», «0,5×»."""
    return f"{speed:g}×".replace(".", ",")


class PlaybackClock(QObject):
    """El reloj de la reproducción.

    Emite `advanced` con los segundos de registro que hay que avanzar en cada
    paso, y `playing_changed` cuando arranca o se detiene.

    Args:
        parent: el dueño de Qt. El reloj se detiene solo al destruirse.
        clock: de dónde sale la hora, en segundos. Los tests pasan uno falso
            y llaman a `_tick()` a mano, sin esperar al temporizador.
    """

    #: Segundos de registro que corresponde avanzar.
    advanced = Signal(float)
    #: True al arrancar, False al detenerse.
    playing_changed = Signal(bool)

    def __init__(
        self,
        parent: QObject | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Crea el reloj detenido, a la velocidad de fábrica."""
        super().__init__(parent)
        self._reloj = clock
        self._velocidad = DEFAULT_SPEED
        #: La hora del paso anterior. None mientras está detenido.
        self._anterior: float | None = None
        self._temporizador = QTimer(self)
        self._temporizador.setInterval(TICK_MS)
        self._temporizador.timeout.connect(self._tick)

    @property
    def is_playing(self) -> bool:
        """Si está reproduciendo."""
        return self._anterior is not None

    @property
    def speed(self) -> float:
        """La velocidad, como múltiplo del tiempo real."""
        return self._velocidad

    @speed.setter
    def speed(self, value: float) -> None:
        """Cambia la velocidad, aunque esté reproduciendo.

        Raises:
            InvalidPlaybackSpeedError: si no es una de `PLAYBACK_SPEEDS`.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (
            value not in PLAYBACK_SPEEDS
        ):
            raise InvalidPlaybackSpeedError(
                "No se puede reproducir a esa velocidad.",
                details=(
                    f"Se pidió {value!r}; las disponibles son "
                    f"{', '.join(speed_text(v) for v in PLAYBACK_SPEEDS)}."
                ),
            )
        self._velocidad = float(value)

    def start(self) -> None:
        """Arranca. Si ya estaba reproduciendo, no hace nada."""
        if self.is_playing:
            return
        self._anterior = self._reloj()
        self._temporizador.start()
        self.playing_changed.emit(True)

    def stop(self) -> None:
        """Se detiene. Si ya estaba detenido, no hace nada ni avisa."""
        if not self.is_playing:
            return
        self._temporizador.stop()
        self._anterior = None
        self.playing_changed.emit(False)

    def toggle(self) -> None:
        """Arranca si estaba detenido y se detiene si estaba reproduciendo."""
        if self.is_playing:
            self.stop()
        else:
            self.start()

    def _tick(self) -> None:
        """Un paso: cuánto pasó desde el anterior, por la velocidad."""
        if self._anterior is None:
            return
        ahora = self._reloj()
        # Un reloj que retrocede no debería existir, pero un cero es mejor que
        # un avance negativo: la página iría para atrás.
        transcurrido = min(max(ahora - self._anterior, 0.0), MAX_STEP_SECONDS)
        self._anterior = ahora
        if transcurrido > 0:
            self.advanced.emit(transcurrido * self._velocidad)
