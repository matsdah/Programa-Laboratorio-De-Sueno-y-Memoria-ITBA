"""Tests de las nomenclaturas de scoring y su conversión.

Verifican especialmente que REM esté presente en las dos nomenclaturas: el
listado del pliego la omitía, el cliente confirmó que tiene que estar, y este
test es lo que evita que la omisión vuelva a colarse.
"""

import pytest

from psglab.core.nomenclature import (
    STAGE_CODES,
    Nomenclature,
    SleepStage,
    convert,
    is_valid,
    stage_code,
    stage_label,
    stages_of,
)

def test_rk_incluye_rem():
    """Rechtschaffen y Kales sin REM no sería una nomenclatura válida."""
    assert SleepStage.REM in stages_of(Nomenclature.RK)


def test_aasm_incluye_rem():
    """AASM llama R a la fase REM, pero tiene que estar."""
    assert SleepStage.R in stages_of(Nomenclature.AASM)


def test_rk_tiene_las_siete_fases():
    """W, S1, S2, S3, S4, REM y MT."""
    assert len(stages_of(Nomenclature.RK)) == 7


def test_aasm_tiene_las_cinco_fases():
    """W, N1, N2, N3 y R."""
    assert len(stages_of(Nomenclature.AASM)) == 5


def test_el_orden_del_histograma_empieza_por_wake_y_rem():
    """El pliego fija el orden vertical: W, REM, S1, S2, S3, S4, MT."""
    orden = stages_of(Nomenclature.RK)
    assert orden[0] == SleepStage.WAKE
    assert orden[1] == SleepStage.REM


def test_una_fase_de_rk_no_es_valida_en_aasm():
    """S4 no existe en AASM: aceptarla dejaría un scoring inconsistente."""
    assert not is_valid(SleepStage.S4, Nomenclature.AASM)


@pytest.mark.parametrize(
    ("origen", "esperado"),
    [
        (SleepStage.S1, SleepStage.N1),
        (SleepStage.S2, SleepStage.N2),
        (SleepStage.S3, SleepStage.N3),
        (SleepStage.S4, SleepStage.N3),  # S3 y S4 se funden en N3
        (SleepStage.REM, SleepStage.R),
        (SleepStage.WAKE, SleepStage.WAKE),
    ],
)
def test_conversion_de_rk_a_aasm(origen, esperado):
    assert convert(origen, Nomenclature.AASM) == esperado


def test_la_conversion_de_rk_a_aasm_pierde_informacion():
    """S3 y S4 caen los dos en N3, y volver no puede distinguirlos.

    No es un defecto: es una propiedad de las nomenclaturas. El test la deja
    documentada para que nadie intente "arreglarla" más adelante.
    """
    n3_desde_s3 = convert(SleepStage.S3, Nomenclature.AASM)
    n3_desde_s4 = convert(SleepStage.S4, Nomenclature.AASM)
    assert n3_desde_s3 == n3_desde_s4
    assert convert(n3_desde_s4, Nomenclature.RK) == SleepStage.S3


def test_una_ventana_sin_scorear_sigue_sin_scorear_al_convertir():
    assert convert(SleepStage.UNSCORED, Nomenclature.AASM) == SleepStage.UNSCORED


def test_el_movimiento_se_convierte_en_vigilia():
    """MT no existe en AASM y hay que mandarlo a algún lado.

    Es la convención habitual —un tramo de movimiento no es sueño— y es una
    pérdida de información deliberada, así que conviene tenerla fijada: sin este
    test, mandar MT a "sin scorear" pasaba desapercibido.
    """
    assert convert(SleepStage.MT, Nomenclature.AASM) == SleepStage.WAKE


