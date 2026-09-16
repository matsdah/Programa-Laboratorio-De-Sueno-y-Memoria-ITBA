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
        # El menú que se puebla desde el registro de herramientas.
        "tools_menu",
        # Los widgets del layout central.
        "signal_view",
        "channel_selector",
        "scoring_panel",
        "navigation",
        "overview_panel",
        "histogram_view",
        "tool_readout",
        # Los seis paneles de análisis y sus contenedores. **El panel y el
        # contenedor son atributos distintos a propósito**: los tests preguntan
        # por el título del contenedor y por el contenido del panel.
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
        # Archivo.
        "open_recording",
        "open_recording_dialog",
        "open_scoring",
        "open_scoring_dialog",
        "export",
        "export_scoring_dialog",
        # Navegación y scoring.
        "go_to_next_window",
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
    from psglab.ui.shortcuts import ACTIONS

    faltantes = [metodo for metodo in ACTIONS.values() if not hasattr(ventana, metodo)]

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
