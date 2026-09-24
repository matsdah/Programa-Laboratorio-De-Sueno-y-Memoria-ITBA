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
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.overview import TRACE_BUCKETS, OverviewTool
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


def test_cada_ventana_del_contexto_trae_su_fase(panel: OverviewTool, sesion: Session):
    """**El panel mostraba tres ventanas y ninguna decía en qué fase estaba.**
    La Übersicht existe para ver el contexto de la que se scorea, y la fase es
    la mitad de ese contexto. Es dato y no dibujo: la herramienta dice cuál es
    y la interfaz decide con qué color pintarla."""
    sesion.scoring.set_stage(1, SleepStage.N2)
    sesion.go_to_window(1)
    panel.on_window_changed(1)

    actual = [v for v in panel.windows() if v.is_current][0]

    assert actual.stage is SleepStage.N2


def test_una_ventana_sin_scorear_lo_dice(panel: OverviewTool):
    """`UNSCORED` y no `None`: es el mismo vocabulario que el resto del
    programa, y lo que le permite a la interfaz no dibujar ningún chip."""
    assert all(v.stage is SleepStage.UNSCORED for v in panel.windows())


# -- La señal de cada ventana (hito 51) --------------------------------------

#: Dónde cae la espiga del canal EOG: en la ventana 3, a 12 s de su comienzo.
ESPIGA = 3 * 3000 + 1200


def _sesion_con_senal(frecuencia: float = 100.0) -> Session:
    """Cinco ventanas de dos canales: ruido chico en C3, y en EOG una espiga
    de 300 µV en la ventana 3."""
    muestras = int(5 * 30 * frecuencia)
    datos = np.random.default_rng(51).normal(scale=5.0, size=(2, muestras))
    donde = int(ESPIGA * frecuencia / 100.0)
    datos[1, donde] = 300.0
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0),
            Channel("EOG", ChannelKind.EOG, "µV", 1),
        ],
        data=datos,
        sampling_rate=frecuencia,
    )
    return Session(registro, Scoring(5, Nomenclature.AASM), AnnotationSet())


def _contexto(sesion: Session, actual: int = 2) -> OverviewTool:
    sesion.go_to_window(actual)
    tool = OverviewTool()
    tool.activate(sesion)
    return tool


def test_cada_ventana_trae_su_senal():
    """**Hasta el hito 51 la Übersicht no mostraba señal**: número, fase y
    eventos anotados. Un huso justo antes sólo se veía si alguien ya lo había
    anotado, que es lo que el panel existe para ayudar a encontrar."""
    tool = _contexto(_sesion_con_senal())

    assert [v.index for v in tool.windows()] == [1, 2, 3]
    assert all(v.trace is not None for v in tool.windows())


def test_sin_seleccion_es_el_primer_canal_visible():
    """La misma regla que la banda de amplitud: tiene que mostrar algo apenas
    se abre el registro."""
    tool = _contexto(_sesion_con_senal())

    assert {v.trace.channel_name for v in tool.windows()} == {"C3"}


def test_sigue_al_canal_seleccionado():
    sesion = _sesion_con_senal()
    tool = _contexto(sesion)

    sesion.set_selected_channels(["EOG"])
    tool.refresh()

    assert {v.trace.channel_name for v in tool.windows()} == {"EOG"}


def test_la_espiga_de_la_ventana_siguiente_se_ve_en_su_lugar():
    """**Para esto existe el panel**: lo que pasa en la ventana de al lado,
    sin ir hasta ahí. La espiga sale a su altura y en su posición: 12 s de
    30 son el 40 % de la caja."""
    sesion = _sesion_con_senal()
    sesion.set_selected_channels(["EOG"])
    tool = _contexto(sesion)

    siguiente = [v for v in tool.windows() if v.index == 3][0].trace
    donde = int(np.argmax(siguiente.microvolts))

    assert siguiente.microvolts[donde] == 300.0
    assert siguiente.positions[donde] == pytest.approx(0.4)


def test_una_ventana_densa_se_reduce_sin_perder_la_espiga():
    """A 1000 Hz son 30 000 muestras por ventana. Se reducen con la misma
    envolvente que el visualizador, que no puede perder un pico."""
    sesion = _sesion_con_senal(frecuencia=1000.0)
    sesion.set_selected_channels(["EOG"])
    tool = _contexto(sesion)

    siguiente = [v for v in tool.windows() if v.index == 3][0].trace

    assert len(siguiente.positions) <= 2 * TRACE_BUCKETS + 2
    assert siguiente.microvolts.max() == 300.0


def test_la_escala_es_la_del_canal_en_el_visualizador():
    """**No se ajusta cada caja a su propio máximo**: una ventana tranquila
    tiene que verse tranquila, y ajustada a su máximo el ruido llenaría la caja
    igual que un complejo K."""
    sesion = _sesion_con_senal()
    sesion.set_scale_uv("C3", 37.5)
    tool = _contexto(sesion)

    assert all(v.trace.scale_uv == 37.5 for v in tool.windows())


def test_la_posicion_va_de_cero_a_uno_dentro_de_la_ventana():
    tool = _contexto(_sesion_con_senal())

    for ventana in tool.windows():
        assert ventana.trace.positions.min() >= 0.0
        assert ventana.trace.positions.max() < 1.0


def test_sin_canales_visibles_no_hay_senal():
    """Sin nada que mostrar no se inventa un canal: la caja queda sin señal."""
    sesion = _sesion_con_senal()
    tool = _contexto(sesion)

    sesion.set_visible_channels([])
    tool.refresh()

    assert all(v.trace is None for v in tool.windows())


def test_la_senal_no_cuenta_al_comparar_ventanas():
    """Dos descripciones de la misma ventana son iguales aunque sus arrays sean
    objetos distintos: la comparación con arrays de numpy elevaría."""
    sesion = _sesion_con_senal()
    primera = _contexto(sesion).windows()
    segunda = _contexto(sesion).windows()

    assert primera == segunda
