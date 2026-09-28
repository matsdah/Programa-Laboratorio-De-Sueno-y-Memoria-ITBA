"""El scoring por la ventana: el hipnograma, las fases y lo que se deshace.

Es parte de la comprobación de entrega, separada de `test_entrega.py` en el
hito 79, y con su misma regla: todo pasa por `MainWindow`, y los clics se
mandan como eventos de Qt en vez de llamar a la pieza.

Cubre el eje y el clic del hipnograma, el flujo de scorear de corrido, las
fases que sugiere el clasificador, deshacer y rehacer, y que anotar un arousal
marque su ventana. Lo que cambia es lo que termina en `Scoring.txt`, así que un
error acá no se ve en pantalla: se ve en el archivo, días después.
"""

from pathlib import Path

import numpy as np
import pyqtgraph as pg
import pytest

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QInputDialog

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.core.nomenclature import Nomenclature, SleepStage, stages_of  # noqa: E402
from psglab.core.scoring import StageSuggestion  # noqa: E402
from psglab.exporters.scoring_txt import export_scoring  # noqa: E402
# Los módulos donde se buscan los nombres que la suite reemplaza (hito 76):
# reemplazarlos en `main_window` no tendría efecto, porque ahí ya no se usan.
import psglab.ui.window_scoring as scoring_mod  # noqa: E402
from psglab.ui import theme  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from psglab.ui.work_guard import WorkGuard  # noqa: E402

from conftest import escribir_brainvision  # noqa: E402
from entrega_comun import (  # noqa: E402, F401
    VENTANAS,
    a_la_vista,
    anotar_en,
    arrastrar_un_tramo,
    bandas_dibujadas,
    clic_derecho,
    confirmacion,
    evento_de_mouse,
    reproduccion,
    teclear,
    ventana,
)


# -- El eje del histograma (V2_F del histograma) -----------------------------
#
# Faltaba entero hasta el hito 9: `set_time_axis()` prendía un booleano que no
# leía nadie, y el eje se dibujaba con los índices crudos de `range()`, o sea
# base 0 y sin marcas.


def marcas_horizontales(ventana: MainWindow) -> list[tuple[float, str]]:
    return ventana.histogram_view.getPlotItem().getAxis("bottom")._tickLevels[0]


def barras_de_fase(ventana: MainWindow) -> list[pg.BarGraphItem]:
    """Los tramos de color del hipnograma, si el esquema los tiene."""
    return [
        item
        for item in ventana.histogram_view.getPlotItem().items
        if isinstance(item, pg.BarGraphItem)
    ]


@pytest.fixture
def con_escala_de_fases(ventana: MainWindow):
    """Fija el esquema, que es estado global del proceso.

    `theme.current()` lo comparten todos los widgets, así que un test anterior
    que haya elegido otro esquema decide qué se pinta acá. Se deja como estaba.
    """
    anterior = theme.current()
    ventana.set_color_scheme(theme.SERENO, remember=False)
    yield ventana
    ventana.set_color_scheme(anterior, remember=False)


def test_el_hipnograma_pinta_cada_fase_de_su_color(con_escala_de_fases: MainWindow):
    """**El programa no tenía colores de fase hasta el hito 34**: la curva se
    dibujaba en una sola tinta y reconocer una fase obligaba a leer el eje."""
    ventana = con_escala_de_fases
    ventana._go_to_window(1)
    ventana.score_current_window(SleepStage.N2)

    (barras,) = barras_de_fase(ventana)
    esperado = theme.SERENO.color_for_stage(SleepStage.N2.value)
    assert esperado is not None
    assert esperado in barras.opts["brushes"]


def test_la_franja_de_posicion_muestra_lo_scoreado(con_escala_de_fases: MainWindow):
    """**Decía dónde estoy y no cuánto llevo hecho**, que es la otra mitad de
    la pregunta. Sale de la misma fuente que el hipnograma, así que una fase se
    ve igual en los dos lugares."""
    ventana = con_escala_de_fases
    ventana._go_to_window(1)
    ventana.score_current_window(SleepStage.N2)

    colores = ventana.navigation.strip._colores
    esperado = theme.SERENO.color_for_stage(SleepStage.N2.value)
    assert colores[1] == esperado
    assert colores[0] is None, "lo no scoreado no se pinta"


