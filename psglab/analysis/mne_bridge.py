"""El puente entre `Recording` y `mne.io.Raw`, en las dos direcciones.

**Por qué existe.** MNE ya trae filtrado, ICA y re-referenciado, y por eso se lo
eligió (`docs/ARQUITECTURA.md`). Pero hasta el hito 10 se lo usaba en **una sola
dirección**: los dos lectores hacen `Raw → Recording` al abrir un archivo, y el
viaje de vuelta no estaba escrito en ninguna parte. Sin él no hay
`filters.apply_filters()` ni nada de `ica.py`.

Se escribe una vez acá y no adentro de cada análisis, porque son tres los
módulos que lo necesitan y duplicarlo tres veces garantiza que las tres copias
se separen.

**El problema de la unidad, que es el que hace esto delicado.** MNE trabaja en
**volts** —`readers/edf.py` lo tiene medido contra el rango físico de la
cabecera y por eso convierte al leer— y el `Recording` trabaja en
**microvoltios**. El viaje de ida divide por un millón y el de vuelta
multiplica, pero **sólo los canales eléctricos**: un termómetro en grados o un
sensor de flujo sin unidad conservan la suya, y `Channel.unit` es la fuente de
verdad de cuál es. Escalar un canal de temperatura por un millón no da un error
visible: da una temperatura absurda que alguien va a interpretar como señal.

**Ida y vuelta tiene que devolver lo mismo.** Es la propiedad que hace confiable
todo lo que se apoye acá, y es lo que su test verifica primero.

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura de la Parte 2:
lo usan el filtrado, la ICA y el re-referenciado, que sí tienen los suyos.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import InvalidRecordingError
from psglab.utils.units import MICROVOLT, is_electrical

#: Unidad en la que MNE espera y entrega los canales de voltaje. El mismo valor
#: que `readers/edf.py` y `readers/brainvision.py` usan al leer; está repetido
#: acá y no importado de ellos porque `analysis/` no depende de `readers/`.
UNIDAD_DE_MNE: str = "V"

#: Cuántos microvoltios entran en un volt. Se escribe una vez.
_MICROVOLTIOS_POR_VOLT: float = 1e6

#: Qué tipo de canal declara MNE para cada clase nuestra. MNE usa el tipo para
#: decidir cosas —qué canales filtra por defecto, cuáles entran en una ICA—, así
#: que declararlos todos como "misc" haría que las funciones de MNE ignoraran
#: justo los canales que interesan.
_TIPOS_DE_MNE: dict[ChannelKind, str] = {
    ChannelKind.EEG: "eeg",
    ChannelKind.EOG: "eog",
    ChannelKind.EMG: "emg",
    ChannelKind.ECG: "ecg",
    ChannelKind.RESPIRATORY: "resp",
    ChannelKind.OTHER: "misc",
}


def _exigir_registro(valor: object, nombre: str) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`.

    Está separado porque lo usan las dos direcciones del puente, y porque el
    error que evita es el de siempre: un `AttributeError` crudo atraviesa el
    `except PsgLabError` de la ventana principal y termina como traza en la cara
    del investigador.
    """
    if not isinstance(valor, Recording):
        raise InvalidRecordingError(
            "No se puede analizar eso: no es un registro abierto.",
            details=f"{nombre} es {type(valor).__name__}, se esperaba Recording.",
        )


def _factor_hacia_mne(canal: Channel) -> float:
    """Por cuánto multiplicar los datos de un canal para dárselos a MNE.

    Uno para lo que no es eléctrico: MNE no le va a aplicar ninguna unidad y
    devolverlo escalado sería inventarle una magnitud.
    """
    return 1.0 / _MICROVOLTIOS_POR_VOLT if is_electrical(canal.unit) else 1.0


