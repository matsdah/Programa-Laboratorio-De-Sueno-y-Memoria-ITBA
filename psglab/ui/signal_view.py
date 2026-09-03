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
`psglab/ui/channel_selector.py`; acá se los dibuja).
"""

import pyqtgraph as pg

from psglab.core.session import Session


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

    def sample_at(self, x_pixel: float) -> int:
        """Muestra del registro que cae bajo una coordenada horizontal.

        Lo usan las herramientas que trabajan con el mouse (anotador, lupa,
        ocupación) para traducir un clic a una posición en la señal.
        """
        raise NotImplementedError("Pendiente: convertir píxel a muestra.")
