"""La superficie pública de la ventana principal, congelada a propósito.

Este archivo no verifica que el programa haga algo: eso es `test_entrega.py`,
que recorre el camino completo. Verifica **cómo se llama** lo que hace, que es
otra cosa y hoy estaba escrito sólo de forma implícita, repartido en las 1610
líneas de aquél.

Existe por el refactor de la interfaz. Cuando `_build_layout()` se reescriba
para usar paneles acoplables, cualquiera va a poder saber de un vistazo qué
nombres no puede cambiar sin actualizar los tests que los usan —y, sobre todo,
va a **enterarse en el momento** si renombra uno sin querer, en vez de
descubrirlo por un `AttributeError` en un test de integración que habla de otra
cosa.

La lista es deliberadamente exhaustiva y deliberadamente frágil: si agregás un
panel nuevo, este test falla y hay que sumarlo acá. Esa fricción es el punto.
"""

import pytest
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QMainWindow

pytest.importorskip("pyqtgraph")

from psglab.app import create_main_window  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from psglab.ui.shortcuts import install_shortcuts  # noqa: E402

#: Los widgets y acciones que la ventana cuelga de sí misma. Cada uno lo usa
#: algún test o el usuario a través de un atajo, así que renombrarlos rompe
#: algo que no se ve desde `main_window.py`.
ATRIBUTOS_PUBLICOS: frozenset[str] = frozenset(
    {
        # Acciones de menú que los tests prenden y apagan.
        "accion_eje_en_hora",
        "accion_señal_original",
        # La primera que arrancó un cálculo en otro hilo: hay que poder
        # apagarla mientras dura, porque con uno en curso no se puede pedir
        # otro (hito 42).
        "accion_conectividad_de_la_noche",
        # Los dos menús que sustituyen el registro —«Montaje» entero, y
        # «Filtrar», que además lleva la otra operación que corre en otro
        # hilo—. Se apagan mientras dura un cálculo: cambiar la señal debajo
        # de una ICA que se está ajustando dejaría una descomposición de una
        # señal que ya no está (hito 47).
        "menu_montaje",
        "menu_filtrar",
        # Los dos esquemas, en el menú «Ver» desde el hito 35: la ventana
        # necesita poder tildar el que aplique, venga del menú o del archivo
        # de preferencias.
        "acciones_de_esquema",
        # El menú que se puebla desde el registro de herramientas.
        "tools_menu",
        # Los dos submenús que se rearman desde las preferencias (hito 64):
        # «Abrir reciente» y «Vistas de canales».
        "menu_recientes",
        "menu_vistas",
        # El botón de la esquina de la barra de menú, que abre un registro. El
        # cambio de esquema le vuelve a dibujar el icono.
        "open_button",
        # Qué registro está abierto, en la otra esquina de esa barra (hito 36).
        "recording_summary",
        # Los paneles acoplables, por nombre, y los cuatro de trabajo.
        "docks",
        "channels_dock",
        "overview_dock",
        "scoring_dock",
        "histogram_dock",
        # La barra fija de abajo, que no es un dock a propósito.
        "navigation_bar",
        # Los widgets que van adentro de todo eso.
        "signal_view",
        "channel_selector",
        "scoring_panel",
        "navigation",
        "overview_panel",
        "histogram_view",
        "tool_readout",
        "page_readout",
        "settings_dialog",
        # El reloj de la reproducción, que los tests hacen avanzar a mano.
        "playback",
        # Los seis paneles de análisis y sus contenedores. **El panel y el
        # contenedor son atributos distintos a propósito**: los tests muestran
        # el contenedor y preguntan por el contenido del panel. El título del
        # contenedor es fijo desde el hito 31: es el texto de su entrada en
        # «Herramientas».
        "psd_panel",
        "psd_dialog",
        "metric_panel",
        "metric_dialog",
        "connectivity_panel",
        "connectivity_dialog",
        "impedance_panel",
        "impedance_dialog",
        "filter_panel",
        "filter_dialog",
        "ica_panel",
        "ica_dialog",
    }
)

