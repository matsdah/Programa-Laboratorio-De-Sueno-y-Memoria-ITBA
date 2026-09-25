"""Importación de un scoring escrito por otro programa: CSV, EDF+ y XML.

Es la mitad de lectura de `exporters/scoring_formats.py`, y lee lo que aquél
escribe. Pero no sólo eso: el objetivo es **traer el trabajo hecho en otro
lado** —el hipnograma de la Sleep-EDF, una planilla, un XML del NSRR—, así que
cada lector acepta las variantes habituales del formato y no sólo la propia.

`scoring_reader.read_scoring()` es la única puerta y elige el lector por la
extensión; el `.txt` lo sigue leyendo aquél. La dependencia va en un solo
sentido, de `scoring_reader` hacia acá.

## La nomenclatura no se adivina

Es la misma regla que en el `.txt`, y por el mismo motivo: el código 2 es S2
en Rechtschaffen y Kales y N2 en AASM, y una noche leída con la equivocada se
carga entera mal traducida sin ningún error visible. Se decide así:

1. **La que el archivo declara**: el elemento `<Nomenclature>` del XML.
2. **La única compatible con lo que el archivo trae.** Un rótulo como «S2» o
   «N2», un código 4 o un «Movement time» sólo existen en una de las dos.
3. **La que pasó quien llama**, que en la ventana es la que eligió el usuario.
4. Si no hay ninguna, `UndeclaredNomenclatureError`, que la ventana convierte
   en la pregunta.

Si lo que el archivo trae no entra en ninguna de las dos —fases de las dos
mezcladas, o una que declara AASM y trae un S4—, el archivo se rechaza.

## Eventos y épocas

El EDF+ y el XML no hablan de épocas sino de eventos con inicio y duración,
que en un hipnograma real abarcan muchas: la Sleep-EDF abre con un único
«Sleep stage W» de 8,5 horas. La traducción es
`core.windows.windows_in_span()`, que asigna cada época al evento que cubre su
punto medio.

**Lo que se pasa del final del registro se ignora sólo si no está scoreado.**
El hipnograma de la Sleep-EDF termina con un «Sleep stage ?» que excede la
señal en casi dos horas, y eso no es un error. Una fase scoreada más allá del
final sí lo es: el archivo es de otro registro.

Cubre del pliego: V3_F de "Importación de archivos".
"""

import csv
import math
import re
import warnings
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from psglab.config import WINDOW_SECONDS
from psglab.core.nomenclature import (
    Nomenclature,
    SleepStage,
    is_valid,
    stage_from_code,
)
from psglab.core.scoring import Scoring
from psglab.core.windows import windows_in_span
from psglab.utils.errors import (
    InvalidStageError,
    ScoringMismatchError,
    UndeclaredNomenclatureError,
    UnreadableFileError,
)

#: Cómo se puede escribir cada nomenclatura, en minúscula. Se aceptan el nombre
#: corto y el largo porque el archivo lo puede haber escrito una persona: "RK"
#: y "Rechtschaffen y Kales" son la misma intención. Lo usan también la
#: cabecera del `.txt` y el `<Nomenclature>` del XML.
NOMENCLATURE_NAMES: Final[dict[str, Nomenclature]] = {
    **{n.name.lower(): n for n in Nomenclature},
    **{n.value.lower(): n for n in Nomenclature},
}

#: Los nombres de columna del CSV que se reconocen, en minúscula. El primero de
#: cada uno es el que escribe este programa; los otros son los habituales en
#: planillas escritas en inglés.
_COLUMNAS_VENTANA: Final[frozenset[str]] = frozenset({"ventana", "epoch", "window"})
_COLUMNAS_FASE: Final[frozenset[str]] = frozenset({"fase", "stage", "etapa"})
_COLUMNAS_AROUSAL: Final[frozenset[str]] = frozenset({"arousal"})

#: El rótulo de una fase en un EDF+: «Sleep stage 2», «Sleep stage N2»…
_FASE_EDF: Final[re.Pattern[str]] = re.compile(r"^sleep stage\s+(\S+)$", re.IGNORECASE)