def to_raw(recording: Recording) -> Any:
    """Arma un `mne.io.RawArray` con los datos del registro.

    Los canales eléctricos se pasan a volts, que es lo que MNE espera; los
    demás van tal cual. El tipo de cada canal se declara según su
    `ChannelKind`, para que las funciones de MNE que filtran por tipo —la ICA
    entre ellas— vean lo que tienen que ver.

    Args:
        recording: el registro a convertir. **No se lo modifica**: los datos se
            copian antes de escalarlos.

    Returns:
        El objeto `Raw` de MNE, ya con los datos cargados.

    Raises:
        InvalidRecordingError: si lo que se le pasa no es un `Recording`. Sin la
            guarda salía un `AttributeError` sobre `.channels`, que la ventana
            principal **no atrapa**: sólo atrapa `PsgLabError`, así que le
            llegaba al investigador como traza de Python.

    **No valida que haya canales**, y no es un olvido: `Recording.__post_init__`
    rechaza un registro sin ninguno, así que acá no puede llegar uno vacío.
    Repetir la guarda sería código que nunca corre.
    """
    import mne

    _exigir_registro(recording, "recording")

    # **Copia explícita.** `Recording.data` puede llegar como vista de sólo
    # lectura —`get_segment()` pone `writeable = False`— y MNE escribe sobre el
    # buffer que recibe. Sin la copia, filtrar reventaría con un error de numpy
    # sobre un array de sólo lectura, tres capas más abajo.
    datos = np.array(recording.data, dtype=float, copy=True)
    for canal in recording.channels:
        datos[canal.index] *= _factor_hacia_mne(canal)

    info = mne.create_info(
        ch_names=[canal.name for canal in recording.channels],
        sfreq=recording.sampling_rate,
        ch_types=[_TIPOS_DE_MNE[canal.kind] for canal in recording.channels],
    )
    return mne.io.RawArray(datos, info, verbose="ERROR")


def from_raw(raw: Any, original: Recording) -> Recording:
    """Devuelve un `Recording` nuevo con los datos que salieron de MNE.

    **El original no se toca**, que es la regla 1 de esta carpeta: el usuario
    tiene que poder comparar la señal procesada con la cruda y volver atrás.

    Se conserva del original todo lo que MNE no sabe: la ruta del archivo, la
    hora de inicio, las clases de canal, las unidades y los metadatos. MNE
    devuelve volts y acá se vuelve a microvoltios, otra vez sólo para lo
    eléctrico.

    Args:
        raw: el `Raw` procesado.
        original: el registro del que salió, del que se toman los campos que
            MNE no lleva.

    Returns:
        Un registro nuevo, en las mismas unidades que el original.

    Raises:
        InvalidRecordingError: si `raw` trae canales que el original no tiene.
            Pasa si alguien re-referencia agregando un canal y espera que esta
            función lo adivine: no puede, porque no sabe de qué clase es ni en
            qué unidad viene.
    """
    _exigir_registro(original, "original")
    if not hasattr(raw, "ch_names") or not hasattr(raw, "get_data"):
        raise InvalidRecordingError(
            "Lo que devolvió el análisis no es una señal que se pueda leer.",
            details=(
                f"raw es {type(raw).__name__}; se esperaba un objeto de MNE con "
                "ch_names y get_data()."
            ),
        )

    nombres = list(raw.ch_names)
    conocidos = {canal.name: canal for canal in original.channels}
    desconocidos = [nombre for nombre in nombres if nombre not in conocidos]
    if desconocidos:
        raise InvalidRecordingError(
            "El análisis devolvió canales que no estaban en el registro, así que "
            "no se sabe de qué tipo son ni en qué unidad vienen.",
            details=f"canales nuevos: {desconocidos}",
        )

    datos = np.array(raw.get_data(), dtype=float, copy=True)
    canales: list[Channel] = []
    for posicion, nombre in enumerate(nombres):
        viejo = conocidos[nombre]
        if is_electrical(viejo.unit):
            datos[posicion] *= _MICROVOLTIOS_POR_VOLT
        canales.append(
            Channel(
                name=viejo.name,
                kind=viejo.kind,
                unit=viejo.unit,
                index=posicion,
                original_sampling_rate=viejo.original_sampling_rate,
            )
        )

    return Recording(
        file_path=original.file_path,
        channels=canales,
        data=datos,
        sampling_rate=float(raw.info["sfreq"]),
        start_time=original.start_time,
        metadata=dict(original.metadata),
    )


def unidad_de_salida(canal: Channel) -> str:
    """En qué unidad queda un canal después de pasar por MNE.

    Existe para que los análisis no tengan que volver a razonar la regla: los
    eléctricos vuelven a microvoltios y el resto conserva la suya.

    Raises:
        InvalidRecordingError: si no se le pasa un `Channel`.
    """
    if not isinstance(canal, Channel):
        raise InvalidRecordingError(
            "No se puede saber en qué unidad queda algo que no es un canal.",
            details=f"canal es {type(canal).__name__}, se esperaba Channel.",
        )
    return MICROVOLT if is_electrical(canal.unit) else canal.unit
