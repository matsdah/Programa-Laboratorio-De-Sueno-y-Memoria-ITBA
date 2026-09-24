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
    explained_variance,
    fit_ica,
)
from psglab.analysis.psd import band_power, compute_psd
from psglab.config import WINDOW_SECONDS
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


# -- Una sola ventana (hito 19) ----------------------------------------------
#
# El panel dibuja **la ventana que el investigador está mirando**, igual que el
# espectro y la conectividad: la serie de las ocho horas no se puede mirar, y
# reconstruirla entera cuesta una copia completa de la señal.


def test_pedir_una_ventana_devuelve_solo_esa_ventana(mezclado: Recording):
    """La fixture dura 60 s a 256 Hz: dos ventanas de 7680 muestras."""
    ica = fit_ica(mezclado)
    frontal = componente_frontal(ica)

    primera = component_time_course(ica, frontal, mezclado, window_index=0)

    assert primera.shape == (int(WINDOW_SECONDS * FS),)
    assert primera.shape[0] < mezclado.n_samples


def test_la_ventana_pedida_es_el_tramo_de_esa_ventana(mezclado: Recording):
    """**No basta con que mida lo que corresponde: tiene que ser ese tramo.**

    Un recorte del principio para cualquier ventana pasaría el test de largo y
    le mostraría al investigador el artefacto de otro momento de la noche.
    """
    ica = fit_ica(mezclado)
    frontal = componente_frontal(ica)
    entera = component_time_course(ica, frontal, mezclado)

    for ventana in (0, 1):
        desde = int(ventana * WINDOW_SECONDS * FS)
        trozo = component_time_course(ica, frontal, mezclado, window_index=ventana)
        esperado = entera[desde : desde + len(trozo)]
        # No es idéntico bit a bit: reconstruir 30 s no es recortar la
        # reconstrucción de 60. Lo que tiene que coincidir es la señal.
        assert np.corrcoef(trozo, esperado)[0, 1] == pytest.approx(1.0, abs=1e-3)


def test_las_dos_ventanas_no_son_la_misma(mezclado: Recording):
    """El parpadeo de 0,3 Hz está en otra fase en cada ventana."""
    ica = fit_ica(mezclado)
    frontal = componente_frontal(ica)

    primera = component_time_course(ica, frontal, mezclado, window_index=0)
    segunda = component_time_course(ica, frontal, mezclado, window_index=1)

    assert not np.allclose(primera, segunda)


@pytest.mark.parametrize("ventana", [2, -1, 99])
def test_una_ventana_que_no_existe_se_rechaza(mezclado: Recording, ventana: int):
    """Con la ventana −1, numpy cuenta desde el final y devolvería señal del
    final de la noche presentada como si fuera del principio."""
    ica = fit_ica(mezclado)

    with pytest.raises(PsgLabError):
        component_time_course(ica, 0, mezclado, window_index=ventana)


def test_sin_ventana_sigue_devolviendo_el_registro_entero(mezclado: Recording):
    """La firma vieja no cambió de significado: `None` es el registro completo,
    que es lo que un script del laboratorio sigue pudiendo pedir."""
    ica = fit_ica(mezclado)
    curso = component_time_course(ica, 0, mezclado, window_index=None)

    assert curso.shape == (mezclado.n_samples,)


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


# -- Cuánta varianza explica cada componente (hito 54) ----------------------


def test_el_parpadeo_es_el_que_mas_varianza_explica(mezclado: Recording):
    """El parpadeo se mezcló con cinco veces la amplitud del alfa: es el que
    más pesa, y es justamente la pista que la lista tiene que dar."""
    ica = fit_ica(mezclado)
    varianzas = explained_variance(ica, mezclado)

    assert int(np.argmax(varianzas)) == componente_frontal(ica)


def test_hay_una_fraccion_por_componente_y_entre_cero_y_uno(mezclado: Recording):
    ica = fit_ica(mezclado)
    varianzas = explained_variance(ica, mezclado)

    assert len(varianzas) == ica.n_components_
    assert all(0.0 <= v <= 1.0 for v in varianzas)


def test_con_tantos_componentes_como_canales_suman_uno(mezclado: Recording):
    """Con cuatro componentes sobre cuatro canales, la descomposición explica
    toda la señal."""
    varianzas = explained_variance(fit_ica(mezclado), mezclado)

    assert sum(varianzas) == pytest.approx(1.0, abs=0.02)


