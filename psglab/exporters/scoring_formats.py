"""El scoring en los formatos que leen otros programas: CSV, EDF+ y XML.

`Scoring.txt` es el formato del pliego y el que esperan los scripts del
laboratorio. Éstos existen para lo otro: **llevar el scoring a un programa que
no es éste** —una planilla, EDFbrowser, Luna, YASA, las herramientas del
NSRR— y traerlo de vuelta. El módulo gemelo, `readers/scoring_formats.py`, lee
lo que éste escribe, y los tests verifican la ida y la vuelta de cada uno.

El formato **se elige por la extensión del archivo**, igual que al importar:
`export_scoring_as()` es la única puerta, y el `.txt` sigue yendo a
`scoring_txt.export_scoring()`, sin cambios. La interfaz arma el menú y los
diálogos recorriendo `SCORING_FORMATS`, así que un formato nuevo aparece solo.

## Los tres formatos

- **CSV**: una fila por ventana, con cabecera `ventana,inicio_s,fase,arousal`.
  La fase va con su **rótulo** (W, S2, N2, REM, R…) y no con el código
  numérico del `.txt`: los rótulos no se repiten entre nomenclaturas, así que
  el archivo dice solo con cuál se scoreó, sin una columna más.
- **EDF+**: un archivo de anotaciones sin ninguna señal, como el hipnograma de
  la Sleep-EDF. Una anotación por **tramo** de fase igual, con los rótulos de
  esa base (`Sleep stage W`, `Sleep stage 2`…), y `Sleep stage N2` para AASM,
  que es lo que distingue una nomenclatura de la otra al volver a leerlo.
- **XML**: el formato del NSRR (`<PSGAnnotation>`), un `<ScoredEvent>` por
  tramo. Lleva además un elemento `<Nomenclature>`, que el NSRR no define y sus
  lectores ignoran: sin él, el código 2 del archivo no dice si es S2 o N2.

En los tres, **las ventanas sin scorear también se escriben**, como en el
`.txt`: un archivo que las saltea no permite distinguir "no se miró" de "el
archivo es más corto". Y el arousal va aparte de la fase, un evento de una
época por cada ventana marcada, porque el pliego lo trata como independiente.

## Por qué el EDF+ se escribe a mano

MNE lee EDF+ pero para escribirlo pide `edfio`, una dependencia más, y además
sólo exporta un `Raw`, que no puede tener cero canales. Un EDF+ de sólo
anotaciones es una cabecera ASCII de 512 bytes y un bloque de texto: escribirlo
acá cuesta menos que la dependencia, y el test lo vuelve a leer con MNE.

Cubre del pliego: V1_F de "Archivo de salida".
"""

import csv
import itertools
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Final

from psglab.config import WINDOW_SECONDS
from psglab.core.nomenclature import SleepStage, stage_code, stage_label
from psglab.core.scoring import Scoring
from psglab.core.windows import window_span_seconds
from psglab.exporters.scoring_txt import export_scoring
from psglab.utils.errors import UnsupportedFormatError

#: Los formatos en que se puede exportar un scoring, por extensión y con el
#: nombre con que se los ofrece en el diálogo. **El orden es el del menú.**
SCORING_FORMATS: Final[dict[str, str]] = {
    "txt": "Texto",
    "csv": "CSV",
    "edf": "EDF+",
    "xml": "XML (NSRR)",
}

#: Cabecera del CSV. `readers/scoring_formats.py` busca las columnas por estos
#: nombres, así que cambiarlos es cambiar el formato.
CSV_COLUMNS: Final[tuple[str, ...]] = ("ventana", "inicio_s", "fase", "arousal")

#: Rótulo de cada fase en el EDF+. R&K sigue la convención de la Sleep-EDF, que
#: es el material de prueba del laboratorio. AASM usa el prefijo N, que es lo
#: que permite reconocerla al volver a leer: «Sleep stage 2» no dice cuál es.
#: REM y R comparten rótulo, como comparten código en el `.txt`.
EDF_STAGE_LABELS: Final[dict[SleepStage, str]] = {
    SleepStage.WAKE: "Sleep stage W",
    SleepStage.S1: "Sleep stage 1",
    SleepStage.S2: "Sleep stage 2",
    SleepStage.S3: "Sleep stage 3",
    SleepStage.S4: "Sleep stage 4",
    SleepStage.REM: "Sleep stage R",
    SleepStage.MT: "Movement time",
    SleepStage.N1: "Sleep stage N1",
    SleepStage.N2: "Sleep stage N2",
    SleepStage.N3: "Sleep stage N3",
    SleepStage.R: "Sleep stage R",
    SleepStage.UNSCORED: "Sleep stage ?",
}

#: Rótulo del arousal en el EDF+. El lector reconoce cualquier anotación que
#: empiece con esta palabra.
EDF_AROUSAL_LABEL: Final[str] = "Arousal"

