"""Tests del formato exacto de los archivos de salida.

Los tres archivos son la salida real del trabajo del laboratorio: alimentan
los análisis estadísticos posteriores. Un cambio silencioso de formato rompe
scripts río abajo sin que nadie se entere hasta mucho después, así que el
formato se fija acá.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
import psglab.exporters.statistics as stats
from psglab.exporters.annotations_txt import export_annotations
from psglab.exporters.information_txt import (
    build_report,
    export_information,
    format_duration,
)
from psglab.exporters.scoring_txt import export_scoring, format_header, format_line
from psglab.core.windows import count_windows
from psglab.readers.base import read_recording
from psglab.readers.scoring_reader import read_scoring
from psglab.utils.errors import PsgLabError

RAIZ = Path(__file__).resolve().parent.parent
EDF_REAL = RAIZ / "data" / "SC4001E0-PSG.edf"

necesita_edf = pytest.mark.skipif(
    not EDF_REAL.exists(),
    reason=(
        "hace falta el registro de prueba de data/, que el .gitignore excluye porque "
        "son datos de participantes. Ver el hito 0 de docs/TODO.md para bajarlos."
    ),
)


def registro(n_ventanas_completas: int = 3, cola_segundos: float = 10.0) -> Recording:
    """Un registro cuya **última ventana está incompleta**, que es el caso real.

    Casi ningún registro termina justo en el borde de una ventana de 30 s, y esa
    cola es la que distingue las dos medidas de tiempo del módulo.
    """
    fs = 100.0
    muestras = int((n_ventanas_completas * 30 + cola_segundos) * fs)
    return Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0, original_sampling_rate=fs)],
        data=np.zeros((1, muestras)),
        sampling_rate=fs,
    )


def scoring_de_ejemplo() -> Scoring:
    """Cuatro ventanas: W, N2, N2, N3. La de N3 es la incompleta."""
    scoring = Scoring(n_windows=4, nomenclature=Nomenclature.AASM)
    for indice, fase in enumerate(
        [SleepStage.WAKE, SleepStage.N2, SleepStage.N2, SleepStage.N3]
    ):
        scoring.set_stage(indice, fase)
    return scoring


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

    La cabecera va explícita en `False`, como el número de ventana: con
    `config.SCORING_INCLUDES_NOMENCLATURE_HEADER` en `True`, que es el valor de
    hoy, un archivo de 20 ventanas tiene 21 líneas y este test contaría la
    cabecera como si fuera una ventana. Lo que se verifica acá es que no falte
    ninguna ventana, no cómo está configurado el formato.
    """
    scoring = Scoring(n_windows=20, nomenclature=Nomenclature.AASM)
    scoring.set_stage(0, SleepStage.WAKE)
    destino = tmp_path / "Scoring.txt"
    export_scoring(scoring, destino, include_header=False)
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
    # Las dos constantes de formato van explícitas: este test mira el primer
    # campo de cada línea, así que sólo tiene sentido sin el número de ventana
    # adelante y sin la cabecera arriba. Si dependiera de los valores de
    # `config`, fallaría cuando alguno cambiara, y por un motivo que no es el
    # que este test verifica. Con la cabecera puesta, la primera línea sería
    # "# AASM" y el primer campo, "#".
    export_scoring(scoring, destino, include_window_number=False, include_header=False)
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


# -- Las dos medidas de tiempo, que no miden lo mismo ------------------------


def test_la_tabla_por_fase_suma_la_duracion_real_del_registro():
    """**El test que justifica el cambio de firma del hito.**

    La última ventana casi siempre está incompleta. Multiplicar la cuenta de
    ventanas por 30 le atribuiría a su fase hasta medio minuto que el registro
    no tiene, y ese número se publica en `Informacion.txt`.
    """
    reg, scoring = registro(), scoring_de_ejemplo()
    duraciones = stats.stage_durations_seconds(scoring, reg.n_samples, reg.sampling_rate)
    assert sum(duraciones.values()) == pytest.approx(reg.duration_seconds)
    # La ventana incompleta aporta 10 s, no 30.
    assert duraciones[SleepStage.N3] == pytest.approx(10.0)