def test_un_esquema_sin_escala_de_fases_no_pinta_nada(con_escala_de_fases: MainWindow):
    """El campo admite el vacío, y entonces el hipnograma y la franja se
    dibujan como antes del hito 34: con una sola tinta."""
    import dataclasses

    ventana = con_escala_de_fases
    ventana._go_to_window(1)
    ventana.score_current_window(SleepStage.N2)

    ventana.set_color_scheme(
        dataclasses.replace(theme.SERENO, stage_colors=()), remember=False
    )

    assert barras_de_fase(ventana) == []
    assert ventana.navigation.strip._colores == ()


def test_lo_no_scoreado_queda_en_blanco(ventana: MainWindow):
    """**V1_P: "el histograma tiene el tamaño total de la noche desde el
    arranque, y lo no anotado queda en blanco".**

    Se dibuja como `NaN`, que es lo que `connect="finite"` omite. Se mapeaba a
    cero, y entonces ese parámetro no podía hacer nada —ningún valor era no
    finito— y lo no scoreado salía como una línea en la base: un tramo sin
    mirar se leía como una fase más.
    """
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])

    curva = ventana.histogram_view.getPlotItem().listDataItems()[0]
    _, alturas = curva.getData()

    assert not np.isnan(alturas[0]), "la ventana scoreada tiene que tener altura"
    sin_scorear = alturas[1:]
    assert np.all(np.isnan(sin_scorear)), (
        "las ventanas sin scorear tienen que quedar en blanco, no en la base"
    )


def test_scorear_una_ventana_le_da_altura(ventana: MainWindow):
    """La otra mitad: el blanco tiene que desaparecer al scorear."""
    fases = stages_of(ventana.session.scoring.nomenclature)
    ventana._go_to_window(2)
    ventana.score_current_window(fases[1])

    _, alturas = ventana.histogram_view.getPlotItem().listDataItems()[0].getData()
    assert not np.isnan(alturas[2])


def test_una_flecha_no_rearma_el_hipnograma(ventana: MainWindow):
    """**Lo rearmaba dos veces por flecha**, y no muestra la época actual: con
    una noche de ocho horas a medio scorear era la mitad de lo que costaba una
    flecha. La curva tiene que ser el mismo objeto antes y después."""
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])
    antes = ventana.histogram_view.getPlotItem().listDataItems()[0]

    ventana.go_to_next_window()
    ventana.go_to_previous_window()

    assert ventana.histogram_view.getPlotItem().listDataItems()[0] is antes


def test_scorear_despues_de_una_flecha_rearma_el_hipnograma(ventana: MainWindow):
    """El otro lado: lo que cambia el dibujo lo tiene que seguir cambiando."""
    fases = stages_of(ventana.session.scoring.nomenclature)
    ventana._go_to_window(0)
    ventana.go_to_next_window()

    ventana.score_current_window(fases[1])

    _, alturas = ventana.histogram_view.getPlotItem().listDataItems()[0].getData()
    assert not np.isnan(alturas[1])


def test_cambiar_el_eje_a_hora_rearma_el_hipnograma(ventana: MainWindow):
    """El eje de abajo es parte del dibujo, aunque las fases no cambien."""
    if ventana.session.recording.start_time is None:
        pytest.skip("el registro de prueba no informa su hora de inicio")
    en_ventanas = marcas_horizontales(ventana)

    ventana.set_histogram_time_axis(True)

    assert marcas_horizontales(ventana) != en_ventanas
    assert not ventana.carteles


def test_cambiar_de_nomenclatura_sin_nada_scoreado_rearma_el_eje(ventana: MainWindow):
    """Sin nada scoreado, las fases son las mismas —todas sin scorear— pero el
    eje de la izquierda nombra las de la otra nomenclatura."""
    from psglab.core.nomenclature import stage_label

    otra = (
        Nomenclature.RK
        if ventana.session.scoring.nomenclature is Nomenclature.AASM
        else Nomenclature.AASM
    )

    ventana._change_nomenclature(otra)

    textos = [
        texto
        for _, texto in ventana.histogram_view.getPlotItem().getAxis("left")._tickLevels[0]
    ]
    assert textos == [stage_label(fase) for fase in stages_of(otra)]


