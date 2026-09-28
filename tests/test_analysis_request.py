"""Tests de la fila con que se pide un análisis desde su panel, sin la ventana.

Que la ventana la llene y calcule con ella lo verifica `test_entrega_analisis.py`.
Acá se mira lo que es de la fila: qué se conserva al volver a llenarla, cuándo
el botón está prendido y qué pasa con un campo o una opción que no existen.
"""

import pytest

from psglab.ui.analysis_request import CALCULAR, AnalysisRequest
from psglab.utils.errors import PsgLabError

CANALES = ["C3", "C4", "EOG-izq"]
BANDAS = ["Delta", "Theta", "Alfa"]


@pytest.fixture
def fila(qt_app) -> AnalysisRequest:
    return AnalysisRequest()


def test_arranca_sin_campos_y_con_el_boton_apagado(fila: AnalysisRequest):
    assert fila.keys() == []
    assert fila.boton.text() == CALCULAR
    assert not fila.boton.isEnabled()


def test_los_campos_llevan_sus_opciones_y_la_preferida(fila: AnalysisRequest):
    fila.set_fields([("canal", "Canal:", CANALES, "C4"), ("banda", "Banda:", BANDAS, None)])

    assert fila.keys() == ["canal", "banda"]
    assert fila.options("canal") == CANALES
    assert fila.value("canal") == "C4"
    assert fila.value("banda") == "Delta"
    assert fila.boton.isEnabled()


def test_volver_a_llenarla_conserva_lo_elegido(fila: AnalysisRequest):
    """Pedir otra vez el espectro no le cambia el canal al usuario."""
    fila.set_fields([("canal", "Canal:", CANALES, "C3")])
    fila.set_value("canal", "EOG-izq")

    fila.set_fields([("canal", "Canal:", CANALES, "C3")])

    assert fila.value("canal") == "EOG-izq"


def test_si_lo_elegido_ya_no_esta_va_la_preferida(fila: AnalysisRequest):
    """Un canal que desapareció al volver a la señal original."""
    fila.set_fields([("canal", "Canal:", [*CANALES, "C3-C4"], None)])
    fila.set_value("canal", "C3-C4")

    fila.set_fields([("canal", "Canal:", CANALES, "C4")])

    assert fila.value("canal") == "C4"


def test_cambiar_de_campos_rehace_la_fila(fila: AnalysisRequest):
    """El panel de la métrica pasa de canal y medida a banda."""
    fila.set_fields([("canal", "Canal:", CANALES, None), ("medida", "Medida:", ["higuchi"], None)])

    fila.set_fields([("banda", "Banda:", BANDAS, None)])

    assert fila.keys() == ["banda"]
    with pytest.raises(PsgLabError):
        fila.value("canal")


def test_un_campo_sin_opciones_apaga_el_boton(fila: AnalysisRequest):
    fila.set_fields([("canal", "Canal:", [], None)])

    assert fila.value("canal") == ""
    assert not fila.boton.isEnabled()


def test_calcular_avisa(fila: AnalysisRequest):
    avisos: list[bool] = []
    fila.requested.connect(lambda: avisos.append(True))
    fila.set_fields([("canal", "Canal:", CANALES, None)])

    fila.boton.click()

    assert avisos == [True]


def test_elegir_algo_que_no_se_ofrece_se_rechaza(fila: AnalysisRequest):
    fila.set_fields([("canal", "Canal:", CANALES, None)])

    with pytest.raises(PsgLabError):
        fila.set_value("canal", "Fp1")
    assert fila.value("canal") == "C3"


def test_pedir_un_campo_que_no_existe_se_rechaza(fila: AnalysisRequest):
    with pytest.raises(PsgLabError):
        fila.options("canal")
