"""Modelo del registro polisomnográfico cargado en memoria.

Es la estructura central del programa: todo lo demás (visualización, scoring,
anotaciones, análisis) opera sobre un `Recording`. Los lectores de
`psglab.readers` producen objetos de este tipo, de modo que el resto del
programa no sabe ni le importa de qué formato vino la señal.

Cubre del pliego: es el soporte de V1_F, V2_F y V3_F de "Importación de
archivos" y de V4_F de "Visualización de la señal".
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np


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
    """

    file_path: Path
    channels: list[Channel]
    data: np.ndarray
    sampling_rate: float
    start_time: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def n_channels(self) -> int:
        """Cantidad de canales del registro."""
        raise NotImplementedError("Pendiente: devolver la cantidad de canales.")

    @property
    def n_samples(self) -> int:
        """Cantidad de muestras ("puntos") por canal."""
        raise NotImplementedError("Pendiente: devolver la cantidad de muestras.")

    @property
    def duration_seconds(self) -> float:
        """Duración total del registro en segundos."""
        raise NotImplementedError("Pendiente: calcular n_samples / sampling_rate.")

    def channel_names(self) -> list[str]:
        """Nombres de todos los canales, en orden."""
        raise NotImplementedError("Pendiente: devolver los nombres de los canales.")

    def channel_by_name(self, name: str) -> Channel:
        """Busca un canal por su nombre.

        Raises:
            ChannelNotFoundError: si no existe un canal con ese nombre.
        """
        raise NotImplementedError("Pendiente: buscar el canal por nombre.")

    def channels_of_kind(self, kind: ChannelKind) -> list[Channel]:
        """Devuelve todos los canales de una clase dada.

        Lo usa el selector de canales para ofrecer "mostrar todos los EEG" o
        "ocultar los EMG" (V3_P).
        """
        raise NotImplementedError("Pendiente: filtrar los canales por clase.")

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
        """
        raise NotImplementedError("Pendiente: recortar el tramo pedido de la matriz.")
