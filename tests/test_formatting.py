"""Tests de cómo se escribe un número para el usuario y cómo se lee el que escribe.

`utils/formatting.py` reemplazó en el hito 79 veinticinco `.replace(".", ",")`
repartidos por el programa, y de paso arregló unos veinte mensajes que
escribían el número con punto. Lo que se fija acá es la forma que ya tenían
casi todos —`f"{x:g}"` con coma— para que ningún texto cambie más que eso.
"""

import math

import numpy as np
import pytest

from psglab.utils.errors import InvalidNumberError
from psglab.utils.formatting import SIN_VALOR, duration, number, parse_number, quantity


# -- number -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "texto"),
    [(0.5, "0,5"), (30.0, "30"), (30, "30"), (256.125, "256,125"), (-2.5, "-2,5"), (0.0, "0")],
)
def test_sin_cifras_pedidas_se_escribe_con_coma_y_sin_ceros_de_mas(valor, texto):
    assert number(valor) == texto


def test_con_decimales_se_escriben_siempre_esos_decimales():
    assert number(2, 1) == "2,0"
    assert number(12.345, 2) == "12,35"
    assert number(74.6, 0) == "75"


def test_con_cifras_significativas_sirve_para_cualquier_orden_de_magnitud():
    assert number(123.456, significant=3) == "123"
    assert number(0.012345, significant=3) == "0,0123"


def test_acepta_los_numeros_de_numpy():
    """Es lo que devuelve cualquier cuenta sobre un array."""
    assert number(np.float64(0.5)) == "0,5"
    assert number(np.float32(0.5)) == "0,5"
    assert number(np.int64(3)) == "3"


@pytest.mark.parametrize("valor", [math.nan, math.inf, -math.inf])
def test_un_numero_que_no_existe_no_se_escribe_nan(valor):
    assert number(valor) == SIN_VALOR
    assert number(valor, 2) == SIN_VALOR


@pytest.mark.parametrize("valor", ["0.5", None, True, [1.0]])
def test_lo_que_no_es_un_numero_se_rechaza(valor):
    with pytest.raises(InvalidNumberError):
        number(valor)


@pytest.mark.parametrize("pedido", [{"decimals": -1}, {"decimals": 1.5}, {"significant": 0}, {"decimals": True}])
def test_unas_cifras_imposibles_se_rechazan(pedido):
    with pytest.raises(InvalidNumberError):
        number(1.0, **pedido)


def test_decimales_y_cifras_a_la_vez_se_rechazan():
    with pytest.raises(InvalidNumberError):
        number(1.0, 2, significant=3)


# -- quantity ---------------------------------------------------------------


def test_la_unidad_va_despues_de_un_espacio():
    assert quantity(0.5, "Hz") == "0,5 Hz"
    assert quantity(75.0, "µV", 0) == "75 µV"
    assert quantity(3.04, "kΩ", 1) == "3,0 kΩ"


def test_sin_unidad_queda_el_numero_solo():
    """Un canal sin unidad declarada: se escribe lo que se sabe."""
    assert quantity(12.5, "") == "12,5"


def test_una_unidad_que_no_es_texto_se_rechaza():
    with pytest.raises(InvalidNumberError):
        quantity(1.0, None)


# -- duration ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("segundos", "texto"),
    [(0.2, "200 ms"), (0.01, "10 ms"), (30.0, "30 s"), (2.5, "2,5 s"), (300.0, "5 min"),
     (90.0, "1,5 min"), (3600.0, "1 h"), (5400.0, "1,5 h")],
)
def test_una_duracion_se_escribe_en_la_unidad_que_la_lee_un_investigador(segundos, texto):
    assert duration(segundos) == texto


def test_una_duracion_que_no_es_un_numero_se_rechaza():
    with pytest.raises(InvalidNumberError):
        duration("30 s")


# -- parse_number -----------------------------------------------------------


@pytest.mark.parametrize(("texto", "valor"), [("0,5", 0.5), ("0.5", 0.5), (" 30 ", 30.0), ("-1,25", -1.25)])
def test_se_lee_con_coma_o_con_punto(texto, valor):
    assert parse_number(texto) == valor


@pytest.mark.parametrize("texto", ["", "   ", "treinta", "1,2,3", "nan", "inf", "-inf"])
def test_lo_que_no_es_un_numero_finito_se_lee_como_nada(texto):
    """«inf» lo acepta `float()`, y un corte de «inf» Hz se leería como uno de verdad."""
    assert parse_number(texto) is None


def test_leer_algo_que_no_es_texto_se_rechaza():
    with pytest.raises(InvalidNumberError):
        parse_number(0.5)


def test_lo_que_se_escribe_se_vuelve_a_leer_igual():
    """La tabla de filtros y la de bandas escriben un número y después lo leen."""
    for valor in (0.3, 35.0, 49.5, 0.125):
        assert parse_number(number(valor)) == valor


@pytest.mark.parametrize("segundos", [math.inf, -math.inf, math.nan])
def test_una_duracion_que_no_es_finita_se_muestra_como_sin_valor(segundos: float):
    """La rama existía y ningún test la recorría (hito 81)."""
    assert duration(segundos) == SIN_VALOR
