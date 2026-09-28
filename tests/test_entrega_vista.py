"""Mirar la señal por la ventana: la Übersicht, la reproducción y la rueda.

Es parte de la comprobación de entrega, separada de `test_entrega.py` en el
hito 79, con su misma regla: todo pasa por `MainWindow`.

Cubre las dos nociones horizontales de `CLAUDE.md` —la época, que se scorea,
y la página, que se ve— donde más fácil se confunden: la reproducción cuenta
desde el medio del gráfico y la época es la del cursor (hito 27), y la rueda
cambia la escala dejando quieto el instante que está debajo (hito 56).
"""

from pathlib import Path

import pytest

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.ui import theme  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402

from conftest import escribir_brainvision  # noqa: E402
from entrega_comun import (  # noqa: E402, F401
    VENTANAS,
    arrastrar,
    elige_clase,
    reproduccion,
    ventana,
)


# -- La Übersicht, por la ventana (V1_F, V2_F, V3_F de "Übersicht") ----------


def test_el_panel_de_contexto_arranca_encendido(ventana: MainWindow):
    """Es un panel permanente, no un modo del mouse: `exclusive = False`. Un
    panel que arranca vacío esperando que alguien adivine que hay que apretar
    un botón es un hueco en la pantalla."""
    assert ventana.overview_panel.rectangles(), "la Übersicht arrancó vacía"


@pytest.mark.parametrize(
    "texto, clave", [("Contexto (Übersicht)", "overview"), ("Hipnograma", "histogram")]
)
def test_tildar_un_panel_desde_herramientas_lo_muestra_con_contenido(
    ventana: MainWindow, texto: str, clave: str
):
    """Hito 28: la herramienta y su panel son una sola entrada. La herramienta
    ya estaba prendida desde que se abrió el registro, así que el panel aparece
    con su contenido; destildarlo sólo lo oculta."""
    (entrada,) = [a for a in ventana.tools_menu.actions() if a.text() == texto]
    dock = ventana.docks[clave]

    def tiene_contenido() -> bool:
        if clave == "overview":
            return bool(ventana.overview_panel.rectangles())
        return bool(ventana.histogram_view.getPlotItem().listDataItems())

    # El hipnograma arranca visible desde el hito 64: se lo oculta primero.
    # Con `hide()` y no con la acción, que sigue la visibilidad del panel
    # sólo con la ventana en pantalla, y ésta no se muestra.
    dock.hide()
    assert dock.isHidden()

    entrada.trigger()

    assert not dock.isHidden()
    assert tiene_contenido()

    entrada.trigger()

    # Oculto, pero la herramienta sigue prendida: vuelve a verse igual.
    assert dock.isHidden()
    assert tiene_contenido()


def test_el_panel_sigue_a_la_navegacion(ventana: MainWindow):
    """Se recentra sola: `Session` avisa y la herramienta se entera, que es la
    decisión del hito 6."""
    ventana._go_to_window(3)

    assert ventana.overview_panel.current_index == 3


def test_el_panel_respeta_el_span_asimetrico(ventana: MainWindow):
    """V3_F: el pliego pide poder mostrar dos antes y una después."""
    ventana._go_to_window(2)
    ventana.tool_controller.tools["overview"].set_span(before=2, after=1)

    indices = [v.index for v, _ in ventana.overview_panel.rectangles()]
    assert indices == [0, 1, 2, 3]


def test_el_tamano_del_panel_llega_a_la_pantalla(ventana: MainWindow):
    """V2_F. `set_size()` existía desde el hito 7 y no lo llamaba nadie."""
    ventana.tool_controller.tools["overview"].set_size(600, 130)

    assert ventana.overview_panel.height() == 130


