"""Derivaciones: canales nuevos calculados a partir de los existentes.

Una derivación es la diferencia entre dos canales, y es la forma estándar de
nombrar los montajes de polisomnografía: "C3-A2" quiere decir el canal C3
leído respecto del mastoides A2.

El canal derivado se agrega al registro en lugar de reemplazar a los
originales, para que el usuario pueda seguir viendo los canales de base.

**Tres cosas que el esqueleto dejaba sin decidir**, y que se deciden acá porque
el canal nuevo no puede quedar sin ellas:

- **La unidad.** Los dos canales tienen que tener la misma o la resta no
  significa nada. Restar un termómetro de un EEG da un número, y ése es el
  problema: no da error, da señal falsa. Se rechaza.
- **La clase.** Si los dos son de la misma, el derivado la hereda; si no, queda
  como `OTHER`. Un "C3-EMG" no es un EEG ni un EMG, y decir que es cualquiera
  de los dos haría que se filtrara con los parámetros equivocados.
- **La frecuencia original.** Se conserva si los dos coinciden, y si no queda
  en `None`: es el campo que dice a qué frecuencia venía el canal en el
  archivo, y un derivado de dos frecuencias distintas no vino a ninguna.

Cubre del pliego: sección "Derivar".
"""

from __future__ import annotations

import numpy as np

from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    ChannelNotFoundError,
    DuplicateChannelError,
    InvalidRecordingError,
    memoria_suficiente,
)


