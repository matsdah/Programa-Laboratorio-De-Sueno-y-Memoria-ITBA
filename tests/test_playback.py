"""Tests del reloj de la reproducción.

**No se espera al temporizador.** Un test que durmiera para ver avanzar la
página tardaría lo que dura la espera y fallaría en una máquina cargada. El
reloj recibe la hora de afuera, así que acá se le pasa una falsa y se llama al
paso a mano: lo que se verifica es la cuenta, que es lo que se rompe en
silencio —una reproducción que va al doble o a la mitad de lo que dice se ve
"andando" igual—.

Que la página avance y la época no, y que se detenga en el final, se verifica
por la ventana en `test_entrega.py`.
"""

import pytest

pytest.importorskip("pyqtgraph")

from psglab.ui.playback import (  # noqa: E402
    DEFAULT_SPEED,
    MAX_STEP_SECONDS,
    PLAYBACK_SPEEDS,
    TICK_MS,
    PlaybackClock,
    speed_text,
)
from psglab.utils.errors import InvalidPlaybackSpeedError, PsgLabError  # noqa: E402


class RelojFalso:
    """Una hora que sólo avanza cuando el test lo dice."""

    def __init__(self) -> None:
        self.ahora = 1000.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def reloj() -> RelojFalso:
    return RelojFalso()


@pytest.fixture
def reproduccion(qt_app, reloj: RelojFalso):
    """El reloj con la hora falsa, y la lista de lo que pidió avanzar."""
    clock = PlaybackClock(clock=reloj)
    clock.pedidos = []
    clock.advanced.connect(clock.pedidos.append)
    yield clock
    clock.stop()


# -- La cuenta -----------------------------------------------------------------


def test_a_tiempo_real_avanza_lo_que_paso(reproduccion, reloj):
    reproduccion.start()
    reloj.ahora += 0.04

    reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(0.04)]


@pytest.mark.parametrize("velocidad", PLAYBACK_SPEEDS)
def test_la_velocidad_multiplica_lo_que_paso(reproduccion, reloj, velocidad):
    reproduccion.speed = velocidad
    reproduccion.start()
    reloj.ahora += 0.5

    reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(0.5 * velocidad)]


def test_cada_paso_mide_desde_el_anterior_y_no_desde_el_arranque(reproduccion, reloj):
    reproduccion.start()
    for _ in range(3):
        reloj.ahora += 0.1
        reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(0.1)] * 3


def test_un_paso_lento_no_frena_la_reproduccion(reproduccion, reloj):
    """Si dibujar tardó 300 ms, el paso es de 300 ms y no de los 40 del
    temporizador: la velocidad sigue siendo la pedida."""
    reproduccion.start()
    reloj.ahora += 0.3

    reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(0.3)]


def test_una_pausa_de_la_maquina_no_hace_saltar_la_vista(reproduccion, reloj):
    reproduccion.speed = 60.0
    reproduccion.start()
    reloj.ahora += 1800.0

    reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(MAX_STEP_SECONDS * 60.0)]


def test_un_reloj_que_retrocede_no_hace_retroceder_la_pagina(reproduccion, reloj):
    reproduccion.start()
    reloj.ahora -= 5.0

    reproduccion._tick()

    assert reproduccion.pedidos == []


def test_detenido_no_avanza(reproduccion, reloj):
    reloj.ahora += 1.0

    reproduccion._tick()

    assert reproduccion.pedidos == []


def test_cambiar_la_velocidad_reproduciendo_vale_desde_el_paso_siguiente(
    reproduccion, reloj
):
    reproduccion.start()
    reloj.ahora += 0.1
    reproduccion._tick()

    reproduccion.speed = 10.0
    reloj.ahora += 0.1
    reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(0.1), pytest.approx(1.0)]


# -- Arrancar y detener --------------------------------------------------------


def test_arranca_detenido_y_a_tiempo_real(reproduccion):
    assert not reproduccion.is_playing
    assert reproduccion.speed == DEFAULT_SPEED == 1.0


def test_arrancar_y_detener_avisa_una_vez_cada_uno(reproduccion):
    estados: list[bool] = []
    reproduccion.playing_changed.connect(estados.append)

    reproduccion.start()
    reproduccion.start()
    reproduccion.stop()
    reproduccion.stop()

    assert estados == [True, False]


def test_alternar_arranca_y_detiene(reproduccion):
    reproduccion.toggle()
    assert reproduccion.is_playing

    reproduccion.toggle()
    assert not reproduccion.is_playing


def test_arrancar_prende_el_temporizador(reproduccion):
    reproduccion.start()

    assert reproduccion._temporizador.isActive()
    assert reproduccion._temporizador.interval() == TICK_MS

    reproduccion.stop()
    assert not reproduccion._temporizador.isActive()


def test_al_volver_a_arrancar_no_cuenta_la_pausa(reproduccion, reloj):
    """Diez minutos en pausa no pueden aparecer en el primer paso."""
    reproduccion.start()
    reproduccion.stop()
    reloj.ahora += 600.0
    reproduccion.start()
    reloj.ahora += 0.04

    reproduccion._tick()

    assert reproduccion.pedidos == [pytest.approx(0.04)]


# -- Las velocidades -------------------------------------------------------------


@pytest.mark.parametrize("velocidad", [0.0, -1.0, 3.0, float("nan"), "1", None, True])
def test_una_velocidad_que_no_se_ofrece_se_rechaza(reproduccion, velocidad):
    """Cero congela sin avisar y una negativa retrocede."""
    with pytest.raises(InvalidPlaybackSpeedError):
        reproduccion.speed = velocidad
    assert reproduccion.speed == DEFAULT_SPEED


def test_el_error_de_velocidad_es_del_programa():
    assert issubclass(InvalidPlaybackSpeedError, PsgLabError)


def test_las_velocidades_van_de_menor_a_mayor_e_incluyen_el_tiempo_real():
    assert list(PLAYBACK_SPEEDS) == sorted(PLAYBACK_SPEEDS)
    assert DEFAULT_SPEED in PLAYBACK_SPEEDS
    assert all(v > 0 for v in PLAYBACK_SPEEDS)


@pytest.mark.parametrize(
    "velocidad, texto", [(0.5, "0,5×"), (1.0, "1×"), (30.0, "30×")]
)
def test_la_velocidad_se_escribe_como_la_lee_el_usuario(velocidad, texto):
    assert speed_text(velocidad) == texto
