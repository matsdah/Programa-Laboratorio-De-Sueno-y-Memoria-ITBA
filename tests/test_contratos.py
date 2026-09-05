"""Que ningún método público escape del `except` de la interfaz.

`psglab/utils/errors.py` hace una promesa de la que cuelga todo el manejo de
errores del programa: la ventana principal atrapa **una sola clase**,
`PsgLabError`, y convierte lo que salga en un cartel legible. Cualquier
`AttributeError`, `TypeError` o `KeyError` crudo atraviesa ese `except` y el
investigador termina viendo una traza de Python.

Una auditoría encontró **seis caminos** que escapaban así, y todos tenían la
misma forma: la guarda funcionaba y el `raise` era el que explotaba al armar el
mensaje. `Scoring.set_stage(0, "N2")` daba `AttributeError: 'str' object has no
attribute 'value'` — el rechazo era correcto y la explicación del rechazo,
imposible.

Este archivo recorre cada método público de los módulos implementados con
entradas hostiles y afirma que lo que sale hereda de `PsgLabError`. La tabla es
explícita a propósito: un método nuevo sin fila hace fallar
`test_consistencia.py`, igual que pasa con `COBERTURA_DE_TESTS`.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.utils import units
from psglab.utils.errors import PsgLabError

#: Valores que nunca deberían llegar, y que llegan igual: un lector con un bug,
#: una cabecera que no trae el campo, un parser que se olvidó de convertir.
HOSTILES = (None, "texto", 3.5, [], {}, object())


def registro(canales: int = 2, muestras: int = 3000, fs: float = 100.0) -> Recording:
    """Un registro válido de una ventana, para partir de algo sano."""
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=[Channel(f"C{i}", ChannelKind.EEG, "µV", i) for i in range(canales)],
        data=np.zeros((canales, muestras)),
        sampling_rate=fs,
    )


def sesion() -> Session:
    return Session(registro(), Scoring(1, Nomenclature.AASM), AnnotationSet())


#: Cada fila es (nombre legible, función que recibe un valor hostil).
#:
#: **Al agregar un método público a un módulo implementado hay que agregar su
#: fila**, o `test_consistencia.py` hace fallar la suite.
CONTRATOS: dict[str, list[tuple[str, object]]] = {
    "psglab/core/recording.py": [
        ("Recording(data=...)", lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0)], v, 100.0)),
        ("Recording(sampling_rate=...)", lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0)], np.zeros((1, 10)), v)),
        ("Recording(channels=...)", lambda v: Recording(Path("x.edf"), v, np.zeros((1, 10)), 100.0)),
        ("Recording(file_path=...)", lambda v: Recording(v, [Channel("C0", ChannelKind.EEG, "µV", 0)], np.zeros((1, 10)), 100.0)),
        ("channel_by_name", lambda v: registro().channel_by_name(v)),
        ("channels_of_kind", lambda v: registro().channels_of_kind(v)),
        ("get_segment(channel_names=...)", lambda v: registro().get_segment(0, 10, [v])),
    ],
    "psglab/core/scoring.py": [
        ("Scoring(nomenclature=...)", lambda v: Scoring(3, v)),
        ("Scoring(n_windows=...)", lambda v: Scoring(v, Nomenclature.AASM)),
        ("set_stage(stage=...)", lambda v: Scoring(3, Nomenclature.AASM).set_stage(0, v)),
        ("set_arousal(arousal=...)", lambda v: Scoring(3, Nomenclature.AASM).set_arousal(0, v)),
        ("get", lambda v: Scoring(3, Nomenclature.AASM).get(v)),
    ],
    "psglab/core/annotations.py": [
        ("add(onset=...)", lambda v: AnnotationSet().add(Annotation("Arousal", v, 10))),
        ("add(duration=...)", lambda v: AnnotationSet().add(Annotation("Arousal", 0, v))),
        ("color_of", lambda v: AnnotationSet().color_of(v)),
        ("remove_at", lambda v: AnnotationSet().remove_at(v)),
    ],
    "psglab/core/session.py": [
        ("go_to_window", lambda v: sesion().go_to_window(v)),
        ("scale_uv", lambda v: sesion().scale_uv(v)),
        ("set_scale_uv(scale=...)", lambda v: sesion().set_scale_uv("C0", v)),
        ("set_visible_channels", lambda v: sesion().set_visible_channels([v])),
        ("set_selected_channels", lambda v: sesion().set_selected_channels([v])),
    ],
    "psglab/utils/units.py": [
        ("conversion_factor", lambda v: units.conversion_factor(v)),
        ("to_microvolts(unit=...)", lambda v: units.to_microvolts(1.0, v)),
    ],
}

CASOS = [
    (modulo, nombre, llamada, hostil)
    for modulo, filas in CONTRATOS.items()
    for nombre, llamada in filas
    for hostil in HOSTILES
]


@pytest.mark.parametrize(
    ("modulo", "nombre", "llamada", "hostil"),
    CASOS,
    ids=[f"{n}[{h!r}]" for _, n, _, h in CASOS],
)
def test_una_entrada_hostil_sale_como_error_del_programa(modulo, nombre, llamada, hostil):
    """Si el valor se rechaza, tiene que rechazarse con un `PsgLabError`.

    No se exige que **todo** valor hostil sea rechazado: algunos son legítimos
    para algunas firmas —un `3.5` de escala es un número finito y válido— y
    aceptarlos está bien. Lo que no está bien es rechazarlo con una traza.
    """
    try:
        llamada(hostil)
    except PsgLabError:
        pass
    except Exception as error:  # noqa: BLE001 - es justamente lo que se persigue
        pytest.fail(
            f"{nombre} con {hostil!r} elevó {type(error).__name__}, que no hereda de "
            f"PsgLabError y escaparía del except de la interfaz: {error}"
        )


def test_la_tabla_cubre_los_modulos_implementados():
    """Una fila que apunte a un módulo inexistente dejaría de proteger nada."""
    raiz = Path(__file__).resolve().parent.parent
    inexistentes = [m for m in CONTRATOS if not (raiz / m).exists()]
    assert not inexistentes, f"la tabla nombra módulos que no existen: {inexistentes}"
