"""Tests del registro de herramientas y de su clase base.

`psglab/tools/base.py` y `psglab/tools/registry.py` están implementados desde el
esqueleto y **no tienen stubs**, pero eso nunca fue lo mismo que estar
verificados. Son el mecanismo del que cuelgan las seis herramientas: si el
registro estuviera roto, el síntoma aparecería en seis lugares distintos y en
ninguno se vería la causa.

Por eso este archivo va **antes** que las herramientas del hito 7 y no después.

Lo que se fija acá son dos promesas que el resto del proyecto da por sentadas:

- **Agregar una herramienta no obliga a tocar ningún archivo existente.** Basta
  crear el módulo y decorar la clase; `load_all_tools()` recorre el paquete.
- **Los métodos de evento de `Tool` y `ViewerTool` no hacen nada por defecto**,
  en vez de elevar `NotImplementedError`. Es una decisión cerrada de
  `docs/ARQUITECTURA.md`: si el método base fallara, activar una herramienta y
  navegar rompería el programa entero.
"""

import pytest

from psglab.tools import registry
from psglab.tools.base import Overlay, Tool, ViewerTool
from psglab.tools.registry import (
    available_tools,
    get_tool,
    load_all_tools,
    register_tool,
)
from psglab.utils.errors import DuplicateToolError, PsgLabError, UnknownToolError

#: Las seis que el pliego pide. Escritas a mano a propósito: si alguien borra
#: una herramienta, este archivo tiene que decirlo en vez de adaptarse.
HERRAMIENTAS_DEL_PLIEGO = frozenset(
    {"amplitude_band", "annotator", "histogram", "magnifier", "occupancy", "overview"}
)


@pytest.fixture
def registro_aislado():
    """Guarda y restaura el registro, que es estado de módulo.

    Una herramienta de mentira registrada en un test **queda registrada para
    toda la sesión**, y después la barra de la ventana principal la mostraría en
    cualquier otro test. Es el tipo de contaminación donde el que falla no es el
    que la causó.
    """
    original = dict(registry._REGISTRY)
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(original)


def herramienta_de_mentira(nombre: str = "de_mentira") -> type[Tool]:
    """Una herramienta mínima, para no depender de ninguna de las seis reales."""

    class DeMentira(Tool):
        name = nombre
        label = "De mentira"
        description = "Sólo existe para los tests."

        def activate(self, session) -> None:
            return None

        def deactivate(self) -> None:
            return None

    return DeMentira


# -- El punto de extensión ---------------------------------------------------


def test_una_herramienta_nueva_se_registra_sin_tocar_ningun_archivo(registro_aislado):
    """Es la promesa de escalabilidad del pliego, sección 7."""
    cls = register_tool(herramienta_de_mentira())
    assert cls in available_tools()


def test_el_decorador_devuelve_la_clase_sin_tocarla(registro_aislado):
    """Decorar hace visible la herramienta, no cambia su comportamiento."""
    original = herramienta_de_mentira()
    assert register_tool(original) is original


def test_dos_herramientas_con_el_mismo_nombre_se_rechazan(registro_aislado):
    """Falla **al importar**, que es cuando conviene enterarse.

    En tiempo de ejecución el síntoma sería que una de las dos desapareció de la
    barra, sin ninguna pista de por qué.
    """
    register_tool(herramienta_de_mentira("repetida"))
    with pytest.raises(DuplicateToolError):
        register_tool(herramienta_de_mentira("repetida"))


def test_el_error_de_nombre_repetido_dice_de_donde_salen_las_dos(registro_aislado):
    """Con seis herramientas en archivos distintos, saber cuáles chocan es la
    mitad del arreglo."""
    register_tool(herramienta_de_mentira("repetida"))
    with pytest.raises(DuplicateToolError) as excepcion:
        register_tool(herramienta_de_mentira("repetida"))
    # El detalle nombra los dos módulos de origen. Se afirma sobre el nombre
    # que ve Python al importar el test, que no lleva el paquete adelante.
    assert str(excepcion.value.details).count("test_registry") == 2


def test_se_busca_una_herramienta_por_su_nombre_interno(registro_aislado):
    cls = register_tool(herramienta_de_mentira("buscable"))
    assert get_tool("buscable") is cls


def test_pedir_una_herramienta_que_no_existe_es_un_error_del_programa():
    with pytest.raises(UnknownToolError):
        get_tool("no_existe")


def test_el_error_de_herramienta_desconocida_lista_las_que_hay():
    """Un nombre mal escrito es el caso más probable, y la lista lo resuelve."""
    load_all_tools()
    with pytest.raises(UnknownToolError) as excepcion:
        get_tool("lupa")  # el nombre interno es "magnifier"
    assert "magnifier" in str(excepcion.value.details)


# -- El autodescubrimiento ---------------------------------------------------


def test_las_seis_herramientas_del_pliego_se_descubren_solas():
    """Nadie las importa a mano: `load_all_tools()` recorre el paquete.

    `psglab/tools/__init__.py` no las importa **a propósito**: mantener ahí una
    lista sería justo el archivo que habría que tocar para agregar una.
    """
    load_all_tools()
    assert {cls.name for cls in available_tools()} >= HERRAMIENTAS_DEL_PLIEGO


