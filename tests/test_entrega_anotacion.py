"""Anotar por la ventana: el mouse, las herramientas que dibujan y las clases.

Es parte de la comprobación de entrega, separada de `test_entrega.py` en el
hito 79, y es **donde nació su regla**: el hito 9 existió porque la entrega se
había verificado anotando desde un script, y en el programa corriendo no había
forma de anotar. Por eso los gestos se mandan como eventos de Qt al viewport,
con `arrastrar()` y `evento_de_mouse()`, y nunca se llama a la herramienta.

Cubre anotar y corregir una anotación, la clase activa, las marcas que trae el
archivo, y el camino entre una herramienta que dibuja y la pantalla.
"""

from pathlib import Path

import numpy as np
import pytest
import json

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtWidgets import QApplication, QInputDialog

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.core.annotations import Annotation  # noqa: E402
from psglab.exporters import DEFAULT_FILENAMES as NOMBRES  # noqa: E402
# Los módulos donde se buscan los nombres que la suite reemplaza (hito 76):
# reemplazarlos en `main_window` no tendría efecto, porque ahí ya no se usan.
import psglab.ui.window_files as files_mod  # noqa: E402
from psglab.ui import preferences as preferencias_mod  # noqa: E402
from psglab.tools.base import BandOverlay  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402

from conftest import FRECUENCIA_BV, escribir_brainvision  # noqa: E402
from entrega_comun import (  # noqa: E402, F401
    anotar_en,
    arrastrar,
    arrastrar_un_tramo,
    bandas_dibujadas,
    clic_derecho,
    confirmacion,
    elige_clase,
    elige_en_el_menu,
    evento_de_mouse,
    otro_registro,
    ventana,
)


# -- Anotar, por el camino del mouse (V1_F de "Anotación") -------------------
#
# Estos dos estuvieron marcados `xfail` mientras duró el hueco del hito 9:
# `main_window` no leía `pending_selection_samples` ni llamaba a
# `create_annotation()`, así que se podía arrastrar una selección y no pasaba
# nada. Se les sacó la marca al cablearlo.
#
# **Mandan eventos de Qt de verdad al viewport**, no llaman a la herramienta.
# Ésa es toda la diferencia: llamando a la herramienta, estos tests pasaban en
# verde con el programa roto, que fue exactamente lo que ocurrió en el hito 6.


def test_se_puede_anotar_un_evento_desde_la_interfaz(
    ventana: MainWindow, elige_clase
):
    """**El camino, no la pieza.**"""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    anotaciones = ventana.session.annotations.all()
    assert len(anotaciones) == 1
    assert anotaciones[0].label == "Spindle"
    assert anotaciones[0].duration_samples > 0
    assert not ventana.carteles


