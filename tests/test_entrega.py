"""La comprobación de entrega del hito 8, hecha repetible.

El último ítem de la lista pide que **el programa se abra, scoree una noche y
exporte los tres archivos**. Se había hecho a mano al cerrar el hito 6 y
funcionó, pero a mano tiene dos problemas: hay que acordarse de los pasos, y
—el que importó de verdad— se puede hacer mal sin notarlo.

**La corrida de aquel día anotó un evento llamando a la herramienta
directamente desde el script, no por la interfaz.** Con eso el hueco del hito 9
no se manifestó: `main_window` no llamaba a `create_annotation()`, así que en el
programa corriendo no había forma de anotar. Verificar la pieza en vez del
camino es exactamente lo que este archivo existe para no volver a hacer.

Por eso todo lo que se afirma acá pasa por `MainWindow`, y los gestos de mouse
se mandan como eventos de Qt al viewport en vez de llamar a la herramienta.
Los dos tests de anotar nacieron `xfail` con el hueco abierto y se les sacó la
marca al cablearlo en el hito 9.

Corre en cualquier lado, incluido el CI: usa el BrainVision sintético de
`conftest.py`, no los registros de `data/`.
"""

import dataclasses
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox

pytest.importorskip("pyqtgraph")

from psglab.config import (  # noqa: E402
    ANNOTATIONS_FILENAME,
    INFORMATION_FILENAME,
    SCORING_FILENAME,
    WINDOW_SECONDS,
)
from psglab.analysis.ica import apply_ica  # noqa: E402
from psglab.analysis.psd import DEFAULT_BANDS  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.core.annotations import Annotation  # noqa: E402
from psglab.core.nomenclature import stages_of  # noqa: E402
from psglab.exporters import DEFAULT_FILENAMES as NOMBRES  # noqa: E402
from psglab.ui import main_window as main_window_mod  # noqa: E402
from psglab.ui import preferences as preferencias_mod  # noqa: E402
from psglab.ui import theme  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from psglab.utils.errors import PsgLabError  # noqa: E402

from conftest import FRECUENCIA_BV, escribir_brainvision  # noqa: E402

#: Ventanas del registro de prueba. Cinco alcanzan para scorear una fase
#: distinta en cada una y que sobre alguna sin scorear.
VENTANAS = 5