@pytest.mark.parametrize(
    ("origen", "esperado"),
    [
        (SleepStage.N1, SleepStage.S1),
        (SleepStage.N2, SleepStage.S2),
        (SleepStage.N3, SleepStage.S3),
        (SleepStage.R, SleepStage.REM),
        (SleepStage.WAKE, SleepStage.WAKE),
    ],
)
def test_conversion_de_aasm_a_rk(origen, esperado):
    """La dirección inversa, que sólo estaba cubierta para N3."""
    assert convert(origen, Nomenclature.RK) == esperado


def test_rem_y_r_son_la_misma_fase_en_las_dos_nomenclaturas():
    """Es el propósito declarado de este archivo, y no estaba verificado.

    Los tests de arriba comprueban que REM **pertenezca** a cada nomenclatura,
    pero la equivalencia entre las dos etiquetas —que es donde vive el riesgo
    real— no se probaba en ninguna dirección: se podía romper `R → REM` sin que
    nada fallara.
    """
    assert convert(SleepStage.REM, Nomenclature.AASM) == SleepStage.R
    assert convert(SleepStage.R, Nomenclature.RK) == SleepStage.REM


# -- Lo que termina escrito en Scoring.txt -----------------------------------


def test_la_etiqueta_de_una_fase_es_la_que_ve_el_usuario():
    """El panel de scoring y el histograma muestran esto.

    Sin este test se podía devolver el nombre del miembro del enum en vez de su
    valor, y la interfaz entera pasaba a decir "WAKE" en vez de "W".
    """
    assert stage_label(SleepStage.WAKE) == "W"
    assert stage_label(SleepStage.REM) == "REM"
    assert stage_label(SleepStage.N2) == "N2"
    assert stage_label(SleepStage.UNSCORED) == "-"


@pytest.mark.parametrize(
    ("fase", "codigo"),
    [
        (SleepStage.WAKE, 0),
        (SleepStage.S1, 1),
        (SleepStage.S2, 2),
        (SleepStage.S3, 3),
        (SleepStage.S4, 4),
        (SleepStage.REM, 5),
        (SleepStage.MT, 6),
        (SleepStage.N1, 1),
        (SleepStage.N2, 2),
        (SleepStage.N3, 3),
        (SleepStage.R, 5),
        (SleepStage.UNSCORED, -1),
    ],
)
def test_el_codigo_de_cada_fase_es_el_que_confirmo_el_cliente(fase, codigo):
    """Dos decisiones del hito 0 viven en esta tabla y no tenían ningún test.

    Los códigos de REM y MT y el `-1` de la ventana sin scorear se confirmaron
    con el cliente el 4 de septiembre de 2026, y son lo que terminan leyendo los
    scripts de análisis del laboratorio. Se podía poner la tabla entera en cero
    sin que la suite se inmutara.
    """
    assert stage_code(fase) == codigo


def test_la_tabla_de_codigos_no_es_inyectiva_a_proposito():
    """S1 y N1 comparten el 1, igual que S2/N2, S3/N3 y REM/R.

    Codificar está bien; **decodificar exige saber la nomenclatura**, y por eso
    `Scoring.txt` la declara en su cabecera. Si algún día la tabla se volviera
    inyectiva, esa cabecera dejaría de ser necesaria y el cambio tiene que ser
    deliberado, no un descuido.
    """
    assert stage_code(SleepStage.S1) == stage_code(SleepStage.N1)
    assert stage_code(SleepStage.REM) == stage_code(SleepStage.R)


def test_la_ventana_sin_scorear_no_puede_confundirse_con_ninguna_fase():
    """El `-1` se eligió justamente por eso: las fases reales son todas >= 0."""
    codigo_sin_scorear = stage_code(SleepStage.UNSCORED)
    reales = [c for f, c in STAGE_CODES.items() if f is not SleepStage.UNSCORED]
    assert codigo_sin_scorear < 0
    assert all(c >= 0 for c in reales)


def test_todas_las_fases_tienen_codigo_y_etiqueta():
    """Una fase nueva sin entrada en la tabla elevaría KeyError al exportar."""
    for fase in SleepStage:
        assert isinstance(stage_code(fase), int)
        assert stage_label(fase)