def test_otro_registro_con_otra_hora_rearma_el_eje(ventana: MainWindow, tmp_path: Path):
    """Mismo largo y nada scoreado, así que las fases son las mismas; con el eje
    en hora, lo que cambia es la hora de cada marca."""
    ventana.set_histogram_time_axis(True)
    antes = marcas_horizontales(ventana)
    vhdr = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * VENTANAS)
    marcadores = vhdr.with_suffix(".vmrk")
    marcadores.write_text(
        marcadores.read_text(encoding="utf-8").replace("20260907130000", "20260907223000"),
        encoding="utf-8",
    )

    ventana.open_recording(vhdr)

    assert ventana.session.recording.start_time.hour == 22
    assert marcas_horizontales(ventana) != antes
    assert not ventana.carteles


def test_el_eje_arranca_numerando_las_ventanas_desde_uno(ventana: MainWindow):
    """Base 0 adentro, base 1 al mostrar. El eje mostraba base 0."""
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])

    marcas = marcas_horizontales(ventana)
    assert marcas, "el eje del histograma no tiene ninguna marca"
    assert marcas[0] == (0.0, "1")


def test_se_puede_pasar_a_la_hora_real_de_la_noche(ventana: MainWindow):
    """La otra mitad de V2_F. El BrainVision sintético informa su hora de
    inicio, así que la conversión tiene con qué."""
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])
    ventana.accion_eje_en_hora.setChecked(True)

    textos = [texto for _, texto in marcas_horizontales(ventana)]
    assert all(":" in texto for texto in textos), textos


def test_volver_al_numero_de_ventana(ventana: MainWindow):
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])
    ventana.accion_eje_en_hora.setChecked(True)
    ventana.accion_eje_en_hora.setChecked(False)

    assert marcas_horizontales(ventana)[0] == (0.0, "1")


def test_las_fases_se_nombran_como_en_el_resto_del_programa(ventana: MainWindow):
    """`str(fase)` daba "SleepStage.WAKE" en el eje. Es el mismo `stage_label()`
    que usan el panel de scoring y `Informacion.txt`."""
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])

    etiquetas = [
        texto
        for _, texto in ventana.histogram_view.getPlotItem().getAxis("left")._tickLevels[0]
    ]
    assert "W" in etiquetas
    assert not any(texto.startswith("SleepStage.") for texto in etiquetas)


