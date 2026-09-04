"""Interfaz común de las herramientas.

El pliego agrupa bajo "herramienta" cosas que se comportan de dos maneras
distintas, y el código las distingue porque el contrato de coordenadas no es
el mismo:

  - Herramientas del visualizador: actúan con el mouse sobre la ventana de la
    señal, y reciben coordenadas en segundos y microvoltios. Son la banda de
    amplitud, el medidor de ocupación, la lupa y el anotador.
  - Paneles: tienen su propia zona de la pantalla y su propio sistema de
    coordenadas. Son la Übersicht y el histograma; un clic en el histograma
    no cae "en el segundo 12 de la ventana", cae en una ventana de la noche
    entera.

Por eso hay dos clases base: `Tool`, con el ciclo de vida que comparten
todas, y `ViewerTool`, que agrega los eventos de mouse del visualizador.
Mezclarlas obligaría a documentar `x` de dos formas contradictorias.

Ninguna de las dos hereda de QObject: son objetos comunes de Python, y por
eso se las puede testear sin levantar la interfaz gráfica. Avisan de lo que
pasa por callbacks, no por señales de Qt.

Cubre del pliego: es la base de "Herramienta de amplitud", "Herramienta de
ocupación de la página", "Herramienta Lupa", "Herramienta Übersicht",
"Anotación de la señal" e "Histograma".
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from psglab.core.session import Session


@dataclass(frozen=True)
class Overlay:
    """Algo que una herramienta quiere que se dibuje sobre la señal.

    **Es dato, no dibujo.** Acá no hay ningún objeto de Qt, y por eso una
    herramienta se puede testear afirmando sobre lo que devuelve `overlays()`,
    sin abrir una ventana. Quien traduce esto a píxeles es
    `psglab/ui/signal_view.py`, que es lo único que conoce el ancho de la
    pantalla.

    Las coordenadas van en las unidades que ya documenta `ViewerTool`: `x` en
    segundos desde el inicio de la ventana, `y` en microvoltios.

    Attributes:
        tool_name: el `name` de la herramienta que lo pidió. Sirve para borrar
            lo de una sola herramienta sin tocar lo de las demás.
    """

    tool_name: str


@dataclass(frozen=True)
class BandOverlay(Overlay):
    """Banda horizontal de altura fija. La usa la herramienta de amplitud."""

    y_center_uv: float
    height_uv: float


@dataclass(frozen=True)
class SegmentOverlay(Overlay):
    """Segmento recto entre dos puntos. Lo usa el medidor de ocupación."""

    x1_seconds: float
    y1_uv: float
    x2_seconds: float
    y2_uv: float


@dataclass(frozen=True)
class SpanOverlay(Overlay):
    """Tramo de tiempo marcado y etiquetado. Lo usa el anotador."""

    start_seconds: float
    end_seconds: float
    label: str
    color: str | None = None


@dataclass(frozen=True)
class CircleOverlay(Overlay):
    """Círculo de aumento centrado en un punto. Lo usa la lupa.

    El radio va en segundos y no en píxeles: la herramienta no conoce la
    pantalla, y el visualizador sabe cuántos píxeles son.
    """

    x_seconds: float
    y_uv: float
    radius_seconds: float
    zoom: float


class Tool(ABC):
    """Algo que el usuario puede activar y desactivar.

    Attributes:
        name: identificador interno, único entre todas las herramientas.
        label: nombre que se le muestra al usuario en la barra.
        description: texto de ayuda que aparece al pasar el mouse.
        exclusive: si es True, activarla desactiva las demás herramientas
            exclusivas. Lo son las tres que se quedan con el clic del mouse
            sobre el visualizador: la lupa, el anotador y el medidor de
            ocupación. La banda de amplitud no, porque sólo se dibuja y no
            escucha clics; los paneles tampoco, porque tienen su propia zona de
            pantalla y no compiten por el mouse del visualizador.

            El valor por defecto es True, así que una herramienta que no compita
            por el mouse tiene que declarar `exclusive = False` explícitamente.
    """

    name: str = ""
    label: str = ""
    description: str = ""
    exclusive: bool = True

    #: A quién avisarle cuando cambia lo que la herramienta quiere mostrar. Lo
    #: cablea la ventana principal al activarla. **Se asigna sobre la instancia,
    #: nunca sobre la clase**: asignado en la clase, Python lo convertiría en un
    #: método ligado y la llamada le pasaría `self` de más.
    on_changed: Callable[["Tool"], None] | None = None

    def notify_changed(self) -> None:
        """Avisa de que cambió lo que la herramienta quiere mostrar.

        Callback y no señal de Qt, por la misma razón por la que `Tool` no
        hereda de `QObject`: es lo que permite testear las seis herramientas sin
        levantar la interfaz. La ventana principal engancha acá su repintado.

        No hace nada si nadie se enganchó, que es el caso de un test.
        """
        if self.on_changed is not None:
            self.on_changed(self)

    @abstractmethod
    def activate(self, session: Session) -> None:
        """Activa la herramienta sobre la sesión actual.

        Recibe la sesión y nada más: **ninguna herramienta recibe el
        visualizador ni nada de Qt**. Lo que quiera dibujar lo publica como
        datos por `overlays()` y avisa con `notify_changed()`. Es lo que
        mantiene a `tools/` sin conocer `ui/`.
        """

    @abstractmethod
    def deactivate(self) -> None:
        """Desactiva la herramienta y limpia lo que haya dibujado."""

    def on_window_changed(self, window_index: int) -> None:
        """El usuario navegó a otra ventana.

        No hace nada por defecto: una herramienta sobrescribe este método sólo
        si le interesa enterarse. El medidor de ocupación lo usa para borrar
        sus líneas (V5_F) y la Übersicht para redibujarse.
        """
        return None


class ViewerTool(Tool):
    """Herramienta que actúa con el mouse sobre la ventana de la señal.

    Las coordenadas que reciben sus métodos son siempre las del visualizador:

        x: segundos desde el inicio de la ventana de 30 segundos
        y: microvoltios

    **En el programa conviven tres unidades horizontales distintas y hay que
    convertir explícitamente entre ellas.** Confundirlas no rompe nada de forma
    visible: produce números plausibles y equivocados, que es peor.

        Unidad              Rango típico   Quién la produce
        ------------------  -------------  ---------------------------------
        píxeles             0 .. ancho     el evento de Qt
        segundos            0 .. 30        `SignalView.seconds_at_pixel()`
        fracción de ventana 0 .. 1         `SignalView.window_fraction_at_pixel()`
        muestras            0 .. n_samples `SignalView.sample_at_pixel()`

    Los métodos de esta clase reciben **segundos**, ya convertidos por el
    visualizador. Una herramienta que necesite otra unidad **la pide a
    `psglab/core/windows.py`**, que es el único lugar donde se convierte entre
    unidades: `seconds_to_window_fraction()` para el medidor de ocupación, que
    trabaja en fracción, y `seconds_to_sample()` para el anotador, que guarda
    muestras porque es lo que exige "Anotaciones.txt". Ninguna escribe la cuenta
    a mano.

    Los tres métodos de mouse no hacen nada por defecto. Cada herramienta
    sobrescribe los que necesita: la banda de amplitud sólo escucha el
    movimiento, el anotador necesita los tres.
    """

    def overlays(self) -> Sequence[Overlay]:
        """Lo que la herramienta quiere que el visualizador dibuje **ahora**.

        Devuelve el estado completo, no un delta: redibujar es reemplazar. Una
        herramienta que no dibuje nada —o que esté desactivada— devuelve la
        secuencia vacía, que es el valor por defecto.

        Este método es lo que hace testeable a una herramienta gráfica sin
        pantalla: se le mandan eventos de mouse y se afirma sobre lo que
        devuelve acá.
        """
        return ()

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Se apretó un botón del mouse sobre el visualizador.

        Args:
            x: segundos desde el inicio de la ventana.
            y: microvoltios.
            button: "left", "right" o "middle".
        """
        return None

    def on_mouse_move(self, x: float, y: float) -> None:
        """El mouse se movió sobre el visualizador."""
        return None

    def on_mouse_release(self, x: float, y: float, button: str) -> None:
        """Se soltó el botón del mouse sobre el visualizador."""
        return None
