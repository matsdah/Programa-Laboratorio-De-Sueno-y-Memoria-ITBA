"""Tests de las nomenclaturas de scoring y su conversión.

Verifican especialmente que REM esté presente en las dos nomenclaturas: el
listado del pliego la omitía, el cliente confirmó que tiene que estar, y este
test es lo que evita que la omisión vuelva a colarse.
"""

import pytest

from psglab.core.nomenclature import (
    Nomenclature,
    SleepStage,
    convert,
    is_valid,
    stages_of,
)

pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")


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
