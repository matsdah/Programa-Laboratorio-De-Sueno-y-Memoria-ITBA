"""Tests de la barra de menú.

**No se testea que un menú se llame de una forma.** Los rótulos son decisiones
de interfaz y renombrarlos no debería hacer fallar nada; el test que miraba si
existía "&Análisis" quedó obsoleto en cuanto ese menú se repartió, y lo que de
verdad protegía —que cada análisis fuera alcanzable— se verifica en
`test_entrega.py`, por la acción.

Lo que sí se testea acá son las tres cosas que sí se pueden romper en silencio:

- **Ninguna acción queda sin conectar.** Una entrada de menú que no llama a
  nada se ve exactamente igual que una que funciona, hasta que alguien la usa.
- **Los tres objetos que el resto del programa busca por nombre** quedan puestos
  sobre la ventana: `accion_eje_en_hora`, `accion_señal_original` y
  `tools_menu`. Se los arma acá y se los usa en otro archivo.
- **El submenú de esquemas se arma solo**, recorriendo el registro de esquemas,
  igual que la barra de herramientas recorre el registro de herramientas.
"""

import pytest
from PySide6.QtWidgets import QMenu

pytest.importorskip("pyqtgraph")

import psglab.ui.menus as menus  # noqa: E402
import psglab.ui.theme as theme  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture
def ventana(qt_app) -> MainWindow:
    return create_main_window()


def menu_llamado(ventana: MainWindow, titulo: str) -> QMenu:
    """El menú de la barra con ese título, para no repetir la búsqueda."""
    for accion in ventana.menuBar().actions():
        if accion.text() == titulo:
            assert accion.menu() is not None
            return accion.menu()
    raise AssertionError(f"no hay ningún menú «{titulo}»")


# -- La estructura -----------------------------------------------------------


def test_estan_los_once_menus(ventana: MainWindow):
    """Eran cinco, con «Análisis» de cajón de sastre: nueve entradas
    heterogéneas en un solo menú obligan a leerlo entero cada vez."""
    titulos = [accion.text() for accion in ventana.menuBar().actions()]

    assert titulos == [
        "&Archivo",
        "&Sesión",
        "&Escala de tiempo",
        "A&mplitud",
        "&Ver",
        "&Montaje",
        "&Filtrar",
        "&Analizar",
        "&Herramientas",
        "&Configuración",
        "A&yuda",
    ]


def test_cada_menu_tiene_contenido(ventana: MainWindow):
    """Un menú vacío o en gris es peor que su ausencia: promete algo que no
    está. El de herramientas se puebla aparte, desde el registro."""
    vacios = [
        accion.text()
        for accion in ventana.menuBar().actions()
        if accion.menu() is not None and not accion.menu().actions()
    ]

    assert vacios == []


def test_ninguna_accion_quedo_sin_conectar(ventana: MainWindow):
    """Una entrada que no llama a nada se ve igual que una que funciona.

    Se mira que tenga al menos un receptor conectado a `triggered`; los
    separadores y los submenús quedan afuera porque no disparan nada.

    La firma va con el prefijo `2`, que es como Qt codifica una señal en
    `receivers()`. Sin él la cuenta da cero para todas y el test pasaría
    siempre, verificando nada.
    """
    sueltas: list[str] = []
    for menu in ventana.menuBar().actions():
        if menu.menu() is None:
            continue
        for accion in menu.menu().actions():
            if accion.isSeparator() or accion.menu() is not None:
                continue
            if accion.receivers("2triggered(bool)") == 0:
                sueltas.append(f"{menu.text()} → {accion.text()}")

    assert sueltas == []


# -- Lo que el resto del programa busca por nombre ---------------------------


def test_deja_puestas_las_dos_acciones_que_se_tocan_despues(ventana: MainWindow):
    """`accion_eje_en_hora` la prende el usuario y la consulta `test_entrega`;
    `accion_señal_original` se habilita cuando un análisis sustituye la señal."""
    assert ventana.accion_eje_en_hora.isCheckable()
    assert ventana.accion_señal_original is not None


