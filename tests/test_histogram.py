"""Tests del histograma (hipnograma) de la noche completa.

Es la vista que resume una noche entera en una sola imagen y la principal forma
de navegar: un clic lleva a esa ventana (V4_F).

**Su `on_click()` no es el de `ViewerTool`**, y esa es la razón de que el
histograma herede de `Tool` y no de aquélla: acá `x` no son segundos dentro de
una ventana de 30 s, sino una posición dentro de la noche entera. Confundir las
dos unidades no rompe nada de forma visible —los dos son números pequeños— así
que hay tests que fijan los bordes.
"""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.tools.histogram import HistogramTool
from psglab.utils.errors import InvalidScaleError, PsgLabError

VENTANAS = 5


def construir_sesion(con_hora: bool = False) -> Session:
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, VENTANAS * 3000)),
        sampling_rate=100.0,
        start_time=datetime(2026, 9, 7, 23, 0, tzinfo=timezone.utc) if con_hora else None,
    )
    scoring = Scoring(VENTANAS, Nomenclature.AASM)
    scoring.set_stage(0, SleepStage.WAKE)
    scoring.set_stage(1, SleepStage.N2)
    return Session(registro, scoring, AnnotationSet())


@pytest.fixture
def sesion() -> Session:
    return construir_sesion()


@pytest.fixture
def histograma(sesion: Session) -> HistogramTool:
    tool = HistogramTool()
    tool.activate(sesion)
    return tool


# -- El largo de la noche desde el arranque (V1_P) ---------------------------


def test_tiene_el_largo_de_la_noche_entera_desde_el_principio(
    histograma: HistogramTool,
):
    """El pliego lo pide: así el usuario puede scorear una parte alejada del
    registro sin haber pasado por las anteriores."""
    assert len(histograma.bars()) == VENTANAS


def test_lo_no_scoreado_queda_sin_fase(histograma: HistogramTool):
    """El panel lo deja en blanco. `UNSCORED` no es una fase: es la ausencia."""
    assert histograma.bars()[2] is SleepStage.UNSCORED


def test_refleja_las_fases_ya_scoreadas(histograma: HistogramTool):
    assert histograma.bars()[0] is SleepStage.WAKE
    assert histograma.bars()[1] is SleepStage.N2


def test_scorear_una_ventana_actualiza_solo_esa_barra(
    histograma: HistogramTool, sesion: Session
):
    """Redibujar la noche entera en cada tecla haría pesado el trabajo, que es
    justamente lo que el usuario hace cientos de veces seguidas."""
    sesion.scoring.set_stage(4, SleepStage.N3)
    histograma.update_window(4)

    assert histograma.bars()[4] is SleepStage.N3
    assert histograma.bars()[2] is SleepStage.UNSCORED


def test_actualizar_una_ventana_que_no_existe_no_rompe(histograma: HistogramTool):
    """La ventana principal podría pedirlo con un índice viejo tras cerrar un
    registro."""
    histograma.update_window(99)
    assert len(histograma.bars()) == VENTANAS


def test_redibujar_toma_el_scoring_del_momento(
    histograma: HistogramTool, sesion: Session
):
    """Es lo que se usa al importar un scoring entero de un archivo."""
    for indice in range(VENTANAS):
        sesion.scoring.set_stage(indice, SleepStage.N3)
    histograma.redraw()
    assert all(fase is SleepStage.N3 for fase in histograma.bars())


# -- Navegar haciendo clic (V4_F) --------------------------------------------


@pytest.mark.parametrize(
    ("fraccion", "esperada"),
    [(0.0, 0), (0.25, 1), (0.5, 2), (0.99, 4), (1.0, 4)],
)
def test_el_clic_lleva_a_la_ventana_de_esa_posicion(
    histograma: HistogramTool, fraccion: float, esperada: int
):
    """`x_fraction` va de 0 —inicio del registro— a 1 —final—, y no en segundos.

    El caso de 1.0 es el que se rompe solo: `int(1.0 * 5)` da 5, que es una
    ventana que no existe. Se recorta contra el borde.
    """
    saltos: list[int] = []
    histograma.on_window_requested = saltos.append
    histograma.on_click(fraccion)
    assert saltos == [esperada]


def test_un_clic_fuera_de_rango_se_recorta(histograma: HistogramTool):
    """Puede pasar si el panel dibuja un margen alrededor del histograma."""
    saltos: list[int] = []
    histograma.on_window_requested = saltos.append
    histograma.on_click(-0.5)
    histograma.on_click(3.0)
    assert saltos == [0, VENTANAS - 1]


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), "medio", None])
def test_un_clic_que_no_es_un_numero_es_un_error_del_programa(
    histograma: HistogramTool, valor
):
    with pytest.raises(PsgLabError):
        histograma.on_click(valor)


def test_sin_nadie_escuchando_el_clic_no_rompe(histograma: HistogramTool):
    """Es el caso de un test, y el de un histograma todavía sin cablear."""
    assert histograma.on_window_requested is None
    histograma.on_click(0.5)


def test_el_clic_con_el_panel_cerrado_no_hace_nada():
    tool = HistogramTool()
    saltos: list[int] = []
    tool.on_window_requested = saltos.append
    tool.on_click(0.5)
    assert saltos == []


# -- El indicador de posición ------------------------------------------------


def test_marca_la_ventana_que_se_esta_viendo(histograma: HistogramTool):
    histograma.mark_current_window(3)
    assert histograma.current_window == 3


def test_navegar_mueve_el_indicador_solo(histograma: HistogramTool):
    """`Tool.on_window_changed()` no hace nada por defecto; el histograma la
    sobrescribe porque es de las que sí quieren enterarse."""
    histograma.on_window_changed(4)
    assert histograma.current_window == 4


# -- El eje horizontal (V2_F) ------------------------------------------------


def test_por_defecto_el_eje_numera_las_ventanas(histograma: HistogramTool):
    assert histograma.uses_clock_time is False


def test_el_eje_en_hora_real_necesita_que_el_registro_la_informe(
    histograma: HistogramTool,
):
    """**Inventar una hora de comienzo sería peor que negarse**: el investigador
    leería el eje como si fuera real."""
    with pytest.raises(InvalidScaleError):
        histograma.set_time_axis(True)


def test_con_horario_de_inicio_el_eje_en_hora_real_se_puede_pedir():
    sesion = construir_sesion(con_hora=True)
    tool = HistogramTool()
    tool.activate(sesion)
    tool.set_time_axis(True)
    assert tool.uses_clock_time is True


def test_siempre_se_puede_volver_a_numerar_ventanas(histograma: HistogramTool):
    """Aunque el registro no informe la hora: es el modo que siempre funciona."""
    histograma.set_time_axis(False)
    assert histograma.uses_clock_time is False


# -- Ciclo de vida -----------------------------------------------------------


def test_cerrado_no_muestra_nada():
    assert HistogramTool().bars() == ()


def test_al_desactivarlo_deja_de_mostrar(histograma: HistogramTool):
    histograma.deactivate()
    assert histograma.bars() == ()


def test_no_es_exclusivo_porque_es_un_panel_permanente():
    """No es un modo del mouse: convive con el anotador y con la lupa."""
    assert HistogramTool.exclusive is False


def test_avisa_cuando_hay_que_repintarlo(sesion: Session):
    tool = HistogramTool()
    avisos: list = []
    tool.on_changed = avisos.append

    tool.activate(sesion)
    tool.update_window(0)
    tool.mark_current_window(2)
    tool.deactivate()

    assert len(avisos) == 4
    assert all(aviso is tool for aviso in avisos)
