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

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QInputDialog

pytest.importorskip("pyqtgraph")

from psglab.config import (  # noqa: E402
    ANNOTATIONS_FILENAME,
    INFORMATION_FILENAME,
    SCORING_FILENAME,
    WINDOW_SECONDS,
)
from psglab.app import create_main_window  # noqa: E402
from psglab.core.nomenclature import stages_of  # noqa: E402
from psglab.exporters import DEFAULT_FILENAMES as NOMBRES  # noqa: E402
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
    # la barra de herramientas y el filtro del diálogo de apertura se arman
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
    """V4_F: los tres se piden **de a uno**, que es lo que el pliego pide."""
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


def arrastrar(ventana: MainWindow, desde_x: float, hasta_x: float) -> None:
    """Presiona, mueve y suelta el botón izquierdo sobre el visualizador."""
    caja = ventana.signal_view.getPlotItem().vb.sceneBoundingRect()
    viewport = ventana.signal_view.viewport()

    def evento(tipo: QEvent.Type, x: float) -> QMouseEvent:
        punto = QPointF(float(x), caja.center().y())
        return QMouseEvent(
            tipo,
            punto,
            punto,
            punto,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

    aplicacion = QApplication.instance()
    aplicacion.sendEvent(viewport, evento(QEvent.Type.MouseButtonPress, desde_x))
    aplicacion.sendEvent(viewport, evento(QEvent.Type.MouseMove, hasta_x))
    aplicacion.sendEvent(viewport, evento(QEvent.Type.MouseButtonRelease, hasta_x))


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
