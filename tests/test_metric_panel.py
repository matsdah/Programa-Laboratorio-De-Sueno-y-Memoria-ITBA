"""Tests del panel de métrica por ventana.

**El dibujo no se testea.** Lo que sí son las dos decisiones que hacen que el
panel sirva de algo:

- **El eje va en base 1**, como el histograma y la barra de estado. Dibujar
  desde 0 desplazaría la curva una ventana respecto del histograma, que es
  exactamente el error que hace que dos gráficos alineados no lo estén.
- **Los NaN se dibujan como hueco y no como cero.** Un cero es un valor de
  complejidad plausible y bajo, indistinguible a ojo de una medición real, así
  que pintarlo mentiría sobre una ventana que no se midió.
"""

import numpy as np
import pytest

pytest.importorskip("pyqtgraph")

from psglab.ui.metric_panel import MetricPanel  # noqa: E402


@pytest.fixture
def panel(qt_app) -> MetricPanel:
    widget = MetricPanel()
    widget.resize(600, 300)
    return widget


def serie(valores: list[float]) -> np.ndarray:
    return np.array(valores, dtype=float)


# -- Qué queda dibujado ------------------------------------------------------


def test_arranca_vacio(panel: MetricPanel):
    assert panel.channels() == []
    assert panel.metric_label == ""


def test_dibuja_una_curva_por_canal(panel: MetricPanel):
    panel.set_metric("PE", {"C3": serie([0.1, 0.2]), "C4": serie([0.3, 0.4])})

    assert panel.channels() == ["C3", "C4"]


def test_los_valores_son_los_que_se_pasaron(panel: MetricPanel):
    valores = serie([0.1, 0.5, 0.9])
    panel.set_metric("PE", {"C3": valores})

    assert np.allclose(panel.series("C3"), valores)


def test_el_rotulo_dice_que_se_esta_midiendo(panel: MetricPanel):
    """Un número por ventana sin decir de qué es no sirve."""
    panel.set_metric("higuchi_fractal_dimension", {"C3": serie([1.2, 1.3])})

    assert panel.metric_label == "higuchi_fractal_dimension"


def test_un_canal_que_no_esta_devuelve_none(panel: MetricPanel):
    panel.set_metric("PE", {"C3": serie([0.1])})

    assert panel.series("O2") is None


# -- La base 1 ---------------------------------------------------------------


def test_el_eje_empieza_en_uno(panel: MetricPanel):
    """**Base 0 adentro, base 1 al mostrar**, que es la regla del proyecto."""
    panel.set_metric("PE", {"C3": serie([0.1, 0.2, 0.3])})

    assert panel.window_positions("C3")[0] == 1.0


def test_hay_una_posicion_por_valor(panel: MetricPanel):
    panel.set_metric("PE", {"C3": serie([0.1, 0.2, 0.3, 0.4])})

    posiciones = panel.window_positions("C3")
    assert len(posiciones) == 4
    assert list(posiciones) == [1.0, 2.0, 3.0, 4.0]


# -- Los NaN -----------------------------------------------------------------


def test_las_ventanas_sin_medir_se_declaran_como_hueco(panel: MetricPanel):
    """**El error que este panel existe para no cometer**: pintar el NaN como
    cero lo haría indistinguible de una complejidad baja real."""
    panel.set_metric("PE", {"C3": serie([0.1, np.nan, 0.3])})

    assert panel.gap_windows("C3") == [2]


def test_sin_nan_no_hay_huecos(panel: MetricPanel):
    panel.set_metric("PE", {"C3": serie([0.1, 0.2, 0.3])})

    assert panel.gap_windows("C3") == []


def test_los_huecos_tambien_van_en_base_uno(panel: MetricPanel):
    """La última ventana de un registro de tres es la 3, no la 2."""
    panel.set_metric("PE", {"C3": serie([0.1, 0.2, np.nan])})

    assert panel.gap_windows("C3") == [3]


def test_el_valor_del_hueco_sigue_siendo_nan(panel: MetricPanel):
    """No se lo reemplaza por cero al guardarlo: quien lea la serie tiene que
    ver que no se midió."""
    panel.set_metric("PE", {"C3": serie([0.1, np.nan, 0.3])})

    assert np.isnan(panel.series("C3")[1])


# -- Redibujar reemplaza -----------------------------------------------------


def test_redibujar_no_acumula(panel: MetricPanel):
    """Dos métricas superpuestas quedarían en escalas distintas."""
    panel.set_metric("PE", {"C3": serie([0.1, 0.2])})
    panel.set_metric("Higuchi", {"O1": serie([1.2, 1.3])})

    assert panel.channels() == ["O1"]
    assert panel.metric_label == "Higuchi"


def test_vaciar_lo_deja_como_al_principio(panel: MetricPanel):
    panel.set_metric("PE", {"C3": serie([0.1])})
    panel.clear_metric()

    assert panel.channels() == []


def test_una_serie_vacia_no_rompe(panel: MetricPanel):
    panel.set_metric("PE", {"C3": serie([])})

    assert panel.channels() == ["C3"]
    assert panel.gap_windows("C3") == []
