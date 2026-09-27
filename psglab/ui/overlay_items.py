"""Lo que las herramientas dibujan encima de la señal.

Las herramientas publican `Overlay` en segundos y microvoltios —no conocen los
píxeles—, y esta capa los traduce a ítems de pyqtgraph sobre el gráfico de
`SignalView`: la banda de amplitud, las bandas de anotación con su rótulo, los
segmentos de la ocupación y la lente de la lupa. La geometría de los carriles
—dónde está cada canal y cuántos carriles mide un microvoltio— es del
visualizador, y la capa se la pregunta.

**Reutiliza lo que ya está dibujado.** `set_overlays()` recibe siempre el
estado completo, y con la lupa o el anotador activos eso pasa en cada
movimiento del mouse. Rehacer cada banda de anotación de la página con su
rótulo en cada movimiento era el costo; ahora un overlay que ya está dibujado
**con la misma geometría** —misma página, mismos canales, misma escala y
desplazamiento de cada uno, mismo esquema— se deja como está, y sólo se crea
lo nuevo y se saca lo que ya no va. La lente se rehace siempre: depende de
cuánto mide un píxel, que puede cambiar sin que cambie el overlay.

Cubre del pliego: V1_F de "Herramienta Lupa", por `_dibujar_lupa()`, que es lo
que **amplía** de verdad el tramo bajo el cursor: `MagnifierTool` publica el
radio y el zoom, y acá se los usa. Y el dibujo de V1_F de "Herramienta de
amplitud": la banda de 75 µV sobre el carril de su canal.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QRectF
from PySide6.QtGui import QBrush, QColor, QPainterPath
from PySide6.QtWidgets import QGraphicsItem, QGraphicsItemGroup, QGraphicsPathItem

from psglab.core.windows import seconds_to_clock_time, seconds_to_samples
from psglab.tools.base import (
    BandOverlay,
    CircleOverlay,
    Overlay,
    SegmentOverlay,
    SpanOverlay,
)
from psglab.ui import theme
from psglab.ui.fonts import font_for
from psglab.utils.units import format_amplitude

if TYPE_CHECKING:
    from psglab.ui.signal_view import SignalView

#: Dónde caen en la pila de la escena las dos herramientas que se dibujan
#: **encima** de la señal. Debajo de las curvas —que van en 0— están la grilla,
#: en −10, y la banda de la época, en −5. La lente tapa a la banda de amplitud
#: porque es la que el usuario está mirando en ese momento.
Z_DE_LA_BANDA: float = 5.0
Z_DE_LA_LENTE: float = 10.0


class OverlayLayer:
    """Los ítems que las herramientas piden dibujar sobre un `SignalView`."""

    def __init__(self, view: SignalView) -> None:
        """Arma la capa vacía sobre el gráfico de `view`."""
        self._vista = view
        #: Lo dibujado, por (overlay, geometría con que se dibujó). Una lista
        #: por clave porque dos overlays iguales son dos dibujos.
        self._dibujados: dict[tuple[Overlay, object], list[tuple[object, ...]]] = {}
        #: Los ítems en el orden de los overlays que los pidieron.
        self._items: list[object] = []

    @property
    def items(self) -> list[object]:
        """Los ítems dibujados, en el orden de los overlays que los pidieron."""
        return list(self._items)

    def set_overlays(self, overlays: Sequence[Overlay]) -> None:
        """Deja dibujado exactamente `overlays`, reutilizando lo que se pueda.

        Recibe **estado completo, no un delta**: lo que estaba y no viene se
        saca, lo que viene y no estaba se crea, y lo que estaba y viene igual
        con la misma geometría queda como está.
        """
        item = self._vista.getPlotItem()
        firma = self._vista.overlay_signature()
        anteriores = self._dibujados
        nuevos: dict[tuple[Overlay, object], list[tuple[object, ...]]] = {}
        orden: list[object] = []

        for overlay in overlays:
            clave = (overlay, firma)
            reusables = anteriores.get(clave)
            if reusables and not isinstance(overlay, CircleOverlay):
                piezas = reusables.pop(0)
            else:
                dibujado = self._dibujar(overlay)
                if dibujado is None:
                    continue
                piezas = dibujado if isinstance(dibujado, tuple) else (dibujado,)
                for pieza in piezas:
                    item.addItem(pieza)
            nuevos.setdefault(clave, []).append(piezas)
            orden.extend(piezas)

        for sobrantes in anteriores.values():
            for piezas in sobrantes:
                for pieza in piezas:
                    item.removeItem(pieza)
        self._dibujados = nuevos
        self._items = orden

    def _dibujar(self, overlay: Overlay) -> object | tuple[object, ...] | None:
        """Traduce un `Overlay` a algo que pyqtgraph sepa pintar.

        Devuelve `None` para un tipo que esta versión todavía no dibuja, en vez
        de elevar: una herramienta nueva no puede voltear el visualizador.
        """
        if isinstance(overlay, BandOverlay):
            return self._dibujar_banda(overlay)
        if isinstance(overlay, SpanOverlay):
            return self._dibujar_anotacion(overlay)
        if isinstance(overlay, SegmentOverlay):
            return self._dibujar_segmento(overlay)
        if isinstance(overlay, CircleOverlay):
            return self._dibujar_lupa(overlay)
        return None

    # -- La banda de amplitud -----------------------------------------------

    def _dibujar_banda(self, overlay: BandOverlay) -> tuple[object, ...] | None:
        """La banda de amplitud sobre **su** canal: sin canal, sus µV no
        tendrían una única traducción, porque la escala es por canal.

        **El alto es una longitud y el centro una posición**, y no se
        convierten igual: la posición resta el desplazamiento vertical del
        canal y la longitud no. Convertidas con la misma cuenta, una banda de
        75 µV sobre un canal centrado en 500 µV —un respiratorio, que se centra
        solo al abrir el registro— medía doce veces lo que debía.
        """
        vista = self._vista
        centro = vista.lane_center(overlay.channel_name)
        if centro is None:
            return None
        media = vista.height_to_lanes(overlay.height_uv / 2, overlay.channel_name)
        base = centro + vista.to_lanes(overlay.y_center_uv, overlay.channel_name)
        esquema = theme.current()
        region = pg.LinearRegionItem(
            values=(base - media, base + media),
            orientation="horizontal",
            movable=False,
            brush=pg.mkBrush(QColor(esquema.accent).lighter(160).name() + "3c"),
            pen=pg.mkPen(esquema.accent, width=2),
        )
        # **Encima de la señal, y traslúcida**: con el relleno de fábrica de
        # pyqtgraph la banda quedaba invisible sobre un trazo azul. Lo que hay
        # que poder leer son los dos bordes, que dicen dónde terminan sus µV.
        region.setZValue(Z_DE_LA_BANDA)
        return region, self._rotulo_de_la_amplitud(overlay, base + media)

    def _rotulo_de_la_amplitud(self, overlay: BandOverlay, techo: float) -> pg.TextItem:
        """Cuántos µV mide la banda y sobre qué canal, en su borde de arriba.

        Con una escala por canal, los mismos µV ocupan distinto en cada carril,
        así que la banda dice contra cuál mide. Va a la derecha de la página,
        que es donde menos tapa: la banda sigue al mouse y el mouse casi nunca
        está en el borde.
        """
        decimales = 0 if float(overlay.height_uv).is_integer() else 1
        texto = f"{format_amplitude(overlay.height_uv, decimales)} · {overlay.channel_name}"
        esquema = theme.current()
        rotulo = pg.TextItem(
            texto,
            anchor=(1, 1),
            color=theme.ink_over(esquema, esquema.accent),
            fill=pg.mkBrush(esquema.accent),
        )
        sesion = self._vista.session
        derecha = sesion.viewport.end_seconds if sesion is not None else 0.0
        rotulo.setPos(derecha, techo)
        rotulo.setZValue(Z_DE_LA_BANDA + 1)
        return rotulo

    # -- Las anotaciones -----------------------------------------------------

    def _dibujar_anotacion(self, overlay: SpanOverlay) -> object | tuple[object, ...]:
        """Una banda de todo el alto, para que se vea sin importar qué canales
        estén visibles, con los bordes del color de su clase, que se agarran
        para corregir el tramo."""
        region = pg.LinearRegionItem(
            values=(overlay.start_seconds, overlay.end_seconds), movable=False
        )
        if overlay.color:
            region.setBrush(pg.mkBrush(overlay.color + "55"))
            for linea in region.lines:
                linea.setPen(pg.mkPen(overlay.color, width=1))
        if not overlay.label:
            return region
        rotulo = self._rotulo_de_la_anotacion(overlay)
        # **Encima de su banda**, que está encima de la señal: si no, el borde
        # de una banda más angosta que su nombre le cruza el texto.
        rotulo.setZValue(region.zValue() + 1)
        return region, rotulo

    def _rotulo_de_la_anotacion(self, overlay: SpanOverlay) -> pg.TextItem:
        """La pestaña con el nombre de la clase, colgada del borde de la banda.

        Rellena con el color de la clase y con la tinta que elige
        `theme.ink_over()` contra ese relleno, como la de la época. **Va una
        línea más abajo que la de la época**, para que una anotación que empieza
        con la época no tape el número, y se recorta contra el borde de la
        página: con una banda que empieza antes, quedaría fuera de la pantalla.
        """
        color = overlay.color or theme.current().accent
        rotulo = pg.TextItem(
            overlay.label,
            anchor=(0, -1.15),
            color=theme.ink_over(theme.current(), color),
            fill=pg.mkBrush(color),
        )
        inicio = overlay.start_seconds
        sesion = self._vista.session
        if sesion is not None:
            inicio = max(inicio, sesion.viewport.start_seconds)
        rotulo.setPos(inicio, self._vista.epoch_tab_top())
        return rotulo

    # -- Los segmentos de la ocupación ---------------------------------------

    def _dibujar_segmento(self, overlay: SegmentOverlay) -> object | tuple[object, ...] | None:
        """Una línea sobre el carril de su canal, con lo que mide encima."""
        vista = self._vista
        visibles = vista.visible_channels
        canal = overlay.channel_name or (visibles[0] if visibles else None)
        centro = vista.lane_center(canal) if canal else None
        if centro is None:
            return None
        y1 = centro + vista.to_lanes(overlay.y1_uv, canal)
        y2 = centro + vista.to_lanes(overlay.y2_uv, canal)
        linea = pg.PlotCurveItem(
            [overlay.x1_seconds, overlay.x2_seconds],
            [y1, y2],
            pen=pg.mkPen(theme.current().foreground, width=2),
        )
        if not overlay.label:
            return linea
        # **Con el fondo del esquema** y encima de la señal: sin fondo, el
        # número se perdía sobre una señal densa, que es donde más se mide.
        rotulo = pg.TextItem(
            overlay.label,
            color=theme.current().foreground,
            anchor=(0.5, 1.0),
            fill=pg.mkBrush(theme.current().background),
        )
        rotulo.setPos((overlay.x1_seconds + overlay.x2_seconds) / 2, max(y1, y2))
        rotulo.setZValue(Z_DE_LA_BANDA + 1)
        return linea, rotulo

    # -- La lupa (V1_F) -------------------------------------------------------

    def _dibujar_lupa(self, overlay: CircleOverlay) -> object | None:
        """La lupa: una lente circular sobre el tramo bajo el cursor (V1_F).

        Borde, fondo propio, el tramo ampliado recortado adentro y el instante
        escrito debajo. **El recorte lo hace Qt y no el código**: la elipse es
        un `QGraphicsPathItem` con `ItemClipsChildrenToShape` y la curva es su
        hija; recortar los datos a mano dejaría la onda cortada en los bordes
        en vez de la lente.

        Se amplía **el canal bajo el cursor**, que viene en el overlay: ampliar
        todos los carriles a la vez los superpondría.
        """
        vista = self._vista
        sesion = vista.session
        visibles = vista.visible_channels
        if sesion is None or not visibles:
            return None
        canal = overlay.channel_name or visibles[0]
        if canal not in visibles:
            return None
        registro = sesion.recording
        frecuencia = registro.sampling_rate
        pagina = sesion.viewport

        # El tramo a ampliar, recortado contra los bordes de la **página**:
        # cerca del comienzo o del final hay menos señal de la que pide el radio.
        desde = max(pagina.start_seconds, overlay.x_seconds - overlay.radius_seconds)
        hasta = min(pagina.end_seconds, overlay.x_seconds + overlay.radius_seconds)
        primera, ultima = seconds_to_samples(desde, hasta, frecuencia, registro.n_samples)
        if ultima <= primera:
            return None

        tramo = registro.get_segment(primera, ultima, [canal])[0]
        tiempos = (primera + np.arange(len(tramo))) / frecuencia

        centro_carril = vista.lane_center(canal) or 0.0
        base = centro_carril + vista.to_lanes(overlay.y_uv, canal)
        alturas = centro_carril + vista.array_to_lanes(tramo, canal)

        ampliado_x = overlay.x_seconds + (tiempos - overlay.x_seconds) * overlay.zoom
        ampliado_y = base + (alturas - base) * overlay.zoom
        return self._lente(overlay, ampliado_x, ampliado_y, base, canal)

    def _lente(
        self,
        overlay: CircleOverlay,
        ampliado_x: np.ndarray,
        ampliado_y: np.ndarray,
        base: float,
        channel_name: str,
    ) -> object:
        """El cristal de la lupa, con la curva ampliada adentro.

        **Redonda aunque los dos ejes no compartan unidad** —`x` son segundos y
        `y` son carriles—: el radio vertical sale de `viewPixelSize()`, que dice
        cuánto vale un píxel en cada eje.
        """
        vista = self._vista
        esquema = theme.current()
        radio_x = overlay.radius_seconds * overlay.zoom
        por_pixel = vista.getPlotItem().vb.viewPixelSize()
        proporcion = (por_pixel[1] / por_pixel[0]) if por_pixel[0] else 1.0
        radio_y = radio_x * proporcion

        camino = QPainterPath()
        camino.addEllipse(
            QRectF(overlay.x_seconds - radio_x, base - radio_y, 2 * radio_x, 2 * radio_y)
        )
        # **Un grupo de dos piezas**, porque sólo una recorta: el cristal se
        # lleva la curva adentro y la etiqueta va afuera, debajo del círculo.
        grupo = QGraphicsItemGroup()
        # Encima de la señal: el fondo es opaco para que la onda de abajo no
        # compita con la ampliada.
        grupo.setZValue(Z_DE_LA_LENTE)

        cristal = QGraphicsPathItem(camino)
        cristal.setBrush(QBrush(QColor(esquema.background)))
        cristal.setPen(pg.mkPen(esquema.accent, width=2))
        cristal.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        # **`addToGroup()` y no `setParentItem()`**: sobre un grupo, lo segundo
        # deja el ítem sin dueño, y el recolector se lo lleva sin avisar.
        grupo.addToGroup(cristal)

        # Con el color de su canal: la onda ampliada es la misma que la de
        # abajo, y en otra tinta parecería otra cosa.
        curva = pg.PlotCurveItem(
            ampliado_x,
            ampliado_y,
            pen=pg.mkPen(
                esquema.color_for_channel(vista.visible_channels.index(channel_name)),
                width=2,
            ),
            antialias=False,
        )
        curva.setParentItem(cristal)

        hora = self._hora_del_cursor(overlay.x_seconds)
        if hora is not None:
            etiqueta = pg.TextItem(hora, color=esquema.accent, anchor=(0.5, 0.0))
            fuente = vista.channel_font()
            if fuente is not None:
                etiqueta.setFont(font_for("lectura_secundaria", fuente))
            etiqueta.setPos(overlay.x_seconds, base - radio_y)
            grupo.addToGroup(etiqueta)
        return grupo

    def _hora_del_cursor(self, segundos: float) -> str | None:
        """El instante bajo la lupa, con décimas, que es la resolución que la
        lupa existe para mirar."""
        sesion = self._vista.session
        if sesion is None:
            return None
        reloj = seconds_to_clock_time(segundos, sesion.recording.start_time)
        if reloj is None:
            return f"{segundos:.1f} s".replace(".", ",")
        return reloj.strftime("%H:%M:%S,") + f"{reloj.microsecond // 100000}"
