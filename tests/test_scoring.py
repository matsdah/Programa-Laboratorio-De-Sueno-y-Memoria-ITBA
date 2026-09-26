"""Tests del scoring: fases, arousals y cambio de nomenclatura."""

from dataclasses import FrozenInstanceError

import pytest

from conftest import VENTANAS_SINTETICAS
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.scoring import Scoring, StageSuggestion
from psglab.utils.errors import InvalidStageError, WindowOutOfRangeError

@pytest.fixture
def scoring() -> Scoring:
    """Scoring vacío de 20 ventanas en nomenclatura AASM."""
    return Scoring(n_windows=VENTANAS_SINTETICAS, nomenclature=Nomenclature.AASM)


def test_un_scoring_nuevo_arranca_entero_sin_scorear(scoring):
    """Todas las ventanas existen desde el principio, en UNSCORED.

    Es lo que permite que el histograma tenga el tamaño de la noche completa
    desde el arranque y que se pueda scorear una parte alejada del registro.
    """
    assert scoring.n_windows == VENTANAS_SINTETICAS
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
        scoring.get(VENTANAS_SINTETICAS)
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


@pytest.mark.parametrize("indice", [VENTANAS_SINTETICAS, -1, 999])
def test_asignar_una_fase_fuera_de_rango_falla(scoring, indice):
    """`get` ya lo verificaba; los dos que escriben, no.

    Importa más acá que en `get`: escribir en la ventana −1 no devolvería un
    dato equivocado, lo **guardaría** en la última ventana de la noche.
    """
    with pytest.raises(WindowOutOfRangeError):
        scoring.set_stage(indice, SleepStage.N2)


@pytest.mark.parametrize("indice", [VENTANAS_SINTETICAS, -1])
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


def test_stages_devuelve_una_lista_nueva_en_cada_llamada(scoring):
    """El histograma sólo quiere leerla.

    La versión anterior de este test mutaba la lista devuelta y comprobaba que
    el scoring no cambiara. Era **tautológico**: `_scores` guarda `EpochScore` y
    `stages()` construye una lista de `SleepStage`, así que no puede devolver la
    interna ni con la implementación más rota. Lo que sí se puede afirmar es que
    dos llamadas no comparten objeto, que es lo que protege ante un cache futuro.
    """
    assert scoring.stages() is not scoring.stages()


def test_una_ventana_sin_tocar_no_tiene_arousal(scoring):
    """Nadie miraba el arousal de una ventana recién creada.

    Con el valor por defecto en `True`, `Scoring.txt` escribiría `1` en todas
    las líneas y V2_F quedaría inservible sin que nada fallara.
    """
    assert scoring.get(0).arousal is False
    assert all(not scoring.get(i).arousal for i in range(scoring.n_windows))


def test_el_mensaje_numera_la_ventana_en_base_1(scoring):
    """La conversión base 0 → base 1 es una regla del proyecto.

    Es el único lugar donde el usuario ve el número, y no había ningún test que
    lo fijara: el mensaje podía numerar cualquier cosa.
    """
    with pytest.raises(WindowOutOfRangeError) as excepcion:
        scoring.get(VENTANAS_SINTETICAS)
    assert str(VENTANAS_SINTETICAS + 1) in excepcion.value.message


def test_el_scoring_de_una_ventana_no_se_puede_escribir_por_atras(scoring):
    """`EpochScore` es inmutable justamente para esto.

    Sin esto, `scoring.get(i).stage = SleepStage.S4` esquivaría `set_stage()`,
    que es la única guarda que impide meter una fase de R&K en un scoring AASM.
    """
    with pytest.raises(FrozenInstanceError):
        scoring.get(0).stage = SleepStage.S4


# -- `EpochScore.is_scored`, que ningún test nombraba (hito 48) --------------


def test_una_ventana_sin_fase_no_esta_scoreada(scoring):
    """Lo consultan `scored_windows()` y el cartel del trabajo sin exportar: si
    devolviera True de entrada, cerrar el programa recién abierto preguntaría
    si se quiere guardar una noche vacía."""
    assert scoring.get(0).is_scored is False


def test_una_ventana_con_fase_esta_scoreada(scoring):
    scoring.set_stage(0, SleepStage.N2)

    assert scoring.get(0).is_scored is True


def test_el_arousal_solo_no_cuenta_como_scoreada(scoring):
    """Son dos preguntas distintas: V2_F marca arousal sobre una ventana que
    puede no tener fase todavía."""
    scoring.set_arousal(0, True)

    assert scoring.get(0).is_scored is False


# -- Fases sugeridas (hito 75) ----------------------------------------------


def _sugerencias(scoring: Scoring, **por_ventana: StageSuggestion) -> list:
    """Una lista del largo del scoring, con sugerencias sólo donde se piden."""
    lista: list = [None] * scoring.n_windows
    for clave, sugerida in por_ventana.items():
        lista[int(clave.removeprefix("v"))] = sugerida
    return lista


def test_una_sugerencia_no_es_scoring(scoring):
    """**Vive en otra capa**: `stage` sigue queriendo decir «la eligió una
    persona», y por eso ni los exportadores ni las estadísticas la ven."""
    scoring.set_suggestions(_sugerencias(scoring, v3=StageSuggestion(SleepStage.N2, 0.9)))

    assert scoring.get(3).stage is SleepStage.UNSCORED
    assert scoring.scored_windows() == 0
    assert scoring.suggestion(3) == StageSuggestion(SleepStage.N2, 0.9)
    assert scoring.pending_suggestions() == 1


