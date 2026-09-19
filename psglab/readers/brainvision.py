"""Lectura de registros en formato BrainVision.

BrainVision reparte el registro en tres archivos que van siempre juntos:

    .vhdr  cabecera: canales, frecuencia de muestreo, unidades
    .vmrk  marcadores y eventos
    .eeg   la señal en sí

El usuario abre el `.vhdr` y los otros dos se cargan solos, porque la
cabecera los referencia por nombre.

**La unidad omitida significa microvoltios.** La línea de canal del formato es
`Ch<n>=<nombre>,<referencia>,<resolución>,<unidad>` y el último campo puede
venir vacío, que es el caso del canal `FP2` del archivo de prueba de MNE. Es una
convención del formato, no un descuido, y MNE la aplica: ese canal vuelve
convertido igual que los que sí la declaran. Tratar la unidad vacía como "no
sé" —que es lo que corresponde en EDF— dejaría un canal de EEG sin convertir, un
millón de veces más chico que sus vecinos.

Igual que en EDF, **MNE entrega volts** para lo que reconoce como voltaje y deja
como viene lo que no reconoce, así que el factor de cada canal depende de qué
hizo MNE con él: de volt a microvolt si lo convirtió, desde su unidad si no. La
regla de MNE distingue mayúsculas y grafías, y la de `utils/units.py` no: ver
`_UNIDADES_QUE_MNE_PASA_A_VOLTS` y el docstring de `readers/edf.py` (hito 33).

**Límite conocido, medido sobre el archivo de prueba.** Para las unidades que no
son de voltaje, MNE aplica el prefijo SI de forma inconsistente: escaló un canal
declarado en `µS` (con la mu real) y no escaló otro declarado en `uS` (con u
ASCII). Esos canales se guardan tal como MNE los entrega y con la unidad que
declara el archivo, así que en un canal auxiliar con prefijo la etiqueta puede
quedar corrida en un factor. No se intenta adivinar: los canales que el programa
mide —EEG, EOG y EMG— son de voltaje y para ésos la conversión es exacta.

Cubre del pliego: V1_F de "Importación de archivos".
"""

import configparser
import math
import re
from pathlib import Path
from typing import Final

import mne
import numpy as np

from psglab.core.recording import Channel, Recording
from psglab.readers.base import Reader, register_reader
from psglab.readers.channel_types import detect_channel_kind
from psglab.utils.errors import UnknownUnitError, UnreadableFileError
from psglab.utils.units import MICROVOLT, conversion_factor, is_electrical

#: Unidad en la que MNE entrega los canales de voltaje. Ver `readers/edf.py`,
#: donde está medido contra el rango físico de la cabecera.
_UNIDAD_DE_MNE = "V"

#: Las unidades que MNE lleva a volts al leer un BrainVision, exactamente como
#: las compara él: son las de voltaje de su `_unit_dict` (MNE 1.12), con el
#: signo micro y no la mu griega. Las demás grafías —`uv`, `μV` con la mu
#: griega— las deja como vienen, y el lector las convierte desde su unidad. Es
#: la misma regla que en `readers/edf.py`, con la tabla de este formato.
_UNIDADES_QUE_MNE_PASA_A_VOLTS: frozenset[str] = frozenset(
    {"V", "µV", "uV", "mV", "nV"}
)

#: Lo que significa el campo de unidad vacío en la línea `Ch<n>=` del `.vhdr`.
_UNIDAD_POR_DEFECTO = MICROVOLT

#: Los tres archivos del formato. El usuario abre el primero.
_EXTENSIONES_DEL_TRIO = (".vhdr", ".eeg", ".vmrk")


#: Clave de `Recording.metadata` donde quedan las impedancias, en kΩ.
#:
#: `core/recording.py` ya anticipaba que `analysis/impedance.py` las buscaría
#: acá; hasta el hito 16 no las guardaba nadie.
IMPEDANCE_KEY: Final[str] = "brainvision_impedances"

