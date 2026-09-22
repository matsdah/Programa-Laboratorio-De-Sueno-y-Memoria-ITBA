"""Tests de la herramienta de ocupación horizontal.

El pliego define esta herramienta con ejemplos numéricos explícitos, así que
se puede testear al pie de la letra. Los casos de abajo son literalmente los
del pliego, más los bordes.

La definición es una **proyección sobre el eje horizontal**: lo que cuenta es
|x2 - x1| sobre el ancho de la ventana, no el largo de la línea. Una diagonal
larga puede ocupar menos que una horizontal corta.
"""

import pytest

from pathlib import Path

import numpy as np

from psglab.config import DEFAULT_SCALE_UV, OCCUPANCY_COUNTS_OVERLAP_ONCE
from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.base import SegmentOverlay
from psglab.tools.occupancy import (
    TOLERANCIA_DE_CLIC_EN_ESCALAS,
    OccupancyLine,
    OccupancyTool,
)


def test_linea_vertical_ocupa_cero_por_ciento():
    """Caso del pliego: una línea vertical no ocupa nada en horizontal."""
    linea = OccupancyLine(x1=0.5, y1=0.0, x2=0.5, y2=1.0)
    assert linea.horizontal_fraction == pytest.approx(0.0)


def test_linea_de_borde_a_borde_ocupa_cien_por_ciento():
    """Caso del pliego: de un lado al otro de la pantalla."""
    linea = OccupancyLine(x1=0.0, y1=0.5, x2=1.0, y2=0.5)
    assert linea.horizontal_fraction == pytest.approx(1.0)


def test_linea_horizontal_de_media_pantalla_ocupa_cincuenta_por_ciento():
    """Caso del pliego."""
    linea = OccupancyLine(x1=0.25, y1=0.5, x2=0.75, y2=0.5)
    assert linea.horizontal_fraction == pytest.approx(0.5)


def test_una_diagonal_ocupa_menos_que_la_horizontal_del_mismo_largo():
    """Caso del pliego: con ángulo, el aporte baja.

    Las dos líneas miden lo mismo, pero la diagonal proyecta menos sobre el
    eje horizontal.
    """
    horizontal = OccupancyLine(x1=0.0, y1=0.5, x2=0.5, y2=0.5)
    diagonal = OccupancyLine(x1=0.0, y1=0.0, x2=0.35, y2=0.35)
    assert diagonal.horizontal_fraction < horizontal.horizontal_fraction


def test_el_sentido_del_trazo_no_cambia_el_resultado():
    """Dibujar de derecha a izquierda da lo mismo que al revés."""
    izquierda_a_derecha = OccupancyLine(x1=0.2, y1=0.5, x2=0.8, y2=0.5)
    derecha_a_izquierda = OccupancyLine(x1=0.8, y1=0.5, x2=0.2, y2=0.5)
    assert izquierda_a_derecha.horizontal_fraction == pytest.approx(
        derecha_a_izquierda.horizontal_fraction
    )


def test_el_total_suma_el_aporte_de_todas_las_lineas():
    """V4_F: varias líneas suman su distancia horizontal."""
    herramienta = OccupancyTool()
    herramienta.clear()
    herramienta.add_line(OccupancyLine(0.0, 0.5, 0.2, 0.5))  # 20 %
    herramienta.add_line(OccupancyLine(0.4, 0.5, 0.7, 0.5))  # 30 %
    assert herramienta.total_percentage() == pytest.approx(50.0)


def test_sin_lineas_el_total_es_cero():
    herramienta = OccupancyTool()
    herramienta.clear()
    assert herramienta.total_percentage() == pytest.approx(0.0)


# -- El gesto del mouse, que es donde se confunden las unidades --------------


