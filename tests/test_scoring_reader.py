"""Tests de la importación de un scoring ya existente.

El pliego (V3_F) pide poder abrir una señal ya scoreada para retomar un trabajo
interrumpido o revisar el de otra persona.

**El test que más importa es el de la nomenclatura.** Los códigos de fase no son
únicos entre sistemas: `2` es S2 en Rechtschaffen y Kales y N2 en AASM, igual
que `1`, `3` y `5`. Leer un archivo con la nomenclatura equivocada carga la
noche entera mal traducida **sin ningún error visible**: el histograma se dibuja,
las estadísticas salen, y todo está mal. Por eso el lector no adivina nunca, y
por eso acá se verifica que prefiera fallar.

Los archivos los escribe el propio test en `tmp_path`, así que no necesita nada
de `data/` y corre en cualquier lado, incluido el CI.
"""

from pathlib import Path

import pytest

from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.scoring import Scoring
from psglab.readers.scoring_reader import (
    detect_line_format,
    detect_nomenclature,
    read_scoring,
)
from psglab.utils.errors import (
    PsgLabError,
    ScoringMismatchError,
    UnreadableFileError,
)


@pytest.fixture
def escribir(tmp_path: Path):
    """Deja un archivo de scoring en disco y devuelve su ruta."""

    def escribir_archivo(contenido: str, nombre: str = "Scoring.txt") -> Path:
        destino = tmp_path / nombre
        destino.write_text(contenido, encoding="utf-8")
        return destino

    return escribir_archivo


# -- El formato nativo -------------------------------------------------------


def test_el_formato_de_dos_campos_se_lee_entero(escribir):
    """Es el que produce el programa: cabecera y una línea por ventana."""
    archivo = escribir("# AASM\n0 0\n2 1\n3 0\n")
    scoring = read_scoring(archivo, 3)

    assert scoring.get(0).stage is SleepStage.WAKE
    assert scoring.get(1).stage is SleepStage.N2
    assert scoring.get(2).stage is SleepStage.N3


def test_el_arousal_se_lee_por_separado_de_la_fase(escribir):
    archivo = escribir("# AASM\n2 1\n2 0\n")
    scoring = read_scoring(archivo, 2)

    assert scoring.get(0).arousal is True
    assert scoring.get(1).arousal is False


def test_el_numero_de_ventana_queda_implicito_en_el_orden(escribir):
    """Con dos campos, la posición de la línea **es** el número de ventana."""
    archivo = escribir("# RK\n0 0\n5 0\n2 0\n")
    scoring = read_scoring(archivo, 3)

    assert [scoring.get(i).stage for i in range(3)] == [
        SleepStage.WAKE,
        SleepStage.REM,
        SleepStage.S2,
    ]


def test_la_variante_de_tres_campos_tambien_se_acepta(escribir):
    """El pliego describe tres campos y su ejemplo muestra dos.

    Se eligió dos, pero leer las dos variantes no cuesta nada y un archivo de
    tres campos sigue siendo legible sin ambigüedad.
    """
    archivo = escribir("# RK\n1 0 0\n2 2 1\n3 5 0\n")
    assert detect_line_format(archivo) is True

    scoring = read_scoring(archivo, 3)
    assert [scoring.get(i).stage for i in range(3)] == [
        SleepStage.WAKE,
        SleepStage.S2,
        SleepStage.REM,
    ]


def test_el_numero_de_ventana_del_archivo_es_base_1(escribir):
    """Adentro del programa las ventanas son base 0 y al exportarlas base 1.

    Un archivo que dice "1" habla de la primera ventana, que adentro es la 0.
    Equivocarse acá corre el scoring entero una ventana.
    """
    archivo = escribir("# AASM\n1 2 0\n")
    scoring = read_scoring(archivo, 3)

    assert scoring.get(0).stage is SleepStage.N2
    assert scoring.get(1).stage is SleepStage.UNSCORED


def test_detect_line_format_sobre_el_formato_de_dos_campos(escribir):
    assert detect_line_format(escribir("# AASM\n0 0\n")) is False


