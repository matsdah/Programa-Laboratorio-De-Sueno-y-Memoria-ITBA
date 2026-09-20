"""Tests de las conversiones del visualizador, y de qué manda a la pantalla.

**El dibujo no se testea.** Lo que sí, y es el motivo por el que este archivo
existe, son los conversores: `signal_view.py` es el **único** lugar del
programa que traduce desde píxeles, y de él salen las unidades con las que
trabajan las herramientas.

    píxeles  --seconds_at_pixel-->       segundos absolutos  (0 .. duración)
    píxeles  --view_fraction_at_pixel--> fracción de página  (0 .. 1)
    píxeles  --sample_at_pixel-->        muestras            (0 .. n_samples)

Confundirlas **no rompe nada de forma visible**: los tres son números chicos y
plausibles. Un medidor de ocupación que reciba segundos informa 3000 %, y un
anotador que reciba fracción guarda el evento en el primer segundo del registro.
Es el riesgo que `tools/base.py` viene señalando módulo por módulo, y acá es
donde se origina.

Los píxeles de los bordes no se escriben a mano: se preguntan al `ViewBox`, que
es lo que hace exacta la afirmación sin depender de los márgenes del gráfico.

La última sección sí mira lo que se manda a dibujar, porque desde la escala de
tiempo libre eso dejó de ser "todas las muestras": con una página larga se
manda la envolvente, y ahí hay dos errores que no se ven — perder un pico, o
dibujar la envolvente de una señal que ya no es la que está abierta.
"""

from datetime import datetime
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
from psglab.ui.channel_axis import ANCHO_DEL_CANALON  # noqa: E402
from psglab.ui import grid as modulo_de_la_grilla  # noqa: E402
from psglab.ui import signal_view as modulo_de_la_vista  # noqa: E402
from psglab.ui.signal_view import SignalView, TimeAxis  # noqa: E402

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
    """Es la unidad del medidor de ocupacion, que mide proporciones del ancho."""
    izquierda, derecha = bordes(vista)
    assert vista.view_fraction_at_pixel(izquierda) == pytest.approx(0.0, abs=0.01)
    assert vista.view_fraction_at_pixel(derecha) == pytest.approx(1.0, abs=0.01)


def test_la_fraccion_es_la_posicion_dentro_de_la_pagina(vista: SignalView):
    """No reimplementa la aritmetica: es pixel a segundos y despues
    `core.windows`, que es su unico lugar.

    **Se medía contra `window_seconds`**, los 30 s de la epoca, que con la
    escala de tiempo libre dejo de ser el ancho de la pantalla. Ahora se mide
    contra la pagina, que es lo que el medidor de ocupacion necesita: sin esto
    informaria 30 000 % sobre una pagina de una hora.
    """
    izquierda, derecha = bordes(vista)
    pagina = vista.session.viewport if vista.session is not None else None
    for pixel in (izquierda, (izquierda + derecha) / 2, derecha):
        if pagina is None:
            esperado = vista.seconds_at_pixel(pixel) / vista.window_seconds
        else:
            esperado = (
                vista.seconds_at_pixel(pixel) - pagina.start_seconds
            ) / pagina.span_seconds
        assert vista.view_fraction_at_pixel(pixel) == pytest.approx(esperado)


def test_la_fraccion_mide_contra_la_pagina_y_no_contra_la_epoca(
    vista: SignalView, sesion
):
    """Con una pagina de cuatro epocas, el punto medio de la pantalla sigue
    dando 0,5 aunque este a dos epocas del comienzo.

    Es la diferencia que hace que la ocupacion siga informando un porcentaje
    que significa algo cuando el usuario cambia de escala.
    """
    vista.set_session(sesion)
    sesion.set_viewport(sesion.viewport.zoomed(4.0))
    vista.draw_viewport()
    izquierda, derecha = bordes(vista)

    assert vista.view_fraction_at_pixel((izquierda + derecha) / 2) == pytest.approx(
        0.5, abs=0.01
    )


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


def test_el_canalon_lleva_un_renglon_por_canal_visible(vista: SignalView):
    """El rótulo salió del área de trazo en el hito 37, pero sigue siendo lo que
    dice qué canal es cada carril."""
    assert [carril.name for carril in vista.channel_axis.lanes()] == [
        "C3",
        "EMG-menton",
    ]


