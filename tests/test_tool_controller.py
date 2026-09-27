"""Tests del controlador de herramientas, armado **sin la ventana principal**.

Es lo que el hito 79 fue a buscar: hasta ahí esta lógica era un mixin de
`MainWindow` que compartía su estado con los otros seis, y la única forma de
probarla era armar la ventana entera. `ToolController` recibe los cuatro
widgets que usa, y lo que la ventana hace después —preguntar la clase de una
anotación, redibujar el hipnograma, ir a una ventana— le llega por señales. Acá
se miran esas señales y el estado propio: quién tiene el mouse, quién dibuja,
qué dice la barra de estado.

Que la ventana lo use bien —el menú, abrir un registro, anotar con el mouse—
lo sigue verificando `test_entrega.py`.
"""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QLabel, QMenu, QWidget

pg = pytest.importorskip("pyqtgraph")

from psglab.core.annotations import AnnotationSet  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.core.scoring import Scoring  # noqa: E402
from psglab.core.session import Session  # noqa: E402
from psglab.tools.registry import available_tools, load_all_tools  # noqa: E402
from psglab.ui.overview_panel import OverviewPanel  # noqa: E402
from psglab.ui.signal_view import SignalView  # noqa: E402
from psglab.ui.tool_controller import ToolController  # noqa: E402

FRECUENCIA = 100.0
VENTANAS = 3

#: Las que son un panel en la ventana de verdad.
PANELES = frozenset({"overview", "histogram"})


@pytest.fixture
def sesion() -> Session:
    tiempos = np.arange(VENTANAS * 3000) / FRECUENCIA
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("C4", ChannelKind.EEG, "µV", 1),
        ],
        data=np.vstack([50.0 * np.sin(2 * np.pi * 10 * tiempos)] * 2),
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def controlador(qt_app):
    """El controlador con sus cuatro widgets, sin sesión todavía.

    **Todo cuelga de un mismo padre**, como en la ventana: sueltos, el
    recolector de Python borra un widget que el controlador todavía mira.
    """
    load_all_tools()
    raiz = QWidget()
    vista = SignalView()
    vista.setParent(raiz)
    vista.resize(800, 400)
    controlador = ToolController(
        vista,
        pg.PlotWidget(raiz),
        OverviewPanel(raiz),
        QLabel("", raiz),
        PANELES,
        parent=raiz,
    )
    yield controlador
    raiz.deleteLater()


@pytest.fixture
def menu(controlador: ToolController) -> QMenu:
    """Un menú de herramientas, que vive lo mismo que el test."""
    menu = QMenu()
    yield menu
    menu.deleteLater()


@pytest.fixture
def con_sesion(controlador: ToolController, sesion: Session) -> ToolController:
    controlador._signal_view.set_session(sesion)
    controlador.attach(sesion)
    return controlador


def evento(tipo: QEvent.Type, x: float, boton: Qt.MouseButton) -> QMouseEvent:
    """Un evento de mouse en el píxel `x`, a media altura del visualizador."""
    punto = QPointF(x, 100.0)
    botones = boton if tipo != QEvent.Type.MouseButtonRelease else Qt.MouseButton.NoButton
    return QMouseEvent(tipo, punto, punto, boton, botones, Qt.KeyboardModifier.NoModifier)


def mandar(controlador: ToolController, *eventos: QMouseEvent) -> None:
    viewport = controlador._signal_view.viewport()
    for uno in eventos:
        assert controlador.eventFilter(viewport, uno) is False


# -- Lo que arma --------------------------------------------------------------


def test_crea_una_herramienta_por_cada_una_del_registro(controlador: ToolController):
    assert set(controlador.tools) == {cls.name for cls in available_tools()}


def test_las_herramientas_no_se_pueden_cambiar_desde_afuera(controlador: ToolController):
    """Es estado propio: la ventana lo consulta, no lo edita."""
    with pytest.raises(TypeError):
        controlador.tools["otra"] = None  # type: ignore[index]


def test_el_menu_lleva_los_modos_del_mouse_y_no_los_paneles(
    controlador: ToolController, menu: QMenu
):
    """Una herramienta que es un panel ya tiene la entrada de su panel (hito
    28): con dos, un menú la mostraba tildada y el otro no."""
    ya_estaba = menu.addAction("Restaurar la disposición")

    controlador.build_menu(menu)

    modos = [a for a in menu.actions() if a is not ya_estaba]
    assert set(controlador.actions) == set(controlador.tools) - PANELES
    assert modos == list(controlador.actions.values())
    assert menu.actions()[-1] is ya_estaba
    assert all(a.isCheckable() and a.statusTip() for a in modos)


# -- Prender y apagar ---------------------------------------------------------


def test_sin_registro_prender_no_hace_nada(controlador: ToolController):
    controlador.toggle("magnifier", True)

    assert controlador.mouse_tool is None


def test_prender_una_exclusiva_apaga_la_otra_y_la_destilda(
    con_sesion: ToolController, menu: QMenu
):
    con_sesion.build_menu(menu)
    con_sesion.actions["occupancy"].setChecked(True)

    con_sesion.actions["magnifier"].setChecked(True)

    assert con_sesion.mouse_tool is con_sesion.tools["magnifier"]
    assert not con_sesion.actions["occupancy"].isChecked()
    assert con_sesion._session.active_tool == "magnifier"


