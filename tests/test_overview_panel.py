"""Tests del panel de contexto (Übersicht).

**El dibujo no se testea.** Lo que sí, y es el motivo por el que
`OverviewPanel` separa `rectangles()` de `paintEvent()`, es la decisión de qué
va dónde: cuántas ventanas entran, cuál está marcada como actual, en qué orden
salen y cuánto mide cada rectángulo.

Es la mitad que faltaba del hito 9: `OverviewTool` estaba completa y testeada
desde el hito 7, y no había ningún widget que la consumiera, así que las tres
funcionalidades que el pliego pide para la Übersicht no se podían ver en el
programa corriendo.
"""

import pytest

pytest.importorskip("pyqtgraph")

from psglab.tools.overview import OverviewWindow  # noqa: E402
from psglab.ui.overview_panel import OverviewPanel  # noqa: E402

ANCHO = 500
ALTO = 80


@pytest.fixture
def panel(qt_app) -> OverviewPanel:
    """Un panel de tamaño conocido, sin ventana visible."""
    widget = OverviewPanel()
    widget.resize(ANCHO, ALTO)
    return widget


def vecinas(actual: int, antes: int = 2, despues: int = 2) -> tuple[OverviewWindow, ...]:
    """Lo que publicaría `OverviewTool` alrededor de una ventana."""
    return tuple(
        OverviewWindow(index=i, is_current=(i == actual))
        for i in range(actual - antes, actual + despues + 1)
    )


# -- Qué se muestra (V1_F) ---------------------------------------------------


def test_sin_nada_abierto_no_dibuja_ninguna_ventana(panel: OverviewPanel):
    """El panel se construye antes de que haya un registro."""
    assert panel.rectangles() == []
    assert panel.current_index is None


def test_muestra_todas_las_ventanas_que_le_pasan(panel: OverviewPanel):
    panel.set_windows(vecinas(actual=10))

    assert [v.index for v, _ in panel.rectangles()] == [8, 9, 10, 11, 12]


def test_la_ventana_actual_queda_marcada(panel: OverviewPanel):
    """V1_F: la actual se pinta distinta. Acá se afirma cuál es, no el color."""
    panel.set_windows(vecinas(actual=10))

    actuales = [v.index for v, _ in panel.rectangles() if v.is_current]
    assert actuales == [10]
    assert panel.current_index == 10


def test_el_orden_es_el_que_manda_la_herramienta(panel: OverviewPanel):
    """Reordenarlas acá rompería la lectura: la Übersicht se lee de izquierda a
    derecha como pasa el tiempo."""
    panel.set_windows(vecinas(actual=10))
    izquierda = [caja.left() for _, caja in panel.rectangles()]

    assert izquierda == sorted(izquierda)


# -- Dónde va cada una -------------------------------------------------------


def test_los_rectangulos_no_se_pisan(panel: OverviewPanel):
    cajas = [caja for _, caja in panel.rectangles()]
    panel.set_windows(vecinas(actual=10))
    cajas = [caja for _, caja in panel.rectangles()]

    for anterior, siguiente in zip(cajas, cajas[1:]):
        assert anterior.right() <= siguiente.left()


def test_todas_miden_lo_mismo(panel: OverviewPanel):
    """Una más ancha que otra se leería como si durara más, y todas duran 30 s."""
    panel.set_windows(vecinas(actual=10))
    anchos = [caja.width() for _, caja in panel.rectangles()]

    assert max(anchos) == pytest.approx(min(anchos))


def test_ocupan_el_ancho_disponible(panel: OverviewPanel):
    panel.set_windows(vecinas(actual=10))
    cajas = [caja for _, caja in panel.rectangles()]

    assert cajas[0].left() == pytest.approx(0.0)
    assert cajas[-1].right() == pytest.approx(ANCHO, abs=1.0)


def test_mas_ventanas_las_hace_mas_angostas(panel: OverviewPanel):
    panel.set_windows(vecinas(actual=10, antes=1, despues=1))
    pocas = panel.rectangles()[0][1].width()
    panel.set_windows(vecinas(actual=10, antes=5, despues=5))
    muchas = panel.rectangles()[0][1].width()

    assert muchas < pocas


def test_una_sola_ventana_ocupa_todo(panel: OverviewPanel):
    """El caso de `set_span(0, 0)`, que el pliego permite: no mostrar vecinas."""
    panel.set_windows((OverviewWindow(index=7, is_current=True),))
    cajas = panel.rectangles()

    assert len(cajas) == 1
    assert cajas[0][1].width() == pytest.approx(ANCHO)


def test_mas_ventanas_que_pixeles_no_rompe(panel: OverviewPanel):
    """**El caso que hace negativo el ancho.**

    `set_span()` no tiene techo, y con doscientas ventanas la separación entre
    rectángulos se come el panel entero: `(ancho - 4 * 199) / 200` da negativo
    mucho antes de que Qt se queje. Sin la guarda, salían rectángulos de ancho
    negativo apilados sobre el borde izquierdo.
    """
    panel.set_windows(vecinas(actual=500, antes=100, despues=100))

    assert panel.rectangles() == []


# -- El tamaño lo elige el usuario (V2_F) ------------------------------------


def test_el_alto_se_puede_cambiar(panel: OverviewPanel):
    """V2_F. `OverviewTool.set_size()` existía desde el hito 7 y **no lo
    llamaba nadie**."""
    panel.set_panel_size(600, 150)

    assert panel.height() == 150


def test_el_ancho_pedido_es_un_minimo(panel: OverviewPanel):
    """Se fija como mínimo y no como ancho exacto, para que el panel siga
    acompañando a la ventana si el usuario la agranda."""
    panel.set_panel_size(600, 150)

    assert panel.minimumWidth() == 600


def test_cambiar_el_tamano_no_borra_lo_que_muestra(panel: OverviewPanel):
    panel.set_windows(vecinas(actual=10))
    panel.set_panel_size(600, 150)

    assert len(panel.rectangles()) == 5


# -- Los eventos que caen adentro (V3_F) -------------------------------------


def test_las_clases_de_evento_llegan_al_panel(panel: OverviewPanel):
    """V3_F: es lo que permite ver que hay un huso justo antes o justo después
    sin navegar hasta ahí."""
    panel.set_windows(
        (
            OverviewWindow(index=9, is_current=False, annotation_labels=("Spindle",)),
            OverviewWindow(index=10, is_current=True),
        )
    )
    con_eventos = [v for v, _ in panel.rectangles() if v.annotation_labels]

    assert [v.index for v in con_eventos] == [9]


def test_los_colores_de_las_clases_se_pueden_fijar(panel: OverviewPanel):
    """Los manda la ventana principal desde `AnnotationSet`: la herramienta
    publica los nombres de las clases, no cómo se ven."""
    panel.set_windows(vecinas(actual=10), {"Spindle": "#4a90e6"})

    assert panel._colors == {"Spindle": "#4a90e6"}


def test_volver_a_dibujar_sin_colores_conserva_los_anteriores(panel: OverviewPanel):
    """Navegar redibuja el panel y no vuelve a mandar la paleta."""
    panel.set_windows(vecinas(actual=10), {"Spindle": "#4a90e6"})
    panel.set_windows(vecinas(actual=11))

    assert panel._colors == {"Spindle": "#4a90e6"}
