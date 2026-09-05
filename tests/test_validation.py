"""Tests del validador numérico compartido.

El módulo existe por un descuido que apareció **cuatro veces** en módulos
distintos: escribir una guarda como `valor < 0` o `valor < 1` y dar por sentado
que rechaza cualquier número inválido. No lo hace, porque toda comparación con
NaN es falsa.

Así que el test que más importa acá es el del NaN. Los demás protegen que el
helper no se vuelva permisivo por otro lado.
"""

import math

import pytest

from psglab.utils.errors import InvalidAnnotationError, PsgLabError
from psglab.utils.validation import check_finite, clamp

MENSAJE = "El valor no sirve."
DETALLE = "Se esperaba un número."


def comprobar(valor, minimo=None) -> None:
    """`check_finite` con los argumentos fijos, para no repetirlos."""
    check_finite(
        valor, error=InvalidAnnotationError, message=MENSAJE, details=DETALLE, minimum=minimo
    )


# -- El caso que motiva el módulo -------------------------------------------


def test_nan_no_atraviesa_la_guarda():
    """La razón de ser del módulo.

    `nan < 1` es **falso**, así que una guarda escrita a mano lo deja pasar. Este
    test es el que impide que la quinta guarda del proyecto nazca con el mismo
    agujero.
    """
    assert not (float("nan") < 1)  # así se cuela
    with pytest.raises(InvalidAnnotationError):
        comprobar(float("nan"), minimo=1)


@pytest.mark.parametrize("valor", [float("inf"), float("-inf")])
def test_los_infinitos_tampoco(valor):
    """Un infinito no explota, que es peor: produce una duración sin fin."""
    with pytest.raises(InvalidAnnotationError):
        comprobar(valor)


def test_nan_se_rechaza_aunque_no_haya_minimo():
    """No hace falta pedir un mínimo para que un NaN sea inválido."""
    with pytest.raises(InvalidAnnotationError):
        comprobar(float("nan"))


# -- Lo que sí tiene que pasar ----------------------------------------------


@pytest.mark.parametrize("valor", [0, 1, -1, 0.5, 1e9, -1e9])
def test_un_numero_finito_pasa(valor):
    comprobar(valor)


def test_el_minimo_es_inclusivo():
    """El borde exacto es válido: una anotación de una muestra existe."""
    comprobar(1, minimo=1)
    with pytest.raises(InvalidAnnotationError):
        comprobar(0, minimo=1)


# -- Lo que no es un número -------------------------------------------------


@pytest.mark.parametrize("valor", [None, "5", [], object(), complex(1, 2)])
def test_lo_que_no_es_un_numero_se_rechaza_con_el_error_del_programa(valor):
    """Sin esto, cada llamador dejaría escapar un `TypeError` crudo.

    Un `TypeError` **no hereda de `PsgLabError`**, así que atraviesa el único
    `except` de la interfaz y el investigador termina viendo una traza de Python
    en vez de un cartel.
    """
    with pytest.raises(InvalidAnnotationError):
        comprobar(valor)


def test_el_error_lo_elige_quien_llama():
    """Un registro incoherente y una anotación mal formada no se explican igual."""
    with pytest.raises(InvalidAnnotationError):
        comprobar("no soy un número")


def test_el_mensaje_es_el_que_se_le_pasa_y_el_detalle_lleva_el_valor():
    with pytest.raises(InvalidAnnotationError) as excepcion:
        comprobar(float("nan"))

    assert excepcion.value.message == MENSAJE
    assert "nan" in (excepcion.value.details or "")


def test_todo_lo_que_eleva_hereda_de_la_base_del_programa():
    """Es la promesa de la que cuelga el manejo de errores entero."""
    with pytest.raises(PsgLabError):
        comprobar(None)


# -- El recorte -------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"), [(50.0, 50.0), (0.5, 1.0), (99999.0, 100.0), (1.0, 1.0), (100.0, 100.0)]
)
def test_el_recorte_deja_el_valor_dentro_del_rango(valor, esperado):
    assert clamp(valor, 1.0, 100.0) == pytest.approx(esperado)


def test_el_recorte_rechaza_lo_que_no_puede_recortar():
    """`min(max(nan, lo), hi)` devuelve **NaN**: la forma corta no recorta nada.

    Es un error de programación y no algo que el usuario provoque —quien llama
    tiene que haber validado antes—, así que es un `ValueError` y no un
    `PsgLabError`.
    """
    assert math.isnan(min(max(float("nan"), 1.0), 100.0))  # la forma que no sirve
    with pytest.raises(ValueError):
        clamp(float("nan"), 1.0, 100.0)