def test_cargar_dos_veces_no_duplica_nada():
    """`main_window` la llama al armar la barra, y podría llamarla de nuevo."""
    load_all_tools()
    antes = list(available_tools())
    load_all_tools()
    assert list(available_tools()) == antes


def test_available_tools_devuelve_clases_y_no_instancias():
    """Igual que `readers.base.available_readers()`.

    Los dos son los puntos de extensión del proyecto y conviene que se consuman
    de la misma forma; antes uno devolvía instancias y el otro clases, y la
    ventana principal iba a tener que tratarlos distinto sin motivo.
    """
    load_all_tools()
    assert all(isinstance(cls, type) for cls in available_tools())


def test_cada_herramienta_declara_lo_que_la_barra_necesita_para_mostrarla():
    """La barra se arma recorriendo el registro: sin etiqueta no hay qué poner."""
    load_all_tools()
    for cls in available_tools():
        assert cls.name and cls.label and cls.description


def test_solo_compiten_por_el_mouse_las_que_actuan_sobre_la_senal():
    """`exclusive` decide qué herramienta se queda con el clic.

    Los dos paneles tienen su propia zona de pantalla y la banda de amplitud
    sólo se dibuja, así que ninguno compite. Marcarlos exclusivos apagaría al
    anotador cada vez que el usuario mira el histograma.
    """
    load_all_tools()
    por_nombre = {cls.name: cls for cls in available_tools()}
    for nombre in ("magnifier", "annotator", "occupancy"):
        assert por_nombre[nombre].exclusive is True
    for nombre in ("amplitude_band", "histogram", "overview"):
        assert por_nombre[nombre].exclusive is False


# -- Los métodos base, que no pueden elevar ----------------------------------


def test_los_eventos_de_mouse_no_hacen_nada_por_defecto():
    """**Decisión cerrada de `ARQUITECTURA.md`.**

    Una herramienta sobrescribe sólo los eventos que le interesan: la banda de
    amplitud escucha el movimiento y nada más. Si el método base elevara, mover
    el mouse con esa herramienta activa rompería el programa.
    """

    class Pelada(ViewerTool):
        name = "pelada"
        label = "Pelada"

        def activate(self, session) -> None:
            return None

        def deactivate(self) -> None:
            return None

    herramienta = Pelada()
    assert herramienta.on_mouse_press(1.0, 2.0, "left") is None
    assert herramienta.on_mouse_move(1.0, 2.0) is None
    assert herramienta.on_mouse_release(1.0, 2.0, "left") is None
    assert herramienta.on_window_changed(5) is None


def test_una_herramienta_que_no_dibuja_devuelve_la_secuencia_vacia():
    """Y no `None`: quien la consume recorre el resultado sin preguntarse nada."""

    class Pelada(ViewerTool):
        name = "pelada"
        label = "Pelada"

        def activate(self, session) -> None:
            return None

        def deactivate(self) -> None:
            return None

    assert list(Pelada().overlays()) == []


def test_avisar_sin_nadie_enganchado_no_rompe():
    """Es el caso de un test, y también el de una herramienta recién creada
    antes de que la ventana principal la cablee."""
    herramienta = herramienta_de_mentira()()
    assert herramienta.on_changed is None
    herramienta.notify_changed()


def test_avisar_llama_al_callback_con_la_herramienta():
    """La ventana principal engancha acá su repintado, y necesita saber **cuál**
    de las herramientas cambió para no redibujarlas todas."""
    herramienta = herramienta_de_mentira()()
    avisos = []
    herramienta.on_changed = avisos.append
    herramienta.notify_changed()
    assert avisos == [herramienta]


def test_el_callback_se_asigna_sobre_la_instancia_y_no_sobre_la_clase():
    """Asignado en la clase, Python lo convertiría en un método ligado y la
    llamada le pasaría `self` de más. Lo dice el comentario de `base.py`; acá
    queda fijado."""
    cls = herramienta_de_mentira()
    una, otra = cls(), cls()
    avisos = []
    una.on_changed = avisos.append

    otra.notify_changed()
    assert avisos == []

    una.notify_changed()
    assert avisos == [una]


# -- Los overlays son datos, no dibujo ---------------------------------------


def test_un_overlay_sabe_que_herramienta_lo_pidio():
    """Sirve para borrar lo de una sola sin tocar lo de las demás."""
    assert Overlay(tool_name="magnifier").tool_name == "magnifier"


def test_los_overlays_son_inmutables():
    """Son datos que la herramienta publica y el visualizador lee. Si el
    visualizador pudiera escribirlos, el estado de la herramienta cambiaría
    desde afuera sin pasar por ella."""
    overlay = Overlay(tool_name="magnifier")
    with pytest.raises(Exception):
        overlay.tool_name = "otro"  # type: ignore[misc]


def test_los_errores_del_registro_los_atrapa_el_except_de_la_interfaz():
    """La ventana principal atrapa una sola clase.

    Cualquier cosa que escape de `PsgLabError` le llega al investigador como una
    traza de Python.
    """
    with pytest.raises(PsgLabError):
        get_tool("no_existe")
