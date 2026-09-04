"""Tests del formato exacto de los archivos de salida.

Los tres archivos son la salida real del trabajo del laboratorio: alimentan
los análisis estadísticos posteriores. Un cambio silencioso de formato rompe
scripts río abajo sin que nadie se entere hasta mucho después, así que el
formato se fija acá.
"""

import pytest

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.scoring import Scoring
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.scoring_txt import export_scoring, format_line

pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")


# -- Scoring.txt ------------------------------------------------------------


def test_una_linea_de_scoring_sigue_el_ejemplo_del_pliego():
    """El pliego da el ejemplo textual: "2 0" es fase 2 sin arousal."""
    assert format_line(1, stage_code=2, arousal=False, include_window_number=False) == "2 0"


def test_el_arousal_se_marca_con_un_uno():
    """El pliego: "2 1" es fase 2 con arousal."""
    assert format_line(1, stage_code=2, arousal=True, include_window_number=False) == "2 1"


def test_el_archivo_tiene_una_linea_por_ventana(tmp_path):
    """Incluidas las ventanas sin scorear.

    Si se saltearan, el número de línea dejaría de coincidir con el número de
    ventana y el archivo se volvería ambiguo.
    """
    scoring = Scoring(n_windows=20, nomenclature=Nomenclature.AASM)
    scoring.set_stage(0, SleepStage.WAKE)
    destino = tmp_path / "Scoring.txt"
    export_scoring(scoring, destino)
    assert len(destino.read_text(encoding="utf-8").strip().splitlines()) == 20


def test_las_ventanas_se_exportan_en_orden(tmp_path):
    """La línea N del archivo corresponde a la ventana N del registro.

    Se scorean tres ventanas con fases distintas (W=0, N1=1, N2=2) para poder
    verificar el orden mirando el código de fase de cada línea.
    """
    scoring = Scoring(n_windows=3, nomenclature=Nomenclature.AASM)
    scoring.set_stage(0, SleepStage.WAKE)
    scoring.set_stage(1, SleepStage.N1)
    scoring.set_stage(2, SleepStage.N2)
    destino = tmp_path / "Scoring.txt"
    # El flag va explícito: este test mira el primer campo de cada línea, así
    # que sólo tiene sentido sin el número de ventana adelante. Si dependiera
    # del valor de `config.SCORING_INCLUDES_WINDOW_NUMBER`, fallaría el día que
    # el cliente confirme la otra variante, y por un motivo que no es el que
    # este test verifica.
    export_scoring(scoring, destino, include_window_number=False)
    lineas = destino.read_text(encoding="utf-8").strip().splitlines()
    codigos_de_fase = [linea.split()[0] for linea in lineas]
    assert codigos_de_fase == ["0", "1", "2"]


# -- Anotaciones.txt --------------------------------------------------------


def test_una_anotacion_tiene_los_tres_campos_del_pliego(tmp_path):
    """Label_Annotation | Puntos_Emp | Duracion_Puntos."""
    anotaciones = AnnotationSet()
    anotaciones.add(Annotation(label="Arousal", onset_sample=7680, duration_samples=512))
    destino = tmp_path / "Anotaciones.txt"
    export_annotations(anotaciones, destino)
    campos = destino.read_text(encoding="utf-8").strip().split("|")
    assert len(campos) == 3
    assert campos[0].strip() == "Arousal"
    assert campos[1].strip() == "7680"
    assert campos[2].strip() == "512"


def test_las_anotaciones_se_exportan_ordenadas_por_inicio(tmp_path):
    """Aunque se hayan creado en otro orden: el archivo se lee cronológicamente."""
    anotaciones = AnnotationSet()
    anotaciones.add(Annotation(label="Arousal", onset_sample=9000, duration_samples=100))
    anotaciones.add(Annotation(label="Spindle", onset_sample=1000, duration_samples=100))
    destino = tmp_path / "Anotaciones.txt"
    export_annotations(anotaciones, destino)
    lineas = destino.read_text(encoding="utf-8").strip().splitlines()
    assert lineas[0].startswith("Spindle")


def test_una_etiqueta_con_el_separador_no_rompe_el_formato(tmp_path):
    """El usuario puede poner cualquier nombre a una clase nueva.

    Si la etiqueta contiene una barra vertical, el archivo tiene que seguir
    teniendo tres campos por línea.
    """
    anotaciones = AnnotationSet()
    anotaciones.add_label("Artefacto | dudoso")
    anotaciones.add(
        Annotation(label="Artefacto | dudoso", onset_sample=100, duration_samples=50)
    )
    destino = tmp_path / "Anotaciones.txt"
    export_annotations(anotaciones, destino)
    assert len(destino.read_text(encoding="utf-8").strip().split("|")) == 3
