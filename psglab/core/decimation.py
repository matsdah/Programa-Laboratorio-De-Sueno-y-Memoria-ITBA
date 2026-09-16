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

**El reparto con `ui/signal_view.py`** es el mismo que ya rige para las
conversiones de `core/windows.py`: acá va la aritmética, que es numpy puro y se
testea sin abrir una ventana; allá va la política, porque cuántas cubetas pedir
depende del ancho en píxeles, que es lo único que `core/` tiene prohibido
conocer.

Cubre del pliego: ningún ID. Es infraestructura de la escala de tiempo libre,
que agregó el refactor de la interfaz; el pliego pide que redibujar sea rápido
(sección 7) y esto es lo que lo sostiene cuando la página es la noche entera.
"""

import numpy as np

from psglab.utils.errors import InvalidRecordingError


def min_max_envelope(
    samples: np.ndarray, n_buckets: int
) -> tuple[np.ndarray, np.ndarray]:
    """Envolvente de una señal: dos puntos por cubeta, el mínimo y el máximo.

    Args:
        samples: la señal de un canal, en una dimensión.
        n_buckets: cuántas cubetas. Quien dibuja pasa el ancho en píxeles.

    Returns:
        Tupla (índices dentro de `samples`, valores). Los índices vienen
        **ordenados y sin repetir**: cada cubeta aporta sus dos extremos en el
        orden en que ocurren, y uno solo si coinciden —una cubeta constante—.
        Como mucho hay `2 * n_buckets` puntos, más dos de la cola que no llena
        una cubeta entera.

        Si la señal ya tiene como mucho `2 * n_buckets` muestras, se devuelve
        **entera y tal cual**: la envolvente no la achicaría, sólo la volvería
        más gruesa.

    **Ningún extremo se pierde.** Cada muestra pertenece a exactamente una
    cubeta y cada cubeta aporta su máximo y su mínimo, así que un pico de una
    sola muestra sobrevive a reducir ocho horas.

    **No copia la señal.** El cuerpo se recorre con un `reshape` sobre un tramo
    contiguo, que numpy resuelve como vista; lo único que se aloja es la salida,
    que tiene el tamaño de la pantalla y no el del registro.

    Raises:
        InvalidRecordingError: si `samples` no es un array de una dimensión, o
            si `n_buckets` no es un entero positivo. El segundo llega desde
            `ui/` calculado sobre un ancho en píxeles que, mientras se arma la
            ventana, puede valer cero: sin esta guarda saldría un
            `ZeroDivisionError`, que la ventana principal no sabe atrapar.
    """
    if not isinstance(samples, np.ndarray) or samples.ndim != 1:
        raise InvalidRecordingError(
            "No se pudo preparar la señal para dibujarla.",
            details=(
                "min_max_envelope() espera un array de una dimensión y recibió "
                f"{type(samples).__name__}"
                + (f" de forma {samples.shape}" if isinstance(samples, np.ndarray) else "")
            ),
        )
    # `bool` es subclase de `int`: sin excluirlo, `True` pasaría como una cubeta.
    if isinstance(n_buckets, bool) or not isinstance(n_buckets, (int, np.integer)):
        raise InvalidRecordingError(
            "No se pudo preparar la señal para dibujarla.",
            details=(
                "min_max_envelope() espera un número entero de cubetas y recibió "
                f"{type(n_buckets).__name__}"
            ),
        )
    if n_buckets <= 0:
        raise InvalidRecordingError(
            "No se pudo preparar la señal para dibujarla.",
            details=(
                f"min_max_envelope() necesita al menos una cubeta y recibió {n_buckets}; "
                "suele pasar si el gráfico todavía no tiene ancho"
            ),
        )

    cantidad = len(samples)
    if cantidad <= 2 * n_buckets:
        return np.arange(cantidad), samples

    por_cubeta = cantidad // n_buckets
    usadas = por_cubeta * n_buckets
    cuerpo = samples[:usadas].reshape(n_buckets, por_cubeta)

    del_minimo = cuerpo.argmin(axis=1)
    del_maximo = cuerpo.argmax(axis=1)
    primero = np.minimum(del_minimo, del_maximo)
    segundo = np.maximum(del_minimo, del_maximo)
    base = np.arange(n_buckets) * por_cubeta

    indices = np.empty(2 * n_buckets, dtype=np.intp)
    indices[0::2] = base + primero
    indices[1::2] = base + segundo
    # Una cubeta constante tiene el mínimo y el máximo en la misma muestra:
    # emitirla dos veces no dibuja nada distinto y rompe la promesa de índices
    # sin repetir.
    conservar = np.ones(2 * n_buckets, dtype=bool)
    conservar[1::2] = segundo != primero
    indices = indices[conservar]

    # La cola que no llena una cubeta entera. No se descarta: ahí puede estar
    # el último evento de la noche.
    if usadas < cantidad:
        cola = samples[usadas:]
        extremos = sorted({usadas + int(cola.argmin()), usadas + int(cola.argmax())})
        indices = np.concatenate([indices, np.asarray(extremos, dtype=np.intp)])

    return indices, samples[indices]
