"""Visualizador de las ondas: el corazón de la interfaz.

Dibuja los canales visibles de la ventana de 30 segundos actual, con el
nombre y la clase de cada uno y la escala de amplitud en microvoltios a la
izquierda.

Sobre la escala vertical: la relación píxeles/µV se mantiene explícita y no
se deja librada al tamaño de la ventana. El pliego pide, en el rol UX/UI,
"pensar en el tamaño de la pantalla con la deformación potencial de la onda";
si la escala dependiera del alto disponible, la misma señal se vería distinta
en dos computadoras y el criterio visual del scoring dejaría de ser
comparable entre personas.

Este módulo recorre el camino V1_P → V5_F del pliego: empieza mostrando los
canales fijos (ojos, C3, C4, EMG) y termina mostrando cualquier canal con
control de amplitud por canal. Es el mismo archivo el que evoluciona.

Cubre del pliego: V1_P, V2_P, V4_F, V5_F de "Visualización de la señal", y la
mitad de dibujo de V3_P (la elección de qué canales mostrar la resuelve
`psglab/ui/channel_selector.py`; acá se los dibuja). También V1_F de "Anotación
de la señal", por `sample_at_pixel()`: es la conversión que traduce el gesto del mouse
a la posición en muestras que guarda la anotación.
"""

from collections.abc import Sequence

import pyqtgraph as pg

from psglab.core.session import Session
from psglab.tools.base import Overlay


class SignalView(pg.PlotWidget):
    """Panel de visualización de las ondas."""

    def __init__(self) -> None:
        """Crea el visualizador vacío, sin registro."""
        raise NotImplementedError("Pendiente: construir el widget de visualización.")

    def set_session(self, session: Session) -> None:
        """Asocia el visualizador a una sesión de trabajo."""
        raise NotImplementedError("Pendiente: asociar la sesión y preparar las curvas.")

    def show_window(self, window_index: int) -> None:
        """Dibuja una ventana de 30 segundos.

        Pide a `Recording.get_segment` sólo el tramo necesario: no se copia ni
        se recorre el registro entero, que puede durar ocho horas.
        """
        raise NotImplementedError("Pendiente: dibujar la ventana pedida.")

    def refresh(self) -> None:
        """Redibuja la ventana actual con la configuración vigente."""
        raise NotImplementedError("Pendiente: redibujar la ventana actual.")

    # -- Lo que dibujan las herramientas ------------------------------------

    def set_overlays(self, overlays: Sequence[Overlay]) -> None:
        """Reemplaza todo lo que las herramientas quieren dibujar encima.

        Recibe **estado completo, no un delta**: redibujar es reemplazar. Los
        `Overlay` vienen en segundos y microvoltios, y acá es donde se traducen
        a píxeles, que es lo único que esta clase sabe hacer y ninguna otra.

        La ventana principal la llama cuando una herramienta avisa por
        `Tool.notify_changed()`.
        """
        raise NotImplementedError("Pendiente: redibujar los overlays de las herramientas.")

    # -- Canales (V3_P, V4_F) ----------------------------------------------

    def set_visible_channels(self, channel_names: list[str]) -> None:
        """Define qué canales se dibujan y en qué orden vertical."""
        raise NotImplementedError("Pendiente: reconstruir las curvas visibles.")

    def channel_label(self, channel_name: str) -> str:
        """Texto que acompaña al canal: nombre y clase detectada.

        Ejemplo: "C3 (EEG)". El pliego pide mostrar la clase junto al nombre
        para saber qué se está viendo (V4_F).
        """
        raise NotImplementedError("Pendiente: componer el nombre con la clase.")

    # -- Amplitud (V2_P, V5_F) ---------------------------------------------

    def increase_amplitude(self) -> None:
        """Aumenta la amplitud y actualiza la escala mostrada (flecha Arriba)."""
        raise NotImplementedError("Pendiente: aumentar la amplitud y redibujar.")

    def decrease_amplitude(self) -> None:
        """Reduce la amplitud y actualiza la escala mostrada (flecha Abajo)."""
        raise NotImplementedError("Pendiente: reducir la amplitud y redibujar.")

    def update_amplitude_scale(self) -> None:
        """Redibuja la escala en µV de la izquierda.

        La escala tiene que reflejar la amplitud real de cada canal: si el
        usuario cambió la ganancia de un solo canal, la referencia de ese
        canal cambia y la de los demás no (V5_F).
        """
        raise NotImplementedError("Pendiente: redibujar la escala en microvoltios.")

    # -- Coordenadas --------------------------------------------------------
    #
    # El visualizador es el **único** que convierte **desde píxeles**, porque
    # es el único que conoce el ancho de la pantalla y la ventana que está
    # dibujando:
    #
    #     píxeles  --seconds_at_pixel-->         segundos  (0 .. 30)
    #     píxeles  --window_fraction_at_pixel--> fracción  (0 .. 1)
    #     píxeles  --sample_at_pixel-->          muestras  (0 .. n_samples)
    #
    # Las conversiones **entre unidades no gráficas** —segundos, fracción,
    # muestras, ventanas— no van acá sino en `psglab/core/windows.py`, que es
    # su único lugar y se puede testear sin abrir una ventana. Estos tres
    # métodos son un píxel→unidad y después una llamada a `windows`; no
    # reimplementan la aritmética.
    #
    # Las herramientas nunca reciben píxeles: la ventana principal convierte
    # antes de avisarles. `ViewerTool` recibe segundos, `OccupancyLine` guarda
    # fracciones y el anotador guarda muestras. Ver `psglab/tools/base.py`.

    def seconds_at_pixel(self, x_pixel: float) -> float:
        """Segundos desde el inicio de la ventana bajo una coordenada horizontal.

        Es la unidad que reciben los métodos de mouse de `ViewerTool`, así que
        esta conversión es la que aplica la ventana principal antes de avisarle
        a la herramienta activa.
        """
        raise NotImplementedError("Pendiente: convertir píxel a segundos de la ventana.")

    def window_fraction_at_pixel(self, x_pixel: float) -> float:
        """Posición dentro de la ventana, de 0 (inicio) a 1 (final).

        La usa el medidor de ocupación, que mide proporciones del ancho y no
        tiempos: con esta unidad el porcentaje sigue siendo correcto aunque el
        usuario redimensione la ventana del programa.
        """
        raise NotImplementedError("Pendiente: convertir píxel a fracción de la ventana.")

    def sample_at_pixel(self, x_pixel: float) -> int:
        """Muestra del registro que cae bajo una coordenada horizontal.

        La usa el anotador, que guarda las posiciones en muestras porque es lo
        que exige "Anotaciones.txt" y lo único que sobrevive a un cambio de
        zoom.
        """
        raise NotImplementedError("Pendiente: convertir píxel a muestra.")
