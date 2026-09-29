"""La interfaz por la ventana: la configuración, el teclado y los textos.

Es parte de la comprobación de entrega, separada de `test_entrega.py` en el
hito 79, con su misma regla: todo pasa por `MainWindow`.

Cubre que las preferencias lleguen a donde tienen efecto, que el teclado
llegue a todo y que un atajo no le gane al control con el foco (hito 67), lo
que dicen los carteles y los botones que arma Qt, y el cartel de los errores
inesperados (hito 68). Son los defectos que ningún test de una pieza ve,
porque viven entre la pieza y la ventana.
"""

import dataclasses
from pathlib import Path

import numpy as np
import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.core.nomenclature import SleepStage, stages_of  # noqa: E402
# Los módulos donde se buscan los nombres que la suite reemplaza (hito 76):
# reemplazarlos en `main_window` no tendría efecto, porque ahí ya no se usan.
import psglab.ui.window_analysis as analysis_mod  # noqa: E402
import psglab.ui.window_annotation as annotation_mod  # noqa: E402
import psglab.ui.window_files as files_mod  # noqa: E402
from psglab.ui import preferences as preferencias_mod  # noqa: E402
from psglab.ui import theme  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from psglab.utils.errors import PsgLabError  # noqa: E402

from conftest import FRECUENCIA_BV, escribir_brainvision  # noqa: E402
from entrega_comun import (  # noqa: E402, F401
    VENTANAS,
    a_la_vista,
    anotar_en,
    clic_derecho,
    confirmacion,
    dialogo_de_guardado,
    elige_canal,
    elige_en_el_menu,
    elige_opciones,
    teclear,
    ventana,
    ventana_con_dos_eeg,
)


# -- La configuración: lo que la ventana hace con las preferencias -------------------
#
# Se verifica por la ventana y no por `Preferences`, que ya tiene sus tests: lo
# que importa acá es que cada preferencia **llegue** a donde tiene efecto. Una
# opción guardada que nadie lee es la clase de camino muerto que costó el hito 9.


@pytest.fixture
def fuente_restaurada(qt_app):
    """La tipografía es global a la aplicación: se deja como estaba."""
    anterior = QFont(QApplication.font())
    yield
    QApplication.setFont(anterior)


@pytest.fixture
def escrituras(monkeypatch) -> list[object]:
    """Registra cualquier intento de escribir el archivo de preferencias."""
    intentos: list[object] = []
    monkeypatch.setattr(
        preferencias_mod, "save", lambda *args, **kwargs: intentos.append(args)
    )
    return intentos


def _con(ventana: MainWindow, **cambios: object) -> None:
    ventana.apply_preferences(ventana.current_preferences.with_changes(**cambios))


def test_aplicar_preferencias_no_escribe_el_archivo_de_quien_corre_los_tests(
    ventana: MainWindow, escrituras: list[object]
):
    """**La ventana de los tests no es la del usuario.** Sólo la que abre
    `main.py` escribe el archivo; si no, correr la suite pisaría la
    configuración de quien la corre."""
    _con(ventana, psd_log_power=False)

    assert escrituras == []


def test_armar_la_ventana_tampoco_escribe_el_archivo(escrituras: list[object], qt_app):
    """**Desde el hito 78 el constructor aplica las preferencias de fábrica**,
    y aplicar es lo que en la ventana del usuario las guarda. La de los tests no
    es la del usuario, así que armarla no puede escribir nada."""
    create_main_window()

    assert escrituras == []


def test_elegir_un_esquema_tampoco_escribe_el_archivo(
    ventana: MainWindow, escrituras: list[object]
):
    """Antes sí lo escribía: `set_color_scheme()` guardaba siempre que no se le
    pasara `remember=False`, fuera quien fuera el que había abierto la
    ventana."""
    anterior = theme.current()
    try:
        ventana.set_color_scheme(theme.NOCTURNO)
        assert escrituras == []
    finally:
        ventana.set_color_scheme(anterior, remember=False)


def test_el_espectro_usa_el_metodo_elegido(
    ventana: MainWindow, elige_canal, monkeypatch
):
    metodos: list[object] = []
    original = analysis_mod.compute_psd

    def espiando(*args: object, **kwargs: object) -> object:
        metodos.append(kwargs.get("method"))
        return original(*args, **kwargs)

    monkeypatch.setattr(analysis_mod, "compute_psd", espiando)
    _con(ventana, psd_method="multitaper")
    elige_canal("C3")

    ventana.show_psd_dialog()

    assert metodos == ["multitaper"]
    assert not ventana.carteles


def test_el_espectro_usa_las_bandas_elegidas(ventana: MainWindow, elige_canal):
    """La tabla y el sombreado muestran las bandas del usuario, no las de
    fábrica."""
    bandas = {"Lenta": (0.5, 2.0), "Huso": (11.0, 16.0)}
    ventana.apply_preferences(ventana.current_preferences.with_bands(bandas))
    elige_canal("C3")

    ventana.show_psd_dialog()

    assert set(ventana.psd_panel.band_powers()) == set(bandas)
    assert ventana.psd_panel.band_ranges() == bandas
    assert not ventana.carteles


def test_la_conectividad_ofrece_las_mismas_bandas_que_el_espectro(ventana: MainWindow):
    """Dos definiciones de «sigma» en el mismo programa serían una trampa."""
    ventana.apply_preferences(
        ventana.current_preferences.with_bands({"Huso": (11.0, 16.0)})
    )

    ventana.show_connectivity_dialog()

    assert ventana.connectivity_panel.request.options("banda") == ["Huso"]


def test_el_eje_del_espectro_sigue_a_la_configuracion(ventana: MainWindow):
    _con(ventana, psd_log_power=False)

    assert not ventana.psd_panel.uses_log_power


def test_el_color_de_una_clase_llega_a_la_sesion_abierta(ventana: MainWindow):
    """Sin reabrir el registro."""
    ventana.apply_preferences(
        ventana.current_preferences.with_annotation_color("Spindle", "#ff8800")
    )

    assert ventana.session.annotations.color_of("Spindle") == "#ff8800"
    assert not ventana.carteles


def test_cambiar_el_color_de_una_clase_no_borra_lo_que_dibuja_otra_herramienta(
    ventana: MainWindow,
):
    """**El visualizador dibuja lo de una sola herramienta a la vez**, y quien
    avisa reemplaza todo lo dibujado. Avisar desde el anotador cuando la activa
    es la ocupación borraba sus líneas de la pantalla: seguían medidas, pero ya
    no se veían."""
    from psglab.tools.occupancy import OccupancyLine

    ventana.tool_controller.toggle("occupancy", True)
    ventana.tool_controller.tools["occupancy"].add_line(OccupancyLine(0.2, 0.0, 0.6, 0.0))
    dibujadas = len(ventana.signal_view.overlay_layer.items)
    assert dibujadas > 0

    ventana.apply_preferences(
        ventana.current_preferences.with_annotation_color("Spindle", "#ff8800")
    )

    assert len(ventana.signal_view.overlay_layer.items) == dibujadas


def test_con_el_anotador_activo_la_banda_cambia_de_color_enseguida(
    ventana: MainWindow,
):
    """El otro lado del test de arriba: cuando el que dibuja es el anotador, la
    banda tiene que tomar el color nuevo sin esperar a la próxima flecha."""
    ventana.tool_controller.toggle("annotator", True)
    ventana.tool_controller.tools["annotator"].create_annotation("Spindle", 250, 250)

    ventana.apply_preferences(
        ventana.current_preferences.with_annotation_color("Spindle", "#ff8800")
    )

    bandas = ventana.signal_view.overlay_layer.annotation_bands
    assert bandas is not None
    assert "#ff8800" in [color for _, _, color in bandas.bands]
    assert not ventana.carteles