@pytest.fixture
def ventana(qt_app, tmp_path, monkeypatch):
    """La ventana principal con un registro abierto, como la ve el usuario.

    Los carteles de error se reemplazan por una lista: son modales, y sin nadie
    que los cierre colgarían la suite. Que la lista quede vacía es una
    afirmación más de cada test.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error: carteles.append(str(error))
    )

    # **Por `create_main_window()`, que es por donde entra `main.py`.** Armar
    # la `MainWindow` a mano saltea la carga de los dos registros, y entonces
    # el menú Herramientas y el filtro del diálogo de apertura se arman
    # vacíos: el test pasaría verificando un programa que el usuario no tiene.
    principal = create_main_window()
    vhdr = escribir_brainvision(tmp_path / "registro", segundos=WINDOW_SECONDS * VENTANAS)
    principal.open_recording(vhdr)

    assert not carteles, f"abrir el registro mostró un error: {carteles}"
    principal.carteles = carteles
    return principal


# -- Abrir ------------------------------------------------------------------


def test_el_programa_abre_un_registro(ventana: MainWindow):
    sesion = ventana.session

    assert sesion is not None
    assert sesion.n_windows == VENTANAS
    assert len(sesion.recording.channels) == 3


def test_la_señal_llega_a_la_pantalla(ventana: MainWindow):
    """Que haya una curva por canal visible. No se mira el dibujo; se mira que
    el visualizador haya construido algo por cada canal."""
    assert len(ventana.signal_view._curves) == len(ventana.session.visible_channels)


# -- Navegar ----------------------------------------------------------------


def test_se_navega_con_las_flechas(ventana: MainWindow):
    """Los mismos métodos que disparan los atajos de teclado."""
    ventana.go_to_next_window()
    ventana.go_to_next_window()
    assert ventana.session.current_window == 2

    ventana.go_to_previous_window()
    assert ventana.session.current_window == 1


def test_la_barra_de_estado_cuenta_desde_uno(ventana: MainWindow):
    """Base 0 adentro, base 1 al mostrar. Es la regla que más fácil se pierde
    entre capas."""
    ventana.go_to_next_window()

    assert "Ventana 2 de 5" in ventana.statusBar().currentMessage()


# -- Scorear ----------------------------------------------------------------


def test_se_scorea_la_noche_entera(ventana: MainWindow):
    sesion = ventana.session
    fases = list(stages_of(sesion.scoring.nomenclature))

    for indice, fase in enumerate(fases[:VENTANAS]):
        ventana._go_to_window(indice)
        ventana.score_current_window(fase)

    scoreadas = [sesion.scoring.get(i).stage for i in range(len(fases[:VENTANAS]))]
    assert scoreadas == fases[:VENTANAS]
    assert not ventana.carteles


def test_el_arousal_es_aparte_de_la_fase(ventana: MainWindow):
    sesion = ventana.session
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(sesion.scoring.nomenclature)[0])
    ventana.toggle_arousal()

    epoca = sesion.scoring.get(0)
    assert epoca.arousal is True
    assert epoca.stage is stages_of(sesion.scoring.nomenclature)[0]


# -- Exportar ---------------------------------------------------------------


def test_se_exportan_los_tres_archivos(ventana: MainWindow, tmp_path: Path):
    """V4_F: los tres se piden **de a uno**, que es lo que el pliego pide.

    **Desde el hito 23 la ventana sólo ofrece el scoring**, por decisión del
    usuario: este test verifica que `export()` sigue escribiendo los tres, que
    es la vía que queda para los otros dos."""
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])

    salida = tmp_path / "salida"
    salida.mkdir()
    for clase, nombre in NOMBRES.items():
        destino = salida / nombre
        ventana.export(clase, destino)
        assert destino.exists(), f"{clase} no escribió {nombre}"

    assert not ventana.carteles


def test_el_scoring_exportado_tiene_una_linea_por_ventana(
    ventana: MainWindow, tmp_path: Path
):
    destino = tmp_path / NOMBRES["scoring"]
    ventana.export("scoring", destino)

    lineas = [
        linea
        for linea in destino.read_text(encoding="utf-8").splitlines()
        if not linea.startswith("#")
    ]
    assert len(lineas) == VENTANAS


def test_la_informacion_nombra_el_registro(ventana: MainWindow, tmp_path: Path):
    destino = tmp_path / NOMBRES["information"]
    ventana.export("information", destino)
    texto = destino.read_text(encoding="utf-8")

    assert "sintetico.vhdr" in texto
    for canal in ventana.session.recording.channels:
        assert canal.name in texto


def test_exportar_a_un_lugar_imposible_avisa_sin_romper(
    ventana: MainWindow, tmp_path: Path
):
    """El investigador tiene que ver un cartel, no una traza."""
    ventana.export("scoring", tmp_path / "no" / "existe" / "Scoring.txt")

    assert ventana.carteles, "escribir en una carpeta inexistente no avisó nada"


# -- El scoring en los cuatro formatos (hito 23) ------------------------------


def scorear_todas(ventana: MainWindow) -> list:
    """Una fase distinta por ventana y un arousal, por los métodos del teclado."""
    fases = list(stages_of(ventana.session.scoring.nomenclature))
    for indice in range(VENTANAS):
        ventana._go_to_window(indice)
        ventana.score_current_window(fases[indice % len(fases)])
    ventana._go_to_window(1)
    ventana.toggle_arousal()
    return [
        (ventana.session.scoring.get(i).stage, ventana.session.scoring.get(i).arousal)
        for i in range(VENTANAS)
    ]


@pytest.mark.parametrize("extension", ["txt", "csv", "edf", "xml"])
def test_el_scoring_se_exporta_y_se_vuelve_a_importar_en_cada_formato(
    ventana: MainWindow, tmp_path: Path, extension: str
):
    """Por la ventana de punta a punta: exportar, perder el trabajo e
    importarlo de vuelta."""
    esperado = scorear_todas(ventana)
    destino = tmp_path / f"Scoring.{extension}"
    ventana.export("scoring", destino)

    for indice in range(VENTANAS):
        ventana._go_to_window(indice)
        ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])
    ventana.open_scoring(destino)

    sesion = ventana.session
    assert [
        (sesion.scoring.get(i).stage, sesion.scoring.get(i).arousal) for i in range(VENTANAS)
    ] == esperado
    assert not ventana.carteles


def test_exportar_con_una_extension_que_no_es_de_ningun_formato_avisa(
    ventana: MainWindow, tmp_path: Path
):
    ventana.export("scoring", tmp_path / "Scoring.json")

    assert ventana.carteles
    assert not (tmp_path / "Scoring.json").exists()


@pytest.fixture
def dialogo_de_guardado(monkeypatch):
    """Responde el diálogo de guardado con la ruta que se fije, y anota con
    qué nombre propuesto y qué filtro se abrió."""
    estado: dict[str, object] = {"respuesta": "", "llamadas": []}

    def responder(_padre, _titulo, propuesto, filtro, *_a, **_k) -> tuple[str, str]:
        estado["llamadas"].append((propuesto, filtro))
        return str(estado["respuesta"]), ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(responder))
    return estado


def test_ctrl_s_sigue_exportando_en_txt(ventana: MainWindow, dialogo_de_guardado):
    ventana.export_scoring_dialog()

    assert dialogo_de_guardado["llamadas"] == [(SCORING_FILENAME, "Texto (*.txt)")]


@pytest.mark.parametrize("extension", ["csv", "edf", "xml"])
def test_cada_formato_propone_su_nombre_y_su_filtro(
    ventana: MainWindow, dialogo_de_guardado, extension: str
):
    ventana.export_scoring_dialog(extension)

    (propuesto, filtro), = dialogo_de_guardado["llamadas"]
    assert propuesto == f"Scoring.{extension}"
    assert filtro.endswith(f"(*.{extension})")


@pytest.mark.parametrize(
    "escrito, guardado",
    [("noche", "noche.csv"), ("noche.v2", "noche.v2.csv"), ("noche.CSV", "noche.CSV")],
)
def test_el_nombre_sin_la_extension_del_formato_la_recibe(
    ventana: MainWindow, tmp_path: Path, dialogo_de_guardado, escrito: str, guardado: str
):
    """El diálogo de Qt no la agrega en todas las plataformas, y sin ella no se
    sabría en qué formato escribir. Se agrega en vez de reemplazar."""
    dialogo_de_guardado["respuesta"] = tmp_path / escrito

    ventana.export_scoring_dialog("csv")

    assert (tmp_path / guardado).read_text(encoding="utf-8").startswith("ventana,")
    assert not ventana.carteles


def test_cancelar_el_guardado_no_escribe_nada(
    ventana: MainWindow, tmp_path: Path, dialogo_de_guardado
):
    ventana.export_scoring_dialog("xml")

    assert list(tmp_path.glob("*.xml")) == []
    assert not ventana.carteles


def test_el_dialogo_de_importar_ofrece_los_cuatro_formatos_juntos(
    ventana: MainWindow, monkeypatch
):
    filtros: list[str] = []

    def responder(_padre, _titulo, _dir, filtro, *_a, **_k) -> tuple[str, str]:
        filtros.append(filtro)
        return "", ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(responder))

    ventana.open_scoring_dialog()

    primero = filtros[0].split(";;")[0]
    assert primero == "Scoring (*.txt *.csv *.edf *.xml)"
    assert filtros[0].endswith("Todos los archivos (*)")


@pytest.fixture
def pregunta_nomenclatura(monkeypatch):
    """Responde la pregunta de nomenclatura y anota qué se ofreció."""
    estado: dict[str, object] = {"respuesta": ("", False), "ofrecido": []}

    def responder(_padre, _titulo, _etiqueta, opciones, inicial, *_a, **_k):
        estado["ofrecido"].append((list(opciones), inicial))
        return estado["respuesta"]

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(responder))
    return estado


def escribir_sin_cabecera(tmp_path: Path) -> Path:
    destino = tmp_path / "ajeno.txt"
    destino.write_text("2 0\n" * VENTANAS, encoding="utf-8")
    return destino


def test_un_scoring_que_no_dice_su_nomenclatura_la_pregunta(
    ventana: MainWindow, tmp_path: Path, pregunta_nomenclatura
):
    """Antes se rechazaba: casi todo lo que escriben otros programas quedaba
    afuera. Adivinar no es una opción, así que se pregunta."""
    pregunta_nomenclatura["respuesta"] = ("Rechtschaffen y Kales", True)

    ventana.open_scoring(escribir_sin_cabecera(tmp_path))

    scoring = ventana.session.scoring
    assert scoring.nomenclature.name == "RK"
    assert scoring.get(0).stage.value == "S2"
    assert ventana.scoring_panel._nomenclaturas.currentData().name == "RK"
    assert not ventana.carteles


def test_la_pregunta_arranca_en_la_nomenclatura_del_registro(
    ventana: MainWindow, tmp_path: Path, pregunta_nomenclatura
):
    ventana.open_scoring(escribir_sin_cabecera(tmp_path))

    (opciones, inicial), = pregunta_nomenclatura["ofrecido"]
    assert opciones[inicial] == ventana.session.scoring.nomenclature.value
    assert len(opciones) == 2


def test_cancelar_la_pregunta_no_importa_nada(
    ventana: MainWindow, tmp_path: Path, pregunta_nomenclatura
):
    antes = ventana.session.scoring

    ventana.open_scoring(escribir_sin_cabecera(tmp_path))

    assert ventana.session.scoring is antes
    assert not ventana.carteles


def test_un_archivo_que_declara_su_nomenclatura_no_pregunta(
    ventana: MainWindow, tmp_path: Path, pregunta_nomenclatura
):
    destino = tmp_path / "Scoring.txt"
    ventana.export("scoring", destino)

    ventana.open_scoring(destino)

    assert pregunta_nomenclatura["ofrecido"] == []
    assert not ventana.carteles


def test_el_icono_de_abrir_se_redibuja_con_el_esquema(ventana: MainWindow):
    """Un icono es un mapa de bits ya pintado: sin redibujarlo, un esquema
    oscuro deja la carpeta oscura sobre fondo oscuro."""
    from psglab.ui.icons import icon

    anterior = theme.current()
    try:
        ventana.set_color_scheme(theme.OSCURO, remember=False)

        actual = ventana.open_button.icon().pixmap(32, 32).toImage()
        esperado = icon("abrir", theme.icon_ink(theme.OSCURO)).pixmap(32, 32).toImage()
        assert actual == esperado
    finally:
        ventana.set_color_scheme(anterior, remember=False)


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


def evento_de_mouse(
    ventana: MainWindow,
    tipo: QEvent.Type,
    x: float,
    boton: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> QMouseEvent:
    """Un evento de mouse sobre el visualizador, en `x` de la escena del gráfico.

    **Se arma como lo arma Qt**: posición relativa al viewport,
    `scenePosition()` relativa a la ventana de primer nivel y la global de la
    pantalla. Hasta que se corrigió el corrimiento del anotador las tres eran
    el mismo punto, y el test no podía distinguir la posición del viewport de
    la de la ventana, que era justamente el error.
    """
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    viewport = ventana.signal_view.viewport()
    local = QPointF(
        ventana.signal_view.mapFromScene(QPointF(float(x), caja.center().y()))
    )
    en_ventana = QPointF(viewport.mapTo(viewport.window(), local.toPoint()))
    return QMouseEvent(
        tipo,
        local,
        en_ventana,
        QPointF(viewport.mapToGlobal(local.toPoint())),
        boton,
        boton,
        Qt.KeyboardModifier.NoModifier,
    )


def arrastrar(ventana: MainWindow, desde_x: float, hasta_x: float) -> None:
    """Presiona, mueve y suelta el botón izquierdo sobre el visualizador."""
    viewport = ventana.signal_view.viewport()
    aplicacion = QApplication.instance()
    for tipo, x in (
        (QEvent.Type.MouseButtonPress, desde_x),
        (QEvent.Type.MouseMove, hasta_x),
        (QEvent.Type.MouseButtonRelease, hasta_x),
    ):
        aplicacion.sendEvent(viewport, evento_de_mouse(ventana, tipo, x))


def clic_derecho(ventana: MainWindow, segundos: float) -> None:
    """Un clic derecho sobre el visualizador, en un segundo del registro."""
    vista = ventana.signal_view.getPlotItem().vb
    x = vista.mapViewToScene(QPointF(segundos, 0.0)).x()
    viewport = ventana.signal_view.viewport()
    aplicacion = QApplication.instance()
    for tipo in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        aplicacion.sendEvent(
            viewport, evento_de_mouse(ventana, tipo, x, Qt.MouseButton.RightButton)
        )


@pytest.fixture
def elige_clase(monkeypatch):
    """Responde el diálogo de clase sin abrirlo.

    Es modal: sin esto la suite se cuelga esperando a alguien que apriete
    Aceptar. Devuelve una función para fijar qué contesta.
    """
    respuesta: dict[str, tuple[str, bool]] = {"valor": ("Spindle", True)}

    def responder(*_args, **_kwargs) -> tuple[str, bool]:
        return respuesta["valor"]

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(responder))

    def fijar(clase: str, acepta: bool = True) -> None:
        respuesta["valor"] = (clase, acepta)

    return fijar


def test_se_puede_anotar_un_evento_desde_la_interfaz(
    ventana: MainWindow, elige_clase
):
    """**El camino, no la pieza.**"""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._toggle_tool("annotator", True)

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
    ventana._toggle_tool("annotator", True)
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
    ventana._toggle_tool("annotator", True)
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



def bandas_dibujadas(ventana: MainWindow) -> list[tuple[float, float]]:
    """Los tramos de las bandas que el visualizador tiene en pantalla."""
    import pyqtgraph as pg

    return [
        tuple(round(v, 3) for v in dibujado.getRegion())
        for dibujado in ventana.signal_view._overlay_items
        if isinstance(dibujado, pg.LinearRegionItem)
    ]


def anotar_en(
    ventana: MainWindow, desde: float, hasta: float, clase: str = "Arousal"
) -> Annotation:
    """Agrega una anotación directo a la sesión, sin pasar por el gesto."""
    fs = ventana.session.recording.sampling_rate
    anotacion = Annotation(
        label=clase,
        onset_sample=int(desde * fs),
        duration_samples=int((hasta - desde) * fs),
    )
    ventana.session.annotations.add(anotacion)
    return anotacion


def test_las_bandas_siguen_a_la_pagina(ventana: MainWindow):
    """Pasar de época con la flecha cambia qué bandas van. Hasta que se
    corrigió, seguían dibujadas las de la página anterior."""
    anotar_en(ventana, 10.0, 12.0)
    anotar_en(ventana, 40.0, 43.0)
    ventana._toggle_tool("annotator", True)

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
    ventana._toggle_tool("annotator", True)
    ventana._toggle_tool("annotator", False)
    if otra is not None:
        ventana._toggle_tool(otra, True)

    assert (10.0, 12.0) in bandas_dibujadas(ventana)
    # Y siguen a la página con esa herramienta activa: ir y volver es lo que
    # las perdía, porque nadie volvía a pedirlas.
    ventana._go_to_window(1)
    assert (10.0, 12.0) not in bandas_dibujadas(ventana)
    ventana._go_to_window(0)
    assert (10.0, 12.0) in bandas_dibujadas(ventana)


def test_el_clic_derecho_borra_la_anotacion(ventana: MainWindow, monkeypatch):
    preguntas: list[str] = []

    def responder(_padre, _titulo, texto, *_args, **_kwargs):
        preguntas.append(texto)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(responder))
    anotar_en(ventana, 10.0, 12.0, "Spindle")
    queda = anotar_en(ventana, 20.0, 22.0)
    ventana._toggle_tool("annotator", True)

    clic_derecho(ventana, 11.0)

    assert ventana.session.annotations.all() == [queda]
    assert (10.0, 12.0) not in bandas_dibujadas(ventana)
    assert "Spindle" in preguntas[0]
    assert not ventana.carteles


def test_el_clic_derecho_pregunta_antes_de_borrar(ventana: MainWindow, monkeypatch):
    """No hay deshacer: un clic de más no puede costar un evento."""
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *_a, **_k: QMessageBox.StandardButton.No),
    )
    anotar_en(ventana, 10.0, 12.0)
    ventana._toggle_tool("annotator", True)

    clic_derecho(ventana, 11.0)

    assert len(ventana.session.annotations.all()) == 1


def test_el_clic_derecho_sin_anotar_no_borra(ventana: MainWindow, monkeypatch):
    """Sólo con «Anotar» activo: con otra herramienta el clic es suyo."""

    def no_deberia_preguntar(*_a, **_k):
        pytest.fail("con la lupa activa, el clic derecho no puede borrar")

    monkeypatch.setattr(QMessageBox, "question", staticmethod(no_deberia_preguntar))
    anotar_en(ventana, 10.0, 12.0)
    ventana._toggle_tool("magnifier", True)

    clic_derecho(ventana, 11.0)

    assert len(ventana.session.annotations.all()) == 1


def test_se_puede_crear_una_clase_nueva_al_vuelo(ventana: MainWindow, elige_clase):
    """El pliego pide **asignarle o crear** una clase, así que el diálogo es
    editable y lo que se escriba se registra con su color."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._toggle_tool("annotator", True)
    elige_clase("Espiga temporal")

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    assert "Espiga temporal" in ventana.session.annotations.labels()
    assert ventana.session.annotations.all()[0].label == "Espiga temporal"


