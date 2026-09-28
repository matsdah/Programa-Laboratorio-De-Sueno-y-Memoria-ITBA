"""La ventana de prueba de la comprobación de entrega y lo que comparten sus archivos.

**No es un test**: pytest no lo recolecta, porque no empieza con `test_`. Lo
importan los seis `test_entrega*.py`, que eran uno solo hasta el hito 79.
Acá está la fixture `ventana` —la principal con un registro abierto, armada
por `create_main_window()` como la arma `main.py`— y lo que usa más de uno:
los gestos de mouse, las fixtures con otros registros y los espías de los
carteles.

Una fixture que usa un solo archivo se queda en ése. Al partirlo, lo que
decidió qué venía acá fue quién lo usaba, no qué parecía general.
"""

from pathlib import Path

import pyqtgraph as pg
import pytest

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.core.annotations import Annotation  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402

from conftest import escribir_brainvision  # noqa: E402

#: Ventanas del registro de prueba. Cinco alcanzan para scorear una fase
#: distinta en cada una y que sobre alguna sin scorear.
VENTANAS = 5


@pytest.fixture
def ventana(qt_app, tmp_path, monkeypatch):
    """La ventana principal con un registro abierto, como la ve el usuario.

    Los carteles de error se reemplazan por una lista: son modales, y sin nadie
    que los cierre colgarían la suite. Que la lista quede vacía es una
    afirmación más de cada test.
    """
    carteles: list[str] = []
    # Qué no se pudo hacer, en el mismo orden: es la primera línea del cartel.
    acciones: list[str | None] = []

    def anotar_el_cartel(_ventana, error, accion=None):
        carteles.append(str(error))
        acciones.append(accion)

    monkeypatch.setattr(MainWindow, "_show_error", anotar_el_cartel)

    # **Por `create_main_window()`, que es por donde entra `main.py`.** Armar
    # la `MainWindow` a mano saltea la carga de los dos registros, y entonces
    # el menú Herramientas y el filtro del diálogo de apertura se arman
    # vacíos: el test pasaría verificando un programa que el usuario no tiene.
    principal = create_main_window()
    vhdr = escribir_brainvision(tmp_path / "registro", segundos=WINDOW_SECONDS * VENTANAS)
    principal.open_recording(vhdr)

    assert not carteles, f"abrir el registro mostró un error: {carteles}"
    principal.carteles = carteles
    principal.acciones = acciones
    return principal


@pytest.fixture
def dialogo_de_guardado(monkeypatch):
    """Responde el diálogo de guardado con la ruta que se fije, y anota con
    qué nombre propuesto y qué filtro se abrió.

    **`respuestas` contesta distinto cada vez**, en orden: el cartel del
    trabajo sin exportar abre un diálogo por cada cosa en juego, y con una sola
    ruta el segundo archivo pisaría al primero.
    """
    estado: dict[str, object] = {"respuesta": "", "respuestas": [], "llamadas": []}

    def responder(_padre, _titulo, propuesto, filtro, *_a, **_k) -> tuple[str, str]:
        estado["llamadas"].append((propuesto, filtro))
        pendientes = estado["respuestas"]
        if pendientes:
            return str(pendientes.pop(0)), ""
        return str(estado["respuesta"]), ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(responder))
    return estado


