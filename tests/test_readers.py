"""Tests del registro de formatos y de los dos lectores de señal.

**Este archivo está partido en dos a propósito.**

La primera mitad prueba el despacho —el punto de extensión del proyecto— con un
lector de mentira y señal sintética. No toca el disco y corre en cualquier lado,
incluido el CI.

La segunda necesita los registros de prueba, que viven en `data/` y que el
`.gitignore` excluye entero: son datos de participantes y no van al repositorio.
En el CI esos archivos no están, así que esos tests se saltean **con un motivo
explícito**, visible con `python -m pytest -rs`. Saltearlos en silencio sería el
verde por omisión que este repositorio combate; bajarlos en el workflow ataría
el verde a que PhysioNet esté disponible.

Los tests de archivo real verifican lo que de verdad hacía falta medir en el
hito 4: que la señal salga en la escala correcta. MNE entrega **volts** para
los canales cuya unidad reconoce, y confundirse ahí deja la señal un millón de
veces más chica sin que se note en pantalla. Por eso el test compara la amplitud
contra el rango físico que declara la cabecera, **leyéndola por su cuenta** y no
con el parser del propio lector: usar el mismo código de los dos lados no
verificaría nada.

Como esa mitad no corre en el CI, las dos últimas partes repiten lo esencial con
archivos sintéticos que se escriben en el momento: un BrainVision y, desde el
hito 33, un EDF. No reemplazan a los reales —verifican que sepamos leer lo que
escribimos nosotros, no lo que escribe un equipo—, pero hacen que los dos
lectores se ejecuten en las seis combinaciones del CI.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.readers import base
from psglab.readers.base import (
    IMPORT_WARNINGS_KEY,
    Reader,
    available_readers,
    file_dialog_filter,
    load_all_readers,
    read_recording,
    register_reader,
)
from psglab.readers.brainvision import BrainVisionReader
from psglab.readers.edf import EdfReader
from psglab.utils.errors import UnreadableFileError, UnsupportedFormatError
from psglab.utils.units import MICROVOLT

from conftest import (
    ANOTACIONES_EDF,
    FRECUENCIA_BV,
    FRECUENCIA_EDF,
    PICOS_EDF_UV,
    RESOLUCION_BV_UV,
    TEMPERATURA_EDF,
    UV_POR_UNIDAD_BV,
    UV_POR_UNIDAD_EDF,
    escribir_brainvision,
    escribir_edf,
)

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"
EDF_REAL = DATOS / "SC4001E0-PSG.edf"
HIPNOGRAMA = DATOS / "SC4001EC-Hypnogram.edf"
VHDR_REAL = DATOS / "test.vhdr"

#: Por qué se saltea, con todas las letras. Aparece en `pytest -rs`, que es
#: donde alguien lo va a leer.
_MOTIVO = (
    "hace falta el registro de prueba de data/, que el .gitignore excluye porque "
    "son datos de participantes. Ver el hito 0 de docs/TODO.md para bajarlos."
)

necesita_edf = pytest.mark.skipif(not EDF_REAL.exists(), reason=_MOTIVO)
necesita_hipnograma = pytest.mark.skipif(not HIPNOGRAMA.exists(), reason=_MOTIVO)
necesita_brainvision = pytest.mark.skipif(not VHDR_REAL.exists(), reason=_MOTIVO)


# -- Primera mitad: el despacho, sin tocar el disco --------------------------


@pytest.fixture
def registro_aislado():
    """Guarda y restaura el registro de lectores, que es estado de módulo.

    `base._REGISTRY` y `base._REGISTRY_CARGADO` viven a nivel de módulo, así que
    un lector de mentira registrado en un test **queda registrado para toda la
    sesión**. Sin esta fixture, `file_dialog_filter()` empezaría a nombrarlo en
    cualquier otro test del archivo, y el que falla no es el que lo causó.
    """
    original = list(base._REGISTRY)
    cargado = base._REGISTRY_CARGADO
    yield
    base._REGISTRY[:] = original
    base._REGISTRY_CARGADO = cargado


def registro_sintetico(path: Path, canales: int = 2, muestras: int = 3000) -> Recording:
    """Un `Recording` válido mínimo, para que el lector de mentira devuelva algo."""
    return Recording(
        file_path=path,
        channels=[
            Channel(f"C{i}", ChannelKind.EEG, "µV", i, original_sampling_rate=100.0)
            for i in range(canales)
        ],
        data=np.zeros((canales, muestras)),
        sampling_rate=100.0,
    )


class LectorDeMentira(Reader):
    """Un formato inventado, para probar el despacho sin depender de MNE."""

    format_name = "Formato de mentira"
    extensions = (".mentira",)

    def read(self, path: Path) -> Recording:
        return registro_sintetico(path)


def test_un_lector_nuevo_se_registra_sin_tocar_ningun_archivo(registro_aislado):
    """Es la promesa del punto de extensión: agregar un formato no obliga a
    modificar `__init__.py`, ni `main.py`, ni la ventana principal."""
    register_reader(LectorDeMentira)
    assert LectorDeMentira in available_readers()


def test_available_readers_devuelve_clases_y_no_instancias(registro_aislado):
    """Igual que `tools.registry.available_tools()`.

    Los dos son los puntos de extensión del proyecto y se consumen igual. Antes
    uno devolvía instancias y el otro clases, y la ventana principal iba a tener
    que tratarlos distinto sin ningún motivo.
    """
    assert all(isinstance(cls, type) for cls in available_readers())


def test_read_recording_despacha_al_lector_que_corresponde(registro_aislado):
    register_reader(LectorDeMentira)
    registro = read_recording(Path("noche.mentira"))
    assert registro.n_channels == 2
    assert registro.file_path.name == "noche.mentira"


def test_un_formato_desconocido_se_rechaza_nombrando_los_conocidos():
    """El mensaje tiene que servirle a un investigador, no a un programador."""
    with pytest.raises(UnsupportedFormatError) as excepcion:
        read_recording(Path("registro.xyz"))
    assert "registro.xyz" in str(excepcion.value)
    assert ".edf" in str(excepcion.value.details)


@pytest.mark.parametrize("nombre", ["r.MENTIRA", "r.Mentira", "r.mentira"])
def test_can_read_no_distingue_mayusculas(nombre: str):
    """Windows no distingue mayúsculas en las extensiones y el usuario tampoco."""
    assert LectorDeMentira().can_read(Path(nombre))


def test_can_read_rechaza_lo_que_no_es_suyo():
    assert not LectorDeMentira().can_read(Path("registro.edf"))


def test_los_dos_lectores_reales_se_descubren_solos():
    """Nadie los importa a mano: `load_all_readers()` recorre el paquete.

    Es lo que hace que agregar un formato no obligue a tocar ningún archivo
    existente, ni siquiera el `__init__.py` de la carpeta.
    """
    registrados = available_readers()
    assert EdfReader in registrados
    assert BrainVisionReader in registrados


def test_cargar_dos_veces_no_duplica_lectores():
    """Lo promete su docstring, y `read_recording()` la llama en cada apertura."""
    load_all_readers()
    antes = list(available_readers())
    load_all_readers()
    assert list(available_readers()) == antes


def test_el_filtro_del_dialogo_ofrece_primero_todos_los_formatos():
    """Es la entrada que el diálogo usa por defecto.

    El usuario quiere abrir "el registro" sin acordarse de en qué formato se lo
    exportó el equipo.
    """
    entradas = file_dialog_filter().split(";;")
    assert entradas[0].startswith("Todos los formatos soportados")
    assert ".edf" in entradas[0] and ".vhdr" in entradas[0]


def test_el_filtro_termina_dejando_ver_cualquier_archivo():
    """Para la extensión inesperada, que en un laboratorio pasa."""
    assert file_dialog_filter().split(";;")[-1] == "Todos los archivos (*)"


def test_el_filtro_nombra_cada_formato_registrado():
    filtro = file_dialog_filter()
    for cls in available_readers():
        assert cls.format_name in filtro


def test_un_formato_nuevo_aparece_solo_en_el_dialogo(registro_aislado):
    """La otra mitad de la promesa del punto de extensión: no hay que tocar la
    interfaz para que un formato nuevo se pueda abrir."""
    assert "Formato de mentira" not in file_dialog_filter()
    register_reader(LectorDeMentira)
    assert "Formato de mentira" in file_dialog_filter()
    assert "*.mentira" in file_dialog_filter()


# -- Segunda mitad: los archivos reales --------------------------------------


def rango_fisico_declarado(path: Path) -> dict[str, tuple[float, float]]:
    """Rango físico de cada canal, leído de la cabecera EDF **por este test**.

    Se parsea acá a mano y no con `edf._leer_cabecera()` a propósito: si los dos
    lados usaran el mismo código, un error de offsets se cancelaría solo y el
    test pasaría sin verificar nada.
    """
    with path.open("rb") as archivo:
        archivo.seek(252)
        cantidad = int(archivo.read(4))
        archivo.seek(256)
        nombres = [archivo.read(16).decode("latin-1").strip() for _ in range(cantidad)]
        archivo.seek(256 + cantidad * 104)
        minimos = [float(archivo.read(8)) for _ in range(cantidad)]
        maximos = [float(archivo.read(8)) for _ in range(cantidad)]
    return dict(zip(nombres, zip(minimos, maximos)))


@pytest.fixture(scope="module")
def edf_real() -> Recording:
    """El registro se carga una sola vez: son 48 MB y 22 horas de señal."""
    return read_recording(EDF_REAL)


@pytest.fixture(scope="module")
def brainvision_real() -> Recording:
    return read_recording(VHDR_REAL)


@necesita_edf
def test_el_edf_real_trae_sus_siete_canales(edf_real: Recording):
    assert edf_real.n_channels == 7
    assert edf_real.sampling_rate == 100.0
    assert 22 < edf_real.duration_seconds / 3600 < 23


@necesita_edf
def test_el_edf_real_informa_su_hora_de_inicio(edf_real: Recording):
    """El histograma pone el eje en hora real si el archivo la trae (V2_F)."""
    assert edf_real.start_time is not None
    assert edf_real.start_time.year == 1989


@necesita_edf
@pytest.mark.parametrize(
    ("canal", "clase"),
    [
        ("EEG Fpz-Cz", ChannelKind.EEG),
        ("EEG Pz-Oz", ChannelKind.EEG),
        ("EOG horizontal", ChannelKind.EOG),
        ("EMG submental", ChannelKind.EMG),
        ("Resp oro-nasal", ChannelKind.RESPIRATORY),
        ("Temp rectal", ChannelKind.OTHER),
        ("Event marker", ChannelKind.OTHER),
    ],
)
def test_las_clases_del_edf_real(edf_real: Recording, canal: str, clase: ChannelKind):
    """Sobre el archivo, no sobre los nombres sueltos.

    `tests/test_channel_types.py` ya prueba la clasificación con los nombres como
    texto; acá se verifica que el lector le pase la unidad que corresponde, que
    es lo que salva a `"Temp rectal"` de salir EEG.
    """
    assert edf_real.channel_by_name(canal).kind is clase


@necesita_edf
@pytest.mark.parametrize(
    ("canal", "frecuencia"),
    [
        ("EEG Fpz-Cz", 100.0),
        ("EEG Pz-Oz", 100.0),
        ("EOG horizontal", 100.0),
        ("Resp oro-nasal", 1.0),
        ("EMG submental", 1.0),
        ("Temp rectal", 1.0),
        ("Event marker", 1.0),
    ],
)
def test_la_frecuencia_original_de_cada_canal_queda_registrada(
    edf_real: Recording, canal: str, frecuencia: float
):
    """MNE unifica todo a 100 Hz sobremuestreando y no avisa.

    Sin este dato, un EMG que venía a 1 Hz se vería como una señal normal de
    100 Hz y nada diría que su resolución real es cien veces menor.
    """
    assert edf_real.channel_by_name(canal).original_sampling_rate == frecuencia


@necesita_edf
def test_la_matriz_tiene_una_sola_frecuencia_aunque_el_archivo_no(
    edf_real: Recording,
):
    """El modelo exige una sola, y el archivo trae dos. Las dos cosas conviven
    porque la original viaja en cada canal."""
    originales = {c.original_sampling_rate for c in edf_real.channels}
    assert originales == {100.0, 1.0}
    assert edf_real.sampling_rate == 100.0


@necesita_edf
def test_la_senal_electrica_queda_en_microvoltios(edf_real: Recording):
    """**El test que justifica todo este archivo.**

    MNE entrega volts para los canales cuya unidad reconoce. Aplicar el factor
    de la unidad del archivo —`conversion_factor("uV")`, que vale 1— dejaría la
    señal un millón de veces más chica, y con autoescala en pantalla seguiría
    pareciendo una señal.

    Se compara contra el rango físico que declara la cabecera, leído por este
    test. Si el lector volviera a convertir de más o de menos, la señal se sale
    del rango que el propio archivo promete.
    """
    declarado = rango_fisico_declarado(EDF_REAL)
    for canal in edf_real.channels:
        if canal.unit != "µV":
            continue
        minimo, maximo = declarado[canal.name]
        senal = edf_real.data[canal.index]
        # La holgura es de una parte en mil millones, y existe porque la señal
        # **toca** su máximo declarado: `EEG Pz-Oz` llega a 196.00000000000003
        # contra los 196.0 de la cabecera. Es el resto del viaje entero →
        # físico → volt → microvolt, no un error de escala. Lo que este test
        # persigue son órdenes de magnitud, y con esta holgura un factor 10⁶
        # sigue haciéndolo fallar por catorce cifras de margen.
        holgura = (maximo - minimo) * 1e-9
        assert minimo - holgura <= senal.min() and senal.max() <= maximo + holgura, (
            f"{canal.name} se sale del rango físico declarado [{minimo}, {maximo}]: "
            f"[{senal.min()}, {senal.max()}]. Si la diferencia es de un factor 10^6, "
            "alguien volvió a convertir lo que MNE ya había convertido."
        )


@necesita_edf
def test_los_canales_que_no_son_electricos_conservan_su_escala(edf_real: Recording):
    """Una temperatura corporal en °C tiene que seguir siendo una temperatura.

    Convertirla a µV no significa nada, y descartar el canal contradiría el
    pedido del pliego de no limitar por tipo de señal.
    """
    temperatura = edf_real.channel_by_name("Temp rectal")
    assert temperatura.unit == "DegC"
    valores = edf_real.data[temperatura.index]
    assert 30 < valores.min() and valores.max() < 45


@necesita_hipnograma
def test_un_edf_sin_senal_manda_al_importador_de_scoring():
    """El hipnograma de la Sleep-EDF es un EDF+ de anotaciones, no un registro.

    MNE le saca el canal de anotaciones y no queda ninguno. Sin este control,
    `Recording` elevaría "no tiene ningún canal": un mensaje correcto que le hace
    creer al investigador que su archivo está roto.
    """
    with pytest.raises(UnreadableFileError) as excepcion:
        read_recording(HIPNOGRAMA)
    assert "scoring" in str(excepcion.value).lower()


@necesita_brainvision
def test_el_brainvision_real_trae_sus_treinta_y_dos_canales(
    brainvision_real: Recording,
):
    assert brainvision_real.n_channels == 32
    assert brainvision_real.sampling_rate == 1000.0


@necesita_brainvision
def test_el_brainvision_real_detecta_sus_canales_10_20(brainvision_real: Recording):
    """Los nombres son posiciones del 10-20: FP1, F3, C3, O2..."""
    eeg = [c for c in brainvision_real.channels if c.kind is ChannelKind.EEG]
    assert len(eeg) == 26


@necesita_brainvision
def test_el_canal_sin_unidad_declarada_se_convierte_igual(
    brainvision_real: Recording,
):
    """`FP2` no declara unidad, y en BrainVision eso significa µV.

    Es el canal que destapó el bug del `Codepage`: leyendo la cabecera como
    latin-1, la unidad "µV" de los otros canales llegaba partida en dos
    caracteres y **23 canales de EEG quedaban sin convertir**, mientras que FP2
    —que no declara ninguna— sí se convertía. Salían de órdenes de magnitud
    distintos, que es como se notó.
    """
    fp1 = brainvision_real.channel_by_name("FP1")
    fp2 = brainvision_real.channel_by_name("FP2")
    assert fp1.unit == fp2.unit == "µV"

    maximo_fp1 = np.abs(brainvision_real.data[fp1.index]).max()
    maximo_fp2 = np.abs(brainvision_real.data[fp2.index]).max()
    assert 0.1 < maximo_fp1 / maximo_fp2 < 10, (
        "FP1 y FP2 tienen que estar en la misma escala; una diferencia de 10^6 "
        "significa que uno de los dos no se convirtió."
    )


@necesita_brainvision
def test_los_marcadores_del_vmrk_se_conservan(brainvision_real: Recording):
    """Su docstring promete guardarlos para poder convertirlos en anotaciones.

    `Recording.metadata` depende del formato de origen, así que ninguna capa
    debería darlo por presente sin verificarlo: por eso se comprueba la clave.
    """
    marcadores = brainvision_real.metadata.get("brainvision_markers")
    assert marcadores is not None
    assert len(marcadores) == 13
    inicio, duracion, descripcion = marcadores[0]
    assert isinstance(inicio, float) and isinstance(descripcion, str)


# -- Tercera mitad: el BrainVision sintético, que corre en todas partes -------
#
# La segunda mitad no corre en el CI, así que hasta acá el lector de
# BrainVision no se ejecutaba en ninguna de las seis combinaciones de sistema y
# versión de Python. Estos tests usan la fixture `brainvision_sintetico`, que
# escribe los tres archivos del formato en el momento: verifican el camino de
# parseo en todas partes, y **no reemplazan** a los de archivo real, que son los
# que verifican que sepamos leer lo que no escribimos nosotros.


def test_el_brainvision_sintetico_se_lee(brainvision_sintetico: Path):
    registro = read_recording(brainvision_sintetico)

    assert len(registro.channels) == 3
    assert registro.sampling_rate == pytest.approx(FRECUENCIA_BV)


def test_el_despacho_reconoce_el_vhdr(brainvision_sintetico: Path):
    """Que el `.vhdr` sea el archivo que se abre, y no el `.eeg` ni el `.vmrk`."""
    assert BrainVisionReader().can_read(brainvision_sintetico)


def test_la_resolucion_del_archivo_se_aplica(brainvision_sintetico: Path):
    """**Es la cuenta que separa una señal correcta de una 2000 veces más
    chica.** El archivo guarda enteros y la cabecera dice cuántos µV vale cada
    cuenta; sin aplicar la resolución, el pico de 50 µV llega como 100.
    """
    registro = read_recording(brainvision_sintetico)
    pico = float(np.max(np.abs(registro.data[0])))

    # El seno se cuantiza a pasos de RESOLUCION_BV_UV, así que el pico queda a
    # menos de un paso de los 50 µV que se sintetizaron.
    assert pico == pytest.approx(50.0, abs=RESOLUCION_BV_UV)


def test_cada_canal_conserva_su_amplitud(brainvision_sintetico: Path):
    """Tres amplitudes distintas: una escala aplicada de más o de menos se ve en
    los tres a la vez, y una permutación de canales, en uno solo."""
    registro = read_recording(brainvision_sintetico)
    picos = [float(np.max(np.abs(fila))) for fila in registro.data]

    for medido, esperado in zip(picos, (50.0, 30.0, 20.0)):
        assert medido == pytest.approx(esperado, abs=RESOLUCION_BV_UV)


def test_la_unidad_declarada_en_utf8_se_entiende(brainvision_sintetico: Path):
    """**El bug que motivó `_decodificar_cabecera()`.**

    La cabecera declara `Codepage=UTF-8` y escribe la unidad en UTF-8. Leída
    como latin-1, el micro llega partido en dos caracteres, la unidad deja de
    reconocerse y el canal ni se convierte ni se clasifica. En el registro real
    eso dejó veintitrés canales EEG afuera, y se descubrió por casualidad
    porque un canal sin unidad declarada salía mejor que uno con ella.
    """
    registro = read_recording(brainvision_sintetico)

    for canal in registro.channels:
        assert canal.unit == MICROVOLT


def test_las_clases_se_detectan_sobre_el_sintetico(brainvision_sintetico: Path):
    registro = read_recording(brainvision_sintetico)
    clases = {canal.name: canal.kind for canal in registro.channels}

    assert clases == {
        "C3": ChannelKind.EEG,
        "EOG-izq": ChannelKind.EOG,
        "EMG-menton": ChannelKind.EMG,
    }


def test_el_sintetico_dura_lo_que_dice_su_cabecera(brainvision_sintetico: Path):
    """`SamplingInterval` está en microsegundos y es fácil equivocarle el
    factor: con milisegundos, el registro duraría mil veces más."""
    registro = read_recording(brainvision_sintetico)

    assert registro.n_samples == int(FRECUENCIA_BV * 3)


@pytest.mark.parametrize("unidad", sorted(UV_POR_UNIDAD_BV))
def test_la_senal_del_brainvision_queda_en_microvoltios(tmp_path: Path, unidad: str):
    """**Cada grafía, escrita en su unidad, vuelve a los mismos µV** (hito 33).

    MNE convierte a volts las que reconoce —`µV` con el signo micro, `uV`,
    `mV`, `nV`— y deja como vienen las demás: `uv`, `mv`, la mu griega. El
    lector multiplicaba de volt a microvolt en los dos casos, y un canal en `uv`
    llegaba un millón de veces más grande; uno en `nV` quedaba en volts con la
    etiqueta `nV`.
    """
    vhdr = escribir_brainvision(tmp_path, segundos=3, canales=[("C3", unidad)])
    registro = read_recording(vhdr)

    assert registro.channels[0].unit == MICROVOLT
    pico = float(np.max(np.abs(registro.data[0])))
    assert pico == pytest.approx(50.0, abs=RESOLUCION_BV_UV), (
        f"con la unidad {unidad!r} el pico sale {pico} µV y se escribieron 50"
    )


def test_un_vhdr_sin_codepage_se_decodifica_como_lo_hace_mne(tmp_path: Path):
    """Sin `Codepage`, MNE prueba UTF-8 y entiende "µV"; el lector probaba
    latin-1, leía "Âµ" y no convertía: los tres canales quedaban en volts,
    con la unidad "ÂµV" y fuera del EEG. Encontrado en el hito 33."""
    vhdr = escribir_brainvision(tmp_path, segundos=3, codepage=None)
    registro = read_recording(vhdr)

    assert [canal.unit for canal in registro.channels] == [MICROVOLT] * 3
    assert registro.channel_by_name("C3").kind is ChannelKind.EEG
    pico = float(np.max(np.abs(registro.data[0])))
    assert pico == pytest.approx(50.0, abs=RESOLUCION_BV_UV)


def test_las_coordenadas_no_pisan_las_unidades(tmp_path: Path):
    """`[Coordinates]` también tiene líneas `Ch<n>=`, y no hablan de unidades.
    Leyendo la cabecera por posición, sin mirar la sección, un canal en mV se
    quedaba con la unidad por omisión."""
    vhdr = escribir_brainvision(
        tmp_path, segundos=3, canales=[("C3", "mv"), ("C4", "µV")], coordenadas=True
    )
    registro = read_recording(vhdr)

    picos = [float(np.max(np.abs(fila))) for fila in registro.data]
    assert picos == pytest.approx([50.0, 30.0], abs=RESOLUCION_BV_UV)


# -- Cuarta parte: el EDF sintético, que también corre en todas partes --------
#
# Lo mismo que la tercera, para el otro formato. Hasta el hito 33 el lector de
# EDF sólo corría contra `data/`, así que en el CI la conversión a µV —el test
# que justifica todo este archivo— no se ejercitaba nunca. La fixture
# `edf_sintetico` y `escribir_edf()` escriben el archivo en el momento, **cada
# canal en su propia unidad**: leerlo bien es recuperar los µV que se
# sintetizaron. Tampoco reemplazan a los de archivo real.


def test_el_edf_sintetico_se_lee(edf_sintetico: Path):
    registro = read_recording(edf_sintetico)

    assert registro.n_channels == 3
    assert registro.sampling_rate == FRECUENCIA_EDF
    assert registro.n_samples == int(FRECUENCIA_EDF * 3)


def test_el_despacho_reconoce_el_edf(edf_sintetico: Path):
    assert EdfReader().can_read(edf_sintetico)


@pytest.mark.parametrize("unidad", sorted(UV_POR_UNIDAD_EDF))
def test_la_senal_del_edf_queda_en_microvoltios(tmp_path: Path, unidad: str):
    """**El gemelo sintético de `test_la_senal_electrica_queda_en_microvoltios`.**

    Una unidad por caso, con la señal escrita en esa unidad. MNE entrega volts
    para las grafías que reconoce y deja como vienen las demás, y el lector
    tiene que saber cuál de las dos cosas pasó: si se equivoca, el pico se va
    por un factor mil o un millón. `uv`, `UV`, `mv` y `nV` son las que el hito
    33 encontró rotas; la mu de Shift-JIS es la que MNE sí reconoce y la
    detección de unidades no.
    """
    edf = escribir_edf(tmp_path, segundos=3, canales=[("EEG C3-A2", unidad, FRECUENCIA_EDF)])
    registro = read_recording(edf)

    assert registro.channels[0].unit == MICROVOLT
    pico = float(np.max(np.abs(registro.data[0])))
    assert pico == pytest.approx(PICOS_EDF_UV[0], rel=1e-3), (
        f"con la unidad {unidad!r} el pico sale {pico} µV y se escribieron "
        f"{PICOS_EDF_UV[0]}: un factor 10^3 o 10^6 es una conversión de más o de menos"
    )


def test_cada_canal_del_edf_conserva_su_amplitud(edf_sintetico: Path):
    """Tres picos distintos: una escala equivocada se ve en los tres, y una
    permutación de canales, en uno solo."""
    registro = read_recording(edf_sintetico)
    picos = [float(np.max(np.abs(fila))) for fila in registro.data]

    assert picos == pytest.approx(list(PICOS_EDF_UV[:3]), rel=1e-3)


def test_un_canal_no_electrico_del_edf_conserva_su_escala(tmp_path: Path):
    """El gemelo de `test_los_canales_que_no_son_electricos_conservan_su_escala`:
    una temperatura sigue en grados, con su unidad y fuera del EEG."""
    edf = escribir_edf(
        tmp_path,
        segundos=3,
        canales=[
            ("EEG C3-A2", "uV", FRECUENCIA_EDF),
            ("Temp rectal", "DegC", FRECUENCIA_EDF),
        ],
    )
    registro = read_recording(edf)
    temperatura = registro.channel_by_name("Temp rectal")

    assert temperatura.unit == "DegC"
    assert temperatura.kind is ChannelKind.OTHER
    valores = registro.data[temperatura.index]
    assert float(valores.max()) == pytest.approx(TEMPERATURA_EDF + 0.5, abs=1e-3)


def test_un_edf_con_frecuencias_mixtas_se_unifica_y_las_recuerda(tmp_path: Path):
    """El gemelo de `test_la_matriz_tiene_una_sola_frecuencia_aunque_el_archivo_no`.

    MNE sobremuestrea el canal de 1 Hz a 100 Hz sin avisar; lo que el lector
    agrega es no perder de dónde venía cada fila.
    """
    edf = escribir_edf(
        tmp_path,
        segundos=10,
        canales=[("EEG C3-A2", "uV", 100.0), ("EMG submental", "uV", 1.0)],
    )
    registro = read_recording(edf)

    assert registro.sampling_rate == 100.0
    assert registro.n_samples == 1000
    assert [c.original_sampling_rate for c in registro.channels] == [100.0, 1.0]


def test_el_edf_sintetico_informa_su_hora_de_inicio(edf_sintetico: Path):
    """La que escribió `escribir_edf()`: el 7 de septiembre de 2026 a las 23."""
    inicio = read_recording(edf_sintetico).start_time

    assert inicio is not None
    assert (inicio.year, inicio.month, inicio.day, inicio.hour, inicio.minute) == (
        2026, 9, 7, 23, 0,
    )


def test_las_clases_se_detectan_sobre_el_edf_sintetico(edf_sintetico: Path):
    registro = read_recording(edf_sintetico)
    clases = {canal.name: canal.kind for canal in registro.channels}

    assert clases == {
        "EEG C3-A2": ChannelKind.EEG,
        "EOG izquierdo": ChannelKind.EOG,
        "EMG submental": ChannelKind.EMG,
    }


def test_dos_canales_del_edf_con_la_misma_etiqueta_quedan_en_microvoltios(tmp_path: Path):
    """**El otro error de escala del hito 33.** MNE renombra los repetidos
    (`EEG-0`, `EEG-1`), y la cabecera se buscaba por nombre: no los encontraba y
    los dejaba en volts, sin unidad y fuera del EEG. Ahora se empareja por
    posición."""
    edf = escribir_edf(
        tmp_path,
        segundos=3,
        canales=[("EEG", "uV", FRECUENCIA_EDF), ("EEG", "mV", FRECUENCIA_EDF)],
    )
    registro = read_recording(edf)

    assert registro.channel_names() == ["EEG-0", "EEG-1"]
    assert [canal.unit for canal in registro.channels] == [MICROVOLT, MICROVOLT]
    picos = [float(np.max(np.abs(fila))) for fila in registro.data]
    assert picos == pytest.approx(list(PICOS_EDF_UV[:2]), rel=1e-3)


def test_el_canal_de_anotaciones_no_corre_las_unidades(tmp_path: Path):
    """MNE saca de la señal el canal `EDF Annotations` de un EDF+, y el lector
    tiene que sacarlo igual para que las posiciones de la cabecera coincidan: si
    no, el canal de después se quedaría con la unidad y la frecuencia del de
    anotaciones."""
    edf = escribir_edf(
        tmp_path,
        segundos=3,
        canales=[
            ("EEG C3-A2", "uV", FRECUENCIA_EDF),
            (ANOTACIONES_EDF, "", 30.0),
            ("EMG submental", "mV", FRECUENCIA_EDF),
        ],
    )
    registro = read_recording(edf)

    assert registro.channel_names() == ["EEG C3-A2", "EMG submental"]
    emg = registro.channel_by_name("EMG submental")
    assert emg.unit == MICROVOLT
    assert emg.original_sampling_rate == FRECUENCIA_EDF
    # El pico sale de la posición en el archivo, que es la tercera.
    assert float(np.max(np.abs(registro.data[emg.index]))) == pytest.approx(
        PICOS_EDF_UV[2], rel=1e-3
    )


def test_una_unidad_ambigua_queda_como_vino(tmp_path: Path):
    """«MV» puede ser mega o mili, y `utils/units.py` se niega a adivinar. El
    canal queda con los números del archivo y con su unidad a la vista, en vez
    de convertirse con un factor inventado o de impedir abrir el registro
    entero por un solo canal."""
    edf = escribir_edf(
        tmp_path,
        segundos=3,
        canales=[("EEG C3-A2", "uV", FRECUENCIA_EDF), ("EMG submental", "MV", FRECUENCIA_EDF)],
    )
    registro = read_recording(edf)
    emg = registro.channel_by_name("EMG submental")

    assert emg.unit == "MV"
    assert float(registro.data[emg.index].max()) == pytest.approx(TEMPERATURA_EDF + 0.5, abs=1e-3)
    assert registro.channels[0].unit == MICROVOLT


def truncar_edf(edf: Path, registros_que_quedan: int, bytes_por_registro: int) -> None:
    """Deja la cabecera y esa cantidad de registros de datos, más medio registro
    suelto: es como queda una copia interrumpida."""
    canales = int(edf.read_bytes()[252:256].strip())
    cabecera = 256 * (canales + 1)
    largo = cabecera + registros_que_quedan * bytes_por_registro + bytes_por_registro // 2
    edf.write_bytes(edf.read_bytes()[:largo])


def test_un_edf_truncado_se_abre_con_lo_que_trae_y_avisa(tmp_path: Path):
    """**Hito 33.** MNE lee los registros que hay y avisa sólo por consola, así
    que abrir media noche no se distinguía de abrir una noche entera. Se abre
    igual —lo que llegó puede ser todo lo que hay— y el aviso lo dice."""
    edf = escribir_edf(tmp_path, segundos=10)
    # Tres canales a 100 Hz: 300 muestras de dos bytes por registro de un segundo.
    truncar_edf(edf, registros_que_quedan=4, bytes_por_registro=600)

    registro = read_recording(edf)

    assert registro.n_samples == 4 * int(FRECUENCIA_EDF)
    (aviso,) = registro.metadata[IMPORT_WARNINGS_KEY]
    assert "sintetico.edf" in aviso
    assert "4 s" in aviso and "10 s" in aviso


def test_un_edf_entero_no_avisa(edf_sintetico: Path):
    assert IMPORT_WARNINGS_KEY not in read_recording(edf_sintetico).metadata


def test_un_edf_que_no_dice_cuantos_registros_tiene_no_avisa(tmp_path: Path):
    """Mientras graba, un equipo escribe -1 registros: el formato dice que se
    deducen del tamaño, y eso no es un archivo incompleto."""
    edf = escribir_edf(tmp_path, segundos=3)
    crudo = bytearray(edf.read_bytes())
    crudo[236:244] = b"-1      "
    edf.write_bytes(bytes(crudo))

    registro = read_recording(edf)

    assert registro.n_samples == 3 * int(FRECUENCIA_EDF)
    assert IMPORT_WARNINGS_KEY not in registro.metadata


# -- Precalentar los lectores (hito 33) --------------------------------------


def test_precalentar_deja_importado_lo_que_mne_carga_al_usarlo():
    """**De los 9,2 s de la primera lectura de un proceso, 8,65 eran esto**:
    `mne.io` carga el módulo de cada formato recién la primera vez que se lo
    usa, con la ventana congelada en lo primero que hace el usuario."""
    import sys

    from psglab.readers.base import warm_up_readers

    warm_up_readers()

    assert "mne.io.edf" in sys.modules
    assert "mne.io.brainvision" in sys.modules


def test_un_lector_que_no_tiene_nada_que_adelantar_no_hace_nada(registro_aislado):
    """`Reader.warm_up()` no hace nada por defecto, como los métodos de evento
    de `Tool`: un formato nuevo no tiene que saber que existe."""
    from psglab.readers.base import warm_up_readers

    register_reader(LectorDeMentira)

    warm_up_readers()  # No eleva.


def test_precalentar_no_lee_ningun_archivo(monkeypatch, registro_aislado):
    """Adelanta importaciones, no lecturas: no puede tocar el disco del usuario."""
    from psglab.readers.base import warm_up_readers

    leidos: list[Path] = []
    monkeypatch.setattr(LectorDeMentira, "read", lambda self, path: leidos.append(path))
    register_reader(LectorDeMentira)

    warm_up_readers()

    assert leidos == []


@pytest.mark.parametrize("nombre", ["no_existe.edf", "no_existe.vhdr"])
def test_un_archivo_que_no_esta_no_se_informa_como_danado(tmp_path: Path, nombre: str):
    """Decir que está dañado manda a buscar el problema al lugar equivocado: el
    archivo puede estar en otra carpeta, o el disco de la noche sin montar."""
    with pytest.raises(UnreadableFileError) as error:
        read_recording(tmp_path / nombre)

    assert "no se encontró" in str(error.value).lower()
