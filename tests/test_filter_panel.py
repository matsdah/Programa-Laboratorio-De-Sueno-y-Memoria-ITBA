"""Tests del panel de filtros.

**El dibujo no se testea.** Lo que sí son las dos decisiones que el panel toma
y que se pueden afirmar sin mirar una pantalla:

- **Se ofrece por clase de canal**, que es lo que pide V1_F, y sólo de las
  clases que el registro tiene. Una fila de ECG en un registro sin ECG le pide
  al usuario que decida sobre algo que no existe.
- **La celda vacía desactiva el filtro**, y es la única forma. El cero está
  rechazado río abajo justamente para que no haya dos maneras de escribir lo
  mismo, una de las cuales MNE lee como "sin filtro".
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pyqtgraph")

from psglab.analysis.filters import (  # noqa: E402
    DEFAULT_FILTERS,
    FilterSettings,
    settings_for_kinds,
)
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.ui.filter_panel import FilterPanel  # noqa: E402
from psglab.utils.units import MICROVOLT  # noqa: E402


def registro(
    clases: list[tuple[str, ChannelKind]], fs: float = 256.0
) -> Recording:
    """Un registro con los canales pedidos y señal cualquiera."""
    return Recording(
        file_path=Path("filtros.edf"),
        channels=[
            Channel(nombre, clase, MICROVOLT, posicion)
            for posicion, (nombre, clase) in enumerate(clases)
        ],
        data=np.zeros((len(clases), 512)),
        sampling_rate=fs,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


@pytest.fixture
def panel(qt_app) -> FilterPanel:
    widget = FilterPanel()
    widget.resize(700, 300)
    return widget


def escribir(panel: FilterPanel, fila: int, columna: int, texto: str) -> None:
    """Simula al usuario escribiendo en una celda."""
    panel.tabla.topLevelItem(fila).setText(columna, texto)


# -- Una fila por clase presente ---------------------------------------------


def test_arranca_vacio(panel: FilterPanel):
    assert panel.kinds() == []
    assert panel.settings() == {}


def test_una_fila_por_clase_y_no_por_canal(panel: FilterPanel):
    """Es lo que pide V1_F, y lo que evita poner el mismo pasa-bajos veinte
    veces y equivocarse en uno solo sin notarlo."""
    panel.set_recording(
        registro([("C3", ChannelKind.EEG), ("C4", ChannelKind.EEG),
                  ("EOG-izq", ChannelKind.EOG)])
    )

    assert panel.kinds() == [ChannelKind.EEG, ChannelKind.EOG]
    assert panel.tabla.topLevelItemCount() == 2


def test_solo_las_clases_que_el_registro_tiene(panel: FilterPanel):
    """Ofrecer una fila de ECG en un registro sin ECG le pide al usuario que
    decida sobre algo que no existe."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    assert ChannelKind.ECG not in panel.kinds()
    assert panel.kinds() == [ChannelKind.EEG]


def test_respeta_el_orden_del_registro(panel: FilterPanel):
    """No se ordenan alfabéticamente, por lo mismo que la tabla de
    impedancias: el investigador las busca donde las vio."""
    panel.set_recording(
        registro([("EMG-menton", ChannelKind.EMG), ("C3", ChannelKind.EEG)])
    )

    assert panel.kinds() == [ChannelKind.EMG, ChannelKind.EEG]


# -- Los sugeridos -----------------------------------------------------------


def test_arranca_con_los_sugeridos(panel: FilterPanel):
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    assert panel.settings()[ChannelKind.EEG] == DEFAULT_FILTERS[ChannelKind.EEG]


def test_restaurar_sugeridos_deshace_lo_escrito(panel: FilterPanel):
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))
    escribir(panel, 0, 2, "12")

    panel.restore_defaults()

    assert panel.settings()[ChannelKind.EEG].lowpass_hz == 35.0


def test_editar_no_toca_los_sugeridos_del_programa(panel: FilterPanel):
    """La otra mitad de `default_for()` devolviendo una copia: si el panel
    editara la fila compartida, el próximo registro arrancaría con lo que
    alguien escribió para el anterior."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    escribir(panel, 0, 2, "12")

    assert DEFAULT_FILTERS[ChannelKind.EEG].lowpass_hz == 35.0


# -- La celda vacía desactiva -------------------------------------------------


def test_la_celda_vacia_desactiva_el_filtro(panel: FilterPanel):
    """**Y es la única forma.** El cero está rechazado río abajo para que no
    haya dos maneras de escribir lo mismo."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    escribir(panel, 0, 1, "")

    assert panel.settings()[ChannelKind.EEG].highpass_hz is None


