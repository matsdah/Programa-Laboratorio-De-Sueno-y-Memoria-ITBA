"""Tests de la carrocería que comparten los paneles de análisis.

Lo que se verifica es lo que el encabezado y el cartel de vacío **dicen**, y la
decisión que los motivó: que el cartel **reemplace** al gráfico en vez de
escribirle encima. Ésa se puede afirmar sin mirar una pantalla —es qué widget
está al frente de la pila— y es exactamente lo que no se veía cuando las dos
cosas iban al título del gráfico.
"""

import pytest
from PySide6.QtGui import QFont

pg = pytest.importorskip("pyqtgraph")

from psglab.ui import theme  # noqa: E402
from psglab.ui.connectivity_panel import ConnectivityPanel  # noqa: E402
from psglab.ui.filter_panel import FilterPanel  # noqa: E402
from psglab.ui.ica_panel import IcaPanel  # noqa: E402
from psglab.ui.impedance_panel import ImpedancePanel  # noqa: E402
from psglab.ui.metric_panel import MetricPanel  # noqa: E402
from psglab.ui.panel_header import (  # noqa: E402
    ALTO_DEL_ENCABEZADO,
    EmptyState,
    PanelHeader,
    plain_axes,
)
from psglab.ui.psd_panel import PsdPanel  # noqa: E402


@pytest.fixture
def encabezado(qt_app) -> PanelHeader:
    """Un encabezado suelto, con su rótulo."""
    return PanelHeader("Espectro")


# -- El encabezado ------------------------------------------------------------


def test_el_rotulo_se_escribe_en_mayusculas(encabezado: PanelHeader):
    """**No con `text-transform`**, que la hoja de estilo de Qt no soporta. El
    prototipo lo usaba, y fue una de las cosas que no se pudieron llevar a la
    ventana en el hito 36."""
    assert encabezado.label() == "ESPECTRO"


def test_el_rotulo_lleva_espaciado_entre_letras(encabezado: PanelHeader):
    """`letter-spacing` tampoco existe en la hoja de estilo, pero `QFont` sí lo
    sabe hacer: es lo que le da el aire a una palabra corta en mayúsculas."""
    fuente = encabezado._rotulo.font()

    assert fuente.letterSpacingType() == QFont.SpacingType.AbsoluteSpacing
    assert fuente.letterSpacing() > 0


def test_la_descripcion_y_el_metodo_son_dos_cosas(encabezado: PanelHeader):
    """Qué se está mirando y cómo se calculó van a los extremos de la franja:
    en un renglón solo, el método empujaba la descripción fuera de la vista."""
    encabezado.set_caption("Ventana 341 · C3 (EEG)")
    encabezado.set_detail("Welch · 4 s · Hann")

    assert encabezado.caption() == "Ventana 341 · C3 (EEG)"
    assert encabezado.detail() == "Welch · 4 s · Hann"


def test_el_encabezado_tiene_alto_fijo(encabezado: PanelHeader):
    """Es la franja contra la que se alinean los seis paneles: uno más alto que
    otro se nota al cambiar de solapa."""
    assert encabezado.height() == ALTO_DEL_ENCABEZADO


# -- El cartel de vacío -------------------------------------------------------


def test_el_cartel_dice_de_donde_se_pide(qt_app):
    """El texto lo arma la ventana principal con `menus.menu_path()`, así que
    sigue al menú si alguien lo renombra."""
    cartel = EmptyState()
    cartel.set_text("Se pide desde Analizar → Espectro de la ventana…")

    assert "Analizar" in cartel.text()


def test_el_cartel_arranca_sin_texto(qt_app):
    assert EmptyState().text() == ""


def test_el_icono_del_cartel_sigue_al_esquema(qt_app):
    """Un `QPixmap` ya dibujado no cambia de color, así que hay que rehacerlo:
    es la misma razón por la que los botones de la barra rehacen el suyo."""
    cartel = EmptyState()
    antes = cartel._icono.pixmap().toImage()

    theme.set_current(theme.NOCTURNO)
    try:
        cartel.apply_scheme()
        despues = cartel._icono.pixmap().toImage()
    finally:
        theme.set_current(theme.SERENO)

    assert antes != despues


# -- Los tres paneles de curva usan la misma carrocería -----------------------


PANELES = (PsdPanel, MetricPanel, ConnectivityPanel)

