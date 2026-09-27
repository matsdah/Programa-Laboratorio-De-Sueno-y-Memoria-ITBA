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

**El montaje de la AASM se arma de un clic** (`plan_aasm_montage()`): busca
en el registro los electrodos de cada derivación recomendada, con los nombres
que les dan los equipos, y deriva las que encuentra. Ahí la clase no sale de
la regla de arriba sino del montaje: «E1-M2» es un EOG aunque M2 sea un
electrodo de EEG, y así lo declara la AASM.

Cubre del pliego: sección "Derivar".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

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
    a: Channel,
    b: Channel,
    nombre: str,
    posicion: int,
    clase: ChannelKind | None = None,
) -> Channel:
    """Arma el `Channel` del derivado, resolviendo las tres decisiones de arriba.

    `clase` es la que declara el montaje, si la declara; si no, la regla de
    arriba.

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
        kind=clase if clase is not None else (a.kind if a.kind is b.kind else ChannelKind.OTHER),
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


def derive_montage(
    recording: Recording,
    pairs: list[tuple[str, str]],
    *,
    names: list[str] | None = None,
    channel_kinds: list[ChannelKind] | None = None,
) -> Recording:
    """Aplica un montaje completo de una sola vez.

    Es lo que hace «Montaje › Montaje AASM», con los pares que encuentra
    `plan_aasm_montage()`. Un script del laboratorio la puede llamar con los
    suyos.

    Args:
        pairs: lista de pares (canal, referencia).
        names: el nombre de cada derivado, en el orden de `pairs`. Si falta,
            «canal-referencia» con los nombres del archivo, que para
            «EEG C4-REF» menos «M1» sería «EEG C4-REF-M1»: el montaje AASM
            los nombra como la AASM.
        channel_kinds: la clase de cada derivado, en el orden de `pairs`. Si falta,
            la regla de `derive()`: la de los dos canales si coinciden.

    Returns:
        Un `Recording` nuevo con un canal derivado por cada par, en ese orden.

    **Es atómico**: si un par falla —porque nombra un canal que no existe, o
    porque las unidades no coinciden— no se aplica ninguno. Un montaje a medias
    es peor que ninguno: el usuario vería algunos canales derivados y otros no,
    sin nada que le diga cuáles.

    Raises:
        ChannelNotFoundError, DuplicateChannelError, InvalidRecordingError: lo
            mismo que `derive()`, para el primer par que falle; y
            `InvalidRecordingError` si `names` o `channel_kinds` no acompañan a
            `pairs` uno a uno.
    """
    _exigir_registro(recording)
    if not isinstance(pairs, list):
        raise InvalidRecordingError(
            "El montaje tiene que ser una lista de pares (canal, referencia).",
            details=f"pairs es {type(pairs).__name__}, se esperaba list.",
        )
    _exigir_uno_por_par(names, str, "names", "un nombre", len(pairs))
    _exigir_uno_por_par(channel_kinds, ChannelKind, "channel_kinds", "una clase", len(pairs))

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
            f"El registro no tiene ningún canal llamado «{nombre}».",
            details=f"Canales disponibles: {', '.join(c.name for c in canales)}.",
        )

    for i, par in enumerate(pairs):
        if not isinstance(par, tuple) or len(par) != 2:
            raise InvalidRecordingError(
                "Cada entrada del montaje tiene que ser un par (canal, referencia).",
                details=f"se recibió {par!r}.",
            )
        a, b = _buscar(par[0]), _buscar(par[1])
        nombre = names[i] if names is not None else f"{a.name}-{b.name}"
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
        derivado = _canal_derivado(
            a, b, nombre, len(canales), channel_kinds[i] if channel_kinds is not None else None
        )
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


def _exigir_uno_por_par(
    valores: object, tipo: type, campo: str, que: str, cuantos: int
) -> None:
    """Rechaza una lista de nombres o de clases que no acompañe a los pares.

    Una lista más corta dejaría derivados sin nombre, y una más larga diría
    que hay un par que no está: las dos son un montaje mal armado.
    """
    if valores is None:
        return
    if not isinstance(valores, list) or not all(isinstance(v, tipo) for v in valores):
        raise InvalidRecordingError(
            f"El montaje tiene que traer {que} por par.",
            details=f"{campo} es {valores!r}, se esperaba una lista de {tipo.__name__}.",
        )
    if len(valores) != cuantos:
        raise InvalidRecordingError(
            f"El montaje tiene que traer {que} por par.",
            details=f"{campo} trae {len(valores)} y hay {cuantos} pares.",
        )


# -- El montaje de la AASM ---------------------------------------------------

#: Las derivaciones del montaje recomendado por la AASM, como
#: (electrodo, referencia, clase). Las tres primeras son las recomendadas y las
#: tres siguientes su respaldo del otro hemisferio; se derivan todas las que el
#: registro permita, porque el respaldo es justamente para cuando un electrodo
#: se suelta a mitad de la noche. Los dos EOG van contra M2, como pide la AASM.
AASM_MONTAGE: Final[tuple[tuple[str, str, ChannelKind], ...]] = (
    ("F4", "M1", ChannelKind.EEG),
    ("C4", "M1", ChannelKind.EEG),
    ("O2", "M1", ChannelKind.EEG),
    ("F3", "M2", ChannelKind.EEG),
    ("C3", "M2", ChannelKind.EEG),
    ("O1", "M2", ChannelKind.EEG),
    ("E1", "M2", ChannelKind.EOG),
    ("E2", "M2", ChannelKind.EOG),
)

#: Con qué otros nombres graban los equipos el mismo electrodo, en orden de
#: preferencia. LOC y ROC son E1 y E2 con su nombre de antes. A1 y A2 son los
#: lóbulos de la oreja y **no** las mastoides: se usan sólo si no hay M1 ni M2,
#: y el derivado se llama con el que se usó, «C4-A1», para que el nombre no
#: diga una cosa que no se registró.
_EQUIVALENTES: Final[dict[str, tuple[str, ...]]] = {
    "E1": ("E1", "LOC"),
    "E2": ("E2", "ROC"),
    "M1": ("M1", "A1"),
    "M2": ("M2", "A2"),
}

#: Cómo se nombra el electrodo en el derivado. LOC es E1: mismo electrodo.
_NOMBRE_EN_EL_DERIVADO: Final[dict[str, str]] = {"LOC": "E1", "ROC": "E2"}

#: Palabras que los equipos le agregan al nombre del electrodo y que no lo
#: cambian: «EEG C4-REF» es el C4.
_ADORNOS: Final[frozenset[str]] = frozenset({"eeg", "eog", "ref"})


def _electrodos(nombre: str) -> tuple[str, ...]:
    """Los electrodos que nombra un canal, sin los adornos, en minúscula.

    «EEG C4-REF» da ("c4",), «C4-M1» da ("c4", "m1") y «Resp» da ("resp",).
    """
    return tuple(
        t for t in re.split(r"[^a-z0-9]+", nombre.lower()) if t and t not in _ADORNOS
    )


@dataclass(frozen=True)
class MontagePlan:
    """Qué derivaciones del montaje AASM se pueden armar con este registro.

    Attributes:
        pairs: los canales del archivo de cada derivación que se puede armar,
            como (canal, referencia), listos para `derive_montage()`.
        names: el nombre de cada una, como la nombra la AASM.
        channel_kinds: la clase de cada una.
        already_present: las que el registro ya trae derivadas.
        missing: las que no se pueden armar, con el electrodo que falta, como
            «O1-M2 (falta O1)».
    """

    pairs: list[tuple[str, str]]
    names: list[str]
    channel_kinds: list[ChannelKind]
    already_present: list[str]
    missing: list[str]


def plan_aasm_montage(recording: Recording) -> MontagePlan:
    """Busca en el registro las derivaciones del montaje AASM.

    No deriva nada: dice qué se puede derivar, qué ya está y qué falta, para
    que quien llama lo aplique con `derive_montage()` y le cuente al usuario
    lo que no se pudo. Un registro que no tiene ninguna no es un error: el
    plan vuelve vacío.

    Un canal es un electrodo si, sin los adornos, **su nombre es sólo ese
    electrodo**: «C4» y «EEG C4-REF» lo son, «C4-M1» no —es una derivación, y
    cuenta como ya presente—.
    """
    _exigir_registro(recording)
    por_electrodo: dict[str, str] = {}
    derivados: set[tuple[str, ...]] = set()
    for canal in recording.channels:
        partes = _electrodos(canal.name)
        if len(partes) == 1:
            por_electrodo.setdefault(partes[0], canal.name)
        elif len(partes) == 2:
            derivados.add(partes)

    def _buscar(electrodo: str) -> tuple[str, str] | None:
        """El canal del archivo y el nombre con que va en el derivado."""
        for alternativa in _EQUIVALENTES.get(electrodo, (electrodo,)):
            if alternativa.lower() in por_electrodo:
                return (
                    por_electrodo[alternativa.lower()],
                    _NOMBRE_EN_EL_DERIVADO.get(alternativa, alternativa),
                )
        return None

    plan = MontagePlan(pairs=[], names=[], channel_kinds=[], already_present=[], missing=[])
    for activo, referencia, clase in AASM_MONTAGE:
        encontrado_a, encontrado_b = _buscar(activo), _buscar(referencia)
        if encontrado_a is None or encontrado_b is None:
            faltan = [e for e, x in ((activo, encontrado_a), (referencia, encontrado_b)) if x is None]
            plan.missing.append(f"{activo}-{referencia} (falta {' y '.join(faltan)})")
            continue
        (canal_a, nombre_a), (canal_b, nombre_b) = encontrado_a, encontrado_b
        nombre = f"{nombre_a}-{nombre_b}"
        # Ya derivada con cualquiera de sus nombres: «E1-M2» o «LOC-M2».
        claves = {
            (nombre_a.lower(), nombre_b.lower()),
            (_electrodos(canal_a)[0], _electrodos(canal_b)[0]),
        }
        if claves & derivados or nombre in recording.channel_names():
            plan.already_present.append(nombre)
            continue
        plan.pairs.append((canal_a, canal_b))
        plan.names.append(nombre)
        plan.channel_kinds.append(clase)
    return plan