#: Métodos y properties públicos. Son la API que usan los atajos de teclado
#: (por nombre, vía `getattr`), los menús y `test_entrega.py`.
METODOS_PUBLICOS: frozenset[str] = frozenset(
    {
        # Estado.
        "session",
        "refresh",
        "set_color_scheme",
        # Configuración.
        "apply_preferences",
        "current_preferences",
        "show_settings_dialog",
        "show_connectivity_night_dialog",
        # Accesibilidad.
        "focusable_panes",
        "current_pane",
        "focus_next_pane",
        "focus_previous_pane",
        # Escala de tiempo.
        "set_timescale",
        "halve_timescale",
        "double_timescale",
        "show_whole_recording",
        "ask_timescale",
        "pan_view_left",
        "pan_view_right",
        "pan_view_page_left",
        "pan_view_page_right",
        "restore_default_layout",
        "apply_saved_preferences",
        # Reproducción.
        "toggle_playback",
        # Archivo.
        "open_recording",
        "open_recording_dialog",
        "open_scoring",
        "open_scoring_dialog",
        "export",
        "export_scoring_dialog",
        # Amplitud.
        "fit_amplitude_to_pane",
        "center_amplitude_offsets",
        "reset_amplitude_offsets",
        "set_amplitude_scale",
        "ask_amplitude_scale",
        # Navegación y scoring.
        "go_to_next_window",
        # Hito 62: ir a cualquier ventana y anotar, sin mouse.
        "go_to_first_window",
        "go_to_last_window",
        "ask_window",
        # Hito 64: recientes y vistas de canales.
        "open_recent_file",
        # Las marcas del archivo como anotaciones (hito 73).
        "import_file_marks",
        # Las fases sugeridas, «Analizar › Fases sugeridas» (hito 75).
        "request_stage_suggestions",
        "accept_safe_suggestions",
        "accept_all_suggestions",
        "discard_suggestions",
        "save_channel_view",
        "apply_channel_view",
        "delete_channel_view",
        "annotate_current_window",
        "annotation_menu_for_current_window",
        "go_to_previous_window",
        "increase_amplitude",
        "decrease_amplitude",
        "score_current_window",
        "toggle_arousal",
        "set_histogram_time_axis",
        # Montaje.
        "derive_dialog",
        "rereference_dialog",
        "apply_average_reference",
        "restore_original_recording",
        # Análisis.
        "show_psd_dialog",
        "show_complexity_dialog",
        "show_connectivity_dialog",
        "show_filter_dialog",
        "apply_filters_from_panel",
        "show_impedance_dialog",
        "load_impedances_dialog",
        "show_ica_dialog",
        # Lo que se precalienta en segundo plano —los lectores y la compilación
        # de `antropy`—, que pide `main.py` por
        # `create_main_window(warm_up=True)` (hitos 31 y 33).
        "warm_up_in_background",
        # Esperar el cálculo largo que esté corriendo. La llama el cierre de la
        # ventana antes de soltar la sesión, y cualquier test que necesite el
        # resultado (hito 42).
        "wait_for_background",
        # El contador de la lupa, desde «Herramientas» (hito 32).
        "reset_magnifier_count",
    }
)

#: Privados que `test_entrega.py` llama o monkeypatchea. No son API pública,
#: pero la suite depende de ellos igual, así que renombrarlos tampoco es gratis.
PRIVADOS_QUE_LA_SUITE_USA: frozenset[str] = frozenset(
    {
        "_show_error",
        "_go_to_window",
        "_toggle_tool",
        "_tools",
        "_session",
        "_activate_panel_tools",
        "_ica",
        "_aplicar_analisis",
        # El cartel del trabajo sin exportar, que es modal (hito 33).
        "_preguntar_por_el_trabajo",
        # El cartel de un archivo que trae menos de lo que declara (hito 33).
        "_mostrar_avisos_de_lectura",
        # La pregunta antes de lo que no se deshace, también modal (hito 65).
        "_confirmar",
    }
)


@pytest.fixture
def ventana(qt_app) -> MainWindow:
    """La ventana recién construida, sin ningún registro abierto."""
    return create_main_window()


