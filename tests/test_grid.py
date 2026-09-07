"""Tests de la grilla de fondo del visualizador.

El pliego fija dos densidades sobre la ventana de 30 segundos —una línea visible
cada 3 s, que la parte en 10 fragmentos, y una discreta cada 0,5 s, que la parte
en 60— y tres fondos elegibles por el usuario (V2_F).

Se puede afirmar sobre eso **sin mirar una pantalla**: cuántas líneas hay y en
qué posición están es lo que define el fondo. Los píxeles no se testean.
"""

import pytest

pg = pytest.importorskip("pyqtgraph")

from psglab.config import COARSE_GRID_SECONDS, FINE_GRID_SECONDS  # noqa: E402
from psglab.ui.grid import BackgroundStyle, GridBackground  # noqa: E402

VENTANA = 30.0


@pytest.fixture
def grilla(qt_app):
    """Una grilla sobre un gráfico de verdad, sin ventana visible.

    **Hay que mantener vivo el `PlotWidget` mientras dure el test.** Si sólo se
    guardara el `PlotItem`, Python recolectaría el widget al salir de acá, Qt
    borraría el objeto C++ de abajo y cualquier uso posterior elevaría
    `RuntimeError: Internal C++ object already deleted`. Por eso se cede desde
    un generador en vez de devolver.
    """
    plot = pg.PlotWidget()
    yield GridBackground(plot.getPlotItem())


def posiciones(grid: GridBackground) -> list[float]:
    return sorted(linea.value() for linea in grid.lines())


# -- Los tres fondos del pliego (V2_F) ---------------------------------------


def test_el_fondo_blanco_no_dibuja_ninguna_linea(grilla: GridBackground):
    grilla.set_style(BackgroundStyle.BLANK)
    grilla.redraw(VENTANA)
    assert grilla.lines() == []


def test_el_fondo_de_tres_segundos_parte_la_ventana_en_diez(
    grilla: GridBackground,
):
    """Diez fragmentos son once líneas, contando las dos de los bordes."""
    grilla.set_style(BackgroundStyle.COARSE)
    grilla.redraw(VENTANA)
    assert len(grilla.lines()) == int(VENTANA / COARSE_GRID_SECONDS) + 1


def test_el_fondo_completo_trae_las_dos_densidades(grilla: GridBackground):
    grilla.set_style(BackgroundStyle.FULL)
    grilla.redraw(VENTANA)
    esperadas = (
        int(VENTANA / COARSE_GRID_SECONDS) + 1 + int(VENTANA / FINE_GRID_SECONDS) + 1
    )
    assert len(grilla.lines()) == esperadas


def test_las_lineas_caen_en_los_multiplos_que_pide_el_pliego(
    grilla: GridBackground,
):
    grilla.set_style(BackgroundStyle.COARSE)
    grilla.redraw(VENTANA)
    assert posiciones(grilla) == [
        paso * COARSE_GRID_SECONDS
        for paso in range(int(VENTANA / COARSE_GRID_SECONDS) + 1)
    ]


def test_la_ultima_linea_cae_exactamente_en_el_borde(grilla: GridBackground):
    """**Se multiplica en vez de acumular.**

    Sumar 0,5 sesenta veces arrastra error de punto flotante y la última línea
    queda corrida del borde, que es el mismo error que `core/windows.py`
    documenta para las ventanas.
    """
    grilla.set_style(BackgroundStyle.FULL)
    grilla.redraw(VENTANA)
    assert max(posiciones(grilla)) == VENTANA


def test_ninguna_linea_se_sale_de_la_ventana(grilla: GridBackground):
    grilla.set_style(BackgroundStyle.FULL)
    grilla.redraw(VENTANA)
    assert all(0.0 <= posicion <= VENTANA for posicion in posiciones(grilla))


# -- Cambiar de fondo --------------------------------------------------------


def test_cambiar_de_fondo_redibuja_solo(grilla: GridBackground):
    """El usuario elige el fondo del menú; no tiene que decir además cuánto dura
    la ventana."""
    grilla.redraw(VENTANA)
    grilla.set_style(BackgroundStyle.BLANK)
    assert grilla.lines() == []

    grilla.set_style(BackgroundStyle.COARSE)
    assert len(grilla.lines()) > 0


def test_redibujar_no_acumula_lineas(grilla: GridBackground):
    """Cada redibujado reemplaza: dibujar la ventana siguiente no puede dejar
    encima las líneas de la anterior."""
    grilla.set_style(BackgroundStyle.FULL)
    grilla.redraw(VENTANA)
    cuantas = len(grilla.lines())
    grilla.redraw(VENTANA)
    assert len(grilla.lines()) == cuantas


def test_borrar_deja_el_grafico_limpio(grilla: GridBackground):
    grilla.redraw(VENTANA)
    grilla.clear()
    assert grilla.lines() == []


# -- La ventana no siempre dura 30 s -----------------------------------------


def test_la_grilla_se_adapta_a_otra_duracion_de_ventana(grilla: GridBackground):
    """`redraw()` recibe la duración por parámetro y no la lee de `config`: la
    grilla tiene que seguir siendo correcta si el laboratorio trabaja con
    ventanas de otro tamaño."""
    grilla.set_style(BackgroundStyle.COARSE)
    grilla.redraw(60.0)
    assert max(posiciones(grilla)) == 60.0


def test_una_ventana_mas_corta_que_una_division(grilla: GridBackground):
    """Queda sólo la línea del comienzo, y no se rompe."""
    grilla.set_style(BackgroundStyle.COARSE)
    grilla.redraw(1.0)
    assert posiciones(grilla) == [0.0]


# -- Las etiquetas que ve el usuario -----------------------------------------


def test_las_etiquetas_de_los_fondos_salen_de_config():
    """Un texto fijo acá seguiría prometiendo la separación vieja el día que el
    laboratorio cambie la grilla. Hay un chequeo de consistencia que lo prohíbe,
    y esto lo afirma desde el otro lado.
    """
    assert "3" in BackgroundStyle.COARSE.value
    assert "0,5" in BackgroundStyle.FULL.value


def test_el_separador_decimal_es_la_coma():
    """Es el idioma del programa: nadie escribe "0.5 segundos" a mano en
    español."""
    assert "0.5" not in BackgroundStyle.FULL.value
