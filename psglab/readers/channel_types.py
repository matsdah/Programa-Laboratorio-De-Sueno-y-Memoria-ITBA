"""Detección automática de la clase de cada canal.

El pliego (V4_F de "Visualización de la señal") pide que el software detecte
solo si un canal es EEG, EOG, EMG, ECG u otra cosa, y que lo muestre junto al
nombre del canal. Sin esto, el usuario tendría que clasificar a mano decenas
de canales en cada registro.

La detección se basa en el nombre del canal, porque es lo único que traen
todos los formatos de forma confiable. Se usan dos fuentes:

    1. Los nombres estándar del sistema 10-20 (C3, C4, Fz, O1, ...).
    2. Patrones habituales en los registros del laboratorio (EOG, EMG, ECG,
       Chin, Resp, ...).

Si el nombre no coincide con nada, el canal se clasifica como OTHER y se
muestra igual: el pliego pide explícitamente que no haya limitación de tipo.

**Los patrones se anclan al comienzo de una palabra.** Buscados en cualquier
parte del nombre, `loc` encontraba EOG en «Clock», `e1` en «Line1», `ojo` en
«Cable rojo» y `chin` encontraba EMG en «Machine».

Cubre del pliego: V4_F de "Visualización de la señal".
"""

import re
import unicodedata
from typing import Final

from psglab.core.recording import ChannelKind
from psglab.utils.units import is_electrical

#: Nombres del sistema internacional 10-20, en minúscula y sin el número.
#:
#: **Se comparan contra los tokens del nombre, no contra su principio.** La
#: diferencia no es cosmética y se midió sobre el registro de prueba: comparando
#: prefijos, `"Temp rectal"` empieza con `"t"` y salía **EEG**, mientras que
#: `"EEG Fpz-Cz"` empieza con `"e"` y no coincidía con nada, así que los dos
#: canales de EEG del único registro real —la señal que se scorea— caían en
#: OTHER. Partiendo el nombre en tokens, la posición de `"EEG Fpz-Cz"` es `Fpz`
#: y `"Temp rectal"` no tiene ninguna.
EEG_POSITIONS: Final[tuple[str, ...]] = (
    "fp", "af", "f", "ft", "fc", "t", "c", "tp", "cp", "p", "po", "o", "iz",
)

#: Los electrodos de referencia: mastoides (M1, M2) y lóbulos de la oreja
#: (A1, A2). Grabados solos son EEG, y **tienen que serlo** para que una
#: derivación como «C4-M1» herede la clase del EEG: `analysis/derivation.py`
#: le da la clase de sus dos canales sólo si coinciden.
EEG_REFERENCES: Final[tuple[str, ...]] = ("m1", "m2", "a1", "a2")

#: Patrones por clase de señal. Se evalúan en orden: el primero que coincide
#: gana, así que los patrones más específicos van primero.
#:
#: Se buscan sobre los tokens unidos por espacios, y **los cortos empiezan en
#: el comienzo de una palabra** (`\b`). Algunos exigen además la palabra
#: entera: «LAT» y «RAT» son los tibiales anteriores, pero `\blat` a secas
#: sería también «Lateral». Los nombres de clase —`eog`, `emg`, `ecg`,
#: `ekg`— siguen valiendo en cualquier parte, porque «HEOG», «VEOG» o
#: «ChinEMG» los llevan pegados y ninguna palabra común los contiene.
#:
#: - **EOG**: `E1` y `E2` son los nombres de la AASM para los dos ojos.
#: - **EMG**: «Leg», «LAT» y «RAT» son las piernas; «LLEG1-RLEG1» también.
#: - **Respiratorio**: el esfuerzo (ABD, THO, Chest, Effort), el flujo
#:   (Therm, Nasal, Pres, PTAF, Cannula) y la oximetría (SpO2, Pleth, Pulse).
#:   La oximetría no tiene clase propia y va acá, donde ya iba la SpO2: es lo
#:   que se mira junto con el flujo, y así se escala sola como él.
#:
#: **La posición del cuerpo («Pos») queda en OTHER a propósito**: no es de
#: ninguna de estas clases, y darle una la agruparía con lo que no es.
KIND_PATTERNS: Final[tuple[tuple[ChannelKind, str], ...]] = (
    (ChannelKind.EOG, r"eog|\b(?:loc|roc|e[12])\d*\b|\bojo"),
    (
        ChannelKind.EMG,
        r"emg|\bchin|\bmenton|\btib|\bbarbilla|\bsubment"
        r"|\b[lr]?legs?\d*\b|\b(?:lat|rat)\d*\b|\bpierna",
    ),
    (ChannelKind.ECG, r"ecg|ekg|\bcardio"),
    (
        ChannelKind.RESPIRATORY,
        r"\bresp|flow|\bflujo|\btho|\babd|\bchest|\beffort|\besfuerzo"
        r"|\btherm|\bnasal|\bpres|\bptaf|\bcannula|\bcanula"
        r"|snore|\bronqu|\bsao2|\bspo2|\bpleth|\bpulse|\bpulso|\bco2|\betco2",
    ),
)