# -- La nomenclatura, que es lo que no se puede adivinar ---------------------


@pytest.mark.parametrize(
    ("cabecera", "esperada"),
    [
        ("# AASM", Nomenclature.AASM),
        ("# aasm", Nomenclature.AASM),
        ("# RK", Nomenclature.RK),
        ("# rk", Nomenclature.RK),
        ("# Rechtschaffen y Kales", Nomenclature.RK),
    ],
)
def test_la_cabecera_se_reconoce_por_el_nombre_corto_y_el_largo(
    escribir, cabecera: str, esperada: Nomenclature
):
    """El archivo lo puede haber escrito una persona, no sólo el programa."""
    assert detect_nomenclature(escribir(f"{cabecera}\n0 0\n")) is esperada


def test_sin_cabecera_no_es_un_error_sino_una_ausencia(escribir):
    """Un archivo escrito a mano o por una versión anterior es válido.

    Sólo hay que decirle al lector con qué nomenclatura interpretarlo.
    """
    assert detect_nomenclature(escribir("0 0\n2 0\n")) is None


def test_el_mismo_codigo_es_una_fase_distinta_en_cada_nomenclatura(escribir):
    """La razón de ser de la cabecera, en un solo test.

    El mismo archivo, leído con una nomenclatura y con la otra, da fases
    distintas. Por eso el lector nunca adivina.
    """
    contenido = "2 0\n"
    en_rk = read_scoring(escribir(contenido, "rk.txt"), 1, Nomenclature.RK)
    en_aasm = read_scoring(escribir(contenido, "aasm.txt"), 1, Nomenclature.AASM)

    assert en_rk.get(0).stage is SleepStage.S2
    assert en_aasm.get(0).stage is SleepStage.N2


def test_la_cabecera_del_archivo_gana_sobre_el_parametro(escribir):
    """El archivo sabe mejor que quien lo abre con qué se escribió."""
    archivo = escribir("# AASM\n2 0\n")
    scoring = read_scoring(archivo, 1, nomenclature=Nomenclature.RK)

    assert scoring.get(0).stage is SleepStage.N2


def test_sin_cabecera_y_sin_parametro_falla_en_vez_de_adivinar(escribir):
    """Adivinar cargaría la noche entera mal traducida sin que se note.

    Es la peor forma de fallar que tiene este módulo, y por eso no falla así.
    """
    with pytest.raises(UnreadableFileError) as excepcion:
        read_scoring(escribir("0 0\n2 0\n"), 2)
    assert "nomenclatura" in str(excepcion.value).lower()


def test_sin_cabecera_el_parametro_alcanza(escribir):
    scoring = read_scoring(escribir("0 0\n2 0\n"), 2, Nomenclature.RK)
    assert scoring.get(1).stage is SleepStage.S2


def test_la_cabecera_se_deja_de_buscar_en_la_primera_linea_de_datos(escribir):
    """Un comentario a mitad del archivo no puede cambiar lo ya leído.

    Si se siguiera buscando, las líneas de más arriba habrían quedado
    interpretadas con una nomenclatura y las de abajo con otra, dentro del mismo
    scoring y sin ningún aviso.
    """
    archivo = escribir("0 0\n# AASM\n2 0\n")
    assert detect_nomenclature(archivo) is None


# -- Lo que el archivo no dice ----------------------------------------------


def test_las_ventanas_ausentes_quedan_sin_scorear(escribir):
    """Un scoring parcial es un caso de uso, no un archivo roto: es alguien que
    dejó el trabajo por la mitad y lo va a retomar."""
    scoring = read_scoring(escribir("# AASM\n2 0\n2 0\n"), 5)

    assert scoring.get(1).stage is SleepStage.N2
    for ventana in (2, 3, 4):
        assert scoring.get(ventana).stage is SleepStage.UNSCORED


def test_el_codigo_menos_uno_es_una_ventana_sin_scorear(escribir):
    """Se eligió -1 porque no puede confundirse con ninguna fase real: todas
    son 0 o positivas."""
    scoring = read_scoring(escribir("# AASM\n-1 0\n2 0\n"), 2)

    assert scoring.get(0).stage is SleepStage.UNSCORED
    assert scoring.get(1).stage is SleepStage.N2


