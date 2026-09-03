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

from psglab.core.session import Session


class Tool(ABC):
    """Algo que el usuario puede activar y desactivar.

    Attributes:
        name: identificador interno, único entre todas las herramientas.
        label: nombre que se le muestra al usuario en la barra.
        description: texto de ayuda que aparece al pasar el mouse.
        exclusive: si es True, activarla desactiva las demás herramientas
            exclusivas. Lo son las que se quedan con el clic del mouse sobre
            el visualizador: la lupa y el anotador. La banda de amplitud no,
            porque sólo se dibuja; los paneles tampoco, porque no compiten por
            el mouse del visualizador.
    """

    name: str = ""
    label: str = ""
    description: str = ""
    exclusive: bool = True

    @abstractmethod
    def activate(self, session: Session) -> None:
        """Activa la herramienta sobre la sesión actual."""

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

    Los tres métodos de mouse no hacen nada por defecto. Cada herramienta
    sobrescribe los que necesita: la banda de amplitud sólo escucha el
    movimiento, el anotador necesita los tres.
    """

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