#: Qué dice cada rótulo del EDF+. Un código necesita la nomenclatura para
#: volverse fase; una fase explícita, no. El prefijo N es sólo de AASM.
_ROTULOS_EDF: Final[dict[str, int | SleepStage]] = {
    "w": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "r": 5,
    "n1": SleepStage.N1,
    "n2": SleepStage.N2,
    "n3": SleepStage.N3,
    "?": SleepStage.UNSCORED,
}
_MOVIMIENTO_EDF: Final[str] = "movement time"

#: El número con que el NSRR escribe una época sin scorear. Los demás
#: coinciden con los códigos del `.txt`.
_NSRR_SIN_SCOREAR: Final[int] = 9

#: Los meses de la cabecera de un EDF+, para leer el año de cuatro cifras.
_MESES: Final[dict[str, int]] = {
    m: i
    for i, m in enumerate(
        ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
         "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"),
        start=1,
    )
}


@dataclass(frozen=True)
class _Tramo:
    """Épocas que el archivo marca con una misma fase.

    La fase llega de una de dos formas: explícita (`fase`), cuando el rótulo la
    nombra sin ambigüedad, o como código (`codigo`), que necesita la
    nomenclatura para traducirse. `donde` dice en qué parte del archivo estaba,
    para que el error sea accionable.
    """

    ventanas: range
    donde: str
    fase: SleepStage | None = None
    codigo: int | None = None

    def fase_en(self, nomenclature: Nomenclature) -> SleepStage:
        """La fase del tramo en esa nomenclatura. Eleva si no existe en ella."""
        if self.fase is not None:
            if not is_valid(self.fase, nomenclature):
                raise InvalidStageError(
                    f"La fase {self.fase.value} no existe en {nomenclature.value}.",
                )
            return self.fase
        if self.codigo is None:
            raise InvalidStageError("El tramo no trae ninguna fase.")
        return stage_from_code(self.codigo, nomenclature)

    def cabe_en(self, nomenclature: Nomenclature) -> bool:
        try:
            self.fase_en(nomenclature)
        except InvalidStageError:
            return False
        return True

    def rotulo(self) -> str:
        return self.fase.value if self.fase is not None else f"el código {self.codigo}"


@dataclass
class _Lectura:
    """Lo que un lector sacó del archivo, antes de decidir la nomenclatura."""

    tramos: list[_Tramo] = field(default_factory=list)
    #: Épocas y si llevan arousal. El CSV dice sí o no por fila; el EDF+ y el
    #: XML sólo marcan las que sí.
    arousals: list[tuple[range, bool]] = field(default_factory=list)
    declarada: Nomenclature | None = None


# -- La puerta -----------------------------------------------------------------


def read_scoring_file(
    path: Path,
    n_windows: int,
    nomenclature: Nomenclature | None = None,
    start_time: datetime | None = None,
) -> Scoring:
    """Lee un scoring en CSV, EDF+ o XML, según la extensión.

    Args:
        path: el archivo. La extensión decide el lector.
        n_windows: ventanas del registro abierto.
        nomenclature: la que se usa si el archivo no permite saberla.
        start_time: cuándo empezó el registro. Sólo lo usa el EDF+, para
            alinear un hipnograma que empiece en otro momento.

    Raises:
        UndeclaredNomenclatureError: si hace falta la nomenclatura y no hay
            forma de saberla.
        ScoringMismatchError: si el archivo scorea épocas que el registro no
            tiene.
        UnreadableFileError: si el archivo no se puede leer o no tiene el
            formato esperado.
    """
    formato = path.suffix.lower()
    if formato == ".csv":
        lectura = _leer_csv(path)
    elif formato == ".edf":
        lectura = _leer_edf(path, start_time)
    elif formato == ".xml":
        lectura = _leer_xml(path)
    else:
        raise UnreadableFileError(
            f"No se reconoce el formato de scoring de «{path.name}».",
            details=f"Extensión {formato or '(ninguna)'}; se esperaba .csv, .edf o .xml.",
        )
    return _armar_scoring(lectura, path, n_windows, nomenclature)