def test_el_color_de_una_clase_sobrevive_a_abrir_otro_registro(
    ventana: MainWindow, tmp_path: Path
):
    """Una clase que el usuario definió una vez queda disponible en cualquier
    registro."""
    ventana.apply_preferences(
        ventana.current_preferences.with_annotation_color("Apnea", "#00aa88")
    )

    ventana.open_recording(
        escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 2)
    )

    assert ventana.session.annotations.color_of("Apnea") == "#00aa88"
    assert not ventana.carteles


def test_lo_de_la_solapa_otras_espera_al_proximo_registro(
    ventana: MainWindow, tmp_path: Path
):
    """El registro abierto no cambia de página ni de nomenclatura bajo los pies
    del usuario; el próximo arranca con lo elegido."""
    _con(ventana, open_view_seconds=60.0, open_nomenclature="RK")

    assert ventana.session.viewport.span_seconds == WINDOW_SECONDS

    ventana.open_recording(
        escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * VENTANAS)
    )

    assert ventana.session.viewport.span_seconds == 60.0
    assert ventana.session.scoring.nomenclature.name == "RK"
    assert not ventana.carteles


def test_el_histograma_arranca_en_hora_real_si_se_eligio(
    ventana: MainWindow, tmp_path: Path
):
    _con(ventana, open_clock_axis=True)

    ventana.open_recording(
        escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * VENTANAS)
    )

    assert ventana.session.recording.start_time is not None
    assert ventana.accion_eje_en_hora.isChecked()
    assert not ventana.carteles


def test_sin_hora_de_inicio_esa_preferencia_no_muestra_un_cartel(
    ventana: MainWindow, tmp_path: Path, monkeypatch
):
    """Pedir la hora real a un registro que no la informa es un cartel de
    error. Mostrarlo en cada apertura, por una preferencia elegida para otros
    archivos, sería castigar al usuario por haberla elegido."""
    _con(ventana, open_clock_axis=True)
    original = files_mod.read_recording
    monkeypatch.setattr(
        files_mod,
        "read_recording",
        lambda ruta: dataclasses.replace(original(ruta), start_time=None),
    )
    ventana.accion_eje_en_hora.setChecked(False)

    ventana.open_recording(
        escribir_brainvision(tmp_path / "sin-hora", segundos=WINDOW_SECONDS * 2)
    )

    assert not ventana.accion_eje_en_hora.isChecked()
    assert not ventana.carteles


def test_la_tipografia_elegida_llega_tambien_a_los_nombres_de_canal(
    ventana: MainWindow, fuente_restaurada
):
    """Los nombres son ítems de pyqtgraph y no siguen solos a la aplicación."""
    _con(ventana, font_size=17)

    assert QApplication.font().pointSize() == 17
    assert ventana.signal_view.channel_axis.lanes()
    assert ventana.signal_view.channel_axis._fuente.pointSize() == 17


def test_se_puede_volver_a_la_tipografia_del_sistema(
    ventana: MainWindow, fuente_restaurada
):
    """**Vuelve el tamaño y no la familia**, desde el hito 43: la familia es la
    del programa y no se elige. Lo que se suelta al destildar la casilla es el
    tamaño."""
    del_sistema = QFont(ventana._fuente_del_sistema)
    _con(ventana, font_size=17)

    _con(ventana, font_size=None)

    assert QApplication.font().pointSize() == del_sistema.pointSize()


def test_la_tipografia_del_programa_se_aplica_si_esta(
    ventana: MainWindow, fuente_restaurada
):
    """**La única desde el hito 43.** Se registra acá adentro: la suite no pasa
    por `create_application()`, que es quien lo hace al arrancar."""
    from psglab.ui import fonts

    fonts.register_bundled_fonts()

    _con(ventana, font_size=13)

    assert QApplication.font().family() == fonts.UI_FONT_FAMILY


def test_sin_los_archivos_queda_la_del_sistema(
    ventana: MainWindow, fuente_restaurada, monkeypatch
):
    """**`setFamily()` con un nombre que no existe no avisa**: Qt sustituye por
    lo que le parece, que suele ser peor que la del sistema. Con la del
    programa como la única, eso le pasaría a cualquiera que instale sin los
    archivos."""
    from psglab.ui import fonts

    del_sistema = QFont(ventana._fuente_del_sistema)
    monkeypatch.setattr(fonts, "available_family", lambda *_: None)

    _con(ventana, font_size=13)

    assert QApplication.font().family() == del_sistema.family()


def test_aplicar_algo_que_no_son_preferencias_avisa_sin_romper(ventana: MainWindow):
    ventana.apply_preferences({"font_size": 12})

    assert ventana.carteles


# -- La ventana de configuración, abierta desde la principal -----------------------


def test_la_configuracion_muestra_lo_vigente(ventana: MainWindow):
    _con(ventana, psd_method="multitaper")

    ventana.show_settings_dialog()

    assert ventana.settings_dialog.preferences == ventana.current_preferences
    assert ventana.settings_dialog.psd_method.currentData() == "multitaper"
    ventana.settings_dialog.close()


def test_la_configuracion_ofrece_las_clases_del_registro_abierto(ventana: MainWindow):
    """Incluida una que el usuario creó en esta sesión."""
    ventana.session.annotations.add_label("Apnea")

    ventana.show_settings_dialog()

    assert "Apnea" in ventana.settings_dialog.annotation_buttons
    ventana.settings_dialog.close()


def test_un_cambio_en_la_configuracion_llega_a_la_ventana(ventana: MainWindow):
    """**El camino, no la pieza**: la casilla de la ventana de configuración
    termina cambiando el eje del espectro de la principal."""
    ventana.show_settings_dialog()

    ventana.settings_dialog.log_power.setChecked(False)

    assert not ventana.current_preferences.psd_log_power
    assert not ventana.psd_panel.uses_log_power
    ventana.settings_dialog.close()


def test_el_color_elegido_en_la_configuracion_llega_a_la_sesion(ventana: MainWindow):
    ventana.show_settings_dialog()

    ventana.settings_dialog.annotation_buttons["Spindle"].choose("#ff8800")

    assert ventana.session.annotations.color_of("Spindle") == "#ff8800"
    ventana.settings_dialog.close()


def test_volver_a_abrir_la_configuracion_refleja_lo_cambiado_afuera(
    ventana: MainWindow,
):
    """Un esquema que cambia sin pasar por el menú —al aplicar el archivo de
    preferencias, por ejemplo— tiene que quedar tildado igual: desde el hito 35
    el menú «Ver» es el único lugar donde se ve cuál está puesto."""
    anterior = theme.current()
    try:
        ventana.set_color_scheme(theme.NOCTURNO, remember=False)

        assert ventana.acciones_de_esquema["Nocturno"].isChecked()
        assert not ventana.acciones_de_esquema["Sereno"].isChecked()
    finally:
        ventana.set_color_scheme(anterior, remember=False)


def test_la_configuracion_se_abre_sin_registro(qt_app):
    """Con las clases de fábrica, que es lo que el usuario va a tener."""
    principal = create_main_window()

    principal.show_settings_dialog()

    assert set(principal.settings_dialog.annotation_buttons) >= {"Spindle"}
    principal.settings_dialog.close()


# -- Recorrer los paneles con el teclado ---------------------------------------------


def test_f6_arranca_en_la_senal_y_pasa_al_panel_siguiente(ventana: MainWindow):
    paneles = ventana.focusable_panes()
    assert ventana.current_pane() is ventana.signal_view

    ventana.focus_next_pane()

    assert ventana.current_pane() is paneles[1]


def test_f6_da_la_vuelta(ventana: MainWindow):
    for _ in ventana.focusable_panes():
        ventana.focus_next_pane()

    assert ventana.current_pane() is ventana.signal_view


def test_mayus_f6_vuelve_para_atras(ventana: MainWindow):
    ventana.focus_previous_pane()

    assert ventana.current_pane() is ventana.focusable_panes()[-1]