def test_con_pocas_ventanas_coincide_con_mne_sobre_el_registro_entero(
    mezclado: Recording,
):
    """**Es la definición de MNE**, no una aproximación propia: con menos
    ventanas que la muestra, se mide sobre el registro entero y da lo mismo.
    Se probó sacarla de la matriz de mezcla y no coincidía."""
    from psglab.analysis.mne_bridge import to_raw

    ica = fit_ica(mezclado)
    raw = to_raw(mezclado)
    de_mne = [
        ica.get_explained_variance_ratio(raw, components=[i], ch_type="eeg")["eeg"]
        for i in range(ica.n_components_)
    ]

    assert explained_variance(ica, mezclado) == pytest.approx(de_mne, abs=1e-6)


def test_con_muchas_ventanas_mide_sobre_una_muestra(mezclado: Recording, monkeypatch):
    """Reconstruir una vez por componente sobre la noche entera cuesta una copia
    de la señal cada vez. Con más ventanas que la muestra, mide sobre la
    muestra."""
    import psglab.analysis.ica as modulo

    ica = fit_ica(mezclado)
    medidas: list[int] = []
    original = modulo.to_raw

    def contando(recording):
        medidas.append(recording.n_samples)
        return original(recording)

    monkeypatch.setattr(modulo, "VARIANCE_SAMPLE_WINDOWS", 1)
    monkeypatch.setattr(modulo, "to_raw", contando)

    varianzas = explained_variance(ica, mezclado)

    assert medidas == [int(WINDOW_SECONDS * FS)]
    assert len(varianzas) == ica.n_components_


def test_sin_ica_ajustada_se_rechaza(mezclado: Recording):
    with pytest.raises(PsgLabError):
        explained_variance(object(), mezclado)


# -- Ajustar sobre una muestra de la noche (hito 58) --------------------------
#
# La fixture dura 60 s, menos que `FIT_SAMPLES`, así que los tests de arriba se
# ajustan con todas sus muestras y no pasan por la muestra. Éstos bajan el tope
# para que el paso sea de verdad mayor que uno.


@pytest.fixture
def tope_bajo(monkeypatch) -> int:
    """Un tope de 1920 muestras: sobre los 60 s de la fixture, una de cada 8."""
    import psglab.analysis.ica as modulo

    monkeypatch.setattr(modulo, "FIT_SAMPLES", 1920)
    monkeypatch.setattr(modulo, "FIT_SAMPLES_PER_SQUARED_CHANNEL", 1)
    return 1920


def espiar_lo_que_se_ajusta(monkeypatch) -> list[Recording]:
    """Lo que `fit_ica()` le pasa a MNE, en el orden en que se lo pasa."""
    import psglab.analysis.ica as modulo

    vistos: list[Recording] = []
    original = modulo.to_raw

    def espiando(recording):
        vistos.append(recording)
        return original(recording)

    monkeypatch.setattr(modulo, "to_raw", espiando)
    return vistos


def test_sobre_una_muestra_sigue_separando_el_parpadeo(mezclado: Recording, tope_bajo):
    """**La verificación fuerte, otra vez**, con un octavo de las muestras:
    ajustar con menos datos no puede perder lo que se mezcló."""
    ica = fit_ica(mezclado)
    pesos = component_topography(ica, componente_frontal(ica))

    puestos = PESOS[:, 1] / PESOS[:, 1].max()
    recuperados = np.array([abs(pesos[c]) for c in ["Fp1", "Fp2", "O1", "O2"]])
    assert np.allclose(recuperados, puestos, atol=0.15)


def test_lo_ajustado_sobre_la_muestra_limpia_la_senal_entera(mezclado: Recording, tope_bajo):
    """Se ajusta sobre una muestra y se aplica sobre todo: el parpadeo tiene
    que bajar en la señal a la frecuencia original, sin llevarse el alfa."""
    ica = fit_ica(mezclado)
    limpio = apply_ica(mezclado, ica, [componente_frontal(ica)])

    assert limpio.n_samples == mezclado.n_samples
    assert potencia(limpio, "Fp1", (0.1, 1.0)) < potencia(mezclado, "Fp1", (0.1, 1.0)) / 10
    assert potencia(limpio, "O1", (8.0, 12.0)) == pytest.approx(
        potencia(mezclado, "O1", (8.0, 12.0)), rel=0.25
    )