def _armar_scoring(
    lectura: _Lectura,
    path: Path,
    n_windows: int,
    nomenclature: Nomenclature | None,
) -> Scoring:
    """Decide la nomenclatura y vuelca los tramos sobre un scoring nuevo."""
    if not lectura.tramos:
        raise UnreadableFileError(
            f"«{path.name}» no trae ninguna fase de sueño.",
            details="No se encontró ningún evento ni fila con una fase reconocible.",
        )

    elegida = _elegir_nomenclatura(lectura, path, nomenclature)
    scoring = Scoring(n_windows, elegida)

    for tramo in lectura.tramos:
        fase = tramo.fase_en(elegida)
        if tramo.ventanas.stop > n_windows and fase is not SleepStage.UNSCORED:
            _no_corresponde(path, n_windows, tramo.ventanas.stop, tramo.donde)
        for indice in range(tramo.ventanas.start, min(tramo.ventanas.stop, n_windows)):
            scoring.set_stage(indice, fase)

    for ventanas, arousal in lectura.arousals:
        if arousal and ventanas.stop > n_windows:
            _no_corresponde(path, n_windows, ventanas.stop, "un arousal")
        for indice in range(ventanas.start, min(ventanas.stop, n_windows)):
            scoring.set_arousal(indice, arousal)

    return scoring


def _elegir_nomenclatura(
    lectura: _Lectura, path: Path, pedida: Nomenclature | None
) -> Nomenclature:
    """Aplica el orden del docstring del módulo."""
    compatibles = [
        n for n in Nomenclature if all(t.cabe_en(n) for t in lectura.tramos)
    ]

    if lectura.declarada is not None:
        if lectura.declarada in compatibles:
            return lectura.declarada
        extrano = next(t for t in lectura.tramos if not t.cabe_en(lectura.declarada))
        raise UnreadableFileError(
            f"«{path.name}» declara la nomenclatura {lectura.declarada.value}, pero "
            f"{extrano.donde} trae {extrano.rotulo()}, que no existe en ella.",
            details="La declaración y el contenido del archivo no coinciden.",
        )

    if not compatibles:
        imposible = next(
            (t for t in lectura.tramos if not any(t.cabe_en(n) for n in Nomenclature)),
            None,
        )
        if imposible is not None:
            raise UnreadableFileError(
                f"{_mayuscula(imposible.donde)} de «{path.name}» trae "
                f"{imposible.rotulo()}, que no es una fase de ninguna nomenclatura.",
                details="Nomenclaturas conocidas: "
                + ", ".join(n.value for n in Nomenclature)
                + ".",
            )
        raise UnreadableFileError(
            f"«{path.name}» mezcla fases de Rechtschaffen y Kales con fases de AASM, "
            "así que no se puede leer con ninguna de las dos.",
            details="Hay rótulos o códigos que sólo existen en una y otros que sólo "
            "existen en la otra.",
        )

    if len(compatibles) == 1:
        return compatibles[0]
    if pedida is not None:
        return pedida
    raise UndeclaredNomenclatureError(
        f"«{path.name}» no dice con qué nomenclatura se scoreó, y adivinarla "
        "cargaría toda la noche mal traducida sin que se note: el código 2 es S2 "
        "en Rechtschaffen y Kales y N2 en AASM.",
        details="El archivo no declara la nomenclatura y sus fases existen en las dos.",
    )


def _no_corresponde(path: Path, n_windows: int, hasta: int, donde: str) -> None:
    raise ScoringMismatchError(
        f"El scoring de «{path.name}» no corresponde a este registro: llega hasta "
        f"la ventana {hasta} y el registro tiene {n_windows}.",
        details=f"Lo que se pasa del final está en {donde}.",
    )


# -- CSV -----------------------------------------------------------------------


