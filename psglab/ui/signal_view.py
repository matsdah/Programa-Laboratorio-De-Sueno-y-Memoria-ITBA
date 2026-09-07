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

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF

from psglab.config import WINDOW_SECONDS
from psglab.core.session import Session
from psglab.core.windows import (
    seconds_to_sample,
    seconds_to_window_fraction,
    window_to_samples,
)
from psglab.tools.base import (
    BandOverlay,
    CircleOverlay,
    Overlay,
    SegmentOverlay,
    SpanOverlay,
)
from psglab.ui.grid import GridBackground

#: Separación vertical entre canales, en unidades del gráfico. Cada canal ocupa
#: su propio carril y la señal se dibuja dentro de él.
_ALTO_DE_CARRIL: float = 1.0

#: Qué fracción del carril llena una señal que alcanza justo `scale_uv`. Menos
#: de la mitad para que dos canales vecinos no se pisen cuando los dos están al
#: máximo de su escala.
_LLENADO_DEL_CARRIL: float = 0.45


class SignalView(pg.PlotWidget):
    """Panel de visualización de las ondas."""

    def __init__(self) -> None:
        """Crea el visualizador vacío, sin registro."""
        super().__init__()
        self._session: Session | None = None
        self._window_index: int = 0
        self._curves: dict[str, pg.PlotDataItem] = {}
        self._labels: list[pg.TextItem] = []
        self._overlay_items: list[object] = []
        self._visible: list[str] = []

        item = self.getPlotItem()
        item.hideButtons()
        item.setMenuEnabled(False)
        item.setMouseEnabled(x=False, y=False)
        item.hideAxis("left")
        item.setLabel("bottom", "Segundos de la ventana")
        self.grid = GridBackground(item)

    @property
    def session(self) -> Session | None:
        """La sesión que se está dibujando, o None si no hay registro abierto."""
        return self._session

    @property
    def window_seconds(self) -> float:
        """Cuánto dura la ventana que se dibuja. Es la del pliego."""
        return WINDOW_SECONDS

    def set_session(self, session: Session) -> None:
        """Asocia el visualizador a una sesión de trabajo."""
        self._session = session
        self.set_visible_channels(session.visible_channels)
        self.show_window(session.current_window)

    def show_window(self, window_index: int) -> None:
        """Dibuja una ventana de 30 segundos.

        Pide a `Recording.get_segment` sólo el tramo necesario: no se copia ni
        se recorre el registro entero, que puede durar ocho horas.
        """
        if self._session is None:
            return
        self._window_index = window_index
        registro = self._session.recording
        frecuencia = registro.sampling_rate
        inicio, fin = window_to_samples(window_index, frecuencia)

        self.getPlotItem().setXRange(0.0, self.window_seconds, padding=0)
        self.grid.redraw(self.window_seconds)

        for posicion, nombre in enumerate(self._visible):
            tramo = registro.get_segment(inicio, fin, [nombre])[0]
            tiempos = np.arange(len(tramo)) / frecuencia
            escala = self._session.scale_uv(nombre)
            centro = -posicion * _ALTO_DE_CARRIL
            self._curves[nombre].setData(
                tiempos, centro + (tramo / escala) * _LLENADO_DEL_CARRIL
            )
        self.update_amplitude_scale()

    def refresh(self) -> None:
        """Redibuja la ventana actual con la configuración vigente."""
        if self._session is None:
            return
        self.show_window(self._session.current_window)

    # -- Lo que dibujan las herramientas ------------------------------------

    def set_overlays(self, overlays: Sequence[Overlay]) -> None:
        """Reemplaza todo lo que las herramientas quieren dibujar encima.

        Recibe **estado completo, no un delta**: redibujar es reemplazar. Los
        `Overlay` vienen en segundos y microvoltios, y acá es donde se traducen
        a píxeles, que es lo único que esta clase sabe hacer y ninguna otra.

        La ventana principal la llama cuando una herramienta avisa por
        `Tool.notify_changed()`.
        """
        item = self.getPlotItem()
        for dibujado in self._overlay_items:
            item.removeItem(dibujado)
        self._overlay_items.clear()

        for overlay in overlays:
            dibujado = self._dibujar_overlay(overlay)
            if dibujado is not None:
                item.addItem(dibujado)
                self._overlay_items.append(dibujado)

    def _dibujar_overlay(self, overlay: Overlay) -> object | None:
        """Traduce un `Overlay` a algo que pyqtgraph sepa pintar.

        Devuelve `None` para un tipo que esta versión todavía no dibuja, en vez
        de elevar: una herramienta nueva no puede voltear el visualizador.
        """
        if isinstance(overlay, BandOverlay):
            # La banda va sobre **su** canal, que es el dato que el hito 7
            # agregó a `BandOverlay`: sin él, 75 µV no tendrían una única
            # traducción, porque la escala es por canal.
            centro = self._centro_de_carril(overlay.channel_name)
            if centro is None:
                return None
            media = self._a_carril(overlay.height_uv / 2, overlay.channel_name)
            base = centro + self._a_carril(overlay.y_center_uv, overlay.channel_name)
            return pg.LinearRegionItem(
                values=(base - media, base + media),
                orientation="horizontal",
                movable=False,
            )

        if isinstance(overlay, SpanOverlay):
            # Ocupa todo el alto de la ventana, como pide el pliego, para que se
            # vea sin importar qué canales estén visibles.
            region = pg.LinearRegionItem(
                values=(overlay.start_seconds, overlay.end_seconds), movable=False
            )
            if overlay.color:
                region.setBrush(pg.mkBrush(overlay.color + "55"))
            return region

        if isinstance(overlay, SegmentOverlay):
            referencia = self._visible[0] if self._visible else None
            return pg.PlotDataItem(
                [overlay.x1_seconds, overlay.x2_seconds],
                [
                    self._a_carril(overlay.y1_uv, referencia),
                    self._a_carril(overlay.y2_uv, referencia),
                ],
            )

        if isinstance(overlay, CircleOverlay):
            referencia = self._visible[0] if self._visible else None
            return pg.ScatterPlotItem(
                [overlay.x_seconds],
                [self._a_carril(overlay.y_uv, referencia)],
                symbol="o",
                brush=None,
                pen=pg.mkPen(width=2),
                size=30,
            )
        return None

    def _centro_de_carril(self, channel_name: str) -> float | None:
        """Dónde está dibujado el eje de un canal, o None si no está visible."""
        if channel_name not in self._visible:
            return None
        return -self._visible.index(channel_name) * _ALTO_DE_CARRIL

    def _a_carril(self, microvoltios: float, channel_name: str | None) -> float:
        """Pasa una altura en µV a unidades del gráfico, con la escala del canal.

        Es la misma cuenta que usa `show_window()` para la señal, y por eso una
        banda de 75 µV mide en pantalla exactamente lo que miden 75 µV de la
        onda: es todo el sentido de la herramienta de amplitud.
        """
        if self._session is None or channel_name is None:
            return microvoltios
        return (microvoltios / self._session.scale_uv(channel_name)) * _LLENADO_DEL_CARRIL

    # -- Canales (V3_P, V4_F) ----------------------------------------------

    def set_visible_channels(self, channel_names: list[str]) -> None:
        """Define qué canales se dibujan y en qué orden vertical."""
        item = self.getPlotItem()
        for curva in self._curves.values():
            item.removeItem(curva)
        for etiqueta in self._labels:
            item.removeItem(etiqueta)
        self._curves.clear()
        self._labels.clear()

        self._visible = list(channel_names)
        for posicion, nombre in enumerate(self._visible):
            curva = pg.PlotDataItem()
            item.addItem(curva)
            self._curves[nombre] = curva

            etiqueta = pg.TextItem(self.channel_label(nombre), anchor=(0, 0.5))
            etiqueta.setPos(0.0, -posicion * _ALTO_DE_CARRIL)
            item.addItem(etiqueta)
            self._labels.append(etiqueta)

        if self._visible:
            item.setYRange(
                -(len(self._visible) - 1) * _ALTO_DE_CARRIL - 0.5, 0.5, padding=0
            )
        self.refresh()

    def channel_label(self, channel_name: str) -> str:
        """Texto que acompaña al canal: nombre y clase detectada.

        Ejemplo: "C3 (EEG)". El pliego pide mostrar la clase junto al nombre
        para saber qué se está viendo (V4_F).

        Sin registro abierto devuelve el nombre solo: la clase la detecta el
        lector, así que antes de abrir un archivo no hay ninguna que mostrar.
        """
        if self._session is None:
            return channel_name
        try:
            canal = self._session.recording.channel_by_name(channel_name)
        except Exception:  # noqa: BLE001 - un canal que ya no está no rompe el dibujo
            return channel_name
        return f"{canal.name} ({canal.kind.value})"

    # -- Amplitud (V2_P, V5_F) ---------------------------------------------

    def increase_amplitude(self) -> None:
        """Aumenta la amplitud y actualiza la escala mostrada (flecha Arriba).

        La cuenta la hace `Session`, que es donde vive la regla —incluido que
        aumentar la amplitud **baje** el número de `scale_uv`—; acá sólo se
        redibuja.
        """
        if self._session is None:
            return
        self._session.increase_amplitude()
        self.refresh()

    def decrease_amplitude(self) -> None:
        """Reduce la amplitud y actualiza la escala mostrada (flecha Abajo)."""
        if self._session is None:
            return
        self._session.decrease_amplitude()
        self.refresh()

    def update_amplitude_scale(self) -> None:
        """Redibuja la escala en µV de la izquierda.

        La escala tiene que reflejar la amplitud real de cada canal: si el
        usuario cambió la ganancia de un solo canal, la referencia de ese
        canal cambia y la de los demás no (V5_F).
        """
        if self._session is None:
            return
        for etiqueta, nombre in zip(self._labels, self._visible):
            escala = self._session.scale_uv(nombre)
            etiqueta.setText(f"{self.channel_label(nombre)} — {escala:.0f} µV")

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

        Se recorta contra los bordes de la ventana: un clic en el margen del
        gráfico daría un segundo negativo o mayor que 30, y de ahí saldría una
        muestra fuera del registro.
        """
        vista = self.getPlotItem().vb
        segundos = float(vista.mapSceneToView(QPointF(float(x_pixel), 0.0)).x())
        return min(self.window_seconds, max(0.0, segundos))

    def window_fraction_at_pixel(self, x_pixel: float) -> float:
        """Posición dentro de la ventana, de 0 (inicio) a 1 (final).

        La usa el medidor de ocupación, que mide proporciones del ancho y no
        tiempos: con esta unidad el porcentaje sigue siendo correcto aunque el
        usuario redimensione la ventana del programa.

        Es un píxel→segundos y después `core.windows`: la aritmética entre
        unidades no gráficas vive allá y no se reimplementa acá.
        """
        return seconds_to_window_fraction(
            self.seconds_at_pixel(x_pixel), self.window_seconds
        )

    def sample_at_pixel(self, x_pixel: float) -> int:
        """Muestra del registro que cae bajo una coordenada horizontal.

        La usa el anotador, que guarda las posiciones en muestras porque es lo
        que exige "Anotaciones.txt" y lo único que sobrevive a un cambio de
        zoom.

        Igual que la anterior: píxel→segundos y después `core.windows`, que es
        quien sabe sumar el desplazamiento sobre el borde real de la ventana.
        Calcularlo como `ventana * 30 * fs` deja la anotación en la ventana de
        al lado cuando la frecuencia no es redonda.
        """
        if self._session is None:
            return 0
        return seconds_to_sample(
            self._window_index,
            self.seconds_at_pixel(x_pixel),
            self._session.recording.sampling_rate,
            self.window_seconds,
        )
