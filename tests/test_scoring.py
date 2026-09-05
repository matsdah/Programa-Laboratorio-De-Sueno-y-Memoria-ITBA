"""Tests del scoring: fases, arousals y cambio de nomenclatura."""

from dataclasses import FrozenInstanceError

import pytest

from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.scoring import Scoring
from psglab.utils.errors import InvalidStageError, WindowOutOfRangeError

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


# -- Los bordes del índice --------------------------------------------------


@pytest.mark.parametrize("indice", [20, -1, 999])
def test_asignar_una_fase_fuera_de_rango_falla(scoring, indice):
    """`get` ya lo verificaba; los dos que escriben, no.

    Importa más acá que en `get`: escribir en la ventana −1 no devolvería un
    dato equivocado, lo **guardaría** en la última ventana de la noche.
    """
    with pytest.raises(WindowOutOfRangeError):
        scoring.set_stage(indice, SleepStage.N2)


@pytest.mark.parametrize("indice", [20, -1])
def test_marcar_un_arousal_fuera_de_rango_falla(scoring, indice):
    with pytest.raises(WindowOutOfRangeError):
        scoring.set_arousal(indice, True)


def test_la_ventana_se_valida_antes_que_la_fase(scoring):
    """Con los dos argumentos mal, el índice es la respuesta más útil.

    Decirle al usuario que S4 no existe en AASM cuando además pidió una ventana
    que no existe lo manda a mirar el problema equivocado.
    """
    with pytest.raises(WindowOutOfRangeError):
        scoring.set_stage(999, SleepStage.S4)


def test_un_scoring_con_ventanas_negativas_no_se_puede_crear():
    with pytest.raises(WindowOutOfRangeError):
        Scoring(n_windows=-1, nomenclature=Nomenclature.AASM)


def test_un_scoring_de_cero_ventanas_es_valido():
    """Es lo que corresponde a un registro sin muestras, y no es incoherente."""
    vacio = Scoring(n_windows=0, nomenclature=Nomenclature.AASM)
    assert vacio.n_windows == 0
    assert vacio.stages() == []
    assert vacio.scored_windows() == 0


# -- Borrar el scoring de una ventana ---------------------------------------


def test_se_puede_despuntuar_una_ventana_marcada_por_error(scoring):
    """Asignar UNSCORED es cómo el usuario deshace un scoring.

    Depende de que `nomenclature.is_valid(UNSCORED, ...)` sea `True`, que es una
    decisión del hito 1. Si alguna vez se revirtiera, esto falla acá y no en la
    interfaz seis meses después.
    """
    scoring.set_stage(7, SleepStage.N2)
    assert scoring.scored_windows() == 1

    scoring.set_stage(7, SleepStage.UNSCORED)
    assert scoring.get(7).stage == SleepStage.UNSCORED
    assert scoring.scored_windows() == 0


def test_despuntuar_no_borra_el_arousal(scoring):
    """Son dos hechos independientes: uno se deshace sin el otro."""
    scoring.set_stage(2, SleepStage.N3)
    scoring.set_arousal(2, True)
    scoring.set_stage(2, SleepStage.UNSCORED)
    assert scoring.get(2).arousal is True


# -- La nomenclatura --------------------------------------------------------


def test_cambiar_a_la_misma_nomenclatura_no_hace_nada(scoring):
    """La interfaz puede llamar sin preguntar si hace falta."""
    scoring.set_stage(0, SleepStage.N2)
    scoring.change_nomenclature(Nomenclature.AASM)
    assert scoring.nomenclature == Nomenclature.AASM
    assert scoring.get(0).stage == SleepStage.N2


def test_cambiar_de_nomenclatura_cambia_la_nomenclatura_activa(scoring):
    """Traducir las fases y dejar la etiqueta vieja sería peor que no traducir.

    `Scoring.txt` declara su nomenclatura en la cabecera, así que una etiqueta
    equivocada produce un archivo que dice una cosa y contiene otra.
    """
    scoring.change_nomenclature(Nomenclature.RK)
    assert scoring.nomenclature == Nomenclature.RK


def test_la_traduccion_pierde_informacion_y_no_vuelve(scoring):
    """S4 y S3 caen los dos en N3, y al volver sólo puede salir S3.

    No es un defecto: es una propiedad de las nomenclaturas, y está fijada acá
    para que nadie intente "arreglarla". Es además el motivo por el que la
    interfaz tiene que avisar antes de cambiar la nomenclatura de un registro
    ya scoreado.
    """
    rk = Scoring(n_windows=2, nomenclature=Nomenclature.RK)
    rk.set_stage(0, SleepStage.S3)
    rk.set_stage(1, SleepStage.S4)

    rk.change_nomenclature(Nomenclature.AASM)
    assert rk.get(0).stage == rk.get(1).stage == SleepStage.N3

    rk.change_nomenclature(Nomenclature.RK)
    assert rk.get(0).stage == rk.get(1).stage == SleepStage.S3


def test_las_ventanas_sin_scorear_sobreviven_al_cambio(scoring):
    """UNSCORED no es una fase y no se traduce."""
    scoring.set_stage(0, SleepStage.N2)
    scoring.change_nomenclature(Nomenclature.RK)
    assert scoring.get(5).stage == SleepStage.UNSCORED
    assert scoring.scored_windows() == 1


# -- Lo que se le presta a quien consulta -----------------------------------


def test_stages_devuelve_una_copia(scoring):
    """El histograma sólo quiere leerla.

    Prestarle la lista interna dejaría que la corrompiera sin pasar por
    `set_stage`, que es la única guarda de la nomenclatura.
    """
    prestada = scoring.stages()
    prestada[0] = SleepStage.S4
    assert scoring.get(0).stage == SleepStage.UNSCORED


def test_el_scoring_de_una_ventana_no_se_puede_escribir_por_atras(scoring):
    """`EpochScore` es inmutable justamente para esto.

    Sin esto, `scoring.get(i).stage = SleepStage.S4` esquivaría `set_stage()`,
    que es la única guarda que impide meter una fase de R&K en un scoring AASM.
    """
    with pytest.raises(FrozenInstanceError):
        scoring.get(0).stage = SleepStage.S4