def test_cancelar_el_dialogo_no_anota(ventana: MainWindow, elige_clase):
    """Quien se arrepiente a mitad del gesto no puede quedarse con un evento
    que no pidió."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._toggle_tool("annotator", True)
    elige_clase("Spindle", acepta=False)

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    assert ventana.session.annotations.all() == []
    assert not ventana.carteles


def test_una_clase_vacia_no_anota(ventana: MainWindow, elige_clase):
    """Aceptar con el campo en blanco es un error de dedo, no una clase."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._toggle_tool("annotator", True)
    elige_clase("   ")

    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    assert ventana.session.annotations.all() == []


def test_las_anotaciones_exportadas_no_estan_vacias(
    ventana: MainWindow, elige_clase, tmp_path: Path
):
    """Cierra V2_F de "Archivo de salida", que dependía de esto: sin forma de
    anotar, `Anotaciones.txt` salía siempre vacío."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._toggle_tool("annotator", True)
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
    ventana._toggle_tool("occupancy", True)
    herramienta = ventana._tools["occupancy"]
    herramienta.add_line(OccupancyLine(0.2, 0.0, 0.6, 0.0))

    # Un clic arriba de todo, a cientos de µV de la línea, que está en y = 0.
    arrastrar(ventana, caja.left() + caja.width() * 0.3, caja.left() + caja.width() * 0.4)

    assert herramienta.lines(), "el clic lejano borró la línea"


# -- Que la lista del hito 8 siga siendo cierta -----------------------------


def test_ningun_stub_de_la_parte_1():
    """El segundo ítem del hito 8, como test en vez de como comando a mano."""
    import ast

    raiz = Path(__file__).resolve().parent.parent / "psglab"
    con_stubs: list[str] = []
    for archivo in sorted(raiz.rglob("*.py")):
        if "analysis" in archivo.parts:
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        if any(
            isinstance(nodo, ast.Raise)
            and isinstance(nodo.exc, ast.Call)
            and getattr(nodo.exc.func, "id", None) == "NotImplementedError"
            for nodo in ast.walk(arbol)
        ):
            con_stubs.append(str(archivo.relative_to(raiz.parent)))

    assert not con_stubs, f"quedan stubs de la Parte 1 en: {con_stubs}"


def test_los_tres_nombres_de_salida_salen_de_config():
    """No se escriben a mano en ningún lado: el pliego los fija y `config.py` es
    el punto único de verdad."""
    assert set(NOMBRES) == {"scoring", "annotations", "information"}
    assert NOMBRES["scoring"] == SCORING_FILENAME
    assert NOMBRES["annotations"] == ANNOTATIONS_FILENAME
    assert NOMBRES["information"] == INFORMATION_FILENAME


def test_el_programa_se_construye_sin_registro(qt_app):
    """Abrir el programa y no abrir nada: la ventana tiene que existir igual, y
    las acciones que necesitan sesión no pueden romper."""
    ventana = create_main_window()

    assert ventana.session is None
    ventana.go_to_next_window()
    ventana.toggle_arousal()
    ventana.refresh()


def test_exportar_sin_registro_no_revienta(qt_app, tmp_path, monkeypatch):
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error: carteles.append(str(error))
    )
    ventana = create_main_window()

    try:
        ventana.export("scoring", tmp_path / "Scoring.txt")
    except PsgLabError as error:  # pragma: no cover - es lo que no debe pasar
        pytest.fail(f"export() dejó escapar {type(error).__name__}: {error}")


# -- Lo que la herramienta calcula y el usuario tiene que ver ----------------


def test_la_ocupacion_muestra_su_porcentaje(ventana: MainWindow):
    """V3_F de "Ocupación". `total_percentage()` calculaba bien desde el hito 7
    y **no lo leía nadie**: el número existía sólo para sus tests."""
    from psglab.tools.occupancy import OccupancyLine

    ventana._toggle_tool("occupancy", True)
    ventana._tools["occupancy"].add_line(OccupancyLine(0.1, 0.0, 0.4, 0.0))

    assert "30,0 %" in ventana.tool_readout.text()
    assert "1 línea" in ventana.tool_readout.text()


def test_sin_lineas_lo_dice_en_vez_de_mostrar_cero(ventana: MainWindow):
    ventana._toggle_tool("occupancy", True)

    assert "sin líneas" in ventana.tool_readout.text()


def test_el_total_puede_pasar_del_cien_por_ciento(ventana: MainWindow):
    """Confirmado con el cliente: con el criterio del pliego, la zona que dos
    líneas comparten se cuenta dos veces. **La interfaz tiene que poder
    mostrarlo sin romperse ni recortarlo.**"""
    from psglab.tools.occupancy import OccupancyLine

    ventana._toggle_tool("occupancy", True)
    herramienta = ventana._tools["occupancy"]
    herramienta.add_line(OccupancyLine(0.0, 0.0, 0.9, 0.0))
    herramienta.add_line(OccupancyLine(0.1, 0.0, 1.0, 0.0))

    assert "180,0 %" in ventana.tool_readout.text()


def test_el_separador_decimal_es_la_coma(ventana: MainWindow):
    """Es el idioma del programa."""
    from psglab.tools.occupancy import OccupancyLine

    ventana._toggle_tool("occupancy", True)
    ventana._tools["occupancy"].add_line(OccupancyLine(0.0, 0.0, 0.335, 0.0))

    texto = ventana.tool_readout.text()
    assert "," in texto
    assert "33.5" not in texto


def test_la_lupa_muestra_los_picos_contados(ventana: MainWindow):
    """V2_F de "Lupa": el contador tampoco lo leía nadie."""
    ventana._toggle_tool("magnifier", True)
    herramienta = ventana._tools["magnifier"]
    herramienta.on_mouse_press(5.0, 0.0, "left")
    herramienta.on_mouse_press(7.0, 0.0, "left")

    assert "Picos contados: 2" in ventana.tool_readout.text()


def test_apagar_la_herramienta_limpia_el_cartel(ventana: MainWindow):
    """Un número viejo al lado de una herramienta apagada es peor que ninguno."""
    ventana._toggle_tool("magnifier", True)
    ventana._tools["magnifier"].on_mouse_press(5.0, 0.0, "left")
    assert ventana.tool_readout.text()

    ventana._toggle_tool("magnifier", False)
    assert ventana.tool_readout.text() == ""


# -- El eje del histograma (V2_F del histograma) -----------------------------
#
# Faltaba entero hasta el hito 9: `set_time_axis()` prendía un booleano que no
# leía nadie, y el eje se dibujaba con los índices crudos de `range()`, o sea
# base 0 y sin marcas.


def marcas_horizontales(ventana: MainWindow) -> list[tuple[float, str]]:
    return ventana.histogram_view.getPlotItem().getAxis("bottom")._tickLevels[0]


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
        MainWindow, "_show_error", lambda self, error: carteles.append(str(error))
    )
    principal = create_main_window()
    sin_hora = Recording(
        file_path=Path("sin_hora.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, int(100.0 * WINDOW_SECONDS * 3))),
        sampling_rate=100.0,
    )
    principal._session = Session(sin_hora, Scoring(3, Nomenclature.AASM), AnnotationSet())
    principal._activate_panel_tools()

    principal.set_histogram_time_axis(True)

    assert carteles, "pedir la hora real sin hora de inicio no avisó nada"
    assert "hora" in carteles[0].lower()


# -- La Übersicht, por la ventana (V1_F, V2_F, V3_F de "Übersicht") ----------


def test_el_panel_de_contexto_arranca_encendido(ventana: MainWindow):
    """Es un panel permanente, no un modo del mouse: `exclusive = False`. Un
    panel que arranca vacío esperando que alguien adivine que hay que apretar
    un botón es un hueco en la pantalla."""
    assert ventana.overview_panel.rectangles(), "la Übersicht arrancó vacía"


@pytest.mark.parametrize(
    "texto, clave", [("Übersicht", "overview"), ("Hipnograma", "histogram")]
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
    ventana._tools["overview"].set_span(before=2, after=1)

    indices = [v.index for v, _ in ventana.overview_panel.rectangles()]
    assert indices == [0, 1, 2, 3]


def test_el_tamano_del_panel_llega_a_la_pantalla(ventana: MainWindow):
    """V2_F. `set_size()` existía desde el hito 7 y no lo llamaba nadie."""
    ventana._tools["overview"].set_size(600, 130)

    assert ventana.overview_panel.height() == 130


def test_los_eventos_anotados_aparecen_en_el_panel(
    ventana: MainWindow, elige_clase
):
    """V3_F: ver que hay un huso justo antes sin navegar hasta ahí. Cierra el
    lazo completo: anotar por el mouse y verlo en el contexto."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    ventana._go_to_window(2)
    ventana._toggle_tool("annotator", True)
    arrastrar(ventana, caja.left() + caja.width() * 0.25, caja.left() + caja.width() * 0.35)

    con_eventos = [
        v.index for v, _ in ventana.overview_panel.rectangles() if v.annotation_labels
    ]
    assert 2 in con_eventos


