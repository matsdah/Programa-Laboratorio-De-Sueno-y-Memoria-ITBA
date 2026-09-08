"""Tests de la conectividad entre canales.

**El ancla principal es el propio motivo del módulo**: que wPLI sea inmune al
volume conduction y la coherencia común no.

Ese test se escribió mal la primera vez, y vale contar por qué. La predicción
era "dos canales idénticos dan coherencia 1 y **wPLI 0**", que suena bien y es
falsa: con señales exactamente idénticas la parte imaginaria del espectro
cruzado es cero, wPLI **divide por ella**, y lo que sale es ruido numérico
—medido: 0,39—. La afirmación correcta no es sobre un caso degenerado sino
sobre el escenario real que el docstring describe:

    Dos electrodos que captan la misma fuente, cada uno con su propio ruido,
    tienen coherencia alta y **wPLI bajo**. Dos señales con un desfase real
    tienen coherencia parecida y **wPLI alto**.

Medido: misma fuente da coherencia 0,74 y wPLI 0,39; desfasadas 45° dan
coherencia 0,79 y wPLI 1,00. **La coherencia no las distingue y wPLI sí**, que
es exactamente lo que hace falta para no confundir volume conduction con
conexión.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.connectivity import (
    EPOCH_SECONDS,
    METHODS,
    average_connectivity,
    compute_connectivity,
    connectivity_by_window,
)
from psglab.config import WINDOW_SECONDS
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.windows import count_windows
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidBandError,
    InvalidRecordingError,
    PsgLabError,
    UnknownConnectivityMethodError,
    WindowOutOfRangeError,
)
from psglab.utils.units import MICROVOLT

FS = 256.0
DELTA = (0.5, 4.0)


def registro(filas: dict[str, np.ndarray], fs: float = FS) -> Recording:
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=[
            Channel(nombre, ChannelKind.EEG, MICROVOLT, posicion)
            for posicion, nombre in enumerate(filas)
        ],
        data=np.vstack(list(filas.values())),
        sampling_rate=fs,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


@pytest.fixture
def escenario() -> Recording:
    """Los tres casos que separan volume conduction de conexión real.

    - `VC_A` y `VC_B` captan **la misma fuente** sin desfase, cada uno con su
      ruido: es el volume conduction.
    - `RETARDO` trae la misma frecuencia con un desfase real de 45°: es una
      conexión.
    - `AJENO` es ruido independiente.
    """
    n = int(FS * WINDOW_SECONDS)
    t = np.arange(n) / FS
    rng = np.random.default_rng(0)
    fuente = 50.0 * np.sin(2 * np.pi * 2 * t)
    return registro(
        {
            "VC_A": fuente + rng.normal(0, 10, n),
            "VC_B": 0.7 * fuente + rng.normal(0, 10, n),
            "RETARDO": 50.0 * np.sin(2 * np.pi * 2 * t + np.pi / 4)
            + rng.normal(0, 10, n),
            "AJENO": rng.normal(0, 50, n),
        }
    )


# -- Lo que justifica el módulo ----------------------------------------------


def test_wpli_distingue_volume_conduction_de_conexion(escenario: Recording):
    """**El test que justifica que el módulo exista.**

    Los dos pares tienen coherencia parecida. Si wPLI no los separara, no habría
    motivo para ofrecerlo.
    """
    wpli = compute_connectivity(escenario, band=DELTA, method="wpli")

    misma_fuente = wpli[0, 1]
    con_desfase = wpli[0, 2]
    assert con_desfase > misma_fuente * 2


def test_la_coherencia_comun_no_los_distingue(escenario: Recording):
    """La otra mitad de la afirmación: **si la coherencia los separara, wPLI no
    haría falta.**"""
    coh = compute_connectivity(escenario, band=DELTA, method="coherence")

    assert coh[0, 1] == pytest.approx(coh[0, 2], rel=0.25)


def test_dos_canales_identicos_dan_coherencia_uno():
    """El caso exacto que sí se sostiene."""
    n = int(FS * WINDOW_SECONDS)
    onda = 50.0 * np.sin(2 * np.pi * 2 * np.arange(n) / FS)
    igual = registro({"A": onda, "B": onda.copy()})

    coh = compute_connectivity(igual, band=DELTA, method="coherence")
    assert coh[0, 1] == pytest.approx(1.0, abs=1e-6)


def test_un_desfase_de_noventa_grados_da_wpli_maximo():
    """El otro extremo: desfase de un cuarto de ciclo, todo parte imaginaria."""
    n = int(FS * WINDOW_SECONDS)
    t = np.arange(n) / FS
    desfasadas = registro(
        {
            "A": 50.0 * np.sin(2 * np.pi * 2 * t),
            "B": 50.0 * np.sin(2 * np.pi * 2 * t + np.pi / 2),
        }
    )

    wpli = compute_connectivity(desfasadas, band=DELTA, method="wpli")
    assert wpli[0, 1] == pytest.approx(1.0, abs=0.01)


def test_dos_señales_ajenas_dan_conectividad_baja(escenario: Recording):
    coh = compute_connectivity(escenario, band=DELTA, method="coherence")

    assert coh[0, 3] < 0.3


# -- La matriz ---------------------------------------------------------------


def test_la_matriz_es_cuadrada_y_del_tamaño_pedido(escenario: Recording):
    matriz = compute_connectivity(escenario, channels=["VC_A", "VC_B", "AJENO"], band=DELTA)

    assert matriz.shape == (3, 3)


def test_la_matriz_es_simetrica(escenario: Recording):
    """mne-connectivity devuelve sólo el triángulo inferior; este módulo promete
    una matriz simétrica, así que quien la lea no tiene que saber de qué lado
    quedó cada par."""
    matriz = compute_connectivity(escenario, band=DELTA)

    assert np.allclose(matriz, matriz.T)


def test_la_diagonal_es_cero(escenario: Recording):
    """Un canal consigo mismo no es una conexión."""
    matriz = compute_connectivity(escenario, band=DELTA)

    assert np.allclose(np.diag(matriz), 0.0)


def test_se_puede_elegir_la_banda(escenario: Recording):
    """La fuente común está en 2 Hz: en delta se ve y en beta no."""
    en_delta = compute_connectivity(escenario, band=DELTA, method="coherence")
    en_beta = compute_connectivity(escenario, band=(16.0, 30.0), method="coherence")

    assert en_delta[0, 1] > en_beta[0, 1]


def test_los_cinco_metodos_declarados_funcionan(escenario: Recording):
    for metodo in METHODS:
        matriz = compute_connectivity(escenario, band=DELTA, method=metodo)
        assert matriz.shape == (4, 4)


def test_se_puede_pedir_una_sola_ventana(escenario: Recording):
    matriz = compute_connectivity(escenario, band=DELTA, window_index=0)

    assert matriz.shape == (4, 4)


# -- El promedio -------------------------------------------------------------


def test_el_promedio_ignora_la_diagonal():
    """**Poner 1,0 en la diagonal no puede cambiar el resultado.** Es lo que
    demuestra que la ignora de verdad y no que la reste."""
    matriz = np.array([[0.0, 0.5], [0.5, 0.0]])
    con_unos = np.array([[1.0, 0.5], [0.5, 1.0]])

    assert average_connectivity(matriz) == pytest.approx(0.5)
    assert average_connectivity(con_unos) == pytest.approx(0.5)


def test_el_promedio_es_el_de_los_pares():
    matriz = np.array([[0.0, 0.2, 0.4], [0.2, 0.0, 0.6], [0.4, 0.6, 0.0]])

    assert average_connectivity(matriz) == pytest.approx(0.4)


def test_una_matriz_toda_nan_da_nan():
    """Es lo que llega de una ventana que no se pudo medir, y promediarla como
    cero la haría pasar por una ventana sin conectividad."""
    assert np.isnan(average_connectivity(np.full((3, 3), np.nan)))


def test_una_matriz_que_no_es_cuadrada_se_rechaza():
    with pytest.raises(InvalidRecordingError):
        average_connectivity(np.zeros((2, 3)))


def test_una_matriz_de_un_solo_canal_se_rechaza():
    """La conectividad es entre canales: con uno solo no hay ningún par."""
    with pytest.raises(InvalidRecordingError):
        average_connectivity(np.zeros((1, 1)))


# -- La noche entera ---------------------------------------------------------


def test_hay_una_matriz_por_ventana(escenario: Recording):
    por_ventana = connectivity_by_window(escenario, ["VC_A", "VC_B"], DELTA)

    esperadas = count_windows(escenario.n_samples, escenario.sampling_rate)
    assert por_ventana.shape == (esperadas, 2, 2)


def test_la_ultima_ventana_corta_queda_en_nan():
    """La misma convención que fijó `psd.py`."""
    n = int(FS * WINDOW_SECONDS) + int(FS * 2)  # una ventana más dos segundos
    t = np.arange(n) / FS
    corto = registro(
        {
            "A": 50.0 * np.sin(2 * np.pi * 2 * t),
            "B": 50.0 * np.sin(2 * np.pi * 2 * t + 0.5),
        }
    )

    por_ventana = connectivity_by_window(corto, ["A", "B"], DELTA)

    assert por_ventana.shape[0] == 2
    assert np.isfinite(por_ventana[0]).all()
    assert np.isnan(por_ventana[1]).all()


def test_una_cola_de_una_epoca_si_se_mide():
    """`EPOCH_SECONDS` es el umbral, no la ventana entera."""
    n = int(FS * WINDOW_SECONDS) + int(FS * EPOCH_SECONDS)
    t = np.arange(n) / FS
    con_cola = registro(
        {
            "A": 50.0 * np.sin(2 * np.pi * 2 * t),
            "B": 50.0 * np.sin(2 * np.pi * 2 * t + 0.5),
        }
    )

    por_ventana = connectivity_by_window(con_cola, ["A", "B"], DELTA)
    assert np.isfinite(por_ventana[-1]).all()


# -- Los rechazos ------------------------------------------------------------


def test_un_metodo_desconocido_se_rechaza(escenario: Recording):
    """Importa más que en otros casos: la coherencia común y wPLI responden
    preguntas distintas, así que elegir uno por omisión daría un resultado que
    se interpreta al revés."""
    with pytest.raises(UnknownConnectivityMethodError):
        compute_connectivity(escenario, band=DELTA, method="magia")


def test_un_solo_canal_se_rechaza(escenario: Recording):
    with pytest.raises(InvalidRecordingError):
        compute_connectivity(escenario, channels=["VC_A"], band=DELTA)


def test_un_canal_que_no_existe_se_rechaza(escenario: Recording):
    with pytest.raises(ChannelNotFoundError):
        compute_connectivity(escenario, channels=["VC_A", "no_existe"], band=DELTA)


@pytest.mark.parametrize("banda", [(4.0, 0.5), (-1.0, 4.0), (2.0, 2.0), None, "delta"])
def test_una_banda_mal_formada_se_rechaza(escenario: Recording, banda):
    with pytest.raises(InvalidBandError):
        compute_connectivity(escenario, band=banda)


def test_una_ventana_que_no_existe_se_rechaza(escenario: Recording):
    with pytest.raises(WindowOutOfRangeError):
        compute_connectivity(escenario, band=DELTA, window_index=999)


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        compute_connectivity(hostil, band=DELTA)
    with pytest.raises(PsgLabError):
        connectivity_by_window(hostil, ["A", "B"], DELTA)