def test_los_paneles_cerrados_no_se_recorren(ventana: MainWindow):
    """Dejar el foco en algo que no se ve es peor que no moverlo."""
    cerrado = ventana.focusable_panes()[1]
    cerrado.hide()

    assert cerrado not in ventana.focusable_panes()


def test_los_paneles_de_analisis_cerrados_al_arrancar_no_se_recorren(
    ventana: MainWindow,
):
    assert ventana.psd_dock not in ventana.focusable_panes()

    ventana.psd_dock.show()

    assert ventana.psd_dock in ventana.focusable_panes()


def test_todos_los_paneles_tienen_un_nombre_para_el_lector_de_pantalla(
    ventana: MainWindow,
):
    """Sin él, un lector anuncia «grupo» o nada al llegar al panel."""
    assert ventana.signal_view.accessibleName()
    for dock in ventana.docks.values():
        assert dock.widget().accessibleName(), dock.windowTitle()


def test_la_senal_acepta_el_foco_del_teclado(ventana: MainWindow):
    """Si no, F6 no tendría dónde dejarlo al volver a ella."""
    assert ventana.signal_view.focusPolicy() & Qt.FocusPolicy.TabFocus


def test_f6_mueve_el_foco_de_verdad(ventana: MainWindow):
    """**Lo que el recorrido cree y lo que pasa tienen que coincidir.** El panel
    de contexto no tiene nada que tome el foco, y cuando se lo recorría F6 lo
    daba por visitado mientras el foco seguía en el panel anterior."""
    ventana.resize(1200, 800)
    ventana.show()
    ventana.activateWindow()
    QApplication.processEvents()
    try:
        for _ in ventana.focusable_panes():
            ventana.focus_next_pane()
            QApplication.processEvents()
            panel = ventana.current_pane()
            destino = panel.widget() if hasattr(panel, "widget") else panel
            foco = QApplication.focusWidget()
            assert foco is not None
            assert foco is destino or destino.isAncestorOf(foco), panel.windowTitle()
    finally:
        ventana.close()


def test_el_panel_de_contexto_no_se_recorre(ventana: MainWindow):
    """Se pinta a mano y no tiene controles: no hay dónde dejar el foco."""
    assert ventana.docks
    contexto = [d for d in ventana.docks.values() if d.widget() is ventana.overview_panel]
    assert contexto
    assert contexto[0] not in ventana.focusable_panes()


# -- Hito 30: las decisiones de la verificación -------------------------------


def test_la_cantidad_de_vecinas_de_la_ubersicht_se_elige_en_la_configuracion(
    ventana: MainWindow,
):
    """V3_F no tenía camino desde la ventana: `set_span()` no lo llamaba nadie y
    la cantidad sólo se cambiaba editando `config.py`."""
    ventana.show()
    ventana.overview_dock.show()
    ventana._go_to_window(3)

    ventana.apply_preferences(
        ventana.current_preferences.with_changes(overview_before=2, overview_after=0)
    )

    mostradas = [(v.index, v.is_current) for v in ventana.tool_controller.tools["overview"].windows()]
    assert mostradas == [(1, False), (2, False), (3, True)]
    assert len(ventana.overview_panel.rectangles()) == 3


@pytest.mark.parametrize("clave", ["psd", "metric", "connectivity", "ica"])
def test_un_panel_vacio_dice_desde_donde_se_pide(ventana: MainWindow, clave: str):
    """Desde «Herramientas» los paneles de resultados aparecían en blanco.

    **La ruta que dice tiene que llevar al panel**: se la sigue en el menú de
    verdad y se comprueba que lo muestra. Así la pista no puede quedar
    mandando a una entrada renombrada.
    """
    from psglab.ui.menus import menu_path

    panel = getattr(ventana, f"{clave}_panel")
    ventana.docks[clave].toggleViewAction().trigger()
    que_falta, _, pista = panel.visible_hint().partition("<br>")
    # Primero qué falta (hito 65), y después desde dónde se pide.
    assert que_falta.endswith(".") and "Se pide" not in que_falta
    assert pista.startswith("Se pide desde ")

    # Los que llevan sus parámetros arriba lo dicen en el último renglón.
    renglones = pista.removeprefix("Se pide desde ").split("<br>")
    con_calcular = clave != "ica"
    assert (renglones[-1] == "o con «Calcular», arriba") is con_calcular
    if con_calcular:
        renglones = renglones[:-1]
    # Una ruta por renglón: la métrica tiene dos.
    rutas = [renglon.removeprefix("o desde ") for renglon in renglones]
    for ruta in rutas:
        metodo = next(
            accion.data()
            for de_la_barra in ventana.menuBar().actions()
            if de_la_barra.menu() is not None
            for accion in de_la_barra.menu().actions()
            if accion.data() and menu_path(ventana, accion.data()) == ruta
        )
        assert metodo.startswith("show_") and metodo.endswith("_dialog")


def test_filtrar_vacia_los_resultados_de_la_señal_anterior(
    ventana: MainWindow, elige_canal
):
    """Después de filtrar, el espectro seguía siendo el de la señal sin filtrar,
    con el mismo título y sin decirlo."""
    elige_canal("C3")
    ventana.show_psd_dialog()
    assert ventana.psd_panel.channels() == ["C3"]

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()
    ventana.wait_for_background()

    assert ventana.psd_panel.channels() == []
    assert ventana.psd_panel.caption() == ""
    assert ventana.psd_panel.visible_hint().startswith("No hay ningún espectro calculado.")


def test_volver_a_la_original_vacia_los_resultados_de_la_procesada(
    ventana: MainWindow, elige_canal
):
    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()
    ventana.wait_for_background()
    elige_canal("C3")
    ventana.show_psd_dialog()

    ventana.restore_original_recording()

    assert ventana.psd_panel.channels() == []
    assert not ventana.carteles


# -- Hito 31: lo que encontró el recorrido manual ----------------------------


def textos_de_herramientas(ventana: MainWindow) -> list[str]:
    return [accion.text() for accion in ventana.tools_menu.actions()]


def test_calcular_no_renombra_el_menu_de_herramientas(
    ventana: MainWindow, elige_opciones
):
    """El título de un dock es el texto de su entrada en «Herramientas», y la
    ventana se lo cambiaba con cada cálculo: el menú decía «Espectro de «C3» —
    ventana 1». La descripción va ahora en el panel."""
    antes = textos_de_herramientas(ventana)
    canal = ventana.session.visible_channels[0]
    elige_opciones(
        (canal, True),
        (canal, True), ("permutation_entropy", True),
        ("Delta", True),
        ("Delta", True),
    )

    ventana.show_psd_dialog()
    assert f"«{canal}»" in ventana.psd_panel.caption()
    ventana.show_complexity_dialog()
    ventana.show_connectivity_dialog()
    assert "Delta" in ventana.connectivity_panel.caption()
    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()
    assert "noche" in ventana.metric_panel.caption()

    assert textos_de_herramientas(ventana) == antes
    assert not ventana.carteles


def test_main_py_precalienta_en_segundo_plano(qt_app, monkeypatch):
    """Las dos esperas que se cobraban la primera vez: las importaciones que
    los lectores le piden a MNE al abrir el primer registro, y la compilación
    de `antropy`. `main.py` las pide al arrancar, en otro hilo."""
    import threading

    import psglab.ui.window_analysis as modulo

    hecho: list[str] = []
    monkeypatch.setattr(
        modulo, "warm_up_readers",
        lambda: hecho.append(f"lectores:{threading.current_thread().name}"),
    )
    monkeypatch.setattr(
        modulo, "warm_up", lambda: hecho.append(f"antropy:{threading.current_thread().name}")
    )

    create_main_window(warm_up=True)
    for hilo in threading.enumerate():
        if hilo.name == "precalentar-analisis":
            hilo.join(timeout=5)

    # **Los lectores primero**: abrir un registro es lo primero que hace el
    # usuario, y compilar `antropy` no lo tiene esperando a él.
    assert hecho == ["lectores:precalentar-analisis", "antropy:precalentar-analisis"]


