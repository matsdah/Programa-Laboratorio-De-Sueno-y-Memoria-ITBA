"""Tests de la herramienta de ocupación horizontal.

El pliego define esta herramienta con ejemplos numéricos explícitos, así que
se puede testear al pie de la letra. Los casos de abajo son literalmente los
del pliego, más los bordes.

La definición es una **proyección sobre el eje horizontal**: lo que cuenta es
|x2 - x1| sobre el ancho de la ventana, no el largo de la línea. Una diagonal
larga puede ocupar menos que una horizontal corta.
"""

import pytest

from psglab.tools.occupancy import OccupancyLine, OccupancyTool

pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")


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
