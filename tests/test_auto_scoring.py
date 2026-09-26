"""Tests de las fases sugeridas por el clasificador (hito 75).

**Corren el clasificador de verdad**, sobre señal sintética. No pueden medir
qué tan bien scorea —eso se midió a mano contra un experto, y está en el
docstring del módulo—, pero sí lo que se rompería sin que nadie lo notara:
que el modelo de YASA todavía se deje cargar con el scikit-learn instalado, y
que la señal le llegue en la unidad y la frecuencia correctas.

Lo que se afirma es **lo que una señal sintética sostiene**. Se probó: un tramo
de alfa sobre fondo 1/f sale vigilia en todas las ventanas, y uno lento y
amplio sale sueño; **qué** fase de sueño depende de detalles del fondo que una
señal inventada no reproduce, así que eso no se afirma.
"""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import butter, sosfiltfilt

from psglab.analysis.auto_scoring import default_channels, suggest_stages
from psglab.config import WINDOW_SECONDS
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.windows import count_windows
from psglab.utils.errors import ChannelNotFoundError, StagingNotPossibleError

#: Minutos de vigilia y de sueño de la noche sintética.
MINUTOS_DESPIERTO = 30
MINUTOS_DORMIDO = 90


def _rosa(rng: np.random.Generator, n: int, fs: float, exponente: float) -> np.ndarray:
    """Ruido con espectro 1/f^exponente, de desvío 1."""
    frecuencias = np.fft.rfftfreq(n, 1 / fs)
    frecuencias[0] = frecuencias[1]
    espectro = (rng.normal(size=frecuencias.size) + 1j * rng.normal(size=frecuencias.size)) / (
        frecuencias ** (exponente / 2)
    )
    senal = np.fft.irfft(espectro, n)
    return senal / senal.std()


def _alfa(rng: np.random.Generator, n: int, fs: float) -> np.ndarray:
    senal = sosfiltfilt(butter(4, [8, 12], "bandpass", fs=fs, output="sos"), rng.normal(size=n))
    return senal / senal.std()


def noche(fs: float = 100.0, sobra_segundos: float = 10.0, canales: list[Channel] | None = None) -> Recording:
    """Media hora de vigilia y hora y media de sueño, en µV.

    Vigilia: alfa de 15 µV sobre fondo 1/f de 15 µV. Sueño: fondo 1/f^2,5 de
    60 µV. Sobran unos segundos al final para que la última ventana quede
    incompleta, que el clasificador no mira.
    """
    rng = np.random.default_rng(75)
    despierto = int(MINUTOS_DESPIERTO * 60 * fs)
    dormido = int(MINUTOS_DORMIDO * 60 * fs + sobra_segundos * fs)
    eeg = np.concatenate(
        [
            15 * _alfa(rng, despierto, fs) + 15 * _rosa(rng, despierto, fs, 1.0),
            60 * _rosa(rng, dormido, fs, 2.5),
        ]
    )
    canales = canales or [Channel("C4-M1", ChannelKind.EEG, "µV", 0)]
    datos = np.vstack([eeg] + [5 * rng.normal(size=eeg.size) for _ in canales[1:]])
    return Recording(Path("noche.edf"), canales, datos, fs)


def registro_corto(canales: list[Channel], segundos: float = 60.0, fs: float = 100.0) -> Recording:
    return Recording(Path("corto.edf"), canales, np.zeros((len(canales), int(segundos * fs))), fs)


@pytest.fixture(scope="module")
def noche_de_100() -> Recording:
    return noche()


@pytest.fixture(scope="module")
def sugeridas_de_100(noche_de_100) -> list:
    return suggest_stages(noche_de_100, "C4-M1")


def _fases(sugeridas: list, desde_min: float, hasta_min: float) -> list[SleepStage]:
    """Las fases sugeridas en un tramo, dejando afuera dos ventanas en cada
    borde: el clasificador promedia sobre varios minutos y las transiciones
    no son de nadie."""
    por_minuto = 60 / WINDOW_SECONDS
    desde, hasta = int(desde_min * por_minuto) + 2, int(hasta_min * por_minuto) - 2
    return [s.stage for s in sugeridas[desde:hasta]]


def _fraccion(fases: list[SleepStage], cual) -> float:
    return sum(1 for fase in fases if cual(fase)) / len(fases)


