"""Tests del mapa de calor de conectividad.

**El dibujo no se testea.** Lo que sí son las dos decisiones que hacen legible
el panel:

- **Los ejes llevan los nombres de los canales**, no números. Una matriz de
  conectividad sin saber qué fila es qué electrodo no se puede leer, y ése es
  el motivo por el que este panel existe en vez de imprimir el array.
- **La escala de color es fija, de 0 a 1**, y no ajustada a cada matriz. Con la
  escala automática dos ventanas con conectividades muy distintas se verían
  iguales —cada una normalizada contra sí misma— y comparar ventanas es
  justamente lo que el investigador va a hacer.
"""

import numpy as np
import pytest

pytest.importorskip("pyqtgraph")

from psglab.ui.connectivity_panel import ConnectivityPanel  # noqa: E402


@pytest.fixture
def panel(qt_app) -> ConnectivityPanel:
    widget = ConnectivityPanel()
    widget.resize(400, 400)
    return widget


def matriz(n: int = 3) -> np.ndarray:
    """Una matriz simétrica con la diagonal en cero, como la real."""
    m = np.abs(np.random.default_rng(0).random((n, n)))
    m = (m + m.T) / 2
    np.fill_diagonal(m, 0.0)
    return m


# -- Qué queda dibujado ------------------------------------------------------


def test_arranca_vacio(panel: ConnectivityPanel):
    assert panel.channels() == []
    assert panel.matrix() is None


def test_guarda_la_matriz_que_se_le_paso(panel: ConnectivityPanel):
    m = matriz()
    panel.set_matrix(m, ["C3", "C4", "O1"])

    assert np.allclose(panel.matrix(), m)


def test_guarda_los_canales_en_orden(panel: ConnectivityPanel):
    panel.set_matrix(matriz(), ["C3", "C4", "O1"])

    assert panel.channels() == ["C3", "C4", "O1"]


# -- Los rótulos, que es lo que lo hace legible ------------------------------


def test_los_ejes_llevan_los_nombres_de_canal(panel: ConnectivityPanel):
    """**Sin esto el mapa no se puede leer.** Una matriz de conectividad sin
    saber qué fila es qué electrodo es un cuadro de colores."""
    panel.set_matrix(matriz(), ["C3", "C4", "O1"])

    assert panel.axis_labels() == ["C3", "C4", "O1"]


def test_los_rotulos_siguen_al_orden_de_las_filas(panel: ConnectivityPanel):
    panel.set_matrix(matriz(), ["O1", "C3", "C4"])

    assert panel.axis_labels() == ["O1", "C3", "C4"]


def test_redibujar_cambia_los_rotulos(panel: ConnectivityPanel):
    """Si quedaran los de antes, el mapa nuevo se leería con los nombres
    equivocados, que es peor que no tener ninguno."""
    panel.set_matrix(matriz(3), ["C3", "C4", "O1"])
    panel.set_matrix(matriz(2), ["Fp1", "Fp2"])

    assert panel.axis_labels() == ["Fp1", "Fp2"]
    assert panel.channels() == ["Fp1", "Fp2"]


# -- La escala de color ------------------------------------------------------


def test_la_escala_es_fija_de_cero_a_uno(panel: ConnectivityPanel):
    """**Con escala automática, comparar ventanas sería imposible**: cada una
    quedaría normalizada contra sí misma y todas se verían igual de intensas."""
    assert panel.color_range == (0.0, 1.0)


def test_la_escala_no_cambia_con_la_matriz(panel: ConnectivityPanel):
    floja = np.full((2, 2), 0.05)
    np.fill_diagonal(floja, 0.0)
    panel.set_matrix(floja, ["A", "B"])
    antes = panel.color_range

    fuerte = np.full((2, 2), 0.95)
    np.fill_diagonal(fuerte, 0.0)
    panel.set_matrix(fuerte, ["A", "B"])

    assert panel.color_range == antes


# -- Vaciar ------------------------------------------------------------------