def test_la_anotacion_cae_en_la_ventana_en_la_que_se_hizo(
    ventana: MainWindow, elige_clase
):
    """El error caro: sin sumar el desplazamiento de la ventana, todas las
    anotaciones caen al principio del registro."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)
    ventana._go_to_window(3)

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    inicio = ventana.session.annotations.all()[0].onset_sample
    por_ventana = FRECUENCIA_BV * WINDOW_SECONDS
    assert 3 * por_ventana <= inicio < 4 * por_ventana


def test_la_anotacion_empieza_y_termina_bajo_el_mouse(
    ventana: MainWindow, elige_clase
):
    """**El síntoma que reportó el usuario**: la selección empezaba a la
    derecha del mouse, corrida por el ancho del selector de canales, porque se
    tomaba `scenePosition()` —que en un evento de widget es la ventana— como
    si fuera la escena de pyqtgraph."""
    ventana.resize(1400, 800)
    ventana.show()
    QApplication.processEvents()
    viewport = ventana.signal_view.viewport()
    # Sin distancia entre el gráfico y el borde de la ventana, el test no
    # distinguiría una posición de la otra y pasaría con el error puesto.
    assert viewport.mapTo(ventana, viewport.rect().topLeft()).x() > 0

    vista = ventana.signal_view.getPlotItem().vb
    caja = vista.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)
    desde_x = caja.left() + caja.width() * 0.25
    hasta_x = caja.left() + caja.width() * 0.35

    arrastrar(ventana, desde_x, hasta_x)

    anotacion = ventana.session.annotations.all()[0]
    fs = ventana.session.recording.sampling_rate
    # Un píxel de tolerancia: el evento llega redondeado a píxel entero.
    un_pixel = ventana.session.viewport.span_seconds / caja.width()
    for muestra, x in (
        (anotacion.onset_sample, desde_x),
        (anotacion.end_sample, hasta_x),
    ):
        esperado = vista.mapSceneToView(QPointF(x, 0.0)).x()
        assert abs(muestra / fs - esperado) <= un_pixel


def test_las_bandas_siguen_a_la_pagina(ventana: MainWindow):
    """Pasar de época con la flecha cambia qué bandas van. Hasta que se
    corrigió, seguían dibujadas las de la página anterior."""
    anotar_en(ventana, 10.0, 12.0)
    anotar_en(ventana, 40.0, 43.0)
    ventana.tool_controller.toggle("annotator", True)

    ventana._go_to_window(1)
    assert bandas_dibujadas(ventana) == [(40.0, 43.0)]
    ventana._go_to_window(0)
    assert bandas_dibujadas(ventana) == [(10.0, 12.0)]


@pytest.mark.parametrize("otra", [None, "magnifier", "occupancy", "amplitude_band"])
def test_las_anotaciones_se_ven_con_cualquier_herramienta(
    ventana: MainWindow, otra: str | None
):
    """Decidido con el usuario: una anotación es un dato del registro y se ve
    siempre. Antes se veía lo de la última herramienta que avisó, y activar la
    lupa las borraba de la pantalla."""
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)
    ventana.tool_controller.toggle("annotator", False)
    if otra is not None:
        ventana.tool_controller.toggle(otra, True)

    assert (10.0, 12.0) in bandas_dibujadas(ventana)
    # Y siguen a la página con esa herramienta activa: ir y volver es lo que
    # las perdía, porque nadie volvía a pedirlas.
    ventana._go_to_window(1)
    assert (10.0, 12.0) not in bandas_dibujadas(ventana)
    ventana._go_to_window(0)
    assert (10.0, 12.0) in bandas_dibujadas(ventana)


def test_el_clic_derecho_borra_la_anotacion(
    ventana: MainWindow, confirmacion, elige_en_el_menu
):
    """Desde el hito 52, eligiendo «Borrar» en el menú del clic derecho."""
    elige_en_el_menu.elegir("Borrar")
    anotar_en(ventana, 10.0, 12.0, "Spindle")
    queda = anotar_en(ventana, 20.0, 22.0)
    ventana.tool_controller.toggle("annotator", True)

    clic_derecho(ventana, 11.0)

    assert ventana.session.annotations.all() == [queda]
    assert (10.0, 12.0) not in bandas_dibujadas(ventana)
    assert "Spindle" in confirmacion["preguntas"][0]["pregunta"]
    assert not ventana.carteles


def test_el_clic_derecho_pregunta_antes_de_borrar(
    ventana: MainWindow, confirmacion, elige_en_el_menu
):
    """No hay deshacer: elegir mal en el menú no puede costar un evento."""
    elige_en_el_menu.elegir("Borrar")
    confirmacion["respuesta"] = False
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)

    clic_derecho(ventana, 11.0)

    assert len(ventana.session.annotations.all()) == 1


def test_el_clic_derecho_sin_anotar_no_borra(
    ventana: MainWindow, monkeypatch, elige_en_el_menu
):
    """Sólo con «Anotar» activo: con otra herramienta el clic es suyo, y ni
    siquiera se abre el menú."""
    elige_en_el_menu.elegir("Borrar")

    def no_deberia_preguntar(*_a, **_k):
        pytest.fail("con la lupa activa, el clic derecho no puede borrar")

    monkeypatch.setattr(MainWindow, "_confirmar", no_deberia_preguntar)
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("magnifier", True)

    clic_derecho(ventana, 11.0)

    assert len(ventana.session.annotations.all()) == 1
    assert elige_en_el_menu.menus == []


def test_se_puede_crear_una_clase_nueva_al_vuelo(ventana: MainWindow, elige_clase):
    """El pliego pide **asignarle o crear** una clase, así que el diálogo es
    editable y lo que se escriba se registra con su color."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)
    elige_clase("Espiga temporal")

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    assert "Espiga temporal" in ventana.session.annotations.labels()
    assert ventana.session.annotations.all()[0].label == "Espiga temporal"


def test_cancelar_el_dialogo_no_anota(ventana: MainWindow, elige_clase):
    """Quien se arrepiente a mitad del gesto no puede quedarse con un evento
    que no pidió."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)
    elige_clase("Spindle", acepta=False)

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    assert ventana.session.annotations.all() == []
    assert not ventana.carteles


def test_una_clase_vacia_no_anota(ventana: MainWindow, elige_clase):
    """Aceptar con el campo en blanco es un error de dedo, no una clase."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)
    elige_clase("   ")

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    assert ventana.session.annotations.all() == []


