"""Tests de la detección automática de la clase de cada canal.

El pliego (V4_F de "Visualización de la señal") pide que el software deduzca
solo si un canal es EEG, EOG, EMG, ECG u otra cosa. Sin eso, el investigador
tendría que clasificar a mano decenas de canales en cada registro.

**El test que más importa es el de los siete canales reales.** Son los nombres
exactos del registro de prueba de la Sleep-EDF, y con las tablas como estaban
escritas fallaban tres de siete:

- `"EEG Fpz-Cz"` y `"EEG Pz-Oz"` **no coincidían con nada** y caían en OTHER.
  Son la señal que se scorea: el error más caro posible de esta función.
- `"Temp rectal"` empieza con `"t"`, que `EEG_POSITIONS` incluye suelto, así que
  un termómetro salía clasificado como **EEG**.

Los nombres van como texto y no leyendo el archivo, así que este archivo corre
en cualquier lado, incluido el CI, donde `data/` no existe por el `.gitignore`.
"""

import pytest

from psglab.core.recording import ChannelKind
from psglab.readers.channel_types import (
    detect_all,
    detect_channel_kind,
    is_eeg_position,
)

#: Los siete canales del registro `SC4001E0-PSG.edf`, con la unidad que declara
#: su cabecera. Verificados leyendo el archivo, no de memoria.
CANALES_REALES: list[tuple[str, str, ChannelKind]] = [
    ("EEG Fpz-Cz", "uV", ChannelKind.EEG),
    ("EEG Pz-Oz", "uV", ChannelKind.EEG),
    ("EOG horizontal", "uV", ChannelKind.EOG),
    ("Resp oro-nasal", "", ChannelKind.RESPIRATORY),
    ("EMG submental", "uV", ChannelKind.EMG),
    ("Temp rectal", "DegC", ChannelKind.OTHER),
    ("Event marker", "", ChannelKind.OTHER),
]


# -- El registro real, que es el que manda -----------------------------------


@pytest.mark.parametrize(("nombre", "unidad", "esperada"), CANALES_REALES)
def test_los_canales_del_registro_de_prueba_se_clasifican_bien(
    nombre: str, unidad: str, esperada: ChannelKind
) -> None:
    """Los siete nombres reales, uno por uno. Tres fallaban."""
    assert detect_channel_kind(nombre, unidad) is esperada


def test_los_dos_canales_de_eeg_no_caen_en_otro() -> None:
    """La regresión más cara: es la señal sobre la que se hace el scoring.

    Comparando prefijos, `"EEG Fpz-Cz"` empieza con `"e"` y ninguna posición del
    10-20 empieza así, de modo que los dos canales de EEG del único registro
    real quedaban sin detectar. Se afirma sin pasar la unidad para que el test
    verifique el arreglo del nombre y no lo tape el veto de la unidad.
    """
    assert detect_channel_kind("EEG Fpz-Cz") is ChannelKind.EEG
    assert detect_channel_kind("EEG Pz-Oz") is ChannelKind.EEG


def test_un_termometro_no_es_un_eeg_ni_sin_su_unidad() -> None:
    """La otra regresión, y por partida doble.

    `"Temp rectal"` tiene que salir OTHER **aunque no se pase la unidad**: el
    veto por unidad es la segunda línea de defensa, no la única. Si sólo lo
    salvara el veto, un formato que no declare unidades lo volvería a clasificar
    como EEG.
    """
    assert detect_channel_kind("Temp rectal") is ChannelKind.OTHER
    assert not is_eeg_position("Temp rectal")


# -- Las posiciones del 10-20 ------------------------------------------------


@pytest.mark.parametrize("nombre", ["C3", "C4", "Cz", "O1", "F7", "T3", "Fp1", "Pz"])
def test_las_posiciones_sueltas_son_eeg(nombre: str) -> None:
    assert detect_channel_kind(nombre) is ChannelKind.EEG
    assert is_eeg_position(nombre)


@pytest.mark.parametrize("nombre", ["Fpz-Cz", "Fp1-A2", "C3-M2", "EEG C4-A1"])
def test_los_montajes_bipolares_y_referenciados_tambien(nombre: str) -> None:
    """Alcanza con que **una** parte del nombre sea una posición.

    Exigir que el nombre entero lo fuera dejaría afuera a casi todos los canales
    reales: los bipolares nombran las dos posiciones y los referenciados agregan
    la referencia.
    """
    assert detect_channel_kind(nombre) is ChannelKind.EEG


@pytest.mark.parametrize("nombre", ["EEG", "EEG1", "EEG2"])
def test_un_canal_que_solo_dice_eeg_tambien_lo_es(nombre: str) -> None:
    """No nombra ninguna posición y aun así declara su clase.

    Es lo que traen los montajes que ya vienen derivados del equipo.
    """
    assert detect_channel_kind(nombre) is ChannelKind.EEG


@pytest.mark.parametrize("nombre", ["Event marker", "Temp rectal", "Luz", "SpO2 wave"])
def test_lo_que_no_es_una_posicion_no_lo_parece(nombre: str) -> None:
    """El complemento: `is_eeg_position` no puede volverse permisiva.

    Es la mitad que faltaba cuando la comparación era por prefijo, y la que
    dejaba pasar el termómetro.
    """
    assert not is_eeg_position(nombre)


# -- Los patrones por clase --------------------------------------------------