def test_el_detalle_es_la_escala_del_canal(vista: SignalView, sesion: Session):
    """**Llevaba también la clase y se le sacó**: con un registro de verdad
    —«Resp oro-nasal», clase «Respiratorio»— la línea no entraba en el canalón
    y salía cortada, que es peor que no decirla. La clase se sigue viendo al
    lado del nombre en el selector de canales."""
    assert vista.channel_detail("C3") == f"{sesion.scale_uv('C3'):.0f} µV"
    assert "EEG" not in vista.channel_detail("C3")


def test_sin_registro_no_hay_detalle_que_mostrar(qt_app):
    """La clase la detecta el lector y la escala la fija la sesión: antes de
    abrir un archivo no existe ninguna de las dos."""
    assert SignalView().channel_detail("C3") == ""


def test_un_canal_que_el_registro_no_tiene_no_rompe_el_dibujo(vista: SignalView):
    """Queda sin detalle y sigue. Un canal que desapareció no puede voltear el
    visualizador entero: tanto la clase como la escala salen de buscarlo."""
    assert vista.channel_detail("no_existe") == ""


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
    assert f"{escala:.0f}" in vista.channel_axis.lanes()[0].detail


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


# -- La envolvente: qué se manda a dibujar con una página larga -------------------

#: Una hora a 100 Hz: 360 000 muestras, bastante más de lo que entra en pantalla.
EPOCAS_DE_UNA_HORA = 120

#: Dónde cae la espiga, en muestras. Lejos de cualquier borde de cubeta obvio.
ESPIGA = 200_001


def _registro_de_una_hora(valor_de_la_espiga: float, donde: int = ESPIGA) -> Recording:
    """Una hora de silencio con una sola muestra distinta."""
    datos = np.zeros((1, EPOCAS_DE_UNA_HORA * 3000))
    datos[0, donde] = valor_de_la_espiga
    return Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=datos,
        sampling_rate=FRECUENCIA,
    )


@pytest.fixture
def sesion_larga() -> Session:
    return Session(
        _registro_de_una_hora(500.0),
        Scoring(EPOCAS_DE_UNA_HORA, Nomenclature.AASM),
        AnnotationSet(),
    )


@pytest.fixture
def vista_larga(qt_app, sesion_larga: Session):
    widget = SignalView()
    widget.resize(800, 400)
    widget.set_session(sesion_larga)
    yield widget


def _ver_todo(widget: SignalView, sesion: Session) -> None:
    sesion.set_viewport(sesion.viewport.whole_recording())
    widget.draw_viewport()


@pytest.fixture
def envolventes_calculadas(monkeypatch) -> list[int]:
    """Cuenta cuántas veces se calcula una envolvente de verdad."""
    llamadas: list[int] = []
    original = modulo_de_la_vista.min_max_envelope

    def contando(samples: np.ndarray, n_buckets: int) -> tuple[np.ndarray, np.ndarray]:
        llamadas.append(len(samples))
        return original(samples, n_buckets)

    monkeypatch.setattr(modulo_de_la_vista, "min_max_envelope", contando)
    return llamadas


def test_una_pagina_larga_no_manda_todas_las_muestras(
    vista_larga: SignalView, sesion_larga: Session
):
    """**Es lo que hace dibujable el registro entero.** Sin esto, pedir la noche
    manda millones de puntos a la pantalla."""
    _ver_todo(vista_larga, sesion_larga)

    tiempos, _ = vista_larga._curves["C3"].getData()

    assert len(tiempos) <= 2 * modulo_de_la_vista._COLUMNAS_MINIMAS + 2
    assert len(tiempos) < sesion_larga.recording.n_samples / 100


def test_la_espiga_se_ve_con_la_noche_entera(
    vista_larga: SignalView, sesion_larga: Session
):
    """Una muestra de 500 µV entre 360 000 ceros sigue llegando a la pantalla a
    su altura completa."""
    _ver_todo(vista_larga, sesion_larga)

    _, alturas = vista_larga._curves["C3"].getData()

    assert alturas.max() == pytest.approx(vista_larga._a_carril(500.0, "C3"))