def test_pedir_la_hora_real_sin_hora_de_inicio_avisa(
    qt_app, tmp_path, monkeypatch
):
    """Inventar una hora de comienzo sería peor que negarse: el investigador
    leería el eje como si fuera real. La herramienta se niega y acá se
    convierte en cartel."""
    import numpy as np

    from psglab.core.annotations import AnnotationSet
    from psglab.core.nomenclature import Nomenclature
    from psglab.core.recording import Channel, ChannelKind, Recording
    from psglab.core.scoring import Scoring
    from psglab.core.session import Session

    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    principal = create_main_window()
    sin_hora = Recording(
        file_path=Path("sin_hora.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, int(100.0 * WINDOW_SECONDS * 3))),
        sampling_rate=100.0,
    )
    principal._session = Session(sin_hora, Scoring(3, Nomenclature.AASM), AnnotationSet())
    principal.tool_controller.activate_panel_tools()

    principal.set_histogram_time_axis(True)

    assert carteles, "pedir la hora real sin hora de inicio no avisó nada"
    assert "hora" in carteles[0].lower()


# -- El hipnograma, por el camino del mouse (V4_F) ----------------------------


def test_el_clic_en_el_hipnograma_lleva_a_la_epoca_bajo_el_mouse(ventana: MainWindow):
    """El mismo error que tenía el anotador: el clic se ubicaba con
    `scenePosition()`, que en un evento de widget es la ventana y no la escena.
    El hipnograma está abajo y a la derecha, así que caía cientos de píxeles
    corrido. Nada lo verificaba con un evento de verdad."""
    ventana.resize(1400, 800)
    ventana.show()
    # Los tres paneles de abajo, como se trabaja: solo, el hipnograma ocupa el
    # ancho entero, arranca en el borde de la ventana y el error no se ve.
    for dock in (ventana.overview_dock, ventana.scoring_dock, ventana.histogram_dock):
        dock.show()
    QApplication.processEvents()
    vista = ventana.histogram_view
    viewport = vista.viewport()
    # Sin distancia entre el gráfico y el borde de la ventana, el test pasaría
    # con el error puesto.
    assert viewport.mapTo(ventana, viewport.rect().topLeft()).x() > 0

    caja = vista.getPlotItem().vb.sceneBoundingRect()
    x = caja.left() + caja.width() * 0.7
    evento = evento_de_mouse(ventana, QEvent.Type.MouseButtonPress, x, vista=vista)
    QApplication.instance().sendEvent(viewport, evento)

    assert ventana.session.current_window == int(0.7 * VENTANAS)


# -- V2_F por el camino del usuario y no por la pieza (hito 48) --------------


def test_un_clic_de_verdad_suma_un_pico(ventana: MainWindow):
    """**V2_F sólo se verificaba llamando a la herramienta.**

    Los tres tests que cubrían el contador de picos hacían
    `herramienta.on_mouse_press(...)`, que es exactamente el método que el
    hito 9 señaló como la causa de que seis hitos pasaran sin que nadie notara
    que la lupa no llegaba a la ventana —y que `psglab/ui/README.md` prohíbe
    con todas las letras—. Con la herramienta llamada a mano, estos tests
    pasan en verde aunque el `eventFilter` no le mande nada.

    Lo encontró la auditoría de los tests, no un fallo: el camino funciona.
    """
    ventana.tool_controller.toggle("magnifier", True)
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    x = caja.left() + caja.width() * 0.5
    aplicacion = QApplication.instance()
    for tipo in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        aplicacion.sendEvent(
            ventana.signal_view.viewport(), evento_de_mouse(ventana, tipo, x)
        )

    assert ventana.tool_controller.tools["magnifier"].click_count == 1
    assert "Picos contados: 1" in ventana.tool_readout.text()


def test_el_boton_derecho_descuenta_por_el_mismo_camino(ventana: MainWindow):
    """La otra mitad de V2_F: corregir un clic de más sin reiniciar la cuenta."""
    ventana.tool_controller.toggle("magnifier", True)
    lupa = ventana.tool_controller.tools["magnifier"]
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    x = caja.left() + caja.width() * 0.5
    aplicacion = QApplication.instance()
    aplicacion.sendEvent(
        ventana.signal_view.viewport(),
        evento_de_mouse(ventana, QEvent.Type.MouseButtonPress, x),
    )
    assert lupa.click_count == 1

    clic_derecho(ventana, 15.0)

    assert lupa.click_count == 0


# -- El flujo de scoring (hito 64) --------------------------------------------


def test_puntuar_pasa_a_la_siguiente(ventana: MainWindow):
    """Una tecla por ventana y no dos."""
    ventana.score_current_window(SleepStage.N2)

    assert ventana.session.scoring.get(0).stage is SleepStage.N2
    assert ventana.session.current_window == 1


def test_en_la_ultima_puntuar_no_se_pasa(ventana: MainWindow):
    ventana.go_to_last_window()

    ventana.score_current_window(SleepStage.N2)

    assert ventana.session.current_window == VENTANAS - 1
    assert not ventana.carteles


def test_con_el_paso_apagado_se_queda(ventana: MainWindow):
    ventana._preferencias = ventana._preferencias.with_changes(advance_after_scoring=False)

    ventana.score_current_window(SleepStage.N2)

    assert ventana.session.current_window == 0


def test_reproduciendo_puntuar_no_adelanta_la_reproduccion(reproduccion: MainWindow):
    """La época la lleva el cursor: saltar adelantaría la reproducción una
    ventana por cada tecla."""
    ventana = reproduccion
    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(10.0)
    cursor = ventana.signal_view.playhead()

    ventana.score_current_window(SleepStage.N2)

    assert ventana.signal_view.playhead() == pytest.approx(cursor)
    assert ventana.session.scoring.get(0).stage is SleepStage.N2


def test_la_pestana_toma_el_color_de_la_fase(ventana: MainWindow):
    """**Confirma lo puntuado sin leer la letra**: el color es el mismo de la
    franja y el hipnograma. Sin puntuar, el acento."""
    esquema = theme.current()
    assert ventana.signal_view.epoch_tab_fill() == esquema.accent

    ventana.score_current_window(SleepStage.N2)
    ventana._go_to_window(0)

    assert ventana.signal_view._pestana.toPlainText() == "Ventana 1 · N2"
    assert ventana.signal_view.epoch_tab_fill() == esquema.color_for_stage("N2")


def test_la_pestana_cambia_de_color_con_el_esquema(ventana: MainWindow):
    anterior = theme.current()
    ventana._preferencias = ventana._preferencias.with_changes(advance_after_scoring=False)
    ventana.score_current_window(SleepStage.N2)
    try:
        ventana.set_color_scheme(theme.NOCTURNO, remember=False)

        assert ventana.signal_view.epoch_tab_fill() == theme.NOCTURNO.color_for_stage("N2")
    finally:
        ventana.set_color_scheme(anterior, remember=False)


def test_abrir_un_registro_lo_deja_en_recientes(ventana: MainWindow):
    (ruta,) = ventana.current_preferences.recent_files
    textos = [a.text() for a in ventana.menu_recientes.actions()]

    assert ruta.endswith("sintetico.vhdr")
    assert textos == ["&1  sintetico.vhdr"]


def test_elegir_un_reciente_lo_abre(ventana: MainWindow, tmp_path):
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 2)

    ventana.open_recent_file(str(otro))
    ventana.wait_for_background()

    assert ventana.session.n_windows == 2
    assert ventana.current_preferences.recent_files[0] == str(otro.resolve())