#: Unidad en la que el `.vhdr` declara las impedancias. Se comprueba en vez de
#: darla por sentada: el campo `imp_unit` viene por archivo, y leer ohmios como
#: kiloohmios daría mil veces menos y ningún canal parecería fallar nunca.
_UNIDAD_DE_IMPEDANCIA: Final[str] = "kOhm"


def _impedancias_declaradas(crudo: object, nombres: list[str]) -> dict[str, float]:
    """Las impedancias que trae la sección `[Comment]` del `.vhdr`, en kΩ.

    **BrainVision sí las trae y EDF no puede.** El `.vhdr` tiene una tabla
    `Impedance [kOhm] at hh:mm:ss :` con un valor por electrodo, y MNE la
    parsea a `raw.impedances`. El estándar EDF no tiene ningún campo para
    esto, ni siquiera en EDF+, así que ahí no hay nada que extraer y por eso
    este helper vive sólo en este lector.

    Tres cosas que se filtran a propósito:

    - **Los no medidos.** El `.vhdr` los escribe `???` y MNE los entrega como
      `nan`. Se omiten en vez de guardarlos: "no medido" y "0 kΩ" no son lo
      mismo, y confundirlos ocultaría un electrodo suelto. Es el contrato que
      `analysis/impedance.py` documenta.
    - **`Ref` y `Gnd`**, que MNE incluye y **no son canales del registro**.
      Dejarlos haría que un informe hablara de canales que el usuario no ve.
    - **Las unidades que no son kΩ.** Si el archivo declarara otra, se descarta
      el valor: es preferible no tener el dato a tenerlo mil veces mal.

    El atributo existe sólo mientras vive el `Raw` —MNE avisa que no sobrevive
    a guardar y volver a leer—, así que hay que copiarlo acá o se pierde.
    """
    tabla = getattr(crudo, "impedances", None)
    if not isinstance(tabla, dict):
        return {}

    conocidos = set(nombres)
    medidas: dict[str, float] = {}
    for canal, datos in tabla.items():
        if canal not in conocidos or not isinstance(datos, dict):
            continue
        valor = datos.get("imp")
        if datos.get("imp_unit") != _UNIDAD_DE_IMPEDANCIA:
            continue
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            continue
        if math.isnan(numero):
            continue
        medidas[canal] = numero
    return medidas


def _decodificar_cabecera(crudo: bytes) -> str:
    """Decodifica el `.vhdr` **como lo decodifica MNE**.

    La cabecera trae una línea `Codepage=` en `[Common Infos]`. **Ignorarla no
    es cosmético**: el archivo de prueba de MNE declara UTF-8, y leerlo como
    latin-1 convierte la unidad "µV" en "Âµ V" —dos caracteres en vez de uno—,
    con lo cual `is_electrical()` deja de reconocerla. El efecto medido fue que
    23 canales de EEG quedaban **sin convertir**, un millón de veces más chicos,
    y además clasificados como OTHER porque el veto de la unidad se los comía.

    **Sin declaración se usa UTF-8, y si no se puede, latin-1**, que es la
    regla de MNE (`_aux_hdr_info`). Hasta el hito 33 acá se usaba latin-1
    directamente, y con un `.vhdr` sin `Codepage` escrito en UTF-8 pasaba lo
    mismo que arriba, por el otro lado: MNE entendía "µV" y convertía a volts,
    y este lector leía otra unidad y no convertía. Lo que importa no es cuál
    decodificación es la correcta sino **que sea la misma que la de MNE**: la
    unidad sólo sirve para saber qué hizo MNE con la señal.
    """
    declarada = re.search(r"Codepage=(.+)", crudo.decode("ascii", errors="ignore"), re.IGNORECASE)
    codepage = declarada.group(1).strip() if declarada else "utf-8"
    # BrainAmp Recorder escribe "ANSI", que Python no conoce con ese nombre.
    if codepage == "ANSI":
        codepage = "cp1252"
    try:
        return crudo.decode(codepage)
    except (LookupError, UnicodeDecodeError):
        return crudo.decode("latin-1")