def test_la_espiga_cae_en_su_segundo(vista_larga: SignalView, sesion_larga: Session):
    """Reducir no puede correr el evento: la posición sale de la muestra que
    eligió la envolvente, no de la cubeta."""
    _ver_todo(vista_larga, sesion_larga)

    tiempos, alturas = vista_larga._curves["C3"].getData()

    assert tiempos[int(np.argmax(alturas))] == pytest.approx(ESPIGA / FRECUENCIA)


def test_una_pagina_corta_se_dibuja_muestra_por_muestra(
    vista_larga: SignalView, sesion_larga: Session
):
    """Con menos muestras que puntos de pantalla, reducir sólo engrosaría la
    traza. Diez segundos a 100 Hz son mil muestras."""
    sesion_larga.set_viewport(sesion_larga.viewport.with_span(10.0))
    vista_larga.draw_viewport()

    tiempos, _ = vista_larga._curves["C3"].getData()

    assert len(tiempos) == 1000


def test_volver_a_una_pagina_no_recalcula_su_envolvente(
    vista_larga: SignalView, sesion_larga: Session, envolventes_calculadas: list[int]
):
    """Ir y volver es lo que hace el usuario todo el tiempo, y la segunda vez
    tiene que ser instantánea."""
    _ver_todo(vista_larga, sesion_larga)
    sesion_larga.set_viewport(sesion_larga.viewport.with_span(30.0))
    vista_larga.draw_viewport()
    antes = len(envolventes_calculadas)

    _ver_todo(vista_larga, sesion_larga)

    assert len(envolventes_calculadas) == antes


def test_cambiar_la_amplitud_no_recalcula_la_envolvente(
    vista_larga: SignalView, sesion_larga: Session, envolventes_calculadas: list[int]
):
    """La escala se aplica después de reducir, así que subir la amplitud no
    invalida nada."""
    _ver_todo(vista_larga, sesion_larga)
    antes = len(envolventes_calculadas)

    vista_larga.increase_amplitude()

    assert len(envolventes_calculadas) == antes


def test_con_otra_senal_no_queda_dibujada_la_envolvente_vieja(
    vista_larga: SignalView, sesion_larga: Session
):
    """**El error que la caché podía cometer, y el peor.**

    Filtrar devuelve un registro nuevo con los mismos índices de muestra, así
    que la clave de la envolvente sería la misma. Sin invalidar, se dibujaría la
    señal cruda sobre la filtrada, sin ningún aviso, y el investigador scorearía
    mirando una señal que ya no es la que tiene abierta.
    """
    _ver_todo(vista_larga, sesion_larga)

    sesion_larga.set_recording(_registro_de_una_hora(-700.0, donde=100_003))
    vista_larga.draw_viewport()

    _, alturas = vista_larga._curves["C3"].getData()
    assert alturas.min() == pytest.approx(vista_larga._a_carril(-700.0, "C3"))
    assert alturas.max() == pytest.approx(0.0)


def test_la_cache_de_envolventes_tiene_tope(
    vista_larga: SignalView, sesion_larga: Session
):
    """Recorrer muchas escalas no puede hacer crecer la memoria sin límite."""
    tope = modulo_de_la_vista._ENVOLVENTES_EN_MEMORIA
    for paso in range(tope + 10):
        sesion_larga.set_viewport(sesion_larga.viewport.with_span(100.0 + 10 * paso))
        vista_larga.draw_viewport()

    assert len(vista_larga._envolventes) <= tope


# -- Los nombres de canal ----------------------------------------------------------


@pytest.mark.parametrize("epoca", [0, 1, 2])
def test_los_nombres_de_canal_se_ven_en_cualquier_epoca(
    vista: SignalView, sesion: Session, epoca: int
):
    """**Regresión de la escala de tiempo libre, y de cómo dejó de existir.**

    Los nombres se creaban en x = 0 y ahí quedaban. Con el eje en segundos
    absolutos, desde la segunda época el cero queda fuera de la pantalla y los
    carriles aparecían sin nombre. Se arregló arrastrándolos al borde izquierdo
    en cada dibujo; desde el hito 37 son el canalón, que no vive en
    coordenadas del gráfico, así que la página ya no los puede dejar afuera.
    """
    sesion.go_to_window(epoca)
    vista.show_window(epoca)

    assert len(vista.channel_axis.lanes()) == len(sesion.visible_channels)


