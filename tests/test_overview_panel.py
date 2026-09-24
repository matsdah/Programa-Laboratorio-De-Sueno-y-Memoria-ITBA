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

import numpy as np
import pytest

pytest.importorskip("pyqtgraph")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from psglab.tools.overview import OverviewTrace, OverviewWindow  # noqa: E402
from psglab.ui.overview_panel import ANCHO_MINIMO, OverviewPanel  # noqa: E402

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


def test_el_ancho_pedido_es_el_preferido(panel: OverviewPanel):
    """No es un ancho exacto, para que el panel siga acompañando a la ventana
    si el usuario la agranda.

    **Tampoco es un mínimo**, desde el hito 24: como mínimo no le dejaba lugar
    al hipnograma cuando se abrían los tres paneles de abajo."""
    panel.set_panel_size(600, 150)

    assert panel.sizeHint().width() == 600
    assert panel.minimumWidth() == ANCHO_MINIMO


def test_un_ancho_pedido_menor_que_el_minimo_tambien_vale(panel: OverviewPanel):
    """El mínimo no puede agrandar lo que el usuario pidió chico."""
    panel.set_panel_size(80, 90)

    assert panel.minimumWidth() == 80
    assert panel.sizeHint().width() == 80


def test_con_el_ancho_minimo_se_siguen_viendo_las_tres_ventanas(panel: OverviewPanel):
    """37 px por ventana alcanzan para el número."""
    panel.set_windows(vecinas(actual=10)[1:4])
    panel.resize(ANCHO_MINIMO, ALTO)

    cajas = panel.rectangles()

    assert len(cajas) == 3
    assert all(caja.width() >= 30 for _, caja in cajas)


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


# -- El clic y la señal (hito 51) -------------------------------------------


def _clics(panel: OverviewPanel) -> list[int]:
    recibidos: list[int] = []
    panel.window_clicked.connect(recibidos.append)
    return recibidos


def test_un_clic_en_una_caja_pide_ir_a_esa_ventana(panel: OverviewPanel):
    """**Hasta el hito 51 el panel no respondía al mouse.** El prototipo lo
    pedía: «un clic lleva la señal a esa época»."""
    panel.set_windows(vecinas(actual=10, antes=1, despues=1))
    recibidos = _clics(panel)
    (_, caja), = [(v, c) for v, c in panel.rectangles() if v.index == 11]

    QTest.mouseClick(panel, Qt.MouseButton.LeftButton, pos=caja.center().toPoint())

    assert recibidos == [11]


def test_un_clic_entre_dos_cajas_no_pide_nada(panel: OverviewPanel):
    panel.set_windows(vecinas(actual=10, antes=1, despues=1))
    recibidos = _clics(panel)
    (_, primera), (_, segunda), _ = panel.rectangles()
    entre = QPointF((primera.right() + segunda.left()) / 2, primera.center().y())

    QTest.mouseClick(panel, Qt.MouseButton.LeftButton, pos=entre.toPoint())

    assert recibidos == []


def test_el_clic_derecho_no_navega(panel: OverviewPanel):
    panel.set_windows(vecinas(actual=10, antes=1, despues=1))
    recibidos = _clics(panel)
    _, caja = panel.rectangles()[0]

    QTest.mouseClick(panel, Qt.MouseButton.RightButton, pos=caja.center().toPoint())

    assert recibidos == []


def test_cada_caja_es_un_encabezado_y_debajo_la_senal(panel: OverviewPanel):
    """El encabezado lleva el número, la fase y los eventos; la señal se queda
    con el resto, sin pisarlo."""
    panel.set_windows(vecinas(actual=10))

    for _, caja in panel.rectangles():
        cabecera, senal = panel._partes(caja)
        assert cabecera.top() == caja.top()
        assert senal.top() == cabecera.bottom()
        assert senal.bottom() == pytest.approx(caja.bottom())
        assert 0 < cabecera.height() < senal.height()


def _con_senal(actual: int, valores: np.ndarray) -> tuple[OverviewWindow, ...]:
    trazo = OverviewTrace(
        channel_name="C3",
        positions=np.linspace(0.0, 0.99, len(valores)),
        microvolts=valores,
        scale_uv=50.0,
        offset_uv=0.0,
    )
    return (OverviewWindow(index=actual, is_current=True, trace=trazo),)


def _pixeles_rojos(panel: OverviewPanel) -> int:
    imagen = panel.grab().toImage()
    _, senal = panel._partes(panel.rectangles()[0][1])
    rojos = 0
    for x in range(int(senal.left()) + 2, int(senal.right()) - 2, 2):
        for y in range(int(senal.top()) + 2, int(senal.bottom()) - 2):
            color = imagen.pixelColor(x, y)
            if color.red() > 200 and color.green() < 90 and color.blue() < 90:
                rojos += 1
    return rojos


def test_la_senal_se_dibuja_con_el_color_de_su_canal(panel: OverviewPanel):
    """**Es lo único del dibujo que se afirma**, porque es lo que el hito
    agregó: que la señal llegue a la pantalla y con el color que le pasa la
    ventana, que es el de su carril en el visualizador."""
    panel.set_windows(_con_senal(3, 40.0 * np.sin(np.linspace(0, 30, 800))), {}, "#ff0000")

    assert _pixeles_rojos(panel) > 20


def test_sin_senal_no_se_dibuja_ninguna(panel: OverviewPanel):
    """El contraste que vuelve significativo al test de arriba."""
    panel.set_windows((OverviewWindow(index=3, is_current=True),), {}, "#ff0000")

    assert _pixeles_rojos(panel) == 0


# -- Accesibilidad (hito 63) --------------------------------------------------


def test_se_alcanza_con_el_teclado(panel: OverviewPanel):
    assert panel.focusPolicy() & Qt.FocusPolicy.TabFocus
    assert panel.accessibleName() == "Übersicht"


def test_un_lector_de_pantalla_lee_lo_que_dicen_las_cajas(panel: OverviewPanel):
    """**El panel es sólo dibujo**: la descripción dice lo mismo que las
    cabeceras, con número base 1 y la actual marcada."""
    from psglab.core.nomenclature import SleepStage

    panel.set_windows(
        (
            OverviewWindow(index=0, is_current=False, stage=SleepStage.N1),
            OverviewWindow(index=1, is_current=True, annotation_labels=("Apnea",)),
        )
    )

    assert panel.accessibleDescription() == (
        "Ventana 1: N1; ventana 2 (actual): sin scorear, Apnea"
    )


def test_con_el_foco_dibuja_el_anillo(panel: OverviewPanel):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

    from psglab.ui import theme

    ventana = QWidget()
    capa = QVBoxLayout(ventana)
    otro = QLineEdit()
    capa.addWidget(otro)
    capa.addWidget(panel)
    panel.set_windows(vecinas(3))
    ventana.show()
    ventana.activateWindow()
    acento = QColor(theme.current().accent).name()

    def esquina() -> str:
        return panel.grab().toImage().pixelColor(0, panel.height() // 2).name()

    otro.setFocus()
    QApplication.processEvents()
    assert esquina() != acento

    panel.setFocus()
    QApplication.processEvents()
    assert esquina() == acento