# -- El clasificador de verdad ----------------------------------------------


def test_la_vigilia_sale_vigilia(sugeridas_de_100):
    """Si el modelo dejara de cargarse, o la señal le llegara en volts, esto es
    lo primero que se cae."""
    fases = _fases(sugeridas_de_100, 0, MINUTOS_DESPIERTO)
    assert _fraccion(fases, lambda f: f is SleepStage.WAKE) >= 0.9


def test_el_sueno_sale_sueno(sugeridas_de_100):
    fases = _fases(sugeridas_de_100, MINUTOS_DESPIERTO, MINUTOS_DESPIERTO + MINUTOS_DORMIDO)
    assert _fraccion(fases, lambda f: f is not SleepStage.WAKE) >= 0.8


def test_hay_una_sugerencia_por_ventana_completa(noche_de_100, sugeridas_de_100):
    """El largo es el del scoring, así que entra en `set_suggestions()`. La
    última ventana está incompleta y queda sin sugerencia."""
    ventanas = count_windows(noche_de_100.n_samples, noche_de_100.sampling_rate)
    scoring = Scoring(ventanas, Nomenclature.AASM)
    scoring.set_suggestions(sugeridas_de_100)

    assert all(s is not None for s in sugeridas_de_100[:-1])
    assert sugeridas_de_100[-1] is None
    assert scoring.pending_suggestions() == ventanas - 1
    assert all(0.0 <= s.confidence <= 1.0 for s in sugeridas_de_100[:-1])


def test_las_fases_son_de_la_aasm(sugeridas_de_100):
    fases = {s.stage for s in sugeridas_de_100 if s is not None}
    assert fases <= {SleepStage.WAKE, SleepStage.N1, SleepStage.N2, SleepStage.N3, SleepStage.R}


def test_a_200_hz_se_remuestrea_y_da_lo_mismo():
    """**Se remuestrea acá y no en YASA**, para no pasarle a MNE la noche
    entera a la frecuencia original. Con la razón mal calculada, el
    clasificador vería otra cantidad de ventanas o la señal a otra velocidad."""
    registro = noche(fs=200.0)
    sugeridas = suggest_stages(registro, "C4-M1")

    assert all(s is not None for s in sugeridas[:-1])
    assert _fraccion(_fases(sugeridas, 0, MINUTOS_DESPIERTO), lambda f: f is SleepStage.WAKE) >= 0.9
    # Con la razón al revés el tiempo se estira: el sueño caería más allá del
    # final y las ventanas de sueño verían vigilia.
    dormido = _fases(sugeridas, MINUTOS_DESPIERTO, MINUTOS_DESPIERTO + MINUTOS_DORMIDO)
    assert _fraccion(dormido, lambda f: f is not SleepStage.WAKE) >= 0.8


def test_la_clase_del_canal_la_decide_el_papel(noche_de_100, sugeridas_de_100):
    """Un EEG que el lector no reconoció como tal llega a MNE como «misc», y
    YASA lo leería en volts: la clase se fija según el papel que cumple.

    **Tiene que dar exactamente lo mismo**, no sólo vigilia donde hay alfa:
    casi todos los rasgos del clasificador son relativos, y con la señal un
    millón de veces más chica la vigilia seguía saliendo vigilia."""
    sin_clase = replace(
        noche_de_100,
        channels=[replace(noche_de_100.channels[0], kind=ChannelKind.OTHER)],
    )

    assert suggest_stages(sin_clase, "C4-M1") == sugeridas_de_100


def test_no_modifica_el_registro(noche_de_100, sugeridas_de_100):
    antes = noche_de_100.data.copy()
    suggest_stages(noche_de_100, "C4-M1")
    assert np.array_equal(noche_de_100.data, antes)


# -- Qué canales elige -------------------------------------------------------


def test_prefiere_un_eeg_central():
    registro = registro_corto(
        [
            Channel("Fp1", ChannelKind.EEG, "µV", 0),
            Channel("C3-A2", ChannelKind.EEG, "µV", 1),
            Channel("EOG izq", ChannelKind.EOG, "µV", 2),
            Channel("EMG mentón", ChannelKind.EMG, "µV", 3),
        ]
    )
    canales = default_channels(registro)

    assert (canales.eeg, canales.eog, canales.emg) == ("C3-A2", "EOG izq", "EMG mentón")