def test_las_anotaciones_exportadas_no_estan_vacias(
    ventana: MainWindow, elige_clase, tmp_path: Path
):
    """Cierra V2_F de "Archivo de salida", que dependía de esto: sin forma de
    anotar, `Anotaciones.txt` salía siempre vacío."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("annotator", True)
    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    destino = tmp_path / NOMBRES["annotations"]
    ventana.export("annotations", destino)

    assert "Spindle" in destino.read_text(encoding="utf-8")


def test_un_clic_no_borra_la_linea_de_ocupacion_que_estaba_lejos(
    ventana: MainWindow,
):
    """**La consecuencia del bug de unidades, vista por la ventana.**

    La tolerancia de la ocupación son 10 µV. Mientras la `y` llegaba en
    carriles —de 0 a 1— cualquier clic dentro del rango horizontal de una línea
    caía dentro de la tolerancia y la borraba en vez de empezar otra.
    """
    from psglab.tools.occupancy import OccupancyLine

    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana.tool_controller.toggle("occupancy", True)
    herramienta = ventana.tool_controller.tools["occupancy"]
    herramienta.add_line(OccupancyLine(0.2, 0.0, 0.6, 0.0))

    # **Un clic a 90 µV de la línea, que está en y = 0**, y adentro de su mismo
    # carril: la tolerancia es el 10 % de la escala, o sea 10 µV sobre los 100
    # del primer canal. Hasta el hito 45 acá alcanzaba con apuntar al medio del
    # gráfico, porque la `y` se medía contra el primer canal y el medio caía a
    # cientos de µV; con el carril bien resuelto, el medio de un carril es cero
    # y el clic caía justo encima de la línea.
    primero = ventana.session.visible_channels[0]
    arrastrar(
        ventana,
        caja.left() + caja.width() * 0.3,
        caja.left() + caja.width() * 0.4,
        canal=primero,
        uv=90.0,
    )

    assert herramienta.lines(), "el clic lejano borró la línea"


# -- Lo que la herramienta calcula y el usuario tiene que ver ----------------


def test_la_ocupacion_muestra_su_porcentaje(ventana: MainWindow):
    """V3_F de "Ocupación". `total_percentage()` calculaba bien desde el hito 7
    y **no lo leía nadie**: el número existía sólo para sus tests."""
    from psglab.tools.occupancy import OccupancyLine

    ventana.tool_controller.toggle("occupancy", True)
    ventana.tool_controller.tools["occupancy"].add_line(OccupancyLine(0.1, 0.0, 0.4, 0.0))

    assert "30,0 %" in ventana.tool_readout.text()
    assert "1 línea" in ventana.tool_readout.text()


def test_sin_lineas_lo_dice_en_vez_de_mostrar_cero(ventana: MainWindow):
    ventana.tool_controller.toggle("occupancy", True)

    assert "sin líneas" in ventana.tool_readout.text()


def test_el_total_puede_pasar_del_cien_por_ciento(ventana: MainWindow):
    """Confirmado con el cliente: con el criterio del pliego, la zona que dos
    líneas comparten se cuenta dos veces. **La interfaz tiene que poder
    mostrarlo sin romperse ni recortarlo.**"""
    from psglab.tools.occupancy import OccupancyLine

    ventana.tool_controller.toggle("occupancy", True)
    herramienta = ventana.tool_controller.tools["occupancy"]
    herramienta.add_line(OccupancyLine(0.0, 0.0, 0.9, 0.0))
    herramienta.add_line(OccupancyLine(0.1, 0.0, 1.0, 0.0))

    assert "180,0 %" in ventana.tool_readout.text()


def test_el_separador_decimal_es_la_coma(ventana: MainWindow):
    """Es el idioma del programa."""
    from psglab.tools.occupancy import OccupancyLine

    ventana.tool_controller.toggle("occupancy", True)
    ventana.tool_controller.tools["occupancy"].add_line(OccupancyLine(0.0, 0.0, 0.335, 0.0))

    texto = ventana.tool_readout.text()
    assert "," in texto
    assert "33.5" not in texto


def test_la_lupa_muestra_los_picos_contados(ventana: MainWindow):
    """V2_F de "Lupa": el contador tampoco lo leía nadie."""
    ventana.tool_controller.toggle("magnifier", True)
    herramienta = ventana.tool_controller.tools["magnifier"]
    herramienta.on_mouse_press(5.0, 0.0, "left")
    herramienta.on_mouse_press(7.0, 0.0, "left")

    assert "Picos contados: 2" in ventana.tool_readout.text()


def test_apagar_la_herramienta_limpia_el_cartel(ventana: MainWindow):
    """Un número viejo al lado de una herramienta apagada es peor que ninguno."""
    ventana.tool_controller.toggle("magnifier", True)
    ventana.tool_controller.tools["magnifier"].on_mouse_press(5.0, 0.0, "left")
    assert ventana.tool_readout.text()

    ventana.tool_controller.toggle("magnifier", False)
    assert ventana.tool_readout.text() == ""


# -- Lo que la sesión sabe de las herramientas -------------------------------
#
# `Session.active_tool` existía con su docstring y su test desde el hito 6, y
# la ventana no se lo decía nunca: era `None` pasara lo que pasara. El hito 33
# lo conectó, que es el mismo hallazgo de siempre —código correcto sin ningún
# camino desde la pantalla— visto desde `core/`.


def test_la_sesion_sabe_cual_es_la_herramienta_activa(ventana: MainWindow):
    """Prender una herramienta del menú se lo dice a la sesión."""
    ventana.tool_controller.toggle("magnifier", True)
    assert ventana.session.active_tool == "magnifier"

    # La exclusividad vale también acá: prender otra sustituye, no suma.
    ventana.tool_controller.toggle("annotator", True)
    assert ventana.session.active_tool == "annotator"

    ventana.tool_controller.toggle("annotator", False)
    assert ventana.session.active_tool is None


def test_un_panel_no_desplaza_a_la_herramienta_del_mouse(ventana: MainWindow):
    """`active_tool` es **la exclusiva**, y el histograma no lo es.

    Prender un panel no puede tapar a la lupa, porque no compite con ella por
    el clic: el usuario sigue con la lupa en la mano.
    """
    ventana.tool_controller.toggle("magnifier", True)
    ventana.tool_controller.toggle("histogram", True)

    assert ventana.session.active_tool == "magnifier"


def test_abrir_otro_registro_deja_la_sesion_sin_herramienta(
    ventana: MainWindow, tmp_path: Path
):
    """Las herramientas se sueltan al cambiar de registro, y la sesión que
    queda atrás tiene que decir lo mismo que la barra: ninguna activa."""
    ventana.tool_controller.toggle("magnifier", True)
    anterior = ventana.session

    ventana.open_recording(otro_registro(tmp_path))

    assert anterior.active_tool is None
    assert ventana.session.active_tool is None


# -- El camino entre una herramienta que dibuja y la pantalla (hito 45) -------
#
# **Ésta es la clase de test que faltaba**, y por eso la banda de amplitud
# estuvo sin dibujarse sin que nadie lo notara. Los tests de `tools/` afirman
# que la herramienta publica su `BandOverlay`, y los de `signal_view` que un
# `BandOverlay` se dibuja; ninguno afirmaba que lo primero llegue a lo segundo,
# que es justo donde estaba el hueco. Es el mismo error de método que el hito 9
# dejó anotado: verificar la pieza en vez del camino.


def test_tildar_la_banda_la_dibuja(ventana: MainWindow):
    """El síntoma que reportó el usuario: tildarla no hacía nada.

    `_active_viewer_tool` contestaba dos preguntas con un valor —quién se queda
    con el mouse, y quién tiene algo que dibujar— y sólo se asignaba en la rama
    exclusiva. La banda declara `exclusive = False` con razón, así que su
    `overlays()` no lo llamaba nadie.
    """
    ventana.tool_controller.toggle("amplitude_band", True)

    assert any(isinstance(o, BandOverlay) for o in ventana.tool_controller.drawn_overlays)
    assert ventana.signal_view.overlay_layer.items


def test_destildar_la_banda_la_saca(ventana: MainWindow):
    """La otra mitad, que es la que hace afirmable a la primera."""
    ventana.tool_controller.toggle("amplitude_band", True)
    ventana.tool_controller.toggle("amplitude_band", False)

    assert not any(isinstance(o, BandOverlay) for o in ventana.tool_controller.drawn_overlays)


def test_la_banda_va_sobre_el_canal_seleccionado(ventana: MainWindow):
    """Mide contra un canal y por eso dice cuál: con ganancias distintas, 75 µV
    no ocupan lo mismo en dos carriles."""
    segundo = ventana.session.visible_channels[1]
    ventana.session.set_selected_channels([segundo])
    ventana.tool_controller.toggle("amplitude_band", True)

    bandas = [o for o in ventana.tool_controller.drawn_overlays if isinstance(o, BandOverlay)]
    assert [b.channel_name for b in bandas] == [segundo]


def test_seleccionar_otro_canal_redibuja_la_banda(ventana: MainWindow):
    """Hito 79: la banda se apoya sobre el seleccionado, y cambiar la selección
    no la redibujaba: quedaba en el carril viejo hasta el próximo evento."""
    segundo = ventana.session.visible_channels[1]
    ventana.tool_controller.toggle("amplitude_band", True)

    ventana._set_selected_channels([segundo])

    (banda,) = [o for o in ventana.tool_controller.drawn_overlays if isinstance(o, BandOverlay)]
    assert banda.channel_name == segundo


@pytest.mark.parametrize("modo", [None, "magnifier"])
def test_la_banda_sigue_al_mouse_sobre_el_canal_de_abajo(ventana: MainWindow, modo: str | None):
    """Hito 79: **la banda no se podía mover.** No es exclusiva, así que nunca
    se quedaba con el mouse, y el filtro de eventos sólo se lo daba a la que sí:
    el centro quedaba en 0 µV del primer canal, por más que el mouse pasara por
    encima de la señal, que es lo que pide el pliego. Con la lupa encendida,
    igual: el movimiento es de las dos."""
    segundo = ventana.session.visible_channels[1]
    ventana.tool_controller.toggle("amplitude_band", True)
    if modo is not None:
        ventana.tool_controller.toggle(modo, True)

    QApplication.instance().sendEvent(
        ventana.signal_view.viewport(),
        evento_de_mouse(ventana, QEvent.Type.MouseMove, 300.0, canal=segundo, uv=30.0),
    )

    (banda,) = [o for o in ventana.tool_controller.drawn_overlays if isinstance(o, BandOverlay)]
    assert banda.channel_name == segundo
    assert banda.y_center_uv == pytest.approx(30.0, abs=3.0)


def test_la_banda_no_se_tilda_sola_al_abrir(ventana: MainWindow):
    """**Arrancaba tildada y sin dibujar nada**, porque `activate_panel_tools()`
    usaba `not exclusive` como si dijera «es un panel». Por eso destildarla y
    volver a tildarla no cambiaba nada: ya estaba encendida."""
    assert not ventana.tool_controller.actions["amplitude_band"].isChecked()


def test_los_paneles_si_se_encienden_solos(ventana: MainWindow):
    """La otra mitad: un panel permanente apagado es un hueco en la pantalla
    esperando que alguien adivine que hay que apretar un botón.

    Se afirma sobre lo que producen y no sobre su entrada de menú: los que
    tienen dock no llevan acción propia —la suya es la del panel— y por eso
    `tool_controller.actions` no los tiene.
    """
    assert ventana.tool_controller.tools["overview"].windows()
    assert ventana.tool_controller.tools["histogram"].bars()


def test_la_banda_y_un_modo_del_mouse_conviven(ventana: MainWindow):
    """No son excluyentes entre sí: la banda no compite por el clic."""
    ventana.tool_controller.toggle("amplitude_band", True)
    ventana.tool_controller.toggle("magnifier", True)

    assert any(isinstance(o, BandOverlay) for o in ventana.tool_controller.drawn_overlays)
    assert ventana.tool_controller.mouse_tool is ventana.tool_controller.tools["magnifier"]


# -- La `y` se mide contra el canal bajo el cursor (hito 45) ------------------


def test_el_mouse_sobre_un_carril_da_la_uv_de_ese_canal(ventana: MainWindow):
    """**El centro de un carril es cero microvoltios, sea cual sea el carril.**

    Hasta el hito 45 la ventana medía todo contra el primer canal visible: con
    tres canales, el centro del tercero llegaba como −444 µV. Un número
    plausible y equivocado, que es la peor clase.
    """
    tercero = ventana.session.visible_channels[2]
    ventana.tool_controller.toggle("magnifier", True)
    lupa = ventana.tool_controller.tools["magnifier"]
    QApplication.instance().sendEvent(
        ventana.signal_view.viewport(),
        evento_de_mouse(ventana, QEvent.Type.MouseMove, 300.0, canal=tercero),
    )

    assert lupa.overlays()[0].y_uv == pytest.approx(0.0, abs=1.0)


def test_la_lupa_amplia_el_canal_de_abajo_del_cursor(ventana: MainWindow):
    """El otro síntoma que reportó el usuario: ampliaba siempre el primero.

    `_dibujar_lupa()` tenía `canal = self._visible[0]` escrito a mano, y
    `CircleOverlay` no tenía campo de canal, así que no había por dónde pasar
    la respuesta.
    """
    segundo = ventana.session.visible_channels[1]
    ventana.tool_controller.toggle("magnifier", True)
    QApplication.instance().sendEvent(
        ventana.signal_view.viewport(),
        evento_de_mouse(ventana, QEvent.Type.MouseMove, 300.0, canal=segundo),
    )

    assert ventana.tool_controller.tools["magnifier"].overlays()[0].channel_name == segundo


def test_la_lupa_dibuja_una_lente_y_no_una_linea_suelta(ventana: MainWindow):
    """Del hito 9 al 45 fue una polilínea estirada sin ningún círculo, pese a
    que el tipo se llama `CircleOverlay`."""
    ventana.tool_controller.toggle("magnifier", True)
    QApplication.instance().sendEvent(
        ventana.signal_view.viewport(),
        evento_de_mouse(
            ventana, QEvent.Type.MouseMove, 300.0,
            canal=ventana.session.visible_channels[0],
        ),
    )

    lente = ventana.signal_view.overlay_layer.items[-1]
    tipos = [type(h).__name__ for h in lente.childItems()]
    assert "QGraphicsPathItem" in tipos, "la lente no tiene cristal"
    assert "TextItem" in tipos, "la lente no dice la hora"


# -- Un color de clase editado a mano, de punta a punta (hito 48) ------------


def test_un_color_escrito_a_mano_en_las_preferencias_se_dibuja(
    ventana: MainWindow, tmp_path
):
    """**El bug que encontró validar `add_label(color=...)`.**

    Un archivo de preferencias con `"red"` pasaba la validación, que le
    preguntaba a pyqtgraph y `red` es un color para él. La sesión lo guardaba
    tal cual, y dibujar una anotación de esa clase elevaba un `ValueError`
    crudo: el visualizador pinta la banda con `color + "55"`, y `red55` no es
    un color. Ahora el archivo se normaliza al leerse y la clase llega como
    `#ff0000`.

    Por el camino entero y no por la pieza, que es lo que el hito 9 dejó
    anotado: leer el archivo, aplicarlo a la ventana, anotar y dibujar.
    """
    archivo = tmp_path / "preferencias.json"
    archivo.write_text(
        json.dumps({"version": 1, "annotation_colors": {"Huso": "red"}}),
        encoding="utf-8",
    )
    ventana.apply_preferences(preferencias_mod.load(archivo))

    assert ventana.session.annotations.color_of("Huso") == "#ff0000"

    ventana.session.annotations.add(Annotation("Huso", 0, 100))
    ventana._repintar_anotaciones()

    assert not ventana.carteles


# -- Corregir una anotación (hito 52) ----------------------------------------


def _x_de(ventana: MainWindow, segundos: float) -> float:
    """El `x` de escena de un segundo del registro, para `arrastrar()`."""
    vista = ventana.signal_view.getPlotItem().vb
    return vista.mapViewToScene(QPointF(segundos, 0.0)).x()


def test_el_menu_ofrece_cambiar_la_clase_y_borrar(ventana: MainWindow, elige_en_el_menu):
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)

    clic_derecho(ventana, 11.0)

    assert elige_en_el_menu.menus == [["Cambiar clase…", "Borrar"]]


def test_un_clic_derecho_donde_no_hay_nada_no_abre_el_menu(
    ventana: MainWindow, elige_en_el_menu
):
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)

    clic_derecho(ventana, 20.0)

    assert elige_en_el_menu.menus == []


def test_se_le_puede_cambiar_la_clase(ventana: MainWindow, elige_en_el_menu, elige_clase):
    """**Hasta el hito 52 había que borrarla y rehacer el gesto**, que es
    volver a encontrar el tramo exacto. El tramo no se toca."""
    anotar_en(ventana, 10.0, 12.0, "Spindle")
    antes = ventana.session.annotations.all()[0]
    ventana.tool_controller.toggle("annotator", True)
    elige_en_el_menu.elegir("Cambiar clase…")
    elige_clase("Arousal")

    clic_derecho(ventana, 11.0)

    (despues,) = ventana.session.annotations.all()
    assert despues.label == "Arousal"
    assert (despues.onset_sample, despues.duration_samples) == (
        antes.onset_sample,
        antes.duration_samples,
    )
    assert not ventana.carteles


def test_la_clase_nueva_puede_ser_una_que_no_existia(
    ventana: MainWindow, elige_en_el_menu, elige_clase
):
    """Como al anotar: el diálogo es editable y lo escrito se registra."""
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)
    elige_en_el_menu.elegir("Cambiar clase…")
    elige_clase("Espiga temporal")

    clic_derecho(ventana, 11.0)

    assert "Espiga temporal" in ventana.session.annotations.labels()
    assert ventana.session.annotations.all()[0].label == "Espiga temporal"


def test_cerrar_el_menu_no_cambia_nada(ventana: MainWindow, elige_en_el_menu):
    anotar_en(ventana, 10.0, 12.0, "Spindle")
    ventana.tool_controller.toggle("annotator", True)
    elige_en_el_menu.elegir(None)

    clic_derecho(ventana, 11.0)

    assert [a.label for a in ventana.session.annotations.all()] == ["Spindle"]


def test_arrastrar_el_final_de_una_banda_lo_corrige(ventana: MainWindow, elige_clase):
    """**Con eventos de Qt de verdad**: se aprieta sobre el borde, se suelta más
    allá, y el final queda donde se soltó. Es la otra corrección común: marcar
    el tramo un poco corrido."""
    anotar_en(ventana, 10.0, 12.0)
    fs = ventana.session.recording.sampling_rate
    ventana.tool_controller.toggle("annotator", True)
    elige_clase("", False)

    arrastrar(ventana, _x_de(ventana, 12.0), _x_de(ventana, 14.0))

    (corregida,) = ventana.session.annotations.all()
    assert corregida.onset_sample == int(10.0 * fs)
    assert corregida.end_sample == pytest.approx(14.0 * fs, abs=fs * 0.05)


def test_arrastrar_el_comienzo_de_una_banda_lo_corrige(ventana: MainWindow, elige_clase):
    anotar_en(ventana, 10.0, 12.0)
    fs = ventana.session.recording.sampling_rate
    ventana.tool_controller.toggle("annotator", True)
    elige_clase("", False)

    arrastrar(ventana, _x_de(ventana, 10.0), _x_de(ventana, 8.0))

    (corregida,) = ventana.session.annotations.all()
    assert corregida.onset_sample == pytest.approx(8.0 * fs, abs=fs * 0.05)
    assert corregida.end_sample == int(12.0 * fs)


def test_arrastrar_lejos_de_un_borde_sigue_anotando(ventana: MainWindow, elige_clase):
    """Lejos de un borde el arrastre es el de siempre: una anotación nueva."""
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)
    elige_clase("Arousal")

    arrastrar(ventana, _x_de(ventana, 20.0), _x_de(ventana, 22.0))

    assert len(ventana.session.annotations.all()) == 2


def test_sobre_un_borde_el_cursor_lo_dice(ventana: MainWindow):
    """El ↔ es lo único en la pantalla que avisa que el borde se agarra."""
    anotar_en(ventana, 10.0, 12.0)
    ventana.tool_controller.toggle("annotator", True)
    viewport = ventana.signal_view.viewport()

    for x, forma in (
        (_x_de(ventana, 12.0), Qt.CursorShape.SizeHorCursor),
        (_x_de(ventana, 11.0), Qt.CursorShape.ArrowCursor),
    ):
        evento = evento_de_mouse(
            ventana, QEvent.Type.MouseMove, x, Qt.MouseButton.NoButton
        )
        QApplication.instance().sendEvent(viewport, evento)
        assert viewport.cursor().shape() == forma


# -- Las marcas del registro, a pedido (hito 73) ------------------------------


@pytest.fixture
def ventana_con_marcas(ventana: MainWindow, tmp_path, monkeypatch) -> MainWindow:
    """La ventana con un registro que trae tres marcas, como un `.vmrk`: dos
    estímulos iguales y una respuesta."""
    from psglab.core.recording import Channel, ChannelKind, Recording
    from psglab.readers.base import MARKS_KEY

    fs = 100.0
    registro = Recording(
        file_path=tmp_path / "con_marcas.vhdr",
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, int(fs * WINDOW_SECONDS * 2))),
        sampling_rate=fs,
        metadata={
            MARKS_KEY: [
                (1.0, 0.0, "Stimulus/S  1"),
                (2.0, 0.0, "Stimulus/S  1"),
                (3.0, 0.5, "Response/R  1"),
            ]
        },
    )
    monkeypatch.setattr(files_mod, "read_recording", lambda _ruta: registro)
    ventana.open_recording(tmp_path / "con_marcas.vhdr")
    return ventana


def test_importar_las_marcas_las_agrega_como_anotaciones(ventana_con_marcas, confirmacion):
    """**Los lectores las guardaban y nada las leía**, aunque el docstring del
    de BrainVision prometía convertirlas «si el usuario lo pide»."""
    ventana = ventana_con_marcas

    ventana.import_file_marks()

    (pregunta,) = confirmacion["preguntas"]
    assert "¿Agregar 3 marcas" in pregunta["pregunta"]
    assert pregunta["informativo"] == "Stimulus/S  1 (2), Response/R  1 (1)"
    anotaciones = ventana.session.annotations.all()
    assert [(a.label, a.onset_sample, a.duration_samples) for a in anotaciones] == [
        ("Stimulus/S  1", 100, 1),
        ("Stimulus/S  1", 200, 1),
        ("Response/R  1", 300, 50),
    ]
    assert ventana.session.has_unexported_annotations()
    assert not ventana.carteles


def test_importar_dos_veces_no_las_duplica(ventana_con_marcas, confirmacion):
    ventana = ventana_con_marcas
    ventana.import_file_marks()

    ventana.import_file_marks()

    assert len(ventana.session.annotations.all()) == 3
    assert len(confirmacion["preguntas"]) == 1
    assert "no trae marcas que no estén ya anotadas" in ventana.statusBar().currentMessage()


def test_si_no_se_confirma_no_se_agrega_nada(ventana_con_marcas, confirmacion):
    """Un registro puede traer cientos de marcas de estímulo: se pregunta."""
    ventana = ventana_con_marcas
    confirmacion["respuesta"] = False

    ventana.import_file_marks()

    assert ventana.session.annotations.all() == []


def test_un_registro_sin_marcas_lo_dice_sin_preguntar(ventana: MainWindow, confirmacion):
    ventana.import_file_marks()

    assert confirmacion["preguntas"] == []
    assert "no trae marcas" in ventana.statusBar().currentMessage()


def test_las_marcas_de_un_brainvision_de_verdad_llegan_a_la_ventana(
    ventana: MainWindow, tmp_path, confirmacion
):
    """**El camino entero, sin reemplazar nada** (hito 74): el lector de
    verdad las guarda y la ventana las importa. Los tests del hito 73
    armaban el registro a mano."""
    vhdr = escribir_brainvision(
        tmp_path / "con_marcas",
        segundos=WINDOW_SECONDS,
        eventos=[("Stimulus", "S  1", 1001), ("Stimulus", "S  1", 2001)],
    )
    ventana.open_recording(vhdr)

    ventana.import_file_marks()

    assert [a.label for a in ventana.session.annotations.all()] == ["Stimulus/S  1"] * 2
    assert "Stimulus/S  1 (2)" in confirmacion["preguntas"][0]["informativo"]


# -- Anotar con una clase activa (hito 79) -------------------------------------------


def test_con_una_clase_activa_el_arrastre_no_pregunta(ventana: MainWindow, monkeypatch):
    """Marcar cien husos eran cien carteles."""
    preguntas: list[bool] = []
    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *_a, **_k: preguntas.append(True) or ("Otra", True)),
    )
    ventana.set_annotation_class("Spindle")

    arrastrar_un_tramo(ventana, 0.25, 0.35)
    arrastrar_un_tramo(ventana, 0.60, 0.70)

    assert preguntas == []
    assert [a.label for a in ventana.session.annotations.all()] == ["Spindle", "Spindle"]


def test_con_mayusculas_al_soltar_pregunta_igual(ventana: MainWindow, elige_clase):
    """Para el evento suelto de otra clase, sin cambiar la activa."""
    ventana.set_annotation_class("Spindle")
    elige_clase("Arousal")

    arrastrar_un_tramo(ventana, mayusculas=True)

    assert [a.label for a in ventana.session.annotations.all()] == ["Arousal"]
    assert ventana.tool_controller.tools["annotator"].active_label == "Spindle"


def test_elegir_una_clase_enciende_anotar_y_lo_dice(ventana: MainWindow):
    ventana.set_annotation_class("Spindle")

    assert ventana.tool_controller.actions["annotator"].isChecked()
    assert "«Spindle»" in ventana.tool_readout.text()


def test_la_e_usa_la_clase_activa(ventana: MainWindow, monkeypatch):
    monkeypatch.setattr(
        QInputDialog, "getItem", staticmethod(lambda *_a, **_k: pytest.fail("preguntó"))
    )
    ventana.set_annotation_class("Arousal")

    ventana.annotate_current_window()

    assert [a.label for a in ventana.session.annotations.all()] == ["Arousal"]


def test_la_c_elige_entre_las_clases_del_registro(ventana: MainWindow, elige_en_el_menu):
    elige_en_el_menu.elegir("Spindle")

    ventana.choose_annotation_class()

    (opciones,) = elige_en_el_menu.menus
    assert opciones[0] == "Preguntar cada vez"
    assert opciones[-1] == "Nueva clase…"
    assert "Spindle" in opciones
    assert ventana.tool_controller.tools["annotator"].active_label == "Spindle"


def test_la_c_puede_volver_a_preguntar(ventana: MainWindow, elige_en_el_menu):
    ventana.set_annotation_class("Spindle")
    elige_en_el_menu.elegir("Preguntar cada vez")

    ventana.choose_annotation_class()

    assert ventana.tool_controller.tools["annotator"].active_label is None


def test_la_c_crea_una_clase_nueva(ventana: MainWindow, elige_en_el_menu, monkeypatch):
    """La clase se registra al anotar el primer tramo, como una escrita en el
    cartel."""
    elige_en_el_menu.elegir("Nueva clase…")
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *_a, **_k: ("  Apnea  ", True))
    )

    ventana.choose_annotation_class()
    ventana.annotate_current_window()

    assert ventana.tool_controller.tools["annotator"].active_label == "Apnea"
    assert "Apnea" in ventana.session.annotations.labels()
    assert [a.label for a in ventana.session.annotations.all()] == ["Apnea"]


# -- El menú emergente, sin reemplazarlo (hito 81) -----------------------------


@pytest.mark.parametrize("elegida, esperado", [("Borrar", "Borrar"), (None, None)])
def test_el_menu_emergente_devuelve_el_texto_de_lo_elegido(
    ventana: MainWindow, monkeypatch, elegida, esperado
):
    """Todos los tests del clic derecho reemplazan `_elegir_en_un_menu()`
    entero, porque el menú es modal. Éste reemplaza sólo el `exec()`: arma el
    menú de verdad y verifica que traiga las opciones y que devuelva lo elegido,
    o None si se cerró sin elegir.

    **Con una subclase en el módulo que lo usa**, y no con
    `monkeypatch.setattr(QMenu, "exec", ...)`: en PySide6 `QMenu.exec` es
    estático y de instancia a la vez, Shiboken ignora el reemplazo sobre la
    clase y el menú se abre de verdad, que es colgar la suite."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QMenu

    import psglab.ui.window_annotation as anotacion_mod

    ofrecidas: list[list[str]] = []

    class MenuDePrueba(QMenu):
        def exec(self, _donde):  # noqa: A003 - es el nombre del método de Qt
            ofrecidas.append([a.text() for a in self.actions()])
            return next((a for a in self.actions() if a.text() == elegida), None)

    monkeypatch.setattr(anotacion_mod, "QMenu", MenuDePrueba)

    eleccion = ventana._elegir_en_un_menu(["Cambiar la clase…", "Borrar"], QPoint(0, 0))

    assert eleccion == esperado
    assert ofrecidas == [["Cambiar la clase…", "Borrar"]]
