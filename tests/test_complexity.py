"""Tests de las medidas de complejidad.

**Los valores de referencia salen de la teoría, no de una corrida.** Es la regla
que separa un test de una fotografía: afirmar "da 0,8734" contra lo que devolvió
la primera ejecución no verifica nada, sólo congela el comportamiento actual
incluido su error.

Las cuatro medidas tienen ancla teórica, y las dos primeras son exactas:

    rampa monótona   -> entropía de permutación = 0   (un solo patrón ordinal)
    recta            -> dimensión de Higuchi = 1      (por construcción)
    señal constante  -> Lempel-Ziv mínima
    ruido > senoide > recta, en las cuatro

Se verificaron todas contra la implementación antes de escribirlas acá, que es
lo que evita afirmar algo plausible y falso.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.complexity import (
    MEASURES,
    MIN_SAMPLES,
    complexity_by_window,
    higuchi_fractal_dimension,
    lempel_ziv_complexity,
    permutation_entropy,
    sample_entropy,
)
from psglab.config import WINDOW_SECONDS
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.windows import count_windows
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidRecordingError,
    PsgLabError,
    UnknownMeasureError,
)
from psglab.utils.units import MICROVOLT

from conftest import VENTANAS_SINTETICAS

MUESTRAS = 4096
TIEMPOS = np.arange(MUESTRAS) / 256.0


@pytest.fixture
def rampa() -> np.ndarray:
    """Una rampa monótona: el caso de complejidad mínima."""
    return np.linspace(0.0, 100.0, MUESTRAS)


@pytest.fixture
def senoide() -> np.ndarray:
    return 50.0 * np.sin(2 * np.pi * 10 * TIEMPOS)


@pytest.fixture
def ruido() -> np.ndarray:
    """Ruido blanco: el caso de complejidad máxima."""
    return np.random.default_rng(0).normal(0.0, 50.0, MUESTRAS)


# -- Entropía de permutación -------------------------------------------------


def test_una_rampa_monotona_da_entropia_cero(rampa: np.ndarray):
    """**El ancla exacta.** En una señal siempre creciente hay un solo patrón
    ordinal, así que la entropía de su distribución es exactamente 0."""
    assert permutation_entropy(rampa) == pytest.approx(0.0, abs=1e-12)


def test_el_ruido_blanco_se_acerca_al_maximo(ruido: np.ndarray):
    """Va normalizada, así que el techo es 1."""
    assert permutation_entropy(ruido) > 0.99


def test_la_senoide_queda_en_el_medio(rampa, senoide, ruido):
    assert permutation_entropy(rampa) < permutation_entropy(senoide)
    assert permutation_entropy(senoide) < permutation_entropy(ruido)


def test_va_normalizada_entre_cero_y_uno(rampa, senoide, ruido):
    """Sin normalizar dependería del orden elegido, y dos análisis con órdenes
    distintos no se podrían comparar."""
    for señal in (rampa, senoide, ruido):
        valor = permutation_entropy(señal)
        assert 0.0 <= valor <= 1.0


# -- Lempel-Ziv --------------------------------------------------------------


def test_una_señal_constante_da_la_complejidad_minima(senoide, ruido):
    constante = np.full(MUESTRAS, 42.0)

    assert lempel_ziv_complexity(constante) < lempel_ziv_complexity(senoide)
    assert lempel_ziv_complexity(senoide) < lempel_ziv_complexity(ruido)


def test_se_binariza_contra_la_mediana_y_no_contra_la_media():
    """**La mediana es robusta a la deriva de línea de base**, que en un
    registro de ocho horas siempre hay.

    Una señal con una deriva grande tiene la media corrida hacia el final; con
    la media como umbral, casi toda la primera mitad caería de un solo lado y
    la complejidad medida sería la de la deriva, no la de la señal.
    """
    oscilacion = np.sign(np.sin(2 * np.pi * 5 * TIEMPOS))
    deriva = np.linspace(0.0, 20.0, MUESTRAS)

    con_deriva = lempel_ziv_complexity(oscilacion + deriva)
    sin_deriva = lempel_ziv_complexity(oscilacion)

    assert con_deriva == pytest.approx(sin_deriva, rel=0.3)


# -- Dimensión fractal de Higuchi --------------------------------------------


def test_una_recta_da_dimension_uno(rampa: np.ndarray):
    """**El otro ancla exacta.** La dimensión fractal de una recta es 1 por
    construcción."""
    assert higuchi_fractal_dimension(rampa) == pytest.approx(1.0, abs=1e-6)


def test_el_ruido_se_acerca_a_dos(ruido: np.ndarray):
    """El techo de la medida es 2: una curva que llena el plano."""
    assert 1.9 < higuchi_fractal_dimension(ruido) <= 2.0


def test_el_orden_es_ruido_senoide_recta(rampa, senoide, ruido):
    assert (
        higuchi_fractal_dimension(rampa)
        < higuchi_fractal_dimension(senoide)
        < higuchi_fractal_dimension(ruido)
    )


def test_una_señal_constante_da_nan():
    """**No es un bug y conviene saberlo.** La dimensión fractal de algo sin
    variación no está definida, y un canal desconectado es un caso real: ahí el
    NaN no significa "no se pudo medir por falta de datos" sino "esta medida no
    existe para esta señal".
    """
    assert np.isnan(higuchi_fractal_dimension(np.full(MUESTRAS, 42.0)))


# -- Entropía de muestra -----------------------------------------------------


def test_el_orden_se_sostiene_tambien_en_la_entropia_de_muestra():
    """El valor absoluto depende de la convención de la tolerancia, así que lo
    afirmable es el orden. Se usa un tramo corto: es O(n²) y con 4096 muestras
    tarda 124 ms."""
    corto = slice(0, 1500)
    assert sample_entropy(np.linspace(0, 100, MUESTRAS)[corto]) < sample_entropy(
        (50.0 * np.sin(2 * np.pi * 10 * TIEMPOS))[corto]
    )


def test_la_tolerancia_por_defecto_es_la_convencion():
    """0,2 × desvío estándar. Pasarla explícitamente tiene que dar lo mismo que
    dejarla en None, o la convención documentada sería otra."""
    señal = (50.0 * np.sin(2 * np.pi * 10 * TIEMPOS))[:1200]

    por_defecto = sample_entropy(señal)
    explicita = sample_entropy(señal, r=0.2 * float(np.std(señal)))

    assert por_defecto == pytest.approx(explicita)


def test_la_longitud_de_patron_cambia_el_resultado():
    """Si `m` no llegara a antropy, los dos darían igual."""
    señal = np.random.default_rng(0).normal(0, 1, 1200)

    assert sample_entropy(señal, m=2) != pytest.approx(sample_entropy(señal, m=4))


# -- La noche entera ---------------------------------------------------------


def test_hay_un_valor_por_ventana(registro_sintetico: Recording):
    por_ventana = complexity_by_window(registro_sintetico, ["C4"])

    assert len(por_ventana["C4"]) == VENTANAS_SINTETICAS


def test_una_señal_estacionaria_da_lo_mismo_en_todas_las_ventanas(
    registro_sintetico: Recording,
):
    """La fixture es una senoide pura: si una ventana diera distinto, sería la
    conversión de ventana a muestras la que está mal."""
    valores = complexity_by_window(registro_sintetico, ["C4"])["C4"]

    assert np.allclose(valores, valores[0], rtol=0.02)


def test_se_puede_elegir_la_medida(registro_sintetico: Recording):
    con_pe = complexity_by_window(registro_sintetico, ["C4"])
    con_hf = complexity_by_window(
        registro_sintetico, ["C4"], measure="higuchi_fractal_dimension"
    )

    assert not np.allclose(con_pe["C4"], con_hf["C4"])


def test_estan_todos_los_canales_pedidos(registro_sintetico: Recording):
    por_ventana = complexity_by_window(registro_sintetico, ["C3", "EMG-menton"])

    assert set(por_ventana) == {"C3", "EMG-menton"}


def test_las_cuatro_medidas_declaradas_funcionan(registro_sintetico: Recording):
    """Si `MEASURES` nombrara una que no está cableada, esto lo diría."""
    corto = Recording(
        file_path=Path("corto.edf"),
        channels=[Channel("C4", ChannelKind.EEG, MICROVOLT, 0)],
        data=registro_sintetico.data[:1, : int(256.0 * WINDOW_SECONDS)],
        sampling_rate=256.0,
    )
    for medida in MEASURES:
        resultado = complexity_by_window(corto, ["C4"], measure=medida)
        assert len(resultado["C4"]) == 1


# -- La última ventana incompleta --------------------------------------------


def registro_con_cola(muestras_de_cola: int) -> Recording:
    """Dos ventanas completas más una cola de la longitud pedida."""
    fs = 256.0
    total = int(fs * WINDOW_SECONDS * 2) + muestras_de_cola
    t = np.arange(total) / fs
    return Recording(
        file_path=Path("cola.edf"),
        channels=[Channel("C4", ChannelKind.EEG, MICROVOLT, 0)],
        data=np.vstack([50.0 * np.sin(2 * np.pi * 10 * t)]),
        sampling_rate=fs,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


def test_una_ventana_demasiado_corta_queda_en_nan():
    """**La convención que fijó `psd.py`**, copiada acá: conserva el largo del
    array y dice que ahí no se midió."""
    registro = registro_con_cola(MIN_SAMPLES // 2)
    valores = complexity_by_window(registro, ["C4"])["C4"]

    assert len(valores) == 3
    assert np.isfinite(valores[:2]).all()
    assert np.isnan(valores[2])


def test_el_array_conserva_el_largo(registro_sintetico: Recording):
    registro = registro_con_cola(MIN_SAMPLES // 2)
    esperadas = count_windows(registro.n_samples, registro.sampling_rate)

    assert len(complexity_by_window(registro, ["C4"])["C4"]) == esperadas


def test_una_cola_suficiente_si_se_mide():
    registro = registro_con_cola(MIN_SAMPLES * 3)

    assert np.isfinite(complexity_by_window(registro, ["C4"])["C4"]).all()


# -- Los rechazos ------------------------------------------------------------


def test_una_medida_desconocida_se_rechaza(registro_sintetico: Recording):
    """Sin la comprobación fallaba tarde, con un `KeyError` en vez de un mensaje
    que diga cuáles hay."""
    with pytest.raises(UnknownMeasureError):
        complexity_by_window(registro_sintetico, ["C4"], measure="entropia_magica")


def test_un_canal_que_no_existe_se_rechaza(registro_sintetico: Recording):
    with pytest.raises(ChannelNotFoundError):
        complexity_by_window(registro_sintetico, ["no_existe"])


def test_una_señal_de_dos_dimensiones_se_rechaza():
    """Las medidas son de un canal por vez: pasarle la matriz entera daría un
    número que no es la complejidad de nada."""
    with pytest.raises(InvalidRecordingError):
        permutation_entropy(np.zeros((2, 100)))


def test_una_señal_vacia_se_rechaza():
    with pytest.raises(InvalidRecordingError):
        permutation_entropy(np.array([]))


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, {}])
def test_lo_hostil_sale_como_error_del_programa(hostil):
    """Sin la guarda, antropy eleva lo que le salga —`TypeError`, un error de
    numba— y nada de eso hereda de `PsgLabError`."""
    for medida in (permutation_entropy, lempel_ziv_complexity, higuchi_fractal_dimension):
        with pytest.raises(PsgLabError):
            medida(hostil)


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        complexity_by_window(hostil, ["C4"])
