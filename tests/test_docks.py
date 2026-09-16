"""Tests de los paneles acoplables.

Lo que se verifica no es cómo se ven sino **las cuatro cosas que, si se rompen,
no dan error**:

- que cada dock tenga `objectName`, sin el cual `saveState()` no lo reconoce y
  la disposición no vuelve: Qt lo avisa por consola y sigue, que es la peor
  combinación posible;
- que la señal sea el widget central, que es todo el punto del refactor;
- que los seis paneles de análisis arranquen ocultos, porque un panel de
  conectividad vacío ocupando media pantalla desde el arranque es ruido;
- que la navegación **no** sea un dock, porque poder cerrarla dejaría sin salida
  a quien no conoce las flechas del teclado.
"""

import pytest
from PySide6.QtWidgets import QDockWidget

pytest.importorskip("pyqtgraph")

import psglab.ui.docks as docks  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402


@pytest.fixture
def ventana(qt_app) -> MainWindow:
    return create_main_window()


# -- La estructura -----------------------------------------------------------


def test_la_senal_es_el_widget_central(ventana: MainWindow):
    """Es todo el punto: antes compartía la ventana con cuatro paneles de
    altura fija y no se la podía agrandar."""
    assert ventana.centralWidget() is ventana.signal_view


def test_estan_los_diez_paneles(ventana: MainWindow):
    assert set(ventana.docks) == {
        "channels",
        "overview",
        "scoring",
        "histogram",
        "impedance",
        "psd",
        "metric",
        "connectivity",
        "filter",
        "ica",
    }


def test_cada_panel_tiene_nombre_de_objeto(ventana: MainWindow):
    """Sin él, `saveState()` no puede identificarlo y la disposición guardada
    no se restaura. Qt lo avisa por consola y sigue andando."""
    sin_nombre = [
        dock.windowTitle() for dock in ventana.docks.values() if not dock.objectName()
    ]

    assert sin_nombre == []


def test_los_nombres_de_objeto_no_se_repiten(ventana: MainWindow):
    """Dos docks con el mismo nombre hacen que `restoreState()` ponga uno donde
    va el otro."""
    nombres = [dock.objectName() for dock in ventana.docks.values()]

    assert len(set(nombres)) == len(nombres)


def test_los_cuatro_de_trabajo_arrancan_visibles(ventana: MainWindow):
    """Son los que se usan en cada ventana que se scorea."""
    ocultos = [
        clave
        for clave in ("channels", "overview", "scoring", "histogram")
        if ventana.docks[clave].isHidden()
    ]

    assert ocultos == []


def test_los_seis_de_analisis_arrancan_ocultos(ventana: MainWindow):
    visibles = [
        clave for clave, _ in docks.ORDEN_DE_ANALISIS if not ventana.docks[clave].isHidden()
    ]

    assert visibles == []


def test_la_navegacion_no_es_un_panel_acoplable(ventana: MainWindow):
    """Es la única vía de navegación con el mouse: poder cerrarla dejaría sin
    salida a quien no conoce las flechas del teclado."""
    assert not isinstance(ventana.navigation.parent(), QDockWidget)
    assert ventana.navigation_bar.isMovable() is False


# -- El contenedor de cada panel de análisis ---------------------------------


@pytest.mark.parametrize("clave, titulo", list(docks.ORDEN_DE_ANALISIS))
def test_el_contenedor_conserva_el_nombre_de_atributo(
    ventana: MainWindow, clave: str, titulo: str
):
    """Siguen llamándose `*_dialog` aunque ya no sean `QDialog`.

    `QDockWidget` responde a `windowTitle()`, `show()`, `hide()` e
    `isVisible()` igual que un diálogo, así que los ocho tests de entrega que
    preguntan por el título de estas ventanas siguieron pasando sin tocarse.
    Renombrarlos habría cambiado ocho tests para no ganar nada.
    """
    contenedor = getattr(ventana, f"{clave}_dialog")

    assert isinstance(contenedor, QDockWidget)
    assert contenedor.windowTitle() == titulo
    assert contenedor.widget() is getattr(ventana, f"{clave}_panel")


def test_mostrar_un_panel_de_analisis_lo_saca_de_oculto(ventana: MainWindow):
    """Se pregunta por `isHidden()` y no por `isVisible()`: la ventana de los
    tests nunca se muestra, y un hijo de una ventana no mostrada nunca es
    visible aunque se lo haya pedido explícitamente."""
    ventana.psd_dialog.show()

    assert not ventana.psd_dialog.isHidden()


# -- Guardar y restaurar la disposición --------------------------------------


def test_cerrar_un_panel_y_restaurar_lo_devuelve(ventana: MainWindow):
    """Es la salida cuando alguien arrastró un panel a un lugar del que no sabe
    cómo sacarlo, que con diez paneles deja de ser hipotético."""
    ventana.channels_dock.hide()

    ventana.restore_default_layout()

    assert not ventana.channels_dock.isHidden()


def test_la_disposicion_va_y_vuelve(ventana: MainWindow):
    ventana.scoring_dock.hide()
    estado = ventana.saveState()
    ventana.scoring_dock.show()

    ventana.restoreState(estado)

    assert ventana.scoring_dock.isHidden()


def test_restaurar_no_desarma_los_paneles(ventana: MainWindow):
    """Una disposición restaurada tiene que dejar cada panel con su contenido:
    `restoreState()` mueve contenedores, no widgets."""
    ventana.restore_default_layout()

    assert ventana.psd_dialog.widget() is ventana.psd_panel
    assert ventana.channels_dock.widget() is ventana.channel_selector


def test_la_ventana_recien_construida_no_guarda_al_cerrar(ventana: MainWindow):
    """Lo prende `create_main_window(restore_layout=True)`, que sólo llama
    `main.py`. Si estuviera prendido por omisión, la suite escribiría el
    archivo de preferencias de quien la corre."""
    assert ventana._guardar_disposicion_al_cerrar is False
