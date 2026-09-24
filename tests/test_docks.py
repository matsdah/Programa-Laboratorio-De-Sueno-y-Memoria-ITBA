"""Tests de los paneles acoplables.

Lo que se verifica no es cómo se ven sino **las cuatro cosas que, si se rompen,
no dan error**:

- que cada dock tenga `objectName`, sin el cual `saveState()` no lo reconoce y
  la disposición no vuelve: Qt lo avisa por consola y sigue, que es la peor
  combinación posible;
- que la señal sea el widget central, que es todo el punto del refactor;
- que el programa abra sólo con la señal y el selector de canales (hito 24),
  y que la disposición no se recuerde de una apertura a otra;
- que la navegación **no** sea un dock, porque poder cerrarla dejaría sin salida
  a quien no conoce las flechas del teclado.
"""

import pytest
from PySide6.QtWidgets import QApplication, QDockWidget

pytest.importorskip("pyqtgraph")

import psglab.ui.docks as docks  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
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


def test_arrancan_visibles_los_canales_y_el_hipnograma(ventana: MainWindow):
    """Hito 24: la señal ocupa todo lo demás, y el scoring y el contexto se
    abren desde «Herramientas». **El hipnograma volvió en el hito 64**: en
    los programas de scoring es lo único que está siempre a la vista."""
    visibles = [clave for clave, dock in ventana.docks.items() if not dock.isHidden()]

    assert visibles == ["channels", "histogram"]


@pytest.mark.parametrize("clave", ["overview", "scoring", "histogram"])
def test_los_de_trabajo_se_pueden_mostrar_desde_su_accion(ventana: MainWindow, clave: str):
    """La acción de «Paneles» es la de Qt, que queda sin tildar al arrancar."""
    accion = ventana.docks[clave].toggleViewAction()

    assert not accion.isChecked()
    accion.trigger()
    assert not ventana.docks[clave].isHidden()


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


def test_restaurar_vuelve_a_la_vista_limpia(ventana: MainWindow):
    ventana.scoring_dock.show()
    ventana.psd_dialog.show()

    ventana.restore_default_layout()

    assert [c for c, d in ventana.docks.items() if not d.isHidden()] == ["channels", "histogram"]


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


def test_la_ventana_recien_construida_no_es_la_del_usuario(ventana: MainWindow):
    """Lo prende `create_main_window(saved_preferences=True)`, que sólo llama
    `main.py`. Si estuviera prendido por omisión, la suite escribiría el
    archivo de preferencias de quien la corre."""
    assert ventana._es_la_ventana_del_usuario is False


def test_la_disposicion_no_se_recuerda(qt_app, tmp_path, monkeypatch):
    """Hito 24: por más que un archivo de antes traiga una disposición con
    todos los paneles abiertos, la ventana del usuario abre con la limpia."""
    import json

    from psglab.ui import preferences

    vieja = create_main_window()
    for dock in vieja.docks.values():
        dock.show()
    estado = bytes(vieja.saveState().toBase64()).decode("ascii")
    archivo = tmp_path / "preferencias.json"
    archivo.write_text(
        json.dumps({"version": 1, "scheme_name": "Claro", "window_state": estado}),
        encoding="utf-8",
    )
    monkeypatch.setattr(preferences, "preferences_path", lambda: archivo)
    guardadas = archivo.read_text(encoding="utf-8")

    nueva = create_main_window(saved_preferences=True)
    nueva.close()

    assert [c for c, d in nueva.docks.items() if not d.isHidden()] == ["channels", "histogram"]
    assert archivo.read_text(encoding="utf-8") == guardadas


# -- El ancho de los paneles de abajo ------------------------------------------
#
# Hasta el hito 24 el scoring no bajaba de 690 px y la Übersicht de 480, y al
# abrir los tres el hipnograma se quedaba con unos 230 en una pantalla de
# 1400: la curva de la noche no se leía. Hasta el hito 26 el scoring iba en una
# sola fila y su mínimo, 464 px con Rechtschaffen y Kales, era más de lo que la
# proporción le pedía: el hipnograma perdía 94 px a 1280.


