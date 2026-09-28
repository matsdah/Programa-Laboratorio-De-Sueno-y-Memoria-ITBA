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

**Desde el hito 79 son seis archivos.** Había llegado a 7258 líneas y 437
tests, y cada hito le sumaba una sección al final. Éste se quedó con lo que
es la entrega —abrir, navegar, scorear y exportar— y con lo que protege el
trabajo: los cuatro formatos del scoring, el trabajo sin exportar, la copia
de recuperación y lo que se hace al abrir otro registro. El resto, por tema,
en `test_entrega_scoring.py`, `test_entrega_anotacion.py`,
`test_entrega_vista.py`, `test_entrega_analisis.py` y
`test_entrega_interfaz.py`. La ventana de prueba y lo que usan varios está en
`entrega_comun.py`, que no es un test.

Corre en cualquier lado, incluido el CI: usa el BrainVision sintético de
`conftest.py`, no los registros de `data/`.
"""

from pathlib import Path

import pytest

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

pytest.importorskip("pyqtgraph")

from psglab.config import (  # noqa: E402
    ANNOTATIONS_FILENAME,
    INFORMATION_FILENAME,
    SCORING_FILENAME,
    WINDOW_SECONDS,
)
from psglab.app import create_main_window  # noqa: E402
from psglab.core.annotations import Annotation  # noqa: E402
from psglab.core.nomenclature import SleepStage, stages_of  # noqa: E402
from psglab.exporters import DEFAULT_FILENAMES as NOMBRES  # noqa: E402
from psglab.ui import theme  # noqa: E402
from psglab.ui.docks import ORDEN_DE_ANALISIS  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from psglab.ui.overview_panel import accessible_summary  # noqa: E402
from psglab.ui.work_guard import WorkGuard  # noqa: E402
from psglab.utils.errors import PsgLabError  # noqa: E402

from conftest import escribir_brainvision, escribir_edf  # noqa: E402
from entrega_comun import (  # noqa: E402, F401
    VENTANAS,
    dialogo_de_guardado,
    elige_canal,
    otro_registro,
    ventana,
    ventana_con_dos_eeg,
)


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
    # Puntuar pasa a la siguiente desde el hito 64: se vuelve a marcar el
    # arousal de la misma.
    ventana._go_to_window(0)
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
    ventana: MainWindow, tmp_path: Path, extension: str, cartel_del_scoring
):
    """Por la ventana de punta a punta: exportar, perder el trabajo e
    importarlo de vuelta.

    **Lo de arriba es justamente scoring sin exportar**, así que desde el hito
    33 importar lo pregunta antes de pisarlo; acá el usuario lo descarta, que
    es lo que este test va a hacer de todos modos.
    """
    esperado = scorear_todas(ventana)
    destino = tmp_path / f"Scoring.{extension}"
    ventana.export("scoring", destino)

    for indice in range(VENTANAS):
        ventana._go_to_window(indice)
        ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])
    cartel_del_scoring["respuesta"] = "descartar"
    ventana.open_scoring(destino)

    assert cartel_del_scoring["preguntas"] == [f"importar «{destino.name}»"]

    sesion = ventana.session
    assert [
        (sesion.scoring.get(i).stage, sesion.scoring.get(i).arousal) for i in range(VENTANAS)
    ] == esperado
    assert not ventana.carteles


def test_importar_un_xml_que_declara_entidades_es_un_cartel(
    ventana: MainWindow, tmp_path: Path
):
    """**Un XML hecho a propósito podía agotar la memoria** al expandir sus
    entidades (hito 79). Por la ventana tiene que ser un cartel que dice por
    qué, y el scoring que estaba queda como estaba."""
    ventana._go_to_window(0)
    ventana.score_current_window(stages_of(ventana.session.scoring.nomenclature)[0])
    antes = [ventana.session.scoring.get(i) for i in range(VENTANAS)]
    ruta = tmp_path / "scoring.xml"
    niveles = "".join(
        f'<!ENTITY a{n} "{f"&a{n - 1};" * 10}">' for n in range(1, 10)
    )
    ruta.write_text(
        '<?xml version="1.0"?><!DOCTYPE PSGAnnotation [<!ENTITY a0 "jaja">'
        + niveles
        + "]><PSGAnnotation><Nomenclature>&a9;</Nomenclature></PSGAnnotation>",
        encoding="utf-8",
    )

    ventana.open_scoring(ruta)

    assert ventana.acciones == ["importar el scoring"]
    assert "declara entidades de XML" in ventana.carteles[0]
    assert [ventana.session.scoring.get(i) for i in range(VENTANAS)] == antes


def test_exportar_con_una_extension_que_no_es_de_ningun_formato_avisa(
    ventana: MainWindow, tmp_path: Path
):
    ventana.export("scoring", tmp_path / "Scoring.json")

    assert ventana.carteles
    assert not (tmp_path / "Scoring.json").exists()


def test_ctrl_s_sigue_exportando_en_txt(ventana: MainWindow, dialogo_de_guardado):
    ventana.export_scoring_dialog()

    (propuesto, filtro), = dialogo_de_guardado["llamadas"]
    assert Path(propuesto).name == SCORING_FILENAME
    assert filtro == "Texto (*.txt)"


def test_exportar_propone_la_carpeta_del_registro(ventana: MainWindow, dialogo_de_guardado):
    """Hito 79: arrancaba en la carpeta desde donde se lanzó el programa, y
    con el nombre del pliego siempre igual, dos participantes exportados sin
    mirar quedaban uno encima del otro."""
    ventana.export_scoring_dialog("csv")

    (propuesto, _), = dialogo_de_guardado["llamadas"]
    assert Path(propuesto).parent == ventana.session.recording.file_path.parent


def test_importar_arranca_en_la_carpeta_del_registro(ventana: MainWindow, monkeypatch):
    carpetas: list[str] = []

    def responder(_padre, _titulo, carpeta, _filtro, *_a, **_k) -> tuple[str, str]:
        carpetas.append(carpeta)
        return "", ""

    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(responder))

    ventana.open_scoring_dialog()
    ventana.open_recording_dialog()

    registro = str(ventana.session.recording.file_path.parent)
    assert carpetas == [registro, registro]


@pytest.mark.parametrize("extension", ["csv", "edf", "xml"])
def test_cada_formato_propone_su_nombre_y_su_filtro(
    ventana: MainWindow, dialogo_de_guardado, extension: str
):
    ventana.export_scoring_dialog(extension)

    (propuesto, filtro), = dialogo_de_guardado["llamadas"]
    assert Path(propuesto).name == f"Scoring.{extension}"
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


def test_informacion_se_exporta_desde_el_menu_con_el_informe_de_sueno(
    ventana: MainWindow, tmp_path: Path, dialogo_de_guardado
):
    """Hito 79: Informacion.txt vuelve a «Archivo», y trae al final el
    informe de sueño con lo scoreado de verdad por la ventana."""
    for fase in (SleepStage.WAKE, SleepStage.N2, SleepStage.N2):
        ventana.score_current_window(fase)
    dialogo_de_guardado["respuesta"] = tmp_path / NOMBRES["information"]

    ventana.export_information_dialog()

    (propuesto, _), = dialogo_de_guardado["llamadas"]
    assert Path(propuesto).name == NOMBRES["information"]
    texto = (tmp_path / NOMBRES["information"]).read_text(encoding="utf-8")
    informe = texto.split("INFORME DE SUEÑO", 1)[1]
    assert "Tiempo total de sueño: 0 h 01 min 00,00 s" in informe
    assert "Latencia de sueño: 0 h 00 min 30,00 s" in informe
    assert not ventana.carteles


def test_anotaciones_se_exporta_desde_el_menu(
    ventana: MainWindow, tmp_path: Path, dialogo_de_guardado
):
    """Y cuenta como exportado: cerrar ya no pregunta por las anotaciones."""
    anotar_algo(ventana)
    dialogo_de_guardado["respuesta"] = tmp_path / NOMBRES["annotations"]

    ventana.export_annotations_dialog()

    (propuesto, _), = dialogo_de_guardado["llamadas"]
    assert Path(propuesto).name == NOMBRES["annotations"]
    assert "Spindle" in (tmp_path / NOMBRES["annotations"]).read_text(encoding="utf-8")
    assert ventana.work_guard.unexported() == []
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
        ventana.set_color_scheme(theme.NOCTURNO, remember=False)

        actual = ventana.open_button.icon().pixmap(32, 32).toImage()
        esperado = icon("abrir", theme.icon_ink(theme.NOCTURNO)).pixmap(32, 32).toImage()
        assert actual == esperado
    finally:
        ventana.set_color_scheme(anterior, remember=False)


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
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    ventana = create_main_window()

    try:
        ventana.export("scoring", tmp_path / "Scoring.txt")
    except PsgLabError as error:  # pragma: no cover - es lo que no debe pasar
        pytest.fail(f"export() dejó escapar {type(error).__name__}: {error}")


# -- Al abrir otro registro ---------------------------------------------------
#
# Lo que encontró la verificación de las herramientas: con un registro abierto
# y otro recién abierto, lo del primero seguía a la vista o en memoria.


def test_abrir_otro_registro_suelta_el_anterior(ventana: MainWindow, tmp_path: Path):
    """El anotador y la ocupación guardaban la sesión al apagarse, y con ella el
    registro entero: con dos noches grandes, el doble de memoria."""
    import gc
    import weakref

    for herramienta in ventana.tool_controller.tools:
        ventana.tool_controller.toggle(herramienta, True)
    for herramienta in ventana.tool_controller.tools:
        ventana.tool_controller.toggle(herramienta, False)
    anterior = weakref.ref(ventana.session.recording)

    ventana.open_recording(otro_registro(tmp_path))
    gc.collect()

    assert anterior() is None


def test_los_paneles_de_analisis_no_muestran_el_registro_anterior(
    ventana: MainWindow, elige_canal, tmp_path: Path
):
    """El espectro decía «Espectro de «C3»» sobre un registro sin C3, y la
    tabla de impedancias listaba los canales viejos con el informe de los
    nuevos."""
    elige_canal("C3", "C3", "permutation_entropy", "Delta")
    ventana.show_psd_dialog()
    ventana.show_complexity_dialog()
    ventana.show_connectivity_dialog()
    ventana.show_impedance_dialog()

    ventana.open_recording(otro_registro(tmp_path))

    assert ventana.psd_panel.channels() == []
    assert ventana.psd_panel.band_powers() == {}
    assert ventana.metric_panel.channels() == []
    assert ventana.connectivity_panel.axis_labels() == []
    for clave, titulo in ORDEN_DE_ANALISIS:
        assert ventana.docks[clave].windowTitle() == titulo
    assert ventana.impedance_panel.channels() == ["Fz", "Cz"]
    assert not ventana.carteles


def test_el_panel_de_filtros_es_del_registro_abierto(ventana: MainWindow, tmp_path: Path):
    """Conservaba los sugeridos del registro anterior: en uno de 100 Hz,
    «Aplicar» pedía el notch de 50 Hz y terminaba en un cartel."""
    ventana.show_filter_dialog()
    ventana.open_recording(otro_registro(tmp_path))

    ventana.filter_panel.boton_aplicar.click()

    ventana.wait_for_background()

    assert not ventana.carteles
    assert ventana.accion_señal_original.isEnabled()


def test_aplicar_sin_ningun_filtro_no_toca_la_señal(ventana_con_dos_eeg: MainWindow):
    """Reemplazaba la señal por una copia idéntica, decía «Se filtró la señal»
    y descartaba la ICA ya ajustada."""
    from psglab.ui.filter_panel import CAMPOS

    ventana = ventana_con_dos_eeg
    ventana.show_ica_dialog()
    ventana.wait_for_background()
    ventana.show_filter_dialog()
    tabla = ventana.filter_panel.tabla
    for fila in range(tabla.topLevelItemCount()):
        for columna in range(1, len(CAMPOS) + 1):
            tabla.topLevelItem(fila).setText(columna, "")
    antes = ventana.session.recording

    ventana.filter_panel.boton_aplicar.click()

    ventana.wait_for_background()

    assert ventana.session.recording is antes
    assert ventana.analysis_controller.ica is not None
    assert not ventana.accion_señal_original.isEnabled()
    assert len(ventana.carteles) == 1


# -- El trabajo sin exportar (hito 33) ----------------------------------------
#
# Hasta la auditoría del 19 de septiembre, cerrar la ventana o abrir otro
# registro descartaba el scoring sin preguntar. El cartel es modal, así que acá
# se lo contesta con `cartel_del_scoring`; el último test arma el de verdad.
#
# **Y las anotaciones cuentan igual**, desde el cierre del hito: el cartel
# miraba sólo el scoring, que es lo único que el menú exporta, así que una
# sesión con eventos anotados y ninguna fase puesta se cerraba sin preguntar.


@pytest.fixture
def cartel_del_scoring(monkeypatch):
    """Contesta el cartel con la respuesta que se fije y anota cada pregunta.

    Guarda también **qué estaba en juego** en cada una, que es lo que decide el
    texto del cartel y qué diálogos de guardado se abren.
    """
    estado: dict[str, object] = {"respuesta": "cancelar", "preguntas": [], "en_juego": []}

    def responder(_guardian: WorkGuard, al_hacer: str, en_juego: list[str]) -> str:
        estado["preguntas"].append(al_hacer)
        estado["en_juego"].append(list(en_juego))
        return str(estado["respuesta"])

    monkeypatch.setattr(WorkGuard, "ask", responder)
    return estado


def scorear_algo(ventana: MainWindow) -> None:
    from psglab.core.nomenclature import SleepStage

    ventana._go_to_window(1)
    ventana.score_current_window(SleepStage.N2)


def test_cerrar_sin_nada_scoreado_no_pregunta(ventana: MainWindow, cartel_del_scoring):
    ventana.show()

    assert ventana.close()
    assert cartel_del_scoring["preguntas"] == []


def test_cancelar_deja_la_ventana_abierta_con_el_scoring(
    ventana: MainWindow, cartel_del_scoring
):
    ventana.show()
    scorear_algo(ventana)

    assert not ventana.close()
    assert ventana.isVisible()
    assert cartel_del_scoring["preguntas"] == ["cerrar el programa"]
    assert ventana.session.scoring.scored_windows() == 1
    cartel_del_scoring["respuesta"] = "descartar"
    ventana.close()


def test_descartar_cierra(ventana: MainWindow, cartel_del_scoring):
    ventana.show()
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "descartar"

    assert ventana.close()


def test_exportar_escribe_el_scoring_y_despues_cierra(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    ventana.show()
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuesta"] = tmp_path / "noche"

    assert ventana.close()
    assert (tmp_path / "noche.txt").read_text(encoding="utf-8").splitlines()[2] == "2 0"


def test_cancelar_el_guardado_no_cierra(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado
):
    """Elegir «Exportar…» y después cancelar el diálogo es no haber exportado:
    cerrar igual perdería lo que el usuario quiso guardar."""
    ventana.show()
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"

    assert not ventana.close()
    cartel_del_scoring["respuesta"] = "descartar"
    ventana.close()


def test_un_guardado_que_falla_no_cierra(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    ventana.show()
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuesta"] = tmp_path / "no" / "existe" / "noche.txt"

    assert not ventana.close()
    assert len(ventana.carteles) == 1
    cartel_del_scoring["respuesta"] = "descartar"
    ventana.close()


def test_lo_ya_exportado_no_se_pregunta(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    ventana.show()
    scorear_algo(ventana)
    ventana.export("scoring", tmp_path / "Scoring.txt")

    assert ventana.close()
    assert cartel_del_scoring["preguntas"] == []


def test_abrir_otro_registro_pregunta_y_cancelar_conserva_la_sesion(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 3)
    scorear_algo(ventana)
    antes = ventana.session

    ventana.open_recording(otro)

    assert cartel_del_scoring["preguntas"] == ["abrir «sintetico.vhdr»"]
    assert ventana.session is antes
    assert ventana.session.scoring.scored_windows() == 1


def test_abrir_otro_registro_y_descartar_lo_abre(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 3)
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "descartar"

    ventana.open_recording(otro)

    assert ventana.session.n_windows == 3
    assert ventana.session.scoring.scored_windows() == 0


def test_abrir_otro_registro_y_exportar_guarda_antes_de_abrirlo(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 3)
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuesta"] = tmp_path / "Scoring.txt"

    ventana.open_recording(otro)

    assert (tmp_path / "Scoring.txt").exists()
    assert ventana.session.n_windows == 3


def test_un_registro_que_no_se_puede_abrir_no_pregunta(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    """Se pregunta después de leer: si el archivo nuevo está roto, la sesión
    anterior sigue y no hay nada que perder."""
    roto = tmp_path / "roto.edf"
    roto.write_bytes(b"0" * 300)
    scorear_algo(ventana)
    antes = ventana.session

    ventana.open_recording(roto)

    assert cartel_del_scoring["preguntas"] == []
    assert ventana.session is antes
    assert len(ventana.carteles) == 1


def escribir_un_scoring(ventana: MainWindow, destino: Path) -> Path:
    """Un archivo para importar después, con la sesión todavía sin scorear.

    Exportar marca el scoring como guardado, así que lo que se scoree **después**
    es trabajo sin exportar de verdad, no un efecto del armado del test.
    """
    ventana.export("scoring", destino)
    return destino


def test_importar_encima_pregunta_y_cancelar_conserva_el_scoring(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    """**La misma pérdida que abrir otro registro, por otro camino.** Importar
    reemplaza el scoring entero, y hasta este ítem no preguntaba nada."""
    archivo = escribir_un_scoring(ventana, tmp_path / "ajeno.txt")
    scorear_algo(ventana)

    ventana.open_scoring(archivo)

    assert cartel_del_scoring["preguntas"] == ["importar «ajeno.txt»"]
    assert ventana.session.scoring.scored_windows() == 1


def test_importar_y_descartar_reemplaza_el_scoring(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    archivo = escribir_un_scoring(ventana, tmp_path / "ajeno.txt")
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "descartar"

    ventana.open_scoring(archivo)

    assert ventana.session.scoring.scored_windows() == 0
    assert not ventana.carteles


def test_importar_y_exportar_guarda_lo_que_habia_antes(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    archivo = escribir_un_scoring(ventana, tmp_path / "ajeno.txt")
    scorear_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuesta"] = tmp_path / "mio.txt"

    ventana.open_scoring(archivo)

    assert (tmp_path / "mio.txt").read_text(encoding="utf-8").splitlines()[2] == "2 0"
    assert ventana.session.scoring.scored_windows() == 0


def test_importar_sobre_lo_ya_exportado_no_pregunta(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    scorear_algo(ventana)
    archivo = escribir_un_scoring(ventana, tmp_path / "mio.txt")

    ventana.open_scoring(archivo)

    assert cartel_del_scoring["preguntas"] == []
    assert ventana.session.scoring.scored_windows() == 1


def test_un_scoring_que_no_se_puede_leer_no_pregunta(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    """Se pregunta después de leer, como al abrir un registro: un archivo que
    no se puede importar no pisa nada, así que no hay nada que perder."""
    archivo = escribir_un_scoring(ventana, tmp_path / "roto.txt")
    cabecera = archivo.read_text(encoding="utf-8").splitlines()[0]
    archivo.write_text(
        "\n".join([cabecera, "no soy una ventana", ""]), encoding="utf-8"
    )
    scorear_algo(ventana)

    ventana.open_scoring(archivo)

    assert cartel_del_scoring["preguntas"] == []
    assert ventana.session.scoring.scored_windows() == 1
    assert len(ventana.carteles) == 1


def anotar_algo(ventana: MainWindow, cuantas: int = 1) -> None:
    """Marca eventos como los marca el anotador: sobre el conjunto de la sesión."""
    for numero in range(cuantas):
        ventana.session.annotations.add(
            Annotation("Spindle", onset_sample=100 * (numero + 1), duration_samples=50)
        )


def test_cerrar_con_anotaciones_y_nada_scoreado_pregunta(
    ventana: MainWindow, cartel_del_scoring
):
    """**El hueco que dejó el cartel del hito 33.** Miraba sólo el scoring, que
    es lo único que el menú exporta, así que una noche de eventos anotados sin
    ninguna fase puesta se cerraba sin preguntar nada."""
    ventana.show()
    anotar_algo(ventana, cuantas=3)

    assert not ventana.close()
    assert cartel_del_scoring["preguntas"] == ["cerrar el programa"]
    assert cartel_del_scoring["en_juego"] == [["annotations"]]
    cartel_del_scoring["respuesta"] = "descartar"
    ventana.close()


def test_el_cartel_nombra_lo_que_esta_en_juego(ventana: MainWindow, monkeypatch):
    """Decir «el scoring» sobre una sesión que sólo tiene anotaciones manda a
    buscar al lugar equivocado lo que se va a perder."""
    textos: list[str] = []

    def exec_sin_mostrar(cartel: QMessageBox) -> int:
        # Sin clic en ningún botón: `WorkGuard.ask()` devuelve
        # "cancelar", que acá no importa. Lo que se mira es el texto.
        textos.append(cartel.text())
        return 0

    monkeypatch.setattr(QMessageBox, "exec", exec_sin_mostrar)
    anotar_algo(ventana, cuantas=2)
    for en_juego in (["scoring"], ["annotations"], ["scoring", "annotations"]):
        ventana.work_guard.ask("cerrar el programa", en_juego)

    assert textos[0].startswith("El scoring de ")
    assert textos[1].startswith("Las 2 anotaciones de ")
    assert textos[2].startswith("El scoring y las 2 anotaciones de ")


def test_exportar_desde_el_cartel_guarda_las_anotaciones(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    """**Avisar de una pérdida sin ofrecer cómo evitarla es peor que no
    avisar**: Anotaciones.txt no está en el menú desde el hito 23, así que sin
    esto el cartel sería un callejón sin salida."""
    ventana.show()
    anotar_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuesta"] = tmp_path / NOMBRES["annotations"]

    assert ventana.close()
    escrito = (tmp_path / NOMBRES["annotations"]).read_text(encoding="utf-8")
    assert "Spindle" in escrito
    ((propuesto, _),) = dialogo_de_guardado["llamadas"]
    assert Path(propuesto).name == NOMBRES["annotations"]


def test_con_scoring_y_anotaciones_se_guardan_los_dos(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    """Un diálogo por cada cosa en juego, el scoring primero."""
    ventana.show()
    scorear_algo(ventana)
    anotar_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuestas"] = [
        tmp_path / NOMBRES["scoring"],
        tmp_path / NOMBRES["annotations"],
    ]

    assert ventana.close()
    assert cartel_del_scoring["en_juego"] == [["scoring", "annotations"]]
    assert [Path(propuesto).name for propuesto, _ in dialogo_de_guardado["llamadas"]] == [
        NOMBRES["scoring"],
        NOMBRES["annotations"],
    ]
    assert (tmp_path / NOMBRES["scoring"]).exists()
    assert "Spindle" in (tmp_path / NOMBRES["annotations"]).read_text(encoding="utf-8")


def test_cancelar_el_guardado_de_las_anotaciones_no_cierra(
    ventana: MainWindow, cartel_del_scoring, dialogo_de_guardado, tmp_path: Path
):
    """Con el scoring guardado y las anotaciones no, todavía hay algo que
    perder: cerrar igual sería perderlo después de haber elegido guardarlo."""
    ventana.show()
    scorear_algo(ventana)
    anotar_algo(ventana)
    cartel_del_scoring["respuesta"] = "exportar"
    dialogo_de_guardado["respuestas"] = [tmp_path / NOMBRES["scoring"], ""]

    assert not ventana.close()
    cartel_del_scoring["respuesta"] = "descartar"
    ventana.close()


def test_las_anotaciones_ya_exportadas_no_se_preguntan(
    ventana: MainWindow, cartel_del_scoring, tmp_path: Path
):
    ventana.show()
    anotar_algo(ventana)
    ventana.export("annotations", tmp_path / NOMBRES["annotations"])

    assert ventana.close()
    assert cartel_del_scoring["preguntas"] == []


def test_el_cartel_de_verdad_ofrece_las_tres_salidas(ventana: MainWindow, monkeypatch):
    """El de verdad, sin mostrarlo: se le hace clic a cada botón.

    **Exportar es el botón por omisión y Escape es cancelar**: un Enter apurado
    no puede costar la noche.
    """
    visto: dict[str, object] = {}

    def exec_sin_mostrar(cartel: QMessageBox) -> int:
        botones = {b.text(): b for b in cartel.buttons()}
        visto["botones"] = set(botones)
        visto["por_omision"] = cartel.defaultButton().text()
        visto["escape"] = cartel.escapeButton().text()
        visto["texto"] = cartel.informativeText()
        botones[visto["elegir"]].click()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", exec_sin_mostrar)
    for texto, respuesta in (
        ("Exportar…", "exportar"),
        ("Descartar", "descartar"),
        ("Cancelar", "cancelar"),
    ):
        visto["elegir"] = texto
        assert (
            ventana.work_guard.ask("cerrar el programa", ["scoring"])
            == respuesta
        )

    assert visto["botones"] == {"Exportar…", "Descartar", "Cancelar"}
    assert visto["por_omision"] == "Exportar…"
    assert visto["escape"] == "Cancelar"
    assert "cerrar el programa" in visto["texto"]


# -- Un archivo que trae menos de lo que declara (hito 33) --------------------


@pytest.fixture
def avisos_de_lectura(monkeypatch) -> list[list[str]]:
    """Anota cada cartel de avisos en vez de mostrarlo: es modal."""
    mostrados: list[list[str]] = []
    monkeypatch.setattr(
        MainWindow, "_mostrar_avisos_de_lectura", lambda _v, avisos: mostrados.append(avisos)
    )
    return mostrados


def test_abrir_un_edf_truncado_lo_abre_y_lo_dice(
    ventana: MainWindow, avisos_de_lectura, tmp_path: Path
):
    """Media noche se veía igual que una noche entera. Ahora se abre lo que hay
    y un cartel dice cuánto falta."""
    edf = escribir_edf(tmp_path / "truncado", segundos=90)
    # Cabecera de cuatro bloques de 256 bytes; registros de 600 bytes.
    edf.write_bytes(edf.read_bytes()[: 1024 + 40 * 600 + 300])

    ventana.open_recording(edf)

    assert ventana.session.recording.duration_seconds == pytest.approx(40.0)
    assert len(avisos_de_lectura) == 1
    assert "40 s" in avisos_de_lectura[0][0] and "1 min 30 s" in avisos_de_lectura[0][0]
    assert not ventana.carteles


def test_un_registro_entero_no_muestra_avisos(
    ventana: MainWindow, avisos_de_lectura, tmp_path: Path
):
    ventana.open_recording(escribir_edf(tmp_path / "entero", segundos=90))

    assert avisos_de_lectura == []
    assert ventana.session.recording.duration_seconds == pytest.approx(90.0)


# -- Un registro con muestras sin valor (hito 33) ----------------------------


def test_abrir_un_registro_con_nan_lo_abre_y_lo_dice(
    ventana: MainWindow, avisos_de_lectura, tmp_path: Path
):
    """Un NaN no se ve: la curva se corta y nada lo distingue de una pausa.

    La auditoría metió diez muestras y después de filtrar eran unas treinta
    mil, con la PSD de esa época entera sin valor y ningún cartel en el medio.
    """
    vhdr = escribir_brainvision(
        tmp_path / "rotas", segundos=WINDOW_SECONDS * 3, sin_valor={"C3": range(10, 20)}
    )

    ventana.open_recording(vhdr)

    assert ventana.session.recording.non_finite_channels() == {"C3": 10}
    (avisos,) = avisos_de_lectura
    assert "C3" in avisos[0] and "sin valor" in avisos[0]
    assert not ventana.carteles


def test_un_registro_sano_no_avisa_de_muestras_sin_valor(
    ventana: MainWindow, avisos_de_lectura, tmp_path: Path
):
    ventana.open_recording(
        escribir_brainvision(tmp_path / "sano", segundos=WINDOW_SECONDS * 3)
    )

    assert avisos_de_lectura == []


# -- Las dos barras dicen qué registro está abierto (hito 36) ----------------


def test_la_barra_de_menu_identifica_el_registro(ventana: MainWindow):
    """**No estaba en ningún lado.** Con dos registros parecidos —la misma
    noche filtrada y sin filtrar— no había forma de saber cuál se miraba."""
    resumen = ventana.recording_summary.text()

    assert ventana.session.recording.file_path.name in resumen
    assert "canales" in resumen


def test_sin_registro_todo_lo_dice_con_las_mismas_palabras(qt_app):
    """Hito 65: eran «Sin registro» y «Sin registro abierto» para el mismo
    estado, según dónde se mirara."""
    vacia = create_main_window()
    try:
        assert vacia.recording_summary.text() == "Sin registro abierto"
        assert vacia.statusBar().currentMessage() == "Sin registro abierto"
        assert vacia.navigation._posicion.text() == "Sin registro abierto"
        assert vacia.scoring_panel.status() == "Sin registro abierto"
        # El contexto lo dice sólo al lector de pantalla, y recién cuando le
        # llegan ventanas: se pregunta a la función que arma ese texto.
        assert accessible_summary(()) == "Sin registro abierto"
    finally:
        vacia.close()


def test_la_amplitud_de_cada_canal_se_lee_en_su_carril(ventana: MainWindow):
    """**La barra dejó de decirla** (hito 44), y no se perdió nada: la escala
    de un canal se lee en el canalón, al lado de su nombre y contra su señal.

    La barra la mostró desde el hito 36, y desde el 38 —cuando cada clase pasó
    a abrir con su escala— lo que mostraba era casi siempre un rango, «37–1025
    µV», que no es la amplitud de ningún canal: es el mínimo de uno y el máximo
    de otro."""
    ventana.set_amplitude_scale(200.0)

    detalles = [carril.detail for carril in ventana.signal_view.channel_axis.lanes()]
    assert detalles
    assert all(detalle == "200 µV" for detalle in detalles)


def test_la_escala_personalizada_sin_canales_visibles_no_rompe(
    ventana: MainWindow, monkeypatch
):
    """Hito 79: preguntaba la escala del primer canal visible, y sin ninguno
    elevaba `IndexError`, que salía como el cartel de los errores del
    programa. Arranca en la de fábrica."""
    from psglab.config import DEFAULT_SCALE_UV

    pedida: list[float] = []

    def responder(*args: object) -> tuple[float, bool]:
        pedida.append(float(args[3]))
        return 50.0, True

    monkeypatch.setattr(QInputDialog, "getDouble", staticmethod(responder))
    ventana._set_visible_channels([])

    ventana.ask_amplitude_scale()

    assert pedida == [DEFAULT_SCALE_UV]


def test_la_escala_personalizada_arranca_en_la_del_canal_seleccionado(
    ventana: MainWindow, monkeypatch
):
    """Es a ése al que se le va a aplicar: la del primero visible no dice
    nada si el seleccionado es otro."""
    segundo = ventana.session.visible_channels[1]
    ventana.session.set_scale_uv(segundo, 321.0)
    ventana._set_selected_channels([segundo])
    pedida: list[float] = []

    def responder(*args: object) -> tuple[float, bool]:
        pedida.append(float(args[3]))
        return 0.0, False

    monkeypatch.setattr(QInputDialog, "getDouble", staticmethod(responder))

    ventana.ask_amplitude_scale()

    assert pedida == [321.0]


def test_los_extremos_del_registro_llegan_a_la_franja(ventana: MainWindow):
    inicio = ventana.session.recording.start_time

    assert ventana.navigation._hora_inicial.text() == inicio.strftime("%H:%M")
    assert ventana.navigation._hora_final.text() != ""


def test_el_boton_de_descartar_lleva_la_tinta_de_lo_que_destruye(
    ventana: MainWindow, monkeypatch
):
    """**El rol no alcanza.** `DestructiveRole` le dice a Qt dónde ubicar el
    botón y con qué tecla responde, no de qué color pintarlo: en Windows sale
    idéntico a «Cancelar». La tinta la pone el esquema por una propiedad."""
    vistos: dict[str, bool] = {}

    def espiar(cartel):
        vistos.update(
            {
                boton.text(): bool(boton.property(theme.DESTRUCTIVO_PROPERTY))
                for boton in cartel.buttons()
            }
        )
        return 0

    monkeypatch.setattr(QMessageBox, "exec", espiar)
    ventana.work_guard.ask("cerrar el programa", ["scoring"])

    assert vistos["Descartar"] is True
    assert vistos["Cancelar"] is False


def test_scorear_actualiza_la_fase_que_muestra_la_ubersicht(ventana: MainWindow):
    """**La Übersicht cachea sus ventanas** y las rearma al cambiar de época,
    no al scorear: sin pedirle que se rederive, el chip de la fase recién
    puesta no aparecía hasta la próxima flecha. Es el mismo cuidado que ya
    tenía anotar, y el mismo motivo."""
    from psglab.tools.overview import OverviewTool

    contexto = ventana.tool_controller.tools["overview"]
    assert isinstance(contexto, OverviewTool)

    ventana.score_current_window(SleepStage.N2)

    # Puntuar pasa a la siguiente (hito 64): la recién puntuada es la 0.
    puntuada = [v for v in contexto.windows() if v.index == 0][0]
    assert puntuada.stage is SleepStage.N2


# -- La copia de recuperación (hito 79) -------------------------------------------


def test_la_ventana_de_los_tests_no_escribe_copias(qt_app):
    """Sólo la del usuario, que prende `apply_saved_preferences()`: la suite no
    escribe en el perfil de quien la corre."""
    assert create_main_window().work_guard.recovery_path() is None


def test_despues_de_un_corte_se_recupera_la_noche(qt_app, tmp_path, monkeypatch):
    """De punta a punta, por la ventana: se scorea, el programa se corta sin
    preguntar nada y al reabrir el mismo registro se vuelve a donde estaba."""
    monkeypatch.setattr(WorkGuard, "ask_recovery", lambda *_a: True)
    perfil = tmp_path / "perfil"
    vhdr = escribir_brainvision(tmp_path / "registro", segundos=WINDOW_SECONDS * VENTANAS)

    antes = create_main_window()
    antes.work_guard.enable_recovery(perfil)
    antes.open_recording(vhdr)
    antes.score_current_window(SleepStage.N2)
    antes.score_current_window(SleepStage.N3)
    antes.work_guard.save_recovery()
    # El corte: nadie cierra la ventana ni contesta ningún cartel.

    despues = create_main_window()
    despues.work_guard.enable_recovery(perfil)
    despues.open_recording(vhdr)

    scoring = despues.session.scoring
    assert [scoring.get(i).stage for i in range(2)] == [SleepStage.N2, SleepStage.N3]
    assert despues.session.current_window == 2
    assert despues.statusBar().currentMessage() == (
        "Se recuperó el trabajo que no se había exportado."
    )
