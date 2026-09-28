"""Lo que los lectores hacen con lo que les devuelve MNE, escrito una vez.

`edf.py` y `brainvision.py` leen con MNE y reciben lo mismo: filas de números,
cada una en volts o en la unidad del archivo según lo que MNE haya reconocido,
y las marcas del archivo en `raw.annotations`. Hasta el hito 79 cada lector
tenía su copia de las tres cosas que siguen, y eran iguales salvo la tabla de
grafías:

- **por cuánto multiplicar cada fila** para tenerla en µV (`microvolt_factor`);
- **el armado de los canales**, convirtiendo en el lugar (`build_channels`);
- **las marcas**, como las guarda `Recording.metadata` (`marks_of`).

**La tabla de grafías sigue siendo de cada lector.** MNE lleva a volts
distintas grafías según el formato —en EDF, la mu griega y la de Shift-JIS; en
BrainVision, `nV` y sólo el signo micro—, y comparándolas como él, con
mayúsculas y sin normalizar. Por eso cada lector le pasa la suya a
`microvolt_factor()`. Qué pasa si se usa la regla de `utils/units.py` en su
lugar está en el docstring de `edf.py`: un canal en `uv` quedaba 10⁶ veces más
grande (hito 33).

Cubre del pliego: ningún ID de funcionalidad. Es infraestructura de la
importación: la usan los dos lectores, que sí tienen los suyos.
"""

from collections.abc import Collection, Sequence
from typing import Any

import numpy as np

from psglab.core.recording import Channel
from psglab.readers.channel_types import detect_channel_kind
from psglab.utils.errors import UnknownUnitError
from psglab.utils.units import MICROVOLT, conversion_factor, is_electrical

#: Unidad en la que MNE entrega los canales que reconoce como eléctricos. No es
#: la que declara el archivo: es la del SI, que MNE usa internamente.
#: `readers/edf.py` lo tiene medido contra el rango físico de la cabecera.
MNE_UNIT = "V"


def microvolt_factor(unit: str, mne_volt_units: Collection[str]) -> float | None:
    """Por cuánto multiplicar la fila que entregó MNE para tenerla en µV.

    - Si MNE la llevó a volts —su grafía está en `mne_volt_units`—, de volt a
      microvolt.
    - Si no, y la unidad es eléctrica, desde la unidad del archivo.
    - Si no es eléctrica —una temperatura, un marcador sin unidad—, `None`: el
      canal queda en su escala, con su unidad.

    **Una unidad eléctrica ambigua también da `None`** —«MV», que puede ser
    mega o mili—: `conversion_factor()` se niega a adivinarla, y el canal queda
    como vino y con su unidad a la vista, en vez de impedir abrir el registro
    entero por uno solo.

    Args:
        unit: la unidad que declara el archivo para el canal, tal cual.
        mne_volt_units: las grafías que MNE lleva a volts en este formato,
            comparadas como él las compara.
    """
    if unit in mne_volt_units:
        return conversion_factor(MNE_UNIT)
    if not is_electrical(unit):
        return None
    try:
        return conversion_factor(unit)
    except UnknownUnitError:
        return None


def build_channels(
    names: Sequence[str],
    data: np.ndarray,
    units: Sequence[str],
    original_rates: Sequence[float],
    mne_volt_units: Collection[str],
) -> list[Channel]:
    """Los canales del registro, con las filas de `data` ya pasadas a µV.

    **Convierte en el lugar**: `data` sale modificada. `to_microvolts()`
    devolvería un array nuevo por canal, y sobre el registro de prueba eso
    eran 42 ms por canal en copias que se descartaban enseguida.

    La clase de cada canal se deduce de su unidad: es la que dice que un canal
    en grados no puede ser un EEG. **Si el canal se convirtió, la detección
    recibe µV** y no la grafía del archivo: MNE reconoce grafías —la mu de
    Shift-JIS— que la detección no, y el veto de la unidad dejaría fuera del
    EEG un canal que sí lo es.

    Args:
        names: los nombres, en el orden de las filas de `data`.
        data: la señal que devolvió MNE, una fila por canal.
        units: la unidad que declara el archivo para cada canal.
        original_rates: la frecuencia con que se grabó cada canal. En EDF
            puede no ser la del registro, porque MNE sobremuestrea.
        mne_volt_units: ver `microvolt_factor()`.
    """
    canales: list[Channel] = []
    for posicion, nombre in enumerate(names):
        unidad = units[posicion]
        factor = microvolt_factor(unidad, mne_volt_units)
        if factor is not None:
            data[posicion] *= factor
        canales.append(
            Channel(
                name=nombre,
                kind=detect_channel_kind(nombre, MICROVOLT if factor is not None else unidad),
                unit=MICROVOLT if factor is not None else unidad,
                index=posicion,
                original_sampling_rate=float(original_rates[posicion]),
            )
        )
    return canales


def marks_of(raw: Any) -> list[tuple[float, float, str]]:
    """Las marcas del archivo, como las guarda `Recording.metadata[MARKS_KEY]`.

    Comienzo y duración en segundos desde el inicio del registro, y el texto de
    la marca. Convertirlas en anotaciones es a pedido del usuario (hito 73):
    acá sólo se conservan.

    Args:
        raw: lo que devolvió `mne.io.read_raw_*`. Se usa sólo su
            `annotations`, así que no hace falta importar MNE para llamarla.
    """
    return [
        (float(marca["onset"]), float(marca["duration"]), str(marca["description"]))
        for marca in raw.annotations
    ]