def test_a_mne_le_llega_la_muestra_y_no_la_noche(mezclado: Recording, tope_bajo, monkeypatch):
    vistos = espiar_lo_que_se_ajusta(monkeypatch)

    fit_ica(mezclado)

    (muestra,) = vistos
    assert muestra.n_samples == tope_bajo == mezclado.n_samples / 8


def test_el_tope_es_un_minimo(mezclado: Recording, monkeypatch):
    """**Por lo menos** `FIT_SAMPLES`: con el paso redondeado hacia arriba,
    un registro apenas más largo que el tope se ajustaba con la mitad."""
    import psglab.analysis.ica as modulo

    monkeypatch.setattr(modulo, "FIT_SAMPLES", mezclado.n_samples // 2 + 1)
    monkeypatch.setattr(modulo, "FIT_SAMPLES_PER_SQUARED_CHANNEL", 1)
    vistos = espiar_lo_que_se_ajusta(monkeypatch)

    fit_ica(mezclado)

    assert vistos[0].n_samples >= mezclado.n_samples // 2 + 1


def test_la_muestra_recorre_el_registro_entero(mezclado: Recording, tope_bajo, monkeypatch):
    """**Repartida y no un tramo**: una hora seguida puede ser toda vigilia, y
    el componente de parpadeo de la vigilia no es el de la noche."""
    vistos = espiar_lo_que_se_ajusta(monkeypatch)

    fit_ica(mezclado)

    (muestra,) = vistos
    assert muestra.duration_seconds == pytest.approx(mezclado.duration_seconds, rel=0.01)
    assert np.array_equal(muestra.data[:, 0], mezclado.data[:, 0])
    assert np.array_equal(muestra.data[:, 1], mezclado.data[:, 8])


def test_a_mne_solo_le_llegan_los_eeg(mezclado: Recording, tope_bajo, monkeypatch):
    """Antes se le pasaba el registro entero y MNE elegía: una copia de más de
    cada canal que no se descompone."""
    n = mezclado.n_samples
    con_temperatura = Recording(
        file_path=mezclado.file_path,
        channels=[*mezclado.channels, Channel("Temp", ChannelKind.OTHER, "DegC", 4)],
        data=np.vstack([mezclado.data, np.full(n, 36.5)]),
        sampling_rate=FS,
    )
    vistos = espiar_lo_que_se_ajusta(monkeypatch)

    fit_ica(con_temperatura)

    assert vistos[0].channel_names() == ["Fp1", "Fp2", "O1", "O2"]


def test_un_registro_corto_se_ajusta_entero(mezclado: Recording, monkeypatch):
    """Por debajo del tope no se descarta nada: es lo que hacía antes del
    hito 58, y lo que siguen afirmando los tests de arriba."""
    vistos = espiar_lo_que_se_ajusta(monkeypatch)

    fit_ica(mezclado)

    assert vistos[0].n_samples == mezclado.n_samples


def test_muchos_canales_suben_el_piso(mezclado: Recording, monkeypatch):
    """La ICA necesita más muestras cuantos más canales separa: unas veinte o
    treinta veces su cuadrado. Con un tope fijo muy bajo, manda el piso."""
    import psglab.analysis.ica as modulo

    monkeypatch.setattr(modulo, "FIT_SAMPLES", 10)
    monkeypatch.setattr(modulo, "FIT_SAMPLES_PER_SQUARED_CHANNEL", 120)
    vistos = espiar_lo_que_se_ajusta(monkeypatch)

    fit_ica(mezclado)

    assert vistos[0].n_samples >= 120 * 4**2


def test_ajustar_ya_no_cuesta_varias_copias_de_la_senal(tope_bajo):
    """**Es el número que midió el hito 57**: sobre la noche entera, ajustar
    pedía seis copias de la señal además de la que ya estaba. Con la muestra,
    menos de una.

    Se mide con `tracemalloc`, que numpy alimenta con cada array que reserva.
    La señal se arma antes de empezar a medir, así que no cuenta.
    """
    import tracemalloc

    n = int(FS * 600)
    t = np.arange(n) / FS
    fuentes = np.vstack([30.0 * np.sin(2 * np.pi * 10 * t), 150.0 * np.sin(2 * np.pi * 0.3 * t)])
    datos = PESOS @ fuentes + np.random.default_rng(1).normal(0.0, 1.0, (4, n))
    largo = Recording(
        file_path=Path("largo.edf"),
        channels=[
            Channel(nombre, ChannelKind.EEG, MICROVOLT, posicion)
            for posicion, nombre in enumerate(["Fp1", "Fp2", "O1", "O2"])
        ],
        data=datos,
        sampling_rate=FS,
    )

    tracemalloc.start()
    try:
        fit_ica(largo)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert pico < datos.nbytes


# -- Quitar componentes por tramos (hito 59) ---------------------------------


@pytest.fixture
def tramos_chicos(monkeypatch) -> int:
    """Tramos de 1000 muestras: la fixture de 60 s se parte en dieciséis, y el
    último queda más corto que los demás."""
    import psglab.analysis.ica as modulo

    monkeypatch.setattr(modulo, "_MUESTRAS_POR_TRAMO", 1000)
    return 1000


def test_por_tramos_da_lo_mismo_que_de_una_vez(mezclado: Recording, tramos_chicos):
    """**Quitar un componente es una cuenta muestra por muestra** con las
    matrices del ajuste: partirla en tramos no puede cambiar un número. La
    referencia es lo que hacía `apply_ica()` hasta el hito 59, la señal entera
    en un solo `Raw`."""
    from psglab.analysis.mne_bridge import from_raw, to_raw

    ica = fit_ica(mezclado)
    frontal = componente_frontal(ica)
    raw = to_raw(mezclado)
    ica.apply(raw, exclude=[frontal], verbose="ERROR")

    limpio = apply_ica(mezclado, ica, [frontal])

    assert np.allclose(limpio.data, from_raw(raw, mezclado).data, rtol=0, atol=1e-9)


def test_los_canales_que_no_son_eeg_ni_pasan_por_mne(mezclado: Recording, tramos_chicos):
    """Idénticos bit a bit, no parecidos: salen del original y no hacen el
    viaje µV → V → µV, que deja error de punto flotante."""
    n = mezclado.n_samples
    temperatura = 36.5 + 0.1 * np.sin(np.arange(n) / 100.0)
    con_temperatura = Recording(
        file_path=mezclado.file_path,
        channels=[*mezclado.channels, Channel("Temp", ChannelKind.OTHER, "DegC", 4)],
        data=np.vstack([mezclado.data, temperatura]),
        sampling_rate=FS,
    )
    ica = fit_ica(con_temperatura)

    limpio = apply_ica(con_temperatura, ica, [0])

    assert np.array_equal(limpio.data[4], temperatura)


def test_quitar_no_cuesta_varias_copias_de_la_senal(monkeypatch):
    """**Es el número que midió el hito 57**: cuatro copias con la que ya
    estaba. Por tramos son la salida y un tramo.

    El tramo se achica para que sea, como en una noche real, una fracción
    chica del registro: con el de fábrica, los diez minutos de este test son
    tres tramos y cada uno pesa casi la mitad.
    """
    import tracemalloc

    import psglab.analysis.ica as modulo

    monkeypatch.setattr(modulo, "_MUESTRAS_POR_TRAMO", 4096)
    n = int(FS * 600)
    t = np.arange(n) / FS
    fuentes = np.vstack([30.0 * np.sin(2 * np.pi * 10 * t), 150.0 * np.sin(2 * np.pi * 0.3 * t)])
    datos = PESOS @ fuentes + np.random.default_rng(1).normal(0.0, 1.0, (4, n))
    largo = Recording(
        file_path=Path("largo.edf"),
        channels=[
            Channel(nombre, ChannelKind.EEG, MICROVOLT, posicion)
            for posicion, nombre in enumerate(["Fp1", "Fp2", "O1", "O2"])
        ],
        data=datos,
        sampling_rate=FS,
    )
    ica = fit_ica(largo)

    tracemalloc.start()
    try:
        apply_ica(largo, ica, [0])
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert pico < 1.5 * datos.nbytes