def _unidades_declaradas(path: Path) -> dict[int, str]:
    """Unidad de cada canal **por posición**, leída como la lee MNE.

    MNE consume la unidad al convertir y después no la expone: `info["chs"]`
    dice "V" para todos los canales, **incluidos los que no convirtió**. Está
    medido en `readers/edf.py`, donde ese metadato afirmaba que una temperatura
    en grados estaba en volts.

    Se replica el parseo de MNE (hito 33), porque la unidad sólo sirve para
    saber qué hizo él con cada canal:

    - sólo la sección `[Channel Infos]` y nada de lo que sigue a `[Comment]`;
      las líneas `Ch<n>=` de `[Coordinates]` tienen otro significado;
    - la posición sale del `<n>` de `Ch<n>`, que es como MNE ordena sus canales,
      y no del nombre, que MNE modifica —cambia `\\1` por coma—;
    - la unidad va **sin recortar** y sin el `\\xc2` que deja un UTF-8 leído como
      latin-1, que es lo único que MNE le quita. Vacía o ausente es µV.

    Returns:
        La unidad de cada posición, o un diccionario vacío si la cabecera no se
        puede leer.
    """
    try:
        crudo = path.read_bytes()
    except OSError:
        return {}
    texto = _decodificar_cabecera(crudo)
    # La primera línea es la del formato y no es de configuración.
    cuerpo = texto.split("\n", 1)[1] if "\n" in texto else ""
    parametros = cuerpo.split("[Comment]", 1)[0]
    lector = configparser.ConfigParser(interpolation=None)
    try:
        lector.read_string(parametros)
        filas = lector.items("Channel Infos")
    except configparser.Error:
        return {}

    unidades: dict[int, str] = {}
    for clave, valor in filas:
        # `configparser` pasa las claves a minúscula: "Ch1" llega como "ch1".
        numero = re.search(r"ch(\d+)", clave)
        if numero is None:
            continue
        campos = valor.split(",")
        declarada = campos[3].replace("\xc2", "") if len(campos) > 3 else ""
        unidades[int(numero.group(1)) - 1] = declarada or _UNIDAD_POR_DEFECTO
    return unidades


def _factor_a_microvoltios(unidad: str) -> float | None:
    """Por cuánto multiplicar la fila que entregó MNE para tenerla en µV.

    La misma regla que en `readers/edf.py`, con la tabla de este formato: si MNE
    la llevó a volts, de volt a microvolt; si no y es eléctrica, desde su unidad;
    si no es eléctrica, o es ambigua, None y queda como vino.
    """
    if unidad in _UNIDADES_QUE_MNE_PASA_A_VOLTS:
        return conversion_factor(_UNIDAD_DE_MNE)
    if not is_electrical(unidad):
        return None
    try:
        return conversion_factor(unidad)
    except UnknownUnitError:
        return None


