"""Tests del panel de impedancias.

**El dibujo no se testea.** Lo que sí es la distinción que sostiene el módulo
entero y que este panel tiene que hacer visible: **"sin medir" no es "0 kΩ"**.

Un electrodo suelto que nadie midió es el caso peligroso, porque cero es el
mejor valor posible: si la celda vacía mostrara un cero, o quedara en blanco,
el canal pasaría por perfecto. Dice "sin medir" con todas las letras, y
`values()` no lo incluye.
"""

import pytest

pytest.importorskip("pyqtgraph")

from psglab.ui.impedance_panel import SIN_MEDIR, ImpedancePanel  # noqa: E402


@pytest.fixture
def panel(qt_app) -> ImpedancePanel:
    widget = ImpedancePanel()
    widget.resize(800, 400)
    return widget


def escribir(panel: ImpedancePanel, canal: str, texto: str) -> None:
    """Simula al usuario escribiendo en la celda de un canal."""
    for fila in range(panel.tabla.topLevelItemCount()):
        entrada = panel.tabla.topLevelItem(fila)
        if entrada.text(0) == canal:
            entrada.setText(1, texto)
            return
    raise AssertionError(f"no está el canal {canal}")


# -- La tabla ----------------------------------------------------------------


def test_arranca_vacio(panel: ImpedancePanel):
    assert panel.channels() == []
    assert panel.values() == {}


def test_arma_una_fila_por_canal(panel: ImpedancePanel):
    panel.set_channels(["C3", "C4", "O1"])

    assert panel.channels() == ["C3", "C4", "O1"]
    assert panel.tabla.topLevelItemCount() == 3


def test_respeta_el_orden_del_archivo(panel: ImpedancePanel):
    """No se ordenan alfabéticamente: el investigador los busca donde los vio
    en la pantalla de la señal."""
    panel.set_channels(["O1", "C3", "EMG-menton"])

    assert panel.channels() == ["O1", "C3", "EMG-menton"]


def test_muestra_los_valores_que_se_le_pasan(panel: ImpedancePanel):
    panel.set_channels(["C3", "C4"], {"C3": 4.2})

    assert panel.values() == {"C3": 4.2}


# -- "Sin medir" no es cero --------------------------------------------------


def test_un_canal_sin_valor_dice_sin_medir(panel: ImpedancePanel):
    """**Ni "0" ni en blanco.** Un cero pasaría por el mejor valor posible, y
    una celda vacía se lee como un olvido de la pantalla, no del electrodo."""
    panel.set_channels(["C3", "O1"], {"C3": 4.2})

    assert panel.displayed_value("O1") == SIN_MEDIR
    assert panel.displayed_value("O1") != "0"


def test_los_sin_medir_no_entran_en_los_valores(panel: ImpedancePanel):
    """Mismo contrato que `analysis.impedance.read_impedances()`: ponerlos en
    cero acá desharía todo el cuidado del módulo."""
    panel.set_channels(["C3", "O1"], {"C3": 4.2})

    assert panel.values() == {"C3": 4.2}
    assert panel.unmeasured() == ["O1"]


def test_un_cero_escrito_a_mano_si_cuenta(panel: ImpedancePanel):
    """La otra mitad: 0 kΩ es un valor legítimo y excelente. Lo que no vale es
    **inventarlo** donde no se midió."""
    panel.set_channels(["C3"])
    escribir(panel, "C3", "0")

    assert panel.values() == {"C3": 0.0}
    assert panel.unmeasured() == []


def test_borrar_todo_deja_los_canales_sin_medir(panel: ImpedancePanel):
    """No los saca de la tabla: el registro sigue teniendo esos canales."""
    panel.set_channels(["C3", "C4"], {"C3": 4.2, "C4": 3.8})
    panel.clear_all()

    assert panel.channels() == ["C3", "C4"]
    assert panel.values() == {}
    assert panel.unmeasured() == ["C3", "C4"]


# -- Escribir a mano, que es la tercera vía ----------------------------------


def test_lo_que_escribe_el_usuario_se_lee(panel: ImpedancePanel):
    panel.set_channels(["C3"])
    escribir(panel, "C3", "7.5")

    assert panel.values() == {"C3": 7.5}


def test_la_coma_decimal_tambien_entra(panel: ImpedancePanel):
    """El programa está en español y alguien va a escribir 7,5."""
    panel.set_channels(["C3"])
    escribir(panel, "C3", "7,5")

    assert panel.values() == {"C3": 7.5}


def test_lo_que_no_es_un_numero_se_descarta_sin_romper(panel: ImpedancePanel):
    """Es una celda de texto, no un formulario: elevar un error por cada tecla
    sería insufrible. La celda se corrige sola al recargar."""
    panel.set_channels(["C3", "C4"], {"C4": 3.8})
    escribir(panel, "C3", "cuatro coma dos")

    assert panel.values() == {"C4": 3.8}


def test_un_valor_negativo_se_descarta(panel: ImpedancePanel):
    """Una impedancia negativa no existe."""
    panel.set_channels(["C3"])
    escribir(panel, "C3", "-3")

    assert panel.values() == {}


def test_editar_avisa(panel: ImpedancePanel):
    """Es lo que dispara el recálculo del informe."""
    avisos: list[int] = []
    panel.on_changed = lambda: avisos.append(1)
    panel.set_channels(["C3"])

    escribir(panel, "C3", "4.2")

    assert avisos


def test_rellenar_la_tabla_no_avisa(panel: ImpedancePanel):
    """**El guard contra reentrada.** Sin él, cada carga se avisaría a sí misma
    como si el usuario hubiera escrito, y el informe se recalcularía una vez por
    canal. Es el mismo patrón que `channel_selector.py`."""
    avisos: list[int] = []
    panel.on_changed = lambda: avisos.append(1)

    panel.set_channels(["C3", "C4", "O1"], {"C3": 4.2, "C4": 3.8})

    assert avisos == []


# -- El informe --------------------------------------------------------------


def test_muestra_el_informe_que_se_le_da(panel: ImpedancePanel):
    panel.set_report("IMPEDANCIA\n\nTodo bien.\n")

    assert "Todo bien" in panel.report_text


def test_el_informe_es_de_solo_lectura(panel: ImpedancePanel):
    """Es una salida, no un campo: dejarlo editable invitaría a corregir a mano
    un número que se recalcula solo."""
    assert panel.informe.isReadOnly()
