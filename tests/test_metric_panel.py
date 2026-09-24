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
from PySide6.QtCore import Qt

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
# -- Que la curva se vea ----------------------------------------------------


def test_todos_los_canales_se_dibujan_con_una_pluma_visible(panel: MetricPanel):
    """El segundo canal en adelante se pedía con `mkPen(None)`, que es `NoPen`.

    La curva entraba en la leyenda y no se dibujaba, así que pedir la
    complejidad de tres canales mostraba uno y los otros dos parecían no
    haberse calculado. Es la clase de fallo que no da error: da un gráfico
    incompleto que se lee como un resultado.
    """
    panel.set_metric("PE", {"C3": serie([0.1, 0.2]), "C4": serie([0.3, 0.4]), "O1": serie([0.5, 0.6])})

    estilos = [
        panel._curvas[nombre].opts["pen"].style() for nombre in panel.channels()
    ]

    assert Qt.PenStyle.NoPen not in estilos


def test_dos_canales_no_comparten_color(panel: MetricPanel):
    """Tres curvas del mismo color son tan ilegibles como una sola."""
    panel.set_metric("PE", {"C3": serie([0.1]), "C4": serie([0.2])})

    colores = [
        panel._curvas[nombre].opts["pen"].color().name() for nombre in panel.channels()
    ]

    assert len(set(colores)) == len(colores)


# -- La pista con el panel vacío (hito 30) --------------------------------------


def test_la_pista_se_lee_con_el_panel_vacio(panel: MetricPanel):
    """Se puede mostrar sin resultado —desde «Herramientas», o después de que
    cambió la señal— y un gráfico en blanco no dice qué hacer con él."""
    panel.set_hint("Se pide desde Analizar")
    assert panel.visible_hint() == "Se pide desde Analizar"


def test_la_pista_se_va_con_un_resultado_y_vuelve_al_vaciarlo(panel: MetricPanel):
    panel.set_hint("Se pide desde Analizar")
    panel.set_metric("Entropía", {"C3": np.array([0.5, 0.6])})
    assert panel.visible_hint() == ""
    panel.clear_metric()
    assert panel.visible_hint() == "Se pide desde Analizar"


# -- La leyenda, en su propia franja (hito 40) -------------------------------


def test_la_leyenda_nombra_los_canales_dibujados(panel: MetricPanel):
    """**pyqtgraph la dibuja adentro del gráfico**, flotando sobre la esquina
    superior derecha: con una noche entera dibujada se apoya justo sobre el
    tramo de más actividad y tapa el dato."""
    panel.set_metric("Entropía", {"C3": np.array([0.5, 0.6]), "O1": np.array([0.4, 0.7])})

    assert panel.legend_channels() == ["C3", "O1"]


def test_pedir_otra_metrica_rehace_la_leyenda_entera(panel: MetricPanel):
    """Completarla dejaría en la franja el nombre de un canal que ya no está
    dibujado, que es la misma regla que las curvas."""
    panel.set_metric("Entropía", {"C3": np.array([0.5]), "O1": np.array([0.4])})

    panel.set_metric("Lempel-Ziv", {"C4": np.array([0.9])})

    assert panel.legend_channels() == ["C4"]


def test_sin_metrica_no_hay_leyenda(panel: MetricPanel):
    assert panel.legend_channels() == []


# -- Los números del eje, como son (hito 53) --------------------------------


def test_una_metrica_menor_que_uno_no_se_multiplica_por_mil(panel: MetricPanel):
    """**Una entropía de 0,75 se leía «750»**, con «(x0.001)» en el rótulo:
    pyqtgraph ponía el prefijo por su cuenta. Lo encontró la comparación con el
    prototipo; los tests miraban los datos y no lo que dice el eje."""
    panel.set_metric("Entropía espectral", {"C3": serie([0.5, 0.62, 0.75])})
    eje = panel.grafico.getPlotItem().getAxis("left")

    assert eje.autoSIPrefixScale == 1.0
    assert "x0.001" not in eje.labelString()


# -- La época actual, el eje y los huecos (hito 54) -------------------------


def test_la_epoca_actual_se_marca_en_base_uno(panel: MetricPanel):
    """**La curva no decía dónde estaba parado el usuario.** La época 0 del
    modelo es la 1 del eje, como el resto del panel."""
    panel.set_metric("Entropía", {"C3": serie([0.5, 0.6, 0.7, 0.8])})

    panel.set_current_window(2)

    assert panel._marca_actual.value() == 3.0
    assert panel._marca_actual.isVisible()


def test_la_marca_se_mueve_y_no_se_duplica(panel: MetricPanel):
    import pyqtgraph as pg

    panel.set_metric("Entropía", {"C3": serie([0.5, 0.6, 0.7, 0.8])})
    panel.set_current_window(0)
    panel.set_current_window(3)

    lineas = [
        i for i in panel.grafico.getPlotItem().items if isinstance(i, pg.InfiniteLine)
    ]
    assert len(lineas) == 1
    assert lineas[0].value() == 4.0


def test_sin_epoca_la_marca_se_oculta(panel: MetricPanel):
    panel.set_metric("Entropía", {"C3": serie([0.5, 0.6])})
    panel.set_current_window(1)

    panel.set_current_window(None)

    assert not panel._marca_actual.isVisible()


def test_el_eje_lleva_las_marcas_que_le_pasan(panel: MetricPanel):
    """Son las del hipnograma, para que los dos gráficos de la noche hablen la
    misma unidad."""
    panel.set_time_ticks([(1.0, "23:00"), (3.0, "23:01")], clock_time=True)
    eje = panel.grafico.getPlotItem().getAxis("bottom")

    assert eje._tickLevels == [[(1.0, "23:00"), (3.0, "23:01")]]
    assert "Hora" in eje.labelString()


def test_en_numero_de_ventana_el_eje_lo_dice(panel: MetricPanel):
    panel.set_time_ticks([(1.0, "1"), (2.0, "2")], clock_time=False)

    assert "Ventana" in panel.grafico.getPlotItem().getAxis("bottom").labelString()


def test_el_encabezado_dice_cuantas_ventanas_quedaron_sin_dato(panel: MetricPanel):
    """**Un hueco de una ventana entre dos mil no se ve.** Se cuenta la
    ventana sin dato en cualquier canal, una sola vez."""
    panel.set_metric(
        "Entropía",
        {"C3": serie([0.5, np.nan, 0.7, np.nan]), "C4": serie([np.nan, np.nan, 0.6, 0.7])},
    )

    assert panel.gap_count() == 3
    assert panel.header.detail() == "3 ventanas sin dato"


def test_sin_huecos_el_encabezado_no_dice_nada(panel: MetricPanel):
    panel.set_metric("Entropía", {"C3": serie([0.5, 0.6])})

    assert panel.header.detail() == ""
