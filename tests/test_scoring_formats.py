"""Tests del scoring en CSV, EDF+ y XML: la ida, la vuelta y lo ajeno.

Cubre los dos módulos gemelos, `exporters/scoring_formats.py` y
`readers/scoring_formats.py`, **juntos a propósito**: el contrato entre los dos
no está escrito en ninguna tabla compartida, sino en que lo que uno escribe el
otro lo lee. La ida y la vuelta de cada formato, con las dos nomenclaturas, es
lo que lo fija.

Lo demás son los archivos que **no escribió este programa**: un hipnograma
como el de la Sleep-EDF, un XML del NSRR sin declaración, una planilla con
punto y coma. Se arman acá, sintéticos, igual que la señal de `conftest.py`:
ningún test lee los registros de `data/`.

**El caso que más importa es el de la nomenclatura**, por el mismo motivo que
en `test_scoring_reader.py`: leída con la equivocada, la noche se carga entera
mal traducida y sin ningún error.
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from psglab.config import WINDOW_SECONDS
from psglab.core.nomenclature import Nomenclature, SleepStage, stages_of
from psglab.core.scoring import Scoring
from psglab.exporters.scoring_formats import (
    SCORING_FORMATS,
    _cabecera_edf,
    export_scoring_as,
)
from psglab.readers.scoring_formats import NOMENCLATURE_NAMES, read_scoring_file
from psglab.readers.scoring_reader import read_scoring
from psglab.utils.errors import (
    PsgLabError,
    ScoringMismatchError,
    UndeclaredNomenclatureError,
    UnreadableFileError,
    UnsupportedFormatError,
)

INICIO = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def scoring_completo(nomenclatura: Nomenclature) -> Scoring:
    """Todas las fases de la nomenclatura, tramos de largo distinto, ventanas
    sin scorear en el medio y al final, y dos arousals."""
    fases = stages_of(nomenclatura)
    scoring = Scoring(3 * len(fases) + 4, nomenclatura)
    indice = 0
    for largo, fase in enumerate(fases, start=1):
        for _ in range(min(largo, 3)):
            scoring.set_stage(indice, fase)
            indice += 1
    # Una ventana sin scorear entre dos scoreadas: el tramo tiene que cortarse.
    scoring.set_stage(indice + 1, fases[0])
    scoring.set_arousal(1, True)
    scoring.set_arousal(indice + 1, True)
    return scoring


def fases_y_arousals(scoring: Scoring) -> list[tuple[SleepStage, bool]]:
    return [(scoring.get(i).stage, scoring.get(i).arousal) for i in range(scoring.n_windows)]


def edf_con(
    tmp_path: Path,
    anotaciones: list[tuple[float, float, str]],
    inicio: datetime | None = None,
    nombre: str = "hipnograma.edf",
) -> Path:
    """Un EDF+ de anotaciones con las que se pidan, como las de otro programa.

    Usa la cabecera del exportador para no escribir la misma estructura dos
    veces; lo que importa acá son las anotaciones, que el exportador nunca
    escribiría así.
    """
    bloque = "+0\x14\x14\x00" + "".join(
        f"+{inicio_s:g}\x15{duracion:g}\x14{texto}\x14\x00"
        for inicio_s, duracion, texto in anotaciones
    )
    datos = bloque.encode("utf-8")
    muestras = (len(datos) + 1) // 2
    ruta = tmp_path / nombre
    ruta.write_bytes(_cabecera_edf(inicio, muestras) + datos.ljust(2 * muestras, b"\x00"))
    return ruta


def xml_con(tmp_path: Path, eventos: list[tuple[str, str, float, float]], extra: str = "") -> Path:
    """Un XML del NSRR escrito a mano, sin la declaración que agrega este programa."""
    cuerpo = "".join(
        f"<ScoredEvent><EventType>{tipo}</EventType><EventConcept>{concepto}</EventConcept>"
        f"<Start>{inicio}</Start><Duration>{duracion}</Duration></ScoredEvent>"
        for tipo, concepto, inicio, duracion in eventos
    )
    ruta = tmp_path / "nsrr.xml"
    ruta.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><PSGAnnotation>'
        f"<SoftwareVersion>Compumedics</SoftwareVersion><EpochLength>30</EpochLength>{extra}"
        f"<ScoredEvents>{cuerpo}</ScoredEvents></PSGAnnotation>",
        encoding="utf-8",
    )
    return ruta


def csv_con(tmp_path: Path, contenido: str) -> Path:
    ruta = tmp_path / "Scoring.csv"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# -- La ida y la vuelta ------------------------------------------------------------


@pytest.mark.parametrize("extension", list(SCORING_FORMATS))
@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_lo_que_se_exporta_se_vuelve_a_leer_igual(tmp_path, extension, nomenclatura):
    original = scoring_completo(nomenclatura)
    ruta = tmp_path / f"Scoring.{extension}"

    export_scoring_as(original, ruta, INICIO)
    leido = read_scoring(ruta, original.n_windows, start_time=INICIO)

    assert leido.nomenclature is nomenclatura
    assert fases_y_arousals(leido) == fases_y_arousals(original)


@pytest.mark.parametrize("extension", ["csv", "xml"])
def test_la_vuelta_no_pregunta_aunque_no_haya_fases_exclusivas(tmp_path, extension):
    """Un scoring de R&K sin S4 ni MT usa sólo códigos que AASM también tiene.
    El CSV lo resuelve con los rótulos y el XML con su declaración."""
    original = Scoring(3, Nomenclature.RK)
    original.set_stage(0, SleepStage.S2)
    original.set_stage(1, SleepStage.REM)
    ruta = tmp_path / f"Scoring.{extension}"

    export_scoring_as(original, ruta)

    assert read_scoring(ruta, 3).nomenclature is Nomenclature.RK


def test_un_edf_de_rk_sin_fases_exclusivas_si_pregunta(tmp_path):
    """Es el costo aceptado del EDF+, que no tiene dónde declarar la
    nomenclatura: «Sleep stage 2» se usa en las dos. AASM no pregunta nunca,
    porque escribe «Sleep stage N2»."""
    original = Scoring(3, Nomenclature.RK)
    original.set_stage(0, SleepStage.S2)
    ruta = tmp_path / "Scoring.edf"
    export_scoring_as(original, ruta)

    with pytest.raises(UndeclaredNomenclatureError):
        read_scoring(ruta, 3)
    assert read_scoring(ruta, 3, Nomenclature.RK).get(0).stage is SleepStage.S2


def test_un_scoring_vacio_tambien_hace_el_viaje(tmp_path):
    original = Scoring(4, Nomenclature.AASM)
    ruta = tmp_path / "Scoring.xml"

    export_scoring_as(original, ruta)

    assert fases_y_arousals(read_scoring(ruta, 4)) == fases_y_arousals(original)


# -- Lo que se escribe ---------------------------------------------------------------


def test_los_formatos_son_los_cuatro_en_el_orden_del_menu():
    assert list(SCORING_FORMATS) == ["txt", "csv", "edf", "xml"]


def test_el_csv_lleva_una_fila_por_ventana_con_su_rotulo(tmp_path):
    scoring = Scoring(3, Nomenclature.AASM)
    scoring.set_stage(1, SleepStage.N2)
    scoring.set_arousal(1, True)
    ruta = tmp_path / "Scoring.csv"

    export_scoring_as(scoring, ruta)

    assert ruta.read_text(encoding="utf-8").splitlines() == [
        "ventana,inicio_s,fase,arousal",
        "1,0,-,0",
        "2,30,N2,1",
        "3,60,-,0",
    ]


def test_el_edf_lo_lee_mne_con_los_rotulos_de_la_sleep_edf(tmp_path):
    """MNE es con lo que el resto del mundo va a abrir este archivo."""
    import mne

    scoring = Scoring(4, Nomenclature.RK)
    for indice in range(3):
        scoring.set_stage(indice, SleepStage.S4)
    scoring.set_arousal(0, True)
    ruta = tmp_path / "Scoring.edf"

    export_scoring_as(scoring, ruta)
    anotaciones = mne.read_annotations(ruta)

    # MNE las ordena por inicio, así que se comparan sin orden.
    assert sorted(
        zip(anotaciones.description, anotaciones.onset, anotaciones.duration)
    ) == sorted(
        [
            ("Sleep stage 4", 0.0, 3 * WINDOW_SECONDS),
            ("Sleep stage ?", 3 * WINDOW_SECONDS, WINDOW_SECONDS),
            ("Arousal", 0.0, WINDOW_SECONDS),
        ]
    )


def test_el_edf_de_aasm_usa_el_prefijo_n(tmp_path):
    import mne

    scoring = Scoring(1, Nomenclature.AASM)
    scoring.set_stage(0, SleepStage.N3)
    ruta = tmp_path / "Scoring.edf"

    export_scoring_as(scoring, ruta)

    assert list(mne.read_annotations(ruta).description) == ["Sleep stage N3"]


def test_la_cabecera_del_edf_lleva_la_fecha_del_registro(tmp_path):
    ruta = tmp_path / "Scoring.edf"

    export_scoring_as(Scoring(1, Nomenclature.AASM), ruta, INICIO)
    cabecera = ruta.read_bytes()[:256]

    assert cabecera[88:118] == b"Startdate 02-JAN-2020 X X PSGL"
    assert cabecera[168:184] == b"02.01.2003.04.05"
    assert cabecera[192:197] == b"EDF+C"


def test_sin_fecha_el_edf_dice_que_no_la_sabe(tmp_path):
    ruta = tmp_path / "Scoring.edf"

    export_scoring_as(Scoring(1, Nomenclature.AASM), ruta)

    assert ruta.read_bytes()[88:99] == b"Startdate X"


def test_un_anio_que_no_entra_en_dos_cifras_se_escribe_yy(tmp_path):
    """Es la regla del estándar para después de 2084."""
    ruta = tmp_path / "Scoring.edf"

    export_scoring_as(Scoring(1, Nomenclature.AASM), ruta, datetime(2090, 5, 6))
    cabecera = ruta.read_bytes()[:256]

    assert cabecera[168:176] == b"06.05.yy"
    assert b"Startdate 06-MAY-2090" in cabecera


def test_una_noche_larga_no_sale_en_notacion_cientifica(tmp_path):
    """`f"{x:g}"` pasa a notación científica desde el millón de segundos."""
    scoring = Scoring(40_000, Nomenclature.AASM)
    scoring.set_stage(39_999, SleepStage.N2)
    ruta = tmp_path / "Scoring.edf"

    export_scoring_as(scoring, ruta)

    assert b"+1199970\x1530\x14Sleep stage N2" in ruta.read_bytes()
    assert b"e+" not in ruta.read_bytes()[512:]


def test_el_xml_declara_la_nomenclatura_y_agrupa_los_tramos(tmp_path):
    import xml.etree.ElementTree as ET

    scoring = Scoring(5, Nomenclature.AASM)
    for indice in range(5):
        scoring.set_stage(indice, SleepStage.R)
    ruta = tmp_path / "Scoring.xml"

    export_scoring_as(scoring, ruta)
    raiz = ET.parse(ruta).getroot()

    assert raiz.tag == "PSGAnnotation"
    assert raiz.findtext("Nomenclature") == "AASM"
    eventos = raiz.findall("ScoredEvents/ScoredEvent")
    assert len(eventos) == 1
    assert eventos[0].findtext("EventType") == "Stages|Stages"
    assert eventos[0].findtext("EventConcept") == "REM sleep|5"
    assert eventos[0].findtext("Start") == "0"
    assert eventos[0].findtext("Duration") == "150"


def test_una_extension_desconocida_no_se_exporta(tmp_path):
    with pytest.raises(UnsupportedFormatError) as fallo:
        export_scoring_as(Scoring(1, Nomenclature.AASM), tmp_path / "Scoring.json")

    assert ".csv" in str(fallo.value)
    assert issubclass(UnsupportedFormatError, PsgLabError)


def test_la_extension_se_reconoce_sin_importar_mayusculas(tmp_path):
    scoring = Scoring(1, Nomenclature.AASM)
    scoring.set_stage(0, SleepStage.N1)
    ruta = tmp_path / "SCORING.CSV"

    export_scoring_as(scoring, ruta)

    assert ruta.read_text(encoding="utf-8").startswith("ventana,")
    assert read_scoring(ruta, 1).get(0).stage is SleepStage.N1


def test_un_archivo_con_solo_vigilia_y_sin_scorear_pregunta(tmp_path):
    """W y «sin scorear» existen en las dos: el archivo no alcanza para saber
    con cuál se va a seguir scoreando."""
    ruta = tmp_path / "Scoring.csv"
    export_scoring_as(Scoring(2, Nomenclature.AASM), ruta)

    with pytest.raises(UndeclaredNomenclatureError):
        read_scoring(ruta, 2)
    assert read_scoring(ruta, 2, Nomenclature.AASM).nomenclature is Nomenclature.AASM


# -- El CSV de otro programa ---------------------------------------------------------


def test_un_csv_con_punto_y_coma_se_lee(tmp_path):
    """Es como guarda Excel con la configuración regional en español."""
    ruta = csv_con(tmp_path, "ventana;inicio_s;fase;arousal\n1;0;S2;0\n2;30;REM;1\n")

    scoring = read_scoring(ruta, 2)

    assert fases_y_arousals(scoring) == [(SleepStage.S2, False), (SleepStage.REM, True)]


def test_un_csv_con_columnas_en_ingles_y_marca_de_excel_se_lee(tmp_path):
    ruta = tmp_path / "hipnograma.csv"
    ruta.write_bytes("﻿Epoch,Stage\n2,n1\n".encode("utf-8"))

    scoring = read_scoring(ruta, 3)

    assert scoring.get(1).stage is SleepStage.N1
    assert scoring.get(0).stage is SleepStage.UNSCORED


def test_sin_columna_ventana_cuenta_el_orden_de_las_filas(tmp_path):
    ruta = csv_con(tmp_path, "fase\nW\n?\nN2\n")

    scoring = read_scoring(ruta, 3)

    assert [scoring.get(i).stage for i in range(3)] == [
        SleepStage.WAKE,
        SleepStage.UNSCORED,
        SleepStage.N2,
    ]


def test_un_csv_con_codigos_necesita_la_nomenclatura(tmp_path):
    ruta = csv_con(tmp_path, "fase,arousal\n2,0\n")

    with pytest.raises(UndeclaredNomenclatureError):
        read_scoring(ruta, 1)
    assert read_scoring(ruta, 1, Nomenclature.AASM).get(0).stage is SleepStage.N2
    assert read_scoring(ruta, 1, Nomenclature.RK).get(0).stage is SleepStage.S2


def test_un_codigo_que_existe_en_una_sola_la_decide(tmp_path):
    """El 4 sólo es S4: no hace falta preguntar, y el parámetro no la pisa."""
    ruta = csv_con(tmp_path, "fase\n2\n4\n")

    scoring = read_scoring(ruta, 2, Nomenclature.AASM)

    assert scoring.nomenclature is Nomenclature.RK
    assert scoring.get(0).stage is SleepStage.S2


def test_un_csv_sin_columna_de_fase_avisa(tmp_path):
    ruta = csv_con(tmp_path, "ventana,arousal\n1,0\n")

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 1)

    assert "fase" in str(fallo.value)


def test_una_fase_que_no_existe_avisa_con_su_linea(tmp_path):
    ruta = csv_con(tmp_path, "ventana,fase\n1,W\n2,N5\n")

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 2)

    assert "línea 3" in str(fallo.value)
    assert "N5" in str(fallo.value)


def test_un_arousal_que_no_es_cero_ni_uno_avisa(tmp_path):
    ruta = csv_con(tmp_path, "fase,arousal\nW,si\n")

    with pytest.raises(UnreadableFileError):
        read_scoring(ruta, 1)


def test_una_ventana_cero_avisa_que_se_cuentan_desde_uno(tmp_path):
    ruta = csv_con(tmp_path, "ventana,fase\n0,W\n")

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 1)

    assert "desde 1" in str(fallo.value)


def test_un_csv_vacio_avisa(tmp_path):
    with pytest.raises(UnreadableFileError):
        read_scoring(csv_con(tmp_path, ""), 1)


def test_mezclar_las_dos_nomenclaturas_avisa(tmp_path):
    ruta = csv_con(tmp_path, "fase\nS2\nN2\n")

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 2)

    assert "mezcla" in str(fallo.value)


def test_un_codigo_que_no_existe_en_ninguna_avisa_distinto(tmp_path):
    ruta = csv_con(tmp_path, "fase\n2\n7\n")

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 2)

    assert "ninguna nomenclatura" in str(fallo.value)
    assert "línea 3" in str(fallo.value)


def test_una_fila_scoreada_despues_del_final_avisa(tmp_path):
    ruta = csv_con(tmp_path, "ventana,fase\n1,W\n3,N2\n")

    with pytest.raises(ScoringMismatchError):
        read_scoring(ruta, 2)


def test_una_fila_sin_scorear_despues_del_final_no_molesta(tmp_path):
    ruta = csv_con(tmp_path, "ventana,fase,arousal\n1,N2,0\n3,-,0\n")

    assert read_scoring(ruta, 2).get(0).stage is SleepStage.N2


# -- El hipnograma de otro programa --------------------------------------------------


def test_un_hipnograma_como_el_de_la_sleep_edf(tmp_path):
    """Tramos de muchas épocas, R&K con estadio 4, y un «?» final que se pasa
    del registro: es exactamente como termina el de la Sleep-EDF."""
    ruta = edf_con(
        tmp_path,
        [
            (0, 10 * WINDOW_SECONDS, "Sleep stage W"),
            (300, 60, "Sleep stage 4"),
            (360, 30, "Sleep stage R"),
            (390, 6900, "Sleep stage ?"),
        ],
    )

    scoring = read_scoring(ruta, 14)

    assert scoring.nomenclature is Nomenclature.RK
    assert [scoring.get(i).stage for i in range(14)] == (
        [SleepStage.WAKE] * 10
        + [SleepStage.S4] * 2
        + [SleepStage.REM]
        + [SleepStage.UNSCORED]
    )


def test_movement_time_es_mt_y_decide_rk(tmp_path):
    ruta = edf_con(tmp_path, [(0, 30, "Sleep stage 2"), (30, 30, "Movement time")])

    scoring = read_scoring(ruta, 2)

    assert scoring.nomenclature is Nomenclature.RK
    assert scoring.get(1).stage is SleepStage.MT


def test_las_anotaciones_que_no_son_del_scoring_se_ignoran(tmp_path):
    ruta = edf_con(
        tmp_path, [(0, 0, "Lights off"), (0, 30, "Sleep stage N1"), (15, 5, "Bip")]
    )

    scoring = read_scoring(ruta, 1)

    assert scoring.get(0).stage is SleepStage.N1


def test_un_arousal_del_edf_marca_su_epoca(tmp_path):
    ruta = edf_con(
        tmp_path, [(0, 90, "Sleep stage N2"), (35, 15, "Arousal (ARO SPONT)")]
    )

    scoring = read_scoring(ruta, 3)

    assert [scoring.get(i).arousal for i in range(3)] == [False, True, False]


def test_una_fase_sin_duracion_cuenta_como_una_epoca(tmp_path):
    """Algunos programas escriben así una anotación por época."""
    ruta = edf_con(tmp_path, [(0, 0, "Sleep stage N2"), (30, 0, "Sleep stage N3")])

    scoring = read_scoring(ruta, 2)

    assert [scoring.get(i).stage for i in range(2)] == [SleepStage.N2, SleepStage.N3]


def test_un_edf_sin_ninguna_fase_avisa(tmp_path):
    ruta = edf_con(tmp_path, [(0, 0, "Lights off")])

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 1)

    assert "ninguna fase" in str(fallo.value)


def test_un_rotulo_de_fase_desconocido_avisa_sin_cambiarle_mayusculas(tmp_path):
    ruta = edf_con(tmp_path, [(0, 30, "Sleep stage N4")])

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 1)

    assert "«Sleep stage N4»" in str(fallo.value)


def test_un_edf_roto_avisa(tmp_path):
    ruta = tmp_path / "roto.edf"
    ruta.write_bytes(b"esto no es un EDF")

    with pytest.raises(UnreadableFileError):
        read_scoring(ruta, 1)


def test_el_hipnograma_se_alinea_con_el_inicio_del_registro(tmp_path):
    """Si el hipnograma empieza un minuto después que la señal, su primera
    época es la tercera del registro."""
    ruta = edf_con(
        tmp_path,
        [(0, 30, "Sleep stage N2")],
        inicio=datetime(2020, 1, 2, 3, 5, 5),
    )

    scoring = read_scoring(ruta, 4, start_time=INICIO)

    assert [scoring.get(i).stage for i in range(4)] == [
        SleepStage.UNSCORED,
        SleepStage.UNSCORED,
        SleepStage.N2,
        SleepStage.UNSCORED,
    ]


def test_sin_fecha_en_alguno_de_los_dos_no_se_corre_nada(tmp_path):
    ruta = edf_con(tmp_path, [(0, 30, "Sleep stage N2")])

    assert read_scoring(ruta, 1, start_time=INICIO).get(0).stage is SleepStage.N2
    con_fecha = edf_con(
        tmp_path, [(0, 30, "Sleep stage N2")], inicio=datetime(2020, 1, 2, 5, 0, 0),
        nombre="otro.edf",
    )
    assert read_scoring(con_fecha, 1).get(0).stage is SleepStage.N2


def test_un_hipnograma_que_empieza_antes_que_la_senal_avisa(tmp_path):
    """Recortarlo cargaría la noche corrida sin avisar."""
    ruta = edf_con(
        tmp_path,
        [(0, 120, "Sleep stage N2")],
        inicio=datetime(2020, 1, 2, 3, 2, 5),
    )

    with pytest.raises(ScoringMismatchError):
        read_scoring(ruta, 4, start_time=INICIO)


# -- El XML de otro programa ---------------------------------------------------------


def test_un_xml_del_nsrr_sin_declaracion_pregunta(tmp_path):
    ruta = xml_con(
        tmp_path,
        [
            ("", "Recording Start Time", 0, 60),
            ("Stages|Stages", "Wake|0", 0, 30),
            ("Stages|Stages", "Stage 2 sleep|2", 30, 30),
            ("Respiratory|Respiratory", "Hypopnea|Hypopnea", 40, 12),
        ],
    )

    with pytest.raises(UndeclaredNomenclatureError):
        read_scoring(ruta, 2)
    assert read_scoring(ruta, 2, Nomenclature.AASM).get(1).stage is SleepStage.N2


def test_el_estadio_4_del_nsrr_decide_rk(tmp_path):
    ruta = xml_con(tmp_path, [("Stages|Stages", "Stage 4 sleep|4", 0, 30)])

    assert read_scoring(ruta, 1).get(0).stage is SleepStage.S4


def test_el_nsrr_escribe_9_para_lo_no_scoreado(tmp_path):
    ruta = xml_con(
        tmp_path,
        [("Stages|Stages", "Unscored|9", 0, 30), ("Stages|Stages", "REM sleep|5", 30, 30)],
        extra="<Nomenclature>Rechtschaffen y Kales</Nomenclature>",
    )

    scoring = read_scoring(ruta, 2)

    assert [scoring.get(i).stage for i in range(2)] == [SleepStage.UNSCORED, SleepStage.REM]


def test_un_evento_corrido_unos_segundos_cae_en_su_epoca(tmp_path):
    ruta = xml_con(
        tmp_path,
        [("Stages|Stages", "Wake|0", 0, 31.5), ("Stages|Stages", "REM sleep|5", 31.5, 30)],
        extra="<Nomenclature>AASM</Nomenclature>",
    )

    scoring = read_scoring(ruta, 2)

    assert [scoring.get(i).stage for i in range(2)] == [SleepStage.WAKE, SleepStage.R]


def test_los_arousals_del_nsrr_marcan_su_epoca(tmp_path):
    ruta = xml_con(
        tmp_path,
        [
            ("Stages|Stages", "Wake|0", 0, 60),
            ("Arousals|Arousals", "Arousal|Arousal (Standard)", 40, 10),
        ],
        extra="<Nomenclature>AASM</Nomenclature>",
    )

    scoring = read_scoring(ruta, 2)

    assert [scoring.get(i).arousal for i in range(2)] == [False, True]


def test_una_declaracion_que_el_contenido_contradice_avisa(tmp_path):
    ruta = xml_con(
        tmp_path,
        [("Stages|Stages", "Stage 4 sleep|4", 0, 30)],
        extra="<Nomenclature>AASM</Nomenclature>",
    )

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 1)

    assert "declara" in str(fallo.value)


def test_una_nomenclatura_declarada_que_no_existe_avisa(tmp_path):
    ruta = xml_con(
        tmp_path, [("Stages|Stages", "Wake|0", 0, 30)], extra="<Nomenclature>AASM 2</Nomenclature>"
    )

    with pytest.raises(UnreadableFileError):
        read_scoring(ruta, 1)


def test_un_xml_que_no_es_del_nsrr_avisa(tmp_path):
    ruta = tmp_path / "profusion.xml"
    ruta.write_text("<CMPStudyConfig><SleepStages/></CMPStudyConfig>", encoding="utf-8")

    with pytest.raises(UnreadableFileError) as fallo:
        read_scoring(ruta, 1)

    assert "NSRR" in str(fallo.value)


def test_un_xml_roto_avisa(tmp_path):
    ruta = tmp_path / "roto.xml"
    ruta.write_text("<PSGAnnotation><ScoredEvents>", encoding="utf-8")

    with pytest.raises(UnreadableFileError):
        read_scoring(ruta, 1)


@pytest.mark.parametrize("inicio", ["", "cero", "nan"])
def test_un_inicio_que_no_es_un_numero_avisa(tmp_path, inicio):
    ruta = xml_con(tmp_path, [("Stages|Stages", "Wake|0", inicio, 30)])  # type: ignore[list-item]

    with pytest.raises(UnreadableFileError):
        read_scoring(ruta, 1)


def test_un_concepto_sin_numero_avisa(tmp_path):
    ruta = xml_con(tmp_path, [("Stages|Stages", "Wake", 0, 30)])

    with pytest.raises(UnreadableFileError):
        read_scoring(ruta, 1)


# -- La puerta -----------------------------------------------------------------------


def test_el_lector_de_formatos_no_lee_txt(tmp_path):
    """El `.txt` lo lee `scoring_reader`: llegar acá con uno es un error de
    despacho, y tiene que decirlo en vez de leerlo mal."""
    ruta = tmp_path / "Scoring.txt"
    ruta.write_text("# AASM\n0 0\n", encoding="utf-8")

    with pytest.raises(UnreadableFileError):
        read_scoring_file(ruta, 1)


def test_la_nomenclatura_se_puede_declarar_con_el_nombre_corto_o_el_largo():
    for nomenclatura in Nomenclature:
        assert NOMENCLATURE_NAMES[nomenclatura.name.lower()] is nomenclatura
        assert NOMENCLATURE_NAMES[nomenclatura.value.lower()] is nomenclatura


def test_la_pregunta_es_un_error_de_lectura():
    """Quien atrapaba `UnreadableFileError` lo sigue atrapando."""
    assert issubclass(UndeclaredNomenclatureError, UnreadableFileError)
