"""Tests de lo que los dos lectores hacen con lo que les devuelve MNE.

`readers/from_mne.py` juntó en el hito 79 tres cosas que `edf.py` y
`brainvision.py` tenían copiadas. `tests/test_readers.py` sigue leyendo
archivos sintéticos de los dos formatos de punta a punta; acá se miran las
piezas sin archivo, con filas armadas a mano, que es donde se ve la regla: qué
fila se convierte, desde qué unidad y cuál se queda como vino.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from psglab.core.recording import ChannelKind
from psglab.readers.from_mne import MNE_UNIT, build_channels, marks_of, microvolt_factor
from psglab.utils.units import MICROVOLT

#: Una tabla de grafías cualquiera, como la que le pasa cada lector.
DE_MNE = frozenset({"µV", "uV", "mV", "V"})


# -- microvolt_factor --------------------------------------------------------


def test_lo_que_mne_llevo_a_volts_se_pasa_de_volt_a_microvolt():
    """Aunque el archivo diga mV: MNE ya lo convirtió a volts."""
    assert MNE_UNIT == "V"
    assert microvolt_factor("mV", DE_MNE) == 1e6
    assert microvolt_factor("µV", DE_MNE) == 1e6


def test_lo_que_mne_dejo_como_venia_se_convierte_desde_su_unidad():
    """`uv` en minúscula: MNE no la reconoce, y la fila llega en microvoltios.

    Es el error del hito 33: multiplicarla de volt a microvolt la dejaba un
    millón de veces más grande.
    """
    assert microvolt_factor("uv", DE_MNE) == 1.0
    assert microvolt_factor("mv", DE_MNE) == 1000.0


def test_la_tabla_decide_y_no_la_unidad():
    """La misma grafía da otro factor si el formato no la convierte."""
    assert microvolt_factor("mV", frozenset({"V"})) == 1000.0


@pytest.mark.parametrize("unidad", ["DegC", "", "%", "MV"])
def test_lo_que_no_es_electrico_o_es_ambiguo_queda_como_vino(unidad):
    """«MV» puede ser mega o mili: no se adivina, y no impide abrir el registro."""
    assert microvolt_factor(unidad, DE_MNE) is None


# -- build_channels ----------------------------------------------------------


def test_los_canales_se_convierten_en_el_lugar_y_con_su_unidad():
    datos = np.array([[1e-6, 2e-6], [36.5, 36.6], [1.0, 2.0]])
    canales = build_channels(
        ["C3", "Temp", "EOG izq"],
        datos,
        units=["V", "DegC", "uv"],
        original_rates=[256.0, 1.0, 256.0],
        mne_volt_units=DE_MNE,
    )

    np.testing.assert_allclose(datos[0], [1.0, 2.0])
    np.testing.assert_allclose(datos[1], [36.5, 36.6])
    np.testing.assert_allclose(datos[2], [1.0, 2.0])
    assert [c.unit for c in canales] == [MICROVOLT, "DegC", MICROVOLT]
    assert [c.index for c in canales] == [0, 1, 2]
    assert [c.original_sampling_rate for c in canales] == [256.0, 1.0, 256.0]


def test_la_clase_se_deduce_con_la_unidad_ya_convertida():
    """Una grafía que MNE reconoce y la detección no —la mu de Shift-JIS— no
    puede dejar fuera del EEG a un canal que sí lo es."""
    shift_jis = "\x83\xcaV"
    canales = build_channels(
        ["C3", "Temp"],
        np.zeros((2, 3)),
        units=[shift_jis, "DegC"],
        original_rates=[100.0, 100.0],
        mne_volt_units=frozenset({shift_jis}),
    )
    assert canales[0].kind is ChannelKind.EEG
    assert canales[0].unit == MICROVOLT
    assert canales[1].kind is ChannelKind.OTHER


# -- marks_of ------------------------------------------------------------------


def test_las_marcas_quedan_como_comienzo_duracion_y_texto():
    crudo = SimpleNamespace(
        annotations=[
            {"onset": np.float64(1.5), "duration": 0, "description": "Estímulo"},
            {"onset": 30, "duration": np.float32(2.0), "description": np.str_("Arousal")},
        ]
    )
    marcas = marks_of(crudo)
    assert marcas == [(1.5, 0.0, "Estímulo"), (30.0, 2.0, "Arousal")]
    assert all(type(x) is float for m in marcas for x in m[:2])
    assert all(type(m[2]) is str for m in marcas)


def test_sin_marcas_la_lista_esta_vacia():
    assert marks_of(SimpleNamespace(annotations=[])) == []