def test_el_tiempo_abarcado_cuenta_ventanas_completas_a_proposito():
    """No es un error de redondeo: es otra magnitud.

    `scored_time_seconds()` mide cuánto abarca la grilla de ventanas, y
    `Recording.duration_seconds` cuánto dura el registro. Forzarlas a coincidir
    falsificaría una de las dos, y el informe publica las dos rotuladas
    distinto.
    """
    reg, scoring = registro(), scoring_de_ejemplo()
    assert stats.scored_time_seconds(scoring) == 120.0
    assert reg.duration_seconds == 100.0


def test_las_fases_ausentes_aparecen_en_cero_y_no_desaparecen():
    """Una fila en cero dice que esa noche no tuvo N1, que es información."""
    cuentas = stats.stage_window_counts(scoring_de_ejemplo())
    assert cuentas[SleepStage.N1] == 0
    assert cuentas[SleepStage.N2] == 2


def test_la_fila_de_sin_scorear_aparece_solo_si_hace_falta():
    """En un registro terminado esa fila sobra; en uno a medias es lo que falta."""
    assert SleepStage.UNSCORED not in stats.stage_window_counts(scoring_de_ejemplo())

    a_medias = Scoring(n_windows=3, nomenclature=Nomenclature.AASM)
    a_medias.set_stage(0, SleepStage.WAKE)
    assert stats.stage_window_counts(a_medias)[SleepStage.UNSCORED] == 2


# -- Episodios ---------------------------------------------------------------


def test_los_episodios_agrupan_ventanas_seguidas_de_la_misma_fase():
    """Dos ventanas de N2 seguidas son **un** episodio de dos, no dos de una."""
    episodios = stats.stage_episodes(scoring_de_ejemplo())
    assert episodios[SleepStage.N2] == [2]
    assert episodios[SleepStage.WAKE] == [1]


def test_la_misma_fase_en_dos_tramos_separados_son_dos_episodios():
    """Es lo que distingue una noche fragmentada de una consolidada."""
    scoring = Scoring(n_windows=5, nomenclature=Nomenclature.AASM)
    for indice, fase in enumerate(
        [SleepStage.N2, SleepStage.WAKE, SleepStage.N2, SleepStage.N2, SleepStage.N2]
    ):
        scoring.set_stage(indice, fase)
    assert stats.stage_episodes(scoring)[SleepStage.N2] == [1, 3]


def test_las_metricas_se_calculan_sobre_episodios_y_no_sobre_ventanas():
    """Sobre ventanas sueltas el desvío daría cero: todas duran lo mismo.

    Es el motivo por el que `stage_episodes()` existe.
    """
    metricas = stats.episode_metrics([2, 4])
    assert metricas["promedio"] == pytest.approx(90.0)
    assert metricas["mediana"] == pytest.approx(90.0)
    assert metricas["desvio"] > 0


def test_con_un_solo_episodio_el_desvio_es_cero_y_no_un_error():
    """No está indefinido por un problema de cálculo: no hay dispersión."""
    assert stats.episode_metrics([3])["desvio"] == 0.0


def test_sin_episodios_las_metricas_son_cero():
    assert stats.episode_metrics([]) == {"promedio": 0.0, "desvio": 0.0, "mediana": 0.0}


# -- Resumen de anotaciones --------------------------------------------------


def test_el_resumen_de_anotaciones_agrupa_por_clase():
    anotaciones = AnnotationSet()
    anotaciones.add(Annotation("Arousal", 0, 100))
    anotaciones.add(Annotation("Arousal", 500, 300))
    anotaciones.add(Annotation("Spindle", 200, 50))

    resumen = stats.annotation_summary(anotaciones, sampling_rate=100.0)
    assert resumen["Arousal"]["cantidad"] == 2
    assert resumen["Arousal"]["duracion_promedio"] == pytest.approx(2.0)
    assert resumen["Spindle"]["cantidad"] == 1


def test_una_frecuencia_que_no_sirve_no_divide_por_cero():
    """Las anotaciones se guardan en muestras: la frecuencia es lo único que las
    convierte a tiempo, y una corrupta tiene que salir como error del programa."""
    with pytest.raises(PsgLabError):
        stats.annotation_summary(AnnotationSet(), sampling_rate=0.0)


# -- Informacion.txt ---------------------------------------------------------