def test_un_archivo_vacio_da_un_scoring_entero_sin_scorear(escribir):
    scoring = read_scoring(escribir("# AASM\n"), 3)
    assert scoring.scored_windows() == 0


# -- Los errores -------------------------------------------------------------


def test_un_scoring_mas_largo_que_el_registro_se_rechaza(escribir):
    """Es el caso de abrir el scoring de **otra** noche.

    Sin este control quedarían fases asignadas a ventanas que no existen.
    """
    with pytest.raises(ScoringMismatchError):
        read_scoring(escribir("# AASM\n0 0\n2 0\n2 0\n"), 2)


def test_una_linea_con_menos_campos_de_los_esperados(escribir):
    with pytest.raises(UnreadableFileError) as excepcion:
        read_scoring(escribir("# AASM\n0 0\n2\n"), 2)
    assert "3" in str(excepcion.value)  # nombra la línea, no sólo el archivo


def test_una_linea_que_no_son_numeros(escribir):
    with pytest.raises(UnreadableFileError) as excepcion:
        read_scoring(escribir("# AASM\n0 0\nhola chau\n"), 2)
    assert "3" in str(excepcion.value)


def test_un_codigo_que_la_nomenclatura_no_tiene(escribir):
    """`4` es S4, que existe en R&K y no en AASM.

    Traducirlo a cualquier cosa sería peor que rechazarlo.
    """
    with pytest.raises(UnreadableFileError):
        read_scoring(escribir("# AASM\n4 0\n"), 1)


def test_el_mismo_codigo_si_vale_en_la_otra_nomenclatura(escribir):
    """El complemento del anterior: el rechazo tiene que ser por nomenclatura y
    no porque el lector no sepa leer un 4."""
    scoring = read_scoring(escribir("# RK\n4 0\n"), 1)
    assert scoring.get(0).stage is SleepStage.S4


def test_un_archivo_que_no_existe(tmp_path: Path):
    with pytest.raises(UnreadableFileError):
        read_scoring(tmp_path / "no_esta.txt", 1)


def test_todo_lo_que_eleva_hereda_de_la_base_del_programa(escribir):
    """La ventana principal atrapa una sola clase.

    Cualquier cosa que escape de `PsgLabError` llega al investigador como una
    traza de Python.
    """
    casos = [
        lambda: read_scoring(escribir("0 0\n"), 1),
        lambda: read_scoring(escribir("# AASM\n0 0\n0 0\n"), 1),
        lambda: read_scoring(escribir("# AASM\nhola\n"), 1),
        lambda: read_scoring(escribir("# AASM\n9 0\n"), 1),
    ]
    for caso in casos:
        with pytest.raises(PsgLabError):
            caso()


# -- Ida y vuelta con el exportador -----------------------------------------


def test_lo_que_este_lector_espera_es_lo_que_el_exportador_va_a_escribir(escribir):
    """Contrato entre dos hitos, fijado desde el lado que ya existe.

    `exporters/scoring_txt.py::format_header()` es un stub del hito 5, y cuando
    se escriba tiene que producir exactamente esta cabecera. El test de ida y
    vuelta de verdad —exportar y releer— es del hito 5 y está anotado ahí; éste
    fija la mitad que ya se puede fijar.
    """
    for nomenclatura in Nomenclature:
        archivo = escribir(f"# {nomenclatura.name}\n0 0\n", f"{nomenclatura.name}.txt")
        assert detect_nomenclature(archivo) is nomenclatura


def test_un_scoring_leido_se_puede_seguir_editando(escribir):
    """Lo que se importa tiene que ser un `Scoring` normal, no uno de sólo
    lectura: el caso de uso es **corregir** el trabajo de otra persona."""
    scoring = read_scoring(escribir("# AASM\n2 0\n2 0\n"), 2)
    assert isinstance(scoring, Scoring)

    scoring.set_stage(0, SleepStage.N3)
    assert scoring.get(0).stage is SleepStage.N3