def _leer_csv(path: Path) -> _Lectura:
    """Una fila por ventana, con las columnas buscadas por nombre.

    El separador se detecta: Excel en español guarda con punto y coma.
    """
    texto = _leer_texto(path)
    try:
        dialecto: type[csv.Dialect] = csv.Sniffer().sniff(
            texto[:4096], delimiters=",;\t"
        )
    except csv.Error:
        dialecto = csv.excel

    filas = [
        (numero, fila)
        for numero, fila in enumerate(csv.reader(texto.splitlines(), dialecto), start=1)
        if any(celda.strip() for celda in fila)
    ]
    if not filas:
        raise UnreadableFileError(f"«{path.name}» está vacío.")

    _, cabecera = filas[0]
    nombres = [celda.strip().lower() for celda in cabecera]
    col_fase = _columna(nombres, _COLUMNAS_FASE)
    if col_fase is None:
        raise UnreadableFileError(
            f"«{path.name}» no tiene una columna «fase».",
            details=f"Columnas encontradas: {', '.join(nombres)}.",
        )
    col_ventana = _columna(nombres, _COLUMNAS_VENTANA)
    col_arousal = _columna(nombres, _COLUMNAS_AROUSAL)

    lectura = _Lectura()
    for posicion, (numero, fila) in enumerate(filas[1:]):
        donde = f"la línea {numero}"
        celdas = [c.strip() for c in fila]
        if len(celdas) < len(nombres):
            celdas += [""] * (len(nombres) - len(celdas))

        if col_ventana is None:
            indice = posicion
        else:
            indice = _entero(celdas[col_ventana], path, donde, "un número de ventana") - 1
            if indice < 0:
                raise UnreadableFileError(
                    f"La línea {numero} de «{path.name}» nombra la ventana "
                    f"{indice + 1}, y las ventanas se cuentan desde 1.",
                )
        ventanas = range(indice, indice + 1)

        lectura.tramos.append(_tramo_csv(celdas[col_fase], ventanas, path, donde))
        if col_arousal is not None:
            valor = celdas[col_arousal] or "0"
            if valor not in ("0", "1"):
                raise UnreadableFileError(
                    f"La línea {numero} de «{path.name}» tiene un arousal que no es 0 ni 1.",
                    details=f"Se leyó {valor!r}.",
                )
            lectura.arousals.append((ventanas, valor == "1"))
    return lectura


def _tramo_csv(valor: str, ventanas: range, path: Path, donde: str) -> _Tramo:
    """La fase de una fila: un rótulo (W, S2, N2, REM…) o un código numérico."""
    if re.fullmatch(r"-?\d+", valor):
        return _Tramo(ventanas, donde, codigo=int(valor))
    rotulo = "-" if valor == "?" else valor.upper()
    try:
        return _Tramo(ventanas, donde, fase=SleepStage(rotulo))
    except ValueError as error:
        raise UnreadableFileError(
            f"{_mayuscula(donde)} de «{path.name}» tiene una fase que no se reconoce: "
            f"«{valor}».",
            details="Se esperaba un rótulo (W, S1…S4, REM, MT, N1…N3, R, -) o un código.",
        ) from error


def _columna(nombres: list[str], aceptados: frozenset[str]) -> int | None:
    return next((i for i, n in enumerate(nombres) if n in aceptados), None)


def _entero(valor: str, path: Path, donde: str, que: str) -> int:
    try:
        return int(valor)
    except ValueError as error:
        raise UnreadableFileError(
            f"{_mayuscula(donde)} de «{path.name}» tiene {que} que no es un número entero.",
            details=f"Se leyó {valor!r}.",
        ) from error


# -- EDF+ ----------------------------------------------------------------------