def test_una_sugerencia_nunca_pisa_una_fase_puesta_a_mano(scoring):
    scoring.set_stage(3, SleepStage.WAKE)
    scoring.set_suggestions(_sugerencias(scoring, v3=StageSuggestion(SleepStage.N3, 1.0)))

    assert scoring.get(3).stage is SleepStage.WAKE
    # Ni se muestra: lo que eligió una persona gana.
    assert scoring.suggestion(3) is None
    assert scoring.pending_suggestions() == 0
    assert scoring.accept_suggestions() == 0
    assert scoring.get(3).stage is SleepStage.WAKE


def test_borrar_la_fase_devuelve_la_sugerencia(scoring):
    scoring.set_suggestions(_sugerencias(scoring, v3=StageSuggestion(SleepStage.N2, 0.9)))
    scoring.set_stage(3, SleepStage.N1)
    scoring.set_stage(3, SleepStage.UNSCORED)

    assert scoring.suggestion(3) == StageSuggestion(SleepStage.N2, 0.9)


def test_confirmar_respeta_la_confianza_minima(scoring):
    scoring.set_suggestions(
        _sugerencias(
            scoring,
            v1=StageSuggestion(SleepStage.N2, 0.95),
            v2=StageSuggestion(SleepStage.N3, 0.8),
            v4=StageSuggestion(SleepStage.N1, 0.5),
        )
    )

    assert scoring.accept_suggestions(0.8) == 2

    assert scoring.get(1).stage is SleepStage.N2
    # El umbral es inclusivo: «al menos 80 %».
    assert scoring.get(2).stage is SleepStage.N3
    assert scoring.get(4).stage is SleepStage.UNSCORED
    assert scoring.suggestion(4) == StageSuggestion(SleepStage.N1, 0.5)
    assert scoring.accept_suggestions() == 1
    assert scoring.get(4).stage is SleepStage.N1


def test_las_sugerencias_se_traducen_a_la_nomenclatura_activa():
    """El clasificador sugiere en AASM; sobre R&K una N3 pasa a S3, como en
    `change_nomenclature()`."""
    scoring = Scoring(2, Nomenclature.RK)
    scoring.set_suggestions([StageSuggestion(SleepStage.N3, 0.9), StageSuggestion(SleepStage.R, 0.7)])

    assert scoring.suggestion(0).stage is SleepStage.S3
    assert scoring.suggestion(1).stage is SleepStage.REM
    assert scoring.accept_suggestions() == 2
    assert scoring.stages() == [SleepStage.S3, SleepStage.REM]


def test_cambiar_de_nomenclatura_traduce_tambien_las_sugeridas(scoring):
    """Sin esto, confirmar después asignaría una fase ajena a la nomenclatura y
    `set_stage()` la rechazaría a mitad de camino."""
    scoring.set_suggestions(_sugerencias(scoring, v0=StageSuggestion(SleepStage.N2, 0.9)))
    scoring.change_nomenclature(Nomenclature.RK)

    assert scoring.suggestion(0).stage is SleepStage.S2
    assert scoring.accept_suggestions() == 1


def test_descartar_las_sugerencias_no_toca_lo_scoreado(scoring):
    scoring.set_stage(0, SleepStage.N2)
    scoring.set_suggestions(_sugerencias(scoring, v1=StageSuggestion(SleepStage.N2, 0.9)))
    scoring.clear_suggestions()

    assert scoring.pending_suggestions() == 0
    assert scoring.get(0).stage is SleepStage.N2


def test_una_lista_corrida_se_rechaza_entera(scoring):
    """Una sugerencia por ventana, ni una más ni una menos: corrida en una,
    la noche entera quedaría desfasada sin que nada lo diga."""
    with pytest.raises(WindowOutOfRangeError):
        scoring.set_suggestions([None] * (scoring.n_windows - 1))


@pytest.mark.parametrize(
    "mala",
    [
        StageSuggestion(SleepStage.UNSCORED, 0.9),
        StageSuggestion("N2", 0.9),  # type: ignore[arg-type]
        StageSuggestion(SleepStage.N2, float("nan")),
        StageSuggestion(SleepStage.N2, 1.5),
        StageSuggestion(SleepStage.N2, True),  # type: ignore[arg-type]
        "N2",
    ],
)
def test_una_sugerencia_mala_no_deja_nada_a_medias(scoring, mala):
    """**Se valida todo antes de guardar**: una confianza NaN guardada no
    pasaría nunca ningún umbral, y nada diría por qué."""
    scoring.set_suggestions(_sugerencias(scoring, v0=StageSuggestion(SleepStage.N2, 0.9)))
    lista = _sugerencias(scoring, v1=StageSuggestion(SleepStage.N1, 0.9))
    lista[2] = mala

    with pytest.raises(InvalidStageError):
        scoring.set_suggestions(lista)

    assert scoring.suggestion(0) == StageSuggestion(SleepStage.N2, 0.9)
    assert scoring.suggestion(1) is None


@pytest.mark.parametrize("umbral", [-0.1, 1.01, "0.8", True, None])
def test_la_confianza_minima_es_una_probabilidad(scoring, umbral):
    with pytest.raises(InvalidStageError):
        scoring.accept_suggestions(umbral)
