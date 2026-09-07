"""Modelo del registro polisomnográfico cargado en memoria.

Es la estructura central del programa: todo lo demás (visualización, scoring,
anotaciones, análisis) opera sobre un `Recording`. Los lectores de
`psglab.readers` producen objetos de este tipo, de modo que el resto del
programa no sabe ni le importa de qué formato vino la señal.

Cubre del pliego: es el soporte de V1_F, V2_F y V3_F de "Importación de
archivos" y de V4_F de "Visualización de la señal".
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np

from psglab.utils.errors import (
    ChannelNotFoundError,
    DuplicateChannelError,
    InvalidRecordingError,
)
from psglab.utils.validation import check_finite


class ChannelKind(Enum):
    """Clase de señal de un canal.

    El pliego (V4_F) pide que el software detecte automáticamente la clase de
    cada canal y la muestre junto al nombre. La detección vive en
    `psglab.readers.channel_types`; acá sólo se define el vocabulario.
    """

    EEG = "EEG"
    EOG = "EOG"
    EMG = "EMG"
    ECG = "ECG"
    RESPIRATORY = "Respiratorio"
    OTHER = "Otro"


@dataclass(frozen=True)
class Channel:
    """Un canal del registro.

    Attributes:
        name: nombre tal como viene en el archivo (ej. "C3", "EOG izq").
        kind: clase detectada automáticamente (EEG, EOG, EMG, ECG, ...).
        unit: unidad física original del archivo, y **la fuente de verdad de
            en qué escala está la fila**. Los canales eléctricos se normalizan
            a microvoltios al importar (ver `psglab.utils.units`); los que no
            son eléctricos —una temperatura en °C, un marcador sin unidad— no
            se pueden convertir y conservan la suya.
        index: posición del canal dentro de la matriz de datos.
        original_sampling_rate: frecuencia a la que venía este canal en el
            archivo, en Hz, o None si el formato no la distingue por canal.

    **Inmutable a propósito.** `channel_by_name()` y `channels_of_kind()`
    devuelven el canal interno, y siendo mutable se lo podía renombrar desde
    afuera: después `get_segment(["nombre nuevo"])` devolvía la fila de otro
    canal bajo el nombre pedido, que es señal equivocada presentada como si
    fuera la correcta. Corregir la clase detectada de un canal (V4_F) se hace
    construyendo otro, no escribiéndole encima.

    **La frecuencia original se guarda porque el registro tiene una sola.** Un
    EDF puede traer cada canal a una frecuencia distinta —el registro de prueba
    de la Sleep-EDF trae tres canales a 100 Hz y cuatro a 1 Hz— y MNE los
    unifica sobremuestreando, sin avisar. Después de eso la matriz es coherente,
    pero un EMG de 1 Hz llevado a 100 Hz es señal repetida en escalones, y sin
    este campo **no queda registro de que lo sea**: el investigador vería una
    señal de aspecto normal sin forma de saber que su resolución real es cien
    veces menor. `Recording.sampling_rate` sigue siendo la única frecuencia de
    la matriz; ésta es de dónde vino cada fila.

    """

    name: str
    kind: ChannelKind
    unit: str
    index: int
    original_sampling_rate: float | None = None


@dataclass
class Recording:
    """Un registro polisomnográfico completo.

    Attributes:
        file_path: archivo del que se cargó el registro.
        channels: lista de canales, en el mismo orden que las filas de `data`.
        data: matriz de forma (n_canales, n_muestras). Los canales eléctricos
            están en microvoltios; los que no se pueden convertir conservan su
            escala nativa, y `Channel.unit` dice cuál es. **Ninguna capa debería
            asumir que una fila está en µV sin mirar la unidad de su canal**: el
            pliego pide no limitar por tipo de señal, así que un registro
            normal trae termómetros y marcadores además de EEG.
        sampling_rate: frecuencia de muestreo en Hz, común a todos los canales.
        start_time: horario de inicio del registro si el archivo lo informa.
            El pliego lo usa en V2_F del histograma para poner el eje en hora
            real; si es None, el eje va de ventana 1 a VENMAX.
        metadata: lo que trae el archivo y no entra en los campos de arriba.
            Cada lector decide qué guardar acá: `brainvision.py` deja los
            marcadores del `.vmrk` para poder convertirlos en anotaciones si el
            usuario lo pide, e `impedance.py` busca acá las impedancias cuando
            el formato las trae. **El contenido depende del formato de origen,
            así que ninguna capa debería darlo por presente sin verificarlo.**
    """

    file_path: Path
    channels: list[Channel]
    data: np.ndarray
    sampling_rate: float
    start_time: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Rechaza un registro que no es coherente consigo mismo.

        Se valida acá, al construir, para que el error salte **en el lector, que
        es donde está el bug**, y no tres capas más arriba con una traza de
        numpy que no dice de dónde vino. Es el mismo criterio que ya declara
        `psglab.utils.units.to_microvolts`: preferir fallar a asumir.

        Raises:
            InvalidRecordingError: si `file_path` no es un `Path`, si la matriz
                no es de dos dimensiones, no tiene ningún canal o no tiene
                ninguna muestra, si sus valores no son de punto flotante, si la
                cantidad de canales no coincide con sus filas, si la frecuencia
                de muestreo no es un número finito y positivo, o si el `index` de
                un canal no es su posición en la lista.
            DuplicateChannelError: si dos canales se llaman igual. Los canales se
                piden por nombre en toda la interfaz, así que un nombre repetido
                vuelve ambiguo cuál se está mostrando.
        """
        # Va primero porque todos los mensajes de abajo usan `file_path.name`:
        # con un `str` la validación entera se convertiría en un AttributeError,
        # y el tipo equivocado sólo se notaría el día que hubiera otro error.
        if not isinstance(self.file_path, Path):
            raise InvalidRecordingError(
                "El registro no se pudo interpretar porque su ruta no es una ruta.",
                details=f"file_path es {type(self.file_path).__name__}, se esperaba Path.",
            )

        # El tipo antes de la forma, por el mismo motivo que la ruta: una lista
        # de listas —el error más obvio de un lector nuevo— no tiene `.ndim`, y
        # sin esta guarda la validación entera se convertía en un AttributeError
        # de numpy, que es justo lo que este método existe para impedir.
        if not isinstance(self.data, np.ndarray):
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' no se pudo interpretar: la señal "
                "no llegó como una matriz.",
                details=f"data es {type(self.data).__name__}, se esperaba numpy.ndarray.",
            )

        if not isinstance(self.channels, list):
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' no se pudo interpretar: la lista "
                "de canales no es una lista.",
                details=f"channels es {type(self.channels).__name__}.",
            )

        nombres_raros = [c for c in self.channels if not isinstance(getattr(c, "name", None), str)]
        if nombres_raros:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' tiene canales sin un nombre "
                "utilizable, y los canales se piden por nombre en toda la interfaz.",
                details=f"{len(nombres_raros)} canal(es) con un nombre que no es texto.",
            )

        if self.data.ndim != 2:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' no se pudo interpretar: la señal "
                "no tiene la forma esperada de canales por muestras.",
                details=f"data.ndim = {self.data.ndim}, se esperaba 2.",
            )

        if len(self.channels) != self.data.shape[0]:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' declara {len(self.channels)} canales "
                f"pero la señal trae {self.data.shape[0]}.",
                details=(
                    f"len(channels) = {len(self.channels)}, "
                    f"data.shape = {self.data.shape}."
                ),
            )

        if not self.channels:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' no tiene ningún canal, así que no "
                "hay nada que mostrar ni que scorear.",
                details=f"data.shape = {self.data.shape}.",
            )

        # Simétrico con el de arriba: canales sin señal es tan incoherente como
        # señal sin canales. Además hace imposible por construcción el caso
        # degenerado de `Session`, que sobre un registro sin muestras tendría
        # cero ventanas y un `current_window` apuntando a una que no existe.
        if self.data.shape[1] == 0:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' no tiene ninguna muestra: declara "
                "canales pero no trae señal.",
                details=f"data.shape = {self.data.shape}.",
            )

        # Los enteros son las cuentas crudas del conversor analógico-digital.
        # Que lleguen hasta acá significa que el lector no aplicó la conversión
        # a microvoltios, que es exactamente el fallo que `utils/units.py`
        # existe para impedir, y produce una señal escalada por un factor
        # arbitrario que en pantalla sigue pareciendo una señal.
        if not np.issubdtype(self.data.dtype, np.floating):
            raise InvalidRecordingError(
                f"La señal del registro '{self.file_path.name}' no está en microvoltios: "
                "llegó con valores enteros, que son las cuentas crudas del equipo.",
                details=f"data.dtype = {self.data.dtype}, se esperaba punto flotante.",
            )

        # `<= 0` a secas no alcanza: es **falso** para NaN, así que un NaN se
        # colaba y reaparecía mucho más lejos como un ValueError de numpy dentro
        # de `core/windows.py`. Y un infinito daba una duración de 0 segundos
        # para un registro con muestras. `check_finite` cubre además el caso de
        # una frecuencia que llega como texto, que antes daba un TypeError crudo.
        check_finite(
            self.sampling_rate,
            error=InvalidRecordingError,
            message=(
                f"El registro '{self.file_path.name}' declara una frecuencia de muestreo "
                "que no es válida, así que no se puede ubicar ninguna ventana en el tiempo."
            ),
            details="Se esperaba un número finito y positivo.",
        )
        if self.sampling_rate <= 0:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' declara una frecuencia de muestreo "
                "que no es válida, así que no se puede ubicar ninguna ventana en el tiempo.",
                details=f"sampling_rate = {self.sampling_rate}, se esperaba un número positivo.",
            )

        # Es opcional, pero si viene tiene que ser un número usable: se muestra
        # junto al nombre del canal, y un NaN se leería como "nan Hz" en la
        # lista de canales. Mismo criterio que la frecuencia de la matriz.
        for canal in self.channels:
            if canal.original_sampling_rate is None:
                continue
            check_finite(
                canal.original_sampling_rate,
                error=InvalidRecordingError,
                message=(
                    f"El registro '{self.file_path.name}' declara para el canal "
                    f"'{canal.name}' una frecuencia original que no es válida."
                ),
                details="Se esperaba un número finito y positivo, o ninguno.",
                minimum=0,
            )
            if canal.original_sampling_rate <= 0:
                raise InvalidRecordingError(
                    f"El registro '{self.file_path.name}' declara para el canal "
                    f"'{canal.name}' una frecuencia original que no es válida.",
                    details=(
                        f"original_sampling_rate = {canal.original_sampling_rate}, "
                        "se esperaba un número positivo."
                    ),
                )

        desubicados = [c.name for i, c in enumerate(self.channels) if c.index != i]
        if desubicados:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' tiene canales cuya posición declarada "
                "no coincide con la fila que ocupan en la señal.",
                details=f"Canales desubicados: {', '.join(desubicados)}.",
            )

        nombres = [c.name for c in self.channels]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        if repetidos:
            raise DuplicateChannelError(
                f"El registro '{self.file_path.name}' tiene más de un canal con el mismo "
                "nombre, así que no se puede saber a cuál se refiere cada pedido.",
                details=f"Nombres repetidos: {', '.join(repetidos)}.",
            )

    @property
    def n_channels(self) -> int:
        """Cantidad de canales del registro.

        Sale de `channels` y no de `data.shape[0]`: la lista es la que tiene los
        nombres y las clases, y `__post_init__` es lo que garantiza que las dos
        coincidan. Sin esa validación habría dos fuentes de verdad.
        """
        return len(self.channels)

    @property
    def n_samples(self) -> int:
        """Cantidad de muestras ("puntos") por canal."""
        return int(self.data.shape[1])

    @property
    def duration_seconds(self) -> float:
        """Duración total del registro en segundos.

        Es la duración **real** de la señal. No confundir con el tiempo que
        cubren las ventanas de scoring: la última puede estar incompleta y
        `exporters/statistics.py` la cuenta entera, así que los dos números
        difieren hasta en una ventana.
        """
        return self.n_samples / self.sampling_rate

    def channel_names(self) -> list[str]:
        """Nombres de todos los canales, en orden."""
        return [canal.name for canal in self.channels]

    def channel_by_name(self, name: str) -> Channel:
        """Busca un canal por su nombre.

        Raises:
            ChannelNotFoundError: si no existe un canal con ese nombre.
        """
        for canal in self.channels:
            if canal.name == name:
                return canal
        raise ChannelNotFoundError(
            f"El registro no tiene ningún canal llamado '{name}'.",
            details=f"Canales disponibles: {', '.join(self.channel_names())}.",
        )

    def channels_of_kind(self, kind: ChannelKind) -> list[Channel]:
        """Devuelve todos los canales de una clase dada.

        Lo usa el selector de canales para ofrecer "mostrar todos los EEG" o
        "ocultar los EMG" (V3_P). Una clase sin canales devuelve una lista
        vacía: no es un error, es un registro que no tiene ese tipo de señal.

        Raises:
            InvalidRecordingError: si `kind` no es un `ChannelKind`. Se rechaza
                en vez de devolver la lista vacía porque las dos respuestas se
                leen igual desde afuera: pasar la cadena `"EEG"` en vez del enum
                haría que el programa afirme que el registro no tiene ningún EEG.
        """
        if not isinstance(kind, ChannelKind):
            raise InvalidRecordingError(
                "Se pidieron los canales de una clase que no existe.",
                details=f"kind es {type(kind).__name__}, se esperaba ChannelKind.",
            )
        return [canal for canal in self.channels if canal.kind is kind]

    def get_segment(
        self,
        start_sample: int,
        stop_sample: int,
        channel_names: list[str] | None = None,
    ) -> np.ndarray:
        """Extrae un tramo de señal.

        Es el método que usa el visualizador para pedir exactamente la ventana
        que tiene que dibujar, sin copiar el registro entero.

        Args:
            start_sample: primera muestra incluida.
            stop_sample: primera muestra excluida.
            channel_names: canales pedidos, en el orden en que se quieren
                apilar, que no tiene por qué ser el del registro. **Si es
                `None` devuelve todos; una lista vacía devuelve ninguno**, que
                no es lo mismo. Un nombre repetido en la lista repite la fila.

        Returns:
            Matriz de forma (n_canales_pedidos, stop_sample - start_sample)
            en microvoltios.

            **Si `stop_sample` se pasa del final del registro, el tramo sale más
            corto, en silencio.** No es un descuido: la última ventana de un
            registro que no termina en un múltiplo exacto de 30 segundos es
            justamente así, y `core.windows.window_to_samples` devuelve para ella
            un `stop` posterior al final. O sea que éste es el caso normal al
            dibujar la última ventana, no un error que haya que reportar.

            El arreglo devuelto es de **sólo lectura**. Es un recorte de la
            señal del registro, no una copia, así que escribir en él modificaría
            el registro; y como pedir canales sueltos sí copia, el efecto
            dependería de qué canales pidió el usuario. Se marca de sólo lectura
            para que las dos ramas se comporten igual, sin pagar una copia.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
            InvalidRecordingError: si `start_sample` es negativo o mayor que
                `stop_sample`. `core.windows` documenta que sus conversiones
                devuelven números negativos en silencio ante un índice de
                ventana negativo, y sin esta guarda un índice así devolvía señal
                **del final del registro** presentada como si fuera del
                principio: numpy interpreta el negativo como "desde el final".
                Es la clase de error que produce un resultado plausible y
                equivocado, que es peor que uno vacío.
        """
        if start_sample < 0 or start_sample > stop_sample:
            raise InvalidRecordingError(
                "Se pidió un tramo de señal que no existe en el registro.",
                details=(
                    f"start_sample = {start_sample}, stop_sample = {stop_sample}; "
                    "se esperaba 0 <= start_sample <= stop_sample."
                ),
            )

        if channel_names is None:
            tramo = self.data[:, start_sample:stop_sample]
        else:
            filas = [self.channel_by_name(nombre).index for nombre in channel_names]
            tramo = self.data[filas, start_sample:stop_sample]

        tramo.flags.writeable = False
        return tramo
