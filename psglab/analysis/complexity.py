"""Medidas de complejidad de la señal.

Cuantifican qué tan irregular o impredecible es la señal. En sueño se usan
porque bajan de forma sistemática al profundizarse el sueño y al perderse la
conciencia, y captan cosas que el análisis espectral no ve.

Se ofrecen varias medidas porque no hay una sola definición de "complejidad" y
cada una responde una pregunta distinta.

Las funciones que reciben `window_index` tienen que traducirlo a muestras con
`psglab.core.windows.window_to_samples()`, que es el único lugar del programa
donde se hace esa conversión. No escribir la cuenta `* 30 * fs` acá: si la
ventana deja de ser de 30 s, este módulo quedaría desincronizado en silencio.

**Las cuatro medidas son de antropy**, que expone exactamente los parámetros
que estas firmas prometen — incluida la tolerancia de la entropía de muestra,
cuyo valor por omisión es `0,2 × desvío estándar`, la convención que documenta
`sample_entropy()`.

**Dos van normalizadas y dos no**, y la diferencia importa:

- La entropía de permutación y Lempel-Ziv **se normalizan**. Sin normalizar,
  Lempel-Ziv depende del largo de la ventana y dos registros a frecuencias de
  muestreo distintas no se pueden comparar, que es justamente lo que un estudio
  necesita hacer.
- La dimensión fractal de Higuchi y la entropía de muestra **no**: sus escalas
  ya son absolutas —Higuchi va de 1 a 2 por construcción— y normalizarlas sería
  inventar un techo que no tienen.

**Cuánto cuestan, medido** sobre una ventana de 30 s a 256 Hz, y extrapolado a
las 2650 ventanas de un registro real:

    higuchi_fractal_dimension     0,07 ms/ventana  ->    0,2 s la noche
    permutation_entropy           0,14 ms/ventana  ->    0,4 s la noche
    lempel_ziv_complexity         1,69 ms/ventana  ->    4,5 s la noche
    sample_entropy              124,31 ms/ventana  ->  5,5 min la noche

**La entropía de muestra es dos órdenes de magnitud más cara que las otras**,
porque es O(n²) en el largo del tramo. `complexity_by_window()` la acepta igual
—es una función de biblioteca y quien la llama desde un script puede esperar—,
pero la interfaz no la ofrece para recorrer la noche. La política es de la
interfaz, no del módulo.

**Una señal constante da NaN** en Higuchi y en la entropía de muestra, y es
correcto: la dimensión fractal de una recta sin variación no está definida. Un
canal desconectado es un caso real, así que conviene saber que ahí el NaN no
significa "no se pudo medir por falta de datos" sino "la medida no existe para
esta señal". Lempel-Ziv y la entropía de permutación sí dan 0, que también es
la respuesta correcta para ellas.

Cubre del pliego: sección "Complejidad".
"""

from __future__ import annotations

from typing import Final

import numpy as np

from psglab.core.recording import Recording
from psglab.core.windows import count_windows, window_to_samples
from psglab.utils.errors import InvalidRecordingError, UnknownMeasureError

#: Medidas que `complexity_by_window()` sabe aplicar.
#:
#: Existe por el mismo motivo que el `METHODS` de conectividad: sin ella el
#: módulo aceptaría cualquier cadena y fallaría tarde, con un `KeyError` en vez
#: de un mensaje que diga cuáles hay.
MEASURES: Final[tuple[str, ...]] = (
    "permutation_entropy",
    "lempel_ziv_complexity",
    "higuchi_fractal_dimension",
    "sample_entropy",
)

#: Muestras mínimas para que una medida signifique algo.
#:
#: Cumple el mismo papel que el segmento de Welch en `psd.py` —por debajo de
#: esto la ventana devuelve NaN en vez de un número que nadie puede comparar con
#: los demás— pero **no es la misma clase de umbral, y conviene no confundirlos**:
#: `WELCH_SEGMENT_SECONDS` está en segundos y se traduce a muestras con la
#: frecuencia del registro, así que sube con ella; éste es un número fijo de
#: muestras.
#:
#: La consecuencia es que los dos módulos no descartan las mismas ventanas. A
#: 100 Hz la PSD necesita 400 muestras y la complejidad 256, así que hay
#: ventanas finales cortas donde una mide y la otra devuelve NaN; a 512 Hz la
#: PSD pide 2048 y ésta sigue pidiendo 256. No es un descuido: lo que hace
#: significativa a una medida de complejidad es **cuántos puntos** tiene el
#: patrón, no cuánto tiempo abarcan, mientras que la resolución en frecuencia de
#: Welch es un tiempo. Los dos arrays siguen teniendo `count_windows()`
#: elementos, así que se grafican igual contra el hipnograma.
#:
#: Un segundo a cualquier frecuencia razonable da varios cientos de muestras,
#: que es el piso para que los patrones de orden 3 tengan sentido.
MIN_SAMPLES: Final[int] = 256


