"""Tests de la sesión de trabajo: navegación, canales y amplitud.

`Session` es la **única superficie de acceso de las seis herramientas**:
`Tool.activate(session)` documenta que ninguna recibe el visualizador ni nada de
Qt. Nueve módulos la importan. Lo que se fije acá es lo que van a consumir los
hitos 6 y 7, así que estos tests no verifican un detalle interno: verifican el
contrato del que cuelga media Parte 1.

Y son la prueba de que la capa de negocio se puede testear sin abrir una
ventana, que es el motivo por el que `Session` vive en `core/` y no en `ui/`.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.config import DEFAULT_SCALE_UV, MAX_SCALE_UV, MIN_SCALE_UV
from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import Nomenclature
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session

from conftest import VENTANAS_SINTETICAS
from psglab.utils.errors import (
    ChannelNotFoundError,
    ScoringMismatchError,
    WindowOutOfRangeError,
)

#: Clase de cada canal de la fixture `channel_names`, en su mismo orden.
CLASES = (ChannelKind.EEG, ChannelKind.EEG, ChannelKind.EOG, ChannelKind.EMG)


@pytest.fixture
def recording(synthetic_signal, channel_names, sampling_rate) -> Recording:
    """Registro sintético de cuatro canales: exactamente 20 ventanas."""
    canales = [
        Channel(name=nombre, kind=clase, unit="µV", index=i)
        for i, (nombre, clase) in enumerate(zip(channel_names, CLASES))
    ]
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=canales,
        data=synthetic_signal,
        sampling_rate=sampling_rate,
    )


@pytest.fixture
def session(recording) -> Session:
    """Sesión recién abierta sobre el registro sintético."""
    return Session(
        recording=recording,
        scoring=Scoring(n_windows=VENTANAS_SINTETICAS, nomenclature=Nomenclature.AASM),
        annotations=AnnotationSet(),
    )


# -- Que las tres piezas hablen del mismo registro --------------------------


def test_un_scoring_de_otro_registro_no_se_puede_abrir(recording):
    """El chequeo que le faltaba a la sesión, y el motivo por el que existe.

    Las tres piezas llegan sueltas y nada garantizaba que fueran del mismo
    archivo. Un scoring importado de otro registro daría un histograma de largo
    equivocado y dejaría ventanas imposibles de scorear, **sin ningún error
    visible**. Acá es donde se juntan por primera vez.
    """
    with pytest.raises(ScoringMismatchError):
        Session(recording, Scoring(VENTANAS_SINTETICAS - 1, Nomenclature.AASM), AnnotationSet())


def test_un_scoring_mas_largo_que_el_registro_tampoco(recording):
    """Falla en las dos direcciones, no sólo cuando falta."""
    with pytest.raises(ScoringMismatchError):
        Session(recording, Scoring(VENTANAS_SINTETICAS + 1, Nomenclature.AASM), AnnotationSet())


def test_las_tres_piezas_quedan_accesibles(session, recording):
    """Es el único camino por el que las herramientas llegan a lo que hay abierto."""
    assert session.recording is recording
    assert session.scoring.n_windows == VENTANAS_SINTETICAS
    assert session.annotations.all() == []


def test_lo_que_hay_abierto_es_de_solo_lectura(session):
    """Cambiar de registro no es mutar la sesión: es abrir otra."""
    for propiedad in ("recording", "scoring", "annotations"):
        with pytest.raises(AttributeError):
            setattr(session, propiedad, None)


# -- Navegación (V1_F de "Navegación") --------------------------------------


def test_la_sesion_arranca_en_la_primera_ventana(session):
    assert session.current_window == 0
    assert session.n_windows == VENTANAS_SINTETICAS


def test_la_cantidad_de_ventanas_sale_del_registro(session):
    """Diez minutos a 256 Hz son exactamente veinte ventanas de 30 segundos."""
    assert session.n_windows == session.scoring.n_windows


def test_se_puede_saltar_a_una_ventana_lejana(session):
    """Es a donde llega el clic sobre el histograma (V4_F)."""
    session.go_to_window(15)
    assert session.current_window == 15


@pytest.mark.parametrize("indice", [VENTANAS_SINTETICAS, 999, -1])
def test_saltar_fuera_del_registro_falla(session, indice):
    """El −1 no es paranoia.

    `core/windows.py` documenta que sus conversiones devuelven números negativos
    **en silencio**, y nombra a `go_to_window` como su guarda. Un índice negativo
    que pasara de acá terminaría dibujando el final de la noche como si fuera el
    principio.
    """
    with pytest.raises(WindowOutOfRangeError):
        session.go_to_window(indice)


def test_avanzar_y_retroceder_mueven_de_a_una(session):
    session.next_window()
    session.next_window()
    assert session.current_window == 2
    session.previous_window()
    assert session.current_window == 1


def test_en_la_ultima_ventana_avanzar_no_hace_nada(session):
    """No elevar en el borde es deliberado.

    Quien mantiene apretada la flecha derecha llega al final y se queda ahí; un
    error en el borde convertiría un gesto normal en un fallo.
    """
    session.go_to_window(VENTANAS_SINTETICAS - 1)
    session.next_window()
    assert session.current_window == VENTANAS_SINTETICAS - 1


def test_en_la_primera_ventana_retroceder_no_hace_nada(session):
    session.previous_window()
    assert session.current_window == 0


# -- Canales visibles y seleccionados ---------------------------------------


def test_arranca_con_todos_los_canales_visibles(session, channel_names):
    """En el orden del archivo.

    El subconjunto inicial que pide V1_P —ojos, C3, C4 y EMG— necesita la
    detección de clase de canal, que es del hito 4: ese default es de la
    interfaz, no de `core/`.
    """
    assert session.visible_channels == channel_names
    assert session.selected_channels == []


def test_se_puede_elegir_qué_canales_se_ven_y_en_qué_orden(session):
    session.set_visible_channels(["EMG-menton", "C3"])
    assert session.visible_channels == ["EMG-menton", "C3"]


@pytest.mark.parametrize("metodo", ["set_visible_channels", "set_selected_channels"])
def test_pedir_un_canal_que_no_existe_falla(session, metodo):
    """Los dos ejes validan.

    En el esqueleto sólo uno de los dos mensajes decía "validar"; la asimetría
    parecía un descuido de redacción y no una decisión.
    """
    with pytest.raises(ChannelNotFoundError):
        getattr(session, metodo)(["Fz"])


def test_la_seleccion_no_tiene_que_estar_visible(session):
    """Son ejes distintos y el pliego no los ata.

    Seleccionar un canal y después ocultarlo deja su escala cambiando aunque no
    se vea, y eso es coherente: al volver a mostrarlo aparece como el usuario lo
    dejó.
    """
    session.set_selected_channels(["EOG-izq"])
    session.set_visible_channels(["C3", "C4"])
    assert session.selected_channels == ["EOG-izq"]


@pytest.mark.parametrize("propiedad", ["visible_channels", "selected_channels"])
def test_las_listas_de_canales_son_copias(session, propiedad):
    """Prestarle la interna a la interfaz la dejaría reordenar sin el setter."""
    prestada = getattr(session, propiedad)
    prestada.append("inventado")
    assert "inventado" not in getattr(session, propiedad)


# -- Amplitud (V2_P, V5_F de "Visualización") -------------------------------


def test_todos_los_canales_arrancan_con_la_escala_por_defecto(session, channel_names):
    for nombre in channel_names:
        assert session.scale_uv(nombre) == pytest.approx(DEFAULT_SCALE_UV)


def test_la_flecha_arriba_hace_que_el_canal_represente_menos_microvoltios(session):
    """La decisión menos obvia del módulo, y por eso la que más conviene fijar.

    `scale_uv` es cuántos µV representa la altura del canal. Para que la señal
    se dibuje **más grande**, esa misma altura tiene que representar **menos**
    µV. Subir el número achicaría la onda, que es lo contrario de lo que espera
    quien aprieta la flecha "Arriba".
    """
    antes = session.scale_uv("C3")
    session.increase_amplitude()
    assert session.scale_uv("C3") < antes


def test_la_flecha_abajo_hace_lo_contrario(session):
    antes = session.scale_uv("C3")
    session.decrease_amplitude()
    assert session.scale_uv("C3") > antes


def test_subir_y_bajar_vuelve_al_punto_de_partida(session):
    """El paso es un factor, así que las dos flechas se cancelan."""
    session.increase_amplitude()
    session.decrease_amplitude()
    assert session.scale_uv("C3") == pytest.approx(DEFAULT_SCALE_UV)


def test_sin_seleccion_la_amplitud_llega_a_todos_los_visibles(session):
    session.set_visible_channels(["C3", "C4"])
    session.increase_amplitude()
    assert session.scale_uv("C3") < DEFAULT_SCALE_UV
    assert session.scale_uv("C4") < DEFAULT_SCALE_UV


def test_con_seleccion_la_amplitud_llega_sólo_a_los_seleccionados(session):
    """Es V5_F: sin esto, la selección no significaría nada."""
    session.set_selected_channels(["C4"])
    session.increase_amplitude()
    assert session.scale_uv("C4") < DEFAULT_SCALE_UV
    assert session.scale_uv("C3") == pytest.approx(DEFAULT_SCALE_UV)


def test_la_escala_no_baja_del_tope_inferior(session):
    """Los topes existen para que no se pueda dejar la pantalla inutilizable."""
    for _ in range(200):
        session.increase_amplitude()
    assert session.scale_uv("C3") == pytest.approx(MIN_SCALE_UV)


def test_la_escala_no_sube_del_tope_superior(session):
    for _ in range(200):
        session.decrease_amplitude()
    assert session.scale_uv("C3") == pytest.approx(MAX_SCALE_UV)


def test_se_puede_fijar_la_escala_de_un_solo_canal(session):
    """V5_F: la referencia de un canal cambia y la de los demás no."""
    session.set_scale_uv("C4", 250.0)
    assert session.scale_uv("C4") == pytest.approx(250.0)
    assert session.scale_uv("C3") == pytest.approx(DEFAULT_SCALE_UV)


def test_fijar_una_escala_fuera_de_los_topes_la_recorta(session):
    session.set_scale_uv("C3", 0.0001)
    assert session.scale_uv("C3") == pytest.approx(MIN_SCALE_UV)
    session.set_scale_uv("C3", 1e9)
    assert session.scale_uv("C3") == pytest.approx(MAX_SCALE_UV)


@pytest.mark.parametrize("metodo,args", [("scale_uv", ()), ("set_scale_uv", (50.0,))])
def test_la_escala_de_un_canal_inexistente_falla(session, metodo, args):
    with pytest.raises(ChannelNotFoundError):
        getattr(session, metodo)("Fz", *args)


# -- Herramienta activa -----------------------------------------------------


def test_la_sesion_arranca_sin_herramienta_activa(session):
    assert session.active_tool is None


def test_activar_una_herramienta_reemplaza_a_la_anterior(session):
    """`active_tool` representa **la exclusiva**, así que hay a lo sumo una.

    Los paneles no excluyentes —banda de amplitud, Übersicht, histograma— están
    activos a la vez que una de éstas y los gestiona la ventana principal.
    """
    session.set_active_tool("magnifier")
    assert session.active_tool == "magnifier"
    session.set_active_tool("annotator")
    assert session.active_tool == "annotator"


def test_se_puede_desactivar_la_herramienta(session):
    session.set_active_tool("magnifier")
    session.set_active_tool(None)
    assert session.active_tool is None


def test_el_nombre_de_la_herramienta_no_se_valida(session):
    """Es deliberado, y conviene que quede fijado.

    Validarlo exigiría importar `psglab.tools.registry` desde `core/`, que
    cerraría un ciclo: core.session -> tools.registry -> tools.base ->
    core.session. Para `Session` el nombre es un texto opaco y quien comprueba
    que exista es la ventana principal, que ya conoce el registro.
    """
    session.set_active_tool("una_herramienta_que_no_existe")
    assert session.active_tool == "una_herramienta_que_no_existe"


# -- Que todo esto corra sin interfaz ---------------------------------------


def test_la_sesion_no_necesita_qt(session):
    """El motivo por el que `Session` vive en `core/` y no en `ui/`.

    Si algún día alguien importara PySide6 acá, este test seguiría pasando pero
    `test_las_capas_de_negocio_no_conocen_la_interfaz` fallaría. Éste deja dicho
    para qué sirve la regla: navegar y cambiar la amplitud se verifican sin
    abrir una ventana.
    """
    session.go_to_window(10)
    session.increase_amplitude()
    session.set_active_tool("magnifier")
    assert session.current_window == 10


def test_se_puede_saltar_a_la_primera_ventana(session):
    """Nadie llamaba `go_to_window(0)`.

    Con la guarda escrita `0 < window_index`, la primera ventana quedaría
    inalcanzable desde el clic sobre el histograma y la suite no se enteraría.
    """
    session.go_to_window(10)
    session.go_to_window(0)
    assert session.current_window == 0


def test_retroceder_desde_la_segunda_llega_a_la_primera(session):
    """Nadie retrocedía desde la ventana 1.

    Los tests que había retrocedían desde la 2 y desde la 0, así que la guarda
    podía escribirse `> 1` y la flecha izquierda nunca llegaría al principio de
    la noche.
    """
    session.go_to_window(1)
    session.previous_window()
    assert session.current_window == 0


def test_un_indice_fraccionario_no_corre_la_ventana(session):
    """El clic sobre el histograma calcula el índice desde un píxel.

    `x / ancho * n_windows` da un float, y `1.5` atravesaba la guarda de rango:
    `window_to_samples` devolvía un tramo desplazado media ventana y
    `scoring.get()` reventaba después con un `TypeError` crudo.
    """
    with pytest.raises(WindowOutOfRangeError):
        session.go_to_window(1.5)


def test_el_mensaje_de_ventana_numera_en_base_1(session):
    with pytest.raises(WindowOutOfRangeError) as excepcion:
        session.go_to_window(VENTANAS_SINTETICAS)
    assert str(VENTANAS_SINTETICAS + 1) in excepcion.value.message


def test_un_canal_visible_dos_veces_recibe_el_paso_una_sola_vez(session):
    """Mostrar el mismo canal dos veces es un uso soportado.

    Sin deduplicar, el canal repetido recibía el factor dos veces por pulsación
    y se escapaba del resto sin que el usuario pudiera entender por qué.
    """
    session.set_visible_channels(["C3", "C3", "C4"])
    session.increase_amplitude()
    assert session.scale_uv("C3") == pytest.approx(session.scale_uv("C4"))