def test_c4_gana_a_c3():
    registro = registro_corto(
        [Channel("C3", ChannelKind.EEG, "µV", 0), Channel("C4", ChannelKind.EEG, "µV", 1)]
    )
    assert default_channels(registro).eeg == "C4"


def test_sin_eeg_central_usa_el_primero():
    registro = registro_corto(
        [Channel("EEG Fpz-Oz", ChannelKind.EEG, "µV", 0), Channel("O1", ChannelKind.EEG, "µV", 1)]
    )
    assert default_channels(registro).eeg == "EEG Fpz-Oz"


def test_un_emg_lento_queda_afuera_y_se_dice():
    """Es el caso de la Sleep-EDF: el EMG viene a 1 Hz y el lector lo lleva a
    100. Tiene la forma de una señal y ninguno de sus rasgos."""
    registro = registro_corto(
        [
            Channel("C4", ChannelKind.EEG, "µV", 0),
            Channel("EMG submental", ChannelKind.EMG, "µV", 1, original_sampling_rate=1.0),
        ]
    )
    canales = default_channels(registro)

    assert canales.emg is None
    assert canales.too_slow == ("EMG submental",)


def test_sin_un_eeg_que_sirva_no_se_puede():
    registro = registro_corto(
        [
            Channel("C4", ChannelKind.EEG, "µV", 0, original_sampling_rate=50.0),
            Channel("EOG", ChannelKind.EOG, "µV", 1),
        ]
    )
    with pytest.raises(StagingNotPossibleError, match="80 Hz") as error:
        default_channels(registro)
    assert "C4" in error.value.details


def test_un_registro_de_80_hz_no_alcanza():
    """YASA pide más de 80 Hz: a 80, el contenido llega justo a 40."""
    registro = registro_corto([Channel("C4", ChannelKind.EEG, "µV", 0)], fs=80.0)
    with pytest.raises(StagingNotPossibleError):
        default_channels(registro)


# -- Qué rechaza -------------------------------------------------------------


def test_menos_de_cinco_minutos_no_alcanza():
    registro = registro_corto([Channel("C4", ChannelKind.EEG, "µV", 0)], segundos=4 * 60)
    with pytest.raises(StagingNotPossibleError, match="5 minutos"):
        suggest_stages(registro, "C4")


def test_un_canal_lento_no_puede_cumplir_ningun_papel():
    registro = registro_corto(
        [
            Channel("C4", ChannelKind.EEG, "µV", 0),
            Channel("EMG", ChannelKind.EMG, "µV", 1, original_sampling_rate=1.0),
        ],
        segundos=600,
    )
    with pytest.raises(StagingNotPossibleError, match="lento"):
        suggest_stages(registro, "C4", emg="EMG")


def test_un_canal_que_no_es_electrico_no_sirve():
    registro = registro_corto(
        [Channel("C4", ChannelKind.EEG, "µV", 0), Channel("Temp", ChannelKind.OTHER, "DegC", 1)],
        segundos=600,
    )
    with pytest.raises(StagingNotPossibleError, match="eléctrica"):
        suggest_stages(registro, "C4", eog="Temp")


def test_el_mismo_canal_no_cumple_dos_papeles():
    registro = registro_corto([Channel("C4", ChannelKind.EEG, "µV", 0)], segundos=600)
    with pytest.raises(StagingNotPossibleError, match="a la vez"):
        suggest_stages(registro, "C4", eog="C4")


def test_un_canal_que_no_existe():
    registro = registro_corto([Channel("C4", ChannelKind.EEG, "µV", 0)], segundos=600)
    with pytest.raises(ChannelNotFoundError):
        suggest_stages(registro, "C3")


def test_sin_yasa_lo_dice_en_vez_de_una_traza(monkeypatch):
    """Los imports son diferidos: sin esto, el `ModuleNotFoundError` le
    llegaría al investigador sin decir que falta un requirements."""
    monkeypatch.setitem(__import__("sys").modules, "yasa", None)
    registro = registro_corto([Channel("C4", ChannelKind.EEG, "µV", 0)], segundos=600)
    with pytest.raises(StagingNotPossibleError, match="requirements-analysis"):
        suggest_stages(registro, "C4")