def mostrar_los_de_abajo(ventana: MainWindow, ancho: int = 1400) -> list[QDockWidget]:
    """Los tres paneles de abajo, abiertos desde su acción como lo hace
    «Paneles», con la ventana en pantalla para que haya reparto."""
    ventana.resize(ancho, 800)
    ventana.show()
    QApplication.processEvents()
    abajo = [ventana.docks[clave] for clave in docks.ANCHOS_DE_ABAJO]
    # **Sólo los ocultos**: el hipnograma arranca visible desde el hito 64, y
    # tildarlo otra vez lo ocultaría.
    for dock in abajo:
        if dock.isHidden():
            dock.toggleViewAction().trigger()
    for _ in range(3):
        QApplication.processEvents()
    return abajo


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_el_scoring_se_deja_angostar(ventana: MainWindow, nomenclatura: Nomenclature):
    """Ningún control vuelve al mínimo de Qt, que en Windows es de 75 px por
    botón aunque diga «W».

    El tope se arma con los mínimos declarados y no en píxeles fijos: el ancho
    de «Arousal» depende de la tipografía de cada plataforma —72 px en Windows,
    108 en la de los tests—.

    **Es el de la fila más ancha y no la suma de las dos**, que es todo el punto
    de apilarlas: en una sola fila el mínimo con Rechtschaffen y Kales era de
    464 px, más que lo que la proporción le pedía al scoring.
    """
    from psglab.core.nomenclature import stages_of
    from psglab.ui.scoring_panel import ANCHO_MINIMO_DE_BOTON, ANCHO_MINIMO_DEL_SELECTOR

    panel = ventana.scoring_panel
    panel.set_nomenclature(nomenclatura)
    botones = len(stages_of(nomenclatura))
    margenes = panel.layout().contentsMargins()
    fases = botones * ANCHO_MINIMO_DE_BOTON + panel._fila.spacing() * (botones - 1)
    controles = (
        ANCHO_MINIMO_DEL_SELECTOR
        + panel._arousal.minimumSizeHint().width()
        + panel._controles.spacing() * 2
    )
    tope = margenes.left() + margenes.right() + max(fases, controles)

    assert all(b.minimumWidth() == ANCHO_MINIMO_DE_BOTON for b in panel._botones.values())
    assert panel.minimumSizeHint().width() <= tope
    assert panel.minimumSizeHint().width() < fases + controles


def test_la_ubersicht_se_deja_angostar(ventana: MainWindow):
    assert ventana.overview_dock.minimumSizeHint().width() <= 140


@pytest.mark.parametrize("ancho", [1400, 1280])
@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_con_los_tres_de_abajo_el_hipnograma_es_el_mas_ancho(
    ventana: MainWindow, nomenclatura: Nomenclature, ancho: int
):
    """A 1280 es donde el scoring en una fila le ganaba lugar: el hipnograma
    quedaba en 635 px con Rechtschaffen y Kales."""
    ventana.scoring_panel.set_nomenclature(nomenclatura)
    try:
        overview, scoring, hipnograma = mostrar_los_de_abajo(ventana, ancho)

        assert hipnograma.width() > scoring.width()
        assert hipnograma.width() > overview.width()
        assert hipnograma.width() >= 600
    finally:
        ventana.close()


def test_volver_a_mostrar_el_hipnograma_le_devuelve_el_ancho(ventana: MainWindow):
    """Qt no recuerda un reparto pedido mientras el panel estaba oculto: por
    eso se reparte cada vez que uno aparece."""
    try:
        _, _, hipnograma = mostrar_los_de_abajo(ventana)
        antes = hipnograma.width()
        hipnograma.toggleViewAction().trigger()
        QApplication.processEvents()

        hipnograma.toggleViewAction().trigger()
        for _ in range(3):
            QApplication.processEvents()

        assert hipnograma.width() >= antes - 10
    finally:
        ventana.close()


