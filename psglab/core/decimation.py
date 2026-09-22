"""Reducir una señal larga a lo que cabe en la pantalla sin perder sus picos.

Existe por un número: un registro de 32 canales a 1000 Hz durante ocho horas
son 28,8 millones de muestras **por canal**. Mandar eso a dibujar no es lento,
es imposible —230 MB de `float64` por canal, unos 7 GB por pantalla—, y la
escala de tiempo libre permite pedir el registro entero de una vez.

La salida es la **envolvente mínimo/máximo**: se parte la señal en tantas
cubetas como columnas de píxeles haya, y de cada una se toman dos puntos, el
mínimo y el máximo. Unas tres mil muestras por canal, dé lo mismo si la página
son 30 segundos u ocho horas.

**Por qué mínimo/máximo y no otra cosa.** En polisomnografía el pico *es* el
dato: un huso, un complejo K, una espiga. Tomar una muestra de cada `n`
(`samples[::n]`) la descarta casi siempre, y promediar la aplana. La
envolvente, en cambio, **no puede perder un extremo por construcción**: cada
muestra cae en exactamente una cubeta y cada cubeta aporta su máximo y su
mínimo, así que una espiga de una sola muestra se dibuja a altura completa
sobre ocho horas.

**Por qué en el orden en que ocurren.** Emitir siempre primero el mínimo y
después el máximo dibujaría cada espiga como un ensanchamiento simétrico de la
traza. Respetar el orden cuesta una comparación y es lo que hace que una espiga
hacia arriba se vea como una espiga hacia arriba.

**Las cubetas se cuentan desde el comienzo del registro, no desde el borde de
la página** (hito 49). Hasta entonces cada página se partía desde su primera
muestra, y eso tenía dos costos. El caro: al reproducir, la página avanza un
poco en cada cuadro, así que **ninguna cubeta del cuadro anterior servía** y la
envolvente se recalculaba entera —con 32 canales a 1000 Hz y página de 5 min,
unos 100 ms de los 40 que tiene un cuadro—. El visible: la misma muestra caía
en cubetas distintas de un cuadro al otro, y los picos cambiaban de forma
mientras la señal pasaba. Con la grilla fija al registro, una cubeta es la
misma en cualquier página del mismo tamaño, y el visualizador puede guardarla y
calcular sólo las que entran.

Por eso la función recibe el **tamaño** de cubeta y no la cantidad: la cantidad
depende de dónde empieza el tramo, el tamaño no. `bucket_size_for()` lo saca
del ancho en píxeles.

**El reparto con `ui/signal_view.py`** es el mismo que ya rige para las
conversiones de `core/windows.py`: acá va la aritmética, que es numpy puro y se
testea sin abrir una ventana; allá va la política —cuántas cubetas pedir, qué
guardar y cuánto—, porque depende del ancho en píxeles, que es lo único que
`core/` tiene prohibido conocer.

Cubre del pliego: ningún ID. Es infraestructura de la escala de tiempo libre,
que agregó el refactor de la interfaz; el pliego pide que redibujar sea rápido
(sección 7) y esto es lo que lo sostiene cuando la página es la noche entera.
"""

import numpy as np

from psglab.utils.errors import InvalidRecordingError


def _rechazar(details: str) -> InvalidRecordingError:
    return InvalidRecordingError("No se pudo preparar la señal para dibujarla.", details=details)


def _es_entero(value: object) -> bool:
    # `bool` es subclase de `int`: sin excluirlo, `True` pasaría como un uno.
    return not isinstance(value, bool) and isinstance(value, (int, np.integer))