@pytest.mark.parametrize(
    ("nombre", "esperada"),
    [
        ("EOG izq", ChannelKind.EOG),
        ("LOC-A2", ChannelKind.EOG),
        ("ROC", ChannelKind.EOG),
        ("EMG-menton", ChannelKind.EMG),
        ("Chin1", ChannelKind.EMG),
        ("Tib izq", ChannelKind.EMG),
        ("ECG", ChannelKind.ECG),
        ("EKG II", ChannelKind.ECG),
        ("Flujo nasal", ChannelKind.RESPIRATORY),
        ("Thorax", ChannelKind.RESPIRATORY),
        ("SpO2", ChannelKind.RESPIRATORY),
    ],
)
def test_los_patrones_por_nombre(nombre: str, esperada: ChannelKind) -> None:
    assert detect_channel_kind(nombre) is esperada


def test_un_nombre_desconocido_es_otro_y_no_un_error() -> None:
    """El pliego pide explícitamente que no haya limitación de tipo.

    Un canal que no se reconoce se muestra igual, así que la función no puede
    elevar: devuelve OTHER y sigue.
    """
    assert detect_channel_kind("Sensor 7") is ChannelKind.OTHER


# -- El veto de la unidad ----------------------------------------------------


@pytest.mark.parametrize("unidad", ["DegC", "", "bpm", "%"])
def test_una_unidad_que_no_es_electrica_veta_las_clases_electricas(unidad: str) -> None:
    """El archivo sabe más que el nombre.

    Un canal llamado "C3" pero medido en grados no es un EEG. El parámetro
    `unit` existe para esto y hasta ahora nada obligaba a usarlo.
    """
    assert detect_channel_kind("C3", unidad) is ChannelKind.OTHER
    assert detect_channel_kind("EMG chin", unidad) is ChannelKind.OTHER


@pytest.mark.parametrize("unidad", ["uV", "µV", "mV", "V"])
def test_una_unidad_electrica_no_veta_nada(unidad: str) -> None:
    assert detect_channel_kind("C3", unidad) is ChannelKind.EEG


def test_no_declarar_la_unidad_no_es_lo_mismo_que_declararla_rara() -> None:
    """`None` significa "el formato no lo dice", y no puede vetar.

    BrainVision declara la unidad de cada canal y muchos EDF no, así que tratar
    la ausencia como un veto dejaría sin clasificar registros enteros.
    """
    assert detect_channel_kind("C3", None) is ChannelKind.EEG
    assert detect_channel_kind("C3") is ChannelKind.EEG


def test_el_veto_no_alcanza_a_las_clases_que_no_son_electricas() -> None:
    """Un canal de respiración no se mide en voltios y sigue siendo respiración.

    Si el veto se aplicara a todas las clases, `"Resp oro-nasal"` —que en el
    registro real no declara unidad— saldría OTHER, y `ChannelKind.RESPIRATORY`
    no se podría alcanzar nunca.
    """
    assert detect_channel_kind("Resp oro-nasal", "") is ChannelKind.RESPIRATORY
    assert detect_channel_kind("Flujo", "l/min") is ChannelKind.RESPIRATORY


# -- La versión de lista -----------------------------------------------------


def test_detect_all_clasifica_todos_en_orden() -> None:
    nombres = [n for n, _, _ in CANALES_REALES]
    unidades = [u for _, u, _ in CANALES_REALES]
    assert detect_all(nombres, unidades) == [k for _, _, k in CANALES_REALES]


def test_detect_all_sin_unidades() -> None:
    """Un formato que no las declare no es un error."""
    assert detect_all(["C3", "EOG izq"]) == [ChannelKind.EEG, ChannelKind.EOG]


def test_detect_all_con_menos_unidades_que_canales() -> None:
    """Lo que falta se trata como "no lo dice", no como una unidad vacía.

    Una unidad vacía **veta**, así que confundir las dos cosas haría que los
    canales sin unidad declarada perdieran su clase.
    """
    assert detect_all(["C3", "C4"], ["uV"]) == [ChannelKind.EEG, ChannelKind.EEG]


def test_detect_all_de_una_lista_vacia() -> None:
    assert detect_all([]) == []


# -- Entrada hostil ----------------------------------------------------------


@pytest.mark.parametrize("valor", [None, 3.5, [], {}, object()])
def test_un_nombre_que_no_es_texto_no_rompe_la_importacion(valor: object) -> None:
    """Un lector con un bug no puede voltear la apertura del archivo entero.

    Estas funciones clasifican para mostrar: lo peor que puede pasar con un
    nombre raro es que el canal quede como OTHER, que es lo que ya hace con
    cualquier nombre desconocido.
    """
    assert detect_channel_kind(valor) is ChannelKind.OTHER  # type: ignore[arg-type]
    assert not is_eeg_position(valor)  # type: ignore[arg-type]


@pytest.mark.parametrize("valor", [3.5, [], {}, object()])
def test_una_unidad_que_no_es_texto_veta_como_cualquier_no_electrica(valor: object) -> None:
    """`is_electrical` devuelve False para lo que no es texto, así que veta.

    **`None` no entra en esta lista**, y la distinción es el motivo de que el
    test exista: `None` significa "el formato no declara la unidad" y no puede
    vetar —lo afirma `test_no_declarar_la_unidad_no_es_lo_mismo_que_declararla_rara`—
    mientras que un `3.5` en ese campo es una cabecera mal parseada, y ahí
    desconfiar es lo correcto. La primera versión de este archivo metió `None`
    acá y los dos tests se contradecían.
    """
    assert detect_channel_kind("C3", valor) is ChannelKind.OTHER  # type: ignore[arg-type]
