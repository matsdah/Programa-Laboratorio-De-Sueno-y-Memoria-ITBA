"""Tests de la capa que dibuja lo que piden las herramientas
(`psglab/ui/overlay_items.py`).

Dos cosas. **Qué se reutiliza**: `set_overlays()` recibe el estado completo en
cada movimiento del mouse, y rehacer todas las bandas de anotación de la
página con su rótulo en cada uno costaba un segundo por movimiento con 400
anotaciones. Se afirma sobre la identidad de los ítems, que es exactamente lo
que decide si se rehicieron. **Y la geometría de la banda de amplitud**, que
convertía su alto como si fuera una posición.

Cómo se ve cada overlay lo cubre `test_signal_view.py`.
"""

from pathlib import Path

import numpy as np
import pytest

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
from psglab.ui.overlay_items import OverlayLayer  # noqa: E402
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
def vista(qt_app, sesion: Session):
    widget = SignalView()
    widget.resize(800, 400)
    widget.set_session(sesion)
    yield widget


def en_la_escena(vista: SignalView) -> set[int]:
    return {id(item) for item in vista.getPlotItem().items}


def _bandas_en_la_escena(vista: SignalView) -> int:
    """Cuántas bandas hay en el gráfico, contando la de la época, que también es
    una `LinearRegionItem`."""
    return sum(isinstance(item, pg.LinearRegionItem) for item in vista.getPlotItem().items)


def test_la_vista_dibuja_a_traves_de_su_capa(vista: SignalView):
    assert isinstance(vista.overlay_layer, OverlayLayer)
    vista.set_overlays([ANOTACION])
    assert len(vista.overlay_layer.items) == 2


# -- Qué se reutiliza ----------------------------------------------------------


def test_lo_que_vuelve_igual_no_se_rehace(vista: SignalView):
    """El caso del mouse: la lupa se mueve y las anotaciones siguen igual."""
    vista.set_overlays([ANOTACION, LUPA])
    banda, rotulo, lente = vista.overlay_layer.items

    vista.set_overlays([ANOTACION, LUPA])

    nueva_banda, nuevo_rotulo, nueva_lente = vista.overlay_layer.items
    assert nueva_banda is banda
    assert nuevo_rotulo is rotulo
    assert nueva_lente is not lente


def test_la_lente_se_rehace_siempre_y_la_vieja_sale_de_la_escena(vista: SignalView):
    """Depende de cuánto mide un píxel, que cambia sin que cambie el overlay."""
    vista.set_overlays([LUPA])
    (vieja,) = vista.overlay_layer.items

    vista.set_overlays([LUPA])

    assert id(vieja) not in en_la_escena(vista)
    assert len(vista.overlay_layer.items) == 1


def test_lo_que_ya_no_viene_sale_de_la_escena(vista: SignalView):
    vista.set_overlays([ANOTACION, OTRA])
    primera = vista.overlay_layer.items[:2]

    vista.set_overlays([OTRA])

    escena = en_la_escena(vista)
    assert all(id(item) not in escena for item in primera)
    assert len(vista.overlay_layer.items) == 2


def test_lo_nuevo_se_agrega_a_la_escena(vista: SignalView):
    vista.set_overlays([ANOTACION])
    vista.set_overlays([ANOTACION, OTRA])

    escena = en_la_escena(vista)
    assert all(id(item) in escena for item in vista.overlay_layer.items)
    assert len(vista.overlay_layer.items) == 4


def test_los_items_siguen_el_orden_de_los_overlays(vista: SignalView):
    vista.set_overlays([ANOTACION, OTRA])
    de_la_primera = vista.overlay_layer.items[:2]

    vista.set_overlays([OTRA, ANOTACION])

    assert vista.overlay_layer.items[2:] == de_la_primera


def test_dos_overlays_iguales_son_dos_dibujos(vista: SignalView):
    """Son iguales como dato y hashean igual: una clave por overlay perdería uno."""
    bandas_de_base = _bandas_en_la_escena(vista)
    vista.set_overlays([ANOTACION, ANOTACION])
    assert _bandas_en_la_escena(vista) == bandas_de_base + 2
    assert len({id(item) for item in vista.overlay_layer.items}) == 4

    vista.set_overlays([ANOTACION])

    assert len(vista.overlay_layer.items) == 2
    escena = en_la_escena(vista)
    assert _bandas_en_la_escena(vista) == bandas_de_base + 1
    assert all(id(item) in escena for item in vista.overlay_layer.items)


def test_sin_overlays_no_queda_nada(vista: SignalView):
    vista.set_overlays([ANOTACION, LUPA])
    dibujados = vista.overlay_layer.items

    vista.set_overlays([])

    escena = en_la_escena(vista)
    assert vista.overlay_layer.items == []
    assert all(id(item) not in escena for item in dibujados)


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