def bucket_size_for(n_samples: int, n_buckets: int) -> int:
    """Cuántas muestras por cubeta hacen falta para que `n_samples` entren en
    `n_buckets` cubetas, como mucho.

    **Redondeando hacia arriba, y no con `n_samples // n_buckets`.** Con la
    división entera, 3000 muestras sobre 1120 columnas daban cubetas de 2 que
    cubrían sólo 2240: los últimos 760 —la cuarta parte de una página de 30 s a
    100 Hz— quedaban en la cola, reducidos a dos puntos, y la señal se dibujaba
    cortada con una recta al final. Hacia arriba, las cubetas enteras no pasan
    de `n_buckets`.

    Nunca devuelve menos de uno: una cubeta de una muestra es la señal tal cual.

    Raises:
        InvalidRecordingError: si alguno no es entero, si `n_samples` es
            negativo o si `n_buckets` no es positivo. El segundo llega desde
            `ui/` calculado sobre un ancho en píxeles que, mientras se arma la
            ventana, puede valer cero: sin esta guarda saldría un
            `ZeroDivisionError`, que la ventana principal no sabe atrapar.
    """
    if not _es_entero(n_samples) or n_samples < 0:
        raise _rechazar(
            f"bucket_size_for() espera una cantidad de muestras entera y no negativa, y recibió {n_samples!r}"
        )
    if not _es_entero(n_buckets):
        raise _rechazar(
            "bucket_size_for() espera un número entero de cubetas y recibió "
            f"{type(n_buckets).__name__}"
        )
    if n_buckets <= 0:
        raise _rechazar(
            f"bucket_size_for() necesita al menos una cubeta y recibió {n_buckets}; "
            "suele pasar si el gráfico todavía no tiene ancho"
        )
    return max(1, -(-int(n_samples) // int(n_buckets)))


def envelope_by_bucket_size(
    samples: np.ndarray, bucket_size: int
) -> tuple[np.ndarray, np.ndarray]:
    """Envolvente de una señal: dos puntos por cubeta, el mínimo y el máximo.

    Args:
        samples: la señal de un canal, en una dimensión. **Las cubetas se
            cuentan desde su primera muestra**: para que caigan sobre la grilla
            del registro, quien llama pasa un tramo que empiece en un múltiplo
            de `bucket_size`.
        bucket_size: cuántas muestras por cubeta. Ver `bucket_size_for()`.

    Returns:
        Tupla (índices dentro de `samples`, valores). Los índices vienen
        **ordenados y sin repetir**: cada cubeta aporta sus dos extremos en el
        orden en que ocurren, y uno solo si coinciden —una cubeta constante, o
        una de una sola muestra—. La última cubeta puede ser más corta: es la
        cola que no la llena, y no se descarta.

    **Ningún extremo se pierde.** Cada muestra pertenece a exactamente una
    cubeta y cada cubeta aporta su máximo y su mínimo, así que un pico de una
    sola muestra sobrevive a reducir ocho horas.

    **No copia la señal.** El cuerpo se recorre con un `reshape` sobre un tramo
    contiguo, que numpy resuelve como vista; lo único que se aloja es la salida,
    que tiene el tamaño de la pantalla y no el del registro.

    Raises:
        InvalidRecordingError: si `samples` no es un array de una dimensión, o
            si `bucket_size` no es un entero positivo.
    """
    if not isinstance(samples, np.ndarray) or samples.ndim != 1:
        raise _rechazar(
            "envelope_by_bucket_size() espera un array de una dimensión y recibió "
            f"{type(samples).__name__}"
            + (f" de forma {samples.shape}" if isinstance(samples, np.ndarray) else "")
        )
    if not _es_entero(bucket_size):
        raise _rechazar(
            "envelope_by_bucket_size() espera un tamaño de cubeta entero y recibió "
            f"{type(bucket_size).__name__}"
        )
    if bucket_size <= 0:
        raise _rechazar(
            f"envelope_by_bucket_size() necesita cubetas de al menos una muestra y recibió {bucket_size}"
        )

    por_cubeta = int(bucket_size)
    cantidad = len(samples)
    cubetas = cantidad // por_cubeta
    usadas = por_cubeta * cubetas
    cuerpo = samples[:usadas].reshape(cubetas, por_cubeta)

    del_minimo = cuerpo.argmin(axis=1)
    del_maximo = cuerpo.argmax(axis=1)
    primero = np.minimum(del_minimo, del_maximo)
    segundo = np.maximum(del_minimo, del_maximo)
    base = np.arange(cubetas) * por_cubeta

    indices = np.empty(2 * cubetas, dtype=np.intp)
    indices[0::2] = base + primero
    indices[1::2] = base + segundo
    # Una cubeta constante tiene el mínimo y el máximo en la misma muestra:
    # emitirla dos veces no dibuja nada distinto y rompe la promesa de índices
    # sin repetir.
    conservar = np.ones(2 * cubetas, dtype=bool)
    conservar[1::2] = segundo != primero
    indices = indices[conservar]

    # La cola que no llena una cubeta entera. No se descarta: ahí puede estar
    # el último evento de la noche.
    if usadas < cantidad:
        cola = samples[usadas:]
        extremos = sorted({usadas + int(cola.argmin()), usadas + int(cola.argmax())})
        indices = np.concatenate([indices, np.asarray(extremos, dtype=np.intp)])

    return indices, samples[indices]
