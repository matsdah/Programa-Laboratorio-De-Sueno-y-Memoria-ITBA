"""Tests del control de impedancia.

**Todo este archivo gira alrededor de una distinción**: "no medido" no es
"0 kΩ". Un electrodo suelto que nadie midió es el caso peligroso, porque si
apareciera como cero pasaría por perfecto — y cero es el mejor valor posible.

De ahí salen las afirmaciones que más importan:

- `read_impedances()` **omite** los canales sin dato en vez de darles un número.
- El informe distingue **tres** estados y no dos.
- Un `???` en el `.vhdr` no llega como cero: no llega.

Lo demás es aritmética exacta sobre diccionarios y parseo de un archivo de
texto, así que se afirma sin tolerancias.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.impedance import (
    COMMENT_PREFIX,
    DEFAULT_LIMIT_KOHM,
    METADATA_KEY,
    channels_above_limit,
    impedance_report,
    load_impedances_from_file,
    read_impedances,
)
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.readers.base import read_recording
from psglab.utils.errors import (
    InvalidRecordingError,
    PsgLabError,
    UnreadableFileError,
)
from psglab.utils.units import MICROVOLT

from conftest import escribir_brainvision


def registro(metadata: dict | None = None) -> Recording:
    """Tres canales, con los metadatos que se le pasen."""
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=[
            Channel(nombre, ChannelKind.EEG, MICROVOLT, posicion)
            for posicion, nombre in enumerate(["C3", "C4", "O1"])
        ],
        data=np.zeros((3, 1000)),
        sampling_rate=100.0,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
        metadata=metadata or {},
    )


# -- Leer del registro -------------------------------------------------------


def test_lee_lo_que_dejo_el_lector():
    reg = registro({METADATA_KEY: {"C3": 4.2, "C4": 12.5}})

    assert read_impedances(reg) == {"C3": 4.2, "C4": 12.5}


def test_un_registro_sin_impedancias_da_un_diccionario_vacio():
    """**Es el caso de todo EDF**, y no es un fallo: el estándar no tiene
    ningún campo de impedancia, ni siquiera en EDF+."""
    assert read_impedances(registro()) == {}


def test_los_canales_que_el_registro_no_tiene_se_descartan():
    """El `.vhdr` incluye `Ref` y `Gnd`, que no son canales del registro.
    Dejarlos haría que el informe hablara de canales que el usuario no ve."""
    reg = registro({METADATA_KEY: {"C3": 4.2, "Ref": 0.0, "Gnd": 4.0}})

    assert read_impedances(reg) == {"C3": 4.2}


def test_un_nan_no_llega_como_cero():
    """**La distinción que sostiene el módulo.** MNE entrega los `???` del
    `.vhdr` como `nan`, y un cero pasaría por el mejor valor posible."""
    reg = registro({METADATA_KEY: {"C3": 4.2, "O1": float("nan")}})

    leidas = read_impedances(reg)
    assert "O1" not in leidas
    assert leidas == {"C3": 4.2}


# -- El viaje completo desde el archivo --------------------------------------


def test_un_brainvision_con_impedancias_llega_hasta_el_modulo(tmp_path: Path):
    """**BrainVision sí las trae**: el `.vhdr` tiene una tabla
    `Impedance [kOhm]` en su sección `[Comment]`, ya en kΩ."""
    vhdr = escribir_brainvision(
        tmp_path / "con_imp",
        segundos=10,
        canales=[("C3", "µV"), ("C4", "µV"), ("O1", "µV")],
        impedancias={"C3": 4.2, "C4": 12.5, "O1": None},
    )

    leidas = read_impedances(read_recording(vhdr))

    assert leidas == {"C3": 4.2, "C4": 12.5}


def test_el_que_estaba_sin_medir_no_aparece(tmp_path: Path):
    """`???` en el archivo, ausente en el resultado. Si apareciera como 0 el
    electrodo suelto pasaría por perfecto."""
    vhdr = escribir_brainvision(
        tmp_path / "sin_medir",
        segundos=10,
        canales=[("C3", "µV"), ("O1", "µV")],
        impedancias={"C3": 4.2, "O1": None},
    )

    assert "O1" not in read_impedances(read_recording(vhdr))


def test_un_brainvision_sin_tabla_de_impedancias_no_rompe(tmp_path: Path):
    vhdr = escribir_brainvision(tmp_path / "sin_tabla", segundos=10)

    assert read_impedances(read_recording(vhdr)) == {}


# -- El archivo aparte -------------------------------------------------------


def escribir(tmp_path: Path, texto: str) -> Path:
    destino = tmp_path / "impedancias.txt"
    destino.write_text(texto, encoding="utf-8")
    return destino


def test_lee_canal_y_valor(tmp_path: Path):
    archivo = escribir(tmp_path, "C3 4.2\nC4 3.8\n")

    assert load_impedances_from_file(archivo) == {"C3": 4.2, "C4": 3.8}


def test_los_comentarios_y_las_lineas_vacias_se_ignoran(tmp_path: Path):
    archivo = escribir(
        tmp_path, f"{COMMENT_PREFIX} medido el 8/9\n\nC3 4.2\n\n{COMMENT_PREFIX} fin\n"
    )

    assert load_impedances_from_file(archivo) == {"C3": 4.2}


def test_sin_unidad_se_asumen_kiloohmios(tmp_path: Path):
    """Es lo que declara el equipo y lo que usa todo el módulo."""
    assert load_impedances_from_file(escribir(tmp_path, "C3 4.2\n")) == {"C3": 4.2}


def test_la_unidad_se_respeta_cuando_esta(tmp_path: Path):
    """**El error de mil veces.** Leer 12000 ohmios como kiloohmios daría 12000
    y todos los canales fallarían; al revés, ninguno fallaría nunca."""
    archivo = escribir(tmp_path, "C3 4.2 kOhm\nO1 12000 Ohm\n")

    assert load_impedances_from_file(archivo) == {"C3": 4.2, "O1": 12.0}


def test_la_coma_decimal_tambien_entra(tmp_path: Path):
    """El programa está en español y alguien va a escribir 4,2."""
    assert load_impedances_from_file(escribir(tmp_path, "C3 4,2\n")) == {"C3": 4.2}


def test_un_archivo_vacio_da_un_diccionario_vacio(tmp_path: Path):
    assert load_impedances_from_file(escribir(tmp_path, "")) == {}


@pytest.mark.parametrize(
    "linea", ["C3\n", "C3 4.2 kOhm demas\n", "C3 cuatro\n", "C3 -1\n", "C3 4.2 megas\n"]
)
def test_una_linea_mal_formada_se_rechaza_nombrandola(tmp_path: Path, linea: str):
    """**"La línea 47 no se entiende" es accionable y "el archivo está mal" no.**
    Es el criterio que fijó `scoring_reader.py`."""
    archivo = escribir(tmp_path, f"C3 4.2\n{linea}")

    with pytest.raises(UnreadableFileError) as fallo:
        load_impedances_from_file(archivo)
    assert "2" in str(fallo.value)


def test_un_archivo_que_no_existe_se_rechaza(tmp_path: Path):
    with pytest.raises(UnreadableFileError):
        load_impedances_from_file(tmp_path / "no_existe.txt")


# -- El límite ---------------------------------------------------------------


def test_informa_los_que_superan_el_limite():
    assert channels_above_limit({"C3": 4.2, "C4": 12.5, "O1": 8.0}) == ["C4", "O1"]


def test_el_limite_es_inclusivo():
    """**Exactamente 5 kΩ con un límite de 5 kΩ pasa.** El límite es el máximo
    aceptable, no el primer valor rechazado, que es como lo lee cualquiera que
    escriba "impedancia menor a 5"."""
    assert channels_above_limit({"C3": DEFAULT_LIMIT_KOHM}) == []
    assert channels_above_limit({"C3": DEFAULT_LIMIT_KOHM + 0.1}) == ["C3"]


def test_se_puede_cambiar_el_limite():
    assert channels_above_limit({"C3": 4.2}, limit_kohm=3.0) == ["C3"]


def test_un_canal_sin_medir_no_figura_entre_los_que_superan():
    """No está en el diccionario, así que no puede superar nada. **Tampoco
    quiere decir que esté bien**: para eso está el informe."""
    assert channels_above_limit({"C3": 4.2}) == []


# -- El informe, y sus tres estados ------------------------------------------


def test_el_informe_nombra_los_que_superan():
    texto = impedance_report({"C3": 4.2, "C4": 12.5})

    assert "C4" in texto
    assert "12,5" in texto


def test_el_informe_distingue_los_tres_estados():
    """**Es lo que el docstring exige y lo que un informe descuidado pierde.**"""
    texto = impedance_report(
        {"C3": 4.2, "C4": 12.5}, channels=["C3", "C4", "O1"]
    )

    assert "Dentro del límite" in texto
    assert "Por encima del límite" in texto
    assert "Sin medición disponible" in texto
    assert "O1" in texto


def test_el_informe_dice_que_sin_medir_no_es_estar_bien():
    """Decir sólo "sin dato" dejaría al lector sacando la conclusión cómoda."""
    texto = impedance_report({"C3": 4.2}, channels=["C3", "O1"])

    assert "no quiere decir que estén bien" in texto.lower()


def test_sin_la_lista_de_canales_no_puede_haber_tercer_estado():
    """**Por eso `channels` se agregó a la firma.** `read_impedances()` omite
    los canales sin dato, así que lo que falta no está en el diccionario: sin
    la lista, esta función no puede cumplir su propia promesa.
    """
    texto = impedance_report({"C3": 4.2})

    assert "Sin medición disponible" not in texto
    assert "C3" in texto


def test_el_informe_dice_el_limite_que_se_uso():
    """Un informe que no dice contra qué se comparó no se puede interpretar."""
    assert "3,0 kΩ" in impedance_report({"C3": 4.2}, limit_kohm=3.0)


def test_sin_ninguna_impedancia_lo_dice_y_ofrece_las_vias():
    """Es el caso de todo EDF, y el usuario tiene que saber qué hacer."""
    texto = impedance_report({})

    assert "No hay ninguna impedancia cargada" in texto
    assert "archivo" in texto


def test_el_separador_decimal_es_la_coma():
    assert "4,2" in impedance_report({"C3": 4.2})
    assert "4.2" not in impedance_report({"C3": 4.2})


# -- Los rechazos ------------------------------------------------------------


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        read_impedances(hostil)


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, []])
def test_impedancias_que_no_son_un_diccionario_se_rechazan(hostil):
    with pytest.raises(InvalidRecordingError):
        channels_above_limit(hostil)
    with pytest.raises(InvalidRecordingError):
        impedance_report(hostil)


@pytest.mark.parametrize("limite", [0, -1, None, "cinco", float("nan")])
def test_un_limite_invalido_se_rechaza(limite):
    """Un límite de cero haría fallar todos los canales, y uno negativo no
    significa nada."""
    with pytest.raises(InvalidRecordingError):
        channels_above_limit({"C3": 4.2}, limit_kohm=limite)


def test_una_impedancia_que_no_es_numero_se_rechaza():
    with pytest.raises(InvalidRecordingError):
        channels_above_limit({"C3": "cuatro"})


@pytest.mark.parametrize("hostil", ["texto", 3.5, {}])
def test_una_lista_de_canales_invalida_se_rechaza(hostil):
    with pytest.raises(InvalidRecordingError):
        impedance_report({"C3": 4.2}, channels=hostil)