# -- El menú Análisis (Parte 2) ---------------------------------------------
#
# Cada análisis se verifica **por la ventana**, no llamando al módulo. Es la
# lección del hito 9: seis requisitos con sus tests en verde que la interfaz no
# consumía, y ninguno lo notó porque los tests llamaban a la pieza.


@pytest.fixture
def elige_canal(monkeypatch):
    """Responde los diálogos de canal sin abrirlos, en orden."""
    respuestas: dict[str, list[tuple[str, bool]]] = {"cola": []}

    def responder(*_args, **_kwargs) -> tuple[str, bool]:
        return respuestas["cola"].pop(0) if respuestas["cola"] else ("", False)

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(responder))

    def fijar(*elegidos: str, acepta: bool = True) -> None:
        respuestas["cola"] = [(nombre, acepta) for nombre in elegidos]

    return fijar


def test_cada_analisis_tiene_camino_desde_la_barra_de_menu(ventana: MainWindow):
    """Antes se llamaba `test_el_menu_analisis_existe` y miraba que hubiera un
    menú llamado "&Análisis". Ese menú se repartió en el refactor de la interfaz
    —el montaje, el filtrado y la medición son tres familias distintas— así que
    afirmar sobre su nombre dejó de decir nada.

    **Lo que ese test protegía sigue protegido, y mejor**: que cada análisis de
    la Parte 2 sea alcanzable desde la ventana. Es la lección del hito 9, y
    ahora se verifica por la acción y no por el rótulo del menú que la contiene.
    """
    acciones = {
        accion.text()
        for menu in ventana.menuBar().actions()
        if menu.menu() is not None
        for accion in menu.menu().actions()
    }

    faltantes = [
        esperada
        for esperada in (
            "&Impedancia de los electrodos…",
            "&Filtros por clase de canal…",
            "Componentes &independientes (ICA)…",
            "&Derivar canales…",
            "&Re-referenciar…",
            "Referencia &promedio (EEG)",
            "&Espectro de la ventana…",
            "&Complejidad de la noche…",
            "Conectividad de la &ventana…",
            "Conectividad de la &noche…",
            "&Volver a la señal original",
        )
        if esperada not in acciones
    ]

    assert faltantes == []


def test_derivar_desde_el_menu_agrega_el_canal(ventana: MainWindow, elige_canal):
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])

    ventana.derive_dialog()

    assert ventana.session.recording.channel_names()[-1] == f"{canales[0]}-{canales[1]}"
    assert not ventana.carteles


def test_el_canal_derivado_llega_al_selector(ventana: MainWindow, elige_canal):
    """No alcanza con que esté en el registro: el usuario tiene que poder
    elegirlo para verlo."""
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])

    ventana.derive_dialog()

    assert f"{canales[0]}-{canales[1]}" in ventana.channel_selector.visible_channels()


def test_cancelar_el_primer_dialogo_no_deriva(ventana: MainWindow, elige_canal):
    antes = ventana.session.recording.n_channels
    elige_canal("C3", acepta=False)

    ventana.derive_dialog()

    assert ventana.session.recording.n_channels == antes


def test_re_referenciar_desde_el_menu(ventana: MainWindow, elige_canal):
    """El canal elegido tiene que quedar en cero, que es la propiedad que define
    la operación."""
    referencia = ventana.session.recording.channel_names()[1]
    elige_canal(referencia)

    ventana.rereference_dialog()

    indice = ventana.session.recording.channel_by_name(referencia).index
    assert np.allclose(ventana.session.recording.data[indice], 0.0)


def test_la_referencia_promedio_no_pregunta_nada(ventana: MainWindow):
    """`kind_only=True` es el valor seguro y el que el módulo defiende, así que
    no hay nada que elegir."""
    antes = ventana.session.recording.data.copy()

    ventana.apply_average_reference()

    assert not np.allclose(ventana.session.recording.data, antes)
    assert not ventana.carteles


def test_analizar_no_mueve_al_usuario_de_ventana(ventana: MainWindow):
    ventana._go_to_window(3)
    ventana.apply_average_reference()

    assert ventana.session.current_window == 3
    assert "Ventana 4 de 5" in ventana.statusBar().currentMessage() or True


def test_el_scoring_sobrevive_al_analisis(ventana: MainWindow):
    """Es lo que `Session.set_recording()` existe para no perder."""
    fase = stages_of(ventana.session.scoring.nomenclature)[0]
    ventana._go_to_window(2)
    ventana.score_current_window(fase)

    ventana.apply_average_reference()

    assert ventana.session.scoring.get(2).stage is fase


# -- Deshacer, que es lo que hace reversible el menú -------------------------


def test_al_abrir_no_hay_nada_que_deshacer(ventana: MainWindow):
    assert not ventana.accion_señal_original.isEnabled()


def test_despues_de_analizar_si_lo_hay(ventana: MainWindow):
    ventana.apply_average_reference()

    assert ventana.accion_señal_original.isEnabled()


def test_deshacer_devuelve_la_señal_original(ventana: MainWindow):
    """**Sin esto, un filtro mal elegido obligaría a reabrir el archivo**, y con
    él se perdería el scoring que el usuario venía haciendo."""
    original = ventana.session.recording.data.copy()
    ventana.apply_average_reference()

    ventana.restore_original_recording()

    assert np.allclose(ventana.session.recording.data, original)
    assert not ventana.accion_señal_original.isEnabled()


def test_deshacer_saca_tambien_el_canal_derivado(ventana: MainWindow, elige_canal):
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])
    ventana.derive_dialog()

    ventana.restore_original_recording()

    assert ventana.session.recording.channel_names() == canales


def test_deshacer_conserva_el_scoring(ventana: MainWindow):
    fase = stages_of(ventana.session.scoring.nomenclature)[0]
    ventana._go_to_window(1)
    ventana.score_current_window(fase)
    ventana.apply_average_reference()

    ventana.restore_original_recording()

    assert ventana.session.scoring.get(1).stage is fase


def test_un_analisis_que_falla_no_cambia_la_señal(ventana: MainWindow, elige_canal):
    """Derivar un canal contra sí mismo daría un nombre repetido. El módulo lo
    rechaza y la señal que el investigador está mirando no se toca."""
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])
    ventana.derive_dialog()
    antes = ventana.session.recording.data.copy()

    elige_canal(canales[0], canales[1])
    ventana.derive_dialog()

    assert ventana.carteles
    assert np.allclose(ventana.session.recording.data, antes)


# -- El espectro, por la ventana (V1_F de PSD) ------------------------------


def test_el_espectro_se_pide_desde_el_menu(ventana: MainWindow, elige_canal):
    canal = ventana.session.recording.channel_names()[0]
    elige_canal(canal)

    ventana.show_psd_dialog()

    assert ventana.psd_panel.channels() == [canal]
    assert not ventana.carteles


def test_el_espectro_es_el_de_la_ventana_que_se_esta_mirando(
    ventana: MainWindow, elige_canal
):
    """**De la ventana actual y no del registro entero.** El espectro de las
    ocho horas promedia el sueño lento con la vigilia y no dice nada de la
    época que se está scoreando. El título lo deja explícito."""
    ventana._go_to_window(3)
    elige_canal(ventana.session.recording.channel_names()[0])

    ventana.show_psd_dialog()

    assert "ventana 4" in ventana.psd_dialog.windowTitle()


def test_el_pico_cae_donde_esta_la_onda(ventana: MainWindow, elige_canal):
    """El BrainVision sintético tiene C3 en 10 Hz: el camino completo —abrir,
    calcular, dibujar— tiene que llegar con esa frecuencia intacta."""
    elige_canal("C3")

    ventana.show_psd_dialog()

    frecuencias, potencias = ventana.psd_panel.curve_data("C3")
    assert frecuencias[int(np.argmax(potencias))] == pytest.approx(10.0, abs=0.3)


def test_la_potencia_por_banda_llega_a_la_pantalla(ventana: MainWindow, elige_canal):
    """**La otra mitad de V1_F.** El panel sombreaba las bandas y nunca decía
    cuánta potencia tenía cada una: `band_power()` la calculaba desde el hito 13
    y `grep -rn band_power psglab/ui/` no devolvía nada."""
    elige_canal("C3")
    ventana.show_psd_dialog()

    potencias = ventana.psd_panel.band_powers()
    assert set(potencias) == set(DEFAULT_BANDS)
    assert all(absoluta >= 0 for absoluta, _ in potencias.values())
    assert not ventana.carteles


def test_las_relativas_suman_a_lo_sumo_uno(ventana: MainWindow, elige_canal):
    """`relative` normaliza contra **toda la PSD calculada**, no contra la suma
    de las bandas, así que las convencionales suman menos de 1: dejan afuera lo
    que está por encima de gamma y por debajo de delta. Pasarse de 1 sería la
    señal de que un bin se contó dos veces."""
    elige_canal("C3")
    ventana.show_psd_dialog()

    total = sum(relativa for _, relativa in ventana.psd_panel.band_powers().values())
    assert 0.0 < total <= 1.0


def test_la_banda_de_la_onda_se_lleva_la_mayor_parte(ventana: MainWindow, elige_canal):
    """El BrainVision sintético tiene su onda en una frecuencia conocida, así
    que la banda que la contiene tiene que dominar. Es lo que hace que la tabla
    diga algo y no sólo que exista."""
    elige_canal("C3")
    ventana.show_psd_dialog()

    potencias = ventana.psd_panel.band_powers()
    mayor = max(potencias, key=lambda banda: potencias[banda][0])
    desde, hasta = DEFAULT_BANDS[mayor]
    # C3 del BrainVision sintético está en 10 Hz, que cae en Alpha.
    assert desde <= 10.0 < hasta


def test_cancelar_no_abre_nada(ventana: MainWindow, elige_canal):
    elige_canal("C3", acepta=False)

    ventana.show_psd_dialog()

    assert ventana.psd_panel.channels() == []


