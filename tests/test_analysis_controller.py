"""Tests del controlador del análisis, armado **sin la ventana principal**.

Hasta el hito 79 la señal original, la ICA ajustada y el cálculo en otro hilo
eran `MainWindow._registro_original`, `_ica` y `_tarea`, y probar sus reglas era
armar la ventana entera. `AnalysisController` recibe la barra de estado, y lo
que es de la ventana —el cartel de un error, vaciar el panel de la ICA, prender
«Volver a la señal original»— le llega por señales. Acá se miran esas señales y
las tres reglas: un análisis que falla no cambia nada, cambiar la señal olvida
la ICA, y un resultado de otra señal se descarta.

Qué pide cada análisis y cómo se muestra lo sigue verificando
`test_entrega.py`, por la ventana.
"""

import threading
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow

from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.ui.analysis_controller import AnalysisController
from psglab.utils.errors import PsgLabError

FRECUENCIA = 100.0
VENTANAS = 2


def _registro(valor: float = 0.0) -> Recording:
    muestras = int(VENTANAS * 30 * FRECUENCIA)
    return Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.full((1, muestras), valor),
        sampling_rate=FRECUENCIA,
    )


def _sesion() -> Session:
    return Session(_registro(), Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


class Escucha:
    """Lo que el controlador le avisó a la ventana, en orden."""

    def __init__(self, controlador: AnalysisController) -> None:
        self.fallas: list[tuple[object, object]] = []
        self.icas_olvidadas = 0
        self.restaurables: list[bool] = []
        controlador.failed.connect(lambda error, que: self.fallas.append((error, que)))
        controlador.ica_forgotten.connect(self._olvido)
        controlador.restorable_changed.connect(self.restaurables.append)

    def _olvido(self) -> None:
        self.icas_olvidadas += 1


@pytest.fixture
def ventana(qt_app):
    """Una `QMainWindow` cualquiera, por su barra de estado: no la principal."""
    ventana = QMainWindow()
    yield ventana
    ventana.deleteLater()


@pytest.fixture
def controlador(ventana: QMainWindow) -> AnalysisController:
    controlador = AnalysisController(ventana.statusBar(), parent=ventana)
    yield controlador
    controlador.wait()


@pytest.fixture
def con_sesion(controlador: AnalysisController) -> AnalysisController:
    controlador.attach(_sesion())
    return controlador


# -- La señal original --------------------------------------------------------


def test_tomar_un_registro_lo_guarda_como_original(controlador: AnalysisController):
    escucha = Escucha(controlador)
    sesion = _sesion()

    controlador.attach(sesion)

    assert controlador.original_recording is sesion.recording
    assert escucha.restaurables == [False]


def test_tomar_otro_registro_olvida_la_ica(con_sesion: AnalysisController):
    """Es de otra señal y de otros canales."""
    con_sesion.keep_ica(object())
    escucha = Escucha(con_sesion)

    con_sesion.attach(_sesion())

    assert con_sesion.ica is None
    assert escucha.icas_olvidadas == 1


def test_un_analisis_deja_su_resultado_y_olvida_la_ica(con_sesion: AnalysisController):
    sesion = con_sesion._session
    original = sesion.recording
    con_sesion.keep_ica(object())
    escucha = Escucha(con_sesion)
    procesado = _registro(1.0)

    devuelto = con_sesion.replace_recording(lambda _actual: procesado)

    assert devuelto is procesado
    assert sesion.recording is procesado
    assert con_sesion.original_recording is original
    assert con_sesion.ica is None
    assert escucha.icas_olvidadas == 1
    assert escucha.restaurables == [True]


def test_un_analisis_que_falla_no_cambia_nada(con_sesion: AnalysisController):
    """La señal que el investigador mira sigue siendo la de antes, y la ICA
    sigue siendo suya."""
    sesion = con_sesion._session
    antes = sesion.recording
    descomposicion = object()
    con_sesion.keep_ica(descomposicion)
    escucha = Escucha(con_sesion)

    def falla(_actual: Recording) -> Recording:
        raise PsgLabError("No se pudo filtrar.")

    with pytest.raises(PsgLabError):
        con_sesion.replace_recording(falla)

    assert sesion.recording is antes
    assert con_sesion.ica is descomposicion
    assert escucha.icas_olvidadas == 0
    assert escucha.restaurables == []


def test_sin_registro_un_analisis_se_rechaza(controlador: AnalysisController):
    with pytest.raises(PsgLabError):
        controlador.replace_recording(lambda registro: registro)


def test_volver_a_la_original_la_pone_y_olvida_la_ica(con_sesion: AnalysisController):
    sesion = con_sesion._session
    original = sesion.recording
    con_sesion.replace_recording(lambda _actual: _registro(1.0))
    con_sesion.keep_ica(object())
    escucha = Escucha(con_sesion)

    assert con_sesion.restore_original() is original

    assert sesion.recording is original
    assert con_sesion.ica is None
    assert escucha.restaurables == [False]


def test_sin_registro_no_hay_a_que_volver(controlador: AnalysisController):
    assert controlador.restore_original() is None


def test_olvidar_sin_ica_no_avisa_nada(con_sesion: AnalysisController):
    """Se la puede llamar desde cualquier camino sin preguntar antes."""
    escucha = Escucha(con_sesion)

    con_sesion.forget_ica()

    assert escucha.icas_olvidadas == 0


# -- El cálculo en segundo plano ------------------------------------------------


def test_el_resultado_vuelve_y_la_barra_se_va(con_sesion: AnalysisController):
    resultados: list[object] = []

    con_sesion.run_in_background("Calculando", lambda: 42, resultados.append)
    assert con_sesion.wait_bar.isVisibleTo(con_sesion.parent())
    con_sesion.wait()

    assert resultados == [42]
    assert not con_sesion.wait_bar.isVisibleTo(con_sesion.parent())


def test_mientras_calcula_las_acciones_largas_se_apagan(con_sesion: AnalysisController):
    """Dos cálculos a la vez sobre la misma sesión se pisan el resultado."""
    accion = QAction("Filtrar")
    con_sesion.set_long_actions([accion])
    seguir = threading.Event()

    con_sesion.run_in_background("Calculando", seguir.wait, lambda _r: None)
    assert not accion.isEnabled()
    seguir.set()
    con_sesion.wait()

    assert accion.isEnabled()


def test_un_error_del_calculo_sale_por_su_senal(con_sesion: AnalysisController):
    escucha = Escucha(con_sesion)
    error = PsgLabError("No convergió.")

    def falla() -> None:
        raise error

    con_sesion.run_in_background("Calculando", falla, lambda _r: None, action="calcular")
    con_sesion.wait()

    assert escucha.fallas == [(error, "calcular")]


def test_un_resultado_de_otra_senal_se_descarta(
    con_sesion: AnalysisController, ventana: QMainWindow
):
    """Hito 67: la ICA de la noche A se mostraba como la de B."""
    resultados: list[object] = []
    seguir = threading.Event()

    def calcular() -> object:
        seguir.wait()
        return "de la señal anterior"

    con_sesion.run_in_background("Calculando", calcular, resultados.append)
    con_sesion.attach(_sesion())
    seguir.set()
    con_sesion.wait()

    assert resultados == []
    assert "señal anterior" in ventana.statusBar().currentMessage()
