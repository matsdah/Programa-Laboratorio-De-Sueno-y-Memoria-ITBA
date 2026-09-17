"""Tests de la barra de menú.

**No se testea que un menú se llame de una forma.** Los rótulos son decisiones
de interfaz y renombrarlos no debería hacer fallar nada; el test que miraba si
existía "&Análisis" quedó obsoleto en cuanto ese menú se repartió, y lo que de
verdad protegía —que cada análisis fuera alcanzable— se verifica en
`test_entrega.py`, por la acción.

Lo que sí se testea acá son las tres cosas que sí se pueden romper en silencio:

- **Ninguna acción queda sin conectar.** Una entrada de menú que no llama a
  nada se ve exactamente igual que una que funciona, hasta que alguien la usa.
- **Los cuatro objetos que el resto del programa busca por nombre** quedan
  puestos sobre la ventana: `accion_eje_en_hora`, `accion_señal_original`,
  `open_button` y `tools_menu`. Se los arma acá y se los usa en otro archivo.
- **Las exportaciones del scoring se arman solas**, recorriendo
  `SCORING_FORMATS`, igual que el menú de herramientas recorre su registro.

Y, desde el hito 23, lo que se sacó a pedido del usuario: un test que lo
afirme es lo único que impide que vuelva en el próximo refactor sin que nadie
lo decida.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QToolBar, QToolButton

pytest.importorskip("pyqtgraph")

import psglab.ui.menus as menus  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.exporters.scoring_formats import SCORING_FORMATS  # noqa: E402
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


def _todas_las_acciones(ventana: MainWindow) -> list:
    """Las acciones de todos los menús y submenús, sin separadores.

    Incluye las entradas de la barra que no tienen submenú, como
    «Configuración».
    """
    acciones = []

    def recorrer(menu) -> None:
        for accion in menu.actions():
            if accion.menu() is not None:
                recorrer(accion.menu())
            elif not accion.isSeparator():
                acciones.append(accion)

    for accion_de_menu in ventana.menuBar().actions():
        if accion_de_menu.menu() is not None:
            recorrer(accion_de_menu.menu())
        else:
            acciones.append(accion_de_menu)
    return acciones


# -- La estructura -----------------------------------------------------------


def test_estan_las_once_entradas(ventana: MainWindow):
    """Eran cinco, con «Análisis» de cajón de sastre: nueve entradas
    heterogéneas en un solo menú obligan a leerlo entero cada vez.

    «Archivo» ya no está —es el botón de la esquina— y «Paneles» salió de
    «Ver» para ser una entrada propia."""
    titulos = [accion.text() for accion in ventana.menuBar().actions()]

    assert titulos == [
        "&Scoring",
        "&Escala de tiempo",
        "A&mplitud",
        "&Ver",
        "&Paneles",
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
    separadores y los submenús quedan afuera porque no disparan nada. Las
    entradas de la barra sin submenú, como «Configuración», también cuentan.

    La firma va con el prefijo `2`, que es como Qt codifica una señal en
    `receivers()`. Sin él la cuenta da cero para todas y el test pasaría
    siempre, verificando nada.
    """
    sueltas: list[str] = []
    for menu in ventana.menuBar().actions():
        if menu.menu() is None:
            if menu.receivers("2triggered(bool)") == 0:
                sueltas.append(menu.text())
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
    """Lo llena `_build_tools_menu()` recorriendo el registro: es el punto de
    extensión del pliego, y una herramienta nueva tiene que aparecer sola."""
    assert ventana.tools_menu is not None
    assert len(ventana.tools_menu.actions()) > 0


def test_el_boton_de_abrir_queda_en_la_esquina_de_la_barra(ventana: MainWindow):
    esquina = ventana.menuBar().cornerWidget(Qt.Corner.TopLeftCorner)

    assert isinstance(ventana.open_button, QToolButton)
    assert esquina is ventana.open_button


# -- El botón de abrir -------------------------------------------------------


def test_abrir_es_un_boton_con_icono_y_no_un_menu(ventana: MainWindow):
    """«Archivo» tenía una sola acción: un menú de una entrada son dos clics
    para lo que un botón hace en uno."""
    titulos = [accion.text() for accion in ventana.menuBar().actions()]

    assert "&Archivo" not in titulos
    assert not ventana.open_button.icon().isNull()
    assert ventana.open_button.text() == ""


