"""La envolvente de la señal, calculada por trozos y guardada entre cuadros.

Una página larga no se dibuja muestra por muestra sino con la envolvente
mínimo/máximo de `core/decimation.py`, que no puede perder un pico. Esta clase
decide **qué** se calcula y **qué se guarda**; la cuenta es de `core/`.

**Los trozos se cuentan desde el comienzo del registro** y no desde el borde
de la página. Al reproducir, la página avanza una fracción de sí misma por
cuadro y casi todos sus trozos ya están: con 32 canales a 1000 Hz y página de
5 min, calcular la envolvente pasó de unos 95 ms por cuadro a 1,2 ms en uno de
cada cuatro. Contados desde el borde, cada paso los recalculaba enteros.

**La clave no incluye la escala ni el desplazamiento**, que se aplican
después: cambiar la amplitud no obliga a recalcular nada. Tampoco incluye el
registro, y por eso `forget_if_changed()` existe: filtrar devuelve un registro
nuevo con los mismos índices de muestra.

No usa Qt: es numpy y una caché, y se testea sin armar ninguna ventana.

Cubre del pliego: ningún ID; es infraestructura del visualizador.
"""

from collections import OrderedDict

import numpy as np

from psglab.core.decimation import bucket_size_for, envelope_by_bucket_size

#: Por debajo de cuántas muestras por columna de píxeles se dibuja la señal tal
#: cual. La envolvente emite dos puntos por columna, así que con menos de dos
#: muestras por columna no achicaría nada: sólo volvería más gruesa la traza.
MUESTRAS_POR_COLUMNA: int = 2

#: Cuántas cubetas se calculan y se guardan juntas: un **trozo**.
#:
#: **Es lo que decide el tirón del cuadro que cruza a un trozo nuevo.** La
#: reproducción avanza en cada cuadro una fracción de página, y cuando el borde
#: entra en un trozo que no está, se calcula entero, en todos los canales. Con
#: trozos del ancho de una página ese cuadro costaría lo mismo que sin trozos,
#: sólo que una vez cada cincuenta; con 64 cubetas es la dieciseisava parte.
#: Medido con 32 canales a 1000 Hz y página de 5 min: un paso de cada cuatro
#: cruza a un trozo nuevo, y calcularlo cuesta 1,2 ms. Más chico tampoco
#: conviene: cada trozo es una búsqueda en la caché por canal y por cuadro.
CUBETAS_POR_TROZO: int = 64

#: Cuántos trozos se recuerdan. Una página de mil columnas son dieciséis por
#: canal, así que alcanza para unas ocho páginas de 32 canales: ir y volver es
#: instantáneo. Cada trozo son como mucho 130 índices, así que el tope son unos
#: 4 MB.
TROZOS_EN_MEMORIA: int = 4096


class EnvelopeCache:
    """Qué muestras de cada canal se mandan a la pantalla, recordando lo calculado."""

    def __init__(self, capacity: int = TROZOS_EN_MEMORIA) -> None:
        """Arma la caché vacía, con lugar para `capacity` trozos."""
        self._capacidad = capacity
        #: Trozos ya calculados, del más viejo al más nuevo. La clave es
        #: (canal, muestras por cubeta, número de trozo) y el valor, los índices
        #: **absolutos** de las muestras elegidas.
        self._trozos: OrderedDict[tuple[str, int, int], np.ndarray] = OrderedDict()
        #: El registro del que salieron. Ver `forget_if_changed()`.
        self._registro: object | None = None

    def __len__(self) -> int:
        """Cuántos trozos hay guardados."""
        return len(self._trozos)

    def forget_if_changed(self, recording: object) -> None:
        """Descarta todo si el registro que se dibuja es otro.

        **La caché mentiría sin esto**, y de la peor forma: filtrar la señal
        devuelve un registro nuevo con los mismos índices de muestra, así que la
        clave sería la misma y se dibujaría la envolvente de la señal cruda
        sobre la filtrada, sin ningún aviso.

        Se compara la **identidad** del objeto y no se espera un aviso: cualquier
        camino que cambie el registro —filtrar, derivar, re-referenciar,
        deshacer, abrir otro archivo— termina en un dibujo, y acá se entera sin
        que nadie tenga que acordarse de avisarle.
        """
        if recording is not self._registro:
            self._trozos.clear()
            self._registro = recording

    def samples_to_draw(
        self,
        channel_name: str,
        start_sample: int,
        stop_sample: int,
        channel: np.ndarray,
        columns: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Qué muestras de un canal se dibujan, y en qué posición.

        Args:
            channel: el canal **entero**, no la página: las cubetas se cuentan
                desde la primera muestra del registro.
            columns: las columnas de píxeles del área de dibujo.

        Returns:
            Tupla (posiciones relativas a `start_sample`, valores). Con pocas
            muestras son todas las de la página; con muchas, la envolvente
            mínimo/máximo, que conserva cada pico y tiene el tamaño de la
            pantalla y no el del registro.

        **Las cubetas de los bordes se devuelven enteras**, aunque empiecen
        antes de la página o terminen después. Un extremo que cae afuera queda
        fuera de la pantalla, que lo recorta; recortarlo acá partiría la cubeta
        y le cambiaría la forma según dónde esté el borde.
        """
        if stop_sample - start_sample <= MUESTRAS_POR_COLUMNA * columns:
            return np.arange(stop_sample - start_sample), channel[start_sample:stop_sample]

        por_cubeta = bucket_size_for(stop_sample - start_sample, columns)
        por_trozo = CUBETAS_POR_TROZO * por_cubeta
        trozos = range(start_sample // por_trozo, (stop_sample - 1) // por_trozo + 1)
        indices = np.concatenate(
            [self._trozo(channel_name, trozo, por_cubeta, channel) for trozo in trozos]
        )

        # Los trozos de los bordes traen cubetas que no tocan la página.
        desde = (start_sample // por_cubeta) * por_cubeta
        hasta = -(-stop_sample // por_cubeta) * por_cubeta
        primero, ultimo = np.searchsorted(indices, (desde, hasta))
        indices = indices[primero:ultimo]
        return indices - start_sample, channel[indices]

    def _trozo(
        self, channel_name: str, chunk: int, bucket_size: int, channel: np.ndarray
    ) -> np.ndarray:
        """Los índices absolutos que la envolvente elige en un trozo, calculados
        una sola vez."""
        clave = (channel_name, bucket_size, chunk)
        guardado = self._trozos.get(clave)
        if guardado is not None:
            self._trozos.move_to_end(clave)
            return guardado

        desde = chunk * CUBETAS_POR_TROZO * bucket_size
        hasta = min(desde + CUBETAS_POR_TROZO * bucket_size, len(channel))
        indices, _ = envelope_by_bucket_size(channel[desde:hasta], bucket_size)
        calculado = indices + desde
        self._trozos[clave] = calculado
        if len(self._trozos) > self._capacidad:
            self._trozos.popitem(last=False)
        return calculado