def test_vaciar_lo_deja_como_al_principio(panel: ConnectivityPanel):
    panel.set_matrix(matriz(), ["C3", "C4", "O1"])
    panel.clear_matrix()

    assert panel.channels() == []
    assert panel.matrix() is None
    assert panel.axis_labels() == []


def test_una_matriz_con_nan_no_rompe(panel: ConnectivityPanel):
    """Es lo que llega de una ventana que no se pudo medir."""
    panel.set_matrix(np.full((2, 2), np.nan), ["A", "B"])

    assert panel.channels() == ["A", "B"]


# -- La pista con el panel vacío (hito 30) --------------------------------------


def test_la_pista_se_lee_con_el_panel_vacio(panel: ConnectivityPanel):
    """Se puede mostrar sin resultado —desde «Herramientas», o después de que
    cambió la señal— y un gráfico en blanco no dice qué hacer con él."""
    panel.set_hint("Se pide desde Analizar")
    assert panel.visible_hint() == "Se pide desde Analizar"


def test_la_pista_se_va_con_un_resultado_y_vuelve_al_vaciarlo(panel: ConnectivityPanel):
    panel.set_hint("Se pide desde Analizar")
    panel.set_matrix(np.eye(2), ["C3", "C4"])
    assert panel.visible_hint() == ""
    panel.clear_matrix()
    assert panel.visible_hint() == "Se pide desde Analizar"


# -- La barra de color (hito 31) ---------------------------------------------------


def test_la_barra_no_sale_de_cero_a_uno(panel: ConnectivityPanel):
    """Sin límites se podía arrastrar a cualquier lado."""
    panel._barra.setLevels((-0.5, 2.0))
    assert panel._barra.levels() == (0.0, 1.0)


def test_la_barra_se_arrastra_de_a_centesimos(panel: ConnectivityPanel):
    """Redondeaba a enteros, y sobre una escala de 0 a 1 eso hacía que todo
    arrastre volviera a su lugar o saltara al otro extremo."""
    assert panel._barra.rounding == pytest.approx(0.01)


def test_una_matriz_nueva_conserva_el_contraste_elegido(panel: ConnectivityPanel):
    panel.set_matrix(np.eye(2), ["C3", "C4"])
    panel._barra.setLevels((0.2, 0.8))

    panel.set_matrix(np.eye(2) * 0.5, ["C3", "C4"])

    assert panel._barra.levels() == (0.2, 0.8)
    assert tuple(panel._imagen.levels) == pytest.approx((0.2, 0.8))


def test_vaciar_el_panel_devuelve_la_barra_a_cero_uno(panel: ConnectivityPanel):
    panel.set_matrix(np.eye(2), ["C3", "C4"])
    panel._barra.setLevels((0.2, 0.8))

    panel.clear_matrix()

    assert panel._barra.levels() == (0.0, 1.0)


# -- Qué mide la escala de color (hito 40) -----------------------------------


def test_la_escala_dice_que_mide(panel: ConnectivityPanel):
    """**Decía de 0 a 1 y no de qué.** Un mapa de colores sin la unidad se
    puede leer de izquierda a derecha, pero no se puede comparar con el de otra
    medida."""
    panel.set_matrix(np.eye(2), ["C3", "C4"], measure="wPLI")

    assert panel.measure() == "wPLI"


def test_sin_medida_la_escala_no_rotula_nada(panel: ConnectivityPanel):
    """Es lo que pasa con el camino viejo, que no la pasaba: mejor sin rótulo
    que con uno inventado."""
    panel.set_matrix(np.eye(2), ["C3", "C4"])

    assert panel.measure() == ""


def test_vaciar_el_panel_borra_la_medida(panel: ConnectivityPanel):
    """Una escala rotulada sobre un panel vacío diría que hay un resultado."""
    panel.set_matrix(np.eye(2), ["C3", "C4"], measure="wPLI")

    panel.clear_matrix()

    assert panel.measure() == ""
