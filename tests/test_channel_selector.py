"""Tests del selector de canales.

**No tenía test propio** y figuraba en `SIN_TEST_PROPIO` mientras era un árbol
con casillas: lo único suyo era reflejar el registro, y `test_entrega.py` lo
recorría desde la ventana. Dejó de alcanzar cuando el árbol pasó a ser una
lista con chips y un pie de atajos por clase: el pie tiene estado propio —un
botón marcado quiere decir "esta clase se ve entera"— y ese estado se puede
desincronizar de las casillas sin que nada falle a la vista.

Lo que se verifica es eso y las dos listas que el panel publica. El chip no:
es dibujo, y lo que se puede afirmar de él es de qué color sale, que se
pregunta sin pintarlo.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.ui import theme
from psglab.ui.channel_selector import ChannelSelector, color_de_la_clase

FRECUENCIA = 100.0


@pytest.fixture
def registro() -> Recording:
    """Cuatro canales de tres clases: dos EEG, un EOG y un EMG."""
    clases = (ChannelKind.EEG, ChannelKind.EEG, ChannelKind.EOG, ChannelKind.EMG)
    nombres = ("C3", "C4", "EOG-izq", "EMG-menton")
    return Recording(
        file_path=Path("noche.edf"),
        channels=[
            Channel(nombre, clase, "µV", posicion)
            for posicion, (nombre, clase) in enumerate(zip(nombres, clases))
        ],
        data=np.zeros((4, int(FRECUENCIA * 30))),
        sampling_rate=FRECUENCIA,
    )


@pytest.fixture
def selector(qt_app, registro: Recording) -> ChannelSelector:
    """Un selector con ese registro ya cargado."""
    panel = ChannelSelector()
    panel.set_recording(registro)
    return panel


class theme_puesto:
    """Deja un esquema puesto mientras dura el bloque y devuelve el anterior.

    `theme.current()` es estado global del módulo, así que un test que lo
    cambie y no lo devuelva rompe a los que corran después, y sólo cuando
    corren en ese orden.
    """

    def __init__(self, esquema: theme.ColorScheme) -> None:
        self._esquema = esquema
        self._anterior: theme.ColorScheme | None = None

    def __enter__(self) -> theme.ColorScheme:
        self._anterior = theme.current()
        theme.set_current(self._esquema)
        return self._esquema

    def __exit__(self, *_: object) -> None:
        if self._anterior is not None:
            theme.set_current(self._anterior)


# -- La lista -----------------------------------------------------------------


def test_los_canales_salen_en_el_orden_del_archivo(selector: ChannelSelector):
    """No alfabético ni por clase: es el orden que el equipo grabó, el que el
    investigador reconoce y el mismo con el que el visualizador los apila."""
    assert selector.visible_channels() == ["C3", "C4", "EOG-izq", "EMG-menton"]


def test_todos_arrancan_visibles(selector: ChannelSelector, registro: Recording):
    assert selector.visible_channels() == registro.channel_names()


def test_destildar_uno_lo_saca_de_los_visibles(selector: ChannelSelector):
    selector.set_visible(["C3", "EOG-izq"])

    assert selector.visible_channels() == ["C3", "EOG-izq"]


def test_los_visibles_conservan_el_orden_del_archivo(selector: ChannelSelector):
    """Se pidan en el orden que se pidan."""
    selector.set_visible(["EMG-menton", "C3"])

    assert selector.visible_channels() == ["C3", "EMG-menton"]


# -- El atajo por clase (V3_P) ------------------------------------------------


def test_ocultar_una_clase_oculta_todos_sus_canales(selector: ChannelSelector):
    """El pliego lo pide con esas palabras: decidir si visualizar o no los
    canales de EOG y EMG, sin marcarlos uno por uno."""
    selector.toggle_kind(ChannelKind.EEG, False)

    assert selector.visible_channels() == ["EOG-izq", "EMG-menton"]


def test_volver_a_mostrar_una_clase_la_trae_entera(selector: ChannelSelector):
    selector.toggle_kind(ChannelKind.EEG, False)
    selector.toggle_kind(ChannelKind.EEG, True)

    assert selector.visible_channels() == ["C3", "C4", "EOG-izq", "EMG-menton"]


def test_ocultar_una_clase_avisa(selector: ChannelSelector):
    """La ventana se entera por la señal, no repreguntando."""
    avisos: list[list[str]] = []
    selector.visible_changed.connect(avisos.append)

    selector.toggle_kind(ChannelKind.EOG, False)

    assert avisos == [["C3", "C4", "EMG-menton"]]


def test_solo_hay_atajo_para_las_clases_que_el_registro_trae(
    selector: ChannelSelector,
):
    """Un botón «ECG» en un registro sin ECG sería un control que no hace
    nada."""
    assert set(selector._atajos) == {ChannelKind.EEG, ChannelKind.EOG, ChannelKind.EMG}


def test_destildar_un_canal_apaga_el_atajo_de_su_clase(selector: ChannelSelector):
    """**El estado del pie se puede desincronizar y no se nota.** Si el botón
    siguiera marcado con medio EEG a la vista, el próximo clic ocultaría la
    clase en vez de completarla, que es lo contrario de lo que espera quien lo
    aprieta."""
    selector.set_visible(["C3", "EOG-izq", "EMG-menton"])

    assert not selector._atajos[ChannelKind.EEG].isChecked()
    assert selector._atajos[ChannelKind.EOG].isChecked()


def test_mostrar_todo_los_trae_a_todos(selector: ChannelSelector):
    selector.toggle_kind(ChannelKind.EEG, False)
    selector.toggle_kind(ChannelKind.EOG, False)

    selector._mostrar_todo()

    assert selector.visible_channels() == ["C3", "C4", "EOG-izq", "EMG-menton"]


def test_al_cargar_otro_registro_los_atajos_se_rehacen(
    selector: ChannelSelector, registro: Recording
):
    """Quedarse con los de antes dejaría un botón de una clase que el registro
    nuevo no tiene."""
    solo_eeg = Recording(
        file_path=Path("otra.edf"),
        channels=[Channel("Fz", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, int(FRECUENCIA * 30))),
        sampling_rate=FRECUENCIA,
    )

    selector.set_recording(solo_eeg)

    assert set(selector._atajos) == {ChannelKind.EEG}


# -- La selección, que es otro eje --------------------------------------------


def test_la_seleccion_arranca_vacia(selector: ChannelSelector):
    """`Session` no exige que lo seleccionado esté visible, y el pliego tampoco
    los ata: son dos ejes independientes."""
    assert selector.selected_channels() == []


def test_lo_seleccionado_sale_en_orden_del_archivo(selector: ChannelSelector):
    selector._lista.item(3).setSelected(True)
    selector._lista.item(1).setSelected(True)

    assert selector.selected_channels() == ["C4", "EMG-menton"]


# -- El chip ------------------------------------------------------------------


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=lambda e: e.name)
def test_cada_clase_tiene_su_color(qt_app, esquema: theme.ColorScheme):
    """Dos clases con el mismo color harían del chip una decoración. Se cumple
    porque la paleta de los dos esquemas tiene al menos tantos colores como
    clases; una paleta más corta las haría repetir."""
    with theme_puesto(esquema):
        colores = {color_de_la_clase(clase) for clase in ChannelKind}

    assert len(colores) == len(list(ChannelKind))


def test_el_color_del_chip_sale_del_esquema(qt_app):
    """Y no de una tabla propia, que sería otro juego de colores que mantener
    en los dos esquemas y verificar contra WCAG por separado."""
    esperado = theme.SERENO.color_for_channel(list(ChannelKind).index(ChannelKind.EEG))

    with theme_puesto(theme.SERENO):
        assert color_de_la_clase(ChannelKind.EEG) == esperado