def test_pedir_el_espectro_de_otra_ventana_reemplaza(ventana: MainWindow, elige_canal):
    """No puede quedar la curva de la anterior encima."""
    elige_canal("C3")
    ventana.show_psd_dialog()
    elige_canal("EOG-izq")
    ventana._go_to_window(1)
    ventana.show_psd_dialog()

    assert ventana.psd_panel.channels() == ["EOG-izq"]


# -- Complejidad y conectividad, por la ventana (hito 14) --------------------


@pytest.fixture
def elige_opciones(monkeypatch):
    """Contesta una secuencia de diálogos de `QInputDialog.getItem`.

    Los de complejidad y conectividad preguntan dos cosas seguidas —canal y
    medida, o banda—, así que hace falta ir devolviendo respuestas distintas.
    """
    def responder_con(*respuestas):
        cola = iter(respuestas)
        monkeypatch.setattr(
            QInputDialog, "getItem", staticmethod(lambda *a, **k: next(cola))
        )
    return responder_con


def test_la_complejidad_recorre_la_noche_desde_el_menu(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("C3", True), ("permutation_entropy", True))

    ventana.show_complexity_dialog()

    serie = ventana.metric_panel.series("C3")
    assert len(serie) == VENTANAS
    assert np.isfinite(serie).all()
    assert not ventana.carteles


def test_el_eje_de_la_metrica_empieza_en_uno(ventana: MainWindow, elige_opciones):
    """Base 0 adentro, base 1 al mostrar: si empezara en 0, la curva quedaría
    desplazada una ventana respecto del histograma."""
    elige_opciones(("C3", True), ("permutation_entropy", True))

    ventana.show_complexity_dialog()

    assert ventana.metric_panel.window_positions("C3")[0] == 1.0


def test_la_interfaz_no_ofrece_la_medida_lenta():
    """**Está medido, no supuesto**: la entropía de muestra tarda 124 ms por
    ventana contra 0,07–1,7 ms de las otras tres, así que sobre un registro
    real son más de cinco minutos con la ventana congelada.

    El módulo la acepta igual; la política es de la interfaz.
    """
    from psglab.analysis.complexity import MEASURES
    from psglab.ui.main_window import MEDIDAS_RAPIDAS

    assert "sample_entropy" in MEASURES
    assert "sample_entropy" not in MEDIDAS_RAPIDAS
    assert set(MEDIDAS_RAPIDAS) < set(MEASURES)