def _leer_edf(path: Path, start_time: datetime | None) -> _Lectura:
    """Las anotaciones de fase y de arousal de un EDF+.

    Las lee MNE. Una anotación sin duración —algunos programas escriben así una
    por época— cuenta como una época.
    """
    import mne

    try:
        with warnings.catch_warnings(), mne.utils.use_log_level("ERROR"):
            warnings.simplefilter("ignore")
            anotaciones = mne.read_annotations(path)
    except Exception as error:  # noqa: BLE001 - MNE eleva de todo
        raise UnreadableFileError(
            f"No se pudieron leer las anotaciones de «{path.name}»: el archivo está "
            "dañado o no es un EDF+.",
            details=f"{type(error).__name__}: {error}",
        ) from error

    desfase = _desfase_edf(path, start_time)
    lectura = _Lectura()
    for numero, (inicio, duracion, texto) in enumerate(
        zip(anotaciones.onset, anotaciones.duration, anotaciones.description), start=1
    ):
        inicio = float(inicio) + desfase
        duracion = float(duracion) if duracion > 0 else WINDOW_SECONDS
        rotulo = str(texto).strip()
        donde = f"la anotación {numero} («{rotulo}»)"

        if rotulo.lower().startswith("arousal"):
            lectura.arousals.append((windows_in_span(inicio, duracion), True))
            continue

        if rotulo.lower() == _MOVIMIENTO_EDF:
            valor: int | SleepStage = 6
        else:
            coincide = _FASE_EDF.match(rotulo)
            if coincide is None:
                continue  # otra clase de evento: no es asunto del scoring
            clave = coincide.group(1).lower()
            if clave not in _ROTULOS_EDF:
                raise UnreadableFileError(
                    f"{_mayuscula(donde)} de «{path.name}» nombra una fase que no "
                    "se reconoce.",
                    details="Se esperaba Sleep stage W, 1, 2, 3, 4, R, N1, N2, N3 o ?.",
                )
            valor = _ROTULOS_EDF[clave]

        lectura.tramos.append(_tramo_evento(valor, inicio, duracion, path, donde))
    return lectura


def _desfase_edf(path: Path, start_time: datetime | None) -> float:
    """Cuántos segundos después del registro empieza el hipnograma.

    MNE da los inicios relativos al propio archivo de anotaciones. Si ese
    archivo empieza en otro momento que la señal, hay que correrlos; si alguna
    de las dos fechas no se sabe, no hay contra qué alinear y se asume que
    empiezan juntos, que es lo que hacen la Sleep-EDF y este programa.
    """
    if start_time is None:
        return 0.0
    inicio = _inicio_edf(path)
    if inicio is None:
        return 0.0
    if start_time.tzinfo is not None:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
    return (inicio - start_time).total_seconds()


def _inicio_edf(path: Path) -> datetime | None:
    """La fecha y hora de inicio de la cabecera, o None si no se sabe.

    Se lee a mano por el mismo motivo que en `edf.py`: la cabecera está
    congelada desde 1992, y MNE no devuelve la fecha de un archivo de
    anotaciones. El año sale de `Startdate dd-MMM-yyyy` si está, porque el
    campo corto sólo tiene dos cifras.
    """
    try:
        with path.open("rb") as archivo:
            cabecera = archivo.read(184).decode("ascii", errors="replace")
    except OSError:
        return None
    identificacion, fecha, hora = cabecera[88:168], cabecera[168:176], cabecera[176:184]
    partes = identificacion.split()
    if len(partes) >= 2 and partes[0] == "Startdate" and partes[1] == "X":
        return None
    try:
        dia, mes, anio_corto = fecha.split(".")
        horas, minutos, segundos = (int(x) for x in hora.split("."))
        anio = None
        if len(partes) >= 2 and partes[0] == "Startdate":
            _, m, a = partes[1].split("-")
            if m.upper() in _MESES:
                anio = int(a)
        if anio is None:
            corto = int(anio_corto)
            anio = 1900 + corto if corto >= 85 else 2000 + corto
        return datetime(anio, int(mes), int(dia), horas, minutos, segundos)
    except ValueError:
        return None


# -- XML del NSRR ----------------------------------------------------------------