def test_la_banda_dibuja_sin_quedarse_con_el_mouse(con_sesion: ToolController):
    """Hito 45: dibujar y recibir los clics son dos preguntas."""
    con_sesion.toggle("magnifier", True)
    con_sesion.toggle("amplitude_band", True)

    assert con_sesion.mouse_tool is con_sesion.tools["magnifier"]
    assert con_sesion.drawn_overlays


def test_los_paneles_se_prenden_solos(con_sesion: ToolController):
    con_sesion.activate_panel_tools()

    assert all(con_sesion.tools[nombre]._session is not None for nombre in PANELES)
    assert con_sesion.mouse_tool is None


def test_apagar_todo_suelta_el_mouse_y_la_sesion(con_sesion: ToolController):
    con_sesion.toggle("occupancy", True)

    con_sesion.deactivate_all()

    assert con_sesion.mouse_tool is None
    assert con_sesion._session.active_tool is None
    assert con_sesion.drawn_overlays == ()


# -- La barra de estado -------------------------------------------------------


def test_la_lectura_dice_la_ocupacion_y_los_picos(con_sesion: ToolController):
    con_sesion.toggle("occupancy", True)
    assert con_sesion._readout.text() == "Ocupación: sin líneas"

    con_sesion.toggle("magnifier", True)
    con_sesion.tools["magnifier"].on_mouse_press(1.0, 0.0, "left")
    assert con_sesion._readout.text() == "Picos contados: 1"

    con_sesion.reset_magnifier_count()
    assert con_sesion._readout.text() == "Picos contados: 0"


# -- El mouse -----------------------------------------------------------------


def test_un_clic_en_la_senal_le_llega_a_la_herramienta(con_sesion: ToolController):
    con_sesion.toggle("magnifier", True)

    mandar(con_sesion, evento(QEvent.Type.MouseButtonPress, 300, Qt.MouseButton.LeftButton))

    assert con_sesion.tools["magnifier"].click_count == 1


def test_sin_herramienta_un_clic_no_va_a_ningun_lado(con_sesion: ToolController):
    mandar(con_sesion, evento(QEvent.Type.MouseButtonPress, 300, Qt.MouseButton.LeftButton))

    assert con_sesion.tools["magnifier"].click_count == 0


def test_soltar_el_anotador_avisa_a_la_ventana(con_sesion: ToolController):
    """Preguntar la clase es un cartel, y los carteles son de la ventana."""
    soltados: list[object] = []
    con_sesion.annotation_released.connect(lambda herramienta, _: soltados.append(herramienta))
    con_sesion.toggle("annotator", True)

    mandar(
        con_sesion,
        evento(QEvent.Type.MouseButtonPress, 200, Qt.MouseButton.LeftButton),
        evento(QEvent.Type.MouseMove, 400, Qt.MouseButton.LeftButton),
        evento(QEvent.Type.MouseButtonRelease, 400, Qt.MouseButton.LeftButton),
    )

    assert soltados == [con_sesion.tools["annotator"]]
    assert con_sesion.tools["annotator"].pending_selection_samples is not None


def test_soltar_con_mayusculas_pide_preguntar(con_sesion: ToolController):
    """Hito 79: con una clase activa, Mayúsculas al soltar pide el cartel."""
    from PySide6.QtCore import QPointF as Punto

    soltados: list[bool] = []
    con_sesion.annotation_released.connect(lambda _h, preguntar: soltados.append(preguntar))
    con_sesion.toggle("annotator", True)
    punto = Punto(400.0, 100.0)
    suelta = QMouseEvent(
        QEvent.Type.MouseButtonRelease, punto, punto, Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.ShiftModifier,
    )

    mandar(
        con_sesion,
        evento(QEvent.Type.MouseButtonPress, 200, Qt.MouseButton.LeftButton),
        suelta,
        evento(QEvent.Type.MouseButtonPress, 200, Qt.MouseButton.LeftButton),
        evento(QEvent.Type.MouseButtonRelease, 400, Qt.MouseButton.LeftButton),
    )

    assert soltados == [True, False]


def test_la_lectura_dice_con_que_clase_se_anota(con_sesion: ToolController):
    con_sesion.toggle("annotator", True)
    assert con_sesion._readout.text() == "Anotar: se pregunta la clase de cada evento"

    con_sesion.tools["annotator"].set_active_label("Spindle")

    assert con_sesion._readout.text().startswith("Anotar como «Spindle»")


def test_el_clic_derecho_del_anotador_pide_su_menu(con_sesion: ToolController):
    pedidos: list[tuple] = []
    con_sesion.annotation_menu_requested.connect(lambda *datos: pedidos.append(datos))
    con_sesion.toggle("annotator", True)

    mandar(con_sesion, evento(QEvent.Type.MouseButtonPress, 300, Qt.MouseButton.RightButton))

    ((herramienta, segundos, _donde),) = pedidos
    assert herramienta is con_sesion.tools["annotator"]
    assert 0.0 <= segundos <= VENTANAS * 30.0


def test_el_hipnograma_pide_ir_a_una_ventana_por_senal(controlador: ToolController):
    pedidas: list[int] = []
    controlador.window_requested.connect(pedidas.append)

    controlador.tools["histogram"].on_window_requested(2)

    assert pedidas == [2]