def test_volver_a_la_senal_original_arranca_apagada(ventana: MainWindow):
    """Sin ningún análisis aplicado no hay nada a lo que volver, y un botón
    habilitado que no hace nada es una promesa falsa."""
    assert not ventana.accion_señal_original.isEnabled()


def test_el_menu_de_herramientas_queda_listo_para_poblarse(ventana: MainWindow):
    """Lo llena `_build_toolbar()` recorriendo el registro: es el punto de
    extensión del pliego, y una herramienta nueva tiene que aparecer sola."""
    assert ventana.tools_menu is not None
    assert len(ventana.tools_menu.actions()) > 0


# -- Lo que se arma recorriendo un registro ----------------------------------


def test_el_submenu_de_esquemas_los_ofrece_a_todos(ventana: MainWindow):
    """Se arma recorriendo `theme.SCHEMES`, así que agregar un esquema no
    obliga a tocar `menus.py`."""
    configuracion = menu_llamado(ventana, "&Configuración")
    submenus = [a.menu() for a in configuracion.actions() if a.menu() is not None]

    assert len(submenus) == 1
    assert [a.text() for a in submenus[0].actions()] == list(theme.SCHEMES)


def test_elegir_un_esquema_desde_el_menu_lo_aplica(ventana: MainWindow, monkeypatch):
    """No se guarda en el archivo real de quien corre los tests."""
    aplicados: list[theme.ColorScheme] = []
    monkeypatch.setattr(
        MainWindow,
        "set_color_scheme",
        lambda self, esquema, remember=True: aplicados.append(esquema),
    )

    configuracion = menu_llamado(ventana, "&Configuración")
    submenu = next(a.menu() for a in configuracion.actions() if a.menu() is not None)
    submenu.actions()[1].trigger()

    assert aplicados == [list(theme.SCHEMES.values())[1]]


# -- Dónde quedó cada cosa ---------------------------------------------------


def test_exportar_se_mudo_de_archivo_a_sesion(ventana: MainWindow):
    """Abrir un registro es abrir el dato de entrada; exportar un scoring es
    manejar el trabajo propio, que es lo que más veces por sesión se hace."""
    archivo = [a.text() for a in menu_llamado(ventana, "&Archivo").actions()]
    sesion = [a.text() for a in menu_llamado(ventana, "&Sesión").actions()]

    assert not [t for t in archivo if t.startswith("Exportar")]
    assert len([t for t in sesion if t.startswith("Exportar")]) == 3


def test_el_montaje_junta_lo_que_cambia_de_donde_sale_la_senal(ventana: MainWindow):
    montaje = [a.text() for a in menu_llamado(ventana, "&Montaje").actions()]

    assert "&Derivar canales…" in montaje
    assert "&Re-referenciar…" in montaje
    assert "Referencia &promedio (EEG)" in montaje


def test_la_ica_esta_en_filtrar_y_no_en_analizar(ventana: MainWindow):
    """Ajustar la descomposición no cambia nada, pero aplicarla **sustituye la
    señal**: es la operación menos reversible del programa, y agruparla con el
    filtrado dice a qué familia pertenece antes de que alguien la use."""
    filtrar = [a.text() for a in menu_llamado(ventana, "&Filtrar").actions()]
    analizar = [a.text() for a in menu_llamado(ventana, "&Analizar").actions()]

    assert "Componentes &independientes (ICA)…" in filtrar
    assert "Componentes &independientes (ICA)…" not in analizar


def test_la_impedancia_va_primero_en_analizar(ventana: MainWindow):
    """No es un análisis de la señal sino el control de calidad previo a
    confiar en cualquiera de los otros."""
    analizar = [a.text() for a in menu_llamado(ventana, "&Analizar").actions()]

    assert analizar[0] == "&Impedancia de los electrodos…"


def test_construir_los_menus_no_necesita_saber_de_la_ventana(ventana: MainWindow):
    """`menus.py` importa `MainWindow` sólo para las anotaciones, bajo
    `TYPE_CHECKING`: si lo importara de verdad habría un ciclo, porque
    `main_window.py` importa `build_menus`."""
    assert "MainWindow" not in vars(menus)
