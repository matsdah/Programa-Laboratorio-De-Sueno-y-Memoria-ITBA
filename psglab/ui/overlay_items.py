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

**Las bandas de anotación son una sola pieza**, `AnnotationBands`, que pinta
todos los rectángulos de la página, como la grilla pinta todas sus líneas.
Eran una `LinearRegionItem` por anotación, cada una con sus dos
`InfiniteLine`, y con 400 en la página pintarlas era casi todo el cuadro. Sus
rótulos siguen siendo un `TextItem` cada uno.

Cubre del pliego: V1_F de "Herramienta Lupa", por `_dibujar_lupa()`, que es lo
que **amplía** de verdad el tramo bajo el cursor: `MagnifierTool` publica el
radio y el zoom, y acá se los usa. Y el dibujo de V1_F de "Herramienta de
amplitud": la banda de 75 µV sobre el carril de su canal.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QTransform
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

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

#: Las bandas de anotación van **encima de la señal y debajo de todo lo
#: demás**, y sus rótulos, un escalón más arriba. Encima de las curvas era lo
#: que pasaba antes por orden de llegada, con las curvas y las bandas en 0;
#: una pieza que dura entre dibujos lo perdía la primera vez que se rearmaban
#: las curvas, así que ahora se dice.
Z_DE_LAS_ANOTACIONES: float = 1.0

#: El relleno y el borde de una banda sin clase —la selección en curso, que
#: todavía no tiene—: los que pyqtgraph le daba a una `LinearRegionItem` sin
#: pincel ni pluma, para que se siga viendo igual.
_RELLENO_SIN_CLASE = QColor(0, 0, 255, 50)
_BORDE_SIN_CLASE = QColor(200, 200, 100)

#: Una banda: comienzo y final en segundos absolutos, y el color de su clase o
#: None.
Banda = tuple[float, float, str | None]


def _translucido(color: str) -> QColor:
    """El relleno de una banda: su color con la opacidad de siempre.

    **No con `QColor(color + "55")`**: con ocho cifras Qt lee `#AARRGGBB` y
    pyqtgraph `#RRGGBBAA`, así que el mismo texto que antes daba un verde
    traslúcido pasaba a dar un rojo casi opaco.
    """
    relleno = QColor(color)
    relleno.setAlpha(0x55)
    return relleno


