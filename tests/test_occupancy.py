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

from psglab.config import OCCUPANCY_COUNTS_OVERLAP_ONCE
from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.base import SegmentOverlay
from psglab.tools.occupancy import OccupancyLine, OccupancyTool


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
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, 3000)),
        sampling_rate=100.0,
    )
    return Session(registro, Scoring(1, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def herramienta(sesion: Session) -> OccupancyTool:
    tool = OccupancyTool()
    tool.activate(sesion)
    return tool


def arrastrar(tool: OccupancyTool, desde_s: float, hasta_s: float, y: float = 0.0) -> None:
    """Un gesto completo: apretar, mover y soltar, en segundos."""
    tool.on_mouse_press(desde_s, y, "left")
    tool.on_mouse_move(hasta_s, y)
    tool.on_mouse_release(hasta_s, y, "left")


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


def test_cambiar_de_ventana_borra_las_lineas(herramienta: OccupancyTool):
    """V5_F: las líneas miden algo de la ventana que se estaba mirando, así que
    no significan nada en la siguiente."""
    arrastrar(herramienta, 0.0, 15.0)
    herramienta.on_window_changed(1)
    assert herramienta.lines() == []
    assert herramienta.total_percentage() == pytest.approx(0.0)


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