def _leer_xml(path: Path) -> _Lectura:
    """Los `<ScoredEvent>` de fase y de arousal de un `<PSGAnnotation>`."""
    try:
        raiz = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise UnreadableFileError(
            f"No se pudo leer «{path.name}»: el archivo está dañado o no es XML.",
            details=f"{type(error).__name__}: {error}",
        ) from error
    if raiz.tag != "PSGAnnotation":
        raise UnreadableFileError(
            f"«{path.name}» no tiene el formato de scoring del NSRR.",
            details=f"El elemento raíz es <{raiz.tag}> y se esperaba <PSGAnnotation>.",
        )

    lectura = _Lectura()
    declarada = (raiz.findtext("Nomenclature") or "").strip().lower()
    if declarada:
        if declarada not in NOMENCLATURE_NAMES:
            raise UnreadableFileError(
                f"«{path.name}» declara una nomenclatura que no se conoce: "
                f"«{raiz.findtext('Nomenclature')}».",
            )
        lectura.declarada = NOMENCLATURE_NAMES[declarada]

    for numero, evento in enumerate(raiz.iter("ScoredEvent"), start=1):
        tipo = (evento.findtext("EventType") or "").lower()
        concepto = (evento.findtext("EventConcept") or "").strip()
        donde = f"el evento {numero} («{concepto}»)"
        if "stage" not in tipo and "arousal" not in tipo:
            continue
        inicio = _flotante(evento.findtext("Start"), path, donde, "inicio")
        duracion = _flotante(evento.findtext("Duration"), path, donde, "duración")

        if "arousal" in tipo:
            lectura.arousals.append((windows_in_span(inicio, duracion), True))
            continue

        _, _, numero_de_fase = concepto.rpartition("|")
        codigo = _entero(numero_de_fase, path, donde, "un código de fase")
        valor: int | SleepStage = (
            SleepStage.UNSCORED if codigo == _NSRR_SIN_SCOREAR else codigo
        )
        lectura.tramos.append(_tramo_evento(valor, inicio, duracion, path, donde))
    return lectura


def _flotante(valor: str | None, path: Path, donde: str, que: str) -> float:
    try:
        numero = float(valor or "")
    except ValueError as error:
        raise UnreadableFileError(
            f"{_mayuscula(donde)} de «{path.name}» no tiene un {que} válido.",
            details=f"Se leyó {valor!r}.",
        ) from error
    if not math.isfinite(numero):
        raise UnreadableFileError(
            f"{_mayuscula(donde)} de «{path.name}» no tiene un {que} válido.",
            details=f"Se leyó {valor!r}.",
        )
    return numero


# -- Compartido ----------------------------------------------------------------


def _tramo_evento(
    valor: int | SleepStage, inicio: float, duracion: float, path: Path, donde: str
) -> _Tramo:
    """Un evento con inicio y duración, traducido a épocas.

    **Una fase scoreada que empieza antes del registro es un error**, no algo
    que se recorta: con un hipnograma de otra noche, o mal alineado, el
    recorte cargaría la noche corrida sin avisar.
    """
    sin_scorear = valor is SleepStage.UNSCORED
    if inicio < -WINDOW_SECONDS / 2 and not sin_scorear:
        raise ScoringMismatchError(
            f"El scoring de «{path.name}» no corresponde a este registro: "
            f"{donde} empieza {-inicio:g} s antes que la señal.",
            details="Revisá que el archivo de scoring sea el de este registro.",
        )
    ventanas = windows_in_span(inicio, duracion)
    if isinstance(valor, SleepStage):
        return _Tramo(ventanas, donde, fase=valor)
    return _Tramo(ventanas, donde, codigo=valor)


def _leer_texto(path: Path) -> str:
    """El archivo como texto. UTF-8 (con o sin marca de Excel), o latin-1."""
    try:
        crudo = path.read_bytes()
    except OSError as error:
        raise UnreadableFileError(
            f"No se pudo abrir el archivo de scoring «{path.name}».",
            details=f"{type(error).__name__}: {error}",
        ) from error
    try:
        return crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return crudo.decode("latin-1")


def _mayuscula(texto: str) -> str:
    """La primera letra en mayúscula, sin tocar el resto.

    `str.capitalize()` no sirve: pasa todo lo demás a minúscula, y el resto es
    el rótulo del archivo, que el usuario tiene que reconocer tal cual.
    """
    return texto[:1].upper() + texto[1:]