def _como_array(signal: np.ndarray, nombre: str = "signal") -> np.ndarray:
    """Convierte a array de una dimensión, o rechaza como `PsgLabError`.

    Sin esta guarda, antropy recibe cualquier cosa y eleva lo que le salga
    —`TypeError`, `ValueError`, un error de numba—, y nada de eso hereda de
    `PsgLabError`: escaparía del `except` de la ventana principal y le llegaría
    al investigador como traza.
    """
    try:
        datos = np.asarray(signal, dtype=float)
    except (TypeError, ValueError) as error:
        raise InvalidRecordingError(
            "La señal a analizar tiene que ser una secuencia de números.",
            details=f"{nombre} es {type(signal).__name__}: {error}",
        ) from error
    if datos.ndim != 1:
        raise InvalidRecordingError(
            "Las medidas de complejidad se calculan sobre un canal por vez.",
            details=f"{nombre} tiene forma {datos.shape}, se esperaba una dimensión.",
        )
    if datos.size == 0:
        raise InvalidRecordingError(
            "No se puede medir la complejidad de una señal vacía.",
            details=f"{nombre} no tiene ninguna muestra.",
        )
    return datos


def _entero_positivo(valor: object, nombre: str) -> int:
    """Rechaza como `PsgLabError` lo que no sea un entero mayor que cero.

    Sin esta guarda, antropy le pasa el valor a numba y lo que sale es un error
    de compilación —"No matching definition for argument type(s)", "cannot
    compute fingerprint of empty list"— que no hereda de `PsgLabError`, escapa
    del `except` de la ventana principal, y le diría eso al investigador. Lo
    encontró `test_contratos.py`.
    """
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise InvalidRecordingError(
            f"El parámetro «{nombre}» tiene que ser un número entero.",
            details=f"{nombre} es {type(valor).__name__}: {valor!r}.",
        )
    if valor < 1:
        raise InvalidRecordingError(
            f"El parámetro «{nombre}» tiene que ser mayor que cero.",
            details=f"{nombre} = {valor}.",
        )
    return valor


def _tolerancia(valor: object) -> float | None:
    """Rechaza una tolerancia que no sea None o un número finito positivo."""
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise InvalidRecordingError(
            "La tolerancia tiene que ser un número, o None para usar la "
            "convención de 0,2 × desvío estándar.",
            details=f"r es {type(valor).__name__}: {valor!r}.",
        )
    if not np.isfinite(valor) or valor <= 0:
        raise InvalidRecordingError(
            "La tolerancia tiene que ser un número finito mayor que cero.",
            details=f"r = {valor}.",
        )
    return float(valor)


def sample_entropy(signal: np.ndarray, m: int = 2, r: float | None = None) -> float:
    """Entropía de muestra: probabilidad de que patrones parecidos sigan parecidos.

    Args:
        m: longitud de los patrones comparados.
        r: tolerancia. Si es None, se usa 0,2 veces el desvío estándar de la
            señal, que es la convención habitual.

    **Es la más cara de las cuatro por dos órdenes de magnitud**: es O(n²) en el
    largo del tramo, unos 124 ms por ventana de 30 s a 256 Hz. Recorrer una
    noche entera con ella lleva más de cinco minutos.

    Devuelve NaN si la señal es constante: sin variación no hay patrones que
    comparar.

    Raises:
        InvalidRecordingError: si la señal no es una secuencia de números de una
            dimensión.
    """
    import antropy

    datos = _como_array(signal)
    return float(
        antropy.sample_entropy(datos, order=_entero_positivo(m, "m"), tolerance=_tolerancia(r))
    )


def permutation_entropy(signal: np.ndarray, order: int = 3) -> float:
    """Entropía de permutación: complejidad según el orden relativo de las muestras.

    Es rápida y robusta al ruido, lo que la hace práctica para recorrer una
    noche entera ventana por ventana.

    **Va normalizada**, así que va de 0 a 1 y no depende del orden elegido: una
    rampa monótona da exactamente 0 —hay un solo patrón ordinal en toda la
    señal— y el ruido blanco se acerca a 1.

    Raises:
        InvalidRecordingError: si la señal no es una secuencia de números.
    """
    import antropy

    datos = _como_array(signal)
    return float(
        antropy.perm_entropy(datos, order=_entero_positivo(order, "order"), normalize=True)
    )


def lempel_ziv_complexity(signal: np.ndarray) -> float:
    """Complejidad de Lempel-Ziv sobre la señal binarizada.

    Cuenta patrones distintos en la señal. Es la medida más usada en los
    trabajos sobre niveles de conciencia.

    **Se binariza contra la mediana** y no contra la media: es la convención, y
    además es robusta a la deriva de línea de base, que en un registro de ocho
    horas siempre hay.

    **Va normalizada**, porque sin normalizar el valor crece con el largo del
    tramo y dos registros a frecuencias de muestreo distintas dejarían de ser
    comparables.

    Raises:
        InvalidRecordingError: si la señal no es una secuencia de números.
    """
    import antropy

    datos = _como_array(signal)
    binaria = (datos > np.median(datos)).astype(np.int8)
    return float(antropy.lziv_complexity(binaria, normalize=True))