def test_ningun_nombre_de_canal_se_dibuja_sobre_la_senal(
    vista: SignalView, sesion: Session
):
    """**La regresión que motivó el canalón.**

    Los rótulos eran `pg.TextItem` apoyados en el carril, o sea adentro del
    área de trazo, y la captura de la ventana entera los mostró cruzados por su
    propia onda. Hoy la señal no puede taparlos porque no comparten píxeles: el
    `ViewBox` arranca después del ancho que el eje reservó.
    """
    textos = [
        item.toPlainText()
        for item in vista.getPlotItem().items
        if isinstance(item, pg.TextItem)
    ]
    for nombre in sesion.visible_channels:
        assert not any(nombre in texto for texto in textos)

    assert vista.getPlotItem().vb.geometry().left() >= ANCHO_DEL_CANALON


def test_el_area_de_trazo_arranca_despues_del_canalon(
    vista_larga: SignalView, sesion_larga: Session
):
    """Desplazar la página no le devuelve al gráfico el ancho del canalón."""
    sesion_larga.set_viewport(sesion_larga.viewport.with_span(300.0).panned(1200.0))
    vista_larga.draw_viewport()

    assert vista_larga.getPlotItem().vb.geometry().left() >= ANCHO_DEL_CANALON


# -- Las líneas de cero las dibuja la grilla (hito 25) -----------------------


def test_cada_canal_visible_tiene_su_linea_de_cero(vista: SignalView, sesion: Session):
    """Eran una `InfiniteLine` por canal, con el mismo costo por cuadro que una
    línea de grilla; ahora las dibuja el objeto de la grilla."""
    vista.set_session(sesion)

    alturas = [linea.position for linea in vista.grid.baselines()]

    assert len(alturas) == len(sesion.visible_channels)
    assert alturas == sorted(alturas, reverse=True)


def test_cambiar_los_canales_visibles_mueve_las_lineas_de_cero(
    vista: SignalView, sesion: Session
):
    vista.set_session(sesion)
    uno = sesion.visible_channels[:1]

    vista.set_visible_channels(uno)

    assert len(vista.grid.baselines()) == 1


# -- La banda de la época se mueve, no se rehace (hito 25) -------------------


def test_la_banda_de_la_epoca_no_se_rehace_en_cada_dibujo(
    vista: SignalView, sesion: Session
):
    """**Era lo que hacía que la señal se repintara dos veces por cuadro.**
    Sacar un ítem de la escena y poner otro son dos cambios, y el segundo llega
    cuando el primer repintado ya empezó."""
    vista.set_session(sesion)
    banda = vista._epoca

    for inicio in range(5):
        sesion.set_viewport(sesion.viewport.with_start(inicio * 1.2))
        vista.draw_viewport()

    assert banda is not None
    assert vista._epoca is banda
    assert banda in vista.getPlotItem().items


def test_la_banda_sigue_a_la_epoca(vista: SignalView, sesion: Session):
    """Es lo único que le dice al usuario qué época va a scorear cuando la
    página muestra muchas."""
    from psglab.core.windows import epoch_to_seconds

    vista.set_session(sesion)
    esperado = epoch_to_seconds(1, sesion.recording.sampling_rate)

    vista.show_window(1)

    assert vista._epoca.getRegion() == pytest.approx(esperado)


def test_desplazar_la_pagina_no_mueve_la_banda(vista: SignalView, sesion: Session):
    """Desplazar la página —Mayús+→ en pausa— mueve la vista y no la época: la
    banda se queda donde está. Reproducir, desde el hito 27, sí mueve la
    época, pero lo hace por `mark_window()`."""
    vista.set_session(sesion)
    antes = vista._epoca.getRegion()

    sesion.set_viewport(sesion.viewport.with_start(12.0))
    vista.draw_viewport()

    assert vista._epoca.getRegion() == antes


