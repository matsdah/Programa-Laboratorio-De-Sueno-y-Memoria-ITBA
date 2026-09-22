"""Tests de `psglab/core/decimation.py`: la envolvente que hace dibujable la noche.

El primero es el que justifica el módulo: **una espiga de una sola muestra
sobrevive a reducir ocho horas**. Es lo que impide que alguien lo "optimice"
cambiándolo por `samples[::n]`, que es más corto, más rápido y la pierde.

**Desde el hito 49 la función recibe el tamaño de cubeta y no la cantidad**,
para que las cubetas caigan sobre una grilla fija al registro. La mayoría de
los tests de abajo piensan en columnas de pantalla, que es como se escribieron,
y pasan por `envolvente()`: la misma cuenta que hace el visualizador con una
página que empieza en la muestra cero.
"""

import tracemalloc

import numpy as np
import pytest

from psglab.core.decimation import bucket_size_for, envelope_by_bucket_size
from psglab.utils.errors import PsgLabError

#: Ocho horas a 100 Hz, que es la frecuencia del registro de prueba real.
OCHO_HORAS = 8 * 3600 * 100

#: El ancho de una pantalla común, en píxeles.
ANCHO = 1600


def envolvente(senal: np.ndarray, columnas: int) -> tuple[np.ndarray, np.ndarray]:
    """La envolvente de una señal entera repartida en `columnas` cubetas."""
    return envelope_by_bucket_size(senal, bucket_size_for(len(senal), columnas))


# -- Lo que el módulo promete -------------------------------------------------


def test_una_espiga_de_una_sola_muestra_sobrevive_a_ocho_horas():
    """**El test que justifica el módulo.**

    Una muestra de 200 µV entre casi tres millones de ceros. Tomando una de cada
    `n` desaparece casi seguro; con la envolvente no puede, porque cada muestra
    cae en una cubeta y cada cubeta aporta su máximo.
    """
    senal = np.zeros(OCHO_HORAS)
    senal[1_234_567] = 200.0

    _, valores = envolvente(senal, ANCHO)

    assert valores.max() == 200.0


def test_una_espiga_hacia_abajo_tambien_sobrevive():
    """El mínimo vale lo mismo que el máximo: un complejo K es una deflexión
    negativa."""
    senal = np.zeros(OCHO_HORAS)
    senal[2_000_001] = -150.0

    _, valores = envolvente(senal, ANCHO)

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

    indices_cortos, _ = envolvente(corta, ANCHO)
    indices_largos, _ = envolvente(larga, ANCHO)

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

    indices, _ = envolvente(senal, columnas)

    assert indices[0] < por_cubeta
    assert indices[-1] >= muestras - por_cubeta
    assert np.diff(indices).max() < 2 * por_cubeta


def test_los_valores_son_los_de_la_senal_en_esos_indices():
    """La envolvente elige muestras; no inventa ni interpola ninguna."""
    senal = np.random.default_rng(1).normal(size=100_000)

    indices, valores = envolvente(senal, 300)

    assert np.array_equal(valores, senal[indices])


def test_los_indices_vienen_ordenados_y_sin_repetir():
    """Es lo que permite dibujarlos como una sola curva de izquierda a
    derecha."""
    senal = np.random.default_rng(2).normal(size=100_000)

    indices, _ = envolvente(senal, 300)

    assert np.all(np.diff(indices) > 0)


def test_los_extremos_salen_en_el_orden_en_que_ocurren():
    """**Emitir siempre primero el mínimo dibujaría cada espiga como un
    ensanchamiento simétrico.** En esta cubeta el máximo llega antes."""
    senal = np.zeros(1000)
    senal[10] = 5.0   # el máximo, primero
    senal[80] = -5.0  # el mínimo, después

    _, valores = envolvente(senal, 10)

    assert list(valores[:2]) == [5.0, -5.0]


def test_cada_cubeta_aporta_su_maximo_y_su_minimo():
    """La envolvente de cada columna de píxeles es exactamente el rango de las
    muestras que caen en ella."""
    senal = np.random.default_rng(3).normal(size=10_000)
    cubetas = 50
    por_cubeta = len(senal) // cubetas

    _, valores = envolvente(senal, cubetas)

    esperados = senal.reshape(cubetas, por_cubeta)
    obtenidos = valores.reshape(cubetas, 2)
    assert np.array_equal(obtenidos.max(axis=1), esperados.max(axis=1))
    assert np.array_equal(obtenidos.min(axis=1), esperados.min(axis=1))


def test_la_cola_que_no_llena_una_cubeta_no_se_descarta():
    """Ahí puede estar el último evento de la noche."""
    senal = np.zeros(10_007)
    senal[-1] = 99.0

    indices, valores = envolvente(senal, 10)

    assert valores.max() == 99.0
    assert indices[-1] == len(senal) - 1


def test_una_senal_constante_no_repite_indices():
    """Una cubeta plana tiene el mínimo y el máximo en la misma muestra:
    emitirla dos veces no dibuja nada distinto."""
    indices, _ = envolvente(np.ones(10_000), 100)

    assert len(indices) == len(np.unique(indices))


