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

import numpy as np
import pytest

pg = pytest.importorskip("pyqtgraph")

from psglab.core.annotations import AnnotationSet  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.core.scoring import Scoring  # noqa: E402
from psglab.core.session import Session  # noqa: E402
from psglab.core.windows import seconds_to_sample  # noqa: E402
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
