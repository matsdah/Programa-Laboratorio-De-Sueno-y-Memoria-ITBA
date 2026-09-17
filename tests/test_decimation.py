"""Tests de `psglab/core/decimation.py`: la envolvente que hace dibujable la noche.

El primero es el que justifica el módulo: **una espiga de una sola muestra
sobrevive a reducir ocho horas**. Es lo que impide que alguien lo "optimice"
cambiándolo por `samples[::n]`, que es más corto, más rápido y la pierde.
"""

import tracemalloc

import numpy as np
import pytest

from psglab.core.decimation import min_max_envelope
from psglab.utils.errors import PsgLabError

#: Ocho horas a 100 Hz, que es la frecuencia del registro de prueba real.
OCHO_HORAS = 8 * 3600 * 100

#: El ancho de una pantalla común, en píxeles.
ANCHO = 1600


# -- Lo que el módulo promete -------------------------------------------------


def test_una_espiga_de_una_sola_muestra_sobrevive_a_ocho_horas():
    """**El test que justifica el módulo.**

    Una muestra de 200 µV entre casi tres millones de ceros. Tomando una de cada
    `n` desaparece casi seguro; con la envolvente no puede, porque cada muestra
    cae en una cubeta y cada cubeta aporta su máximo.
    """
    senal = np.zeros(OCHO_HORAS)
    senal[1_234_567] = 200.0

    _, valores = min_max_envelope(senal, ANCHO)

    assert valores.max() == 200.0


def test_una_espiga_hacia_abajo_tambien_sobrevive():
    """El mínimo vale lo mismo que el máximo: un complejo K es una deflexión
    negativa."""
    senal = np.zeros(OCHO_HORAS)
    senal[2_000_001] = -150.0

    _, valores = min_max_envelope(senal, ANCHO)

    assert valores.min() == -150.0


def test_submuestrear_ingenuamente_la_perderia():
    """Es el contraste que vuelve significativo al test de arriba: si esto
    dejara de fallar, el de arriba no probaría nada."""
    senal = np.zeros(OCHO_HORAS)
    senal[1_234_567] = 200.0

    paso = OCHO_HORAS // ANCHO
    assert senal[::paso].max() == 0.0


def test_la_cantidad_de_puntos_no_crece_con_la_duracion():
    """Treinta segundos y ocho horas dan pantallas del mismo tamaño.

    Es lo que vuelve constante el costo de dibujar: sin esto, pedir el registro
    entero manda millones de puntos a la pantalla.
    """
    rng = np.random.default_rng(0)
    corta = rng.normal(size=30 * 1000)
    larga = rng.normal(size=OCHO_HORAS)

    indices_cortos, _ = min_max_envelope(corta, ANCHO)
    indices_largos, _ = min_max_envelope(larga, ANCHO)

    # Las cubetas tienen que ser iguales y cubrir la señal, así que su tamaño se
    # redondea hacia arriba y pueden ser algo menos que columnas: con más de
    # dos muestras por columna, nunca menos de dos tercios.
    for indices in (indices_cortos, indices_largos):
        assert 2 * ANCHO * 2 / 3 <= len(indices) <= 2 * ANCHO + 2


