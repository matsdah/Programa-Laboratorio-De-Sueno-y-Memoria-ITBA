"""Tests de la lupa: zoom circular y contador de picos.

El pliego pide dos cosas distintas bajo la misma herramienta (V1_F y V2_F): un
círculo que amplía la señal debajo del mouse, y un contador de clics para ir
marcando picos.

**El contador se puede testear sin dibujar nada**, que es el motivo por el que
la herramienta no hereda de `QObject`: se le mandan clics y se afirma sobre el
número.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.base import CircleOverlay
from psglab.tools.magnifier import RADIO_INICIAL_SEGUNDOS, ZOOM_INICIAL, MagnifierTool
from psglab.utils.errors import InvalidScaleError


@pytest.fixture
def sesion() -> Session:
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, 3000)),
        sampling_rate=100.0,
    )
    return Session(registro, Scoring(1, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def lupa(sesion: Session) -> MagnifierTool:
    tool = MagnifierTool()
    tool.activate(sesion)
    return tool


# -- El círculo (V1_F) -------------------------------------------------------


def test_no_dibuja_nada_antes_de_que_entre_el_mouse(lupa: MagnifierTool):
    """Un círculo en una posición inventada aparecería al activar la
    herramienta, lejos de donde el usuario está mirando."""
    assert list(lupa.overlays()) == []


def test_la_lupa_sigue_al_mouse(lupa: MagnifierTool):
    lupa.on_mouse_move(12.0, 30.0)
    (circulo,) = lupa.overlays()
    assert isinstance(circulo, CircleOverlay)
    assert circulo.x_seconds == 12.0
    assert circulo.y_uv == 30.0


def test_el_radio_va_en_segundos_y_no_en_pixeles(lupa: MagnifierTool):
    """`tools/base.py` declara que una herramienta nunca recibe píxeles: no
    tiene forma de conocerlos. El visualizador sabe cuántos son."""
    lupa.on_mouse_move(1.0, 0.0)
    (circulo,) = lupa.overlays()
    assert circulo.radius_seconds == RADIO_INICIAL_SEGUNDOS
    assert circulo.zoom == ZOOM_INICIAL


def test_el_radio_y_el_aumento_se_pueden_cambiar(lupa: MagnifierTool):
    lupa.on_mouse_move(1.0, 0.0)
    lupa.set_radius_seconds(2.5)
    lupa.set_zoom(8.0)
    (circulo,) = lupa.overlays()
    assert circulo.radius_seconds == 2.5
    assert circulo.zoom == 8.0


@pytest.mark.parametrize("valor", [0, -1.0, float("nan"), float("inf"), "texto", None])
def test_un_radio_con_el_que_no_se_puede_dibujar_se_rechaza(
    lupa: MagnifierTool, valor
):
    """Un círculo de radio cero no se ve, y el usuario lo buscaría sin
    encontrarlo."""
    with pytest.raises(InvalidScaleError):
        lupa.set_radius_seconds(valor)


@pytest.mark.parametrize("valor", [0, -2.0, float("nan"), "texto"])
def test_un_aumento_invalido_se_rechaza(lupa: MagnifierTool, valor):
    """Un factor de 0 colapsaría la señal y uno negativo la daría vuelta."""
    with pytest.raises(InvalidScaleError):
        lupa.set_zoom(valor)


def test_un_aumento_de_uno_es_valido(lupa: MagnifierTool):
    """Significa "sin ampliar", que es un pedido legítimo."""
    lupa.set_zoom(1.0)
    lupa.on_mouse_move(1.0, 0.0)
    assert lupa.overlays()[0].zoom == 1.0


# -- El contador de picos (V2_F) ---------------------------------------------


def test_cada_clic_izquierdo_suma_un_pico(lupa: MagnifierTool):
    for _ in range(3):
        lupa.on_mouse_press(1.0, 0.0, "left")
    assert lupa.click_count == 3


def test_el_boton_derecho_descuenta(lupa: MagnifierTool):
    """Para corregir un clic de más sin tener que reiniciar la cuenta."""
    for _ in range(3):
        lupa.on_mouse_press(1.0, 0.0, "left")
    lupa.on_mouse_press(1.0, 0.0, "right")
    assert lupa.click_count == 2


def test_el_contador_no_baja_de_cero(lupa: MagnifierTool):
    """Una cuenta de picos negativa no significa nada, y quien descuenta de más
    espera quedar en cero."""
    lupa.on_mouse_press(1.0, 0.0, "right")
    lupa.on_mouse_press(1.0, 0.0, "right")
    assert lupa.click_count == 0


def test_el_boton_del_medio_no_cuenta(lupa: MagnifierTool):
    """Sólo se cuentan los dos gestos que el pliego define."""
    lupa.on_mouse_press(1.0, 0.0, "middle")
    assert lupa.click_count == 0


def test_el_contador_se_puede_reiniciar(lupa: MagnifierTool):
    lupa.on_mouse_press(1.0, 0.0, "left")
    lupa.reset_count()
    assert lupa.click_count == 0


def test_desactivarla_conserva_la_cuenta(lupa: MagnifierTool):
    """El usuario cuenta picos, apaga la lupa para ver la señal sin el círculo
    encima, y vuelve. Reiniciar al desactivar le perdería el trabajo."""
    lupa.on_mouse_press(1.0, 0.0, "left")
    lupa.deactivate()
    assert lupa.click_count == 1


def test_desactivarla_deja_de_dibujar(lupa: MagnifierTool):
    lupa.on_mouse_move(1.0, 0.0)
    lupa.deactivate()
    assert list(lupa.overlays()) == []


def test_el_mouse_sobre_la_herramienta_desactivada_no_cuenta():
    """La ventana principal puede mandarle eventos igual."""
    tool = MagnifierTool()
    tool.on_mouse_press(1.0, 0.0, "left")
    assert tool.click_count == 0


def test_es_exclusiva_porque_se_queda_con_el_clic():
    """Cuenta picos con el botón izquierdo, así que no puede convivir con el
    anotador ni con el medidor de ocupación."""
    assert MagnifierTool.exclusive is True


def test_avisa_cuando_cambia_lo_que_hay_que_mostrar(sesion: Session):
    tool = MagnifierTool()
    avisos: list = []
    tool.on_changed = avisos.append

    tool.activate(sesion)
    tool.on_mouse_move(1.0, 0.0)
    tool.on_mouse_press(1.0, 0.0, "left")
    tool.reset_count()

    assert len(avisos) == 4
    assert all(aviso is tool for aviso in avisos)