def test_cambiar_de_esquema_repinta_la_banda(vista: SignalView, sesion: Session):
    """La banda ya no se rehace en cada dibujo, así que su color lo tiene que
    cambiar `apply_scheme()`."""
    import psglab.ui.theme as theme

    vista.set_session(sesion)
    antes = vista._epoca.brush.color().name()

    anterior = theme.current()
    try:
        theme.set_current(theme.NOCTURNO)
        vista.apply_scheme()
        assert vista._epoca.brush.color().name() != antes
    finally:
        theme.set_current(anterior)
        vista.apply_scheme()


def test_marcar_la_epoca_no_mueve_la_pagina(vista: SignalView, sesion: Session):
    """Es lo que necesita la reproducción: `show_window()` llevaría una página
    de 5 s al comienzo de la época y el cursor dejaría el medio."""
    from psglab.core.windows import epoch_to_seconds

    vista.set_session(sesion)
    sesion.set_viewport(sesion.viewport.with_span(5.0).with_center(47.5))
    pagina = sesion.viewport

    vista.mark_window(1)

    assert sesion.viewport == pagina
    assert vista._epoca.getRegion() == pytest.approx(
        epoch_to_seconds(1, sesion.recording.sampling_rate)
    )


# -- El cursor de la reproducción (hito 27) ----------------------------------


def test_sin_reproducir_no_hay_cursor(vista: SignalView, sesion: Session):
    vista.set_session(sesion)

    assert vista.playhead() is None


def test_el_cursor_es_una_sola_linea_que_se_mueve(vista: SignalView, sesion: Session):
    """Veinticinco pasos por segundo: rehacerla sería el error que el hito 25
    encontró con la banda de la época."""
    vista.set_session(sesion)
    vista.set_playhead(10.0)
    linea = vista._cursor

    for segundos in (11.0, 12.5, 14.0):
        vista.set_playhead(segundos)

    assert vista._cursor is linea
    assert vista.playhead() == pytest.approx(14.0)
    assert sum(1 for item in vista.getPlotItem().items if item is linea) == 1


def test_al_pausar_el_cursor_se_oculta(vista: SignalView, sesion: Session):
    vista.set_session(sesion)
    vista.set_playhead(10.0)

    vista.set_playhead(None)

    assert vista.playhead() is None


def test_cambiar_de_esquema_repinta_el_cursor(vista: SignalView, sesion: Session):
    import psglab.ui.theme as theme

    vista.set_session(sesion)
    vista.set_playhead(10.0)
    antes = vista._cursor.pen.color().name()

    anterior = theme.current()
    try:
        theme.set_current(theme.NOCTURNO)
        vista.apply_scheme()
        assert vista._cursor.pen.color().name() != antes
    finally:
        theme.set_current(anterior)
        vista.apply_scheme()


# -- La pestaña de la época (hito 34) ----------------------------------------


def test_la_pestana_dice_que_epoca_es(vista: SignalView, sesion: Session):
    """**La banda decía dónde se scorea y no qué se scorea.** Con la página
    larga hay que mirar la barra de abajo para saber en qué época cayó."""
    vista.set_session(sesion)

    vista.show_window(2)

    assert vista._pestana.toPlainText() == "Época 3"


def test_la_pestana_dice_la_fase_cuando_la_hay(vista: SignalView, sesion: Session):
    """La fase sólo se ve en el panel de scoring, que puede estar cerrado."""
    from psglab.core.nomenclature import SleepStage

    sesion.scoring.set_stage(2, SleepStage.N2)
    vista.set_session(sesion)

    vista.show_window(2)

    assert vista._pestana.toPlainText() == "Época 3 · N2"


def test_la_pestana_se_mueve_con_la_banda(vista: SignalView, sesion: Session):
    from psglab.core.windows import epoch_to_seconds

    vista.set_session(sesion)
    vista.show_window(1)

    inicio, _ = epoch_to_seconds(1, sesion.recording.sampling_rate)
    assert vista._pestana.pos().x() == pytest.approx(inicio)


def test_la_pestana_no_se_rehace_en_cada_dibujo(vista: SignalView, sesion: Session):
    """La misma regla que la banda y el cursor: se crea una vez y se mueve."""
    vista.set_session(sesion)
    pestana = vista._pestana

    for inicio in range(5):
        sesion.set_viewport(sesion.viewport.with_start(inicio * 1.2))
        vista.draw_viewport()

    assert pestana is not None
    assert vista._pestana is pestana