def test_lo_que_escribe_el_usuario_se_lee(panel: FilterPanel):
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    escribir(panel, 0, 2, "12")

    assert panel.settings()[ChannelKind.EEG].lowpass_hz == 12.0


def test_la_coma_decimal_tambien_entra(panel: FilterPanel):
    """El programa está en español y alguien va a escribir 0,5."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    escribir(panel, 0, 1, "0,5")

    assert panel.settings()[ChannelKind.EEG].highpass_hz == 0.5


def test_los_sugeridos_se_muestran_con_coma(panel: FilterPanel):
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    assert panel.displayed_value(ChannelKind.EEG, "highpass_hz") == "0,3"


def test_lo_que_no_es_un_numero_se_descarta_sin_romper(panel: FilterPanel):
    """Es una celda de texto, no un formulario: elevar un error por cada tecla
    sería insufrible. La celda se corrige sola al recargar."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    escribir(panel, 0, 2, "treinta y cinco")

    assert panel.settings()[ChannelKind.EEG].lowpass_hz is None


def test_aplicar_avisa(panel: FilterPanel):
    """Es lo que dispara el filtrado. **Abrir el panel no filtra nada.**"""
    avisos: list[int] = []
    panel.on_apply = lambda: avisos.append(1)
    panel.set_recording(registro([("C3", ChannelKind.EEG)]))

    assert avisos == []

    panel.boton_aplicar.click()

    assert avisos == [1]


# -- Lo que el panel le entrega al módulo -------------------------------------


def test_lo_que_sale_del_panel_entra_en_el_modulo(panel: FilterPanel):
    """La costura: el panel habla por clase y `apply_filters()` por canal, y
    `settings_for_kinds()` es el que traduce."""
    grabacion = registro(
        [("C3", ChannelKind.EEG), ("C4", ChannelKind.EEG),
         ("EMG-menton", ChannelKind.EMG)]
    )
    panel.set_recording(grabacion)

    por_canal = settings_for_kinds(grabacion, panel.settings())

    assert set(por_canal) == {"C3", "C4", "EMG-menton"}
    assert por_canal["C3"] == DEFAULT_FILTERS[ChannelKind.EEG]
    assert por_canal["EMG-menton"] == DEFAULT_FILTERS[ChannelKind.EMG]


def test_una_clase_sin_ningun_filtro_no_estorba(panel: FilterPanel):
    """Vaciar las tres celdas de una clase la deja sin filtrar, y eso tiene que
    llegar así hasta el módulo."""
    grabacion = registro([("C3", ChannelKind.EEG)])
    panel.set_recording(grabacion)
    for columna in (1, 2, 3):
        escribir(panel, 0, columna, "")

    por_canal = settings_for_kinds(grabacion, panel.settings())

    assert por_canal["C3"] == FilterSettings()


# -- Los sugeridos, adaptados al registro (hallazgo del hito 17) --------------


def test_en_un_registro_de_100_hz_el_notch_viene_vacio(panel: FilterPanel):
    """La mitad que se ve del hallazgo: el panel no puede ofrecer un notch de
    50 Hz en un registro cuyo Nyquist es 50, porque apretar Aplicar sin tocar
    nada terminaría en un cartel de error."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)], fs=100.0))

    assert panel.displayed_value(ChannelKind.EEG, "notch_hz") == ""
    assert panel.settings()[ChannelKind.EEG].notch_hz is None


def test_lo_que_si_entra_se_sigue_ofreciendo(panel: FilterPanel):
    """No se vacía de más."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)], fs=100.0))

    assert panel.displayed_value(ChannelKind.EEG, "lowpass_hz") == "35"


def test_el_panel_dice_hasta_donde_llega_el_registro(panel: FilterPanel):
    """**Sin esto, una celda vacía por imposibilidad se lee igual que una que
    el usuario borró**: como un olvido de la pantalla y no del archivo. Es la
    misma distinción que el panel de impedancias hace con "sin medir"."""
    panel.set_recording(registro([("C3", ChannelKind.EEG)], fs=100.0))

    assert "100" in panel.rotulo.text()
    assert "50" in panel.rotulo.text()


def test_restaurar_sugeridos_respeta_la_frecuencia(panel: FilterPanel):
    """El botón vuelve a los sugeridos **de este registro**, no a los de la
    tabla: si no, restaurar volvería a poner el notch que no se puede aplicar.
    """
    panel.set_recording(registro([("C3", ChannelKind.EEG)], fs=100.0))
    escribir(panel, 0, 3, "50")

    panel.restore_defaults()

    assert panel.settings()[ChannelKind.EEG].notch_hz is None