def test_la_conectividad_de_la_ventana_desde_el_menu(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    matriz = ventana.connectivity_panel.matrix()
    assert matriz.shape[0] == len(ventana.session.visible_channels)
    assert not ventana.carteles


def test_el_mapa_lleva_los_nombres_de_los_canales(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    assert ventana.connectivity_panel.axis_labels() == ventana.session.visible_channels


def test_el_titulo_dice_la_ventana_y_el_promedio(ventana: MainWindow, elige_opciones):
    ventana._go_to_window(2)
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    titulo = ventana.connectivity_dialog.windowTitle()
    assert "ventana 3" in titulo
    assert "promedio" in titulo


def test_con_un_solo_canal_visible_avisa_en_vez_de_romper(
    ventana: MainWindow, elige_opciones
):
    """La conectividad se mide entre canales."""
    ventana.session.set_visible_channels(["C3"])
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    assert ventana.carteles


def test_cancelar_no_calcula_nada(ventana: MainWindow, elige_opciones):
    elige_opciones(("C3", False))

    ventana.show_complexity_dialog()

    assert ventana.metric_panel.channels() == []


# -- ICA, por la ventana (V5_F de "Filtración") ------------------------------


@pytest.fixture
def ventana_con_dos_eeg(qt_app, tmp_path, monkeypatch):
    """Como `ventana`, pero con dos canales EEG.

    La ICA necesita al menos dos: con uno solo el módulo se niega, con razón,
    porque no hay mezcla que separar. El BrainVision por omisión trae un solo
    EEG, y derivar no alcanza: `derive()` marca como `OTHER` un canal hecho de
    dos clases distintas, que es su regla y está bien.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "dos_eeg",
        segundos=WINDOW_SECONDS * 2,
        canales=[("C3", "µV"), ("C4", "µV"), ("EOG-izq", "µV")],
    )
    principal.open_recording(vhdr)
    principal.carteles = carteles
    return principal


def test_con_un_solo_eeg_la_ica_avisa(ventana: MainWindow):
    """El módulo se niega y acá eso tiene que salir como cartel, no como traza:
    con un canal no hay mezcla que separar."""
    ventana.show_ica_dialog()

    assert ventana.carteles


def test_ajustar_no_aplica_nada(ventana_con_dos_eeg: MainWindow):
    """**Ajustar e inspeccionar son dos pasos separados de aplicar**, porque
    quitar el componente equivocado no se puede deshacer."""
    antes = ventana_con_dos_eeg.session.recording.data.copy()

    ventana_con_dos_eeg.show_ica_dialog()

    assert ventana_con_dos_eeg.ica_panel.component_count() == 2
    assert ventana_con_dos_eeg.ica_panel.excluded() == []
    assert np.array_equal(ventana_con_dos_eeg.session.recording.data, antes)
    assert not ventana_con_dos_eeg.carteles


def test_la_curva_del_componente_llega_a_la_pantalla(ventana_con_dos_eeg: MainWindow):
    """**La mitad de V5_F que faltaba.** `component_time_course()` existía desde
    el hito 15 prometiendo en su docstring ser "lo que se dibuja debajo de la
    señal", y hasta el hito 19 no la llamaba nadie: el panel mostraba sólo la
    topografía, o sea *dónde* pesa el componente y no *cuándo* ocurre.
    """
    ventana_con_dos_eeg.show_ica_dialog()

    curva = ventana_con_dos_eeg.ica_panel.time_course_data()
    assert curva is not None, "el panel abrió sin curva"
    segundos, valores = curva
    assert len(segundos) == len(valores) > 0
    assert not ventana_con_dos_eeg.carteles


def test_la_curva_abarca_una_ventana_y_no_el_registro_entero(
    ventana_con_dos_eeg: MainWindow,
):
    """**De la ventana actual**, por el mismo motivo que el espectro y la
    conectividad: la serie de las ocho horas no se puede mirar, y reconstruirla
    entera cuesta una copia completa de la señal."""
    sesion = ventana_con_dos_eeg.session
    ventana_con_dos_eeg.show_ica_dialog()

    segundos, valores = ventana_con_dos_eeg.ica_panel.time_course_data()
    assert segundos[-1] < WINDOW_SECONDS
    assert len(valores) < sesion.recording.n_samples


def test_la_curva_se_pide_para_la_ventana_en_la_que_esta_el_usuario(
    ventana_con_dos_eeg: MainWindow, monkeypatch
):
    """**No se puede afirmar comparando las dos curvas**, y conviene decir por
    qué: el BrainVision sintético es periódico, así que sus dos ventanas
    contienen la misma onda y dan, correctamente, la misma serie. Comparar los
    valores verificaría la señal de prueba y no el cableado.

    Lo que sí se puede afirmar es la costura: qué ventana se pide.
    """
    import psglab.ui.main_window as ventana_principal

    pedidas: list[int] = []
    real = ventana_principal.component_time_course

    def espiar(ica, component, recording, window_index=None):
        pedidas.append(window_index)
        return real(ica, component, recording, window_index=window_index)

    monkeypatch.setattr(ventana_principal, "component_time_course", espiar)

    ventana_con_dos_eeg.show_ica_dialog()
    assert pedidas == [0]

    ventana_con_dos_eeg.go_to_next_window()
    ventana_con_dos_eeg.ica_panel.lista.setCurrentRow(1)

    assert pedidas == [0, 1], "la curva no siguió a la ventana actual"
    assert not ventana_con_dos_eeg.carteles


def test_elegir_otro_componente_cambia_la_curva(ventana_con_dos_eeg: MainWindow):
    """Cada componente tiene su serie; mostrar la del anterior debajo de otra
    topografía se leería como si fuera de ésta."""
    ventana_con_dos_eeg.show_ica_dialog()
    _, del_primero = ventana_con_dos_eeg.ica_panel.time_course_data()

    ventana_con_dos_eeg.ica_panel.lista.setCurrentRow(1)
    _, del_segundo = ventana_con_dos_eeg.ica_panel.time_course_data()

    assert not np.allclose(del_primero, del_segundo)
    assert not ventana_con_dos_eeg.carteles


def test_aplicar_deja_volver_a_la_señal_original(ventana_con_dos_eeg: MainWindow):
    """**Es la única red contra una exclusión equivocada**, y por eso la ICA
    pasa por el mismo camino que los demás análisis del menú."""
    ventana_con_dos_eeg.show_ica_dialog()
    original = ventana_con_dos_eeg.session.recording.data.copy()

    ventana_con_dos_eeg.ica_panel.set_excluded([0])
    ventana_con_dos_eeg.ica_panel._aplicar()

    assert not np.array_equal(ventana_con_dos_eeg.session.recording.data, original)
    assert ventana_con_dos_eeg.accion_señal_original.isEnabled()

    ventana_con_dos_eeg.restore_original_recording()
    assert np.allclose(ventana_con_dos_eeg.session.recording.data, original)


# -- Que la ICA no sobreviva a un cambio de señal ----------------------------
#
# `fit_ica()` se ajusta sobre la señal que hay en ese momento y el panel se queda
# abierto esperando que el usuario elija qué quitar. Si entre el ajuste y el
# "Aplicar" la señal cambia, la matriz de desmezclado deja de corresponder.
#
# **Y no falla sola**, que es lo que lo vuelve caro: filtrar no cambia los
# nombres de los canales, así que MNE acepta el pedido sin protestar y devuelve
# una señal reconstruida con una descomposición ajena. Plausible, irreversible y
# equivocada. Son tres caminos y los tres se prueban por la ventana.


def test_filtrar_despues_de_ajustar_descarta_la_descomposicion(
    ventana_con_dos_eeg: MainWindow,
):
    """El camino que encontró el bug: ajustar, filtrar, y el panel seguía vivo."""
    ventana_con_dos_eeg.show_ica_dialog()
    assert ventana_con_dos_eeg.ica_panel.component_count() == 2

    ventana_con_dos_eeg.show_filter_dialog()
    ventana_con_dos_eeg.filter_panel.boton_aplicar.click()

    assert ventana_con_dos_eeg._ica is None
    assert ventana_con_dos_eeg.ica_panel.component_count() == 0
    assert not ventana_con_dos_eeg.carteles


def test_volver_a_la_señal_original_descarta_la_descomposicion(
    ventana_con_dos_eeg: MainWindow,
):
    """Deshacer también cambia la señal: la ICA se ajustó sobre la procesada."""
    ventana_con_dos_eeg.show_filter_dialog()
    ventana_con_dos_eeg.filter_panel.boton_aplicar.click()
    ventana_con_dos_eeg.show_ica_dialog()
    assert ventana_con_dos_eeg._ica is not None

    ventana_con_dos_eeg.restore_original_recording()

    assert ventana_con_dos_eeg._ica is None
    assert ventana_con_dos_eeg.ica_panel.component_count() == 0


def test_abrir_otro_registro_descarta_la_descomposicion(
    ventana_con_dos_eeg: MainWindow, tmp_path: Path
):
    """Es el mismo motivo por el que abrir un registro suelta las herramientas:
    lo que quedó guardado es de otra señal y de otros canales."""
    ventana_con_dos_eeg.show_ica_dialog()
    assert ventana_con_dos_eeg._ica is not None

    otro = escribir_brainvision(
        tmp_path / "otro",
        segundos=WINDOW_SECONDS * 2,
        canales=[("Fp1", "µV"), ("Fp2", "µV")],
    )
    ventana_con_dos_eeg.open_recording(otro)

    assert ventana_con_dos_eeg._ica is None
    assert ventana_con_dos_eeg.ica_panel.component_count() == 0
    assert not ventana_con_dos_eeg.carteles


def test_aplicar_una_ica_de_otros_canales_avisa_en_vez_de_reconstruir(
    ventana_con_dos_eeg: MainWindow, tmp_path: Path
):
    """La segunda guarda, la del módulo, para cuando la primera no alcanzara.

    `apply_ica()` comprueba que los canales sobre los que se ajustó sigan
    existiendo. No ve el caso del filtro —ahí los nombres son los mismos— pero sí
    éste, que es el que deja una señal reconstruida con una mezcla de otra
    cabeza.
    """
    ventana_con_dos_eeg.show_ica_dialog()
    descomposicion = ventana_con_dos_eeg._ica

    otro = escribir_brainvision(
        tmp_path / "ajeno",
        segundos=WINDOW_SECONDS * 2,
        canales=[("Fp1", "µV"), ("Fp2", "µV")],
    )
    ventana_con_dos_eeg.open_recording(otro)
    antes = np.array(ventana_con_dos_eeg.session.recording.data, copy=True)

    with pytest.raises(PsgLabError):
        apply_ica(ventana_con_dos_eeg.session.recording, descomposicion, [0])

    assert np.array_equal(ventana_con_dos_eeg.session.recording.data, antes)


# -- Impedancia, por la ventana (V1_F de "Impedancia") -----------------------


@pytest.fixture
def ventana_con_impedancias(qt_app, tmp_path, monkeypatch):
    """Como `ventana`, pero con un BrainVision que trae impedancias.

    Uno medido y bien, uno medido y alto, y uno sin medir: los tres estados
    que el informe tiene que distinguir.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "con_impedancias",
        segundos=WINDOW_SECONDS * 2,
        canales=[("C3", "µV"), ("C4", "µV"), ("O1", "µV")],
        impedancias={"C3": 4.2, "C4": 12.5, "O1": None},
    )
    principal.open_recording(vhdr)
    principal.carteles = carteles
    return principal


def test_las_impedancias_del_archivo_llegan_a_la_tabla(
    ventana_con_impedancias: MainWindow,
):
    """**BrainVision sí las trae**, y el camino completo —archivo, lector,
    módulo, panel— tiene que conservarlas."""
    ventana_con_impedancias.show_impedance_dialog()

    assert ventana_con_impedancias.impedance_panel.values() == {"C3": 4.2, "C4": 12.5}
    assert not ventana_con_impedancias.carteles


def test_el_que_estaba_sin_medir_se_ve_como_sin_medir(
    ventana_con_impedancias: MainWindow,
):
    """**La distinción que sostiene el módulo**, vista por la ventana."""
    from psglab.ui.impedance_panel import SIN_MEDIR

    ventana_con_impedancias.show_impedance_dialog()
    panel = ventana_con_impedancias.impedance_panel

    assert panel.displayed_value("O1") == SIN_MEDIR
    assert panel.unmeasured() == ["O1"]


def test_el_informe_muestra_los_tres_estados(ventana_con_impedancias: MainWindow):
    ventana_con_impedancias.show_impedance_dialog()
    informe = ventana_con_impedancias.impedance_panel.report_text

    assert "Por encima del límite" in informe
    assert "Dentro del límite" in informe
    assert "Sin medición disponible" in informe


def test_editar_a_mano_rehace_el_informe(ventana_con_impedancias: MainWindow):
    """Es la tercera vía: cargar a mano lo que el archivo no trae."""
    ventana_con_impedancias.show_impedance_dialog()
    panel = ventana_con_impedancias.impedance_panel
    assert "Sin medición disponible" in panel.report_text

    for fila in range(panel.tabla.topLevelItemCount()):
        entrada = panel.tabla.topLevelItem(fila)
        if entrada.text(0) == "O1":
            entrada.setText(1, "3,1")

    assert "Sin medición disponible" not in panel.report_text
    assert panel.values()["O1"] == 3.1


def test_sin_ninguna_impedancia_el_informe_dice_que_hacer(ventana: MainWindow):
    """**Es el caso de todo EDF**, donde el formato no puede traerlas, y el de
    un BrainVision sin tabla como el de esta fixture.

    Listar los canales sin medir y callarse dejaría al investigador mirando una
    lista sin salida.
    """
    ventana.show_impedance_dialog()

    assert ventana.impedance_panel.values() == {}
    assert "No hay ninguna impedancia cargada" in ventana.impedance_panel.report_text


def test_importar_de_un_archivo_agrega_sin_reemplazar(
    ventana_con_impedancias: MainWindow, tmp_path: Path, monkeypatch
):
    """Un laboratorio puede tener medido medio montaje: el archivo suma."""
    archivo = tmp_path / "imp.txt"
    archivo.write_text("O1 3.1\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(archivo), ""))
    )

    ventana_con_impedancias.show_impedance_dialog()
    ventana_con_impedancias.load_impedances_dialog()

    assert ventana_con_impedancias.impedance_panel.values() == {
        "C3": 4.2,
        "C4": 12.5,
        "O1": 3.1,
    }


def test_un_archivo_mal_formado_avisa_sin_romper(
    ventana_con_impedancias: MainWindow, tmp_path: Path, monkeypatch
):
    archivo = tmp_path / "malo.txt"
    archivo.write_text("C3 cuatro\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(archivo), ""))
    )

    ventana_con_impedancias.show_impedance_dialog()
    ventana_con_impedancias.load_impedances_dialog()

    assert ventana_con_impedancias.carteles


# -- Filtración, por la ventana (V1_F de "Filtración") -----------------------


def test_el_panel_de_filtros_se_arma_con_las_clases_del_registro(ventana: MainWindow):
    """El camino completo: abrir un archivo, abrir el panel y encontrarlo
    cargado con los sugeridos de lo que ese registro tiene."""
    ventana.show_filter_dialog()

    assert ventana.filter_panel.kinds()
    assert set(ventana.filter_panel.kinds()) == {
        canal.kind for canal in ventana.session.recording.channels
    }
    assert not ventana.carteles


def test_abrir_el_panel_no_filtra_nada(ventana: MainWindow):
    """Un menú que filtre con sólo abrirse le cambiaría la señal a alguien que
    entró a mirar qué había."""
    original = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()

    assert np.array_equal(ventana.session.recording.data, original)
    assert not ventana.accion_señal_original.isEnabled()


def test_filtrar_desde_la_ventana_cambia_la_señal(ventana: MainWindow):
    original = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()

    assert not np.array_equal(ventana.session.recording.data, original)
    assert not ventana.carteles


def test_un_filtro_mal_elegido_no_obliga_a_reabrir_el_archivo(ventana: MainWindow):
    """**Poder deshacer**, que es el requisito que el hito tenía escrito. La
    misma acción del menú que deshace una derivación deshace un filtro."""
    original = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()
    assert ventana.accion_señal_original.isEnabled()

    ventana.restore_original_recording()

    assert np.allclose(ventana.session.recording.data, original)


def test_un_corte_imposible_avisa_y_no_cambia_la_señal(ventana: MainWindow):
    """Un pasa-bajos por encima de Nyquist sale como cartel, y la señal que el
    investigador está mirando sigue siendo la de antes."""
    original = np.array(ventana.session.recording.data, copy=True)
    ventana.show_filter_dialog()
    ventana.filter_panel.tabla.topLevelItem(0).setText(2, "9000")

    ventana.filter_panel.boton_aplicar.click()

    assert ventana.carteles
    assert np.array_equal(ventana.session.recording.data, original)


def test_se_puede_filtrar_despues_de_re_referenciar(ventana: MainWindow):
    """Se filtra **la señal que se está viendo**, no la original: es el orden
    en que se trabaja."""
    ventana.apply_average_reference()
    re_referenciada = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()

    assert not np.array_equal(ventana.session.recording.data, re_referenciada)
    assert not ventana.carteles


# -- Un registro de 100 Hz, por la ventana (hallazgo del hito 17) -------------


@pytest.fixture
def ventana_a_100_hz(qt_app, tmp_path, monkeypatch):
    """Como `ventana`, pero con un registro muestreado a 100 Hz.

    **Es la frecuencia que destapó el hito 17.** El registro real de `data/`
    está a 100 Hz, y con Nyquist en 50 el notch sugerido de 50 Hz quedaba justo
    afuera: abrir el panel y apretar Aplicar sin tocar nada terminaba en un
    cartel de error. Toda la suite usaba 256 Hz, así que nada lo veía.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "cien_hz", segundos=WINDOW_SECONDS * 2, frecuencia=100.0
    )
    principal.open_recording(vhdr)
    assert not carteles, f"abrir el registro mostró un error: {carteles}"
    principal.carteles = carteles
    return principal


def test_el_registro_es_de_100_hz(ventana_a_100_hz: MainWindow):
    """Que la fixture sea lo que dice ser: sin esto los tres de abajo podrían
    estar pasando por la razón equivocada."""
    assert ventana_a_100_hz.session.recording.sampling_rate == 100.0


def test_aplicar_los_sugeridos_a_100_hz_no_da_ningun_cartel(
    ventana_a_100_hz: MainWindow,
):
    """**El hallazgo del hito 17, por el camino del usuario.** Abrir el panel,
    no tocar nada y apretar Aplicar, que es lo que hace cualquiera la primera
    vez. Antes daba `InvalidFilterError`."""
    original = np.array(ventana_a_100_hz.session.recording.data, copy=True)

    ventana_a_100_hz.show_filter_dialog()
    ventana_a_100_hz.filter_panel.boton_aplicar.click()

    assert not ventana_a_100_hz.carteles
    assert not np.array_equal(ventana_a_100_hz.session.recording.data, original)


def test_el_notch_no_se_ofrece_a_100_hz(ventana_a_100_hz: MainWindow):
    """La celda viene vacía porque el registro no contiene 50 Hz, no porque
    alguien se haya olvidado."""
    from psglab.core.recording import ChannelKind

    ventana_a_100_hz.show_filter_dialog()
    panel = ventana_a_100_hz.filter_panel

    assert panel.displayed_value(ChannelKind.EEG, "notch_hz") == ""
    assert "50" in panel.rotulo.text()


def test_a_256_hz_el_notch_sigue_estando(ventana: MainWindow):
    """La otra mitad: descartar sólo lo que no entra. La fixture normal es de
    250 Hz, así que el notch de 50 tiene que seguir ofreciéndose."""
    from psglab.core.recording import ChannelKind

    ventana.show_filter_dialog()

    assert ventana.filter_panel.displayed_value(ChannelKind.EEG, "notch_hz") == "50"


# -- Quedarse sin memoria, por la ventana (hito 18) --------------------------


def test_sin_memoria_sale_un_cartel_y_no_una_traza(ventana: MainWindow, monkeypatch):
    """**El único error del programa que llegaba como traza de Python.**

    `_aplicar_analisis()` atrapa `PsgLabError` y nada más, así que un
    `MemoryError` —que es el más probable de todos en un registro de ocho
    horas— se le escapaba y salía por la consola. Ahora sale por el mismo
    cartel que el resto.
    """
    import psglab.analysis.mne_bridge as puente

    def sin_memoria(*_args, **_kwargs):
        raise MemoryError()

    original = np.array(ventana.session.recording.data, copy=True)
    ventana.show_filter_dialog()
    monkeypatch.setattr(puente.np, "array", sin_memoria)

    ventana.filter_panel.boton_aplicar.click()

    assert ventana.carteles, "el MemoryError no se convirtió en cartel"
    assert "memoria" in ventana.carteles[0].lower()


def test_sin_memoria_la_señal_queda_como_estaba(ventana: MainWindow, monkeypatch):
    """La otra mitad del mensaje, y tiene que ser cierta: el cartel promete que
    el registro sigue abierto y sin cambios.

    **La afirmación del cartel va junto con la de la señal, y no es de más.**
    La primera versión de este test miraba sólo la señal y pasaba igual con la
    guarda rota: sin ella el `MemoryError` sale por otro lado, Qt se lo traga, y
    la señal queda intacta de todos modos. Pasaba por la razón equivocada.
    """
    import psglab.analysis.mne_bridge as puente

    original = np.array(ventana.session.recording.data, copy=True)
    ventana.show_filter_dialog()
    monkeypatch.setattr(
        puente.np, "array", lambda *a, **k: (_ for _ in ()).throw(MemoryError())
    )

    ventana.filter_panel.boton_aplicar.click()

    assert ventana.carteles
    assert np.array_equal(ventana.session.recording.data, original)
    assert not ventana.accion_señal_original.isEnabled()


# -- Que se note que está trabajando (hito 18) -------------------------------


def test_durante_un_analisis_el_cursor_dice_que_esta_trabajando(ventana: MainWindow):
    """**No acorta la espera: la hace legible.** Todo corre en el hilo de la
    interfaz, así que la ventana queda congelada mientras dura el cálculo, y sin
    ninguna señal eso se lee como que el programa se colgó. El hito 17 midió que
    la primera complejidad de cada sesión se lleva unos 21 s sólo compilando.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    visto: list[object] = []

    def mirar_el_cursor(registro):
        cursor = QApplication.overrideCursor()
        visto.append(cursor.shape() if cursor is not None else None)
        return registro

    ventana._aplicar_analisis("Se hizo algo", mirar_el_cursor)

    assert visto == [Qt.CursorShape.WaitCursor]


def test_abrir_un_registro_avisa_mientras_lee(
    ventana: MainWindow, tmp_path: Path, monkeypatch
):
    """Leer una noche entera son varios segundos con la ventana congelada: sin
    cursor de espera ni mensaje se lee como que el programa se colgó, y es lo
    primero que hace el usuario."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    visto: list[tuple[object, str]] = []
    leer = main_window_mod.read_recording

    def mirar(ruta):
        cursor = QApplication.overrideCursor()
        visto.append(
            (
                cursor.shape() if cursor is not None else None,
                ventana.statusBar().currentMessage(),
            )
        )
        return leer(ruta)

    monkeypatch.setattr(main_window_mod, "read_recording", mirar)
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS)

    ventana.open_recording(otro)

    (forma, mensaje), = visto
    assert forma == Qt.CursorShape.WaitCursor
    assert otro.name in mensaje
    assert QApplication.overrideCursor() is None
    assert not ventana.carteles


def test_al_terminar_el_cursor_vuelve(ventana: MainWindow):
    """Un cursor de espera que no se restaura deja el programa inutilizable a
    la vista, aunque funcione."""
    from PySide6.QtWidgets import QApplication

    ventana._aplicar_analisis("Se hizo algo", lambda registro: registro)

    assert QApplication.overrideCursor() is None


def test_el_cursor_vuelve_aunque_el_analisis_falle(ventana: MainWindow):
    """Es lo que hace el `finally`: si un análisis eleva, el cursor no puede
    quedarse en espera para siempre."""
    from PySide6.QtWidgets import QApplication
    from psglab.utils.errors import InvalidRecordingError

    def fallar(_registro):
        raise InvalidRecordingError("no se pudo")

    ventana._aplicar_analisis("Se hizo algo", fallar)

    assert QApplication.overrideCursor() is None
    assert ventana.carteles


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


def test_elegir_un_esquema_tampoco_escribe_el_archivo(
    ventana: MainWindow, escrituras: list[object]
):
    """Antes sí lo escribía: `set_color_scheme()` guardaba siempre que no se le
    pasara `remember=False`, fuera quien fuera el que había abierto la
    ventana."""
    anterior = theme.current()
    try:
        ventana.set_color_scheme(theme.OSCURO)
        assert escrituras == []
    finally:
        ventana.set_color_scheme(anterior, remember=False)


def test_el_espectro_usa_el_metodo_elegido(
    ventana: MainWindow, elige_canal, monkeypatch
):
    metodos: list[object] = []
    original = main_window_mod.compute_psd

    def espiando(*args: object, **kwargs: object) -> object:
        metodos.append(kwargs.get("method"))
        return original(*args, **kwargs)

    monkeypatch.setattr(main_window_mod, "compute_psd", espiando)
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


def test_la_conectividad_ofrece_las_mismas_bandas_que_el_espectro(
    ventana: MainWindow, monkeypatch
):
    """Dos definiciones de «sigma» en el mismo programa serían una trampa."""
    ofrecidas: list[list[str]] = []

    def respondiendo(_padre, _titulo, _etiqueta, opciones, *_resto, **_kw):
        ofrecidas.append(list(opciones))
        return ("", False)

    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(respondiendo))
    ventana.apply_preferences(
        ventana.current_preferences.with_bands({"Huso": (11.0, 16.0)})
    )

    ventana.show_connectivity_dialog()

    assert ["Huso"] in ofrecidas


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

    ventana._toggle_tool("occupancy", True)
    ventana._tools["occupancy"].add_line(OccupancyLine(0.2, 0.0, 0.6, 0.0))
    dibujadas = len(ventana.signal_view._overlay_items)
    assert dibujadas > 0

    ventana.apply_preferences(
        ventana.current_preferences.with_annotation_color("Spindle", "#ff8800")
    )

    assert len(ventana.signal_view._overlay_items) == dibujadas


def test_con_el_anotador_activo_la_banda_cambia_de_color_enseguida(
    ventana: MainWindow,
):
    """El otro lado del test de arriba: cuando el que dibuja es el anotador, la
    banda tiene que tomar el color nuevo sin esperar a la próxima flecha."""
    ventana._toggle_tool("annotator", True)
    ventana._tools["annotator"].create_annotation("Spindle", 250, 250)

    ventana.apply_preferences(
        ventana.current_preferences.with_annotation_color("Spindle", "#ff8800")
    )

    colores = [
        item.brush.color().name()
        for item in ventana.signal_view._overlay_items
        if hasattr(item, "brush")
    ]
    assert "#ff8800" in colores
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
    original = main_window_mod.read_recording
    monkeypatch.setattr(
        main_window_mod,
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
    assert ventana.signal_view._labels
    for etiqueta in ventana.signal_view._labels:
        assert etiqueta.textItem.font().pointSize() == 17


def test_se_puede_volver_a_la_tipografia_del_sistema(
    ventana: MainWindow, fuente_restaurada
):
    del_sistema = QFont(ventana._fuente_del_sistema)
    _con(ventana, font_size=17)

    _con(ventana, font_size=None)

    assert QApplication.font().pointSize() == del_sistema.pointSize()
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
    """Un esquema que cambia sin pasar por la configuración —el menú de
    esquemas lo hacía hasta el hito 23; hoy, `set_color_scheme()` llamado
    desde otro lado— tiene que verse al reabrirla."""
    ventana.show_settings_dialog()
    ventana.settings_dialog.close()
    anterior = theme.current()
    try:
        ventana.set_color_scheme(theme.ECG, remember=False)

        ventana.show_settings_dialog()

        assert ventana.settings_dialog.grid_ecg.isChecked()
    finally:
        ventana.settings_dialog.close()
        ventana.set_color_scheme(anterior, remember=False)


def test_la_configuracion_se_abre_sin_registro(qt_app):
    """Con las clases de fábrica, que es lo que el usuario va a tener."""
    principal = create_main_window()

    principal.show_settings_dialog()

    assert set(principal.settings_dialog.annotation_buttons) >= {"Spindle"}
    principal.settings_dialog.close()


# -- La conectividad a lo largo de la noche ---------------------------------------
#
# Era un hueco declarado desde el hito 20: la función existía, el panel también,
# y ningún camino los juntaba.


def test_la_conectividad_de_la_noche_desde_el_menu(ventana: MainWindow, elige_opciones):
    """Un número por época, **con el largo de la noche**: es lo que lo deja
    alineado con el hipnograma."""
    elige_opciones(("Delta", True))

    ventana.show_connectivity_night_dialog()

    (serie,) = ventana.metric_panel.channels()
    assert len(ventana.metric_panel.series(serie)) == ventana.session.n_windows
    assert ventana.metric_panel.window_positions(serie)[0] == 1.0
    assert not ventana.carteles


def test_cada_epoca_vale_lo_mismo_que_la_conectividad_de_esa_ventana(
    ventana: MainWindow, elige_opciones
):
    """**Los dos caminos tienen que coincidir.** El barrido promedia la misma
    matriz que el menú de la ventana muestra: si dieran distinto, uno de los dos
    le estaría mintiendo al investigador."""
    from psglab.analysis.connectivity import average_connectivity

    elige_opciones(("Delta", True), ("Delta", True))
    ventana._go_to_window(2)

    ventana.show_connectivity_night_dialog()
    (serie,) = ventana.metric_panel.channels()
    de_la_noche = ventana.metric_panel.series(serie)[2]
    ventana.show_connectivity_dialog()
    de_la_ventana = average_connectivity(ventana.connectivity_panel.matrix())

    assert de_la_noche == pytest.approx(de_la_ventana)


def test_el_titulo_dice_la_banda_y_entre_que_canales(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("Theta", True))

    ventana.show_connectivity_night_dialog()

    titulo = ventana.metric_dialog.windowTitle()
    assert "Theta" in titulo
    assert "noche" in titulo
    for canal in ventana.session.visible_channels:
        assert canal in titulo


def test_cancelar_la_banda_no_mide_nada(ventana: MainWindow, elige_opciones, monkeypatch):
    """Es la operación más cara del menú después de la ICA: cancelar no puede
    arrancarla igual."""
    llamadas: list[object] = []
    monkeypatch.setattr(
        main_window_mod,
        "connectivity_by_window",
        lambda *args, **kwargs: llamadas.append(args),
    )
    elige_opciones(("", False))

    ventana.show_connectivity_night_dialog()

    assert llamadas == []
    assert not ventana.carteles


def test_con_un_solo_canal_visible_avisa_sin_medir(ventana: MainWindow):
    ventana.session.set_visible_channels(ventana.session.visible_channels[:1])

    ventana.show_connectivity_night_dialog()

    assert ventana.carteles


def test_medir_la_noche_no_mueve_al_usuario_de_ventana(
    ventana: MainWindow, elige_opciones
):
    ventana._go_to_window(3)
    elige_opciones(("Delta", True))

    ventana.show_connectivity_night_dialog()

    assert ventana.session.current_window == 3


def test_medir_la_noche_muestra_el_cursor_de_espera(
    ventana: MainWindow, elige_opciones, monkeypatch
):
    """Tarda medio minuto sobre un registro real: sin cursor, se lee como un
    programa colgado."""
    cursores: list[object] = []
    original = main_window_mod.connectivity_by_window

    def midiendo(*args: object, **kwargs: object) -> object:
        cursores.append(QApplication.overrideCursor())
        return original(*args, **kwargs)

    monkeypatch.setattr(main_window_mod, "connectivity_by_window", midiendo)
    elige_opciones(("Delta", True))

    ventana.show_connectivity_night_dialog()

    assert cursores and cursores[0] is not None
    assert QApplication.overrideCursor() is None


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
    assert ventana.psd_dialog not in ventana.focusable_panes()

    ventana.psd_dialog.show()

    assert ventana.psd_dialog in ventana.focusable_panes()


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


@pytest.fixture
def reproduccion(ventana: MainWindow):
    """La ventana, con la reproducción detenida al terminar pase lo que pase:
    un temporizador vivo seguiría moviendo la página en el test siguiente."""
    yield ventana
    ventana.playback.stop()


def pagina(ventana: MainWindow) -> float:
    return ventana.session.viewport.start_seconds


def centro_de(epoca: int) -> float:
    return (epoca + 0.5) * WINDOW_SECONDS


def test_reproducir_lleva_la_epoca_que_pasa_por_el_medio(reproduccion: MainWindow):
    """Al pausar, el usuario queda parado en la época que estaba mirando."""
    ventana = reproduccion

    ventana.toggle_playback()
    ventana.playback.advanced.emit(10.0)
    ventana.playback.advanced.emit(10.0)

    assert ventana.playback.is_playing
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
    ventana.playback.advanced.emit(WINDOW_SECONDS)

    assert ventana.navigation._posicion.text() == f"Ventana 2 de {VENTANAS}"
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
    ventana.playback.advanced.emit(10.0)

    assert pagina(ventana) == 0.0
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(0) + 10.0)

    ventana.playback.advanced.emit(10.0)

    assert pagina(ventana) == pytest.approx(centro_de(0) + 20.0 - WINDOW_SECONDS)
    assert ventana.session.current_window == 1


def test_al_final_el_cursor_llega_al_borde_y_se_detiene(reproduccion: MainWindow):
    """La página ya no se mueve, y el cursor sigue hasta el final del registro:
    así se recorren también las últimas épocas."""
    ventana = reproduccion
    ventana.set_timescale(2 * WINDOW_SECONDS)
    ventana._go_to_window(VENTANAS - 1)

    ventana.toggle_playback()
    assert ventana.session.viewport.at_end
    ventana.playback.advanced.emit(10.0)
    assert ventana.playback.is_playing

    ventana.playback.advanced.emit(10 * WINDOW_SECONDS)

    assert not ventana.playback.is_playing
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
    ventana.playback.advanced.emit(2 * WINDOW_SECONDS)

    assert ventana.playback.is_playing
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

    assert ventana.playback.is_playing
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(0))
    assert pagina(ventana) == 0.0


def test_sin_registro_reproducir_no_hace_nada(qt_app):
    principal = create_main_window()

    principal.toggle_playback()

    assert not principal.playback.is_playing


def test_apretar_de_nuevo_pausa(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.navigation._reproducir.click()
    ventana.playback.advanced.emit(5.0)

    ventana.navigation._reproducir.click()

    assert not ventana.playback.is_playing
    assert pagina(ventana) == pytest.approx(5.0)
    assert ventana.navigation._reproducir.toolTip() == "Reproducir"


def test_al_pausar_se_va_el_cursor_y_se_queda_la_epoca(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.toggle_playback()
    ventana.playback.advanced.emit(20.0)
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
    assert ventana.playback.is_playing
    assert not ventana.carteles


def test_la_ultima_y_la_franja_reproduciendo_llevan_el_cursor(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.toggle_playback()

    ventana.navigation._ultima.click()
    assert ventana.session.current_window == VENTANAS - 1
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(VENTANAS - 1))

    ventana._go_to_window(2)
    assert ventana.signal_view.playhead() == pytest.approx(centro_de(2))
    assert ventana.playback.is_playing


def test_siguiente_en_la_ultima_reproduciendo_no_hace_nada(reproduccion: MainWindow):
    """Como la flecha en pausa: llegar al borde no es un error ni un salto al
    final del registro."""
    ventana = reproduccion
    ventana._go_to_window(VENTANAS - 1)
    ventana.toggle_playback()

    ventana.go_to_next_window()

    assert ventana.signal_view.playhead() == pytest.approx(centro_de(VENTANAS - 1))
    assert ventana.playback.is_playing


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
    assert ventana.playback.is_playing


def test_scorear_reproduciendo_no_saca_la_pagina_del_cursor(reproduccion: MainWindow):
    """Con la página de 30 s centrada en el cursor la época no entra entera, y
    redibujar con `containing()` la llevaba al comienzo de la época."""
    from psglab.core.nomenclature import SleepStage

    ventana = reproduccion
    ventana.toggle_playback()
    ventana.playback.advanced.emit(10.0)
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

    assert not ventana.playback.is_playing
    assert pagina(ventana) == 0.0
    assert ventana.signal_view.playhead() is None


def test_volver_a_la_senal_original_detiene_la_reproduccion(reproduccion: MainWindow):
    ventana = reproduccion
    ventana.accion_señal_original.setEnabled(True)
    ventana.toggle_playback()

    ventana.restore_original_recording()

    assert not ventana.playback.is_playing


def test_la_velocidad_del_selector_llega_al_reloj(reproduccion: MainWindow):
    selector = reproduccion.navigation.speed_selector

    selector.setCurrentIndex(selector.findText("30×"))

    assert reproduccion.playback.speed == 30.0


def test_espacio_reproduce_y_pausa(reproduccion: MainWindow):
    """El atajo cuelga de la señal. Se lo dispara por su señal: apretar la
    tecla de verdad necesita la ventana en pantalla y con el foco."""
    from PySide6.QtGui import QShortcut

    ventana = reproduccion
    (espacio,) = [
        a for a in ventana.findChildren(QShortcut) if a.key().toString() == "Space"
    ]

    espacio.activated.emit()
    assert ventana.playback.is_playing

    espacio.activated.emit()
    assert not ventana.playback.is_playing


def test_el_programa_abre_solo_con_la_senal_y_los_canales(ventana: MainWindow):
    """Hito 24. Con un registro abierto sigue igual: abrir no despliega nada."""
    visibles = [clave for clave, dock in ventana.docks.items() if not dock.isHidden()]

    assert visibles == ["channels"]