@pytest.mark.parametrize("muestras, columnas", [(3000, 1120), (3000, 1400), (7683, 1000)])
def test_la_envolvente_cubre_la_senal_hasta_el_final(muestras: int, columnas: int):
    """**Hasta el hito 24 no la cubría.** Con cubetas de `muestras // columnas`,
    una página de 30 s a 100 Hz sobre 1120 columnas dejaba los últimos 7,6 s en
    la cola, reducidos a dos puntos: la señal se dibujaba cortada al 75 % y con
    una recta al final. Ningún tramo puede quedar más lejos que dos cubetas del
    punto anterior."""
    senal = np.random.default_rng(7).normal(size=muestras)
    por_cubeta = -(-muestras // columnas)

    indices, _ = min_max_envelope(senal, columnas)

    assert indices[0] < por_cubeta
    assert indices[-1] >= muestras - por_cubeta
    assert np.diff(indices).max() < 2 * por_cubeta


def test_los_valores_son_los_de_la_senal_en_esos_indices():
    """La envolvente elige muestras; no inventa ni interpola ninguna."""
    senal = np.random.default_rng(1).normal(size=100_000)

    indices, valores = min_max_envelope(senal, 300)

    assert np.array_equal(valores, senal[indices])


def test_los_indices_vienen_ordenados_y_sin_repetir():
    """Es lo que permite dibujarlos como una sola curva de izquierda a
    derecha."""
    senal = np.random.default_rng(2).normal(size=100_000)

    indices, _ = min_max_envelope(senal, 300)

    assert np.all(np.diff(indices) > 0)


def test_los_extremos_salen_en_el_orden_en_que_ocurren():
    """**Emitir siempre primero el mínimo dibujaría cada espiga como un
    ensanchamiento simétrico.** En esta cubeta el máximo llega antes."""
    senal = np.zeros(1000)
    senal[10] = 5.0   # el máximo, primero
    senal[80] = -5.0  # el mínimo, después

    _, valores = min_max_envelope(senal, 10)

    assert list(valores[:2]) == [5.0, -5.0]


def test_cada_cubeta_aporta_su_maximo_y_su_minimo():
    """La envolvente de cada columna de píxeles es exactamente el rango de las
    muestras que caen en ella."""
    senal = np.random.default_rng(3).normal(size=10_000)
    cubetas = 50
    por_cubeta = len(senal) // cubetas

    _, valores = min_max_envelope(senal, cubetas)

    esperados = senal.reshape(cubetas, por_cubeta)
    obtenidos = valores.reshape(cubetas, 2)
    assert np.array_equal(obtenidos.max(axis=1), esperados.max(axis=1))
    assert np.array_equal(obtenidos.min(axis=1), esperados.min(axis=1))


def test_la_cola_que_no_llena_una_cubeta_no_se_descarta():
    """Ahí puede estar el último evento de la noche."""
    senal = np.zeros(10_007)
    senal[-1] = 99.0

    indices, valores = min_max_envelope(senal, 10)

    assert valores.max() == 99.0
    assert indices[-1] == len(senal) - 1


def test_una_senal_constante_no_repite_indices():
    """Una cubeta plana tiene el mínimo y el máximo en la misma muestra:
    emitirla dos veces no dibuja nada distinto."""
    indices, _ = min_max_envelope(np.ones(10_000), 100)

    assert len(indices) == len(np.unique(indices))


def test_una_senal_corta_vuelve_entera():
    """Con menos muestras que puntos de pantalla, la envolvente no achicaría
    nada: sólo volvería más gruesa la traza."""
    senal = np.arange(50, dtype=float)

    indices, valores = min_max_envelope(senal, 100)

    assert np.array_equal(indices, np.arange(50))
    assert np.array_equal(valores, senal)


def test_una_senal_vacia_vuelve_vacia():
    indices, valores = min_max_envelope(np.array([]), 100)

    assert len(indices) == 0
    assert len(valores) == 0


def test_no_copia_la_senal():
    """**Lo que hace viable pedir el registro entero.**

    Se mide lo que se aloja mientras se calcula: tiene que ser del tamaño de la
    pantalla y no del registro. Una implementación que copiara la señal para
    partirla alojaría decenas de megabytes acá.
    """
    senal = np.random.default_rng(4).normal(size=OCHO_HORAS)  # ~23 MB
    tamano = senal.nbytes

    tracemalloc.start()
    try:
        min_max_envelope(senal, ANCHO)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert pico < tamano / 100


# -- Lo que rechaza ------------------------------------------------------------


def test_sin_cubetas_avisa_en_vez_de_dividir_por_cero():
    """**El caso real**: mientras se arma la ventana el gráfico todavía no tiene
    ancho, y ese cero llega acá. Un `ZeroDivisionError` atravesaría el `except`
    de la ventana principal."""
    with pytest.raises(PsgLabError):
        min_max_envelope(np.zeros(1000), 0)


def test_una_cantidad_negativa_de_cubetas_se_rechaza():
    with pytest.raises(PsgLabError):
        min_max_envelope(np.zeros(1000), -5)


@pytest.mark.parametrize("cubetas", [True, 3.5, "100", None])
def test_las_cubetas_tienen_que_ser_un_entero(cubetas: object):
    """`True` es un `int` para Python, y pasaría como una cubeta."""
    with pytest.raises(PsgLabError):
        min_max_envelope(np.zeros(1000), cubetas)


def test_un_entero_de_numpy_se_acepta():
    """Es lo que devuelve cualquier cuenta sobre un array: rechazarlo sería
    obligar a quien llama a convertirlo."""
    indices, _ = min_max_envelope(np.zeros(1000), np.int64(10))

    assert len(indices) > 0


@pytest.mark.parametrize(
    "senal",
    [
        np.zeros((2, 1000)),
        [0.0, 1.0, 2.0],
        np.float64(3.0),
    ],
    ids=["dos-dimensiones", "lista", "escalar"],
)
def test_la_senal_tiene_que_ser_un_array_de_una_dimension(senal: object):
    """Una matriz de canales es el error esperable: `Recording.data` lo es."""
    with pytest.raises(PsgLabError):
        min_max_envelope(senal, 10)