def test_los_eventos_anotados_aparecen_en_el_panel(
    ventana: MainWindow, elige_clase
):
    """V3_F: ver que hay un huso justo antes sin navegar hasta ahí. Cierra el
    lazo completo: anotar por el mouse y verlo en el contexto."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._go_to_window(2)
    ventana.tool_controller.toggle("annotator", True)
    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    con_eventos = [
        v.index for v, _ in ventana.overview_panel.rectangles() if v.annotation_labels
    ]
    assert 2 in con_eventos


# -- La reproducción, contada desde el medio (hitos 24 y 27) --------------------
#
# Por la ventana, como todo este archivo: los botones se aprietan con
# `click()` y el reloj se hace avanzar emitiendo su señal, que es lo mismo que
# hace el temporizador. Esperar al temporizador de verdad ataría el test a la
# velocidad de la máquina.
#
# **Desde el hito 27 la época sigue al medio del gráfico** mientras se
# reproduce: el cursor arranca en el centro de la época actual, la página se
# centra en él y la época es la suya. Hasta ese hito la reproducción movía la
# página y la época no se tocaba. El registro de prueba dura cinco épocas, 150 s.


def pagina(ventana: MainWindow) -> float:
    return ventana.session.viewport.start_seconds


def centro_de(epoca: int) -> float:
    return (epoca + 0.5) * WINDOW_SECONDS


def test_reproducir_lleva_la_epoca_que_pasa_por_el_medio(reproduccion: MainWindow):
    """Al pausar, el usuario queda parado en la época que estaba mirando."""
    ventana = reproduccion

    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(10.0)
    ventana.playback_controller.clock.advanced.emit(10.0)

    assert ventana.playback_controller.is_playing
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(0) + 20.0)
    assert ventana.session.viewport.center_seconds == pytest.approx(centro_de(0) + 20.0)
    assert ventana.session.current_window == 1
    assert ventana.navigation._reproducir.toolTip() == "Pausar"
    assert not ventana.carteles


def test_la_epoca_nueva_llega_a_la_barra_y_al_scoring(reproduccion: MainWindow):
    """Lo que depende de la época se pone al día sin que nadie llame a
    `refresh()`: la posición de la barra y el pie del scoring."""
    ventana = reproduccion

    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(WINDOW_SECONDS)

    # La lectura lleva también la hora desde el hito 36, cuando el registro la
    # informa: son la misma pregunta en dos unidades.
    assert ventana.navigation._posicion.text().endswith(f"Ventana 2 de {VENTANAS}")
    assert ventana.scoring_panel.status().startswith("Ventana 2 ")


def test_con_la_pagina_de_una_epoca_arrancar_no_salta(reproduccion: MainWindow):
    """El cursor arranca en el centro de la época actual, que con la página de
    30 s ya es el medio de la pantalla."""
    ventana = reproduccion
    ventana._go_to_window(3)
    antes = ventana.session.viewport

    ventana.toggle_playback()

    assert ventana.session.viewport == antes
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(3))


def test_al_principio_el_cursor_avanza_y_la_pagina_no(reproduccion: MainWindow):
    """Con una página de dos épocas, el medio queda a 30 s: hasta ahí la
    página no se puede mover y es el cursor el que avanza adentro de ella."""
    ventana = reproduccion
    ventana.set_timescale(2 * WINDOW_SECONDS)

    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(10.0)

    assert pagina(ventana) == 0.0
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(0) + 10.0)

    ventana.playback_controller.clock.advanced.emit(10.0)

    assert pagina(ventana) == pytest.approx(centro_de(0) + 20.0 - WINDOW_SECONDS)
    assert ventana.session.current_window == 1


def test_al_final_el_cursor_llega_al_borde_y_se_detiene(reproduccion: MainWindow):
    """La página ya no se mueve, y el cursor sigue hasta el final del registro:
    así se recorren también las últimas épocas."""
    ventana = reproduccion
    ventana.set_timescale(2 * WINDOW_SECONDS)
    ventana._go_to_window(VENTANAS - 1)

    ventana.toggle_playback()
    pagina = ventana.session.viewport
    assert pagina.end_seconds == pytest.approx(pagina.duration_seconds)
    ventana.playback_controller.clock.advanced.emit(10.0)
    assert ventana.playback_controller.is_playing

    ventana.playback_controller.clock.advanced.emit(10 * WINDOW_SECONDS)

    assert not ventana.playback_controller.is_playing
    assert ventana.session.current_window == VENTANAS - 1
    assert ventana.statusBar().currentMessage() == "Fin del registro"
    assert ventana.signal_view.playhead() is None
    assert ventana.navigation._reproducir.isEnabled()


def test_con_el_registro_entero_en_pantalla_tambien_reproduce(reproduccion: MainWindow):
    """Hasta el hito 27 no arrancaba: no había página que mover. Ahora se mueve
    el cursor, y la época con él."""
    ventana = reproduccion
    ventana.show_whole_recording()
    entera = ventana.session.viewport

    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(2 * WINDOW_SECONDS)

    assert ventana.playback_controller.is_playing
    assert ventana.session.viewport == entera
    assert ventana.session.current_window == 2


def test_arranca_desde_la_epoca_actual_aunque_la_vista_se_haya_ido(
    reproduccion: MainWindow,
):
    """Mayús+→ en pausa mueve la vista y no la época, y la reproducción sale
    de la época que se está scoreando, no de lo que quedó en pantalla."""
    ventana = reproduccion
    for _ in range(2 * VENTANAS):
        ventana.pan_view_page_right()

    ventana.toggle_playback()

    assert ventana.playback_controller.is_playing
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(0))
    assert pagina(ventana) == 0.0


def test_sin_registro_reproducir_no_hace_nada(qt_app):
    principal = create_main_window()

    principal.toggle_playback()

    assert not principal.playback_controller.is_playing


def test_apretar_de_nuevo_pausa(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.navigation._reproducir.click()
    ventana.playback_controller.clock.advanced.emit(5.0)

    ventana.navigation._reproducir.click()

    assert not ventana.playback_controller.is_playing
    assert pagina(ventana) == pytest.approx(5.0)
    assert ventana.navigation._reproducir.toolTip() == "Reproducir"


def test_al_pausar_se_va_el_cursor_y_se_queda_la_epoca(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(20.0)
    pagina_al_pausar = ventana.session.viewport

    ventana.toggle_playback()

    assert ventana.signal_view.playhead() is None
    assert ventana.session.current_window == 1
    assert ventana.session.viewport == pagina_al_pausar


def test_siguiente_y_anterior_reproduciendo_llevan_el_cursor(reproduccion: MainWindow):
    """Saltan una época y la reproducción sigue desde su centro."""
    ventana = reproduccion
    ventana.toggle_playback()

    ventana.navigation._siguiente.click()
    assert ventana.session.current_window == 1
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(1))

    ventana.go_to_next_window()
    assert ventana.session.current_window == 2

    ventana.navigation._anterior.click()
    assert ventana.session.current_window == 1
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(1))
    assert ventana.playback_controller.is_playing
    assert not ventana.carteles


def test_la_ultima_y_la_franja_reproduciendo_llevan_el_cursor(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.toggle_playback()

    ventana.navigation._ultima.click()
    assert ventana.session.current_window == VENTANAS - 1
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(VENTANAS - 1))

    ventana._go_to_window(2)
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(2))
    assert ventana.playback_controller.is_playing


def test_siguiente_en_la_ultima_reproduciendo_no_hace_nada(reproduccion: MainWindow):
    """Como la flecha en pausa: llegar al borde no es un error ni un salto al
    final del registro."""
    ventana = reproduccion
    ventana._go_to_window(VENTANAS - 1)
    ventana.toggle_playback()

    ventana.go_to_next_window()

    assert ventana.signal_view.playhead() == pytest.approx(centro_de(VENTANAS - 1))
    assert ventana.playback_controller.is_playing


def test_en_pausa_las_flechas_mueven_la_pagina_lo_minimo(ventana: MainWindow):
    """Como siempre: con la época adentro de la página, la flecha mueve el
    resaltado y no la vista. Sólo reproduciendo se centra."""
    ventana.set_timescale(VENTANAS * WINDOW_SECONDS)
    antes = ventana.session.viewport

    ventana.go_to_next_window()

    assert ventana.session.current_window == 1
    assert ventana.session.viewport == antes
    assert ventana.signal_view.playhead() is None


@pytest.mark.parametrize(
    "accion, esperado",
    [
        ("pan_view_page_right", WINDOW_SECONDS),
        ("pan_view_right", WINDOW_SECONDS / 2),
    ],
)
def test_los_atajos_de_pagina_en_pausa_mueven_la_vista_y_no_la_epoca(
    ventana: MainWindow, accion: str, esperado: float
):
    """Los botones de página se sacaron en el hito 27; sus atajos se quedan."""
    epoca = ventana.session.current_window

    getattr(ventana, accion)()

    assert pagina(ventana) == pytest.approx(esperado)
    assert ventana.session.current_window == epoca
    assert not ventana.carteles


def test_los_atajos_de_pagina_reproduciendo_mueven_el_cursor(reproduccion: MainWindow):
    """Si movieran sólo la página, el paso siguiente la devolvería al cursor."""
    ventana = reproduccion
    ventana.toggle_playback()

    ventana.pan_view_page_right()

    assert ventana.signal_view.playhead() == pytest.approx(centro_de(0) + WINDOW_SECONDS)
    assert ventana.session.current_window == 1
    assert ventana.playback_controller.is_playing


def test_scorear_reproduciendo_no_saca_la_pagina_del_cursor(reproduccion: MainWindow):
    """Con la página de 30 s centrada en el cursor la época no entra entera, y
    redibujar con `containing()` la llevaba al comienzo de la época."""
    from psglab.core.nomenclature import SleepStage

    ventana = reproduccion
    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(10.0)
    centrada = ventana.session.viewport

    ventana.score_current_window(SleepStage.N2)

    assert ventana.session.viewport == centrada
    assert ventana.session.scoring.get(0).stage is SleepStage.N2


def test_abrir_otro_registro_detiene_la_reproduccion(
    reproduccion: MainWindow, tmp_path: Path
):
    ventana = reproduccion
    ventana.toggle_playback()

    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 3)
    ventana.open_recording(otro)

    assert not ventana.playback_controller.is_playing
    assert pagina(ventana) == 0.0
    assert ventana.signal_view.playhead() is None


def test_volver_a_la_senal_original_detiene_la_reproduccion(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.accion_señal_original.setEnabled(True)
    ventana.toggle_playback()

    ventana.restore_original_recording()

    assert not ventana.playback_controller.is_playing


def test_la_velocidad_del_selector_llega_al_reloj(reproduccion: MainWindow):
    selector = reproduccion.navigation.speed_selector

    selector.setCurrentIndex(selector.findText("30×"))

    assert reproduccion.playback_controller.clock.speed == 30.0


def test_espacio_reproduce_y_pausa(reproduccion: MainWindow):
    """El atajo cuelga de la señal. Se lo dispara por su señal: apretar la
    tecla de verdad necesita la ventana en pantalla y con el foco."""
    from PySide6.QtGui import QShortcut

    ventana = reproduccion
    (espacio,) = [
        a for a in ventana.findChildren(QShortcut) if a.key().toString() == "Space"
    ]

    espacio.activated.emit()
    assert ventana.playback_controller.is_playing

    espacio.activated.emit()
    assert not ventana.playback_controller.is_playing


def test_el_programa_abre_con_la_senal_los_canales_el_scoring_y_el_hipnograma(
    ventana: MainWindow,
):
    """Hito 24, con el hipnograma de vuelta desde el 64 y el scoring compacto
    desde el 79. Con un registro abierto sigue igual: abrir no despliega nada
    más."""
    visibles = [clave for clave, dock in ventana.docks.items() if not dock.isHidden()]

    assert visibles == ["channels", "scoring", "histogram"]


# -- La Übersicht dibuja señal y lleva a su ventana (hito 51) ----------------


def _clic_en_la_ubersicht(ventana: MainWindow, indice: int) -> None:
    """Un clic de Qt de verdad sobre la caja de una ventana del contexto."""
    panel = ventana.overview_panel
    (caja,) = [c for v, c in panel.rectangles() if v.index == indice]
    punto = caja.center()
    for tipo in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        evento = QMouseEvent(
            tipo,
            punto,
            panel.mapTo(panel.window(), punto.toPoint()).toPointF(),
            panel.mapToGlobal(punto.toPoint()).toPointF(),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton if tipo == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(panel, evento)


def test_un_clic_en_la_ubersicht_lleva_a_esa_ventana(ventana: MainWindow):
    """**Hasta el hito 51 el panel no respondía al mouse.** Ahora un clic en la
    caja de la ventana siguiente la vuelve la actual, y el contexto se
    recentra sobre ella."""
    ventana._go_to_window(2)

    _clic_en_la_ubersicht(ventana, 3)

    assert ventana.session.current_window == 3
    assert ventana.overview_panel.current_index == 3
    assert not ventana.carteles


def test_la_ubersicht_dibuja_la_senal_del_canal_seleccionado(ventana: MainWindow):
    """Sin selección es el primer canal visible; al seleccionar otro, el
    contexto lo sigue sin que haga falta navegar, y con el color de su carril."""
    visibles = ventana.session.visible_channels
    assert {v.trace.channel_name for v, _ in ventana.overview_panel.rectangles()} == {
        visibles[0]
    }

    ventana._set_selected_channels([visibles[1]])

    assert {v.trace.channel_name for v, _ in ventana.overview_panel.rectangles()} == {
        visibles[1]
    }
    assert ventana.overview_panel._trace_color == theme.current().color_for_channel(1)


def test_la_amplitud_llega_a_la_ubersicht(ventana: MainWindow):
    """La miniatura usa la escala del visualizador, así que subir la amplitud
    también la cambia a ella, sin esperar a la próxima flecha."""
    canal = ventana.session.visible_channels[0]
    ventana._set_selected_channels([canal])

    ventana.increase_amplitude()

    escalas = {v.trace.scale_uv for v, _ in ventana.overview_panel.rectangles()}
    assert escalas == {ventana.session.scale_uv(canal)}


# -- La rueda cambia la escala de tiempo (hito 56) --------------------------


def girar_la_rueda(
    ventana: MainWindow,
    segundos: float,
    muescas: float,
    horizontal: bool = False,
    mayusculas: bool = False,
    de_costado: float = 0.0,
) -> None:
    """Gira la rueda sobre la señal, con el mouse en ese segundo del registro.

    Por el viewport y armado como lo arma Qt, igual que `evento_de_mouse()`:
    una muesca son 120 octavos de grado. Hacia adelante es positivo, y en el
    eje horizontal, hacia la izquierda.

    `de_costado` suma muescas horizontales a un giro vertical: un panel táctil
    casi nunca desliza derecho.
    """
    vista = ventana.signal_view
    caja = vista.getPlotItem().vb
    x = caja.mapViewToScene(QPointF(segundos, 0.0)).x()
    local = QPointF(vista.mapFromScene(QPointF(x, caja.sceneBoundingRect().center().y())))
    viewport = vista.viewport()
    delta = round(muescas * 120)
    angulo = QPoint(delta, 0) if horizontal else QPoint(round(de_costado * 120), delta)
    QApplication.instance().sendEvent(
        viewport,
        QWheelEvent(
            local,
            QPointF(viewport.mapToGlobal(local.toPoint())),
            QPoint(),
            angulo,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.ShiftModifier if mayusculas else Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        ),
    )


@pytest.fixture
def pagina_de_un_minuto(ventana: MainWindow) -> MainWindow:
    """Una página de 60 s que empieza en el segundo 30: hay lugar para
    alejarse y para acercarse sin tocar los bordes del registro."""
    ventana._cambiar_pagina(ventana.session.viewport.with_span(60.0).with_start(30.0))
    return ventana


def test_la_rueda_hacia_adelante_acerca(pagina_de_un_minuto: MainWindow):
    """Dos muescas duplican: acá, la página pasa a durar la mitad."""
    ventana = pagina_de_un_minuto

    girar_la_rueda(ventana, 60.0, 2)

    assert ventana.session.viewport.span_seconds == pytest.approx(30.0)
    assert not ventana.carteles


def test_la_rueda_hacia_atras_aleja(pagina_de_un_minuto: MainWindow):
    ventana = pagina_de_un_minuto

    girar_la_rueda(ventana, 60.0, -2)

    assert ventana.session.viewport.span_seconds == pytest.approx(120.0)


def test_la_rueda_deja_quieto_lo_que_esta_bajo_el_mouse(pagina_de_un_minuto: MainWindow):
    """**Es la diferencia con Ctrl++**, que acerca hacia el centro: para mirar
    un huso de cerca se lo apunta y se gira, sin centrarlo antes."""
    ventana = pagina_de_un_minuto
    antes = ventana.session.viewport
    # El segundo que el mouse tiene de verdad debajo, después de redondear
    # al píxel: es ése el que no se tiene que mover.
    girar_la_rueda(ventana, 45.0, 1)

    despues = ventana.session.viewport
    fraccion_antes = (45.0 - antes.start_seconds) / antes.span_seconds
    assert despues.span_seconds < antes.span_seconds
    assert despues.start_seconds + fraccion_antes * despues.span_seconds == pytest.approx(
        45.0, abs=0.2
    )
    assert despues.center_seconds < antes.center_seconds


def test_la_rueda_llega_al_dibujo_y_al_cartel(pagina_de_un_minuto: MainWindow):
    """No sólo a la sesión: el eje de la señal y el cartel de la página."""
    ventana = pagina_de_un_minuto
    cartel = ventana.page_readout.text()

    girar_la_rueda(ventana, 60.0, 2)

    izquierda, derecha = ventana.signal_view.getPlotItem().vb.viewRange()[0]
    assert derecha - izquierda == pytest.approx(30.0, rel=0.05)
    assert ventana.page_readout.text() != cartel


def test_la_rueda_no_cambia_la_epoca(pagina_de_un_minuto: MainWindow):
    """La página es lo que se ve; la época es lo que se scorea."""
    ventana = pagina_de_un_minuto
    epoca = ventana.session.current_window

    girar_la_rueda(ventana, 80.0, 4)

    assert ventana.session.current_window == epoca


def test_deslizar_de_costado_desplaza_sin_cambiar_la_escala(pagina_de_un_minuto: MainWindow):
    """Lo que manda un panel táctil al deslizar hacia la izquierda: la página
    avanza en el registro, un décimo de sí misma por muesca."""
    ventana = pagina_de_un_minuto
    antes = ventana.session.viewport

    girar_la_rueda(ventana, 60.0, -2, horizontal=True)

    despues = ventana.session.viewport
    assert despues.span_seconds == pytest.approx(antes.span_seconds)
    assert despues.start_seconds == pytest.approx(antes.start_seconds + 0.2 * antes.span_seconds)


def test_deslizar_hacia_el_otro_lado_retrocede(pagina_de_un_minuto: MainWindow):
    ventana = pagina_de_un_minuto
    antes = ventana.session.viewport

    girar_la_rueda(ventana, 60.0, 2, horizontal=True)

    assert ventana.session.viewport.start_seconds < antes.start_seconds


def test_mayusculas_y_la_rueda_desplazan(pagina_de_un_minuto: MainWindow):
    """En Windows llega como rueda vertical con Mayúsculas. Hacia atrás
    avanza en el registro, como bajar en un documento."""
    ventana = pagina_de_un_minuto
    antes = ventana.session.viewport

    girar_la_rueda(ventana, 60.0, -1, mayusculas=True)

    despues = ventana.session.viewport
    assert despues.span_seconds == pytest.approx(antes.span_seconds)
    assert despues.start_seconds == pytest.approx(antes.start_seconds + 0.1 * antes.span_seconds)


def test_mayusculas_ya_convertida_en_horizontal_tambien_desplaza(pagina_de_un_minuto: MainWindow):
    """macOS la entrega como horizontal, con Mayúsculas todavía apretada."""
    ventana = pagina_de_un_minuto
    antes = ventana.session.viewport

    girar_la_rueda(ventana, 60.0, -1, horizontal=True, mayusculas=True)

    assert ventana.session.viewport.start_seconds == pytest.approx(
        antes.start_seconds + 0.1 * antes.span_seconds
    )


def test_un_gesto_torcido_hace_una_sola_cosa(pagina_de_un_minuto: MainWindow):
    """Deslizar de costado con un poco de vertical no puede cambiar también
    la escala: manda el eje que más se movió."""
    ventana = pagina_de_un_minuto
    antes = ventana.session.viewport

    girar_la_rueda(ventana, 60.0, 0.25, de_costado=-2)

    despues = ventana.session.viewport
    assert despues.span_seconds == pytest.approx(antes.span_seconds)
    assert despues.start_seconds > antes.start_seconds


def test_desplazar_en_el_final_no_se_pasa(pagina_de_un_minuto: MainWindow):
    ventana = pagina_de_un_minuto

    girar_la_rueda(ventana, 60.0, -100, horizontal=True)

    assert ventana.session.viewport.end_seconds == pytest.approx(WINDOW_SECONDS * VENTANAS)
    assert not ventana.carteles


def test_reproduciendo_desplazar_mueve_el_cursor(reproduccion: MainWindow):
    """Si se moviera sólo la página, el paso siguiente la devolvería al
    cursor y el gesto no habría hecho nada."""
    ventana = reproduccion
    ventana.set_timescale(60.0)
    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(40.0)
    cursor = ventana.signal_view.playhead()

    girar_la_rueda(ventana, 60.0, -1, horizontal=True)

    assert ventana.signal_view.playhead() == pytest.approx(cursor + 6.0)


def test_en_el_registro_entero_alejar_no_hace_nada(ventana: MainWindow):
    ventana.show_whole_recording()
    antes = ventana.session.viewport

    girar_la_rueda(ventana, 60.0, -2)

    assert ventana.session.viewport == antes
    assert not ventana.carteles


def test_reproduciendo_la_rueda_acerca_hacia_el_cursor(reproduccion: MainWindow):
    """**La página es del cursor** mientras se reproduce: anclarla en el mouse
    la haría saltar al cuadro siguiente, que la vuelve a centrar."""
    ventana = reproduccion
    ventana.set_timescale(60.0)
    ventana.toggle_playback()
    ventana.playback_controller.clock.advanced.emit(40.0)
    cursor = ventana.signal_view.playhead()

    girar_la_rueda(ventana, ventana.session.viewport.start_seconds + 5.0, 2)

    assert ventana.session.viewport.span_seconds == pytest.approx(30.0)
    assert ventana.session.viewport.center_seconds == pytest.approx(cursor)
