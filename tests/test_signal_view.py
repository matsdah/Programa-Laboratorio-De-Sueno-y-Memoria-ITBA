"""Tests de las conversiones del visualizador.

**El dibujo no se testea.** Lo que sí, y es el motivo por el que este archivo
existe, son los tres conversores: `signal_view.py` es el **único** lugar del
programa que traduce desde píxeles, y de él salen las tres unidades con las que
trabajan las herramientas.

    píxeles  --seconds_at_pixel-->         segundos  (0 .. 30)
    píxeles  --window_fraction_at_pixel--> fracción  (0 .. 1)
    píxeles  --sample_at_pixel-->          muestras  (0 .. n_samples)

Confundirlas **no rompe nada de forma visible**: los tres son números chicos y
plausibles. Un medidor de ocupación que reciba segundos informa 3000 %, y un
anotador que reciba fracción guarda el evento en el primer segundo del registro.
Es el riesgo que `tools/base.py` viene señalando módulo por módulo, y acá es
donde se origina.

Los píxeles de los bordes no se escriben a mano: se preguntan al `ViewBox`, que
es lo que hace exacta la afirmación sin depender de los márgenes del gráfico.
"""

from pathlib import Path

from PySide6.QtCore import QPointF

import numpy as np
import pytest

pg = pytest.importorskip("pyqtgraph")

from psglab.core.annotations import AnnotationSet  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.core.scoring import Scoring  # noqa: E402
from psglab.core.session import Session  # noqa: E402
from psglab.core.windows import seconds_to_sample  # noqa: E402
from psglab.tools.base import CircleOverlay  # noqa: E402
from psglab.ui.signal_view import SignalView  # noqa: E402

FRECUENCIA = 100.0
VENTANAS = 3


@pytest.fixture
def sesion() -> Session:
    """Tres ventanas de dos canales, con señal de verdad.

    Tres para poder mirar la del medio: con `window_index = 0` sobra el término
    que puede estar mal en una conversión.
    """
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
    """Un visualizador de tamaño conocido, sin ventana visible."""
    widget = SignalView()
    widget.resize(800, 400)
    widget.set_session(sesion)
    yield widget


def bordes(widget: SignalView) -> tuple[float, float]:
    """Los píxeles del borde izquierdo y derecho del área de dibujo.

    Se preguntan en vez de suponerlos: el gráfico tiene márgenes y ejes, así que
    el píxel 0 del widget **no** es el segundo 0 de la ventana.
    """
    caja = widget.getPlotItem().vb.sceneBoundingRect()
    return caja.left(), caja.right()


# -- Los bordes ---------------------------------------------------------------


def test_el_borde_izquierdo_es_el_comienzo_de_la_ventana(vista: SignalView):
    izquierda, _ = bordes(vista)
    assert vista.seconds_at_pixel(izquierda) == pytest.approx(0.0, abs=0.05)


def test_el_borde_derecho_es_el_final_de_la_ventana(vista: SignalView):
    _, derecha = bordes(vista)
    assert vista.seconds_at_pixel(derecha) == pytest.approx(
        vista.window_seconds, abs=0.05
    )


def test_el_medio_es_la_mitad_de_la_ventana(vista: SignalView):
    izquierda, derecha = bordes(vista)
    medio = (izquierda + derecha) / 2
    assert vista.seconds_at_pixel(medio) == pytest.approx(
        vista.window_seconds / 2, abs=0.05
    )


@pytest.mark.parametrize("afuera", [-500.0, -1.0, 10_000.0])
def test_un_pixel_fuera_del_area_se_recorta(vista: SignalView, afuera: float):
    """**Sin recortar, de acá sale una muestra fuera del registro.**

    El clic en el margen del gráfico —donde están los ejes y el título— existe,
    y daría un segundo negativo o mayor que la ventana.
    """
    segundos = vista.seconds_at_pixel(afuera)
    assert 0.0 <= segundos <= vista.window_seconds


def test_la_conversion_crece_de_izquierda_a_derecha(vista: SignalView):
    """Trivial de leer y no de garantizar: un eje invertido daría lo contrario y
    todas las herramientas trabajarían espejadas."""
    izquierda, derecha = bordes(vista)
    puntos = np.linspace(izquierda, derecha, 20)
    segundos = [vista.seconds_at_pixel(p) for p in puntos]
    assert segundos == sorted(segundos)


# -- Las otras dos se apoyan en `core.windows` --------------------------------


def test_la_fraccion_va_de_cero_a_uno(vista: SignalView):
    """Es la unidad del medidor de ocupación, que mide proporciones del ancho."""
    izquierda, derecha = bordes(vista)
    assert vista.window_fraction_at_pixel(izquierda) == pytest.approx(0.0, abs=0.01)
    assert vista.window_fraction_at_pixel(derecha) == pytest.approx(1.0, abs=0.01)