def test_la_suite_no_precalienta(qt_app, monkeypatch):
    """Cada ventana de la suite lanzaría un hilo."""
    import psglab.ui.window_analysis as modulo

    llamadas: list[bool] = []
    monkeypatch.setattr(modulo, "warm_up", lambda: llamadas.append(True))
    monkeypatch.setattr(modulo, "warm_up_readers", lambda: llamadas.append(True))

    create_main_window()

    assert llamadas == []


# -- Hito 32: los pendientes del TODO -----------------------------------------


def test_el_contador_de_la_lupa_se_pone_en_cero_desde_el_menu(ventana: MainWindow):
    lupa = ventana.tool_controller.tools["magnifier"]
    ventana.tool_controller.toggle("magnifier", True)
    lupa.on_mouse_press(1.0, 0.0, "left")
    lupa.on_mouse_press(2.0, 0.0, "left")
    accion = next(
        a for a in ventana.tools_menu.actions() if a.data() == "reset_magnifier_count"
    )

    accion.trigger()

    assert lupa.click_count == 0
    assert "0" in ventana.tool_readout.text()


def test_los_ajustes_de_herramienta_llegan_a_las_herramientas(ventana: MainWindow):
    ventana.apply_preferences(
        ventana.current_preferences.with_changes(
            amplitude_band_uv=100.0, magnifier_radius_seconds=2.5, magnifier_zoom=8.0
        )
    )

    assert ventana.tool_controller.tools["amplitude_band"].height_uv == 100.0
    ventana.tool_controller.toggle("magnifier", True)
    ventana.tool_controller.tools["magnifier"].on_mouse_move(10.0, 0.0)
    (circulo,) = ventana.tool_controller.tools["magnifier"].overlays()
    assert (circulo.radius_seconds, circulo.zoom) == (2.5, 8.0)


@pytest.fixture
def ventana_con_un_plano(qt_app, tmp_path, monkeypatch):
    """Dos EEG, el primero en cero: un electrodo desconectado."""
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "plano",
        segundos=WINDOW_SECONDS * 3,
        canales=[("C3", "µV"), ("C4", "µV"), ("EOG-izq", "µV")],
    )
    eeg = vhdr.with_suffix(".eeg")
    datos = np.frombuffer(eeg.read_bytes(), dtype="<i2").reshape(-1, 3).copy()
    datos[:, 0] = 0
    eeg.write_bytes(datos.tobytes())
    principal.open_recording(vhdr)
    principal.carteles = carteles
    return principal


def test_el_espectro_de_un_canal_plano_lo_dice(ventana_con_un_plano, elige_opciones):
    """Salía un gráfico vacío en escala logarítmica, sin explicación."""
    elige_opciones(("C3", True))
    ventana_con_un_plano.show_psd_dialog()
    assert "plano" in ventana_con_un_plano.psd_panel.caption()

    elige_opciones(("C4", True))
    ventana_con_un_plano.show_psd_dialog()
    assert "plano" not in ventana_con_un_plano.psd_panel.caption()


def test_la_conectividad_dice_que_canal_plano_baja_el_promedio(
    ventana_con_un_plano, elige_opciones
):
    elige_opciones(("Delta", True))
    ventana_con_un_plano.show_connectivity_dialog()
    assert "«C3»" in ventana_con_un_plano.connectivity_panel.caption()
    assert "baja el promedio" in ventana_con_un_plano.connectivity_panel.caption()


def test_la_metrica_de_un_canal_plano_lo_dice(ventana_con_un_plano, elige_opciones):
    """Higuchi da NaN en todas las ventanas, y el panel quedaba vacío."""
    elige_opciones(("C3", True), ("higuchi_fractal_dimension", True))
    ventana_con_un_plano.show_complexity_dialog()
    assert "«C3» está plano en 3 de 3 ventanas" in ventana_con_un_plano.metric_panel.caption()


def test_importar_impedancias_de_un_archivo_vacio_avisa(
    ventana: MainWindow, tmp_path: Path, monkeypatch
):
    """Devolvía un diccionario vacío, que es correcto como biblioteca, y la
    ventana no hacía nada ni decía nada."""
    vacio = tmp_path / "impedancias.txt"
    vacio.write_text("# sólo un comentario\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(vacio), ""))
    )
    ventana.show_impedance_dialog()
    antes = ventana.impedance_panel.values()

    ventana.load_impedances_dialog()

    assert ventana.impedance_panel.values() == antes
    assert len(ventana.carteles) == 1
    assert "impedancias.txt" in ventana.carteles[0]


# -- Un archivo de preferencias roto no impide arrancar (hito 33) ------------


def test_una_banda_mal_escrita_en_las_preferencias_no_impide_arrancar(
    qt_app, tmp_path: Path, monkeypatch
):
    """El caso de la auditoría: con `[["Delta", 0.5]]` en el archivo,
    `create_application()` elevaba `IndexError` y el programa no abría. Ahora
    arranca, esa banda vuelve a las de fábrica y el resto se conserva."""
    import json

    from psglab.app import _esquema_guardado

    archivo = tmp_path / "preferencias.json"
    archivo.write_text(
        json.dumps({"psd_bands": [["Delta", 0.5]], "overview_before": 2}), encoding="utf-8"
    )
    monkeypatch.setattr(preferencias_mod, "preferences_path", lambda: archivo)

    assert isinstance(_esquema_guardado(), theme.ColorScheme)
    nueva = create_main_window(saved_preferences=True)

    assert nueva.current_preferences.psd_bands is None
    assert nueva.current_preferences.overview_before == 2
    nueva.close()


def test_un_archivo_de_preferencias_danado_se_avisa_al_arrancar(
    qt_app, tmp_path: Path, monkeypatch
):
    """`load()` escribe el mensaje para el investigador y hasta el hito 33 nadie
    lo mostraba: el archivo roto se perdía sin aviso la primera vez que se
    cambiaba algo. Sale con la ventana ya armada, en la vuelta siguiente del
    ciclo de eventos."""
    archivo = tmp_path / "preferencias.json"
    archivo.write_text("{esto no es json", encoding="utf-8")
    monkeypatch.setattr(preferencias_mod, "preferences_path", lambda: archivo)
    carteles: list[str] = []
    monkeypatch.setattr(MainWindow, "_show_error", lambda _v, error, accion=None: carteles.append(str(error)))

    nueva = create_main_window(saved_preferences=True)
    assert carteles == []
    QApplication.processEvents()

    assert len(carteles) == 1 and "preferencias" in carteles[0]
    assert archivo.read_text(encoding="utf-8") == "{esto no es json"
    nueva.close()


# -- Lo que se mostraba sin explicar (hito 33) -------------------------------


def test_la_barra_de_estado_no_se_queda_calculando(ventana: MainWindow, elige_opciones):
    """El aviso de «trabajando» no vencía y nadie lo borraba: con el resultado
    ya en pantalla, la barra seguía diciendo que estaba calculando."""
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    assert "…" not in ventana.statusBar().currentMessage()