#: El concepto del NSRR para cada fase. El número después de la barra es el que
#: leen sus herramientas, y coincide con `STAGE_CODES` salvo el de la ventana
#: sin scorear, que el NSRR escribe 9 y el `.txt`, -1.
NSRR_STAGE_CONCEPTS: Final[dict[int, str]] = {
    0: "Wake|0",
    1: "Stage 1 sleep|1",
    2: "Stage 2 sleep|2",
    3: "Stage 3 sleep|3",
    4: "Stage 4 sleep|4",
    5: "REM sleep|5",
    6: "Movement|6",
}
NSRR_UNSCORED: Final[str] = "Unscored|9"
NSRR_STAGE_TYPE: Final[str] = "Stages|Stages"
NSRR_AROUSAL_TYPE: Final[str] = "Arousals|Arousals"
NSRR_AROUSAL_CONCEPT: Final[str] = "Arousal|Arousal ()"

#: Los meses como los escribe la cabecera de un EDF+: en inglés y en mayúscula,
#: sin depender del idioma de la máquina, que es lo que haría `strftime("%b")`.
_MESES: Final[tuple[str, ...]] = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)


def export_scoring_as(
    scoring: Scoring,
    path: Path,
    start_time: datetime | None = None,
) -> None:
    """Escribe el scoring en el formato que indica la extensión de `path`.

    Args:
        scoring: scoring a exportar.
        path: archivo de destino. Su extensión elige el formato, sin distinguir
            mayúsculas.
        start_time: cuándo empezó el registro, si se sabe. Sólo lo usa el EDF+,
            cuya cabecera lleva fecha y hora.

    Raises:
        UnsupportedFormatError: si la extensión no es de ningún formato de
            `SCORING_FORMATS`.
        OSError: si no se puede escribir. No se envuelve acá por el mismo
            motivo que en los otros exportadores: la ventana lo convierte en un
            cartel que nombra la carpeta.
    """
    formato = path.suffix.lower().lstrip(".")
    if formato == "txt":
        export_scoring(scoring, path)
    elif formato == "csv":
        export_scoring_csv(scoring, path)
    elif formato == "edf":
        export_scoring_edf(scoring, path, start_time)
    elif formato == "xml":
        export_scoring_xml(scoring, path)
    else:
        extensiones = ", ".join(f".{e}" for e in SCORING_FORMATS)
        raise UnsupportedFormatError(
            f"No se puede exportar el scoring como «{path.name}»: los formatos "
            f"disponibles son {extensiones}.",
            details=f"Extensión recibida: {path.suffix or '(ninguna)'}.",
        )


def export_scoring_csv(scoring: Scoring, path: Path) -> None:
    """Una fila por ventana: número (base 1), inicio en segundos, fase y arousal."""
    with path.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(CSV_COLUMNS)
        for indice in range(scoring.n_windows):
            epoca = scoring.get(indice)
            inicio, _ = window_span_seconds(indice, 1)
            escritor.writerow(
                (
                    indice + 1,
                    _numero(inicio),
                    stage_label(epoca.stage),
                    1 if epoca.arousal else 0,
                )
            )


def export_scoring_edf(
    scoring: Scoring,
    path: Path,
    start_time: datetime | None = None,
) -> None:
    """Un EDF+C sin señales, con una anotación por tramo de fase igual.

    La estructura es la de un hipnograma de la Sleep-EDF: un único canal
    «EDF Annotations» y un único registro de datos de duración cero, que el
    estándar permite justamente para los archivos que sólo llevan anotaciones.
    """
    anotaciones = _tramos_edf(scoring) + _arousals_edf(scoring)
    bloque = "+0\x14\x14\x00" + "".join(
        f"+{_numero(inicio)}\x15{_numero(duracion)}\x14{texto}\x14\x00"
        for inicio, duracion, texto in anotaciones
    )
    datos = bloque.encode("utf-8")
    # El canal de anotaciones se declara en "muestras" de 16 bits, así que el
    # bloque tiene que tener una cantidad par de bytes.
    muestras = (len(datos) + 1) // 2
    datos = datos.ljust(2 * muestras, b"\x00")

    path.write_bytes(_cabecera_edf(start_time, muestras) + datos)


def export_scoring_xml(scoring: Scoring, path: Path) -> None:
    """El formato del NSRR, con la nomenclatura declarada aparte."""
    raiz = ET.Element("PSGAnnotation")
    ET.SubElement(raiz, "SoftwareVersion").text = "PSGLab"
    ET.SubElement(raiz, "EpochLength").text = _numero(WINDOW_SECONDS)
    ET.SubElement(raiz, "Nomenclature").text = scoring.nomenclature.name
    eventos = ET.SubElement(raiz, "ScoredEvents")

    for primera, cuantas, fase in _tramos(scoring):
        codigo = stage_code(fase)
        concepto = NSRR_UNSCORED if fase is SleepStage.UNSCORED else NSRR_STAGE_CONCEPTS[codigo]
        _evento_xml(eventos, NSRR_STAGE_TYPE, concepto, primera, cuantas)
    for indice in _ventanas_con_arousal(scoring):
        _evento_xml(eventos, NSRR_AROUSAL_TYPE, NSRR_AROUSAL_CONCEPT, indice, 1)

    ET.indent(raiz)
    ET.ElementTree(raiz).write(path, encoding="UTF-8", xml_declaration=True)


