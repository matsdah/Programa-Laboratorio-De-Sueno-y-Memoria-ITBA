"""Tests del panel Übersicht: la ventana actual en su contexto.

Responde a un problema real del scoring: la ventana de 30 segundos es una grilla
arbitraria y los eventos no la respetan. Un huso que arranca en el segundo 29 se
ve cortado, y sin contexto es difícil decidir.

**Es un panel, no una herramienta del visualizador**: no publica `Overlay` ni
recibe eventos de mouse sobre la señal. Describe qué ventanas hay que mostrar y
la interfaz las pinta, que es lo que permite testearlo sin abrir nada.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.config import OVERVIEW_WINDOWS_AFTER, OVERVIEW_WINDOWS_BEFORE
from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.overview import OverviewTool
from psglab.utils.errors import InvalidScaleError


@pytest.fixture
def sesion() -> Session:
    """Cinco ventanas, con un evento en la segunda.

    Cinco alcanzan para tener bordes de los dos lados y una ventana del medio
    con vecinas a ambos lados.
    """
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, 15000)),
        sampling_rate=100.0,
    )
    anotaciones = AnnotationSet()
    anotaciones.add(Annotation("Arousal", onset_sample=3100, duration_samples=200))
    return Session(registro, Scoring(5, Nomenclature.AASM), anotaciones)


@pytest.fixture
def panel(sesion: Session) -> OverviewTool:
    tool = OverviewTool()
    tool.activate(sesion)
    return tool


def indices(tool: OverviewTool) -> list[int]:
    return [ventana.index for ventana in tool.windows()]


# -- El contexto -------------------------------------------------------------


def test_muestra_la_ventana_actual_con_sus_vecinas(panel: OverviewTool, sesion: Session):
    sesion.go_to_window(2)
    panel.on_window_changed(2)
    assert indices(panel) == [1, 2, 3]


def test_la_ventana_actual_esta_marcada(panel: OverviewTool, sesion: Session):
    """Se pinta con un fondo más oscuro (V1_F), así que el panel tiene que saber
    cuál es."""
    sesion.go_to_window(2)
    panel.on_window_changed(2)
    actuales = [v.index for v in panel.windows() if v.is_current]
    assert actuales == [2]


def test_en_la_primera_ventana_no_hay_anterior(panel: OverviewTool):
    """Pedirla daría un índice negativo, que `Scoring` rechazaría."""
    assert indices(panel) == [0, 1]


def test_en_la_ultima_ventana_no_hay_siguiente(panel: OverviewTool, sesion: Session):
    sesion.go_to_window(4)
    panel.on_window_changed(4)
    assert indices(panel) == [3, 4]


def test_el_alcance_por_defecto_sale_de_config(panel: OverviewTool, sesion: Session):
    sesion.go_to_window(2)
    panel.on_window_changed(2)
    assert len(indices(panel)) == OVERVIEW_WINDOWS_BEFORE + OVERVIEW_WINDOWS_AFTER + 1


# -- El alcance configurable y asimétrico (V3_F) -----------------------------


def test_el_alcance_puede_ser_asimetrico(panel: OverviewTool, sesion: Session):
    """El pliego lo pide: dos ventanas antes y una después, por ejemplo."""
    sesion.go_to_window(3)
    panel.on_window_changed(3)
    panel.set_span(before=2, after=1)
    assert indices(panel) == [1, 2, 3, 4]


def test_se_puede_pedir_un_solo_lado(panel: OverviewTool, sesion: Session):
    """Cero es válido y significa "no mostrar ese lado"."""
    sesion.go_to_window(2)
    panel.on_window_changed(2)
    panel.set_span(before=0, after=2)
    assert indices(panel) == [2, 3, 4]


@pytest.mark.parametrize("valor", [-1, 1.5, "dos", None])
def test_un_alcance_que_no_es_una_cantidad_de_ventanas_se_rechaza(
    panel: OverviewTool, valor
):
    with pytest.raises(InvalidScaleError):
        panel.set_span(before=valor, after=1)


# -- Los eventos vecinos -----------------------------------------------------


def test_el_panel_dice_que_eventos_caen_en_cada_ventana(panel: OverviewTool):
    """Es todo el sentido de la herramienta: ver que hay un huso justo antes o
    justo después sin perder la posición."""
    con_evento = [v for v in panel.windows() if v.annotation_labels]
    assert [v.index for v in con_evento] == [1]
    assert con_evento[0].annotation_labels == ("Arousal",)


def test_una_ventana_sin_eventos_lo_dice_con_una_tupla_vacia(panel: OverviewTool):
    """Y no con `None`: quien la consume la recorre sin preguntarse nada."""
    (primera,) = [v for v in panel.windows() if v.index == 0]
    assert primera.annotation_labels == ()


# -- El tamaño del panel (V2_F) ----------------------------------------------


def test_el_tamano_del_panel_se_puede_cambiar(panel: OverviewTool):
    panel.set_size(400, 200)
    assert panel.size_px == (400, 200)


@pytest.mark.parametrize("ancho", [0, -10, 1.5, "grande"])
def test_un_tamano_con_el_que_no_se_ve_nada_se_rechaza(panel: OverviewTool, ancho):
    with pytest.raises(InvalidScaleError):
        panel.set_size(ancho, 200)


# -- Ciclo de vida -----------------------------------------------------------


def test_cerrado_no_muestra_nada():
    assert OverviewTool().windows() == ()


def test_al_desactivarlo_deja_de_mostrar(panel: OverviewTool):
    panel.deactivate()
    assert panel.windows() == ()


def test_navegar_con_el_panel_cerrado_no_rompe():
    """La ventana principal avisa a todas las herramientas, activas o no."""
    tool = OverviewTool()
    tool.on_window_changed(3)
    assert tool.windows() == ()


def test_no_es_exclusivo_porque_tiene_su_propia_zona():
    """Marcarlo exclusivo apagaría al anotador cada vez que el usuario quiere
    ver el contexto."""
    assert OverviewTool.exclusive is False


def test_avisa_cuando_hay_que_repintarlo(sesion: Session):
    """Un panel no publica overlays: avisa con `notify_changed()` y la ventana
    principal lo repinta."""
    tool = OverviewTool()
    avisos: list = []
    tool.on_changed = avisos.append

    tool.activate(sesion)
    tool.on_window_changed(2)
    tool.set_span(before=2, after=2)
    tool.set_size(300, 150)
    tool.deactivate()

    assert len(avisos) == 5
    assert all(aviso is tool for aviso in avisos)