@pytest.fixture
def sesion() -> Session:
    """Una época de dos canales.

    **Dos y no uno desde el hito 48.** Con un solo canal, la mitad de lo que
    esta herramienta decide —sobre qué carril cae una línea, con qué escala se
    mide la tolerancia del clic— no se puede distinguir de no decidir nada: la
    auditoría de los tests mostró que cuatro mutaciones de `occupancy.py`
    sobrevivían a la suite entera por esto.
    """
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("C4", ChannelKind.EEG, "µV", 1),
        ],
        data=np.zeros((2, 3000)),
        sampling_rate=100.0,
    )
    return Session(registro, Scoring(1, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def sesion_larga() -> Session:
    """Diez épocas, para poder cambiar de escala y desplazarse de verdad.

    La fixture `sesion` dura exactamente una época, así que ahí cualquier zoom
    o desplazamiento se recorta contra el registro y la página no cambia: es la
    adecuada para todo lo demás y la equivocada para probar la página.
    """
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("C4", ChannelKind.EEG, "µV", 1),
        ],
        data=np.zeros((2, 30000)),
        sampling_rate=100.0,
    )
    return Session(registro, Scoring(10, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def herramienta_larga(sesion_larga: Session) -> OccupancyTool:
    tool = OccupancyTool()
    tool.activate(sesion_larga)
    return tool


@pytest.fixture
def herramienta(sesion: Session) -> OccupancyTool:
    tool = OccupancyTool()
    tool.activate(sesion)
    return tool


def arrastrar(
    tool: OccupancyTool,
    desde_s: float,
    hasta_s: float,
    y: float = 0.0,
    canal: str | None = None,
) -> None:
    """Un gesto completo: apretar, mover y soltar, en segundos.

    **Con `canal`, la línea queda en ese carril** (hito 46). Sin él queda sin
    canal, que es lo que pasa cuando no hay ninguno visible.
    """
    tool.on_mouse_press(desde_s, y, "left", canal)
    tool.on_mouse_move(hasta_s, y, canal)
    tool.on_mouse_release(hasta_s, y, "left", canal)


def test_arrastrar_media_ventana_ocupa_cincuenta_por_ciento(herramienta: OccupancyTool):
    """**El test que atrapa la confusión de unidades.**

    Los métodos de mouse reciben **segundos** (0 a 30) y `OccupancyLine` guarda
    **fracción** (0 a 1). Sin convertir, una línea de 15 segundos informaría
    1500 %: un número plausible y equivocado, que no falla de forma visible.
    """
    arrastrar(herramienta, 0.0, 15.0)
    assert herramienta.total_percentage() == pytest.approx(50.0)


def test_arrastrar_la_ventana_entera_ocupa_cien_por_ciento(herramienta: OccupancyTool):
    arrastrar(herramienta, 0.0, 30.0)
    assert herramienta.total_percentage() == pytest.approx(100.0)


def test_un_clic_sin_arrastrar_no_deja_ninguna_linea(herramienta: OccupancyTool):
    """Aportaría 0 % a la suma, pero ensuciaría la lista y el dibujo."""
    herramienta.on_mouse_press(10.0, 0.0, "left")
    herramienta.on_mouse_release(10.0, 0.0, "left")
    assert herramienta.lines() == []


def test_la_linea_en_curso_se_dibuja_antes_de_soltar(herramienta: OccupancyTool):
    """El usuario tiene que ver lo que está trazando mientras arrastra."""
    herramienta.on_mouse_press(0.0, 0.0, "left")
    herramienta.on_mouse_move(15.0, 0.0)
    assert len(herramienta.overlays()) == 1
    # Pero todavía no cuenta para el total: no la soltó.
    assert herramienta.lines() == []


def test_el_mouse_sobre_la_herramienta_desactivada_no_dibuja_nada():
    """La ventana principal puede mandarle eventos igual."""
    tool = OccupancyTool()
    arrastrar(tool, 0.0, 15.0)
    assert tool.lines() == []


# -- Borrar una línea con el mismo gesto (V5_F) ------------------------------


def test_hacer_clic_sobre_una_linea_la_borra(herramienta: OccupancyTool):
    """El pliego pide las dos cosas con el mismo gesto: si el clic cae sobre una
    línea ya dibujada, la borra; si no, empieza una nueva."""
    arrastrar(herramienta, 0.0, 15.0, y=50.0)
    assert len(herramienta.lines()) == 1

    herramienta.on_mouse_press(7.5, 50.0, "left")
    assert herramienta.lines() == []


def test_un_clic_lejos_de_la_linea_no_la_borra(herramienta: OccupancyTool):
    """Si borrara desde cualquier altura, dibujar dos líneas paralelas sería
    imposible: la segunda borraría la primera."""
    arrastrar(herramienta, 0.0, 15.0, y=50.0)
    herramienta.on_mouse_press(7.5, -200.0, "left")
    assert len(herramienta.lines()) == 1


def test_se_borra_la_linea_mas_cercana_al_clic(herramienta: OccupancyTool):
    """Con dos líneas superpuestas en horizontal, gana la que está más cerca en
    vertical. Un rectángulo envolvente borraría cualquiera de las dos."""
    arrastrar(herramienta, 0.0, 20.0, y=0.0)
    arrastrar(herramienta, 0.0, 20.0, y=100.0)

    herramienta.on_mouse_press(10.0, 100.0, "left")
    (queda,) = herramienta.lines()
    assert queda.y1 == 0.0


def test_una_diagonal_se_borra_donde_esta_dibujada(herramienta: OccupancyTool):
    """La altura del clic se compara con la de la línea **en esa posición
    horizontal**, interpolando: en el medio, una diagonal de 0 a 100 µV está
    en 50."""
    herramienta.on_mouse_press(0.0, 0.0, "left")
    herramienta.on_mouse_move(30.0, 100.0)
    herramienta.on_mouse_release(30.0, 100.0, "left")

    herramienta.on_mouse_press(15.0, 50.0, "left")
    assert herramienta.lines() == []


# -- Que el gesto no dependa de la amplitud (hito 19) -------------------------
#
# `TOLERANCIA_DE_CLIC_EN_ESCALAS` es una fracción de `Session.scale_uv()`, que
# es cuántos microvoltios representa la altura del canal. Antes era un número
# fijo de microvoltios, y entonces el gesto cambiaba de sentido con la amplitud:
# con la escala en su mínimo cualquier clic borraba la línea, y con la escala en
# su máximo la línea era imposible de borrar.


def test_a_la_escala_de_fabrica_la_tolerancia_es_la_de_siempre(
    herramienta: OccupancyTool,
):
    """0,10 sobre `DEFAULT_SCALE_UV` da los 10 µV de antes. Es lo que hace que
    este cambio no altere el gesto que el usuario ya tenía."""
    assert herramienta._tolerancia_uv() == pytest.approx(
        TOLERANCIA_DE_CLIC_EN_ESCALAS * DEFAULT_SCALE_UV
    )
    assert herramienta._tolerancia_uv() == pytest.approx(10.0)


def test_con_la_amplitud_al_maximo_un_clic_lejano_ya_no_borra(
    herramienta: OccupancyTool, sesion: Session
):
    """**El síntoma que el hito 9 dice haber corregido, por el otro lado.**

    Con `scale_uv` en 1 µV, una tolerancia fija de 10 µV vale diez veces la
    altura del canal, así que cualquier clic dentro del rango horizontal de la
    línea la borraba en vez de empezar otra.
    """
    arrastrar(herramienta, 0.0, 20.0, y=0.0, canal="C3")
    for nombre in sesion.visible_channels:
        sesion.set_scale_uv(nombre, 1.0)

    # 5 µV son cinco alturas de canal: lejísimos en pantalla.
    herramienta.on_mouse_press(10.0, 5.0, "left", "C3")

    assert len(herramienta.lines()) == 1, "la línea se borró desde muy lejos"


def test_con_la_amplitud_al_minimo_la_linea_se_sigue_pudiendo_borrar(
    herramienta: OccupancyTool, sesion: Session
):
    """El error inverso: con la escala muy alta, 10 µV fijos son una milésima
    de la altura del canal y la línea se volvía imposible de señalar."""
    arrastrar(herramienta, 0.0, 20.0, y=0.0, canal="C3")
    for nombre in sesion.visible_channels:
        sesion.set_scale_uv(nombre, 10_000.0)

    # 500 µV son un vigésimo de la altura del canal: pegado a la línea.
    herramienta.on_mouse_press(10.0, 500.0, "left", "C3")

    assert herramienta.lines() == [], "la línea no se pudo borrar de tan cerca"


def test_la_tolerancia_sigue_al_canal_del_clic(sesion: Session):
    """**El canal de referencia no es una elección libre.**

    La `y` que llega a los métodos de mouse está medida contra el eje del canal
    bajo el cursor. Si la tolerancia mirara otro, los dos números hablarían de
    escalas distintas y volvería el error de unidades del hito 9.

    **Decía «el primero visible», y era cierto hasta el hito 45**: hasta
    entonces `SignalView.microvolts_at_pixel()` medía todo contra ése porque
    nadie le pasaba un canal.
    """
    tool = OccupancyTool()
    tool.activate(sesion)

    sesion.set_scale_uv("C3", 200.0)
    sesion.set_scale_uv("C4", 4_000.0)

    assert tool._tolerancia_uv("C3") == pytest.approx(20.0)
    assert tool._tolerancia_uv("C4") == pytest.approx(400.0)


def test_un_clic_en_otro_carril_no_borra_la_linea(sesion: Session):
    """**El centro de todos los carriles vale 0 µV**, así que sin mirar el
    canal un clic en el medio de cualquiera borraba una línea trazada en otro.

    Estaba tapado hasta el hito 45: mientras la `y` se medía siempre contra el
    primer canal, el centro de los demás no daba cero.
    """
    tool = OccupancyTool()
    tool.activate(sesion)
    arrastrar(tool, 0.0, 20.0, y=0.0, canal="C3")

    tool.on_mouse_press(10.0, 0.0, "left", "C4")

    assert len(tool.lines()) == 1, "el clic en otro carril borró la línea"


def test_un_clic_en_el_mismo_carril_si_la_borra(sesion: Session):
    """La otra mitad, que es la que le da sentido a la primera."""
    tool = OccupancyTool()
    tool.activate(sesion)
    arrastrar(tool, 0.0, 20.0, y=0.0, canal="C3")

    tool.on_mouse_press(10.0, 0.0, "left", "C3")

    assert tool.lines() == []


def test_la_linea_recuerda_sobre_que_canal_se_trazo(sesion: Session):
    """Es lo que el visualizador necesita para dibujarla en su carril: sin el
    nombre las dibujaba todas sobre el primero."""
    tool = OccupancyTool()
    tool.activate(sesion)

    arrastrar(tool, 0.0, 20.0, y=0.0, canal="C4")

    assert tool.lines()[0].channel_name == "C4"
    assert tool.overlays()[0].channel_name == "C4"


def test_cruzar_de_carril_no_le_cambia_el_dueno_a_la_linea(sesion: Session):
    """El canal es el de donde arrancó el trazo: cambiarlo a mitad del
    arrastre haría saltar la línea de carril mientras se dibuja."""
    tool = OccupancyTool()
    tool.activate(sesion)

    tool.on_mouse_press(0.0, 0.0, "left", "C3")
    tool.on_mouse_move(20.0, 0.0, "C4")
    tool.on_mouse_release(20.0, 0.0, "left", "C4")

    assert tool.lines()[0].channel_name == "C3"


def test_sin_sesion_la_tolerancia_cae_en_la_escala_de_fabrica():
    """Devolver cero dejaría una herramienta en la que nada se puede borrar."""
    suelta = OccupancyTool()

    assert suelta._tolerancia_uv() == pytest.approx(
        TOLERANCIA_DE_CLIC_EN_ESCALAS * DEFAULT_SCALE_UV
    )


# -- El total, y que pueda pasar del 100 % -----------------------------------


def test_el_total_puede_pasar_del_cien_por_ciento(herramienta: OccupancyTool):
    """**Confirmado con el cliente y es lo buscado, no un error de cálculo.**

    Se suman los aportes sin descontar la zona compartida, que es "sumar la
    distancia horizontal total" leído al pie de la letra. La interfaz tiene que
    poder mostrarlo sin romperse.
    """
    herramienta.add_line(OccupancyLine(0.0, 0.0, 1.0, 0.0))
    herramienta.add_line(OccupancyLine(0.0, 0.0, 1.0, 0.0))
    # El criterio va explícito: lo que este test afirma es que **sumar sin
    # descontar** puede pasar del 100 %, no cómo está configurado el programa.
    # Dependiendo de `config` fallaría al revertir la decisión del hito 0, y por
    # un motivo que no es el que persigue.
    assert herramienta.total_percentage(counts_overlap_once=False) == pytest.approx(200.0)


def test_la_otra_variante_cuenta_la_zona_compartida_una_sola_vez():
    """Revertir la decisión del hito 0 tiene que seguir siendo cambiar una
    línea de `config`, así que la variante tiene que existir y funcionar."""
    tool = OccupancyTool()
    tool.add_line(OccupancyLine(0.0, 0.0, 0.6, 0.0))
    tool.add_line(OccupancyLine(0.4, 0.0, 1.0, 0.0))

    assert tool.total_percentage(counts_overlap_once=False) == pytest.approx(120.0)
    assert tool.total_percentage(counts_overlap_once=True) == pytest.approx(100.0)


def test_dos_lineas_separadas_suman_igual_en_las_dos_variantes():
    """Sin superposición, unir intervalos no cambia nada."""
    tool = OccupancyTool()
    tool.add_line(OccupancyLine(0.0, 0.0, 0.2, 0.0))
    tool.add_line(OccupancyLine(0.5, 0.0, 0.8, 0.0))

    assert tool.total_percentage(counts_overlap_once=False) == pytest.approx(50.0)
    assert tool.total_percentage(counts_overlap_once=True) == pytest.approx(50.0)


def test_el_valor_por_defecto_sale_de_config():
    """El criterio del hito 0 no se escribe a mano en la herramienta."""
    tool = OccupancyTool()
    tool.add_line(OccupancyLine(0.0, 0.0, 0.6, 0.0))
    tool.add_line(OccupancyLine(0.4, 0.0, 1.0, 0.0))
    esperado = tool.total_percentage(counts_overlap_once=OCCUPANCY_COUNTS_OVERLAP_ONCE)
    assert tool.total_percentage() == pytest.approx(esperado)


def test_el_porcentaje_de_una_linea_suelta(herramienta: OccupancyTool):
    """V2_F: el aporte de cada línea también se muestra por separado."""
    linea = OccupancyLine(0.25, 0.0, 0.75, 0.0)
    assert herramienta.line_percentage(linea) == pytest.approx(50.0)


# -- El ciclo de vida --------------------------------------------------------


def test_cambiar_la_escala_de_tiempo_borra_las_lineas(
    herramienta_larga: OccupancyTool, sesion_larga: Session
):
    """**Es lo que V5_F significa desde la escala de tiempo libre.**

    Una línea guardada como 0,2 a 0,6 de una página de 30 s no mide nada sobre
    una de cuatro horas: dejarla dibujada sería mostrar un porcentaje de algo
    que ya no se está mirando.
    """
    arrastrar(herramienta_larga, 0.0, 15.0)

    herramienta_larga.on_view_changed(sesion_larga.viewport.zoomed(4.0))

    assert herramienta_larga.lines() == []
    assert herramienta_larga.total_percentage() == pytest.approx(0.0)


def test_cambiar_de_epoca_sin_mover_la_pagina_conserva_las_lineas(
    herramienta: OccupancyTool,
):
    """**Antes borraba, y era correcto cuando época y página eran lo mismo.**

    Con la escala libre dejó de serlo: con cuatro horas en pantalla, la flecha
    derecha mueve el resaltado de la época y no mueve nada de lo que se ve.
    Borrar ahí destruiría una medición sin que el usuario vea ningún cambio.

    Este test fija la consecuencia para que nadie la revierta creyendo que es
    un bug.
    """
    arrastrar(herramienta, 0.0, 15.0)

    herramienta.on_window_changed(1)

    assert len(herramienta.lines()) == 1


def test_desplazar_la_vista_reancla_las_lineas(
    herramienta_larga: OccupancyTool, sesion_larga: Session
):
    """El usuario corre la vista dos píxeles y no puede perder la medición.

    La línea se lleva a segundos absolutos con la página vieja y vuelve a
    fracción con la nueva, así que queda **quieta sobre la onda**: su fracción
    cambia justamente para que su posición no cambie.
    """
    arrastrar(herramienta_larga, 0.0, 15.0)
    ancho = herramienta_larga.lines()[0].horizontal_fraction

    herramienta_larga.on_view_changed(sesion_larga.viewport.panned(7.5))

    assert len(herramienta_larga.lines()) == 1
    assert herramienta_larga.lines()[0].horizontal_fraction == pytest.approx(ancho)
    assert herramienta_larga.lines()[0].x1 != 0.0


def test_una_linea_que_queda_fuera_de_la_pagina_se_descarta(
    herramienta_larga: OccupancyTool, sesion_larga: Session
):
    """Mantener una línea invisible que igual suma al porcentaje sería peor que
    perderla: el total dejaría de explicarse con lo que se ve."""
    arrastrar(herramienta_larga, 0.0, 10.0)

    herramienta_larga.on_view_changed(sesion_larga.viewport.panned(270.0))

    assert herramienta_larga.lines() == []


def test_desactivarla_conserva_las_lineas(herramienta: OccupancyTool):
    """Perder las mediciones al desactivar sería una sorpresa desagradable: el
    usuario puede querer mirar la señal sin la herramienta y volver."""
    arrastrar(herramienta, 0.0, 15.0)
    herramienta.deactivate()
    assert len(herramienta.lines()) == 1


def test_lines_devuelve_una_copia(herramienta: OccupancyTool):
    """Prestar la lista interna dejaría cambiar lo dibujado sin pasar por la
    herramienta, y el total mostrado dejaría de corresponderse."""
    arrastrar(herramienta, 0.0, 15.0)
    herramienta.lines().clear()
    assert len(herramienta.lines()) == 1


def test_clear_borra_todo(herramienta: OccupancyTool):
    arrastrar(herramienta, 0.0, 15.0)
    herramienta.clear()
    assert herramienta.lines() == []


# -- Lo que se dibuja --------------------------------------------------------


def test_los_overlays_vuelven_en_segundos(herramienta: OccupancyTool):
    """Adentro se guarda fracción, porque es lo que hace correcto el
    porcentaje; el visualizador entiende segundos."""
    arrastrar(herramienta, 0.0, 15.0)
    (segmento,) = herramienta.overlays()
    assert isinstance(segmento, SegmentOverlay)
    assert segmento.x1_seconds == pytest.approx(0.0)
    assert segmento.x2_seconds == pytest.approx(15.0)


def test_los_overlays_conservan_la_altura_en_microvoltios(
    herramienta: OccupancyTool,
):
    """`y` no entra en la medición, así que viaja sin convertirse: es lo único
    que hace falta para volver a dibujar la línea donde el usuario la trazó."""
    arrastrar(herramienta, 0.0, 15.0, y=42.0)
    (segmento,) = herramienta.overlays()
    assert segmento.y1_uv == pytest.approx(42.0)


def test_cada_overlay_dice_de_que_herramienta_es(herramienta: OccupancyTool):
    arrastrar(herramienta, 0.0, 15.0)
    (segmento,) = herramienta.overlays()
    assert segmento.tool_name == OccupancyTool.name


def test_avisa_cuando_cambia_lo_dibujado(sesion: Session):
    """La ventana principal engancha acá su repintado."""
    tool = OccupancyTool()
    avisos: list = []
    tool.on_changed = avisos.append

    tool.activate(sesion)
    arrastrar(tool, 0.0, 15.0)
    tool.on_window_changed(1)

    assert len(avisos) >= 4
    assert all(aviso is tool for aviso in avisos)


# -- Al pasar de un registro a otro ------------------------------------------


def test_apagarla_suelta_la_sesion(sesion: Session, herramienta: OccupancyTool):
    """Conservarla mantenía vivo el registro anterior después de abrir otro."""
    herramienta.deactivate()
    # Ningún atributo la guarda. No se prueba con un `weakref` porque la
    # fixture de pytest la sigue sosteniendo; eso lo mide `test_entrega.py`
    # con dos registros de verdad.
    assert all(valor is not sesion for valor in vars(herramienta).values())


def test_las_lineas_sobreviven_a_apagarla_y_prenderla(
    sesion: Session, herramienta: OccupancyTool
):
    """Es lo que promete `deactivate()`: apagar para mirar la señal y volver."""
    arrastrar(herramienta, 0.0, 15.0)
    herramienta.deactivate()
    herramienta.activate(sesion)
    assert len(herramienta.lines()) == 1


def test_las_lineas_de_otro_registro_no_pasan_al_nuevo(
    sesion: Session, sesion_larga: Session, herramienta: OccupancyTool
):
    """Son fracciones de una página de otra señal: reaparecían sobre el registro
    nuevo con su porcentaje."""
    arrastrar(herramienta, 0.0, 15.0)
    herramienta.deactivate()
    herramienta.activate(sesion_larga)
    assert herramienta.lines() == []
    assert herramienta.total_percentage() == 0.0



# -- Lo que la auditoría de los tests encontró sin verificar (hito 48) --------
#
# Cuatro mutaciones de `occupancy.py` sobrevivían a la suite **entera**: se
# podía romper el código y nadie se enteraba. Las cuatro tienen la misma causa
# —casos que ningún test recorría— y no una falta de tests en general: este
# archivo ya tenía cuarenta y cuatro.


def test_la_fraccion_se_mide_contra_la_pagina_y_no_contra_la_epoca(
    herramienta_larga: OccupancyTool, sesion_larga: Session
):
    """**Mutaba `if self._session is None` a `is not None` y nadie lo veía.**

    Con la fixture de una época, página y época miden lo mismo, así que la rama
    correcta y la de respaldo dan idéntico resultado. Hace falta una página que
    no empiece en cero y no dure una época para que se distingan.
    """
    sesion_larga.set_viewport(sesion_larga.viewport.with_start(60.0).with_span(30.0))

    # El segundo 75 cae a la mitad de una página que va de 60 a 90.
    assert herramienta_larga._a_fraccion(75.0) == pytest.approx(0.5)
    # Y contra la época, que arranca en cero, daría 2,5: un número plausible.
    assert herramienta_larga._a_fraccion(75.0) != pytest.approx(2.5)


def test_los_segundos_vuelven_desde_la_pagina_y_no_desde_la_epoca(
    herramienta_larga: OccupancyTool, sesion_larga: Session
):
    """La inversa del anterior, y el otro mutante de la misma pareja."""
    sesion_larga.set_viewport(sesion_larga.viewport.with_start(60.0).with_span(30.0))

    assert herramienta_larga._a_segundos(0.5) == pytest.approx(75.0)


def test_una_linea_inclinada_se_borra_donde_esta_dibujada(
    herramienta: OccupancyTool,
):
    """**Todas las líneas de los tests de borrado eran horizontales**, y ahí
    interpolar y tomar el punto medio dan lo mismo: el mutante que cambiaba
    `x2 == x1` por `!=` pasaba en verde.

    Con una diagonal el punto medio y la altura real difieren, que es
    justamente lo que el módulo documenta querer: con un rectángulo envolvente,
    una diagonal larga se borraría haciendo clic muy lejos de donde está.
    """
    # De (0 s, −80 µV) a (30 s, +80 µV): en el segundo 7,5 la línea pasa por −40.
    herramienta.add_line(OccupancyLine(0.0, -80.0, 1.0, 80.0))

    # Un clic en el punto medio de la línea —0 µV— está a 40 µV de ella acá.
    herramienta.on_mouse_press(7.5, 0.0, "left")
    assert len(herramienta.lines()) == 1, "se borró desde el punto medio, no desde la línea"

    herramienta.on_mouse_press(7.5, -40.0, "left")
    assert herramienta.lines() == [], "no se borró donde la línea realmente pasa"


def test_una_linea_vertical_no_rompe_al_buscar_debajo_del_clic(
    herramienta: OccupancyTool,
):
    """El otro lado del mismo `if`: sin él, una vertical divide por cero.

    Había una línea vertical en los tests, pero sólo en los del porcentaje:
    nadie le hacía clic encima.
    """
    herramienta.add_line(OccupancyLine(0.5, 0.0, 0.5, 100.0))

    herramienta.on_mouse_press(15.0, 50.0, "left")

    assert herramienta.lines() == []


def test_la_tolerancia_sin_sesion_no_rompe_aunque_le_den_un_canal():
    """**Este hueco lo dejó el hito 46**, que escribió la guarda y probó sólo
    la mitad: con `and` cambiado por `or`, pedir la tolerancia de un canal sin
    sesión busca `visible_channels` en `None`."""
    suelta = OccupancyTool()

    assert suelta._tolerancia_uv("C3") == pytest.approx(
        TOLERANCIA_DE_CLIC_EN_ESCALAS * DEFAULT_SCALE_UV
    )