#: Un token es una posición 10-20 si es el nombre solo, o seguido de "z" (línea
#: media) o de uno o dos dígitos: "c3", "cz", "fpz", "o1". Se ordenan de más
#: largo a más corto para que "fp" gane antes que "f".
_POSICION_10_20: Final[re.Pattern[str]] = re.compile(
    r"^(?:" + "|".join(sorted(EEG_POSITIONS, key=len, reverse=True)) + r")(?:z|\d{1,2})?$"
)

#: Un token que es un electrodo de referencia, entero.
_REFERENCIA: Final[re.Pattern[str]] = re.compile(r"^(?:" + "|".join(EEG_REFERENCES) + r")$")

#: Un canal llamado sólo "EEG" o "EEG2" no nombra ninguna posición, y aun así
#: declara su clase. Es lo que traen los montajes que ya vienen derivados.
_EEG_EXPLICITO: Final[re.Pattern[str]] = re.compile(r"^eeg\d*$")

#: Clases que sólo tienen sentido en un canal eléctrico. Sirven de veto: un
#: termómetro no es un EEG por más que su nombre lo sugiera, y el `unit` del
#: archivo es la forma barata de saberlo.
ELECTRICAL_KINDS: Final[frozenset[ChannelKind]] = frozenset(
    {ChannelKind.EEG, ChannelKind.EOG, ChannelKind.EMG, ChannelKind.ECG}
)


def _tokens(name: str) -> list[str]:
    """Parte el nombre del canal en palabras comparables.

    Separa por todo lo que no sea letra o dígito, que es lo que hace legibles
    los nombres reales: "EEG Fpz-Cz" da ["eeg", "fpz", "cz"] y "Fp1-A2" da
    ["fp1", "a2"].

    **Antes le saca los acentos**: si no, «Mentón» se partía en «ment» y «n»
    y ya no era EMG, y «Presión» dejaba de ser respiratorio.
    """
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", name.lower()) if not unicodedata.combining(c)
    )
    return [t for t in re.split(r"[^a-z0-9]+", sin_acentos) if t]


def detect_channel_kind(name: str, unit: str | None = None) -> ChannelKind:
    """Deduce la clase de un canal a partir de su nombre.

    Args:
        name: nombre del canal tal como viene en el archivo.
        unit: unidad declarada en el archivo, si la hay. Ayuda a descartar
            falsos positivos (un canal en °C no es un EEG).

    El orden es: patrones explícitos, después posición 10-20 o electrodo de
    referencia, y OTHER si no coincide nada. Sobre eso se aplica el **veto de la unidad**: una clase
    eléctrica con una unidad que no lo es se degrada a OTHER, porque el archivo
    sabe más que el nombre. Es lo que salva a `"Temp rectal"` aunque alguien
    vuelva a poner los prefijos voraces.

    No eleva nunca: un canal que no se reconoce es OTHER y se muestra igual,
    que es lo que pide el pliego al no limitar por tipo de señal.

    Returns:
        La clase detectada, o `ChannelKind.OTHER` si no se reconoce.
    """
    if not isinstance(name, str):
        return ChannelKind.OTHER

    tokens = _tokens(name)
    unido = " ".join(tokens)

    detectada = ChannelKind.OTHER
    for kind, patron in KIND_PATTERNS:
        if re.search(patron, unido):
            detectada = kind
            break
    else:
        if any(
            _EEG_EXPLICITO.match(t) or _POSICION_10_20.match(t) or _REFERENCIA.match(t)
            for t in tokens
        ):
            detectada = ChannelKind.EEG

    # El veto. `unit is None` significa "el formato no lo dice", que no es lo
    # mismo que "no es eléctrico": ahí no se veta nada.
    if unit is not None and detectada in ELECTRICAL_KINDS and not is_electrical(unit):
        return ChannelKind.OTHER
    return detectada


def detect_all(names: list[str], units: list[str] | None = None) -> list[ChannelKind]:
    """Detecta la clase de una lista de canales de una sola vez.

    `units` puede faltar, o traer menos elementos que `names`: un formato que no
    declare la unidad de todos sus canales no es un error, y lo que falte se
    trata como "no lo dice".
    """
    return [
        detect_channel_kind(
            nombre,
            units[i] if units is not None and i < len(units) else None,
        )
        for i, nombre in enumerate(names)
    ]


def is_eeg_position(name: str) -> bool:
    """Indica si el nombre corresponde a una posición del sistema 10-20.

    Alcanza con que **alguno** de sus tokens lo sea: los montajes bipolares se
    nombran con las dos posiciones ("Fpz-Cz") y los referenciados agregan la
    referencia ("Fp1-A2"), así que exigir que el nombre entero fuera una
    posición dejaría afuera a casi todos los canales reales.
    """
    if not isinstance(name, str):
        return False
    return any(_POSICION_10_20.match(t) for t in _tokens(name))
