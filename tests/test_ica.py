"""Tests de la descomposición en componentes independientes.

**ICA devuelve objetos de MNE, así que la tentación es testear que no explote.**
Este archivo hace otra cosa: **mezcla dos fuentes conocidas con pesos conocidos
y comprueba que las recupere**.

    fuente 1: ritmo alfa de 10 Hz
    fuente 2: un "parpadeo" lento y grande, de 0,3 Hz
    mezcla:   los frontales reciben casi todo el parpadeo y poco alfa;
              los occipitales, al revés

Si la descomposición funciona, uno de los componentes tiene que tener peso alto
en los frontales y bajo en los occipitales —que es exactamente cómo se reconoce
un parpadeo— y quitarlo tiene que bajar la potencia de 0,3 Hz **medida por
PSD**, sin tocar el alfa.

Eso es verificable con señal sintética, exacto en lo que importa, y no depende
de qué objeto devuelva MNE.

Dos cosas que ICA **no** conserva y por eso no se afirman: el **orden** de los
componentes y su **signo**. Los dos son arbitrarios por construcción del
algoritmo, así que los tests buscan "el componente frontal" en vez de suponer
que es el 0, y comparan valores absolutos.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.analysis.ica import (
    RANDOM_STATE,
    apply_ica,
    component_time_course,
    component_topography,
    fit_ica,
)
from psglab.analysis.psd import band_power, compute_psd
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import InvalidRecordingError, PsgLabError
from psglab.utils.units import MICROVOLT

FS = 256.0
SEGUNDOS = 60.0

#: Cuánto pesa cada canal en cada fuente. Filas: Fp1, Fp2, O1, O2.
#: Columnas: alfa, parpadeo. Los frontales reciben el parpadeo.
PESOS = np.array([[0.2, 1.0], [0.3, 0.9], [1.0, 0.1], [0.9, 0.05]])


@pytest.fixture
def mezclado() -> Recording:
    """Cuatro canales EEG con dos fuentes conocidas mezcladas."""
    n = int(FS * SEGUNDOS)
    t = np.arange(n) / FS
    alfa = 30.0 * np.sin(2 * np.pi * 10 * t)
    parpadeo = 150.0 * np.sin(2 * np.pi * 0.3 * t)
    datos = PESOS @ np.vstack([alfa, parpadeo])
    datos = datos + np.random.default_rng(0).normal(0.0, 1.0, datos.shape)

    return Recording(
        file_path=Path("mezclado.edf"),
        channels=[
            Channel(nombre, ChannelKind.EEG, MICROVOLT, posicion)
            for posicion, nombre in enumerate(["Fp1", "Fp2", "O1", "O2"])
        ],
        data=datos,
        sampling_rate=FS,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


def componente_frontal(ica) -> int:
    """Cuál de los componentes es el del parpadeo.

    Se lo busca en vez de suponer que es el 0, porque **ICA no conserva el
    orden**: es arbitrario por construcción del algoritmo.
    """
    mejor, puntaje_mejor = 0, -np.inf
    for numero in range(int(ica.n_components_)):
        pesos = component_topography(ica, numero)
        frontal = abs(pesos["Fp1"]) + abs(pesos["Fp2"])
        posterior = abs(pesos["O1"]) + abs(pesos["O2"])
        if frontal - posterior > puntaje_mejor:
            mejor, puntaje_mejor = numero, frontal - posterior
    return mejor


def potencia(recording: Recording, canal: str, banda: tuple[float, float]) -> float:
    frecuencias, potencias = compute_psd(recording, channels=[canal])
    return float(band_power(frecuencias, potencias, banda)[0])


# -- Que separe de verdad las fuentes ----------------------------------------


def test_hay_un_componente_concentrado_en_los_frontales(mezclado: Recording):
    """**Es cómo se reconoce un parpadeo**, y lo que la vista de topografía
    existe para mostrar."""
    ica = fit_ica(mezclado)
    pesos = component_topography(ica, componente_frontal(ica))

    frontal = (abs(pesos["Fp1"]) + abs(pesos["Fp2"])) / 2
    posterior = (abs(pesos["O1"]) + abs(pesos["O2"])) / 2
    assert frontal > posterior * 3


def test_los_pesos_recuperados_se_parecen_a_los_que_se_mezclaron(
    mezclado: Recording,
):
    """**La verificación fuerte**: no que ICA devuelva algo, sino que devuelva
    lo que se puso.

    Se comparan valores absolutos y normalizados, porque el signo y la escala de
    un componente son arbitrarios.
    """
    ica = fit_ica(mezclado)
    pesos = component_topography(ica, componente_frontal(ica))

    puestos = PESOS[:, 1] / PESOS[:, 1].max()
    recuperados = np.array([abs(pesos[c]) for c in ["Fp1", "Fp2", "O1", "O2"]])

    assert np.allclose(recuperados, puestos, atol=0.15)


def test_la_topografia_va_normalizada(mezclado: Recording):
    """Sin normalizar, los números dependen de la escala que ICA le haya dado
    al componente, que es arbitraria: lo que se lee es la forma."""
    ica = fit_ica(mezclado)
    pesos = component_topography(ica, 0)

    assert max(abs(v) for v in pesos.values()) == pytest.approx(1.0)


def test_la_topografia_trae_todos_los_canales(mezclado: Recording):
    ica = fit_ica(mezclado)

    assert set(component_topography(ica, 0)) == {"Fp1", "Fp2", "O1", "O2"}


# -- La serie temporal -------------------------------------------------------


def test_la_serie_temporal_dura_lo_que_el_registro(mezclado: Recording):
    ica = fit_ica(mezclado)
    curso = component_time_course(ica, componente_frontal(ica), mezclado)

    assert curso.shape == (mezclado.n_samples,)


def test_el_componente_frontal_oscila_a_la_frecuencia_del_parpadeo(
    mezclado: Recording,
):
    """Es lo que se ve al mirarlo debajo de la señal: **cuándo** ocurre el
    artefacto."""
    from scipy import signal as sp

    ica = fit_ica(mezclado)
    curso = component_time_course(ica, componente_frontal(ica), mezclado)

    frecuencias, potencias = sp.welch(curso, fs=FS, nperseg=int(FS * 8))
    assert frecuencias[int(np.argmax(potencias))] == pytest.approx(0.3, abs=0.2)


# -- Aplicar -----------------------------------------------------------------


def test_quitar_el_componente_del_parpadeo_baja_su_potencia(mezclado: Recording):
    """**La prueba de que sirve**, medida por PSD y no por inspección: la
    potencia en 0,3 Hz tiene que caer en los frontales."""
    ica = fit_ica(mezclado)
    limpio = apply_ica(mezclado, ica, [componente_frontal(ica)])

    antes = potencia(mezclado, "Fp1", (0.1, 1.0))
    despues = potencia(limpio, "Fp1", (0.1, 1.0))
    assert despues < antes / 10


def test_quitar_el_parpadeo_no_se_lleva_el_alfa(mezclado: Recording):
    """La otra mitad, y la que importa para no romper la señal: si quitar un
    componente se llevara todo, el test de arriba pasaría igual."""
    ica = fit_ica(mezclado)
    limpio = apply_ica(mezclado, ica, [componente_frontal(ica)])

    antes = potencia(mezclado, "O1", (8.0, 12.0))
    despues = potencia(limpio, "O1", (8.0, 12.0))
    assert despues == pytest.approx(antes, rel=0.25)


def test_sin_excluir_nada_la_señal_vuelve_casi_igual(mezclado: Recording):
    """Sirve para comprobar que la descomposición no está rompiendo la señal
    antes de confiarle un componente."""
    ica = fit_ica(mezclado)
    reconstruido = apply_ica(mezclado, ica, [])

    assert np.allclose(reconstruido.data, mezclado.data, atol=1.0)


def test_el_original_no_se_toca(mezclado: Recording):
    """La operación no se puede deshacer sobre los datos ya transformados."""
    antes = mezclado.data.copy()
    ica = fit_ica(mezclado)
    apply_ica(mezclado, ica, [0])

    assert np.array_equal(mezclado.data, antes)


def test_los_canales_que_no_son_eeg_vuelven_intactos(mezclado: Recording):
    """Sólo cambian los EEG, que son sobre los que se ajustó la descomposición."""
    n = mezclado.n_samples
    con_temperatura = Recording(
        file_path=mezclado.file_path,
        channels=[*mezclado.channels, Channel("Temp", ChannelKind.OTHER, "DegC", 4)],
        data=np.vstack([mezclado.data, np.full(n, 36.5)]),
        sampling_rate=FS,
    )
    ica = fit_ica(con_temperatura)
    limpio = apply_ica(con_temperatura, ica, [0])

    assert np.allclose(limpio.data[4], 36.5)


# -- Reproducible ------------------------------------------------------------


def test_dos_corridas_dan_la_misma_descomposicion(mezclado: Recording):
    """**ICA es estocástica**: sin semilla fija, el mismo registro daría
    componentes distintos en cada corrida, en otro orden y con otro signo. Un
    investigador que rehace un análisis tiene que obtener lo mismo."""
    una = component_topography(fit_ica(mezclado), 0)
    otra = component_topography(fit_ica(mezclado), 0)

    assert una == pytest.approx(otra)
    assert RANDOM_STATE is not None


# -- Cuántos componentes -----------------------------------------------------


def test_sin_pedir_cantidad_usa_todos_los_canales(mezclado: Recording):
    """No se puede separar más fuentes que sensores, así que ése es el techo."""
    assert int(fit_ica(mezclado).n_components_) == 4


def test_se_puede_pedir_menos(mezclado: Recording):
    assert int(fit_ica(mezclado, n_components=2).n_components_) == 2


def test_pedir_mas_componentes_que_canales_se_rechaza(mezclado: Recording):
    """Sin la guarda, MNE lo rechaza con un mensaje sobre PCA que no le dice
    nada a un investigador."""
    with pytest.raises(InvalidRecordingError):
        fit_ica(mezclado, n_components=99)


# -- Los rechazos ------------------------------------------------------------


def test_un_registro_con_un_solo_eeg_se_rechaza():
    """Con un solo canal no hay mezcla que separar, y devolver una
    descomposición de un componente haría creer que se hizo algo."""
    n = int(FS * 10)
    solo_uno = Recording(
        file_path=Path("uno.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, MICROVOLT, 0),
            Channel("EMG", ChannelKind.EMG, MICROVOLT, 1),
        ],
        data=np.random.default_rng(0).normal(0, 10, (2, n)),
        sampling_rate=FS,
    )
    with pytest.raises(InvalidRecordingError):
        fit_ica(solo_uno)


def test_una_señal_plana_se_rechaza_con_un_mensaje_util():
    """**Un canal desconectado toda la noche es un caso real.**

    Sin variación no hay nada que descomponer: al blanquear se divide por una
    varianza cero y MNE eleva "array must not contain infs or NaNs", que no le
    dice nada a un investigador y además no hereda de `PsgLabError`, así que se
    escaparía del `except` de la ventana principal. Lo encontró
    `test_contratos.py`.
    """
    plano = Recording(
        file_path=Path("plano.edf"),
        channels=[
            Channel("C3", ChannelKind.EEG, MICROVOLT, 0),
            Channel("C4", ChannelKind.EEG, MICROVOLT, 1),
        ],
        data=np.zeros((2, int(FS * 10))),
        sampling_rate=FS,
    )
    with pytest.raises(InvalidRecordingError):
        fit_ica(plano)


def test_un_componente_que_no_existe_se_rechaza(mezclado: Recording):
    ica = fit_ica(mezclado)

    with pytest.raises(InvalidRecordingError):
        component_topography(ica, 99)


def test_excluir_un_componente_que_no_existe_se_rechaza(mezclado: Recording):
    """Es el error caro: quitar un componente inventado dejaría la señal
    modificada de forma irreversible sin que nadie sepa qué se quitó."""
    ica = fit_ica(mezclado)

    with pytest.raises(InvalidRecordingError):
        apply_ica(mezclado, ica, [0, 99])


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_una_ica_sale_como_error_del_programa(
    mezclado: Recording, hostil
):
    """Sin la guarda sale un `AttributeError` sobre `.get_components()`, que la
    ventana principal no atrapa."""
    with pytest.raises(PsgLabError):
        component_topography(hostil, 0)
    with pytest.raises(PsgLabError):
        apply_ica(mezclado, hostil, [])


@pytest.mark.parametrize("hostil", [None, "texto", 3.5, [], {}])
def test_lo_que_no_es_un_registro_sale_como_error_del_programa(hostil):
    with pytest.raises(PsgLabError):
        fit_ica(hostil)
