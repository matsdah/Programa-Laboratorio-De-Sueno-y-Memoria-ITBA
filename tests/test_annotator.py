"""Tests del anotador de eventos sobre la señal.

Resuelve una de las carencias que motivan el proyecto: en los programas
actuales del laboratorio no se puede anotar la señal (V1_F de "Anotación").

**El test que más importa es el de la conversión a muestras.** Los eventos de
mouse llegan en segundos desde el inicio de la ventana y `Anotaciones.txt`
guarda muestras del registro. Calcular la posición como `ventana * 30 * fs`
deja la anotación en la ventana de al lado cuando la frecuencia no es redonda,
y nada lo hace visible: la banda se dibuja igual, sólo que en otro lado.

La herramienta **no abre ningún diálogo**: no conoce Qt y no puede. Deja el
tramo listo y la ventana principal pregunta la clase. Eso es lo que permite
testear el gesto entero sin abrir una ventana.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.core.windows import seconds_to_sample_absolute
from psglab.tools.annotator import AnnotatorTool, annotation_bands
from psglab.tools.base import SpanOverlay
from psglab.utils.errors import PsgLabError

FRECUENCIA = 100.0


@pytest.fixture
def sesion() -> Session:
    """Tres ventanas, para poder anotar en la del medio.

    Anotar siempre en la primera escondería los errores de conversión: con
    `window_index = 0` sobra el término que puede estar mal.
    """
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, 9000)),
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(3, Nomenclature.AASM), AnnotationSet())


@pytest.fixture
def anotador(sesion: Session) -> AnnotatorTool:
    tool = AnnotatorTool()
    tool.activate(sesion)
    return tool


def seleccionar(tool: AnnotatorTool, desde: float, hasta: float) -> None:
    """Un gesto completo de selección, en **segundos absolutos del registro**.

    Eran segundos dentro de la ventana de 30 s. Cambió con la escala de tiempo
    libre: con una época y una página que ya no coinciden, el único origen
    común es el inicio del registro.
    """
    tool.on_mouse_press(desde, 0.0, "left")
    tool.on_mouse_move(hasta, 0.0)
    tool.on_mouse_release(hasta, 0.0, "left")


# -- La conversión a muestras ------------------------------------------------


def test_la_seleccion_se_convierte_a_muestras_del_registro(
    anotador: AnnotatorTool, sesion: Session
):
    """**El test que atrapa el error caro.**

    El segundo 35 del registro es la muestra 3500 a 100 Hz, y cae dentro de la
    época 1. Con el contrato viejo había que sumar el segundo 5 sobre el borde
    de esa época, que es la cuenta donde fallaban 240 de 960 ventanas a
    256,125 Hz; ahora hay un solo redondeo y esa deriva no puede existir.
    """
    sesion.go_to_window(1)
    seleccionar(anotador, 35.0, 38.0)
    assert anotador.pending_selection_samples == (3500, 300)


def test_la_conversion_es_la_de_windows_y_no_una_cuenta_a_mano(
    anotador: AnnotatorTool, sesion: Session
):
    """Se compara contra `core.windows`, que es el único lugar donde el
    proyecto convierte entre unidades."""
    sesion.go_to_window(2)
    seleccionar(anotador, 63.0, 64.0)
    inicio, _ = anotador.pending_selection_samples
    assert inicio == seconds_to_sample_absolute(63.0, FRECUENCIA)


@pytest.mark.parametrize("frecuencia", [100.0, 256.125])
def test_la_conversion_no_deriva_con_una_frecuencia_no_redonda(frecuencia: float):
    """**El caso donde el contrato viejo fallaba.**

    Con 256,125 Hz, sumar un desplazamiento sobre el borde de una época se
    escapaba a la siguiente en 240 de 960 ventanas: es el hallazgo que
    documenta `core.windows.seconds_to_sample()`. Con segundos absolutos hay un
    solo redondeo, así que la cuenta cierra en cualquier época.

    Arma su propia sesión porque la fixture está fijada a 100 Hz, que es
    justamente la frecuencia redonda donde el error no aparece.
    """
    ventanas = 10
    registro = Recording(
        file_path=Path("noche.edf"),
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, int(ventanas * 30 * frecuencia))),
        sampling_rate=frecuencia,
    )
    sesion = Session(registro, Scoring(ventanas, Nomenclature.AASM), AnnotationSet())
    tool = AnnotatorTool()
    tool.activate(sesion)
    sesion.go_to_window(7)

    segundos = 7 * 30.0 + 11.0
    seleccionar(tool, segundos, segundos + 1.0)

    inicio, _ = tool.pending_selection_samples
    assert inicio == seconds_to_sample_absolute(segundos, frecuencia)


def test_seleccionar_al_reves_da_lo_mismo(anotador: AnnotatorTool):
    """Arrastrar de derecha a izquierda marca el mismo tramo."""
    seleccionar(anotador, 8.0, 5.0)
    assert anotador.pending_selection_samples == (500, 300)


def test_una_seleccion_sin_ancho_no_es_un_evento(anotador: AnnotatorTool):
    """El pliego pide marcar el evento con una banda, y `AnnotationSet` rechaza
    la duración cero por lo mismo: una banda sin ancho no se dibuja ni se
    encuentra nunca."""
    seleccionar(anotador, 5.0, 5.0)
    assert anotador.pending_selection_samples is None


# -- Crear, listar y borrar --------------------------------------------------


def test_la_anotacion_creada_va_al_conjunto_de_la_sesion(
    anotador: AnnotatorTool, sesion: Session
):
    """La herramienta es el gesto, no el dato: las anotaciones viven en la
    sesión, que es lo que el exportador va a leer."""
    anotador.add_label("Huso")
    seleccionar(anotador, 5.0, 8.0)
    creada = anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    assert creada in sesion.annotations.all()
    assert creada.label == "Huso"


def test_crear_la_anotacion_limpia_la_seleccion_pendiente(anotador: AnnotatorTool):
    """Si no, el próximo diálogo ofrecería anotar de nuevo el mismo tramo."""
    anotador.add_label("Huso")
    seleccionar(anotador, 5.0, 8.0)
    anotador.create_annotation("Huso", *anotador.pending_selection_samples)
    assert anotador.pending_selection_samples is None


def test_el_usuario_puede_crear_una_clase_nueva(
    anotador: AnnotatorTool, sesion: Session
):
    """El pliego lo pide explícitamente: la lista no es cerrada."""
    anotador.add_label("Artefacto raro")
    assert "Artefacto raro" in sesion.annotations.labels()


def test_una_anotacion_se_puede_borrar(anotador: AnnotatorTool, sesion: Session):
    anotador.add_label("Huso")
    seleccionar(anotador, 5.0, 8.0)
    creada = anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    anotador.delete_annotation(creada)
    assert sesion.annotations.all() == []



# -- Borrar con el clic derecho -----------------------------------------------


def anotar(sesion: Session, desde: float, hasta: float, clase: str = "Arousal") -> Annotation:
    anotacion = Annotation(
        label=clase,
        onset_sample=seconds_to_sample_absolute(desde, FRECUENCIA),
        duration_samples=seconds_to_sample_absolute(hasta - desde, FRECUENCIA),
    )
    sesion.annotations.add(anotacion)
    return anotacion


def test_encuentra_la_anotacion_bajo_el_clic(anotador: AnnotatorTool, sesion: Session):
    anotacion = anotar(sesion, 35.0, 38.0)
    assert anotador.annotation_at(36.5) == anotacion


def test_donde_no_hay_anotacion_no_encuentra_nada(
    anotador: AnnotatorTool, sesion: Session
):
    """Un clic derecho en la señal limpia no puede borrar nada."""
    anotar(sesion, 35.0, 38.0)
    assert anotador.annotation_at(34.0) is None
    # El final es abierto, igual que `AnnotationSet.in_range()`.
    assert anotador.annotation_at(38.0) is None


def test_entre_dos_superpuestas_elige_la_mas_corta(
    anotador: AnnotatorTool, sesion: Session
):
    """La larga se puede señalar a los costados de la corta; la corta, en
    ningún otro lugar."""
    anotar(sesion, 30.0, 50.0, "Arousal")
    corta = anotar(sesion, 40.0, 41.0, "Spindle")
    assert anotador.annotation_at(40.5) == corta


def test_sin_registro_no_encuentra_nada():
    assert AnnotatorTool().annotation_at(5.0) is None


# -- Las bandas, con la herramienta apagada ------------------------------------


def test_las_bandas_no_dependen_de_la_herramienta(sesion: Session):
    """Una anotación es un dato del registro: la ventana la dibuja esté o no
    activa «Anotar», así que las bandas no pueden pedir una herramienta
    activada."""
    anotar(sesion, 5.0, 8.0)
    (banda,) = annotation_bands(sesion)
    assert (banda.start_seconds, banda.end_seconds) == (5.0, 8.0)


def test_la_herramienta_dibuja_las_mismas_bandas(
    anotador: AnnotatorTool, sesion: Session
):
    anotar(sesion, 5.0, 8.0)
    assert tuple(anotador.overlays()) == annotation_bands(sesion)


def test_anotar_sin_registro_abierto_es_un_error_del_programa():
    """La ventana principal atrapa `PsgLabError`; un `AttributeError` sobre
    `None` le llegaría al investigador como una traza."""
    tool = AnnotatorTool()
    for accion in (
        lambda: tool.create_annotation("Huso", 0, 10),
        lambda: tool.add_label("Huso"),
        lambda: tool.delete_annotation(Annotation("Huso", 0, 10)),
    ):
        with pytest.raises(PsgLabError):
            accion()


# -- Lo que se dibuja --------------------------------------------------------


def test_la_seleccion_en_curso_se_dibuja_antes_de_soltar(anotador: AnnotatorTool):
    """El usuario tiene que ver qué está marcando antes de que se le pregunte
    qué es."""
    anotador.on_mouse_press(5.0, 0.0, "left")
    anotador.on_mouse_move(8.0, 0.0)
    (banda,) = anotador.overlays()
    assert isinstance(banda, SpanOverlay)
    assert banda.start_seconds == 5.0
    assert banda.end_seconds == 8.0
    assert banda.label == ""


def test_las_anotaciones_vuelven_en_segundos_absolutos(
    anotador: AnnotatorTool, sesion: Session
):
    """Se guardan en muestras y el visualizador entiende segundos.

    **Vuelven en segundos del registro y no de la ventana**: el eje del
    visualizador está en absolutos desde la escala de tiempo libre, así que una
    banda en coordenadas de época se dibujaría en otro lado.
    """
    sesion.go_to_window(1)
    anotador.add_label("Huso")
    seleccionar(anotador, 35.0, 38.0)
    anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    (banda,) = anotador.overlays()
    assert banda.start_seconds == pytest.approx(35.0)
    assert banda.end_seconds == pytest.approx(38.0)


def test_una_anotacion_fuera_de_la_pagina_no_se_dibuja(
    anotador: AnnotatorTool, sesion: Session
):
    """Cada pantalla muestra lo suyo: si no, las bandas se apilarían todas en la
    primera.

    **El filtro es la página y no la época.** Con la página de 30 s las dos
    coinciden y esto se comporta igual que antes; lo que cambia es el test de
    abajo, que antes no podía existir.
    """
    sesion.go_to_window(1)
    anotador.add_label("Huso")
    seleccionar(anotador, 35.0, 38.0)
    anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    sesion.go_to_window(0)
    assert list(anotador.overlays()) == []


def test_con_una_pagina_larga_se_dibujan_las_anotaciones_de_otras_epocas(
    anotador: AnnotatorTool, sesion: Session
):
    """**Es lo que hacía inaceptable el contrato viejo.**

    Filtrando por la época, una página de cuatro horas dibujaría las bandas de
    una sola de las 480 que hay en pantalla y las otras 479 aparecerían vacías
    aunque tengan eventos: la herramienta mintiendo sobre lo que hay.
    """
    sesion.go_to_window(1)
    anotador.add_label("Huso")
    seleccionar(anotador, 35.0, 38.0)
    anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    sesion.go_to_window(0)
    sesion.set_viewport(sesion.viewport.with_span(300.0))

    assert len(anotador.overlays()) == 1


def test_la_banda_lleva_el_color_de_su_clase(
    anotador: AnnotatorTool, sesion: Session
):
    """El pliego pide una banda de color; el color lo asigna `AnnotationSet` por
    orden de registro, así que es determinístico."""
    anotador.add_label("Huso")
    seleccionar(anotador, 5.0, 8.0)
    anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    (banda,) = anotador.overlays()
    assert banda.color == sesion.annotations.color_of("Huso")


def test_desactivarla_conserva_las_anotaciones(
    anotador: AnnotatorTool, sesion: Session
):
    """Viven en el `AnnotationSet` de la sesión, no en la herramienta."""
    anotador.add_label("Huso")
    seleccionar(anotador, 5.0, 8.0)
    anotador.create_annotation("Huso", *anotador.pending_selection_samples)

    anotador.deactivate()
    assert len(sesion.annotations.all()) == 1



def test_desactivarla_suelta_la_sesion(anotador: AnnotatorTool, sesion: Session):
    """Conservarla mantenía vivo el registro anterior después de abrir otro.
    Las anotaciones no se pierden: viven en la sesión, no en la herramienta."""
    anotar(sesion, 5.0, 8.0)
    anotador.deactivate()
    # Ningún atributo la guarda. No se prueba con un `weakref` porque la
    # fixture de pytest la sigue sosteniendo; eso lo mide `test_entrega.py`
    # con dos registros de verdad.
    assert all(valor is not sesion for valor in vars(anotador).values())


def test_desactivarla_descarta_la_seleccion_a_medias(anotador: AnnotatorTool):
    """Un tramo marcado y sin clase no sobrevive a apagar la herramienta: el
    usuario ya se fue a otra cosa."""
    anotador.on_mouse_press(5.0, 0.0, "left")
    anotador.on_mouse_move(8.0, 0.0)
    anotador.deactivate()
    assert list(anotador.overlays()) == []
    assert anotador.pending_selection_samples is None


def test_el_mouse_sobre_la_herramienta_desactivada_no_selecciona():
    tool = AnnotatorTool()
    tool.on_mouse_press(5.0, 0.0, "left")
    tool.on_mouse_move(8.0, 0.0)
    assert list(tool.overlays()) == []


def test_solo_el_boton_izquierdo_selecciona(anotador: AnnotatorTool):
    """El derecho queda libre para el menú contextual de la ventana."""
    anotador.on_mouse_press(5.0, 0.0, "right")
    anotador.on_mouse_move(8.0, 0.0)
    assert list(anotador.overlays()) == []


def test_es_exclusiva_porque_se_queda_con_el_arrastre():
    assert AnnotatorTool.exclusive is True