def test_repartir_con_un_solo_panel_abajo_no_hace_nada(ventana: MainWindow):
    """No hay con quién repartir, y `resizeDocks()` con un solo panel lo
    achicaría hasta el ancho pedido."""
    ventana.histogram_dock.show()

    docks.repartir_abajo(ventana)

    assert not ventana.histogram_dock.isHidden()


# -- El ancho de la pila de análisis --------------------------------------------
#
# Hasta el hito 26 lo decidía Qt: al abrir el espectro, la pila se llevaba 640 px
# de una ventana de 1400 y a la señal le quedaban 478. Con 1280, 358.


@pytest.mark.parametrize("ancho", [1400, 1280])
def test_la_pila_de_analisis_se_lleva_la_fraccion_pedida(ventana: MainWindow, ancho: int):
    """La fracción, o el mínimo del panel si es mayor: Qt no deja achicarlo más."""
    try:
        ventana.resize(ancho, 800)
        ventana.show()
        QApplication.processEvents()
        pila = ventana.docks["psd"]
        pila.toggleViewAction().trigger()
        for _ in range(3):
            QApplication.processEvents()

        pedido = max(round(ancho * docks.FRACCION_DE_ANALISIS), pila.minimumSizeHint().width())
        assert abs(pila.width() - pedido) <= 10
    finally:
        ventana.close()


@pytest.mark.parametrize("ancho", [1400, 1280])
def test_con_un_analisis_abierto_la_senal_sigue_siendo_lo_mas_ancho(
    ventana: MainWindow, ancho: int
):
    """Es lo que estaba roto: la pila le ganaba a la señal, que es lo que el
    análisis está explicando."""
    try:
        ventana.resize(ancho, 800)
        ventana.show()
        QApplication.processEvents()
        pila = ventana.docks["psd"]
        pila.toggleViewAction().trigger()
        for _ in range(3):
            QApplication.processEvents()

        assert ventana.centralWidget().width() > pila.width()
    finally:
        ventana.close()


def test_una_pila_suelta_no_se_reparte(ventana: MainWindow):
    """Sacada a otra pantalla no comparte el borde con la señal."""
    pila = ventana.docks["psd"]
    pila.setFloating(True)
    pila.show()
    antes = pila.width()

    docks.repartir_derecha(ventana)

    assert pila.width() == antes


def test_el_selector_muestra_la_abreviatura(ventana: MainWindow):
    """«Rechtschaffen y Kales» entero ocupaba 160 px del panel. El nombre
    completo queda en el tooltip de cada opción y del selector."""
    from PySide6.QtCore import Qt

    selector = ventana.scoring_panel._nomenclaturas
    textos = [selector.itemText(i) for i in range(selector.count())]
    ayudas = [selector.itemData(i, Qt.ItemDataRole.ToolTipRole) for i in range(selector.count())]

    assert textos == ["R&K", "AASM"]
    assert ayudas == [n.value for n in Nomenclature]
    ventana.scoring_panel.set_nomenclature(Nomenclature.RK)
    assert selector.currentData() is Nomenclature.RK
    assert "Rechtschaffen y Kales" in selector.toolTip()


def test_cambiar_de_nomenclatura_oculta_los_botones_viejos_enseguida(
    ventana: MainWindow,
):
    """`deleteLater()` espera al ciclo de eventos; sin ocultarlos, dentro de un
    diálogo modal los botones viejos quedaban dibujados bajo los nuevos."""
    viejos = list(ventana.scoring_panel._botones.values())

    ventana.scoring_panel.set_nomenclature(Nomenclature.RK)

    assert viejos
    assert all(boton.isHidden() for boton in viejos)
