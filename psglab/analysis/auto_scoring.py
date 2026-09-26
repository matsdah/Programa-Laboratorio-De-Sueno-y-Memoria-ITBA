"""Fases sugeridas por un clasificador: el scoring automático (hito 75).

**Sugiere, no scorea.** Lo que devuelve son `StageSuggestion`, que
`Scoring.set_suggestions()` guarda en una capa aparte de las fases elegidas a
mano: no se exportan, no pisan nada y se confirman a pedido. El motivo está en
los números de abajo: acierta cuatro de cada cinco ventanas, y la quinta hay
que encontrarla.

**El clasificador es el de YASA** (BSD-3), un LightGBM entrenado sobre miles
de noches de la NSRR que viene dentro del paquete: no descarga nada. Mira un
EEG y, si los hay, un EOG y un EMG, y da una fase AASM por ventana de 30 s con
su probabilidad.

**Medido contra un experto** sobre la noche SC4001 de la Sleep-EDF (Fpz-Cz y
EOG; su EMG está a 1 Hz y no se usa), en el período de sueño con media hora de
margen a cada lado:

    acuerdo total            78,5 %
    W 90 %   N1 34 %   N2 86 %   N3 87 %   R 50 %
    con confianza >= 80 %    93 % de acuerdo, sobre el 54 % de las ventanas
    tiempo                   7 s para las 22 horas del registro

N1 y R son las flojas, como en la literatura, y R además sufre sin EMG. La
confianza sí separa: por eso la interfaz ofrece confirmar sólo las seguras.

**Qué rechaza, y por qué no lo corre igual:**

- Un canal grabado a 80 Hz o menos. YASA lo exige, y un canal de 1 Hz llevado
  a 100 Hz por el lector —`Recording.content_limit_hz()`— tiene la forma de una
  señal y ninguno de sus rasgos. Un EOG o un EMG así se deja afuera; un EEG así
  no deja sugerir nada.
- Menos de cinco minutos. Los rasgos del clasificador se promedian sobre siete
  minutos y medio alrededor de cada ventana.

**En macOS, LightGBM necesita OpenMP** (`brew install libomp`) y su rueda no
lo trae. Sin él, cargar el modelo falla con un `OSError` de `dlopen`, que no es
un `PsgLabError` y le llegaba al investigador como el cartel de los errores
inesperados; lo encontró el CI de macOS. Por eso LightGBM se carga junto con
YASA, antes de calcular nada, y la falta sale con un mensaje que dice cómo
arreglarla.

**La señal llega a MNE a 100 Hz**, que es a lo que YASA la lleva de todos
modos. Se remuestrea acá, canal por canal, antes de armar el `Raw`: a 1000 Hz,
pasarle tres canales de ocho horas enteros costaba tres copias de 700 MB.

**El modelo está serializado con scikit-learn 0.24** y se carga con la versión
instalada, con una advertencia de scikit-learn. Hoy funciona; el día que una
versión nueva no pueda leerlo, lo va a decir el test que corre el clasificador
de verdad en el CI, y no un investigador.

Cubre del pliego: ningún ID numerado. Es el «scoring automático» que el pliego
nombra entre sus motivaciones; ver `docs/TRAZABILIDAD.md`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Any, Final

import numpy as np

from psglab.analysis.mne_bridge import _exigir_registro, _registro_parcial, to_raw
from psglab.config import WINDOW_SECONDS
from psglab.core.nomenclature import SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import StageSuggestion
from psglab.core.windows import count_windows
from psglab.utils.errors import StagingNotPossibleError, memoria_suficiente
from psglab.utils.units import is_electrical

#: A qué frecuencia trabaja el clasificador. YASA remuestrea a esto.
FRECUENCIA_DEL_CLASIFICADOR: Final[float] = 100.0

#: Hasta dónde tiene que tener contenido un canal para que sirva: la mitad de
#: los 80 Hz que YASA exige como mínimo.
CONTENIDO_MINIMO_HZ: Final[float] = 40.0

#: Cuánta señal hace falta, en minutos. YASA sólo avisa por debajo de esto.
MINUTOS_MINIMOS: Final[float] = 5.0

#: Qué EEG se prefiere, en orden. El clasificador se entrenó con derivaciones
#: centrales (C4-M1 sobre todo); sin ninguna, se usa el primer EEG que sirva.
_EEG_PREFERIDOS: Final[tuple[str, ...]] = ("C4", "C3", "CZ")

#: Cómo nombra YASA cada fase. Las dos formas cortas por si una versión vuelve
#: a las del modelo, que las usa internamente.
_FASES_DE_YASA: Final[dict[str, SleepStage]] = {
    "WAKE": SleepStage.WAKE,
    "W": SleepStage.WAKE,
    "N1": SleepStage.N1,
    "N2": SleepStage.N2,
    "N3": SleepStage.N3,
    "REM": SleepStage.R,
    "R": SleepStage.R,
}


@dataclass(frozen=True)
class StagingChannels:
    """Qué canales mira el clasificador, y cuáles quedaron afuera por lentos.

    Attributes:
        eeg: el EEG. Siempre hay uno: sin él no hay sugerencias.
        eog: el EOG, o None si no hay ninguno que sirva.
        emg: el EMG, o None si no hay ninguno que sirva.
        too_slow: los EEG, EOG y EMG que no se usan porque se grabaron a
            80 Hz o menos. Están para poder decirlo: un EMG que no se usa
            explica por qué R sale peor.
    """

    eeg: str
    eog: str | None = None
    emg: str | None = None
    too_slow: tuple[str, ...] = ()


def default_channels(recording: Recording) -> StagingChannels:
    """Elige los canales con que sugerir las fases de un registro.

    Un EEG —central si hay—, el primer EOG y el primer EMG, **sólo entre los
    que tienen contenido hasta 40 Hz**: ver el docstring del módulo.

    Raises:
        InvalidRecordingError: si `recording` no es un registro.
        StagingNotPossibleError: si no hay ningún EEG que sirva.
    """
    _exigir_registro(recording, "recording")
    lentos: list[str] = []

    def utiles(clase: ChannelKind) -> list[Channel]:
        sirven = []
        for canal in recording.channels_of_kind(clase):
            if not is_electrical(canal.unit):
                continue
            if _es_lento(recording, canal.name):
                lentos.append(canal.name)
            else:
                sirven.append(canal)
        return sirven

    eegs, eogs, emgs = (utiles(clase) for clase in (ChannelKind.EEG, ChannelKind.EOG, ChannelKind.EMG))
    if not eegs:
        raise StagingNotPossibleError(
            "Para sugerir las fases hace falta un EEG grabado a más de 80 Hz, y "
            "este registro no tiene ninguno.",
            details=f"EEG demasiado lentos: {', '.join(lentos) or 'ninguno'}.",
        )
    return StagingChannels(
        eeg=_el_mas_central(eegs).name,
        eog=eogs[0].name if eogs else None,
        emg=emgs[0].name if emgs else None,
        too_slow=tuple(lentos),
    )


def suggest_stages(
    recording: Recording,
    eeg: str,
    eog: str | None = None,
    emg: str | None = None,
) -> list[StageSuggestion | None]:
    """Sugiere la fase de cada ventana del registro, en AASM.

    Args:
        recording: el registro. **No se lo modifica.**
        eeg: el canal de EEG; ver `default_channels()`.
        eog: el de EOG, u omitido.
        emg: el de EMG, u omitido.

    Returns:
        Una entrada por ventana, lista para `Scoring.set_suggestions()`. La
        última es `None` si el registro no termina en una ventana entera: el
        clasificador sólo mira ventanas completas.

    Raises:
        InvalidRecordingError: si `recording` no es un registro.
        ChannelNotFoundError: si un canal no existe.
        StagingNotPossibleError: si un canal no sirve, si dos papeles apuntan
            al mismo canal, si el registro dura menos de cinco minutos o si
            YASA no está instalado.
    """
    _exigir_registro(recording, "recording")
    papeles = {"eeg": eeg, "eog": eog, "emg": emg}
    if not isinstance(eeg, str):
        raise StagingNotPossibleError(
            "Para sugerir las fases hay que elegir un EEG.",
            details=f"eeg es {type(eeg).__name__}, se esperaba el nombre de un canal.",
        )
    elegidos = {papel: nombre for papel, nombre in papeles.items() if nombre is not None}
    for papel, nombre in elegidos.items():
        _exigir_que_sirva(recording, papel, nombre)
    if len(set(elegidos.values())) != len(elegidos):
        raise StagingNotPossibleError(
            "El mismo canal no puede hacer de EEG, EOG y EMG a la vez.",
            details=f"canales elegidos: {elegidos}.",
        )
    minutos = recording.duration_seconds / 60
    if minutos < MINUTOS_MINIMOS:
        raise StagingNotPossibleError(
            f"Para sugerir las fases hacen falta al menos {MINUTOS_MINIMOS:g} minutos "
            "de registro, y éste es más corto.",
            details=f"duración: {minutos:.1f} min.",
        )
    yasa = _importar_el_clasificador()

    nombres = list(elegidos.values())
    clases = {"eeg": ChannelKind.EEG, "eog": ChannelKind.EOG, "emg": ChannelKind.EMG}
    with memoria_suficiente("sugerir las fases"):
        parcial = _registro_parcial(
            recording,
            nombres,
            _a_la_frecuencia_del_clasificador(recording, nombres),
            FRECUENCIA_DEL_CLASIFICADOR,
        )
        # **La clase según el papel y no según el canal.** YASA pasa a µV por
        # tipo de canal de MNE: un EEG que el lector no reconoció como tal
        # llegaría como «misc» y el clasificador lo leería en volts.
        parcial = replace(
            parcial,
            channels=[
                replace(canal, kind=clases[papel])
                for canal, papel in zip(parcial.channels, elegidos)
            ],
        )
        raw = to_raw(parcial)
        hipnograma = yasa.SleepStaging(
            raw, eeg_name=eeg, eog_name=eog, emg_name=emg
        ).predict()

    fases = [str(fase) for fase in hipnograma.hypno.to_numpy()]
    confianzas = np.asarray(hipnograma.proba.max(axis=1), dtype=float)
    sugeridas: list[StageSuggestion | None] = [
        StageSuggestion(_fase(fase), min(1.0, max(0.0, float(confianza))))
        for fase, confianza in zip(fases, confianzas)
    ]
    ventanas = count_windows(recording.n_samples, recording.sampling_rate, WINDOW_SECONDS)
    return (sugeridas + [None] * ventanas)[:ventanas]


def _importar_el_clasificador() -> Any:
    """YASA, con LightGBM ya cargado; ver el docstring del módulo."""
    try:
        import yasa
        import lightgbm  # noqa: F401  # Carga la biblioteca nativa acá.
    except ImportError as error:
        raise StagingNotPossibleError(
            "Para sugerir las fases falta instalar YASA, que está en "
            "requirements-analysis.txt.",
            details=str(error),
        ) from error
    except OSError as error:
        raise StagingNotPossibleError(
            "El clasificador de las fases no pudo cargar una biblioteca del "
            "sistema. En macOS es OpenMP, y se instala con «brew install libomp».",
            details=str(error),
        ) from error
    return yasa


def _es_lento(recording: Recording, nombre: str) -> bool:
    return recording.content_limit_hz(nombre) <= CONTENIDO_MINIMO_HZ


def _exigir_que_sirva(recording: Recording, papel: str, nombre: object) -> None:
    """Un canal que existe, que es eléctrico y que no es lento."""
    if not isinstance(nombre, str):
        raise StagingNotPossibleError(
            f"El canal elegido como {papel.upper()} no es un nombre de canal.",
            details=f"{papel} es {type(nombre).__name__}.",
        )
    canal = recording.channel_by_name(nombre)
    if not is_electrical(canal.unit):
        raise StagingNotPossibleError(
            f"«{nombre}» no es una señal eléctrica, así que no puede hacer de "
            f"{papel.upper()}.",
            details=f"unidad: {canal.unit!r}.",
        )
    if _es_lento(recording, nombre):
        raise StagingNotPossibleError(
            f"«{nombre}» se grabó demasiado lento para sugerir fases: hace falta "
            "más de 80 Hz.",
            details=f"contenido hasta {recording.content_limit_hz(nombre):g} Hz.",
        )


def _el_mas_central(eegs: list[Channel]) -> Channel:
    """El primer EEG con una derivación preferida en el nombre, o el primero."""
    for preferido in _EEG_PREFERIDOS:
        for canal in eegs:
            if preferido in re.split(r"[^A-Z0-9]+", canal.name.upper()):
                return canal
    return eegs[0]


def _a_la_frecuencia_del_clasificador(recording: Recording, nombres: list[str]) -> np.ndarray:
    """Las filas pedidas, remuestreadas a 100 Hz de a una.

    `resample_poly` filtra antes de diezmar, así que no hay aliasing. La razón
    se busca como fracción exacta: 256 Hz es 25/64 de 100.
    """
    filas = [recording.channel_by_name(nombre).index for nombre in nombres]
    if recording.sampling_rate == FRECUENCIA_DEL_CLASIFICADOR:
        return recording.data[filas]
    from scipy.signal import resample_poly

    razon = Fraction(FRECUENCIA_DEL_CLASIFICADOR).limit_denominator() / Fraction(
        recording.sampling_rate
    ).limit_denominator(1000)
    return np.vstack(
        [resample_poly(recording.data[fila], razon.numerator, razon.denominator) for fila in filas]
    )


def _fase(etiqueta: str) -> SleepStage:
    try:
        return _FASES_DE_YASA[etiqueta]
    except KeyError:
        raise StagingNotPossibleError(
            "El clasificador devolvió una fase que el programa no conoce.",
            details=f"fase: {etiqueta!r}.",
        ) from None
