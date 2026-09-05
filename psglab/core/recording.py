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


@dataclass
class Channel:
    """Un canal del registro.

    Attributes:
        name: nombre tal como viene en el archivo (ej. "C3", "EOG izq").
        kind: clase detectada automáticamente (EEG, EOG, EMG, ECG, ...).
        unit: unidad física original del archivo. La señal se normaliza
            internamente a microvoltios (ver `psglab.utils.units`).
        index: posición del canal dentro de la matriz de datos.
    """

    name: str
    kind: ChannelKind
    unit: str
    index: int


@dataclass
class Recording:
    """Un registro polisomnográfico completo.

    Attributes:
        file_path: archivo del que se cargó el registro.
        channels: lista de canales, en el mismo orden que las filas de `data`.
        data: matriz de forma (n_canales, n_muestras) en microvoltios.
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
                no es de dos dimensiones o no tiene ningún canal, si sus valores
                no son de punto flotante, si la cantidad de canales no coincide
                con sus filas, si la frecuencia de muestreo no es un número
                finito y positivo, o si el `index` de un canal no es su posición
                en la lista.
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
        # para un registro con muestras.
        if not math.isfinite(self.sampling_rate) or self.sampling_rate <= 0:
            raise InvalidRecordingError(
                f"El registro '{self.file_path.name}' declara una frecuencia de muestreo "
                "que no es válida, así que no se puede ubicar ninguna ventana en el tiempo.",
                details=(
                    f"sampling_rate = {self.sampling_rate}, se esperaba un número "
                    "finito y positivo."
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
        """
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
            channel_names: canales pedidos. Si es None, devuelve todos.

        Returns:
            Matriz de forma (n_canales_pedidos, stop_sample - start_sample)
            en microvoltios.

            **Si `stop_sample` se pasa del final del registro, el tramo sale más
            corto, en silencio.** No es un descuido: la última ventana de un
            registro que no termina en un múltiplo exacto de 30 segundos es
            justamente así, y `core.windows.window_to_samples` devuelve para ella
            un `stop` posterior al final. O sea que éste es el caso normal al
            dibujar la última ventana, no un error que haya que reportar.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
        """
        if channel_names is None:
            return self.data[:, start_sample:stop_sample]
        filas = [self.channel_by_name(nombre).index for nombre in channel_names]
        return self.data[filas, start_sample:stop_sample]