@pytest.mark.parametrize("sobrescribe", [True, False])
def test_el_nombre_sin_extension_pregunta_antes_de_pisar(
    ventana: MainWindow, tmp_path: Path, dialogo_de_guardado, confirmacion,
    sobrescribe: bool,
):
    """La extensión se agrega **después** de que el diálogo confirmó, así que el
    archivo que se iba a pisar no era el que el usuario vio: escribía «noche» y
    se sobrescribía «noche.txt» sin preguntar."""
    ya_estaba = tmp_path / "noche.txt"
    ya_estaba.write_text("lo que habia antes", encoding="utf-8")
    dialogo_de_guardado["respuesta"] = tmp_path / "noche"
    confirmacion["respuesta"] = sobrescribe

    ventana.export_scoring_dialog("txt")

    piso = ya_estaba.read_text(encoding="utf-8") != "lo que habia antes"
    assert piso is sobrescribe
    assert confirmacion["preguntas"][0]["accion"] == "Reemplazar"
    assert "noche.txt" in confirmacion["preguntas"][0]["pregunta"]


def test_el_espectro_dice_que_una_banda_queda_fuera(
    ventana: MainWindow, elige_opciones
):
    """Una banda por encima de lo que el registro alcanza da potencia cero, y un
    cero no se distingue de un cero real."""
    nyquist = FRECUENCIA_BV / 2
    ventana.apply_preferences(
        ventana.current_preferences.with_bands(
            {"Delta": (0.5, 4.0), "Alta": (nyquist + 10, nyquist + 40)}
        )
    )
    elige_opciones(("C3", True))

    ventana.show_psd_dialog()

    assert "Alta" in ventana.psd_panel.caption()
    assert f"{nyquist:g} Hz" in ventana.psd_panel.caption()


# -- Los botones que arma Qt, en español (hito 53) ---------------------------


def _botones(dialogo) -> list[str]:
    from PySide6.QtWidgets import QPushButton

    dialogo.show()
    textos = [b.text().replace("&", "") for b in dialogo.findChildren(QPushButton)]
    dialogo.close()
    return textos


def test_la_traduccion_de_qt_se_carga(qt_app):
    """**Hasta el hito 53 no se cargaba ninguna**, y los botones estándar salían
    en inglés en un programa escrito en español."""
    from psglab.app import install_qt_translations

    assert install_qt_translations(qt_app)


def test_el_cartel_de_error_muestra_el_detalle_en_espanol(ventana: MainWindow):
    """Es el cartel de `_show_error()`, con el desplegable de la causa técnica.
    Decía «Show Details... / OK»."""
    cartel = QMessageBox(ventana)
    cartel.setText("No se pudo completar la operación")
    cartel.setDetailedText("detalle técnico")

    textos = _botones(cartel)

    assert not any(t.startswith(("Show", "OK")) for t in textos)
    assert any("detalles" in t.lower() for t in textos)


def test_el_dialogo_de_la_clase_dice_aceptar_y_cancelar(ventana: MainWindow):
    """Es el diálogo que pregunta la clase al anotar y al corregirla. Decía
    «OK / Cancel»."""
    dialogo = QInputDialog(ventana)
    dialogo.setComboBoxItems(["Spindle"])

    assert sorted(_botones(dialogo)) == ["Aceptar", "Cancelar"]


# -- Los faltantes del prototipo, por la ventana (hito 54) -------------------


def test_la_metrica_marca_la_epoca_actual(ventana: MainWindow, elige_opciones):
    """Moverse de época mueve la marca de la curva, sin volver a calcular."""
    elige_opciones(("C3", True), ("permutation_entropy", True))
    ventana.show_complexity_dialog()

    ventana._go_to_window(3)

    assert ventana.metric_panel._marca_actual.value() == 4.0


def test_el_eje_de_la_metrica_sigue_al_del_hipnograma(ventana: MainWindow, elige_opciones):
    """**Los dos gráficos de la noche hablaban unidades distintas**: el
    hipnograma podía ir en hora y la métrica decía «Ventana» siempre."""
    elige_opciones(("C3", True), ("permutation_entropy", True))
    ventana.show_complexity_dialog()
    eje = ventana.metric_panel.grafico.getPlotItem().getAxis("bottom")

    ventana.set_histogram_time_axis(True)
    assert "Hora" in eje.labelString()
    assert eje._tickLevels[0][0] == (1.0, "13:00")

    ventana.set_histogram_time_axis(False)
    assert "Ventana" in eje.labelString()
    assert eje._tickLevels[0][0] == (1.0, "1")
    assert not ventana.carteles


def test_la_ica_dice_cuanta_varianza_explica_cada_componente(
    ventana_con_dos_eeg: MainWindow,
):
    """Se calcula en el mismo hilo que el ajuste, y llega a la lista."""
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()

    lista = ventana_con_dos_eeg.ica_panel.lista
    textos = [lista.item(fila).text() for fila in range(lista.count())]
    assert textos and all(texto.endswith("%") for texto in textos)
    assert not ventana_con_dos_eeg.carteles


def test_la_curva_de_la_ica_va_en_segundos_del_registro(ventana_con_dos_eeg: MainWindow):
    """**Iba en segundos de la ventana**, desde cero en cualquier época: no
    había cómo ubicar un pico en la señal. Ahora empieza donde empieza la
    época."""
    ventana_con_dos_eeg._go_to_window(1)
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()

    segundos, _ = ventana_con_dos_eeg.ica_panel.time_course_data()
    assert segundos[0] == pytest.approx(WINDOW_SECONDS)


def test_los_atajos_se_muestran_en_una_tabla(ventana: MainWindow, monkeypatch):
    """**Era un cartel de texto plano** con las columnas desalineadas."""
    from psglab.ui.shortcuts_dialog import ShortcutsDialog

    abiertos: list[ShortcutsDialog] = []
    monkeypatch.setattr(ShortcutsDialog, "exec", lambda self: abiertos.append(self) or 0)

    ventana._show_shortcuts()

    (dialogo,) = abiertos
    assert ("Archivo", "Abrir un registro", "Ctrl+O") in dialogo.rows()


# -- El botón principal del cartel (hito 55) --------------------------------


def test_exportar_es_el_boton_principal_del_cartel(ventana: MainWindow, monkeypatch):
    """Lo que el cartel recomienda va relleno del acento; descartar y cancelar
    no."""
    vistos: dict[str, bool] = {}

    def espiar(cartel):
        vistos.update(
            {
                boton.text(): bool(boton.property(theme.PRIMARIO_PROPERTY))
                for boton in cartel.buttons()
            }
        )
        return 0

    monkeypatch.setattr(QMessageBox, "exec", espiar)
    ventana.work_guard.ask("cerrar el programa", ["scoring"])

    assert vistos == {"Exportar…": True, "Descartar": False, "Cancelar": False}


# -- Accesibilidad: el teclado llega a todo (hito 62) ------------------------


def test_inicio_y_fin_van_a_la_primera_y_la_ultima_ventana(ventana: MainWindow):
    ventana.go_to_last_window()
    assert ventana.session.current_window == VENTANAS - 1

    ventana.go_to_first_window()
    assert ventana.session.current_window == 0


def test_ctrl_g_pregunta_a_que_ventana_ir(ventana: MainWindow, monkeypatch):
    """**Cuenta desde uno**, como la barra de estado; adentro es base 0."""
    pedidos: list[tuple] = []

    def preguntar(_padre, _titulo, _rotulo, valor, minimo, maximo, *_resto):
        pedidos.append((valor, minimo, maximo))
        return 4, True

    monkeypatch.setattr(QInputDialog, "getInt", preguntar)
    ventana.ask_window()

    assert pedidos == [(1, 1, VENTANAS)]
    assert ventana.session.current_window == 3


def test_cancelar_ctrl_g_no_mueve_nada(ventana: MainWindow, monkeypatch):
    ventana.go_to_next_window()
    monkeypatch.setattr(QInputDialog, "getInt", lambda *_a, **_k: (5, False))

    ventana.ask_window()

    assert ventana.session.current_window == 1


def test_los_atajos_nuevos_estan_colgados_de_la_ventana(ventana: MainWindow):
    """Que el método exista no alcanza: tiene que haber un atajo que lo
    llame, o para el teclado sigue sin existir."""
    from PySide6.QtGui import QKeySequence, QShortcut

    teclas = {atajo.key().toString() for atajo in ventana.findChildren(QShortcut)}

    for tecla in ("Home", "End", "Ctrl+G", "E", "Shift+F10", "Menu"):
        assert QKeySequence(tecla).toString() in teclas, tecla


