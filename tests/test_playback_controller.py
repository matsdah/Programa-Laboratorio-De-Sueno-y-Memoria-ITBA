"""Tests del controlador de la reproducción, armado **sin la ventana principal**.

Hasta el hito 79 el cursor era `MainWindow._cabezal` y los pasos los daba un
mixin, así que probar la reproducción era armar la ventana entera. Ahora
`PlaybackController` recibe el visualizador, y lo que es de la ventana
—reflejar la época, avisar el final, mostrar un error— le llega por señales. Acá
se miran esas señales y el cursor; el reloj tiene su propio test en
`test_playback.py`, y que la ventana lo use bien lo sigue verificando
`test_entrega.py`.

Los pasos se dan emitiendo `clock.advanced` a mano, que es lo que hace el reloj
cada 40 ms: así el test no depende del tiempo real.
"""

import math
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QWidget

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.core.annotations import AnnotationSet  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.core.scoring import Scoring  # noqa: E402
from psglab.core.session import Session  # noqa: E402
from psglab.ui.playback_controller import PlaybackController  # noqa: E402
from psglab.ui.signal_view import SignalView  # noqa: E402

FRECUENCIA = 100.0
VENTANAS = 3
MITAD_DE_LA_EPOCA = WINDOW_SECONDS / 2


def _sesion() -> Session:
    muestras = int(VENTANAS * WINDOW_SECONDS * FRECUENCIA)
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, muestras)),
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def controlador(qt_app):
    """El controlador sin sesión, colgado de un padre como en la ventana."""
    raiz = QWidget()
    vista = SignalView()
    vista.setParent(raiz)
    controlador = PlaybackController(vista, parent=raiz)
    yield controlador
    controlador.stop()
    raiz.deleteLater()


@pytest.fixture
def con_sesion(controlador: PlaybackController) -> PlaybackController:
    sesion = _sesion()
    controlador._signal_view.set_session(sesion)
    controlador.attach(sesion)
    return controlador


def avanzar(controlador: PlaybackController, segundos: float) -> None:
    """Un paso del reloj, como los que da cada 40 ms."""
    controlador.clock.advanced.emit(segundos)


# -- Reproducir y pausar ------------------------------------------------------


def test_sin_registro_no_arranca(controlador: PlaybackController):
    controlador.toggle()

    assert not controlador.is_playing
    assert controlador.playhead is None


def test_arranca_desde_el_centro_de_la_epoca_actual(con_sesion: PlaybackController):
    """Es la época que se está scoreando."""
    con_sesion.toggle()

    assert con_sesion.is_playing
    assert con_sesion.playhead == pytest.approx(MITAD_DE_LA_EPOCA)


def test_pausar_saca_el_cursor(con_sesion: PlaybackController):
    con_sesion.toggle()

    con_sesion.toggle()

    assert not con_sesion.is_playing
    assert con_sesion.playhead is None


def test_parar_saca_el_cursor_aunque_no_se_reprodujera(con_sesion: PlaybackController):
    """Un paso pedido a mano —el banco de medición— deja un cursor, y el reloj
    detenido no avisa nada al detenerse otra vez."""
    con_sesion.step(1.0)
    assert con_sesion.playhead is not None

    con_sesion.stop()

    assert con_sesion.playhead is None


def test_tomar_otro_registro_detiene_la_reproduccion(con_sesion: PlaybackController):
    con_sesion.toggle()

    con_sesion.attach(_sesion())

    assert not con_sesion.is_playing
    assert con_sesion.playhead is None


# -- El cursor ----------------------------------------------------------------


def test_cada_paso_del_reloj_avanza_el_cursor(con_sesion: PlaybackController):
    con_sesion.toggle()

    avanzar(con_sesion, 2.5)

    assert con_sesion.playhead == pytest.approx(MITAD_DE_LA_EPOCA + 2.5)


def test_cambiar_de_epoca_se_avisa_una_vez(con_sesion: PlaybackController):
    """La ventana refleja la época fuera del gráfico, y eso pasa una vez cada
    30 s de registro, no en cada paso."""
    cambios: list[bool] = []
    con_sesion.epoch_changed.connect(lambda: cambios.append(True))
    con_sesion.toggle()

    avanzar(con_sesion, 5.0)
    assert cambios == []
    avanzar(con_sesion, WINDOW_SECONDS)

    assert cambios == [True]
    assert con_sesion._session.current_window == 1


def test_al_final_del_registro_se_detiene_y_lo_avisa(con_sesion: PlaybackController):
    finales: list[bool] = []
    con_sesion.reached_end.connect(lambda: finales.append(True))
    con_sesion.toggle()

    avanzar(con_sesion, VENTANAS * WINDOW_SECONDS)

    assert finales == [True]
    assert not con_sesion.is_playing


def test_ir_a_una_epoca_lleva_el_cursor_a_su_centro(con_sesion: PlaybackController):
    con_sesion.toggle()

    assert con_sesion.jump_to_window(2)

    assert con_sesion.playhead == pytest.approx(2 * WINDOW_SECONDS + MITAD_DE_LA_EPOCA)
    assert con_sesion.is_playing


@pytest.mark.parametrize("ventana", [-1, VENTANAS])
def test_una_epoca_que_no_existe_se_ignora(con_sesion: PlaybackController, ventana: int):
    """Detener la reproducción por un índice de más no lo pidió nadie."""
    con_sesion.toggle()

    assert not con_sesion.jump_to_window(ventana)

    assert con_sesion.playhead == pytest.approx(MITAD_DE_LA_EPOCA)
    assert con_sesion.is_playing


# -- Lo que no se pudo ----------------------------------------------------------


def test_un_cursor_imposible_se_avisa_y_detiene(con_sesion: PlaybackController):
    """El cartel es de la ventana; acá sólo se avisa qué no se pudo."""
    fallas: list[str] = []
    con_sesion.failed.connect(lambda _error, que: fallas.append(que))
    con_sesion.toggle()

    avanzar(con_sesion, math.nan)

    assert fallas == ["mover la reproducción"]
    assert not con_sesion.is_playing


def test_una_velocidad_imposible_se_avisa(controlador: PlaybackController):
    fallas: list[str] = []
    controlador.failed.connect(lambda _error, que: fallas.append(que))

    controlador.set_speed(-1.0)

    assert fallas == ["cambiar la velocidad"]