# -- Ayudantes ----------------------------------------------------------------


def _tramos(scoring: Scoring) -> list[tuple[int, int, SleepStage]]:
    """Las ventanas agrupadas en tramos de fase igual: (primera, cuántas, fase)."""
    tramos = []
    primera = 0
    for fase, grupo in itertools.groupby(scoring.stages()):
        cuantas = sum(1 for _ in grupo)
        tramos.append((primera, cuantas, fase))
        primera += cuantas
    return tramos


def _ventanas_con_arousal(scoring: Scoring) -> list[int]:
    return [i for i in range(scoring.n_windows) if scoring.get(i).arousal]


def _tramos_edf(scoring: Scoring) -> list[tuple[float, float, str]]:
    return [
        (*window_span_seconds(primera, cuantas), EDF_STAGE_LABELS[fase])
        for primera, cuantas, fase in _tramos(scoring)
    ]


def _arousals_edf(scoring: Scoring) -> list[tuple[float, float, str]]:
    return [
        (*window_span_seconds(indice, 1), EDF_AROUSAL_LABEL)
        for indice in _ventanas_con_arousal(scoring)
    ]


def _evento_xml(
    padre: ET.Element, tipo: str, concepto: str, primera: int, cuantas: int
) -> None:
    inicio, duracion = window_span_seconds(primera, cuantas)
    evento = ET.SubElement(padre, "ScoredEvent")
    ET.SubElement(evento, "EventType").text = tipo
    ET.SubElement(evento, "EventConcept").text = concepto
    ET.SubElement(evento, "Start").text = _numero(inicio)
    ET.SubElement(evento, "Duration").text = _numero(duracion)


def _numero(valor: float) -> str:
    """Un número sin notación científica y sin ceros de más: 30, 30.5, 79470.

    `f"{x:g}"` no sirve: pasa a notación científica desde el millón, y una
    noche larga en segundos ya se acerca.
    """
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.6f}".rstrip("0").rstrip(".")


def _cabecera_edf(start_time: datetime | None, muestras: int) -> bytes:
    """Los 512 bytes de cabecera: la general y la del canal de anotaciones.

    **Sin fecha conocida se escribe `Startdate X`**, que es como el estándar
    dice "no se sabe", y el lector no intenta alinear nada contra esa fecha.
    Los campos de fecha y hora cortos no admiten un valor vacío, así que llevan
    `01.01.85 00.00.00`, que es lo que escriben los demás programas.

    Los años fuera de 1985–2084 no entran en `dd.mm.yy`: el estándar pide
    escribir `yy` literal y dejar el año verdadero en `Startdate`.
    """
    if start_time is None:
        identificacion = "Startdate X X X PSGLab"
        fecha, hora = "01.01.85", "00.00.00"
    else:
        identificacion = (
            f"Startdate {start_time.day:02d}-{_MESES[start_time.month - 1]}-"
            f"{start_time.year:04d} X X PSGLab"
        )
        anio = f"{start_time.year % 100:02d}" if 1985 <= start_time.year <= 2084 else "yy"
        fecha = f"{start_time.day:02d}.{start_time.month:02d}.{anio}"
        hora = f"{start_time.hour:02d}.{start_time.minute:02d}.{start_time.second:02d}"

    general = (
        _campo("0", 8)
        + _campo("X X X X", 80)
        + _campo(identificacion, 80)
        + _campo(fecha, 8)
        + _campo(hora, 8)
        + _campo("512", 8)
        + _campo("EDF+C", 44)
        + _campo("1", 8)  # un registro de datos
        + _campo("0", 8)  # de duración cero: sólo lleva anotaciones
        + _campo("1", 4)  # un canal
    )
    canal = (
        _campo("EDF Annotations", 16)
        + _campo("", 80)  # transductor
        + _campo("", 8)  # unidad física
        + _campo("-1", 8)  # mínimo físico: el estándar sólo pide que difiera
        + _campo("1", 8)  # del máximo
        + _campo("-32768", 8)
        + _campo("32767", 8)
        + _campo("", 80)  # prefiltrado
        + _campo(str(muestras), 8)
        + _campo("", 32)
    )
    return (general + canal).encode("ascii")


def _campo(texto: str, ancho: int) -> str:
    """Un campo de la cabecera: ASCII, alineado a la izquierda y con espacios."""
    return texto[:ancho].ljust(ancho)