def test_e_anota_la_ventana_actual(ventana: MainWindow, monkeypatch):
    """**Anotar era lo único del pliego que exigía mouse.** Con E se anota la
    ventana entera, con la misma pregunta de clase que al arrastrar."""
    from psglab.core.windows import window_to_samples

    ventana.go_to_next_window()
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("Apnea", True))

    ventana.annotate_current_window()

    (anotacion,) = ventana.session.annotations.all()
    inicio, fin = window_to_samples(1, ventana.session.recording.sampling_rate)
    assert (anotacion.label, anotacion.onset_sample, anotacion.duration_samples) == (
        "Apnea", inicio, fin - inicio
    )
    assert ventana.tool_controller.actions["annotator"].isChecked()
    assert not ventana.carteles


def test_anotar_la_ultima_ventana_no_se_pasa_del_registro(
    ventana: MainWindow, monkeypatch, tmp_path
):
    """Un registro de 145 s tiene la quinta ventana incompleta: anotarla
    entera se pasaría 5 s del final."""
    ventana.open_recording(escribir_brainvision(tmp_path / "corto", segundos=145.0))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("Apnea", True))
    ventana.go_to_last_window()

    ventana.annotate_current_window()

    (anotacion,) = ventana.session.annotations.all()
    assert anotacion.onset_sample + anotacion.duration_samples <= ventana.session.recording.n_samples


def test_mayus_f10_corrige_la_anotacion_de_la_ventana(
    ventana: MainWindow, monkeypatch, elige_en_el_menu
):
    """El menú del clic derecho, sin mouse: cambiar la clase de la anotación
    de la ventana actual. **Si hay dos, la más corta**, como el clic."""
    respuestas = iter([("Apnea", True), ("Arousal", True)])
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: next(respuestas))
    ventana.annotate_current_window()
    fs = ventana.session.recording.sampling_rate
    herramienta = ventana.tool_controller.tools["annotator"]
    herramienta.create_annotation("Apnea", int(5 * fs), int(2 * fs))
    elige_en_el_menu.elegir(annotation_mod._CAMBIAR_CLASE)

    ventana.annotation_menu_for_current_window()

    assert elige_en_el_menu.menus == [[annotation_mod._CAMBIAR_CLASE, annotation_mod._BORRAR]]
    clases = sorted((a.duration_samples, a.label) for a in ventana.session.annotations.all())
    assert clases[0][1] == "Arousal"
    assert clases[1][1] == "Apnea"


def test_mayus_f10_sin_anotacion_lo_dice(ventana: MainWindow, elige_en_el_menu):
    ventana.annotation_menu_for_current_window()

    assert elige_en_el_menu.menus == []
    assert "No hay ninguna anotación" in ventana.statusBar().currentMessage()


def test_la_senal_con_foco_se_ve(ventana: MainWindow):
    """El marco de acento aparece con el foco y se va sin él. Se mira el
    borde de lo que se dibuja, no la hoja de estilo."""
    ventana.show()
    ventana.activateWindow()
    vista = ventana.signal_view
    acento = theme.current().accent

    def borde() -> str:
        imagen = vista.grab().toImage()
        return imagen.pixelColor(0, imagen.height() // 2).name()

    ventana.channel_selector.setFocus()
    QApplication.processEvents()
    assert borde() != acento

    vista.setFocus()
    QApplication.processEvents()
    assert vista.hasFocus()
    assert borde() == acento


# -- Los textos de la interfaz (hito 65) -------------------------------------

#: El `_show_error` de verdad: las fixtures lo reemplazan por una lista.
_MOSTRAR_EL_ERROR = MainWindow._show_error


class EspiaDeCarteles:
    """Reemplaza `QMessageBox.exec`: anota el cartel y aprieta un botón.

    Apretar un botón fuera de `exec()` deja igual `clickedButton()`, que es lo
    único que mira el programa.

    **No anota el título, a propósito** (hito 66): macOS no lo muestra, así que
    un test que lo mirara verificaría algo que en una Mac no se ve. El del
    hito 65 lo hizo, y falló sólo en el CI de macOS.
    """

    def __init__(self, apretar: str | None = None) -> None:
        self.apretar = apretar
        self.vistos: list[dict[str, object]] = []

    def __call__(self, cartel: QMessageBox) -> int:
        botones = {b.text(): b for b in cartel.buttons()}
        self.vistos.append(
            {
                "texto": cartel.text(),
                "informativo": cartel.informativeText(),
                "detalle": cartel.detailedText(),
                "botones": sorted(botones),
                "por_omision": cartel.defaultButton().text() if cartel.defaultButton() else None,
                "destructivos": sorted(
                    t for t, b in botones.items() if b.property(theme.DESTRUCTIVO_PROPERTY)
                ),
            }
        )
        if self.apretar is not None:
            botones[self.apretar].click()
        return 0


def test_confirmar_nombra_la_accion_en_el_boton(ventana: MainWindow, monkeypatch):
    """«Borrar / Cancelar» y no «Sí / No», que obligaba a releer la pregunta
    para saber cuál era cuál. **Cancelar va por omisión** cuando se pierde
    algo: un Enter apurado no puede borrar."""
    espia = EspiaDeCarteles(apretar="Borrar")
    monkeypatch.setattr(QMessageBox, "exec", lambda cartel: espia(cartel))

    confirmado = ventana._confirmar(
        "Borrar la anotación", "¿Borrar?", "Borrar",
        informativo="No se puede deshacer.", destructivo=True,
    )

    assert confirmado is True
    (visto,) = espia.vistos
    assert visto["botones"] == ["Borrar", "Cancelar"]
    assert visto["por_omision"] == "Cancelar"
    assert visto["destructivos"] == ["Borrar"]
    assert visto["informativo"] == "No se puede deshacer."


@pytest.mark.parametrize("apretar", ["Cancelar", None], ids=["cancelar", "cerrar"])
def test_confirmar_sin_apretar_la_accion_no_confirma(
    ventana: MainWindow, monkeypatch, apretar
):
    espia = EspiaDeCarteles(apretar=apretar)
    monkeypatch.setattr(QMessageBox, "exec", lambda cartel: espia(cartel))

    assert ventana._confirmar("Reemplazar el archivo", "¿Reemplazarlo?", "Reemplazar") is False


def test_sin_perder_nada_la_accion_va_por_omision(ventana: MainWindow, monkeypatch):
    espia = EspiaDeCarteles()
    monkeypatch.setattr(QMessageBox, "exec", lambda cartel: espia(cartel))

    ventana._confirmar("Cambiar de nomenclatura", "¿Convertir?", "Convertir")

    assert espia.vistos[0]["por_omision"] == "Convertir"
    assert espia.vistos[0]["destructivos"] == []


def test_borrar_una_anotacion_avisa_que_no_se_deshace(
    ventana: MainWindow, confirmacion, elige_en_el_menu
):
    elige_en_el_menu.elegir("Borrar")
    anotar_en(ventana, 10.0, 12.0, "Spindle")
    ventana.tool_controller.toggle("annotator", True)

    clic_derecho(ventana, 11.0)

    (pregunta,) = confirmacion["preguntas"]
    assert pregunta["accion"] == "Borrar"
    assert pregunta["destructivo"] is True
    assert "deshacer" in pregunta["informativo"]


@pytest.mark.parametrize("convierte", [True, False])
def test_cambiar_de_nomenclatura_pregunta_con_convertir(
    ventana: MainWindow, confirmacion, convierte: bool
):
    from psglab.core.nomenclature import Nomenclature

    antes = ventana.session.scoring.nomenclature
    otra = Nomenclature.RK if antes is Nomenclature.AASM else Nomenclature.AASM
    ventana.score_current_window(stages_of(antes)[0])
    confirmacion["respuesta"] = convierte

    ventana.scoring_panel.nomenclature_changed.emit(otra)

    assert confirmacion["preguntas"][0]["accion"] == "Convertir"
    assert ventana.session.scoring.nomenclature is (otra if convierte else antes)


def test_sin_nada_scoreado_cambiar_de_nomenclatura_no_pregunta(
    ventana: MainWindow, confirmacion
):
    from psglab.core.nomenclature import Nomenclature

    ventana.scoring_panel.nomenclature_changed.emit(Nomenclature.RK)

    assert confirmacion["preguntas"] == []
    assert ventana.session.scoring.nomenclature is Nomenclature.RK


def test_el_cartel_de_error_empieza_por_lo_que_no_se_pudo_hacer(
    ventana: MainWindow, monkeypatch
):
    """Era «No se pudo completar la operación» para todos: después de un
    cálculo largo, nadie recuerda qué había pedido.

    **En el texto y no en el título** (hito 66): el hito 65 lo puso en el
    título, y macOS no lo muestra. Debajo va el porqué, y la causa técnica
    sigue en el desplegable."""
    monkeypatch.setattr(MainWindow, "_show_error", _MOSTRAR_EL_ERROR)
    espia = EspiaDeCarteles()
    monkeypatch.setattr(QMessageBox, "exec", lambda cartel: espia(cartel))

    ventana._show_error(
        PsgLabError("No se encontró el archivo.", details="No existe C:/noche.edf."),
        "abrir «noche.edf»",
    )
    ventana._show_error(PsgLabError("algo"))

    assert [(v["texto"], v["informativo"]) for v in espia.vistos] == [
        ("No se pudo abrir «noche.edf».", "No se encontró el archivo."),
        ("No se pudo completar la operación.", "algo"),
    ]
    assert espia.vistos[0]["detalle"] == "No existe C:/noche.edf."


def test_el_cartel_de_avisos_dice_en_el_texto_que_el_registro_se_abrio(
    ventana: MainWindow, monkeypatch
):
    """Lo decía sólo el título, que macOS no muestra (hito 66). El aviso de
    las muestras sin valor no dice por sí solo que el registro se abrió."""
    espia = EspiaDeCarteles()
    monkeypatch.setattr(QMessageBox, "exec", lambda cartel: espia(cartel))

    ventana._mostrar_avisos_de_lectura(["Primer aviso.", "Segundo aviso."])

    (visto,) = espia.vistos
    nombre = ventana.session.recording.file_path.name
    assert visto["texto"] == f"«{nombre}» se abrió, con avisos."
    assert visto["informativo"] == "Primer aviso.\n\nSegundo aviso."


def test_abrir_un_archivo_que_no_esta_lo_nombra_en_el_cartel(
    ventana: MainWindow, tmp_path
):
    ventana.open_recording(tmp_path / "noche.edf")

    assert ventana.acciones == ["abrir «noche.edf»"]


def test_un_analisis_que_falla_dice_cual_en_el_cartel(ventana: MainWindow):
    def falla(_registro):
        raise PsgLabError("no")

    ventana._aplicar_analisis("Se derivó", falla, accion="derivar «C3-EOG-izq»")

    assert ventana.acciones == ["derivar «C3-EOG-izq»"]


# -- Las teclas son del control que tiene el foco (hito 67) ------------------


def test_el_0_y_el_5_scorean_w_y_r(a_la_vista: MainWindow):
    """Hito 79: son los códigos de `Scoring.txt`, y dejan el scoring entero en
    el teclado numérico. La letra sigue andando."""
    from psglab.core.nomenclature import SleepStage

    ventana = a_la_vista
    ventana.signal_view.setFocus()
    QApplication.processEvents()

    teclear(Qt.Key.Key_0, Qt.Key.Key_5)

    assert ventana.session.scoring.get(0).stage is SleepStage.WAKE
    assert ventana.session.scoring.get(1).stage is SleepStage.R


def test_la_n_lleva_a_la_proxima_sin_scorear(a_la_vista: MainWindow):
    """Hito 79: es como se retoma un scoring a medias. Mayús+N vuelve."""
    from psglab.core.nomenclature import SleepStage

    ventana = a_la_vista
    for indice in (1, 2):
        ventana.session.scoring.set_stage(indice, SleepStage.N2)
    ventana.signal_view.setFocus()
    QApplication.processEvents()

    teclear(Qt.Key.Key_N)
    assert ventana.session.current_window == 3

    from PySide6.QtTest import QTest

    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_N, Qt.KeyboardModifier.ShiftModifier)
    QApplication.processEvents()
    assert ventana.session.current_window == 0