def test_la_fraccion_es_los_segundos_divididos_la_ventana(vista: SignalView):
    """No reimplementa la aritmética: es píxel→segundos y después
    `core.windows`, que es su único lugar."""
    izquierda, derecha = bordes(vista)
    for pixel in (izquierda, (izquierda + derecha) / 2, derecha):
        esperado = vista.seconds_at_pixel(pixel) / vista.window_seconds
        assert vista.window_fraction_at_pixel(pixel) == pytest.approx(esperado)


def test_la_muestra_incluye_el_desplazamiento_de_la_ventana(
    vista: SignalView, sesion: Session
):
    """**El error caro, en el lugar donde se origina.**

    En la ventana 1 el segundo 5 es la muestra 3500, no la 500. Una conversión
    que ignore la ventana deja la anotación al principio del registro, y la
    banda se dibuja igual: sólo que en otro lado.
    """
    vista.show_window(1)
    izquierda, derecha = bordes(vista)
    pixel = izquierda + (derecha - izquierda) * 5.0 / vista.window_seconds

    assert vista.sample_at_pixel(pixel) == seconds_to_sample(1, 5.0, FRECUENCIA)


def test_la_muestra_crece_al_cambiar_de_ventana(vista: SignalView):
    """El mismo píxel es una muestra distinta en cada ventana. Si diera lo
    mismo, todas las anotaciones caerían en la primera."""
    izquierda, derecha = bordes(vista)
    medio = (izquierda + derecha) / 2

    vista.show_window(0)
    primera = vista.sample_at_pixel(medio)
    vista.show_window(2)
    assert vista.sample_at_pixel(medio) > primera


def test_sin_sesion_la_muestra_es_cero(qt_app):
    """El visualizador se construye antes de que haya ningún registro abierto, y
    la ventana principal puede consultarlo igual."""
    assert SignalView().sample_at_pixel(100.0) == 0


# -- La etiqueta del canal (V4_F) ---------------------------------------------


def test_la_etiqueta_lleva_el_nombre_y_la_clase(vista: SignalView):
    """El pliego pide mostrar la clase junto al nombre para saber qué se está
    viendo."""
    assert vista.channel_label("C3") == "C3 (EEG)"
    assert vista.channel_label("EMG-menton") == "EMG-menton (EMG)"


def test_sin_registro_la_etiqueta_es_solo_el_nombre(qt_app):
    """La clase la detecta el lector: antes de abrir un archivo no hay ninguna
    que mostrar."""
    assert SignalView().channel_label("C3") == "C3"


def test_un_canal_que_el_registro_no_tiene_no_rompe_el_dibujo(vista: SignalView):
    """Devuelve el nombre y sigue. Un canal que desapareció no puede voltear el
    visualizador entero."""
    assert vista.channel_label("no_existe") == "no_existe"


# -- La amplitud (V2_P, V5_F) -------------------------------------------------


def test_aumentar_la_amplitud_baja_el_numero_de_escala(
    vista: SignalView, sesion: Session
):
    """Parece al revés y no lo es: `scale_uv` es cuántos µV representa la altura
    del canal, así que para que la señal se vea más grande esa altura tiene que
    representar **menos** µV. La regla vive en `core`; acá sólo se redibuja.
    """
    antes = sesion.scale_uv("C3")
    vista.increase_amplitude()
    assert sesion.scale_uv("C3") < antes


def test_reducir_la_amplitud_sube_el_numero(vista: SignalView, sesion: Session):
    antes = sesion.scale_uv("C3")
    vista.decrease_amplitude()
    assert sesion.scale_uv("C3") > antes


def test_la_escala_mostrada_sigue_a_la_amplitud(vista: SignalView, sesion: Session):
    """V5_F: la referencia en µV tiene que reflejar la amplitud real del canal."""
    vista.increase_amplitude()
    escala = sesion.scale_uv("C3")
    assert f"{escala:.0f}" in vista._labels[0].toPlainText()


def test_cambiar_la_amplitud_sin_registro_no_rompe(qt_app):
    vista = SignalView()
    vista.increase_amplitude()
    vista.decrease_amplitude()


# -- El cuarto conversor: píxeles a microvoltios (hito 9) ---------------------


def test_la_vertical_sale_en_microvoltios_y_no_en_carriles(vista: SignalView):
    """**El bug que motivó este conversor.**

    `ViewerTool` documenta recibir la `y` en µV, y la ventana principal le
    pasaba la coordenada cruda del gráfico, que va de 0 a 1. Con la escala por
    defecto, medio carril son decenas de µV: si el número que sale de acá
    estuviera en carriles, sería menor que 1.
    """
    caja = vista.getPlotItem().vb.sceneBoundingRect()
    arriba = caja.top() + caja.height() * 0.1

    assert abs(vista.microvolts_at_pixel(arriba)) > 1.0


def test_el_eje_del_canal_es_el_cero(vista: SignalView, sesion: Session):
    """El µV 0 cae donde está dibujado el eje del canal, no en el borde."""
    caja = vista.getPlotItem().vb.sceneBoundingRect()
    # El primer canal se dibuja centrado en el carril 0, que es la coordenada
    # de gráfico 0. Se pregunta al ViewBox dónde cae ese punto en la escena.
    eje = vista.getPlotItem().vb.mapViewToScene(QPointF(0.0, 0.0)).y()

    assert vista.microvolts_at_pixel(eje) == pytest.approx(0.0, abs=1e-6)
    assert caja.top() <= eje <= caja.bottom()