@register_reader
class BrainVisionReader(Reader):
    """Lector de registros BrainVision (VHDR/VMRK/EEG)."""

    format_name = "BrainVision"
    extensions = (".vhdr",)

    @classmethod
    def warm_up(cls) -> None:
        """Importa el lector de BrainVision de MNE, que carga recién al usarlo.

        Ver `Reader.warm_up()`. Éste es el que más arrastra: por
        `mne.channels.montage` entran `mne.viz` y `matplotlib`.
        """
        import mne.io.brainvision  # noqa: F401 - importarlo es el trabajo

    def read(self, path: Path) -> Recording:
        """Carga un registro BrainVision a partir de su archivo .vhdr.

        La lectura se apoya en MNE-Python. Los marcadores del .vmrk se
        conservan en `Recording.metadata` para poder convertirlos en
        anotaciones si el usuario lo pide.

        Raises:
            UnreadableFileError: si falta el .eeg o el .vmrk que referencia la
                cabecera, o si el archivo está corrupto.
        """
        try:
            crudo = mne.io.read_raw_brainvision(path, preload=True, verbose="ERROR")
        except Exception as error:  # noqa: BLE001 - MNE eleva de todo
            faltantes = [
                ext
                for ext in _EXTENSIONES_DEL_TRIO
                if not path.with_suffix(ext).exists()
            ]
            if faltantes:
                raise UnreadableFileError(
                    f"Para abrir '{path.name}' hacen falta sus tres archivos, y no se "
                    f"encontró {', '.join(path.stem + e for e in faltantes)}. Los tres "
                    "tienen que estar en la misma carpeta y con el mismo nombre.",
                    details=f"{type(error).__name__}: {error}",
                ) from error
            raise UnreadableFileError(
                f"No se pudo leer el registro '{path.name}': el archivo está dañado o "
                "no tiene el formato BrainVision esperado.",
                details=f"{type(error).__name__}: {error}",
            ) from error

        if not crudo.ch_names:
            raise UnreadableFileError(
                f"El archivo '{path.name}' no declara ningún canal, así que no hay nada "
                "que mostrar ni que scorear.",
                details="La cabecera no trae ninguna línea de canal.",
            )

        declaradas = _unidades_declaradas(path)
        if not declaradas:
            # Sin la unidad no se sabe qué hizo MNE con cada canal, y adivinar
            # deja la señal corrida en un factor mil o un millón (hito 33).
            raise UnreadableFileError(
                f"No se pudo leer el registro '{path.name}': no se entiende en qué "
                "unidad está cada canal.",
                details="La sección [Channel Infos] del .vhdr no se pudo interpretar.",
            )
        datos = np.asarray(crudo.get_data(), dtype=float)

        canales: list[Channel] = []
        for posicion, nombre in enumerate(crudo.ch_names):
            # Por posición: un canal que MNE agrega y la cabecera no nombra
            # —el de las exportaciones con cabecera ASCII— lo entrega en volts,
            # que es lo que dice µV para esta regla.
            unidad_declarada = declaradas.get(posicion, _UNIDAD_POR_DEFECTO)
            factor = _factor_a_microvoltios(unidad_declarada)
            if factor is not None:
                # En sitio, por lo mismo que en `edf.py`: `to_microvolts()`
                # copiaría el canal entero para descartarlo enseguida.
                datos[posicion] *= factor
                unidad_de_la_fila = MICROVOLT
            else:
                unidad_de_la_fila = unidad_declarada
            canales.append(
                Channel(
                    name=nombre,
                    # Igual que en `edf.py`: si se convirtió, la detección recibe
                    # µV y no una grafía que el veto de la unidad no reconozca.
                    kind=detect_channel_kind(
                        nombre, MICROVOLT if factor is not None else unidad_declarada
                    ),
                    unit=unidad_de_la_fila,
                    index=posicion,
                    # BrainVision usa una sola frecuencia para todo el registro,
                    # así que no hay ninguna original distinta que registrar.
                    original_sampling_rate=float(crudo.info["sfreq"]),
                )
            )

        metadatos: dict[str, object] = {}
        if len(crudo.annotations):
            metadatos["brainvision_markers"] = [
                (float(a["onset"]), float(a["duration"]), str(a["description"]))
                for a in crudo.annotations
            ]
        impedancias = _impedancias_declaradas(crudo, list(crudo.ch_names))
        if impedancias:
            metadatos[IMPEDANCE_KEY] = impedancias

        return Recording(
            file_path=path,
            channels=canales,
            data=datos,
            sampling_rate=float(crudo.info["sfreq"]),
            start_time=crudo.info.get("meas_date"),
            metadata=metadatos,
        )