def test_el_boton_de_abrir_se_realza_al_pasar_el_mouse(ventana: MainWindow):
    """`autoRaise` es lo que le da el realce: sin él, el botón se ve siempre
    igual y no parece clickeable."""
    assert ventana.open_button.autoRaise()


def test_el_boton_de_abrir_dice_que_hace_y_su_atajo(ventana: MainWindow):
    """Un icono sin tooltip obliga a adivinar, y el botón no tiene columna de
    atajo como los menús."""
    assert ventana.open_button.toolTip() == "Abrir registro (Ctrl+O)"
    assert ventana.open_button.accessibleName() == "Abrir registro"


def test_el_clic_en_el_boton_abre_el_dialogo(qt_app, monkeypatch):
    """Se reemplaza el método **antes** de armar la ventana: la conexión se
    hace con el método ligado, y uno reemplazado después no se enteraría."""
    llamadas: list[bool] = []
    monkeypatch.setattr(
        MainWindow, "open_recording_dialog", lambda self: llamadas.append(True)
    )
    ventana = create_main_window()

    ventana.open_button.click()

    assert llamadas == [True]


def test_no_existe_salir(ventana: MainWindow):
    """Lo hace la cruz de la ventana."""
    textos = [a.text() for a in _todas_las_acciones(ventana)]

    assert not [t for t in textos if "Salir" in t]


# -- Scoring -----------------------------------------------------------------


def test_scoring_importa_y_exporta_en_los_cuatro_formatos(ventana: MainWindow):
    """Abrir un registro es abrir el dato de entrada; importar y exportar un
    scoring es manejar el trabajo propio, que es lo que más se hace."""
    textos = [
        a.text().partition("\t")[0]
        for a in menu_llamado(ventana, "&Scoring").actions()
        if not a.isSeparator()
    ]

    assert textos == [
        "&Importar scoring…",
        "Exportar .txt…",
        "Exportar .csv…",
        "Exportar .edf…",
        "Exportar .xml…",
    ]


def test_las_exportaciones_salen_de_la_tabla_de_formatos(ventana: MainWindow):
    """Un formato nuevo en `SCORING_FORMATS` tiene que aparecer solo."""
    textos = [
        a.text().partition("\t")[0]
        for a in menu_llamado(ventana, "&Scoring").actions()
        if a.text().startswith("Exportar")
    ]

    assert textos == [f"Exportar .{extension}…" for extension in SCORING_FORMATS]


def test_anotaciones_e_informacion_ya_no_se_ofrecen(ventana: MainWindow):
    """**Decisión del 16 de septiembre de 2026**, aunque el pliego los pide:
    `MainWindow.export()` los sigue escribiendo, pero sólo desde un script. Si
    vuelven al menú, que sea porque alguien lo decidió."""
    textos = " ".join(a.text() for a in _todas_las_acciones(ventana))

    assert "Anotaciones" not in textos
    assert "Informacion" not in textos
    assert "Información" not in textos


def test_cada_exportacion_pide_su_formato(qt_app, monkeypatch):
    pedidos: list[str] = []
    monkeypatch.setattr(
        MainWindow,
        "export_scoring_dialog",
        lambda self, fmt="txt": pedidos.append(fmt),
    )
    ventana = create_main_window()

    for accion in menu_llamado(ventana, "&Scoring").actions():
        if accion.text().startswith("Exportar"):
            accion.trigger()

    assert pedidos == list(SCORING_FORMATS)


# -- Escala, amplitud, paneles, herramientas y configuración -----------------


def test_la_escala_no_ofrece_acercar_ni_alejar(ventana: MainWindow):
    """Agregaban poco frente a la lista de escalas. Siguen en Ctrl++ y Ctrl+-,
    como verifica `test_main_window_layout.py` al buscar el método de cada
    atajo."""
    textos = [a.text() for a in menu_llamado(ventana, "&Escala de tiempo").actions()]

    assert not [t for t in textos if "Acercar" in t or "Alejar" in t]


@pytest.mark.parametrize("titulo", ["&Escala de tiempo", "A&mplitud"])
def test_la_escala_propia_se_llama_personalizado(ventana: MainWindow, titulo: str):
    textos = [a.text() for a in menu_llamado(ventana, titulo).actions()]

    assert "&Personalizado…" in textos
    assert not [t for t in textos if "Definida por el" in t]