# -- Las fases sugeridas (hito 75) -------------------------------------------
#
# El clasificador de verdad corre en `test_auto_scoring.py`; acá se reemplaza
# por uno que devuelve algo conocido, porque lo que se verifica es el camino
# desde el menú y no qué fase sale.


@pytest.fixture
def clasificador(monkeypatch):
    """Reemplaza al clasificador: N2 segura en las ventanas pares, N3 dudosa en
    las impares. Anota con qué canales lo llamaron."""
    llamadas: list[tuple] = []

    def sugerir(registro, eeg, eog=None, emg=None):
        llamadas.append((eeg, eog, emg))
        return [
            StageSuggestion(SleepStage.N2, 0.9) if i % 2 == 0 else StageSuggestion(SleepStage.N3, 0.5)
            for i in range(VENTANAS)
        ]

    monkeypatch.setattr(scoring_mod, "suggest_stages", sugerir)
    return llamadas


def sugerir(ventana: MainWindow) -> None:
    ventana.request_stage_suggestions()
    ventana.wait_for_background()
    QApplication.processEvents()


def test_sugerir_no_scorea_nada(ventana: MainWindow, clasificador, confirmacion):
    """**Sugiere, no scorea**: no hay ninguna fase elegida, ni trabajo sin
    exportar, y el pie dice las dos cosas."""
    sugerir(ventana)

    scoring = ventana.session.scoring
    assert scoring.scored_windows() == 0
    assert scoring.pending_suggestions() == VENTANAS
    assert not ventana.session.has_unexported_scoring()
    assert ventana.scoring_panel.status() == "Ventana 1 · sin scorear · sugerida N2, 90 %"
    assert "Se sugirió la fase de 5 ventanas; 3 con" in ventana.statusBar().currentMessage()
    assert not ventana.carteles


def test_pregunta_antes_y_dice_con_que_canales(ventana: MainWindow, clasificador, confirmacion):
    confirmacion["respuesta"] = False
    ventana.session.scoring.set_stage(0, SleepStage.WAKE)

    ventana.request_stage_suggestions()
    # **Esperar antes de mirar**: si se calculara sin preguntar, el cálculo
    # corre en otro hilo y todavía no llamó al clasificador.
    ventana.wait_for_background()

    pregunta = confirmacion["preguntas"][0]
    # Sólo cuenta las que faltan: lo scoreado no se sugiere.
    assert "4 ventanas sin scorear" in pregunta["pregunta"]
    assert "«C3»" in pregunta["informativo"]
    assert "Scoring › Fases sugeridas › Confirmar las seguras" in pregunta["informativo"]
    assert clasificador == []


def test_lo_scoreado_a_mano_no_se_pisa(ventana: MainWindow, clasificador, confirmacion):
    ventana.session.scoring.set_stage(0, SleepStage.WAKE)
    sugerir(ventana)
    ventana.accept_all_suggestions()

    assert ventana.session.scoring.get(0).stage is SleepStage.WAKE
    assert ventana.session.scoring.get(1).stage is SleepStage.N3