def higuchi_fractal_dimension(signal: np.ndarray, k_max: int = 10) -> float:
    """Dimensión fractal de Higuchi: complejidad geométrica de la curva.

    **No se normaliza**: su escala ya es absoluta, de 1 a 2 por construcción.
    Una recta da exactamente 1 y el ruido blanco se acerca a 2.

    Devuelve NaN si la señal es constante, que es el caso de un canal
    desconectado: la dimensión fractal de algo sin variación no está definida.

    Raises:
        InvalidRecordingError: si la señal no es una secuencia de números.
    """
    import antropy

    datos = _como_array(signal)
    return float(antropy.higuchi_fd(datos, kmax=_entero_positivo(k_max, "k_max")))


#: Cómo se llama cada medida por dentro. Se arma acá y no en el cuerpo de
#: `complexity_by_window()` para que `MEASURES` y este mapa no puedan
#: separarse: si alguien agrega una a la constante y se olvida acá, el chequeo
#: de abajo lo dice.
_POR_NOMBRE = {
    "permutation_entropy": permutation_entropy,
    "lempel_ziv_complexity": lempel_ziv_complexity,
    "higuchi_fractal_dimension": higuchi_fractal_dimension,
    "sample_entropy": sample_entropy,
}
assert set(_POR_NOMBRE) == set(MEASURES), "MEASURES y _POR_NOMBRE se separaron"


def complexity_by_window(
    recording: Recording,
    channels: list[str],
    measure: str = "permutation_entropy",
) -> dict[str, np.ndarray]:
    """Aplica una medida de complejidad a cada ventana de 30 segundos.

    Returns:
        Diccionario canal -> array con un valor por ventana, para poder
        cruzarlo con el hipnograma.

    Los arrays tienen **exactamente `count_windows()` elementos**, y una ventana
    más corta que `MIN_SAMPLES` queda en **NaN**. Es la misma convención que
    fijó `psd.py`, y por el mismo motivo: descartar la ventana desalinearía el
    array del hipnograma, que es justamente para lo que sirve.

    **Acepta `sample_entropy` aunque tarde más de cinco minutos en una noche
    entera.** Es una función de biblioteca y quien la llama desde un script
    puede esperar; la interfaz es la que elige no ofrecerla para el barrido.

    Raises:
        UnknownMeasureError: si la medida no es una de `MEASURES`.
        InvalidRecordingError: si no se le pasa un registro.
        ChannelNotFoundError: si algún canal no existe.
    """
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede medir la complejidad de eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )
    # `not in` sobre un diccionario **hashea la clave**, así que con una lista
    # o un diccionario eleva `TypeError: unhashable type` antes de llegar al
    # mensaje. Comprobar el tipo primero es lo que hace que el rechazo salga
    # como error del programa. Lo encontró `test_contratos.py`.
    if not isinstance(measure, str) or measure not in _POR_NOMBRE:
        raise UnknownMeasureError(
            f"No se conoce la medida de complejidad «{measure}».",
            details=f"medidas disponibles: {', '.join(MEASURES)}.",
        )
    if channels is None:
        nombres = recording.channel_names()
    elif isinstance(channels, (list, tuple)) and all(
        isinstance(n, str) for n in channels
    ):
        nombres = list(channels)
    else:
        raise InvalidRecordingError(
            "Hay que decir qué canales analizar, con una lista de nombres.",
            details=f"channels es {type(channels).__name__}: {channels!r}.",
        )

    calcular = _POR_NOMBRE[measure]
    total = count_windows(recording.n_samples, recording.sampling_rate)
    resultado = {nombre: np.full(total, np.nan) for nombre in nombres}

    for ventana in range(total):
        inicio, fin = window_to_samples(ventana, recording.sampling_rate)
        # `fin` puede pasarse del final en la última ventana; `get_segment`
        # recorta y devuelve un tramo más corto, que es el caso del NaN.
        tramo = recording.get_segment(
            inicio, min(fin, recording.n_samples), nombres
        )
        if tramo.shape[1] < MIN_SAMPLES:
            continue
        for posicion, nombre in enumerate(nombres):
            # Copia explícita: `get_segment()` devuelve un array de sólo
            # lectura y numba escribe sobre el buffer que recibe.
            resultado[nombre][ventana] = calcular(np.array(tramo[posicion], copy=True))

    return resultado


__all__ = [
    "MEASURES",
    "MIN_SAMPLES",
    "complexity_by_window",
    "higuchi_fractal_dimension",
    "lempel_ziv_complexity",
    "permutation_entropy",
    "sample_entropy",
]
