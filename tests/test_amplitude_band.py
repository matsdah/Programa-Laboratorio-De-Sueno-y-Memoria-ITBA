"""Tests de la banda de amplitud de 75 µV.

El pliego (V1_F de "Herramienta de amplitud") pide una banda de referencia que
**se adapte a la amplitud de la señal elegida por el usuario**. Esa frase es la
que decide el diseño: la banda se publica en microvoltios y no en píxeles, así
que sigue midiendo 75 µV reales aunque el usuario agrande o achique el canal.

**El test que más importa es el del canal.** La auditoría había encontrado que
`BandOverlay` no lo llevaba, y sin él la banda es indibujable: `Session.scale_uv()`
es por canal, así que con dos canales a escalas distintas esos 75 µV no tienen
una única traducción a píxeles.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.config import AMPLITUDE_BAND_UV
from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.amplitude_band import AmplitudeBandTool
from psglab.tools.base import BandOverlay
from psglab.utils.errors import InvalidScaleError, PsgLabError


@pytest.fixture
def sesion() -> Session:
    """Dos canales, para que "sobre cuál va la banda" no sea una pregunta trivial."""
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("C4", ChannelKind.EEG, "µV", 1),
        ],
        data=np.zeros((2, 3000)),
        sampling_rate=100.0,
    )
    return Session(registro, Scoring(1, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def herramienta(sesion: Session) -> AmplitudeBandTool:
    band = AmplitudeBandTool()
    band.activate(sesion)
    return band


# -- El canal, que es lo que la hace dibujable -------------------------------


def test_la_banda_dice_sobre_que_canal_va(herramienta: AmplitudeBandTool):
    """Sin esto la banda no se puede traducir a píxeles.

    `Session.scale_uv()` es por canal: con dos canales a escalas distintas, una
    altura de 75 µV se dibuja de dos tamaños diferentes, y el visualizador no
    tendría con qué elegir.
    """
    (banda,) = herramienta.overlays()
    assert isinstance(banda, BandOverlay)
    assert banda.channel_name


def test_la_banda_va_sobre_el_canal_elegido_por_el_usuario(
    herramienta: AmplitudeBandTool, sesion: Session
):
    """Es lo que pide el pliego con todas las letras: que se adapte a la
    amplitud de **la señal elegida por el usuario**."""
    sesion.set_selected_channels(["C4"])
    (banda,) = herramienta.overlays()
    assert banda.channel_name == "C4"


def test_sin_ningun_canal_elegido_cae_al_primero_visible(
    herramienta: AmplitudeBandTool,
):
    """La herramienta tiene que servir apenas se abre un registro, antes de que
    el usuario elija nada."""
    (banda,) = herramienta.overlays()
    assert banda.channel_name == "C3"


def test_la_banda_dice_de_que_herramienta_es(herramienta: AmplitudeBandTool):
    """Sirve para borrar lo suyo sin tocar lo de las demás herramientas."""
    (banda,) = herramienta.overlays()
    assert banda.tool_name == AmplitudeBandTool.name


# -- Los 75 µV ---------------------------------------------------------------


def test_la_altura_por_defecto_sale_de_config(herramienta: AmplitudeBandTool):
    """El 75 no se escribe a mano en ningún lado: cambiar el criterio del pliego
    tiene que seguir siendo cambiar una línea."""
    (banda,) = herramienta.overlays()
    assert banda.height_uv == AMPLITUDE_BAND_UV


def test_la_descripcion_que_ve_el_usuario_tambien_sale_de_config():
    """Un literal en el texto de la barra le mentiría al usuario el día que
    alguien cambie la constante."""
    assert f"{AMPLITUDE_BAND_UV:.0f}" in AmplitudeBandTool.description


def test_la_altura_se_puede_cambiar(herramienta: AmplitudeBandTool):
    """Hay criterios que usan otros umbrales según el montaje y la edad."""
    herramienta.set_height_uv(150.0)
    (banda,) = herramienta.overlays()
    assert banda.height_uv == 150.0


@pytest.mark.parametrize("altura", [0, -5.0, float("nan"), float("inf"), "texto", None])
def test_una_altura_con_la_que_no_se_puede_dibujar_se_rechaza(
    herramienta: AmplitudeBandTool, altura
):
    """Una banda de altura cero o negativa no se dibuja, y el usuario la
    buscaría en la pantalla sin encontrarla."""
    with pytest.raises(InvalidScaleError):
        herramienta.set_height_uv(altura)


def test_el_rechazo_lo_atrapa_el_except_de_la_interfaz(
    herramienta: AmplitudeBandTool,
):
    with pytest.raises(PsgLabError):
        herramienta.set_height_uv(0)


# -- El seguimiento del mouse ------------------------------------------------


def test_la_banda_sigue_al_mouse_en_vertical(herramienta: AmplitudeBandTool):
    herramienta.on_mouse_move(x=12.0, y=40.0)
    (banda,) = herramienta.overlays()
    assert banda.y_center_uv == 40.0


def test_la_posicion_horizontal_del_mouse_no_la_mueve(
    herramienta: AmplitudeBandTool,
):
    """La banda cruza la ventana entera: moverse en horizontal no la cambia."""
    herramienta.on_mouse_move(x=1.0, y=40.0)
    herramienta.on_mouse_move(x=29.0, y=40.0)
    (banda,) = herramienta.overlays()
    assert banda.y_center_uv == 40.0


def test_arranca_centrada_en_la_linea_de_base(herramienta: AmplitudeBandTool):
    """Antes de mover el mouse la banda tiene que estar en algún lado visible."""
    (banda,) = herramienta.overlays()
    assert banda.y_center_uv == 0.0


# -- Activación y desactivación ----------------------------------------------


def test_desactivada_no_dibuja_nada():
    """Devuelve la secuencia vacía, no `None`: quien la consume la recorre."""
    assert list(AmplitudeBandTool().overlays()) == []


def test_al_desactivarla_deja_de_dibujar(herramienta: AmplitudeBandTool):
    herramienta.deactivate()
    assert list(herramienta.overlays()) == []


def test_el_mouse_sobre_una_herramienta_desactivada_no_hace_nada():
    """La ventana principal puede mandarle eventos igual; no puede romperse."""
    band = AmplitudeBandTool()
    band.on_mouse_move(1.0, 50.0)
    assert list(band.overlays()) == []


def test_no_es_exclusiva_porque_no_compite_por_el_clic():
    """Sólo se dibuja. Marcarla exclusiva apagaría al anotador cada vez que el
    usuario quiere ver la referencia de amplitud."""
    assert AmplitudeBandTool.exclusive is False


def test_un_registro_sin_canales_visibles_no_rompe(sesion: Session):
    """No puede pasar hoy —`Recording` exige al menos un canal— pero la
    herramienta no tiene por qué saberlo."""
    band = AmplitudeBandTool()
    band.activate(sesion)
    sesion.set_visible_channels([])
    assert list(band.overlays()) == []


# -- El aviso a la ventana principal -----------------------------------------


def test_avisa_cada_vez_que_cambia_lo_que_hay_que_dibujar(sesion: Session):
    """La ventana principal engancha su repintado acá.

    Sin el aviso, la banda se movería en los datos y no en la pantalla.
    """
    band = AmplitudeBandTool()
    avisos: list = []
    band.on_changed = avisos.append

    band.activate(sesion)
    band.on_mouse_move(1.0, 10.0)
    band.set_height_uv(100.0)
    band.deactivate()

    assert len(avisos) == 4
    assert all(aviso is band for aviso in avisos)