def publicos_de_la_instancia(ventana: MainWindow) -> set[str]:
    """Lo que la ventana se cuelga a sí misma, sin las señales de Qt.

    PySide6 deja las señales de la clase base en el diccionario de la instancia
    (`destroyed`, `windowTitleChanged`…), así que hay que descontarlas para
    quedarse con lo que puso `_build_layout()`.
    """
    de_qt = set(dir(QMainWindow))
    return {
        nombre
        for nombre in vars(ventana)
        if not nombre.startswith("_") and nombre not in de_qt
    }


# -- La superficie -----------------------------------------------------------


def test_los_atributos_publicos_son_los_declarados(ventana: MainWindow):
    """Ni más ni menos. Un panel nuevo tiene que sumarse a la lista."""
    assert publicos_de_la_instancia(ventana) == ATRIBUTOS_PUBLICOS


def test_los_metodos_publicos_son_los_declarados(ventana: MainWindow):
    de_qt = set(dir(QMainWindow))
    encontrados = {
        nombre
        for nombre in dir(MainWindow)
        if not nombre.startswith("_") and nombre not in de_qt
    }

    assert encontrados == METODOS_PUBLICOS


def test_los_privados_que_usa_la_suite_siguen_existiendo(ventana: MainWindow):
    faltantes = [n for n in PRIVADOS_QUE_LA_SUITE_USA if not hasattr(ventana, n)]

    assert faltantes == []


def test_cada_atajo_encuentra_su_metodo(ventana: MainWindow):
    """`shortcuts.py` conecta por nombre con `getattr`, así que un método que se
    renombra no da error: el atajo simplemente deja de instalarse, en silencio.
    """
    from psglab.ui.shortcuts import ACTIONS, SIGNAL_ACTIONS

    faltantes = [
        metodo
        for metodo in [*ACTIONS.values(), *SIGNAL_ACTIONS.values()]
        if not hasattr(ventana, metodo)
    ]

    assert faltantes == []


# -- Los atajos no se acumulan ----------------------------------------------


def test_reinstalar_los_atajos_no_los_duplica(ventana: MainWindow):
    """Se instalan tres veces: al construir, al abrir un registro y al cambiar
    de nomenclatura. Cada llamada dejaba vivos los `QShortcut` de la anterior.

    Dos atajos con la misma tecla colgados de la misma ventana hacen que Qt no
    dispare **ninguno** y escriba "Ambiguous shortcut overload" por consola, así
    que la tecla dejaba de funcionar justo después de cambiar de nomenclatura.
    """
    antes = len(ventana.findChildren(QShortcut))

    install_shortcuts(ventana, None)
    install_shortcuts(ventana, None)

    assert len(ventana.findChildren(QShortcut)) == antes


def test_reinstalar_los_atajos_los_deja_funcionando(ventana: MainWindow):
    """Desinstalar de más sería peor que duplicar: la ventana se quedaría sin
    teclas y el programa seguiría andando, sin avisar de nada.
    """
    install_shortcuts(ventana, None)

    teclas = {
        atajo.key().toString()
        for atajo in ventana.findChildren(QShortcut)
        if atajo.key().toString()
    }

    assert "Right" in teclas
    assert "Ctrl+O" in teclas


def test_espacio_cuelga_de_la_senal_y_no_de_la_ventana(ventana: MainWindow):
    """Colgado de la ventana, Espacio le robaría la tecla a las casillas de
    Canales y a los botones: sólo tiene que andar con el foco en la señal."""
    from PySide6.QtCore import Qt

    espacios = [
        atajo
        for atajo in ventana.findChildren(QShortcut)
        if atajo.key().toString() == "Space"
    ]

    assert len(espacios) == 1
    assert espacios[0].parent() is ventana.signal_view
    assert espacios[0].context() == Qt.ShortcutContext.WidgetWithChildrenShortcut


def test_reinstalar_no_duplica_espacio(ventana: MainWindow):
    install_shortcuts(ventana, None)
    install_shortcuts(ventana, None)

    espacios = [
        a for a in ventana.findChildren(QShortcut) if a.key().toString() == "Space"
    ]
    assert len(espacios) == 1
