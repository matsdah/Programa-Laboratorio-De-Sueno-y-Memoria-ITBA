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

Igual que en EDF, **MNE entrega volts** para lo que reconoce como voltaje, así
que la conversión de acá es de volt a microvolt.

**Límite conocido, medido sobre el archivo de prueba.** Para las unidades que no
son de voltaje, MNE aplica el prefijo SI de forma inconsistente: escaló un canal
declarado en `µS` (con la mu real) y no escaló otro declarado en `uS` (con u
ASCII). Esos canales se guardan tal como MNE los entrega y con la unidad que
declara el archivo, así que en un canal auxiliar con prefijo la etiqueta puede
quedar corrida en un factor. No se intenta adivinar: los canales que el programa
mide —EEG, EOG y EMG— son de voltaje y para ésos la conversión es exacta.

Cubre del pliego: V1_F de "Importación de archivos".
"""

from pathlib import Path

import mne
import numpy as np

from psglab.core.recording import Channel, Recording
from psglab.readers.base import Reader, register_reader
from psglab.readers.channel_types import detect_channel_kind
from psglab.utils.errors import UnreadableFileError
from psglab.utils.units import MICROVOLT, is_electrical, to_microvolts

#: Unidad en la que MNE entrega los canales de voltaje. Ver `readers/edf.py`,
#: donde está medido contra el rango físico de la cabecera.
_UNIDAD_DE_MNE = "V"

#: Lo que significa el campo de unidad vacío en la línea `Ch<n>=` del `.vhdr`.
_UNIDAD_POR_DEFECTO = MICROVOLT

#: Los tres archivos del formato. El usuario abre el primero.
_EXTENSIONES_DEL_TRIO = (".vhdr", ".eeg", ".vmrk")


def _decodificar_cabecera(crudo: bytes) -> str:
    """Decodifica el `.vhdr` respetando la codificación que él mismo declara.

    La cabecera trae una línea `Codepage=` en `[Common Infos]`. **Ignorarla no
    es cosmético**: el archivo de prueba de MNE declara UTF-8, y leerlo como
    latin-1 convierte la unidad "µV" en "Âµ V" —dos caracteres en vez de uno—,
    con lo cual `is_electrical()` deja de reconocerla. El efecto medido fue que
    23 canales de EEG quedaban **sin convertir**, un millón de veces más chicos,
    y además clasificados como OTHER porque el veto de la unidad se los comía.

    Sin declaración se usa latin-1, que es el valor tradicional del formato y
    además nunca falla: cualquier byte es un carácter válido.
    """
    sondeo = crudo[:4096].decode("ascii", errors="ignore")
    declarada = ""
    for linea in sondeo.splitlines():
        if linea.lower().startswith("codepage="):
            declarada = linea.partition("=")[2].strip()
            break

    for codec in (declarada, "latin-1"):
        if not codec:
            continue
        try:
            return crudo.decode(codec)
        except (LookupError, UnicodeDecodeError):
            continue
    return crudo.decode("latin-1", errors="replace")


def _unidades_declaradas(path: Path) -> dict[str, str]:
    """Unidad de cada canal, leída de las líneas `Ch<n>=` del `.vhdr`.

    MNE consume la unidad al convertir y después no la expone: `info["chs"]`
    dice "V" para todos los canales, **incluidos los que no convirtió**. Está
    medido en `readers/edf.py`, donde ese metadato afirmaba que una temperatura
    en grados estaba en volts.

    Devuelve un diccionario vacío si la cabecera no se puede interpretar: son
    datos accesorios y perderlos es mejor que no poder abrir el archivo.
    """
    unidades: dict[str, str] = {}
    try:
        crudo = path.read_bytes()
    except OSError:
        return {}
    texto = _decodificar_cabecera(crudo)

    for linea in texto.splitlines():
        if not linea.startswith("Ch") or "=" not in linea:
            continue
        etiqueta, _, resto = linea.partition("=")
        if not etiqueta[2:].isdigit():
            continue
        campos = resto.split(",")
        if not campos or not campos[0].strip():
            continue
        declarada = campos[3].strip() if len(campos) > 3 else ""
        unidades[campos[0].strip()] = declarada or _UNIDAD_POR_DEFECTO
    return unidades


@register_reader
class BrainVisionReader(Reader):
    """Lector de registros BrainVision (VHDR/VMRK/EEG)."""

    format_name = "BrainVision"
    extensions = (".vhdr",)

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
        datos = np.asarray(crudo.get_data(), dtype=float)

        canales: list[Channel] = []
        for posicion, nombre in enumerate(crudo.ch_names):
            unidad_declarada = declaradas.get(nombre, _UNIDAD_POR_DEFECTO)
            if is_electrical(unidad_declarada):
                datos[posicion] = to_microvolts(datos[posicion], _UNIDAD_DE_MNE)
                unidad_de_la_fila = MICROVOLT
            else:
                unidad_de_la_fila = unidad_declarada
            canales.append(
                Channel(
                    name=nombre,
                    kind=detect_channel_kind(nombre, unidad_declarada),
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

        return Recording(
            file_path=path,
            channels=canales,
            data=datos,
            sampling_rate=float(crudo.info["sfreq"]),
            start_time=crudo.info.get("meas_date"),
            metadata=metadatos,
        )