def test_confirmar_las_seguras_las_vuelve_scoring(ventana: MainWindow, clasificador, confirmacion):
    """Desde ahí son scoring como cualquier otro: trabajo sin exportar."""
    sugerir(ventana)
    ventana.accept_safe_suggestions()

    scoring = ventana.session.scoring
    assert [scoring.get(i).stage for i in range(VENTANAS)] == [
        SleepStage.N2, SleepStage.UNSCORED, SleepStage.N2, SleepStage.UNSCORED, SleepStage.N2
    ]
    assert "al menos 80 %" in confirmacion["preguntas"][-1]["pregunta"]
    assert ventana.session.has_unexported_scoring()
    assert "Se confirmaron 3 fases" in ventana.statusBar().currentMessage()


def test_sin_confirmar_no_se_confirma_nada(ventana: MainWindow, clasificador, confirmacion):
    sugerir(ventana)
    confirmacion["respuesta"] = False
    ventana.accept_all_suggestions()

    assert ventana.session.scoring.scored_windows() == 0


def test_las_sugeridas_no_se_exportan(ventana: MainWindow, clasificador, confirmacion, tmp_path):
    """El archivo sale igual que el de un scoring sin tocar."""
    sin_tocar = tmp_path / "sin_tocar.txt"
    export_scoring(ventana.session.scoring, sin_tocar)
    sugerir(ventana)
    con_sugeridas = tmp_path / "con_sugeridas.txt"
    export_scoring(ventana.session.scoring, con_sugeridas)

    assert con_sugeridas.read_text(encoding="utf-8") == sin_tocar.read_text(encoding="utf-8")


def test_el_hipnograma_y_la_franja_las_muestran_aparte(
    ventana: MainWindow, clasificador, confirmacion
):
    """Una curva punteada en el hipnograma y el color de la fase, apagado, en
    la franja: se ven, pero no como lo scoreado."""
    sugerir(ventana)

    curvas = ventana.histogram_view.getPlotItem().listDataItems()
    assert any(
        curva.opts["pen"].style() == Qt.PenStyle.DashLine
        for curva in curvas
        if hasattr(curva.opts.get("pen"), "style")
    )
    colores = ventana.navigation.strip._colores
    assert all(color is not None and len(color) == 9 for color in colores)


def test_descartar_las_saca(ventana: MainWindow, clasificador, confirmacion):
    sugerir(ventana)
    ventana.discard_suggestions()

    assert ventana.session.scoring.pending_suggestions() == 0
    assert ventana.scoring_panel.status() == "Ventana 1 · sin scorear"
    assert ventana.navigation.strip._colores == (None,) * VENTANAS


def test_scorear_la_ventana_saca_su_sugerida_del_pie(
    ventana: MainWindow, clasificador, confirmacion
):
    ventana._preferencias = ventana._preferencias.with_changes(advance_after_scoring=False)
    sugerir(ventana)
    ventana.score_current_window(SleepStage.N1)

    assert ventana.scoring_panel.status() == "Ventana 1 · N1"


def test_en_rk_se_sugiere_en_rk(ventana: MainWindow, clasificador, confirmacion):
    ventana.session.scoring.change_nomenclature(Nomenclature.RK)
    sugerir(ventana)
    ventana.accept_all_suggestions()

    assert ventana.session.scoring.get(1).stage is SleepStage.S3


def test_un_registro_corto_lo_dice_en_un_cartel(ventana: MainWindow, confirmacion):
    """**Con el clasificador de verdad**: el registro de la ventana de prueba
    dura dos minutos y medio, y el rechazo tiene que llegar como cartel desde
    el otro hilo, no como traza."""
    sugerir(ventana)

    assert ventana.acciones == ["sugerir las fases"]
    assert "5 minutos" in ventana.carteles[0]
    assert ventana.session.scoring.pending_suggestions() == 0


# -- Deshacer y rehacer (hito 79) ---------------------------------------------------