def evento_de_mouse(
    ventana: MainWindow,
    tipo: QEvent.Type,
    x: float,
    boton: Qt.MouseButton = Qt.MouseButton.LeftButton,
    vista: pg.PlotWidget | None = None,
    canal: str | None = None,
    uv: float = 0.0,
    modificadores: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> QMouseEvent:
    """Un evento de mouse sobre un gráfico, en `x` de su escena.

    El gráfico es el visualizador si no se pide otro: el hipnograma usa el
    mismo camino.

    **Con `canal`, el punto cae en ese carril**, a `uv` microvoltios de su eje;
    sin él, en el medio del gráfico, que es lo que hacía siempre. Hizo falta en
    el hito 45: todos los eventos de mouse de la suite apuntaban al centro, así
    que ningún test podía distinguir un carril de otro, y la `y` que recibían
    las herramientas se medía siempre contra el primer canal sin que nada
    fallara.

    El `uv` no puede pasarse de media escala: más arriba empieza el carril de
    al lado, y `channel_at_pixel()` contesta ese otro canal.

    **Se arma como lo arma Qt**: posición relativa al viewport,
    `scenePosition()` relativa a la ventana de primer nivel y la global de la
    pantalla. Hasta que se corrigió el corrimiento del anotador las tres eran
    el mismo punto, y el test no podía distinguir la posición del viewport de
    la de la ventana, que era justamente el error.
    """
    vista = vista or ventana.signal_view
    caja = vista.getPlotItem().vb.sceneBoundingRect()
    viewport = vista.viewport()
    if canal is None:
        y = caja.center().y()
    else:
        centro = vista.lane_center(canal) + vista.to_lanes(uv, canal)
        y = vista.getPlotItem().vb.mapViewToScene(QPointF(0.0, centro)).y()
    local = QPointF(vista.mapFromScene(QPointF(float(x), y)))
    en_ventana = QPointF(viewport.mapTo(viewport.window(), local.toPoint()))
    return QMouseEvent(
        tipo,
        local,
        en_ventana,
        QPointF(viewport.mapToGlobal(local.toPoint())),
        boton,
        boton,
        modificadores,
    )


def arrastrar(
    ventana: MainWindow,
    desde_x: float,
    hasta_x: float,
    canal: str | None = None,
    uv: float = 0.0,
    mayusculas: bool = False,
) -> None:
    """Presiona, mueve y suelta el botón izquierdo sobre el visualizador.

    Con `mayusculas`, suelta con Mayúsculas apretada (hito 79).
    """
    viewport = ventana.signal_view.viewport()
    aplicacion = QApplication.instance()
    al_soltar = (
        Qt.KeyboardModifier.ShiftModifier if mayusculas else Qt.KeyboardModifier.NoModifier
    )
    for tipo, x, modificadores in (
        (QEvent.Type.MouseButtonPress, desde_x, Qt.KeyboardModifier.NoModifier),
        (QEvent.Type.MouseMove, hasta_x, Qt.KeyboardModifier.NoModifier),
        (QEvent.Type.MouseButtonRelease, hasta_x, al_soltar),
    ):
        aplicacion.sendEvent(
            viewport,
            evento_de_mouse(ventana, tipo, x, canal=canal, uv=uv, modificadores=modificadores),
        )


def clic_derecho(ventana: MainWindow, segundos: float) -> None:
    """Un clic derecho sobre el visualizador, en un segundo del registro."""
    vista = ventana.signal_view.getPlotItem().vb
    x = vista.mapViewToScene(QPointF(segundos, 0.0)).x()
    viewport = ventana.signal_view.viewport()
    aplicacion = QApplication.instance()
    for tipo in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        aplicacion.sendEvent(
            viewport, evento_de_mouse(ventana, tipo, x, Qt.MouseButton.RightButton)
        )


@pytest.fixture
def elige_en_el_menu(monkeypatch):
    """Contesta el menú del clic derecho sin abrirlo (hito 52).

    Es modal, igual que el diálogo de clase: sin esto la suite se cuelga, que
    es lo que pasó la primera vez que se corrió con el menú. Devuelve la lista
    de menús que se abrieron, y se le fija qué elegir con `elegir`.
    """
    abiertos: list[list[str]] = []
    respuesta: dict[str, str | None] = {"opcion": None}

    def elegir(_self, opciones, _donde):
        abiertos.append(list(opciones))
        return respuesta["opcion"]

    monkeypatch.setattr(MainWindow, "_elegir_en_un_menu", elegir)

    class Menu:
        menus = abiertos

        @staticmethod
        def elegir(opcion: str | None) -> None:
            respuesta["opcion"] = opcion

    return Menu


@pytest.fixture
def elige_clase(monkeypatch):
    """Responde el diálogo de clase sin abrirlo.

    Es modal: sin esto la suite se cuelga esperando a alguien que apriete
    Aceptar. Devuelve una función para fijar qué contesta.
    """
    respuesta: dict[str, tuple[str, bool]] = {"valor": ("Spindle", True)}

    def responder(*_args, **_kwargs) -> tuple[str, bool]:
        return respuesta["valor"]

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(responder))

    def fijar(clase: str, acepta: bool = True) -> None:
        respuesta["valor"] = (clase, acepta)

    return fijar


def bandas_dibujadas(ventana: MainWindow) -> list[tuple[float, float]]:
    """Los tramos de las bandas que el visualizador tiene en pantalla.

    Son una sola pieza para todas desde que pintarlas por separado era casi
    todo el cuadro; ver `AnnotationBands` en `psglab/ui/overlay_items.py`.
    """
    bandas = ventana.signal_view.overlay_layer.annotation_bands
    if bandas is None:
        return []
    return [(round(inicio, 3), round(fin, 3)) for inicio, fin, _ in bandas.bands]


