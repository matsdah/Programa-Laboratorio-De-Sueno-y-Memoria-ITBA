"""Tests de correr algo largo sin congelar la ventana.

**Un test de hilos que dependa del reloj es peor que ningún test**: pasa en una
máquina y falla en la de al lado, y nadie sabe cuál de las dos tiene razón. Acá
no hay ningún `sleep` ni ninguna espera con tiempo: todo se sincroniza con
`BackgroundTask.wait()`, que es exactamente lo que hace el cierre de la ventana
y por lo mismo —saber que terminó—.

Lo que se verifica es el contrato que la ventana necesita: que el resultado
vuelva, que un error del programa salga por `failed`, que uno **inesperado**
se vuelva a elevar en vez de desaparecer en el hilo, y que `stopped` avise
siempre que terminó, también en ese caso (hito 68).
"""

import threading

import pytest

from psglab.ui.background import BackgroundTask
from psglab.utils.errors import AlreadyRunningError, PsgLabError


@pytest.fixture
def tarea(qt_app) -> BackgroundTask:
    """Una tarea sin nada corriendo."""
    return BackgroundTask()


def recoger(tarea: BackgroundTask) -> dict[str, object]:
    """Anota lo que la tarea entregue, por cualquiera de sus dos señales."""
    visto: dict[str, object] = {}
    tarea.finished.connect(lambda r: visto.__setitem__("resultado", r))
    tarea.failed.connect(lambda e: visto.__setitem__("error", e))
    return visto


# -- El camino feliz ----------------------------------------------------------


def test_el_resultado_vuelve(tarea: BackgroundTask):
    visto = recoger(tarea)

    tarea.start(lambda: 42)
    tarea.wait()

    assert visto["resultado"] == 42


def test_el_trabajo_corre_en_otro_hilo(tarea: BackgroundTask):
    """**Es todo el punto del módulo.** Si corriera en el de la interfaz, la
    ventana seguiría congelada los quince segundos de la conectividad."""
    donde: dict[str, int] = {}

    tarea.start(lambda: donde.__setitem__("hilo", threading.get_ident()))
    tarea.wait()

    assert donde["hilo"] != threading.get_ident()


def test_mientras_corre_lo_dice(tarea: BackgroundTask):
    """Lo consulta la ventana para apagar lo que no se puede pedir."""
    empezo = threading.Event()
    seguir = threading.Event()

    def trabajo() -> None:
        empezo.set()
        seguir.wait()

    tarea.start(trabajo)
    empezo.wait()
    corriendo = tarea.is_running()
    seguir.set()
    tarea.wait()

    assert corriendo
    assert not tarea.is_running()


def test_terminado_se_puede_volver_a_empezar(tarea: BackgroundTask):
    """Pedir dos análisis seguidos es el uso corriente."""
    visto = recoger(tarea)

    tarea.start(lambda: "uno")
    tarea.wait()
    tarea.start(lambda: "dos")
    tarea.wait()

    assert visto["resultado"] == "dos"


# -- Los errores --------------------------------------------------------------


def test_un_error_del_programa_sale_por_failed(tarea: BackgroundTask):
    """Es el contrato de todo el programa: lo que ve el investigador hereda de
    `PsgLabError` y llega a `_show_error()`, no a una traza de Python."""
    visto = recoger(tarea)

    def trabajo() -> None:
        raise PsgLabError("No se pudo medir.", details="por el test")

    tarea.start(trabajo)
    tarea.wait()

    assert isinstance(visto["error"], PsgLabError)
    assert "resultado" not in visto


def test_un_error_inesperado_se_vuelve_a_elevar(tarea: BackgroundTask):
    """**Un bug no se convierte en un cartel.** Y tampoco desaparece: sin esto,
    un `AttributeError` en el hilo dejaría a la ventana esperando para siempre
    un resultado que no llega."""
    def trabajo() -> None:
        raise AttributeError("esto es un bug")

    tarea.start(trabajo)

    with pytest.raises(AttributeError):
        tarea.wait()


def test_dos_calculos_a_la_vez_se_rechazan(tarea: BackgroundTask):
    """Se pisarían el resultado, y cuál gana dependería de cuál termine
    primero: un fallo que depende del reloj es el peor de todos."""
    empezo = threading.Event()
    seguir = threading.Event()

    def trabajo() -> None:
        empezo.set()
        seguir.wait()

    tarea.start(trabajo)
    empezo.wait()
    try:
        with pytest.raises(AlreadyRunningError):
            tarea.start(lambda: None)
    finally:
        seguir.set()
        tarea.wait()


# -- Esperar sin nada corriendo ----------------------------------------------


def test_esperar_sin_nada_corriendo_no_hace_nada(tarea: BackgroundTask):
    """La llama el cierre de la ventana, que no sabe si había algo."""
    visto = recoger(tarea)

    tarea.wait()

    assert visto == {}


def test_esperar_dos_veces_no_entrega_dos_veces(tarea: BackgroundTask):
    """`wait()` fuerza la entrega, y la ventana la llama al cerrar aunque el
    resultado ya haya llegado por la cola de eventos."""
    cuantas: list[object] = []
    tarea.finished.connect(cuantas.append)

    tarea.start(lambda: "uno")
    tarea.wait()
    tarea.wait()

    assert cuantas == ["uno"]


# -- Quien espera se entera siempre de que terminó (hito 68) -----------------


def test_stopped_sale_despues_del_resultado(tarea: BackgroundTask):
    """Después y no antes: la ventana dibuja el resultado con `finished` y
    recién entonces saca la barra de espera."""
    orden: list[str] = []
    tarea.finished.connect(lambda _r: orden.append("finished"))
    tarea.stopped.connect(lambda: orden.append("stopped"))

    tarea.start(lambda: 1)
    tarea.wait()

    assert orden == ["finished", "stopped"]


def test_stopped_sale_despues_de_un_error_del_programa(tarea: BackgroundTask):
    orden: list[str] = []
    tarea.failed.connect(lambda _e: orden.append("failed"))
    tarea.stopped.connect(lambda: orden.append("stopped"))

    def trabajo() -> None:
        raise PsgLabError("No se pudo medir.")

    tarea.start(trabajo)
    tarea.wait()

    assert orden == ["failed", "stopped"]


def test_stopped_sale_aunque_el_error_inesperado_se_vuelva_a_elevar(
    tarea: BackgroundTask,
):
    """**Sin esto la ventana se quedaba esperando**: el error no pasa por
    `finished` ni por `failed`, y la barra de espera seguía girando con los
    menús largos apagados hasta cerrar el programa. El error se sigue
    elevando igual: un bug no se convierte en un cartel del programa."""
    avisos: list[str] = []
    tarea.stopped.connect(lambda: avisos.append("stopped"))

    def trabajo() -> None:
        raise AttributeError("esto es un bug")

    tarea.start(trabajo)

    with pytest.raises(AttributeError):
        tarea.wait()
    assert avisos == ["stopped"]
    assert not tarea.is_running()