class AnnotationBands(pg.GraphicsObject):
    """Todas las bandas de anotación de la página, en una sola pieza.

    Cada banda ocupa **todo el alto del gráfico**, como pide el pliego, con un
    relleno traslúcido del color de su clase y los dos bordes en ese color. Se
    pintan agrupadas por color, en vez de tres objetos por anotación que la
    escena recorría uno por uno.

    Se ve como las `LinearRegionItem` que reemplaza —comparado píxel a píxel,
    la diferencia es de 1/255 por redondeo— salvo en una cosa: **los bordes
    van encima de todos los rellenos**. Antes, el borde de una banda que caía
    dentro de otra quedaba teñido por el relleno de la que se pintaba después;
    ahora se ve entero, y es el que se agarra para corregir el tramo. Dos
    bandas que se superponen se siguen viendo más oscuras donde se tocan.

    No recibe clics. Los bordes que se agarran para corregir un tramo son del
    anotador, que los encuentra por coordenadas y no por objeto.
    """

    def __init__(self) -> None:
        """Arma la pieza vacía."""
        super().__init__()
        self._bandas: tuple[Banda, ...] = ()
        #: De la primera banda a la última, en segundos, o None sin bandas.
        self._extremos: tuple[float, float] | None = None
        #: Los últimos límites que se le dieron a la escena.
        self._limites = QRectF()
        self.setZValue(Z_DE_LAS_ANOTACIONES)

    @property
    def bands(self) -> tuple[Banda, ...]:
        """Las bandas que pinta, en el orden en que se las dio."""
        return self._bandas

    def set_bands(self, bands: Sequence[Banda]) -> None:
        """Reemplaza las bandas. Si son las mismas, no hace nada."""
        nuevas = tuple(bands)
        if nuevas == self._bandas:
            return
        self._bandas = nuevas
        self._extremos = (
            (min(b[0] for b in nuevas), max(b[1] for b in nuevas)) if nuevas else None
        )
        self.boundingRect()
        self.update()

    def dataBounds(
        self, axis: int, frac: float = 1.0, orthoRange: object = None
    ) -> tuple[float, float] | None:
        """Lo que ocupan en el eje horizontal; en el vertical, nada: miden lo
        que la vista, como hacía `LinearRegionItem`."""
        return self._extremos if axis == 0 else None

    def boundingRect(self) -> QRectF:
        """De la primera banda a la última, y de arriba abajo de la vista.

        **Se calcula cada vez**, como en `LinearRegionItem`, y se le avisa a la
        escena cuando cambió: el alto es el de la vista, y cambia sin que la
        pieza se entere —al elegir otros canales, por ejemplo—. Así no depende
        de que la señal de la vista llegue antes de pintar.
        """
        vista = self.viewRect()
        if self._extremos is None or vista is None:
            limites = QRectF()
        else:
            izquierda, derecha = self._extremos
            limites = QRectF(izquierda, vista.top(), derecha - izquierda, vista.height())
            limites = limites.normalized()
        if limites != self._limites:
            self.prepareGeometryChange()
            self._limites = limites
        return QRectF(limites)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Pinta los rellenos en una tira de un píxel de alto, estirada a todo
        el alto, y encima los bordes."""
        vista = self.viewRect()
        if vista is None or not self._bandas:
            return
        arriba, abajo = vista.top(), vista.bottom()
        izquierda, derecha = vista.left(), vista.right()

        por_color: dict[str | None, list[tuple[float, float]]] = {}
        for inicio, fin, color in self._bandas:
            # Lo que cae fuera de la vista no se manda a pintar.
            if fin < izquierda or inicio > derecha:
                continue
            por_color.setdefault(color, []).append((inicio, fin))
        if not por_color:
            return

        self._pintar_rellenos(painter, vista, por_color)
        for color, tramos in por_color.items():
            borde = _BORDE_SIN_CLASE if color is None else QColor(color)
            painter.setPen(pg.mkPen(borde, width=1))
            painter.drawLines(
                [QLineF(x, arriba, x, abajo) for inicio, fin in tramos for x in (inicio, fin)]
            )

    def _pintar_rellenos(
        self,
        painter: QPainter,
        vista: QRectF,
        por_color: dict[str | None, list[tuple[float, float]]],
    ) -> None:
        """Los rellenos traslúcidos, compuestos en una tira y estirados.

        **Es lo que hace barata a la pieza**, más que juntar los objetos.
        Medido sobre una imagen suelta, rellenar 400 rectángulos traslúcidos
        de 5 × 700 píxeles cuesta unos 70 ms aunque sea una sola llamada, y
        opacos, 1,5 ms: lo más probable es que Qt mezcle cada fila por
        separado, y angostos y altos son muchas filas cortas. Todas las filas
        de una banda son iguales, así que se componen una vez, en una fila, y
        la tira se estira a todo el alto: los mismos 400, 1,6 ms. Contra
        pintarlas directo, la diferencia es de 1/255 en un canal, por redondeo.

        La tira está en píxeles del dispositivo —con la densidad de la
        pantalla— y el estirado es sin suavizar, para que los bordes de cada
        relleno caigan donde caían.
        """
        transformacion = painter.transform()
        vista_en_pixeles = transformacion.mapRect(vista)
        if vista_en_pixeles.width() <= 0 or vista_en_pixeles.height() <= 0:
            return
        dispositivo = painter.device()
        densidad = dispositivo.devicePixelRatioF() if dispositivo is not None else 1.0
        # **La tira empieza y termina en un píxel entero** del dispositivo, y
        # se copia uno a uno en horizontal. Con el ancho fraccionario de la
        # vista se estiraba apenas, y la última columna se perdía. Lo que pase
        # del borde lo recorta la vista.
        desde = math.floor(vista_en_pixeles.left() * densidad)
        hasta = math.ceil(vista_en_pixeles.right() * densidad)
        destino = QRectF(
            desde / densidad,
            vista_en_pixeles.top(),
            max(1, hasta - desde) / densidad,
            vista_en_pixeles.height(),
        )
        tira = QImage(max(1, hasta - desde), 1, QImage.Format.Format_ARGB32_Premultiplied)
        tira.setDevicePixelRatio(densidad)
        tira.fill(Qt.GlobalColor.transparent)

        pintor = QPainter(tira)
        # Sólo el eje horizontal de la vista: segundos a píxeles, desde el
        # borde izquierdo de la tira.
        pintor.setTransform(
            QTransform(
                transformacion.m11(), 0.0, 0.0, 1.0,
                transformacion.dx() - destino.left(), 0.0,
            )
        )
        pintor.setPen(Qt.PenStyle.NoPen)
        for color, tramos in por_color.items():
            relleno = _RELLENO_SIN_CLASE if color is None else _translucido(color)
            pintor.setBrush(QBrush(relleno))
            pintor.drawRects([QRectF(inicio, 0.0, fin - inicio, 1.0) for inicio, fin in tramos])
        pintor.end()

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(destino, tira)
        painter.restore()


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
        #: Las bandas de todas las anotaciones, en una pieza que se crea la
        #: primera vez que hace falta y queda en la escena.
        self._bandas: AnnotationBands | None = None

    @property
    def items(self) -> list[object]:
        """Los ítems dibujados, en el orden de los overlays que los pidieron.

        **Sin las bandas de anotación**, que son una sola pieza para todas:
        ver `annotation_bands`. De una anotación, acá está su rótulo.
        """
        return list(self._items)

    @property
    def annotation_bands(self) -> AnnotationBands | None:
        """La pieza que pinta las bandas de anotación, o None si nunca hubo."""
        return self._bandas

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

        bandas: list[Banda] = []
        for overlay in overlays:
            if isinstance(overlay, SpanOverlay):
                bandas.append((overlay.start_seconds, overlay.end_seconds, overlay.color))
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

        if bandas and self._bandas is None:
            self._bandas = AnnotationBands()
            item.addItem(self._bandas)
        if self._bandas is not None:
            self._bandas.set_bands(bandas)

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

    def _dibujar_anotacion(self, overlay: SpanOverlay) -> object | None:
        """El rótulo de una anotación, si tiene clase. **La banda no**: la
        pintan todas juntas `AnnotationBands`, que `set_overlays()` alimenta."""
        if not overlay.label:
            return None
        rotulo = self._rotulo_de_la_anotacion(overlay)
        # **Encima de su banda**, que está encima de la señal: si no, el borde
        # de una banda más angosta que su nombre le cruza el texto.
        rotulo.setZValue(Z_DE_LAS_ANOTACIONES + 1)
        return rotulo

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