def anotar_en(
    ventana: MainWindow, desde: float, hasta: float, clase: str = "Arousal"
) -> Annotation:
    """Agrega una anotación directo a la sesión, sin pasar por el gesto."""
    fs = ventana.session.recording.sampling_rate
    anotacion = Annotation(
        label=clase,
        onset_sample=int(desde * fs),
        duration_samples=int((hasta - desde) * fs),
    )
    ventana.session.annotations.add(anotacion)
    return anotacion


@pytest.fixture
def confirmacion(monkeypatch):
    """Contesta `_confirmar()` con la respuesta que se fije y anota cada pregunta.

    Como `cartel_del_scoring`: el cartel es modal, y sin nadie que lo cierre
    colgaría la suite.
    """
    estado: dict[str, object] = {"respuesta": True, "preguntas": []}

    def responder(_ventana, titulo, pregunta, accion, **opciones) -> bool:
        estado["preguntas"].append(
            {"titulo": titulo, "pregunta": pregunta, "accion": accion, **opciones}
        )
        return bool(estado["respuesta"])

    monkeypatch.setattr(MainWindow, "_confirmar", responder)
    return estado


@pytest.fixture
def elige_canal(monkeypatch):
    """Responde los diálogos de canal sin abrirlos, en orden."""
    respuestas: dict[str, list[tuple[str, bool]]] = {"cola": []}

    def responder(*_args, **_kwargs) -> tuple[str, bool]:
        return respuestas["cola"].pop(0) if respuestas["cola"] else ("", False)

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(responder))

    def fijar(*elegidos: str, acepta: bool = True) -> None:
        respuestas["cola"] = [(nombre, acepta) for nombre in elegidos]

    return fijar


@pytest.fixture
def elige_opciones(monkeypatch):
    """Contesta una secuencia de diálogos de `QInputDialog.getItem`.

    Los de complejidad y conectividad preguntan dos cosas seguidas —canal y
    medida, o banda—, así que hace falta ir devolviendo respuestas distintas.
    """
    def responder_con(*respuestas):
        cola = iter(respuestas)
        monkeypatch.setattr(
            QInputDialog, "getItem", staticmethod(lambda *a, **k: next(cola))
        )
    return responder_con


@pytest.fixture
def ventana_con_dos_eeg(qt_app, tmp_path, monkeypatch):
    """Como `ventana`, pero con dos canales EEG.

    La ICA necesita al menos dos: con uno solo el módulo se niega, con razón,
    porque no hay mezcla que separar. El BrainVision por omisión trae un solo
    EEG, y derivar no alcanza: `derive()` marca como `OTHER` un canal hecho de
    dos clases distintas, que es su regla y está bien.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "dos_eeg",
        segundos=WINDOW_SECONDS * 2,
        canales=[("C3", "µV"), ("C4", "µV"), ("EOG-izq", "µV")],
    )
    principal.open_recording(vhdr)
    principal.carteles = carteles
    return principal


@pytest.fixture
def reproduccion(ventana: MainWindow):
    """La ventana, con la reproducción detenida al terminar pase lo que pase:
    un temporizador vivo seguiría moviendo la página en el test siguiente."""
    yield ventana
    ventana.playback_controller.stop()


def otro_registro(tmp_path: Path) -> Path:
    """Otra frecuencia y otros canales: nada del primero le sirve."""
    return escribir_brainvision(
        tmp_path / "otro",
        segundos=WINDOW_SECONDS * 2,
        canales=[("Fz", "µV"), ("Cz", "µV")],
        frecuencia=100.0,
    )


@pytest.fixture
def a_la_vista(ventana: MainWindow):
    """La ventana mostrada y activa: sin eso no hay foco, y sin foco Qt no
    decide entre un atajo y el control. Se oculta y no se cierra al terminar:
    cerrar preguntaría por el scoring sin exportar, que es modal."""
    ventana.resize(1400, 900)
    ventana.show()
    ventana.activateWindow()
    QApplication.processEvents()
    yield ventana
    ventana.hide()


def teclear(*teclas: Qt.Key) -> None:
    """Cada tecla a lo que tenga el foco **en ese momento**: la primera que
    se tipea en una celda abre su editor, y la siguiente ya va ahí."""
    from PySide6.QtTest import QTest

    for tecla in teclas:
        QTest.keyClick(QApplication.focusWidget(), tecla)
        QApplication.processEvents()


def arrastrar_un_tramo(
    ventana: MainWindow, desde: float = 0.25, hasta: float = 0.35, mayusculas: bool = False
) -> None:
    """Un arrastre sobre la página, entre dos fracciones de su ancho."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    arrastrar(
        ventana,
        caja.left() + caja.width() * desde,
        caja.left() + caja.width() * hasta,
        mayusculas=mayusculas,
    )