@pytest.mark.parametrize(
    ("segundos", "esperado"),
    [
        (3661.5, "1 h 01 min 01,50 s"),
        (0.0, "0 h 00 min 00,00 s"),
        (100.0, "0 h 01 min 40,00 s"),
    ],
)
def test_format_duration_sigue_el_ejemplo_de_su_docstring(segundos, esperado):
    """Coma decimal y segundos con cero adelante, como los minutos."""
    assert format_duration(segundos) == esperado


def test_el_informe_siempre_trae_la_frecuencia_de_muestreo():
    """**No es un dato decorativo.**

    `Anotaciones.txt` guarda posiciones en muestras y no lleva la frecuencia;
    éste es el único archivo que la registra. Sin ella, aquél no se puede
    interpretar.
    """
    for scoring in (None, scoring_de_ejemplo()):
        assert "Frecuencia de muestreo" in build_report(registro(), scoring, None)


def test_el_informe_publica_las_dos_medidas_de_tiempo():
    """Rotuladas distinto, para que nadie las lea como si se contradijeran."""
    informe = build_report(registro(), scoring_de_ejemplo(), None)
    assert "Duración del registro" in informe
    assert "Tiempo abarcado por las ventanas" in informe


def test_un_registro_sin_scorear_lo_dice_en_vez_de_mostrar_ceros():
    """Una tabla de "0,00 s" se confunde con un registro scoreado sin ninguna
    ventana en esa fase. Un texto que lo explica, no."""
    informe = build_report(registro(), None, None)
    assert "no está scoreado" in informe
    assert "Tiempo en cada fase" not in informe


def test_un_registro_sin_anotaciones_lo_dice():
    informe = build_report(registro(), scoring_de_ejemplo(), AnnotationSet())
    assert "no tiene anotaciones" in informe


def test_el_informe_avisa_cuando_un_canal_venia_a_otra_frecuencia():
    """MNE sobremuestrea los canales lentos del EDF sin avisar.

    Callarlo haría que un canal de 1 Hz se leyera como si tuviera la misma
    resolución que el EEG.
    """
    base = registro()
    reg = Recording(
        base.file_path,
        [
            Channel("C3", ChannelKind.EEG, "µV", 0, original_sampling_rate=100.0),
            Channel("EMG", ChannelKind.EMG, "µV", 1, original_sampling_rate=1.0),
        ],
        np.zeros((2, base.n_samples)),
        base.sampling_rate,
    )
    assert "original 1,0 Hz" in build_report(reg, None, None)


def test_el_informe_se_escribe_al_disco(tmp_path):
    destino = tmp_path / "Informacion.txt"
    export_information(registro(), scoring_de_ejemplo(), None, destino)
    assert destino.read_text(encoding="utf-8") == build_report(
        registro(), scoring_de_ejemplo(), None
    )


# -- El contrato con el hito 4 -----------------------------------------------


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_la_cabecera_que_se_escribe_es_la_que_el_lector_sabe_leer(
    tmp_path, nomenclatura: Nomenclature
):
    """**Ida y vuelta entre dos hitos**, del tipo que se rompe en silencio.

    Se exporta un scoring, se lo relee **sin decirle la nomenclatura**, y tiene
    que salir la misma. Si no, un archivo exportado en AASM se reimportaría como
    Rechtschaffen y Kales y la noche entera quedaría mal traducida sin ningún
    error visible: el código 2 es S2 en una y N2 en la otra.
    """
    scoring = Scoring(n_windows=3, nomenclature=nomenclatura)
    destino = tmp_path / "Scoring.txt"
    # La cabecera va explícita: lo que este test verifica es que el lector la
    # entienda, no cómo está configurado el formato. Dependiendo de
    # `config.SCORING_INCLUDES_NOMENCLATURE_HEADER` fallaría al revertir esa
    # decisión, y por un motivo que no es el que persigue.
    export_scoring(scoring, destino, include_header=True)

    releido = read_scoring(destino, n_windows=3)
    assert releido.nomenclature is nomenclatura


def test_lo_que_se_exporta_se_vuelve_a_leer_igual(tmp_path):
    """No alcanza con que la nomenclatura sobreviva: las fases también."""
    scoring = scoring_de_ejemplo()
    destino = tmp_path / "Scoring.txt"
    export_scoring(scoring, destino, include_header=True)

    releido = read_scoring(destino, n_windows=scoring.n_windows)
    assert releido.stages() == scoring.stages()


