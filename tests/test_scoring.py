"""Tests del scoring: fases, arousals y cambio de nomenclatura."""

import pytest

from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.scoring import Scoring
from psglab.utils.errors import InvalidStageError, WindowOutOfRangeError

pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")


@pytest.fixture
def scoring() -> Scoring:
    """Scoring vacío de 20 ventanas en nomenclatura AASM."""
    return Scoring(n_windows=20, nomenclature=Nomenclature.AASM)


def test_un_scoring_nuevo_arranca_entero_sin_scorear(scoring):
    """Todas las ventanas existen desde el principio, en UNSCORED.

    Es lo que permite que el histograma tenga el tamaño de la noche completa
    desde el arranque y que se pueda scorear una parte alejada del registro.
    """
    assert scoring.n_windows == 20
    assert all(s == SleepStage.UNSCORED for s in scoring.stages())
    assert scoring.scored_windows() == 0


def test_se_puede_scorear_una_ventana_alejada_sin_pasar_por_las_anteriores(scoring):
    scoring.set_stage(15, SleepStage.N2)
    assert scoring.get(15).stage == SleepStage.N2
    assert scoring.get(0).stage == SleepStage.UNSCORED
    assert scoring.scored_windows() == 1


def test_el_arousal_es_independiente_de_la_fase(scoring):
    """Una ventana puede ser N2 y tener arousal a la vez."""
    scoring.set_stage(3, SleepStage.N2)
    scoring.set_arousal(3, True)
    assert scoring.get(3).stage == SleepStage.N2
    assert scoring.get(3).arousal is True


def test_no_se_puede_asignar_una_fase_ajena_a_la_nomenclatura(scoring):
    """S4 no existe en AASM."""
    with pytest.raises(InvalidStageError):
        scoring.set_stage(0, SleepStage.S4)


def test_una_ventana_fuera_de_rango_falla_con_un_error_propio(scoring):
    """Un error del programa, no un IndexError crudo de Python."""
    with pytest.raises(WindowOutOfRangeError):
        scoring.get(20)
    with pytest.raises(WindowOutOfRangeError):
        scoring.get(-1)


def test_cambiar_de_nomenclatura_traduce_lo_ya_scoreado(scoring):
    scoring.set_stage(0, SleepStage.N2)
    scoring.set_stage(1, SleepStage.R)
    scoring.change_nomenclature(Nomenclature.RK)
    assert scoring.get(0).stage == SleepStage.S2
    assert scoring.get(1).stage == SleepStage.REM


def test_cambiar_de_nomenclatura_conserva_los_arousals(scoring):
    """El arousal no depende de la nomenclatura y no se debe perder."""
    scoring.set_stage(4, SleepStage.N2)
    scoring.set_arousal(4, True)
    scoring.change_nomenclature(Nomenclature.RK)
    assert scoring.get(4).arousal is True