def test_paneles_es_una_entrada_propia_con_todos_los_paneles(ventana: MainWindow):
    """Quedaba a tres clics, dentro de «Ver». Se arma recorriendo los docks."""
    paneles = menu_llamado(ventana, "&Paneles")
    acciones = [a for a in paneles.actions() if not a.isSeparator()]

    assert acciones[:-1] == [dock.toggleViewAction() for dock in ventana.docks.values()]
    assert acciones[-1].text() == "&Restaurar la disposición"


def test_ver_ya_no_tiene_submenus(ventana: MainWindow):
    ver = menu_llamado(ventana, "&Ver")

    assert not [a for a in ver.actions() if a.menu() is not None]


def test_no_hay_barra_de_herramientas(ventana: MainWindow):
    """Repetía el menú Herramientas justo debajo de la barra de menú. La única
    barra que queda es la de navegación, que no es un panel a propósito."""
    assert ventana.findChildren(QToolBar) == [ventana.navigation_bar]


def test_las_herramientas_se_tildan_desde_su_menu(ventana: MainWindow):
    """El menú no muestra tooltips, así que la descripción va también a la
    barra de estado."""
    acciones = ventana.tools_menu.actions()

    assert acciones
    assert all(a.isCheckable() for a in acciones)
    assert all(a.statusTip() for a in acciones)


def test_construir_los_menus_no_necesita_saber_de_la_ventana(ventana: MainWindow):
    """`menus.py` importa `MainWindow` sólo para las anotaciones, bajo
    `TYPE_CHECKING`: si lo importara de verdad habría un ciclo, porque
    `main_window.py` importa `build_menus`."""
    assert "MainWindow" not in vars(menus)


def test_configuracion_abre_su_ventana_sin_desplegar_nada(ventana: MainWindow):
    """El submenú de esquemas repetía la solapa Colores de esa misma ventana."""
    accion = next(a for a in ventana.menuBar().actions() if a.text() == "&Configuración")

    assert accion.menu() is None
    accion.trigger()

    assert ventana.settings_dialog is not None
    assert ventana.settings_dialog.isVisible()
    ventana.settings_dialog.close()


def test_la_barra_no_es_la_nativa(ventana: MainWindow):
    """La nativa de macOS no muestra el botón de abrir ni una entrada sin
    submenú: la barra sería otra en esa plataforma."""
    assert not ventana.menuBar().isNativeMenuBar()


# -- Los atajos, a la vista ----------------------------------------------------------


def test_las_acciones_con_atajo_lo_muestran(ventana: MainWindow):
    """**Hasta la fase 9 ningún menú mostraba un atajo**, y es lo primero que
    mira quien aprende un programa."""
    from psglab.ui.shortcuts import key_for, readable_key

    con_atajo = [
        accion
        for accion in _todas_las_acciones(ventana)
        if isinstance(accion.data(), str) and key_for(accion.data()) is not None
    ]

    # Exportar .txt, registro entero y las dos de amplitud. Eran siete hasta
    # que abrir, acercar y alejar salieron del menú en el hito 23.
    assert len(con_atajo) >= 4
    for accion in con_atajo:
        rotulo, _, atajo = accion.text().partition("\t")
        assert atajo == readable_key(key_for(accion.data())), rotulo


def test_las_acciones_sin_atajo_no_muestran_ninguno(ventana: MainWindow):
    from psglab.ui.shortcuts import key_for

    for accion in _todas_las_acciones(ventana):
        metodo = accion.data()
        if not isinstance(metodo, str) or key_for(metodo) is None:
            assert "\t" not in accion.text(), accion.text()


def test_exportar_en_txt_muestra_ctrl_s(ventana: MainWindow):
    """Ctrl+S llama al mismo método sin argumento, y por eso se anota a mano."""
    textos = [a.text() for a in menu_llamado(ventana, "&Scoring").actions()]

    assert "Exportar .txt…\tCtrl+S" in textos
    assert [t for t in textos if "\t" in t] == ["Exportar .txt…\tCtrl+S"]


def test_el_atajo_se_muestra_pero_no_se_registra_en_la_accion(ventana: MainWindow):
    """**La tecla ya la instala `shortcuts.py`.** Registrarla también en la
    acción la volvería ambigua, y ante un atajo ambiguo Qt no ejecuta
    ninguno: mostrar el atajo rompería el atajo."""
    for accion in _todas_las_acciones(ventana):
        assert accion.shortcut().isEmpty(), accion.text()
