"""Tests de la presentación de los canales, sin sesión alrededor.

`ChannelDisplay` salió de `Session` en el hito 79, y `tests/test_session.py`
sigue verificando todo lo que la interfaz le pide a la sesión, que ahora
delega. Lo que queda para acá es lo que la sesión no deja ver: que el
despliegue **mide sobre el tramo que se le pasa y no sobre otro**, que no sabe
de épocas, y cómo reparte lo que sobrevive a un registro procesado.

La señal es sintética y armada a mano para cada caso, con el resultado sabido
de antemano: un escalón de 0 a 100 µV tiene media 0 en su primera mitad y 100
en la segunda.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.config import (
    AMPLITUDE_STEP_FACTOR,
    DEFAULT_SCALE_BY_KIND_UV,
    DEFAULT_SCALE_UV,
    MAX_SCALE_UV,
    MIN_SCALE_UV,
)
from psglab.core.channel_display import ChannelDisplay
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidRecordingError,
    InvalidScaleError,
)

FS = 100.0
MUESTRAS = 1000


def registro(clases: dict[str, ChannelKind], datos: np.ndarray | None = None) -> Recording:
    """Un registro con esos canales, en ese orden, en cero si no se dan datos."""
    if datos is None:
        datos = np.zeros((len(clases), MUESTRAS))
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=[
            Channel(nombre, clase, "µV", i) for i, (nombre, clase) in enumerate(clases.items())
        ],
        data=datos,
        sampling_rate=FS,
    )


def escalon(bajo: float = 0.0, alto: float = 100.0) -> np.ndarray:
    """Una fila que vale `bajo` en su primera mitad y `alto` en la segunda."""
    fila = np.full(MUESTRAS, bajo)
    fila[MUESTRAS // 2 :] = alto
    return fila


@pytest.fixture
def tres() -> ChannelDisplay:
    """C3 y C4 de EEG y un EOG, en cero."""
    return ChannelDisplay(
        registro({"C3": ChannelKind.EEG, "C4": ChannelKind.EEG, "EOG": ChannelKind.EOG})
    )


# -- Cómo arranca -----------------------------------------------------------


def test_arranca_con_todos_visibles_en_orden_y_ninguno_seleccionado(tres):
    assert tres.visible_channels == ["C3", "C4", "EOG"]
    assert tres.selected_channels == []


def test_cada_canal_arranca_con_la_escala_de_su_clase_y_sin_desplazamiento(tres):
    assert tres.scale_uv("C3") == DEFAULT_SCALE_BY_KIND_UV["EEG"]
    assert tres.scale_uv("EOG") == DEFAULT_SCALE_BY_KIND_UV["EOG"]
    assert tres.offset_uv("C3") == 0.0


def test_una_clase_sin_escala_propia_no_se_mide_al_construir():
    """Medir necesita un tramo, y al construir nadie dijo cuál se va a ver."""
    datos = np.vstack([np.full(MUESTRAS, 5000.0)])
    despliegue = ChannelDisplay(registro({"Flujo": ChannelKind.RESPIRATORY}, datos), 40.0)
    assert despliegue.scale_uv("Flujo") == 40.0
    assert despliegue.offset_uv("Flujo") == 0.0


def test_la_escala_de_fabrica_se_recorta_a_los_limites():
    despliegue = ChannelDisplay(registro({"Pos": ChannelKind.OTHER}), 0.0)
    assert despliegue.scale_uv("Pos") == MIN_SCALE_UV
    despliegue = ChannelDisplay(registro({"Pos": ChannelKind.OTHER}), 1e9)
    assert despliegue.scale_uv("Pos") == MAX_SCALE_UV


def test_las_listas_que_devuelve_son_copias(tres):
    tres.visible_channels.append("inventado")
    tres.selected_channels.append("inventado")
    assert tres.visible_channels == ["C3", "C4", "EOG"]
    assert tres.selected_channels == []


# -- El alcance de la amplitud ----------------------------------------------


def test_sin_seleccion_la_amplitud_llega_a_todos_los_visibles(tres):
    tres.set_visible_channels(["C3", "EOG"])
    tres.increase_amplitude()
    assert tres.scale_uv("C3") == pytest.approx(DEFAULT_SCALE_BY_KIND_UV["EEG"] / AMPLITUDE_STEP_FACTOR)
    assert tres.scale_uv("C4") == DEFAULT_SCALE_BY_KIND_UV["EEG"]


def test_con_seleccion_la_amplitud_llega_solo_a_los_seleccionados(tres):
    tres.set_selected_channels(["C4"])
    tres.set_amplitude_scale(20.0)
    assert tres.scale_uv("C4") == 20.0
    assert tres.scale_uv("C3") == DEFAULT_SCALE_BY_KIND_UV["EEG"]


def test_un_canal_visible_dos_veces_recibe_el_paso_una_sola_vez(tres):
    tres.set_visible_channels(["C3", "C3"])
    tres.decrease_amplitude()
    assert tres.scale_uv("C3") == pytest.approx(DEFAULT_SCALE_BY_KIND_UV["EEG"] * AMPLITUDE_STEP_FACTOR)


def test_offset_a_cero_respeta_el_alcance(tres):
    tres.set_offset_uv("C3", 30.0)
    tres.set_offset_uv("C4", 30.0)
    tres.set_selected_channels(["C3"])
    tres.reset_offsets()
    assert tres.offset_uv("C3") == 0.0
    assert tres.offset_uv("C4") == 30.0


# -- Lo que se mide sobre un tramo ------------------------------------------


def test_centrar_mide_solo_el_tramo_que_se_le_pasa():
    despliegue = ChannelDisplay(registro({"C3": ChannelKind.EEG}, np.vstack([escalon()])))
    despliegue.center_offsets(0, MUESTRAS // 2)
    assert despliegue.offset_uv("C3") == pytest.approx(0.0)
    despliegue.center_offsets(MUESTRAS // 2, MUESTRAS)
    assert despliegue.offset_uv("C3") == pytest.approx(100.0)


def test_ajustar_al_panel_mide_el_tramo_despues_de_restar_el_desplazamiento():
    despliegue = ChannelDisplay(registro({"C3": ChannelKind.EEG}, np.vstack([escalon(90.0, 110.0)])))
    despliegue.set_offset_uv("C3", 100.0)
    despliegue.fit_to_pane(0, MUESTRAS)
    assert despliegue.scale_uv("C3") == pytest.approx(10.0)


def test_un_canal_plano_no_cambia_de_escala_al_ajustar(tres):
    tres.fit_to_pane(0, MUESTRAS)
    assert tres.scale_uv("C3") == DEFAULT_SCALE_BY_KIND_UV["EEG"]


def test_las_muestras_sin_valor_no_cuentan_al_medir():
    fila = np.full(MUESTRAS, 50.0)
    fila[::7] = np.nan
    despliegue = ChannelDisplay(registro({"C3": ChannelKind.EEG}, np.vstack([fila])))
    despliegue.center_offsets(0, MUESTRAS)
    assert despliegue.offset_uv("C3") == pytest.approx(50.0)


def test_un_tramo_despues_del_final_no_toca_nada(tres):
    """Es la última época corta: `window_to_samples` la da más allá del final."""
    tres.center_offsets(MUESTRAS + 10, MUESTRAS + 20)
    tres.fit_to_pane(MUESTRAS + 10, MUESTRAS + 20)
    assert tres.offset_uv("C3") == 0.0
    assert tres.scale_uv("C3") == DEFAULT_SCALE_BY_KIND_UV["EEG"]


def test_un_tramo_que_empieza_antes_del_registro_se_rechaza(tres):
    with pytest.raises(InvalidRecordingError):
        tres.center_offsets(-10, 10)


# -- Las clases sin escala propia -------------------------------------------


def test_una_clase_sin_escala_propia_se_centra_y_se_mide_sobre_el_tramo():
    """Una temperatura de 37 °C que varía una décima: se centra antes de medir."""
    datos = np.vstack([escalon(36_950.0, 37_050.0)])
    despliegue = ChannelDisplay(registro({"Temp": ChannelKind.OTHER}, datos))
    despliegue.fit_unscaled_kinds(["Temp"], 0, MUESTRAS)
    assert despliegue.offset_uv("Temp") == pytest.approx(37_000.0)
    assert despliegue.scale_uv("Temp") == pytest.approx(50.0)


def test_medir_las_clases_sin_escala_saltea_las_que_tienen_una():
    datos = np.vstack([escalon(0.0, 400.0), escalon(0.0, 400.0)])
    despliegue = ChannelDisplay(
        registro({"C3": ChannelKind.EEG, "Flujo": ChannelKind.RESPIRATORY}, datos)
    )
    despliegue.fit_unscaled_kinds(["C3", "Flujo"], 0, MUESTRAS)
    assert despliegue.scale_uv("C3") == DEFAULT_SCALE_BY_KIND_UV["EEG"]
    assert despliegue.offset_uv("C3") == 0.0
    assert despliegue.scale_uv("Flujo") == pytest.approx(200.0)


def test_medir_las_clases_sin_escala_no_mira_la_seleccion():
    """Al abrir no hay selección que respetar: se miden los que se nombran."""
    datos = np.vstack([escalon(0.0, 400.0), escalon(0.0, 400.0)])
    despliegue = ChannelDisplay(
        registro({"Flujo": ChannelKind.RESPIRATORY, "Pos": ChannelKind.OTHER}, datos)
    )
    despliegue.set_selected_channels(["Pos"])
    despliegue.fit_unscaled_kinds(["Flujo"], 0, MUESTRAS)
    assert despliegue.scale_uv("Flujo") == pytest.approx(200.0)
    assert despliegue.offset_uv("Pos") == 0.0


def test_medir_un_canal_que_no_existe_no_toca_ninguno():
    datos = np.vstack([escalon(0.0, 400.0)])
    despliegue = ChannelDisplay(registro({"Flujo": ChannelKind.RESPIRATORY}, datos))
    with pytest.raises(ChannelNotFoundError):
        despliegue.fit_unscaled_kinds(["Flujo", "inventado"], 0, MUESTRAS)
    assert despliegue.offset_uv("Flujo") == 0.0


# -- Un registro procesado --------------------------------------------------


def test_al_reemplazar_el_registro_se_conserva_lo_que_sobrevive(tres):
    tres.set_visible_channels(["EOG", "C3"])
    tres.set_selected_channels(["C3", "C4"])
    tres.set_scale_uv("C3", 42.0)
    tres.set_offset_uv("C3", 7.0)
    nuevo = registro({"C3": ChannelKind.EEG, "EOG": ChannelKind.EOG, "C3-A2": ChannelKind.EEG})

    nuevos = tres.replace_recording(nuevo)

    assert nuevos == ["C3-A2"]
    assert tres.visible_channels == ["EOG", "C3"]
    assert tres.selected_channels == ["C3"]
    assert tres.scale_uv("C3") == 42.0
    assert tres.offset_uv("C3") == 7.0


def test_un_canal_nuevo_arranca_con_la_escala_de_su_clase(tres):
    tres.replace_recording(
        registro({"C3": ChannelKind.EEG, "EOG-D": ChannelKind.EOG, "Flujo": ChannelKind.RESPIRATORY})
    )
    assert tres.scale_uv("EOG-D") == DEFAULT_SCALE_BY_KIND_UV["EOG"]
    assert tres.scale_uv("Flujo") == DEFAULT_SCALE_UV
    assert tres.offset_uv("EOG-D") == 0.0


def test_si_no_sobrevive_ningun_visible_se_muestran_todos(tres):
    tres.set_visible_channels(["C4"])
    tres.replace_recording(registro({"F3": ChannelKind.EEG, "F4": ChannelKind.EEG}))
    assert tres.visible_channels == ["F3", "F4"]


def test_despues_de_reemplazar_se_mide_sobre_el_registro_nuevo(tres):
    nuevo = registro({"C3": ChannelKind.EEG}, np.vstack([np.full(MUESTRAS, 80.0)]))
    tres.replace_recording(nuevo)
    tres.center_offsets(0, MUESTRAS)
    assert tres.offset_uv("C3") == pytest.approx(80.0)
    with pytest.raises(ChannelNotFoundError):
        tres.scale_uv("C4")


def test_reemplazar_con_algo_que_no_es_un_registro_no_toca_nada(tres):
    tres.set_visible_channels(["C4"])
    with pytest.raises(InvalidRecordingError):
        tres.replace_recording("sintetico.edf")
    assert tres.visible_channels == ["C4"]


def test_una_escala_de_fabrica_que_no_es_un_numero_se_rechaza():
    with pytest.raises(InvalidScaleError):
        ChannelDisplay(registro({"C3": ChannelKind.EEG}), float("nan"))