def test_el_arousal_tambien_sobrevive_la_ida_y_vuelta(tmp_path):
    scoring = scoring_de_ejemplo()
    scoring.set_arousal(1, True)
    destino = tmp_path / "Scoring.txt"
    export_scoring(scoring, destino, include_header=True)

    releido = read_scoring(destino, n_windows=scoring.n_windows)
    assert releido.get(1).arousal is True
    assert releido.get(0).arousal is False


def test_la_cabecera_se_puede_sacar_cambiando_una_constante(tmp_path):
    """El formato tiene que seguir siendo alcanzable desde `config`.

    Un `if` que diera por sentada una variante rompería esa propiedad aunque hoy
    acierte, y revertir la decisión del hito 0 dejaría de ser cambiar una línea.
    """
    scoring = Scoring(n_windows=2, nomenclature=Nomenclature.AASM)
    con = tmp_path / "con.txt"
    sin = tmp_path / "sin.txt"
    export_scoring(scoring, con, include_header=True)
    export_scoring(scoring, sin, include_header=False)

    assert con.read_text(encoding="utf-8").startswith(format_header(Nomenclature.AASM))
    assert not sin.read_text(encoding="utf-8").startswith("#")
    assert len(sin.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_el_numero_de_ventana_tambien_se_puede_agregar(tmp_path):
    """La otra variante que el hito 0 dejó configurable."""
    scoring = Scoring(n_windows=2, nomenclature=Nomenclature.AASM)
    destino = tmp_path / "Scoring.txt"
    export_scoring(scoring, destino, include_window_number=True, include_header=False)

    primera = destino.read_text(encoding="utf-8").splitlines()[0]
    # Base 1: la primera ventana es la 1, no la 0.
    assert primera.split()[0] == "1"


# -- El corte del hito: de punta a punta, sin interfaz -----------------------


@necesita_edf
def test_el_programa_hace_su_trabajo_entero_desde_un_script(tmp_path):
    """**Es el corte que el hito 5 promete**, y por eso vale un test y no un
    script suelto que nadie ejecuta.

    Leer un EDF real, scorear, exportar los tres archivos del pliego y volver a
    leer el scoring. Todo sin abrir una ventana: es el pago concreto de que
    `core/` no importe `ui/`.
    """
    grabacion = read_recording(EDF_REAL)
    n_ventanas = count_windows(grabacion.n_samples, grabacion.sampling_rate)

    scoring = Scoring(n_windows=n_ventanas, nomenclature=Nomenclature.AASM)
    for indice, fase in enumerate([SleepStage.WAKE, SleepStage.N1, SleepStage.N2]):
        scoring.set_stage(indice, fase)
    scoring.set_arousal(2, True)

    anotaciones = AnnotationSet()
    anotaciones.add(Annotation("Arousal", onset_sample=7680, duration_samples=512))

    salida_scoring = tmp_path / "Scoring.txt"
    salida_anotaciones = tmp_path / "Anotaciones.txt"
    salida_informacion = tmp_path / "Informacion.txt"
    export_scoring(scoring, salida_scoring)
    export_annotations(anotaciones, salida_anotaciones)
    export_information(grabacion, scoring, anotaciones, salida_informacion)

    # Los tres existen y ninguno quedó vacío.
    for salida in (salida_scoring, salida_anotaciones, salida_informacion):
        assert salida.read_text(encoding="utf-8").strip()

    # El scoring vuelve igual sin decirle la nomenclatura.
    # Se pasa la nomenclatura porque este test corre con los valores de
    # `config`, sean los que sean: si la cabecera está activada, gana ella. El
    # contrato de la cabecera lo fijan los tres tests de más arriba.
    releido = read_scoring(
        salida_scoring, n_windows=n_ventanas, nomenclature=scoring.nomenclature
    )
    assert releido.nomenclature is Nomenclature.AASM
    assert releido.stages()[:3] == [SleepStage.WAKE, SleepStage.N1, SleepStage.N2]
    assert releido.get(2).arousal is True

    # Y el informe nombra el archivo del que salió todo.
    assert EDF_REAL.name in salida_informacion.read_text(encoding="utf-8")