def _exigir_registro(recording: Recording) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`.

    Sin esto sale un `AttributeError` crudo, que la ventana principal no atrapa:
    sólo atrapa `PsgLabError`, así que le llegaría al investigador como traza.
    """
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede derivar sobre eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )


def _canal_derivado(
    a: Channel, b: Channel, nombre: str, posicion: int
) -> Channel:
    """Arma el `Channel` del derivado, resolviendo las tres decisiones de arriba.

    Raises:
        InvalidRecordingError: si las unidades no coinciden. Es lo que evita la
            resta sin sentido, que no falla sola.
    """
    if a.unit != b.unit:
        raise InvalidRecordingError(
            f"No se puede derivar «{a.name}» menos «{b.name}»: están en unidades "
            "distintas, así que la resta no significaría nada.",
            details=f"{a.name} en {a.unit!r} y {b.name} en {b.unit!r}.",
        )
    return Channel(
        name=nombre,
        kind=a.kind if a.kind is b.kind else ChannelKind.OTHER,
        unit=a.unit,
        index=posicion,
        original_sampling_rate=(
            a.original_sampling_rate
            if a.original_sampling_rate == b.original_sampling_rate
            else None
        ),
    )


def derive(
    recording: Recording,
    channel_a: str,
    channel_b: str,
    name: str | None = None,
) -> Recording:
    """Crea un canal derivado como la diferencia de dos canales.

    Args:
        name: nombre del canal nuevo. Si es None, se arma como "A-B".

    Returns:
        Un `Recording` nuevo con el canal derivado agregado al final.

    Raises:
        ChannelNotFoundError: si alguno de los dos canales no existe.
        DuplicateChannelError: si ya hay un canal con ese nombre.
        InvalidRecordingError: si los dos canales están en unidades distintas, o
            si lo que se pasa no es un registro.
    """
    _exigir_registro(recording)
    # `channel_by_name` es el que eleva `ChannelNotFoundError` con el mensaje
    # que ya nombra los canales disponibles: no hay que repetirlo acá.
    a = recording.channel_by_name(channel_a)
    b = recording.channel_by_name(channel_b)

    nombre = name if name is not None else f"{a.name}-{b.name}"
    if nombre in recording.channel_names():
        raise DuplicateChannelError(
            f"El registro ya tiene un canal llamado «{nombre}».",
            details=(
                "Si es la derivación que ya se hizo, no hace falta repetirla; si "
                "es otra, hay que darle un nombre distinto con `name`."
            ),
        )

    derivado = _canal_derivado(a, b, nombre, len(recording.channels))
    # `np.asarray` porque `data` puede llegar como vista de sólo lectura; la
    # resta produce un array nuevo, así que el original no se toca.
    with memoria_suficiente("derivar los canales"):
        fila = np.asarray(recording.data[a.index]) - np.asarray(recording.data[b.index])
        datos = np.vstack([recording.data, fila])

    return Recording(
        file_path=recording.file_path,
        channels=[*recording.channels, derivado],
        data=datos,
        sampling_rate=recording.sampling_rate,
        start_time=recording.start_time,
        metadata=dict(recording.metadata),
    )


def derive_montage(recording: Recording, pairs: list[tuple[str, str]]) -> Recording:
    """Aplica un montaje completo de una sola vez.

    Args:
        pairs: lista de pares (canal, referencia).

    Returns:
        Un `Recording` nuevo con un canal derivado por cada par, en ese orden.

    **Es atómico**: si un par falla —porque nombra un canal que no existe, o
    porque las unidades no coinciden— no se aplica ninguno. Un montaje a medias
    es peor que ninguno: el usuario vería algunos canales derivados y otros no,
    sin nada que le diga cuáles.

    Raises:
        ChannelNotFoundError, DuplicateChannelError, InvalidRecordingError: lo
            mismo que `derive()`, para el primer par que falle.
    """
    _exigir_registro(recording)
    if not isinstance(pairs, list):
        raise InvalidRecordingError(
            "El montaje tiene que ser una lista de pares (canal, referencia).",
            details=f"pairs es {type(pairs).__name__}, se esperaba list.",
        )

    # **Se acumulan las filas nuevas y se arma la matriz una sola vez.** Antes
    # esto encadenaba `derive()`, y cada llamada hacía su propio `np.vstack` de
    # la matriz entera: un montaje de N pares copiaba el registro N veces, cada
    # una un poco más grande. Sobre el registro real de 22 h, cuatro pares ya
    # costaban 3,1 copias —1399 MB—, y un montaje de veinte es lo normal.
    #
    # La atomicidad se conserva por la misma razón que antes: nada de esto toca
    # `recording`, y si un par eleva se descarta el acumulador. Y también se
    # conserva **poder derivar de una derivación anterior**, que es lo que hacía
    # el encadenado: `canales` crece a medida que se resuelven los pares, y
    # `_senal_de()` sabe si la fila está en el registro o entre las nuevas.
    originales = len(recording.channels)
    canales = list(recording.channels)
    filas: list[np.ndarray] = []

    def _senal_de(canal: Channel) -> np.ndarray:
        """La fila de un canal, venga del registro o de un derivado previo."""
        if canal.index < originales:
            return np.asarray(recording.data[canal.index])
        return filas[canal.index - originales]

    def _buscar(nombre: str) -> Channel:
        """Como `Recording.channel_by_name()`, pero también ve los derivados."""
        for canal in canales:
            if canal.name == nombre:
                return canal
        raise ChannelNotFoundError(
            f"El registro no tiene ningún canal llamado '{nombre}'.",
            details=f"Canales disponibles: {', '.join(c.name for c in canales)}.",
        )

    for par in pairs:
        if not isinstance(par, tuple) or len(par) != 2:
            raise InvalidRecordingError(
                "Cada entrada del montaje tiene que ser un par (canal, referencia).",
                details=f"se recibió {par!r}.",
            )
        a, b = _buscar(par[0]), _buscar(par[1])
        nombre = f"{a.name}-{b.name}"
        if any(canal.name == nombre for canal in canales):
            raise DuplicateChannelError(
                f"El registro ya tiene un canal llamado «{nombre}».",
                details=(
                    "Si es la derivación que ya se hizo, no hace falta repetirla; si "
                    "es otra, hay que darle un nombre distinto con `name`."
                ),
            )
        # `_canal_derivado` es el que rechaza las unidades distintas, así que se
        # lo llama **antes** de calcular la fila: si va a fallar, que falle sin
        # haber reservado memoria.
        derivado = _canal_derivado(a, b, nombre, len(canales))
        filas.append(_senal_de(a) - _senal_de(b))
        canales.append(derivado)

    with memoria_suficiente("derivar los canales"):
        datos = (
            np.vstack([recording.data, *filas])
            if filas
            else np.array(recording.data, dtype=float, copy=True)
        )
    return Recording(
        file_path=recording.file_path,
        channels=canales,
        data=datos,
        sampling_rate=recording.sampling_rate,
        start_time=recording.start_time,
        metadata=dict(recording.metadata),
    )
