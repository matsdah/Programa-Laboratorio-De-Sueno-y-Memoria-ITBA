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