def test_sin_ninguna_sin_scorear_la_n_lo_dice(ventana: MainWindow):
    """Una tecla muda se lee como que no anda."""
    from psglab.core.nomenclature import SleepStage

    for indice in range(ventana.session.n_windows):
        ventana.session.scoring.set_stage(indice, SleepStage.N2)

    ventana.go_to_next_unscored_window()

    assert ventana.session.current_window == 0
    assert "No quedan ventanas sin scorear" in ventana.statusBar().currentMessage()


def test_tipear_en_la_tabla_de_impedancias_escribe_el_valor(a_la_vista: MainWindow):
    """**Scoreaba la ventana**: «2» la marcaba N2 y el paso a la siguiente del
    hito 64 hacía que «25» scoreara dos, mientras el usuario creía estar
    escribiendo la impedancia que la pista del panel le pide."""
    ventana = a_la_vista
    ventana.show_impedance_dialog()
    tabla = ventana.impedance_panel.tabla
    tabla.setFocus()
    tabla.setCurrentItem(tabla.topLevelItem(0), 1)
    QApplication.processEvents()

    teclear(Qt.Key.Key_2, Qt.Key.Key_5, Qt.Key.Key_Return)

    canal = tabla.topLevelItem(0).text(0)
    assert ventana.impedance_panel.values()[canal] == pytest.approx(25.0)
    assert ventana.session.scoring.scored_windows() == 0
    assert ventana.session.current_window == 0


def test_tipear_en_la_tabla_de_filtros_escribe_el_corte(a_la_vista: MainWindow):
    ventana = a_la_vista
    ventana.show_filter_dialog()
    tabla = ventana.filter_panel.tabla
    tabla.setFocus()
    tabla.setCurrentItem(tabla.topLevelItem(0), 1)
    QApplication.processEvents()

    teclear(Qt.Key.Key_2, Qt.Key.Key_Return)

    assert tabla.topLevelItem(0).text(1) == "2"
    assert ventana.session.scoring.scored_windows() == 0


def test_las_flechas_recorren_la_tabla_y_no_cambian_la_amplitud(a_la_vista: MainWindow):
    """↓ agrandaba la escala en vez de bajar de fila: la tabla no se podía
    recorrer con el teclado."""
    ventana = a_la_vista
    ventana.show_impedance_dialog()
    tabla = ventana.impedance_panel.tabla
    tabla.setFocus()
    tabla.setCurrentItem(tabla.topLevelItem(0), 1)
    QApplication.processEvents()
    escalas = {c: ventana.session.scale_uv(c) for c in ventana.session.visible_channels}

    teclear(Qt.Key.Key_Down, Qt.Key.Key_Down)

    assert tabla.indexOfTopLevelItem(tabla.currentItem()) == 2
    assert {c: ventana.session.scale_uv(c) for c in escalas} == escalas


