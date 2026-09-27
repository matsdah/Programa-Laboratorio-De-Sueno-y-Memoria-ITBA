"""Tests de la capa que dibuja lo que piden las herramientas
(`psglab/ui/overlay_items.py`).

Dos cosas. **Qué se reutiliza**: `set_overlays()` recibe el estado completo en
cada movimiento del mouse, y rehacer todas las bandas de anotación de la
página con su rótulo en cada uno costaba un segundo por movimiento con 400
anotaciones. Se afirma sobre la identidad de los ítems, que es exactamente lo
que decide si se rehicieron. **Y la geometría de la banda de amplitud**, que
convertía su alto como si fuera una posición.

**Las bandas de anotación son una sola pieza** para todas, y se verifica que
lo sean, que lleven el tramo y el color de cada una y que se pinten donde van:
un color mal leído o una tira corrida no los ve ningún otro test.

Cómo se ve cada overlay lo cubre `test_signal_view.py`.
"""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

pg = pytest.importorskip("pyqtgraph")

from psglab.core.annotations import AnnotationSet  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.core.scoring import Scoring  # noqa: E402
from psglab.core.session import Session  # noqa: E402
from psglab.tools.base import (  # noqa: E402
    BandOverlay,
    CircleOverlay,
    SegmentOverlay,
    SpanOverlay,
)
from psglab.ui import theme  # noqa: E402
from psglab.ui.overlay_items import OverlayLayer, _translucido  # noqa: E402
from psglab.ui.signal_view import SignalView  # noqa: E402

FRECUENCIA = 100.0
VENTANAS = 3

ANOTACION = SpanOverlay("annotator", 4.0, 7.0, "Spindle", "#6cb04a")
OTRA = SpanOverlay("annotator", 12.0, 14.0, "Arousal", "#e6754a")
LUPA = CircleOverlay("magnifier", x_seconds=15.0, y_uv=0.0, radius_seconds=2.0, zoom=2.0, channel_name="C3")


