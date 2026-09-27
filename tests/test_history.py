"""Tests de deshacer y rehacer: `core/history.py`, sin la ventana.

El historial guarda fotos del trabajo y no operaciones, así que lo que hay que
verificar es que cada forma de cambiar el trabajo vuelva atrás entera: una fase,
un arousal, una anotación nueva, borrada o corrida, la nomenclatura, las
sugeridas confirmadas o descartadas, un scoring importado encima. Y lo que no es
trabajo —moverse de ventana— no tiene que gastar un paso.

Que Ctrl+Z, el menú y la ventana lo usen bien lo verifican `test_menus.py` y
`test_entrega.py`.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.history import History
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring, StageSuggestion
from psglab.core.session import Session

FRECUENCIA = 100.0
VENTANAS = 5
MUESTRAS_POR_VENTANA = int(30 * FRECUENCIA)


@pytest.fixture
def sesion() -> Session:
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, VENTANAS * MUESTRAS_POR_VENTANA)),
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def historial(sesion: Session) -> History:
    return History(sesion)


def fases(sesion: Session) -> list[SleepStage]:
    return [sesion.scoring.get(i).stage for i in range(VENTANAS)]


# -- Lo básico --------------------------------------------------------------------


def test_recien_empezado_no_hay_nada_que_deshacer(historial: History):
    assert not historial.can_undo
    assert not historial.undo()
    assert not historial.redo()


def test_deshacer_una_fase_la_saca_y_dice_donde(sesion: Session, historial: History):
    sesion.scoring.set_stage(2, SleepStage.N2)
    historial.record()

    assert historial.undo()

    assert sesion.scoring.get(2).stage is SleepStage.UNSCORED
    assert historial.changed_window == 2


def test_rehacer_la_vuelve_a_poner(sesion: Session, historial: History):
    sesion.scoring.set_stage(2, SleepStage.N2)
    historial.record()
    historial.undo()

    assert historial.redo()

    assert sesion.scoring.get(2).stage is SleepStage.N2
    assert historial.changed_window == 2


def test_se_deshace_en_orden_inverso(sesion: Session, historial: History):
    for ventana, fase in enumerate([SleepStage.WAKE, SleepStage.N1, SleepStage.N2]):
        sesion.scoring.set_stage(ventana, fase)
        historial.record()

    historial.undo()
    historial.undo()

    assert fases(sesion)[:3] == [SleepStage.WAKE, SleepStage.UNSCORED, SleepStage.UNSCORED]


def test_un_cambio_sin_registrar_tambien_se_deshace(sesion: Session, historial: History):
    """Deshacer siempre deshace lo último que se hizo, aunque nadie lo haya
    registrado todavía."""
    sesion.scoring.set_arousal(1, True)

    assert historial.can_undo
    assert historial.undo()

    assert not sesion.scoring.get(1).arousal


def test_moverse_de_ventana_no_gasta_un_paso(sesion: Session, historial: History):
    """No es trabajo del investigador."""
    sesion.go_to_window(3)

    assert not historial.record()
    assert not historial.can_undo


def test_un_cambio_nuevo_borra_lo_que_se_podia_rehacer(sesion: Session, historial: History):
    sesion.scoring.set_stage(0, SleepStage.N2)
    historial.record()
    historial.undo()

    sesion.scoring.set_stage(1, SleepStage.N3)
    historial.record()

    assert not historial.can_redo
    assert not historial.redo()
    assert sesion.scoring.get(0).stage is SleepStage.UNSCORED


def test_hay_un_limite_de_pasos(sesion: Session):
    historial = History(sesion, limit=2)
    for ventana in range(3):
        sesion.scoring.set_stage(ventana, SleepStage.N2)
        historial.record()

    assert historial.undo()
    assert historial.undo()
    assert not historial.undo()

    assert fases(sesion)[:3] == [SleepStage.N2, SleepStage.UNSCORED, SleepStage.UNSCORED]


def test_olvidar_parte_de_como_esta(sesion: Session, historial: History):
    """Lo que se recupera de la copia no se deshace: sería perderlo."""
    sesion.scoring.set_stage(0, SleepStage.N2)

    historial.reset()

    assert not historial.undo()
    assert sesion.scoring.get(0).stage is SleepStage.N2


# -- Las anotaciones ----------------------------------------------------------------


def test_deshacer_una_anotacion_nueva_la_saca(sesion: Session, historial: History):
    sesion.annotations.add(Annotation("Arousal", 3 * MUESTRAS_POR_VENTANA + 10, 50))
    historial.record()

    historial.undo()

    assert sesion.annotations.all() == []
    assert historial.changed_window == 3


def test_deshacer_un_borrado_la_vuelve_a_poner(sesion: Session, historial: History):
    anotacion = Annotation("Arousal", 100, 50, ("C3",))
    sesion.annotations.add(anotacion)
    historial.record()
    sesion.annotations.remove(anotacion)
    historial.record()

    historial.undo()

    assert sesion.annotations.all() == [anotacion]


def test_deshacer_un_borde_corrido_vuelve_al_tramo_de_antes(
    sesion: Session, historial: History
):
    original = Annotation("Arousal", 100, 50)
    sesion.annotations.add(original)
    historial.record()
    sesion.annotations.replace(original, Annotation("Arousal", 100, 400))
    historial.record()

    historial.undo()

    assert sesion.annotations.all() == [original]


# -- Lo que cambia muchas ventanas de un golpe ----------------------------------------


def test_deshacer_un_cambio_de_nomenclatura_recupera_lo_que_se_perdio(sesion: Session):
    """R&K a AASM funde S3 y S4 en N3: deshacer tiene que devolver S4."""
    rk = Session(sesion.recording, Scoring(VENTANAS, Nomenclature.RK), AnnotationSet())
    historial = History(rk)
    rk.scoring.set_stage(0, SleepStage.S4)
    historial.record()
    rk.scoring.change_nomenclature(Nomenclature.AASM)
    historial.record()

    historial.undo()

    assert rk.scoring.nomenclature is Nomenclature.RK
    assert rk.scoring.get(0).stage is SleepStage.S4


def test_deshacer_confirmar_las_sugeridas_las_deja_pendientes(
    sesion: Session, historial: History
):
    sesion.scoring.set_suggestions([StageSuggestion(SleepStage.N2, 0.9)] * VENTANAS)
    historial.record()
    sesion.scoring.accept_suggestions()
    historial.record()

    historial.undo()

    assert sesion.scoring.scored_windows() == 0
    assert sesion.scoring.pending_suggestions() == VENTANAS


def test_deshacer_descartar_las_sugeridas_las_vuelve_a_poner(
    sesion: Session, historial: History
):
    sesion.scoring.set_suggestions([StageSuggestion(SleepStage.N2, 0.9)] * VENTANAS)
    historial.record()
    sesion.scoring.clear_suggestions()
    historial.record()

    historial.undo()

    assert sesion.scoring.pending_suggestions() == VENTANAS
    assert historial.changed_window is None


def test_deshacer_un_scoring_importado_vuelve_al_de_antes(
    sesion: Session, historial: History
):
    """Importar lo da por exportado; deshacerlo deja trabajo sin exportar."""
    sesion.scoring.set_stage(0, SleepStage.WAKE)
    historial.record()
    importado = Scoring(VENTANAS, Nomenclature.AASM)
    importado.set_stage(0, SleepStage.N3)
    sesion.set_scoring(importado)
    historial.record()

    historial.undo()

    assert sesion.scoring.get(0).stage is SleepStage.WAKE
    assert sesion.has_unexported_scoring()