def test_ctrl_z_deshace_la_fase_y_vuelve_a_su_ventana(a_la_vista: MainWindow):
    """Con el paso solo a la siguiente, una tecla de más scorea la ventana que
    viene: Ctrl+Z la deshace y vuelve a mostrarla. Ctrl+Y la rehace."""
    from PySide6.QtTest import QTest

    ventana = a_la_vista
    ventana.signal_view.setFocus()
    QApplication.processEvents()
    teclear(Qt.Key.Key_2, Qt.Key.Key_2)
    assert ventana.session.current_window == 2

    control = Qt.KeyboardModifier.ControlModifier
    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Z, control)
    QApplication.processEvents()

    assert ventana.session.scoring.get(1).stage is SleepStage.UNSCORED
    assert ventana.session.scoring.get(0).stage is SleepStage.N2
    assert ventana.session.current_window == 1

    QTest.keyClick(QApplication.focusWidget(), Qt.Key.Key_Y, control)
    QApplication.processEvents()

    assert ventana.session.scoring.get(1).stage is SleepStage.N2


def test_deshacer_una_anotacion_la_saca_de_la_senal(ventana: MainWindow, monkeypatch):
    """Anotar no pasa por `refresh()`: tiene que registrarse igual."""
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("Apnea", True))
    ventana.annotate_current_window()
    assert len(ventana.session.annotations.all()) == 1
    assert bandas_dibujadas(ventana)

    ventana.undo()

    assert ventana.session.annotations.all() == []
    assert bandas_dibujadas(ventana) == []


def test_sin_nada_que_deshacer_la_barra_lo_dice(ventana: MainWindow):
    ventana.undo()

    assert ventana.statusBar().currentMessage() == "No hay nada que deshacer."


def test_lo_recuperado_no_se_deshace(qt_app, tmp_path, monkeypatch):
    """Deshacerlo sería perder lo que se acaba de recuperar."""
    monkeypatch.setattr(WorkGuard, "ask_recovery", lambda *_a: True)
    perfil = tmp_path / "perfil"
    vhdr = escribir_brainvision(tmp_path / "registro", segundos=WINDOW_SECONDS * VENTANAS)
    antes = create_main_window()
    antes.work_guard.enable_recovery(perfil)
    antes.open_recording(vhdr)
    antes.score_current_window(SleepStage.N2)
    antes.work_guard.save_recovery()

    despues = create_main_window()
    despues.work_guard.enable_recovery(perfil)
    despues.open_recording(vhdr)
    despues.undo()

    assert despues.session.scoring.get(0).stage is SleepStage.N2


# -- Anotar un arousal marca su ventana (hito 79) ---------------------------------


def test_anotar_un_arousal_marca_su_ventana(ventana: MainWindow):
    """El arousal existía dos veces sin relación, y la marca es la que llega
    a `Scoring.txt`: un arousal anotado con cuidado no llegaba a ningún lado."""
    ventana.set_annotation_class("Arousal")

    arrastrar_un_tramo(ventana)

    assert ventana.session.scoring.get(0).arousal
    assert ventana.scoring_panel.status().endswith("· arousal")


def test_anotar_otra_clase_no_marca_nada(ventana: MainWindow):
    ventana.set_annotation_class("Spindle")

    arrastrar_un_tramo(ventana)

    assert not ventana.session.scoring.get(0).arousal


def test_cambiar_la_clase_a_arousal_la_marca(ventana: MainWindow, monkeypatch):
    anotacion = anotar_en(ventana, 40.0, 43.0, clase="Spindle")
    herramienta = ventana.tool_controller.tools["annotator"]
    ventana.tool_controller.toggle("annotator", True)
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *_a, **_k: ("Arousal", True))
    )

    ventana._cambiar_clase(herramienta, anotacion)

    assert ventana.session.scoring.get(1).arousal


def test_borrar_el_arousal_no_desmarca_la_ventana(ventana: MainWindow, confirmacion):
    """La marca pudo haberse puesto a mano antes de anotar."""
    ventana.set_annotation_class("Arousal")
    arrastrar_un_tramo(ventana)
    (anotacion,) = ventana.session.annotations.all()
    confirmacion["respuesta"] = True

    ventana._borrar_anotacion(ventana.tool_controller.tools["annotator"], anotacion)

    assert ventana.session.annotations.all() == []
    assert ventana.session.scoring.get(0).arousal


def test_deshacer_el_arousal_anotado_saca_las_dos_cosas(ventana: MainWindow):
    """Anotar y marcar son un solo paso: deshacerlo no deja la marca suelta."""
    ventana.set_annotation_class("Arousal")
    arrastrar_un_tramo(ventana)

    ventana.undo()

    assert ventana.session.annotations.all() == []
    assert not ventana.session.scoring.get(0).arousal