def test_ida_y_vuelta_da_lo_mismo(vista: SignalView):
    """Es la inversa exacta de la cuenta con la que se dibuja la señal. Si no lo
    fuera, la banda de amplitud no mediría lo que dice medir."""
    for microvoltios in (0.0, 25.0, -40.0, 75.0):
        carril = vista._a_carril(microvoltios, "C3")
        assert vista._a_microvoltios(carril, "C3") == pytest.approx(microvoltios)


def test_mas_arriba_es_mas_microvoltios(vista: SignalView):
    """Trivial de leer y no de garantizar: en la escena la `y` crece hacia
    abajo, así que un signo de más daría la señal invertida."""
    caja = vista.getPlotItem().vb.sceneBoundingRect()
    arriba = vista.microvolts_at_pixel(caja.top() + 10)
    abajo = vista.microvolts_at_pixel(caja.bottom() - 10)

    assert arriba > abajo


def test_la_escala_del_canal_cambia_la_lectura(vista: SignalView, sesion: Session):
    """Duplicar los µV que representa el carril tiene que duplicar lo que se lee
    en el mismo píxel: es lo que hace que la ocupación y la lupa sigan a la
    amplitud que eligió el usuario."""
    caja = vista.getPlotItem().vb.sceneBoundingRect()
    punto = caja.top() + caja.height() * 0.2

    antes = vista.microvolts_at_pixel(punto)
    sesion.set_scale_uv("C3", sesion.scale_uv("C3") * 2)
    assert vista.microvolts_at_pixel(punto) == pytest.approx(antes * 2)


def test_sin_registro_la_vertical_es_cero(qt_app):
    """El visualizador se construye antes de que haya nada abierto."""
    assert SignalView().microvolts_at_pixel(100.0) == 0.0


# -- La lupa amplía de verdad (V1_F de "Lupa", hito 9) ------------------------
#
# Hasta el hito 9 el `CircleOverlay` se dibujaba como un punto de 30 píxeles,
# **descartando `radius_seconds` y `zoom`**: el círculo seguía al mouse y no
# ampliaba nada. La herramienta publicaba los dos campos y nadie los leía.


def lupa(widget: SignalView, x: float = 15.0, radio: float = 1.0, zoom: float = 4.0):
    """Dibuja una lupa y devuelve los puntos que quedaron en pantalla."""
    widget.set_overlays(
        [
            CircleOverlay(
                tool_name="magnifier",
                x_seconds=x,
                y_uv=0.0,
                radius_seconds=radio,
                zoom=zoom,
            )
        ]
    )
    return widget._overlay_items[0].getData()


def test_la_lupa_dibuja_la_señal_y_no_un_punto(vista: SignalView):
    x, _ = lupa(vista)
    assert len(x) > 2, "la lupa sigue dibujando un punto suelto"


def test_el_ancho_dibujado_sale_del_radio_y_del_zoom(vista: SignalView):
    """El tramo de `radius_seconds` a cada lado se estira `zoom` veces. Con el
    punto de 30 píxeles, este número no dependía de nada."""
    x, _ = lupa(vista, radio=1.0, zoom=4.0)
    assert x.max() - x.min() == pytest.approx(8.0, abs=0.1)


def test_mas_zoom_amplia_mas(vista: SignalView):
    x4, y4 = lupa(vista, zoom=4.0)
    x8, y8 = lupa(vista, zoom=8.0)

    assert (x8.max() - x8.min()) == pytest.approx(2 * (x4.max() - x4.min()), rel=0.02)
    assert (y8.max() - y8.min()) == pytest.approx(2 * (y4.max() - y4.min()), rel=0.02)


def test_un_radio_mas_grande_toma_mas_señal(vista: SignalView):
    corta, _ = lupa(vista, radio=0.5)
    larga, _ = lupa(vista, radio=2.0)

    assert len(larga) > len(corta)


def test_la_lupa_se_centra_donde_esta_el_mouse(vista: SignalView):
    """Ampliar alrededor de otro punto movería la señal bajo el cursor."""
    x, _ = lupa(vista, x=10.0)
    assert (x.min() + x.max()) / 2 == pytest.approx(10.0, abs=0.1)


def test_cerca_del_borde_no_se_sale_de_la_ventana(vista: SignalView):
    """Al principio de la ventana hay menos señal de la que pide el radio, y
    pedirla igual saldría del registro."""
    x, _ = lupa(vista, x=0.2, radio=2.0)
    assert len(x) > 0


def test_sin_registro_la_lupa_no_dibuja_nada(qt_app):
    widget = SignalView()
    widget.set_overlays(
        [
            CircleOverlay(
                tool_name="magnifier",
                x_seconds=1.0,
                y_uv=0.0,
                radius_seconds=1.0,
                zoom=4.0,
            )
        ]
    )
    assert widget._overlay_items == []