def test_en_la_lista_de_canales_las_flechas_son_de_la_lista(a_la_vista: MainWindow):
    """Pero las teclas que escriben siguen scoreando: la lista no carga datos,
    y quien tildó un canal sigue trabajando con el teclado."""
    from PySide6.QtWidgets import QListWidget

    ventana = a_la_vista
    lista = ventana.channel_selector.findChildren(QListWidget)[0]
    lista.setFocus()
    lista.setCurrentRow(0)
    QApplication.processEvents()
    escalas = {c: ventana.session.scale_uv(c) for c in ventana.session.visible_channels}

    teclear(Qt.Key.Key_Down)

    assert lista.currentRow() == 1
    assert {c: ventana.session.scale_uv(c) for c in escalas} == escalas
    teclear(Qt.Key.Key_2)
    assert ventana.session.scoring.get(0).stage is SleepStage.N2


def test_las_flechas_eligen_la_velocidad_en_su_selector(a_la_vista: MainWindow):
    ventana = a_la_vista
    selector = ventana.navigation.speed_selector
    selector.setFocus()
    QApplication.processEvents()
    antes = selector.currentIndex()

    teclear(Qt.Key.Key_Down)

    assert selector.currentIndex() == antes + 1


def test_con_el_foco_en_la_senal_los_atajos_siguen_iguales(a_la_vista: MainWindow):
    """**Lo que no tenía que cambiar**: la señal no es ninguno de los
    controles que se quedan con sus teclas."""
    ventana = a_la_vista
    sesion = ventana.session
    ventana.signal_view.setFocus()
    QApplication.processEvents()
    canal = sesion.visible_channels[0]
    escala = sesion.scale_uv(canal)

    teclear(Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_2)

    assert sesion.scale_uv(canal) > escala
    assert sesion.scoring.get(1).stage is SleepStage.N2
    assert sesion.current_window == 2


def test_el_filtro_de_las_teclas_es_uno_solo_en_toda_la_aplicacion(
    ventana: MainWindow,
):
    """Los atajos se reinstalan al armar cada ventana, al abrir un registro y
    al cambiar de nomenclatura. **Uno por ventana dejó la suite sin
    terminar**: las de los tests no se destruyen, y cada evento pasaba por
    todos. A esta altura de la suite ya se armaron cientos de ventanas."""
    from PySide6.QtCore import QObject

    from psglab.core.nomenclature import Nomenclature

    create_main_window()
    ventana.scoring_panel.nomenclature_changed.emit(Nomenclature.RK)

    aplicacion = QApplication.instance()
    assert len(aplicacion.findChildren(QObject, "psglab-teclas-del-control")) == 1


# -- Los errores inesperados (hito 68) ----------------------------------------


def test_un_error_inesperado_en_otro_hilo_no_deja_la_ventana_esperando(
    ventana: MainWindow,
):
    """La barra de espera seguía girando, la barra de estado decía que se
    estaba calculando y los menús largos quedaban apagados hasta cerrar el
    programa. El error se sigue elevando: es un bug, y no se disfraza."""

    def rompe() -> None:
        raise ValueError("algo que nadie previó")

    ventana.analysis_controller.run_in_background(
        "Probando", rompe, lambda _r: None, action="probar"
    )
    with pytest.raises(ValueError):
        ventana.wait_for_background()

    assert not ventana.analysis_controller.wait_bar.isVisible()
    assert ventana.statusBar().currentMessage() != "Probando…"
    assert ventana.menu_filtrar.menuAction().isEnabled()
    assert ventana.accion_conectividad_de_la_noche.isEnabled()


@pytest.fixture
def aviso_de_errores(qt_app, monkeypatch):
    """Una ventana con el aviso de errores inesperados, como la arma `main.py`.

    `sys.excepthook` se reemplaza antes por uno mudo: el aviso lo llama igual
    —para que la consola siga mostrando la traza— y así la suite no la
    imprime. `monkeypatch` deja el original al terminar, y con él se va el
    aviso. Los carteles se anotan en vez de mostrarse: son modales.
    """
    import sys

    monkeypatch.setattr(sys, "excepthook", lambda *_a: None)
    carteles: list[dict[str, str]] = []

    def anotar(cartel: QMessageBox) -> int:
        carteles.append(
            {
                "texto": cartel.text(),
                "informativo": cartel.informativeText(),
                "detalle": cartel.detailedText(),
            }
        )
        return 0

    monkeypatch.setattr(QMessageBox, "exec", anotar)
    create_main_window(report_unexpected_errors=True)
    return carteles


def elevar(error: BaseException) -> None:
    """Le pasa a `sys.excepthook` un error elevado de verdad, con su traza."""
    import sys

    try:
        raise error
    except BaseException as capturado:  # noqa: BLE001 - es lo que se prueba
        sys.excepthook(type(capturado), capturado, capturado.__traceback__)


def test_un_error_inesperado_se_muestra_como_defecto_del_programa(aviso_de_errores):
    """**Abierto sin consola no lo veía nadie**, y el programa seguía con lo
    que se estaba haciendo a medio hacer. El cartel no lo disfraza de mensaje
    para el investigador: dice que es un defecto, y trae la traza."""
    elevar(KeyError("canal"))

    (cartel,) = aviso_de_errores
    assert cartel["texto"] == "Ocurrió un error del programa."
    assert "No es un problema de tus datos" in cartel["informativo"]
    assert "KeyError: 'canal'" in cartel["detalle"]
    assert "Traceback" in cartel["detalle"]


def test_el_mismo_error_se_muestra_una_sola_vez(aviso_de_errores):
    """Uno que salta al pintar se repetiría en cada cuadro."""
    for _ in range(3):
        elevar(KeyError("canal"))
    elevar(ValueError("otro"))

    assert len(aviso_de_errores) == 2


def test_un_error_en_un_slot_llega_al_aviso(aviso_de_errores):
    """El camino de verdad: PySide6 le pasa a `sys.excepthook` lo que sale de
    un slot, y el bucle de eventos sigue."""
    from PySide6.QtCore import QTimer

    QTimer.singleShot(0, lambda: {}["falta"])
    QApplication.processEvents()

    assert len(aviso_de_errores) == 1
    assert "KeyError" in aviso_de_errores[0]["detalle"]


def test_cortar_con_ctrl_c_no_es_un_error_del_programa(aviso_de_errores):
    elevar(KeyboardInterrupt())

    assert aviso_de_errores == []


def test_sin_pedirlo_la_ventana_no_toca_el_manejador(qt_app):
    """La suite, la captura de pantalla y los bancos arman la ventana sin
    pedirlo: un cartel modal los colgaría."""
    import sys

    antes = sys.excepthook
    create_main_window()

    assert sys.excepthook is antes


def test_la_consola_sigue_mostrando_la_traza(qt_app, monkeypatch):
    """El cartel se suma a la consola, no la reemplaza: quien corre el
    programa desde una terminal sigue viendo la traza donde la veía."""
    import sys

    consola: list[type[BaseException]] = []
    monkeypatch.setattr(sys, "excepthook", lambda tipo, *_a: consola.append(tipo))
    monkeypatch.setattr(QMessageBox, "exec", lambda _cartel: 0)
    create_main_window(report_unexpected_errors=True)

    elevar(KeyError("canal"))

    assert consola == [KeyError]


# -- Lo que ningún test disparaba (hito 81) ------------------------------------


def test_el_atajo_de_una_clase_oculta_y_vuelve_a_mostrar_sus_canales(ventana: MainWindow):
    """El pie del selector de canales: un botón por clase. El registro de
    prueba trae un canal de cada clase, así que ocultar el EEG deja los otros
    dos. Ningún test hacía clic en estos botones."""
    from psglab.core.recording import ChannelKind

    todos = list(ventana.session.visible_channels)
    boton = ventana.channel_selector._atajos[ChannelKind.EEG]

    boton.click()
    assert "C3" not in ventana.session.visible_channels
    assert set(ventana.session.visible_channels) == set(todos) - {"C3"}

    boton.click()
    assert ventana.session.visible_channels == todos
    assert not ventana.carteles
