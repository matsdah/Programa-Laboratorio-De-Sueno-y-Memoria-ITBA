"""Tests de la densidad espectral de potencia.

**Es el caso de test más limpio del proyecto**, y el que `conftest.py` usa para
explicar por qué la señal sintética es mejor que un registro real: si se genera
una onda de 10 Hz, la PSD tiene que dar un pico en 10 Hz, y eso se puede
afirmar. La fixture `registro_sintetico` trae los cuatro canales en frecuencias
distintas y conocidas, así que cada uno es su propio testigo.

Lo demás que se afirma acá son las decisiones que el esqueleto dejaba abiertas:
la banda semiabierta, contra qué normaliza `relative`, y **qué se hace con la
última ventana incompleta**, que es la convención que después copian
`complexity.py` y `connectivity.py`.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.psd import (
    DEFAULT_BANDS,
    METHODS,
    WELCH_SEGMENT_SECONDS,
    band_power,
    band_powers_by_window,
    compute_psd,
)
from psglab.config import WINDOW_SECONDS
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.windows import count_windows
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidBandError,
    InvalidRecordingError,
    PsgLabError,
    UnknownPsdMethodError,
    WindowOutOfRangeError,
)
from psglab.utils.units import MICROVOLT

from conftest import VENTANAS_SINTETICAS


def pico(frecuencias: np.ndarray, potencias: np.ndarray) -> float:
    """La frecuencia donde la PSD tiene su máximo."""
    return float(frecuencias[int(np.argmax(potencias))])


# -- El caso testigo ---------------------------------------------------------


def test_una_onda_de_diez_hercios_da_un_pico_en_diez(registro_sintetico: Recording):
    """El ejemplo que `conftest.py` usa para justificar la señal sintética."""
    frecuencias, potencias = compute_psd(registro_sintetico, channels=["C4"])

    assert pico(frecuencias, potencias[0]) == pytest.approx(10.0, abs=0.3)


def test_cada_canal_da_su_pico(registro_sintetico: Recording):
    """Cuatro frecuencias distintas y conocidas: si dos canales se permutaran,
    dos picos caerían en el lugar del otro."""
    frecuencias, potencias = compute_psd(registro_sintetico)

    esperados = [1.0, 10.0, 0.5, 30.0]
    for posicion, esperado in enumerate(esperados):
        assert pico(frecuencias, potencias[posicion]) == pytest.approx(
            esperado, abs=0.3
        )


def test_la_forma_es_canales_por_frecuencias(registro_sintetico: Recording):
    frecuencias, potencias = compute_psd(registro_sintetico)

    assert potencias.shape == (registro_sintetico.n_channels, len(frecuencias))


def test_elegir_canales_devuelve_solo_esos(registro_sintetico: Recording):
    _, potencias = compute_psd(registro_sintetico, channels=["C4", "EMG-menton"])

    assert potencias.shape[0] == 2


def test_la_resolucion_sale_del_segmento_declarado(registro_sintetico: Recording):
    """`WELCH_SEGMENT_SECONDS` fija la resolución en `1 / segmento`, y de eso
    depende que delta se pueda mirar desde 0,5 Hz."""
    frecuencias, _ = compute_psd(registro_sintetico)
    paso = float(frecuencias[1] - frecuencias[0])

    assert paso == pytest.approx(1.0 / WELCH_SEGMENT_SECONDS)


def test_una_sola_ventana_tambien_da_su_pico(registro_sintetico: Recording):
    frecuencias, potencias = compute_psd(
        registro_sintetico, channels=["C4"], window_index=3
    )

    assert pico(frecuencias, potencias[0]) == pytest.approx(10.0, abs=0.3)


def test_multitaper_encuentra_el_mismo_pico(registro_sintetico: Recording):
    """Los dos métodos estiman la misma magnitud: si dieran picos distintos,
    uno de los dos estaría mal."""
    frecuencias, potencias = compute_psd(
        registro_sintetico, channels=["C4"], method="multitaper"
    )

    assert pico(frecuencias, potencias[0]) == pytest.approx(10.0, abs=0.3)


# -- La potencia por banda ---------------------------------------------------


def test_la_onda_de_diez_pone_su_potencia_en_alpha(registro_sintetico: Recording):
    """10 Hz cae en Alpha (8–12) y no en Delta (0,5–4)."""
    frecuencias, potencias = compute_psd(registro_sintetico, channels=["C4"])

    alpha = band_power(frecuencias, potencias, DEFAULT_BANDS["Alpha"])
    delta = band_power(frecuencias, potencias, DEFAULT_BANDS["Delta"])

    assert alpha[0] > delta[0] * 100


def test_la_potencia_relativa_de_toda_la_psd_es_uno(registro_sintetico: Recording):
    """Normaliza contra toda la PSD calculada, así que la banda completa da 1."""
    frecuencias, potencias = compute_psd(registro_sintetico, channels=["C4"])
    entera = (float(frecuencias[0]), float(frecuencias[-1]) + 1.0)

    relativa = band_power(frecuencias, potencias, entera, relative=True)

    assert relativa[0] == pytest.approx(1.0, abs=1e-6)


def test_la_relativa_esta_entre_cero_y_uno(registro_sintetico: Recording):
    frecuencias, potencias = compute_psd(registro_sintetico)

    for banda in DEFAULT_BANDS.values():
        relativa = band_power(frecuencias, potencias, banda, relative=True)
        assert np.all(relativa >= 0.0)
        assert np.all(relativa <= 1.0)


def test_las_bandas_convencionales_no_se_pisan(registro_sintetico: Recording):
    """**La banda es semiabierta a propósito.** Delta termina en 4 Hz y theta
    empieza ahí: con los dos extremos incluidos, ese bin se contaría dos veces
    y las relativas sumarían más de 1 sin que nada fallara.
    """
    frecuencias, potencias = compute_psd(registro_sintetico)

    suma = sum(
        band_power(frecuencias, potencias, banda, relative=True)[1]
        for banda in DEFAULT_BANDS.values()
    )
    assert suma <= 1.0 + 1e-9


def test_una_psd_de_un_solo_canal_da_un_escalar(registro_sintetico: Recording):
    """La forma de la salida sigue a la de la entrada sin su último eje."""
    frecuencias, potencias = compute_psd(registro_sintetico, channels=["C4"])

    assert band_power(frecuencias, potencias[0], DEFAULT_BANDS["Alpha"]).shape == ()


def test_un_canal_plano_da_relativa_cero():
    """Su potencia total es cero y la fracción no está definida. Cero es la
    respuesta que no miente: no hay potencia en la banda."""
    frecuencias = np.linspace(0.0, 50.0, 201)
    plana = np.zeros((1, 201))

    assert band_power(frecuencias, plana, (8.0, 12.0), relative=True)[0] == 0.0


# -- La noche entera, ventana por ventana ------------------------------------


def test_hay_un_valor_por_ventana(registro_sintetico: Recording):
    """Es lo que permite graficarlo contra el hipnograma sin alinear nada."""
    por_ventana = band_powers_by_window(registro_sintetico, ["C4"])

    assert len(por_ventana["C4"]["Alpha"]) == VENTANAS_SINTETICAS


def test_estan_todas_las_bandas_y_todos_los_canales(registro_sintetico: Recording):
    por_ventana = band_powers_by_window(registro_sintetico, ["C3", "C4"])

    assert set(por_ventana) == {"C3", "C4"}
    assert set(por_ventana["C3"]) == set(DEFAULT_BANDS)


def test_una_señal_estacionaria_da_lo_mismo_en_todas_las_ventanas(
    registro_sintetico: Recording,
):
    """La fixture es una senoide pura: si una ventana diera distinto, sería la
    conversión de ventana a muestras la que está mal."""
    alpha = band_powers_by_window(registro_sintetico, ["C4"])["C4"]["Alpha"]

    assert np.allclose(alpha, alpha[0], rtol=0.05)


def test_se_pueden_pedir_bandas_propias(registro_sintetico: Recording):
    """Los límites varían entre laboratorios, y por eso son editables."""
    por_ventana = band_powers_by_window(
        registro_sintetico, ["C4"], bands={"mia": (9.0, 11.0)}
    )

    assert set(por_ventana["C4"]) == {"mia"}
    assert np.all(por_ventana["C4"]["mia"] > 0)


# -- La última ventana incompleta, que es la convención ----------------------


def registro_con_cola(segundos_de_cola: float, fs: float = 256.0) -> Recording:
    """Dos ventanas completas más una cola de la duración pedida."""
    muestras = int(fs * (WINDOW_SECONDS * 2 + segundos_de_cola))
    tiempos = np.arange(muestras) / fs
    return Recording(
        file_path=Path("con_cola.edf"),
        channels=[Channel("C4", ChannelKind.EEG, MICROVOLT, 0)],
        data=np.vstack([50.0 * np.sin(2 * np.pi * 10 * tiempos)]),
        sampling_rate=fs,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


def test_la_ultima_ventana_incompleta_queda_en_nan():
    """**La convención del módulo**, y la que copian complejidad y
    conectividad. Una cola de 2 s es más corta que el segmento de Welch, así
    que no se puede medir: NaN lo dice, y un número lo escondería.
    """
    registro = registro_con_cola(2.0)
    alpha = band_powers_by_window(registro, ["C4"])["C4"]["Alpha"]

    assert len(alpha) == 3
    assert np.isfinite(alpha[:2]).all()
    assert np.isnan(alpha[2])


def test_el_array_conserva_el_largo_aunque_falte_una(registro_sintetico: Recording):
    """**Descartar la ventana desalinearía el array del hipnograma**, que es
    justamente para lo que sirve."""
    registro = registro_con_cola(2.0)
    esperadas = count_windows(registro.n_samples, registro.sampling_rate)

    assert len(band_powers_by_window(registro, ["C4"])["C4"]["Delta"]) == esperadas


def test_una_cola_larga_si_se_mide():
    """Una cola de 10 s entra holgada en el segmento de 4 s, así que se mide
    como cualquier otra ventana."""
    registro = registro_con_cola(10.0)
    alpha = band_powers_by_window(registro, ["C4"])["C4"]["Alpha"]

    assert np.isfinite(alpha).all()


def test_pedir_la_psd_de_un_tramo_muy_corto_se_rechaza():
    """Desde `compute_psd` es un error y no un NaN: quien la llama pidió esa
    ventana en concreto y merece saber que no se pudo."""
    registro = registro_con_cola(2.0)

    with pytest.raises(InvalidRecordingError):
        compute_psd(registro, window_index=2)


# -- Los rechazos ------------------------------------------------------------


def test_un_metodo_desconocido_se_rechaza(registro_sintetico: Recording):
    """Elegir uno por defecto le daría al usuario un resultado que no pidió y
    que no puede distinguir del que pidió."""
    with pytest.raises(UnknownPsdMethodError):
        compute_psd(registro_sintetico, method="fourier")


def test_los_metodos_declarados_funcionan(registro_sintetico: Recording):
    for metodo in METHODS:
        compute_psd(registro_sintetico, channels=["C4"], method=metodo)


def test_una_ventana_que_no_existe_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(WindowOutOfRangeError):
        compute_psd(registro_sintetico, window_index=999)


def test_una_ventana_negativa_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(WindowOutOfRangeError):
        compute_psd(registro_sintetico, window_index=-1)


def test_un_canal_que_no_existe_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(ChannelNotFoundError):
        compute_psd(registro_sintetico, channels=["no_existe"])


@pytest.mark.parametrize(
    "banda", [(12.0, 8.0), (-1.0, 4.0), (5.0, 5.0), ("a", "b"), None, (1.0,)]
)
def test_una_banda_mal_formada_se_rechaza(banda):
    """Una banda de 12 a 8 Hz no contiene nada, y devolver cero escondería el
    error de tipeo detrás de un resultado plausible."""
    frecuencias = np.linspace(0.0, 50.0, 201)
    potencias = np.ones((1, 201))

    with pytest.raises(InvalidBandError):
        band_power(frecuencias, potencias, banda)


def test_una_banda_mal_formada_se_rechaza_antes_de_recorrer(
    registro_sintetico: Recording,
):
    """Fallar en la ventana 900 de 960 por una banda invertida que se sabía
    desde el principio sería tiempo tirado."""
    with pytest.raises(InvalidBandError):
        band_powers_by_window(registro_sintetico, ["C4"], bands={"mala": (12.0, 8.0)})


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        compute_psd(hostil)
    with pytest.raises(PsgLabError):
        band_powers_by_window(hostil, ["C4"])


# -- `None` es "todos" y `[]` es "ninguno" (hito 21) --------------------------


def test_la_lista_vacia_de_canales_se_rechaza(registro_sintetico: Recording):
    """**No es lo mismo que `None`.** `None` dice "todos"; `[]` dice "ninguno", y
    sobre ninguno no hay nada que medir.

    `compute_psd(channels=[])` devolvia en silencio un espectro de cero canales
    y `band_powers_by_window()` hacia lo contrario --tratarla como "todos"--,
    asi que la misma lista significaba cosas opuestas en funciones hermanas.
    """
    with pytest.raises(PsgLabError):
        compute_psd(registro_sintetico, channels=[])

    with pytest.raises(PsgLabError):
        band_powers_by_window(registro_sintetico, [])


def test_none_sigue_significando_todos(registro_sintetico: Recording):
    """La otra mitad: la salida que la lista vacia deja abierta."""
    _, potencias = compute_psd(registro_sintetico, channels=None)

    assert potencias.shape[0] == len(registro_sintetico.channels)