#: Los seis paneles de análisis. **Los seis llevan encabezado desde el hito
#: 41**: con cuatro puestos y dos sin poner, cambiar de solapa movía el
#: contenido treinta y cuatro píxeles para arriba y para abajo.
TODOS_LOS_PANELES = (
    PsdPanel,
    MetricPanel,
    ConnectivityPanel,
    ImpedancePanel,
    FilterPanel,
    IcaPanel,
)


@pytest.mark.parametrize("clase", TODOS_LOS_PANELES, ids=lambda c: c.__name__)
def test_cada_panel_trae_su_encabezado(qt_app, clase):
    """La fila que dice qué panel es y qué se está mirando.

    **Los seis y no cuatro.** Con dos sin encabezado, cambiar de solapa movía
    el contenido treinta y cuatro píxeles para arriba y para abajo."""
    panel = clase()

    assert panel.header.label() != ""


@pytest.mark.parametrize("clase", TODOS_LOS_PANELES, ids=lambda c: c.__name__)
def test_todos_los_encabezados_miden_lo_mismo(qt_app, clase):
    """Es la franja contra la que se alinean los seis."""
    panel = clase()

    assert panel.header.height() == ALTO_DEL_ENCABEZADO


@pytest.mark.parametrize("clase", PANELES, ids=lambda c: c.__name__)
def test_sin_pista_ni_resultado_se_ve_el_grafico(qt_app, clase):
    """Un panel recién construido no tiene nada que explicar todavía."""
    panel = clase()

    assert panel._pila.currentWidget() is panel._pila.widget(0)


@pytest.mark.parametrize("clase", PANELES, ids=lambda c: c.__name__)
def test_con_la_pista_puesta_el_cartel_reemplaza_al_grafico(qt_app, clase):
    """**La decisión que motivó el módulo.** Con el texto en el título del
    gráfico, el panel vacío seguía mostrando ejes, grilla y leyenda detrás de
    la frase: se leía como un resultado que dio cero."""
    panel = clase()

    panel.set_hint("Se pide desde Analizar…")

    assert panel._pila.currentWidget() is panel.vacio
    assert panel.visible_hint() == "Se pide desde Analizar…"


@pytest.mark.parametrize("clase", PANELES, ids=lambda c: c.__name__)
def test_la_descripcion_va_al_encabezado_y_no_al_grafico(qt_app, clase):
    """Hasta el hito 39 iba al título del gráfico, centrada sobre el dibujo y
    sin ninguna línea que la separara."""
    panel = clase()
    panel.set_caption("Ventana 341 · C3")

    assert panel.caption() == "Ventana 341 · C3"
    assert panel.grafico.getPlotItem().titleLabel.text == ""


# -- El panel de ICA, que tiene dos columnas ---------------------------------


def test_en_ica_el_cartel_reemplaza_las_dos_columnas(qt_app):
    """**Y no sólo los gráficos.** Sin descomposición, la lista de componentes
    está vacía y el botón de aplicar, apagado: media pantalla de controles
    muertos al lado de una frase se lee como un panel roto."""
    panel = IcaPanel()

    panel.set_hint("Se pide desde Filtrar → Análisis de componentes…")

    assert panel._pila.currentWidget() is panel.vacio


def test_el_encabezado_de_ica_dice_cuantos_componentes_salieron(qt_app):
    """Es lo primero que se mira: de cuántos hay que decidir."""
    panel = IcaPanel()

    panel.set_components([{"C3": 0.5, "C4": -0.2}, {"C3": 0.1, "C4": 0.8}])

    assert panel.header.caption() == "2 componentes · 2 canales"


# -- Los ejes sin prefijo automático (hito 53) ------------------------------


def test_los_ejes_numericos_de_los_paneles_no_llevan_prefijo(qt_app):
    """Los cuatro gráficos de análisis con eje numérico pasan por
    `plain_axes()`. Con el prefijo, una entropía de 0,75 se leía «750»."""
    import pyqtgraph as pg

    for panel in (MetricPanel(), PsdPanel(), IcaPanel()):
        for grafico in panel.findChildren(pg.PlotWidget):
            item = grafico.getPlotItem()
            for lado in ("left", "bottom"):
                assert not item.getAxis(lado).autoSIPrefix, (type(panel).__name__, lado)


def test_plain_axes_apaga_el_prefijo_de_los_dos_ejes(qt_app):
    import pyqtgraph as pg

    grafico = pg.PlotWidget()
    item = grafico.getPlotItem()
    plain_axes(item)

    assert not item.getAxis("left").autoSIPrefix
    assert not item.getAxis("bottom").autoSIPrefix
