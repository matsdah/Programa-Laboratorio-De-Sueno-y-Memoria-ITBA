"""Re-referenciación de la señal.

El EEG mide diferencias de potencial, así que todo canal se lee siempre
respecto de alguna referencia. Cambiarla cambia lo que se ve, y es una
operación de rutina: los husos se ven mejor con una referencia y las ondas
lentas con otra.

**Qué pasa con lo que no es eléctrico**, que el esqueleto no decidía: no se
toca. Restarle a un termómetro un promedio de microvoltios da un número, y ése
es el problema —no falla, produce una temperatura falsa—. `Channel.unit` es la
fuente de verdad, igual que en el resto del programa, y los canales que no se
pueden convertir a microvoltios pasan intactos.

**El canal de referencia queda en cero**, y se conserva. Es lo correcto: un
canal leído contra sí mismo es cero por definición, y borrarlo en silencio le
cambiaría al usuario la lista de canales sin avisarle.

Cubre del pliego: sección "Rereferenciar".
"""

from __future__ import annotations

import numpy as np

from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import InvalidRecordingError
from psglab.utils.units import is_electrical


def _exigir_registro(recording: Recording) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`."""
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede re-referenciar eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )


def _restar(recording: Recording, referencia: np.ndarray) -> Recording:
    """Devuelve un registro nuevo con la referencia restada a lo eléctrico.

    Es el motor de las dos funciones públicas: la única diferencia entre ellas
    es de dónde sale el array de referencia.
    """
    datos = np.array(recording.data, dtype=float, copy=True)
    for canal in recording.channels:
        if is_electrical(canal.unit):
            datos[canal.index] -= referencia

    return Recording(
        file_path=recording.file_path,
        channels=[
            Channel(
                name=c.name,
                kind=c.kind,
                unit=c.unit,
                index=c.index,
                original_sampling_rate=c.original_sampling_rate,
            )
            for c in recording.channels
        ],
        data=datos,
        sampling_rate=recording.sampling_rate,
        start_time=recording.start_time,
        metadata=dict(recording.metadata),
    )


def rereference(recording: Recording, reference_channels: list[str]) -> Recording:
    """Re-referencia el registro a uno o varios canales.

    Args:
        reference_channels: canales que forman la referencia nueva. Con más de
            uno se usa su promedio, que es lo habitual al referenciar a los
            mastoides (A1 y A2).

    Returns:
        Un `Recording` nuevo, con el original intacto.

    Raises:
        ChannelNotFoundError: si alguno de los canales de referencia no existe.
        InvalidRecordingError: si la lista viene vacía, si algún canal de
            referencia no es eléctrico, o si lo que se pasa no es un registro.
    """
    _exigir_registro(recording)
    if not isinstance(reference_channels, list) or not reference_channels:
        raise InvalidRecordingError(
            "Hay que decir contra qué canal o canales re-referenciar.",
            details=f"reference_channels = {reference_channels!r}.",
        )

    canales = [recording.channel_by_name(nombre) for nombre in reference_channels]
    no_electricos = [c.name for c in canales if not is_electrical(c.unit)]
    if no_electricos:
        raise InvalidRecordingError(
            "La referencia tiene que ser un canal eléctrico: no se puede leer el "
            f"EEG respecto de {', '.join(no_electricos)}.",
            details=f"unidades: {[(c.name, c.unit) for c in canales]}.",
        )

    # El promedio de las filas elegidas. Con una sola es esa fila, así que no
    # hace falta un caso aparte.
    referencia = np.mean(
        np.asarray(recording.data)[[c.index for c in canales]], axis=0
    )
    return _restar(recording, referencia)


def average_reference(recording: Recording, kind_only: bool = True) -> Recording:
    """Re-referencia al promedio de todos los canales.

    Args:
        kind_only: si es True, promedia sólo los canales EEG. Meter en el
            promedio un EMG o un ECG lo contaminaría todo, así que el valor
            por defecto es el seguro.

    Returns:
        Un `Recording` nuevo, con el original intacto.

    Con `kind_only=True` la suma de los canales EEG re-referenciados da cero en
    cada muestra, que es la propiedad que define la referencia promedio.

    Raises:
        InvalidRecordingError: si no queda ningún canal para promediar. Con
            `kind_only=True` pasa en un registro sin EEG, y devolver la señal
            sin tocar sería peor: el usuario creería que re-referenció.
    """
    _exigir_registro(recording)
    if kind_only:
        canales = recording.channels_of_kind(ChannelKind.EEG)
        de_donde = "EEG"
    else:
        canales = [c for c in recording.channels if is_electrical(c.unit)]
        de_donde = "eléctricos"

    if not canales:
        raise InvalidRecordingError(
            f"El registro no tiene canales {de_donde}, así que no hay con qué "
            "calcular la referencia promedio.",
            details=(
                f"kind_only={kind_only}; unidades presentes: "
                f"{sorted({c.unit for c in recording.channels})}."
            ),
        )

    referencia = np.mean(
        np.asarray(recording.data)[[c.index for c in canales]], axis=0
    )
    return _restar(recording, referencia)