def test_con_cubetas_de_una_muestra_vuelve_la_senal_entera():
    """Con menos muestras que columnas cada cubeta es una muestra, y su mínimo
    y su máximo son ella misma: la envolvente es la señal. Que no se dibuje la
    envolvente en ese caso lo decide el visualizador."""
    senal = np.arange(50, dtype=float)

    indices, valores = envolvente(senal, 100)

    assert np.array_equal(indices, np.arange(50))
    assert np.array_equal(valores, senal)


def test_una_senal_vacia_vuelve_vacia():
    indices, valores = envolvente(np.array([]), 100)

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
        envolvente(senal, ANCHO)
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert pico < tamano / 100


# -- La grilla es la del registro (hito 49) ------------------------------------


def test_por_trozos_da_lo_mismo_que_de_una_vez():
    """**Lo que permite guardar la envolvente por trozos.** Si un trozo empieza
    en un múltiplo del tamaño de cubeta, sus cubetas son las mismas que las del
    registro entero, y juntarlos da exactamente la envolvente del todo. Con la
    cola que no llena una cubeta incluida: 100 003 no es múltiplo de 70."""
    senal = np.random.default_rng(11).normal(size=100_003)
    por_cubeta = 70
    por_trozo = 64 * por_cubeta

    entera, _ = envelope_by_bucket_size(senal, por_cubeta)
    por_trozos = np.concatenate(
        [
            desde + envelope_by_bucket_size(senal[desde : desde + por_trozo], por_cubeta)[0]
            for desde in range(0, len(senal), por_trozo)
        ]
    )

    assert np.array_equal(por_trozos, entera)


def test_la_misma_muestra_cae_en_la_misma_cubeta_en_cualquier_pagina():
    """**Es lo que hace que la traza no titile al reproducir.** Hasta el hito 49
    cada página se partía desde su borde, y una espiga caía en cubetas distintas
    de un cuadro al otro. Con la grilla fija, dos tramos que empiezan en la
    grilla eligen las mismas muestras donde se superponen."""
    senal = np.random.default_rng(12).normal(size=50_000)
    por_cubeta = 25

    a, _ = envelope_by_bucket_size(senal[0:30_000], por_cubeta)
    b, _ = envelope_by_bucket_size(senal[5_000:35_000], por_cubeta)
    b = b + 5_000

    comunes = (5_000, 30_000)
    en_a = a[(a >= comunes[0]) & (a < comunes[1])]
    en_b = b[(b >= comunes[0]) & (b < comunes[1])]
    assert np.array_equal(en_a, en_b)


@pytest.mark.parametrize(
    ("muestras", "cubetas", "tamano"),
    [(3000, 1120, 3), (3000, 1500, 2), (3001, 1500, 3), (50, 100, 1), (0, 100, 1)],
)
def test_el_tamano_de_cubeta_redondea_hacia_arriba(muestras, cubetas, tamano):
    """Hacia arriba, y nunca menos de uno. Con `//`, 3000 sobre 1120 daba 2, y
    la cuarta parte de la página quedaba afuera."""
    assert bucket_size_for(muestras, cubetas) == tamano


def test_las_cubetas_enteras_no_pasan_de_las_pedidas():
    for muestras in (999, 1000, 1001, 123_457):
        tamano = bucket_size_for(muestras, 1000)
        assert muestras // tamano <= 1000


# -- Lo que rechaza ------------------------------------------------------------


def test_sin_cubetas_avisa_en_vez_de_dividir_por_cero():
    """**El caso real**: mientras se arma la ventana el gráfico todavía no tiene
    ancho, y ese cero llega acá. Un `ZeroDivisionError` atravesaría el `except`
    de la ventana principal."""
    with pytest.raises(PsgLabError):
        bucket_size_for(1000, 0)


def test_una_cantidad_negativa_de_cubetas_se_rechaza():
    with pytest.raises(PsgLabError):
        bucket_size_for(1000, -5)


def test_una_cantidad_negativa_de_muestras_se_rechaza():
    with pytest.raises(PsgLabError):
        bucket_size_for(-1, 10)


@pytest.mark.parametrize("cubetas", [True, 3.5, "100", None])
def test_las_cubetas_tienen_que_ser_un_entero(cubetas: object):
    """`True` es un `int` para Python, y pasaría como una cubeta."""
    with pytest.raises(PsgLabError):
        bucket_size_for(1000, cubetas)


@pytest.mark.parametrize("tamano", [0, -3, True, 3.5, "10", None])
def test_el_tamano_de_cubeta_tiene_que_ser_un_entero_positivo(tamano: object):
    """Una cubeta de cero muestras sería un `reshape` imposible."""
    with pytest.raises(PsgLabError):
        envelope_by_bucket_size(np.zeros(1000), tamano)


def test_un_entero_de_numpy_se_acepta():
    """Es lo que devuelve cualquier cuenta sobre un array: rechazarlo sería
    obligar a quien llama a convertirlo."""
    tamano = bucket_size_for(1000, np.int64(10))
    indices, _ = envelope_by_bucket_size(np.zeros(1000), np.int64(tamano))

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
        envelope_by_bucket_size(senal, 10)