@pytest.fixture
def sesion() -> Session:
    """Tres ventanas de dos canales, como en `test_signal_view.py`."""
    tiempos = np.arange(VENTANAS * 3000) / FRECUENCIA
    datos = np.vstack(
        [50.0 * np.sin(2 * np.pi * 10 * tiempos), 30.0 * np.sin(2 * np.pi * tiempos)]
    )
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("EMG-menton", ChannelKind.EMG, "µV", 1),
        ],
        data=datos,
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def sesion_plana() -> Session:
    """Dos canales en cero: lo que se pinte entre los carriles es de las bandas."""
    registro = Recording(
        file_path=Path("plana.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("EMG-menton", ChannelKind.EMG, "µV", 1),
        ],
        data=np.zeros((2, VENTANAS * 3000)),
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def vista(qt_app, sesion: Session):
    widget = SignalView()
    widget.resize(800, 400)
    widget.set_session(sesion)
    yield widget


def en_la_escena(vista: SignalView) -> set[int]:
    return {id(item) for item in vista.getPlotItem().items}


def test_la_vista_dibuja_a_traves_de_su_capa(vista: SignalView):
    assert isinstance(vista.overlay_layer, OverlayLayer)
    vista.set_overlays([ANOTACION])
    (rotulo,) = vista.overlay_layer.items
    assert isinstance(rotulo, pg.TextItem)


# -- Qué se reutiliza ----------------------------------------------------------


def test_lo_que_vuelve_igual_no_se_rehace(vista: SignalView):
    """El caso del mouse: la lupa se mueve y las anotaciones siguen igual."""
    vista.set_overlays([ANOTACION, LUPA])
    rotulo, lente = vista.overlay_layer.items
    bandas = vista.overlay_layer.annotation_bands

    vista.set_overlays([ANOTACION, LUPA])

    nuevo_rotulo, nueva_lente = vista.overlay_layer.items
    assert nuevo_rotulo is rotulo
    assert nueva_lente is not lente
    assert vista.overlay_layer.annotation_bands is bandas


def test_la_lente_se_rehace_siempre_y_la_vieja_sale_de_la_escena(vista: SignalView):
    """Depende de cuánto mide un píxel, que cambia sin que cambie el overlay."""
    vista.set_overlays([LUPA])
    (vieja,) = vista.overlay_layer.items

    vista.set_overlays([LUPA])

    assert id(vieja) not in en_la_escena(vista)
    assert len(vista.overlay_layer.items) == 1


def test_lo_que_ya_no_viene_sale_de_la_escena(vista: SignalView):
    vista.set_overlays([ANOTACION, OTRA])
    primero, _ = vista.overlay_layer.items

    vista.set_overlays([OTRA])

    assert id(primero) not in en_la_escena(vista)
    assert len(vista.overlay_layer.items) == 1
    assert vista.overlay_layer.annotation_bands.bands == ((12.0, 14.0, "#e6754a"),)


def test_lo_nuevo_se_agrega_a_la_escena(vista: SignalView):
    vista.set_overlays([ANOTACION])
    vista.set_overlays([ANOTACION, OTRA])

    escena = en_la_escena(vista)
    assert all(id(item) in escena for item in vista.overlay_layer.items)
    assert len(vista.overlay_layer.items) == 2


def test_los_items_siguen_el_orden_de_los_overlays(vista: SignalView):
    vista.set_overlays([ANOTACION, OTRA])
    del_primero, del_segundo = vista.overlay_layer.items

    vista.set_overlays([OTRA, ANOTACION])

    assert vista.overlay_layer.items == [del_segundo, del_primero]


def test_dos_overlays_iguales_son_dos_dibujos(vista: SignalView):
    """Son iguales como dato y hashean igual: una clave por overlay perdería uno."""
    vista.set_overlays([ANOTACION, ANOTACION])
    assert len({id(item) for item in vista.overlay_layer.items}) == 2
    assert len(vista.overlay_layer.annotation_bands.bands) == 2

    vista.set_overlays([ANOTACION])

    (queda,) = vista.overlay_layer.items
    assert id(queda) in en_la_escena(vista)
    assert len(vista.overlay_layer.annotation_bands.bands) == 1


def test_sin_overlays_no_queda_nada(vista: SignalView):
    vista.set_overlays([ANOTACION, LUPA])
    dibujados = vista.overlay_layer.items

    vista.set_overlays([])

    escena = en_la_escena(vista)
    assert vista.overlay_layer.items == []
    assert all(id(item) not in escena for item in dibujados)
    assert vista.overlay_layer.annotation_bands.bands == ()


# -- Las bandas de anotación, en una sola pieza --------------------------------


def _regiones_en_la_escena(vista: SignalView) -> int:
    """Cuántas `LinearRegionItem` hay en el gráfico: la de la época es una."""
    return sum(isinstance(item, pg.LinearRegionItem) for item in vista.getPlotItem().items)


def test_cien_anotaciones_son_una_sola_pieza(vista: SignalView):
    """**Es el motivo de la pieza**: con una `LinearRegionItem` por anotación,
    y sus dos `InfiniteLine`, pintarlas era casi todo el cuadro."""
    regiones_de_base = _regiones_en_la_escena(vista)
    anotaciones = [
        SpanOverlay("annotator", 0.2 * n, 0.2 * n + 0.1, "", "#6cb04a") for n in range(100)
    ]

    vista.set_overlays(anotaciones)

    assert _regiones_en_la_escena(vista) == regiones_de_base
    bandas = vista.overlay_layer.annotation_bands
    assert id(bandas) in en_la_escena(vista)
    assert len(bandas.bands) == 100


def test_la_pieza_lleva_tramo_y_color_de_cada_banda(vista: SignalView):
    seleccion = SpanOverlay("annotator", 20.0, 22.0, "")

    vista.set_overlays([ANOTACION, seleccion, OTRA])

    assert vista.overlay_layer.annotation_bands.bands == (
        (4.0, 7.0, "#6cb04a"),
        (20.0, 22.0, None),
        (12.0, 14.0, "#e6754a"),
    )


def test_la_pieza_es_la_misma_de_un_dibujo_al_otro(vista: SignalView, sesion: Session):
    """Se crea una vez y queda: cambiar la página no la rehace."""
    vista.set_overlays([ANOTACION])
    bandas = vista.overlay_layer.annotation_bands

    sesion.set_viewport(sesion.viewport.with_span(60.0))
    vista.set_overlays([OTRA])

    assert vista.overlay_layer.annotation_bands is bandas


def test_las_bandas_van_encima_de_la_senal_y_debajo_de_sus_rotulos(vista: SignalView):
    """Encima de las curvas era lo que pasaba antes por orden de llegada; una
    pieza que dura lo perdía al rearmarse las curvas, así que se fija."""
    vista.set_overlays([ANOTACION])
    vista.set_visible_channels(["EMG-menton", "C3"])
    vista.set_overlays([ANOTACION])

    bandas = vista.overlay_layer.annotation_bands
    (rotulo,) = vista.overlay_layer.items
    curvas = [i for i in vista.getPlotItem().items if isinstance(i, pg.PlotCurveItem)]
    assert curvas
    assert all(bandas.zValue() > curva.zValue() for curva in curvas)
    assert rotulo.zValue() > bandas.zValue()


def test_las_bandas_no_cuentan_para_el_alto_de_la_vista(vista: SignalView):
    """Ocupan el alto de la vista, como `LinearRegionItem`: si contaran,
    ajustar la vista a lo dibujado las haría crecer sin fin."""
    vista.set_overlays([ANOTACION, OTRA])
    bandas = vista.overlay_layer.annotation_bands

    assert bandas.dataBounds(0) == (4.0, 14.0)
    assert bandas.dataBounds(1) is None


def test_la_banda_llega_al_carril_que_se_agrega_sin_redibujarla(
    qt_app, sesion_plana: Session
):
    """El alto de las bandas es el de la vista, y cambia sin que la pieza se
    entere: sumar un canal no le pasa bandas nuevas. La banda tiene que llegar
    igual al carril nuevo, que queda fuera del alto que tenía antes."""
    widget = SignalView()
    widget.resize(800, 400)
    widget.set_session(sesion_plana)
    widget.set_visible_channels(["C3"])
    widget.set_overlays([SpanOverlay("annotator", 10.0, 20.0, "", "#20c020")])
    widget.grab()

    widget.set_visible_channels(["C3", "EMG-menton"])
    imagen = widget.grab().toImage()

    # En el carril nuevo, lejos de su línea de cero.
    punto = widget.getPlotItem().vb.mapViewToScene(QPointF(15.2, -1.3))
    color = QColor(imagen.pixel(int(punto.x()), int(punto.y())))
    assert color.green() > color.red() + 20


def test_el_relleno_es_del_color_de_su_clase(qt_app):
    """**Regresión**: con ocho cifras, Qt lee `#AARRGGBB` y pyqtgraph
    `#RRGGBBAA`. Armar el color como texto convertía el verde traslúcido de un
    huso en un rojo casi opaco."""
    relleno = _translucido("#6cb04a")

    assert (relleno.red(), relleno.green(), relleno.blue()) == (0x6C, 0xB0, 0x4A)
    assert relleno.alpha() == 0x55


def test_la_banda_se_pinta_de_su_color_en_la_pantalla(qt_app, sesion_plana: Session):
    """Lo que se ve, y no lo que la pieza guarda: el relleno de un huso verde
    tiene que ser verde, y afuera de la banda no tiene que haber nada."""
    widget = SignalView()
    widget.resize(800, 400)
    widget.set_session(sesion_plana)
    widget.set_overlays([SpanOverlay("annotator", 10.0, 20.0, "", "#20c020")])
    imagen = widget.grab().toImage()

    vb = widget.getPlotItem().vb

    def color_en(segundos: float) -> QColor:
        # Entre los dos carriles, donde no hay señal, y lejos de la grilla.
        punto = vb.mapViewToScene(QPointF(segundos, -0.5))
        return QColor(imagen.pixel(int(punto.x()), int(punto.y())))

    fondo = QColor(theme.current().background).name()
    # **Justo a cada lado de los dos bordes**: la tira que se estira tiene que
    # caer donde está la banda, no corrida.
    for adentro in (10.2, 15.2, 19.8):
        en_la_banda = color_en(adentro)
        assert en_la_banda.green() > en_la_banda.red() + 20, adentro
    for afuera in (9.8, 20.2, 25.2):
        assert color_en(afuera).name() == fondo, afuera

    # Y los dos bordes, opacos y del color de la clase: son los que se
    # agarran para corregir el tramo.
    for borde in (10.0, 20.0):
        punto = vb.mapViewToScene(QPointF(borde, -0.5))
        columnas = {
            QColor(imagen.pixel(x, int(punto.y()))).name()
            for x in range(int(punto.x()) - 1, int(punto.x()) + 2)
        }
        assert "#20c020" in columnas, borde


# -- Cuándo cambia la geometría ------------------------------------------------


def _se_rehace_al(vista: SignalView, overlay, cambio) -> bool:
    vista.set_overlays([overlay])
    antes = vista.overlay_layer.items
    cambio()
    vista.set_overlays([overlay])
    return all(nuevo is not viejo for nuevo, viejo in zip(vista.overlay_layer.items, antes))


BANDA = BandOverlay("amplitude_band", y_center_uv=10.0, height_uv=75.0, channel_name="C3")


def test_cambiar_la_escala_rehace_la_banda(vista: SignalView, sesion: Session):
    assert _se_rehace_al(vista, BANDA, lambda: sesion.set_scale_uv("C3", sesion.scale_uv("C3") * 2))


def test_cambiar_el_desplazamiento_rehace_el_segmento(vista: SignalView, sesion: Session):
    segmento = SegmentOverlay("occupancy", 2.0, 10.0, 6.0, 10.0, "C3", "4,0 s")
    assert _se_rehace_al(vista, segmento, lambda: sesion.set_offset_uv("C3", 40.0))


def test_cambiar_los_canales_visibles_rehace_la_banda(vista: SignalView):
    """El carril de cada canal depende de cuántos hay y en qué orden."""
    assert _se_rehace_al(vista, BANDA, lambda: vista.set_visible_channels(["EMG-menton", "C3"]))


def test_cambiar_la_pagina_rehace_la_anotacion(vista: SignalView, sesion: Session):
    """El rótulo se recorta contra el borde de la página."""
    assert _se_rehace_al(
        vista, ANOTACION, lambda: sesion.set_viewport(sesion.viewport.with_span(60.0))
    )


def test_cambiar_de_esquema_rehace_la_anotacion(vista: SignalView):
    """El rótulo sin color propio toma el acento del esquema."""
    anterior = theme.current()
    try:
        assert _se_rehace_al(vista, ANOTACION, lambda: theme.set_current(theme.NOCTURNO))
    finally:
        theme.set_current(anterior)


def test_un_esquema_con_el_mismo_nombre_y_otros_colores_rehace_la_anotacion(
    vista: SignalView,
):
    """La firma lleva el esquema entero: uno armado con `dataclasses.replace()`
    se llama igual que el original y pinta otra cosa."""
    import dataclasses

    anterior = theme.current()
    otro = dataclasses.replace(anterior, accent="#123456")
    assert otro.name == anterior.name
    try:
        assert _se_rehace_al(vista, ANOTACION, lambda: theme.set_current(otro))
    finally:
        theme.set_current(anterior)


# -- La banda de amplitud: el alto es una longitud ----------------------------


def _alto_y_centro(vista: SignalView) -> tuple[float, float]:
    region = next(i for i in vista.overlay_layer.items if isinstance(i, pg.LinearRegionItem))
    abajo, arriba = region.getRegion()
    return arriba - abajo, (arriba + abajo) / 2


def test_el_desplazamiento_del_canal_no_cambia_el_alto_de_la_banda(
    vista: SignalView, sesion: Session
):
    """**Regresión**: el alto se convertía como una posición y le restaba el
    desplazamiento del canal. Con un canal centrado en 500 µV —un
    respiratorio se centra solo al abrir el registro— la banda de 75 µV medía
    doce veces lo que debía."""
    vista.set_overlays([BANDA])
    alto_sin, centro_sin = _alto_y_centro(vista)

    sesion.set_offset_uv("C3", 500.0)
    vista.set_overlays([BANDA])
    alto_con, centro_con = _alto_y_centro(vista)

    assert alto_con == pytest.approx(alto_sin)
    assert alto_sin == pytest.approx(2 * vista.height_to_lanes(37.5, "C3"))


def test_el_desplazamiento_del_canal_si_mueve_el_centro_de_la_banda(
    vista: SignalView, sesion: Session
):
    """La posición sí se corre: la banda sigue a la señal del carril."""
    vista.set_overlays([BANDA])
    _, centro_sin = _alto_y_centro(vista)

    sesion.set_offset_uv("C3", 500.0)
    vista.set_overlays([BANDA])
    _, centro_con = _alto_y_centro(vista)

    assert centro_con - centro_sin == pytest.approx(-vista.height_to_lanes(500.0, "C3"))
