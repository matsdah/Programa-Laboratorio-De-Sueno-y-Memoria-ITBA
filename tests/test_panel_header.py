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
from psglab.ui.metric_panel import MetricPanel  # noqa: E402
from psglab.ui.panel_header import (  # noqa: E402
    ALTO_DEL_ENCABEZADO,
    EmptyState,
    PanelHeader,
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


def test_los_dos_textos_son_lecturas(encabezado: PanelHeader):
    """Llevan números —la ventana, la frecuencia, el segmento— y el esquema les
    da la tipografía de ancho fijo por esta propiedad."""
    assert encabezado._descripcion.property(theme.READOUT_PROPERTY)
    assert encabezado._detalle.property(theme.READOUT_PROPERTY)


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


@pytest.mark.parametrize("clase", PANELES, ids=lambda c: c.__name__)
def test_cada_panel_trae_su_encabezado(qt_app, clase):
    """La fila que dice qué panel es y qué se está mirando."""
    panel = clase()

    assert panel.header.label() != ""


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