# -- El eje de tiempo, en hora de la noche -----------------------------------


def eje_con_hora(vista: SignalView) -> TimeAxis:
    """El eje de abajo, con un horario de inicio puesto a mano."""
    vista.time_axis.set_start_time(datetime(2026, 9, 20, 23, 58, 30))
    return vista.time_axis


def test_el_eje_numera_en_hora_de_la_noche(vista: SignalView):
    """**Decía «Segundos de la ventana» y numeraba de 1 a 29.** Un scorer no
    nombra un evento por el segundo que ocupa dentro de su época."""
    eje = eje_con_hora(vista)

    assert eje.tickStrings([0.0, 90.0], 1.0, 30.0) == ["23:58:30", "00:00:00"]


def test_con_marcas_de_un_minuto_los_segundos_sobran(vista: SignalView):
    eje = eje_con_hora(vista)

    assert eje.tickStrings([90.0], 1.0, 300.0) == ["00:00"]


def test_con_una_pagina_de_milisegundos_hace_falta_la_decima(vista: SignalView):
    """La escala de tiempo libre llega a los 10 ms, y ahí todas las marcas
    dirían la misma hora."""
    eje = eje_con_hora(vista)

    assert eje.tickStrings([0.0, 0.2], 1.0, 0.2) == ["23:58:30,0", "23:58:30,2"]


def test_sin_horario_de_inicio_el_eje_vuelve_a_los_segundos(vista: SignalView):
    """Es lo que pasa con un EDF anónimo: numerar de 1 a 29 sigue siendo mejor
    que no decir nada, y ahí el rótulo hace falta."""
    vista.time_axis.set_start_time(None)

    assert vista.time_axis.tickStrings([0.0, 10.0], 1.0, 10.0) == ["0", "10"]
    assert vista.time_axis.label.isVisible()


def test_con_hora_el_eje_no_lleva_rotulo(vista: SignalView):
    """«21:05» no necesita que le expliquen qué es."""
    eje = eje_con_hora(vista)

    assert not eje.label.isVisible()


def test_el_eje_toma_la_hora_del_registro_al_abrirlo(qt_app, sesion: Session):
    """No hay que acordarse de ponérsela: sale de `set_session()`."""
    vista = SignalView()
    vista.set_session(sesion)

    assert vista.time_axis.start_time() == sesion.recording.start_time


# -- La banda de la época ----------------------------------------------------


def test_con_la_pagina_de_una_epoca_la_banda_no_se_dibuja(
    vista: SignalView, sesion: Session
):
    """**Lo mostró una captura y no se ve desde el código.** La banda y la
    página son lo mismo con la página de arranque, así que no marca ningún
    tramo: le cambia el color al fondo del visualizador."""
    vista.show_window(0)

    assert not vista._epoca.isVisible()


def test_con_una_pagina_larga_la_banda_se_ve(
    vista_larga: SignalView, sesion_larga: Session
):
    """Que es para lo que existe: con cuatro horas en pantalla, es lo único que
    dice cuál de todas esas épocas es la que se scorea."""
    sesion_larga.set_viewport(sesion_larga.viewport.with_span(300.0))
    vista_larga.draw_viewport()

    assert vista_larga._epoca.isVisible()


def test_la_pestana_no_se_va_con_el_comienzo_de_la_epoca(
    vista_larga: SignalView, sesion_larga: Session
):
    """Con una página más corta que la época, el comienzo de la época queda
    fuera de la pantalla y la pestaña se iba con él."""
    sesion_larga.go_to_window(4)
    sesion_larga.set_viewport(sesion_larga.viewport.with_span(5.0).panned(125.0))
    vista_larga.draw_viewport()
    desde, hasta = vista_larga.getPlotItem().vb.viewRange()[0]

    assert desde <= vista_larga._pestana.pos().x() <= hasta


def test_la_pestana_va_encima_de_la_grilla(vista: SignalView):
    """A −19 estaba debajo de la grilla, que es un solo objeto en −10 y le
    dibujaba sus líneas por encima al texto: salía partida en dos."""
    assert vista._pestana.zValue() > modulo_de_la_grilla._Z_GRILLA
