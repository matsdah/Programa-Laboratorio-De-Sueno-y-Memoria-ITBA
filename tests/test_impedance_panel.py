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

from psglab.analysis.impedance import DEFAULT_LIMIT_KOHM  # noqa: E402
from psglab.ui.impedance_panel import (  # noqa: E402
    PASA,
    SIN_MEDIR,
    SUPERA,
    ImpedancePanel,
)


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


# -- La primera columna no se edita (hito 31) --------------------------------------


def se_edita(tabla, fila, columna: int) -> bool:
    from PySide6.QtWidgets import QAbstractItemView, QApplication

    tabla.editItem(fila, columna)
    QApplication.processEvents()
    editando = tabla.state() == QAbstractItemView.State.EditingState
    tabla.setFocus()
    QApplication.processEvents()
    return editando


def test_el_nombre_de_la_fila_no_se_edita(panel_cargado):
    """`QTreeWidgetItem` no tiene permisos por columna: marcar la fila editable
    dejaba cambiar también su nombre."""
    tabla = panel_cargado.tabla
    tabla.show()
    fila = tabla.topLevelItem(0)

    assert not se_edita(tabla, fila, 0)
    assert se_edita(tabla, fila, 1)


@pytest.fixture
def panel_cargado(panel: ImpedancePanel) -> ImpedancePanel:
    panel.set_channels(["C3", "C4"], {"C3": 5.0})
    return panel


# -- La columna de estado (hito 40) ------------------------------------------


def test_un_canal_bajo_el_limite_pasa(panel: ImpedancePanel):
    """El límite es el mismo con el que `impedance_report()` arma el informe,
    así que la columna y el informe no se pueden contradecir."""
    panel.set_channels(["C3"], {"C3": DEFAULT_LIMIT_KOHM - 1.0})

    assert panel.displayed_state("C3") == PASA


def test_exactamente_el_limite_pasa(panel: ImpedancePanel):
    """`channels_above_limit()` documenta que el límite es **inclusivo**: 5 kΩ
    con un límite de 5 kΩ pasa. El chip tiene que decir lo mismo."""
    panel.set_channels(["C3"], {"C3": DEFAULT_LIMIT_KOHM})

    assert panel.displayed_state("C3") == PASA


def test_por_encima_del_limite_supera(panel: ImpedancePanel):
    panel.set_channels(["C3"], {"C3": DEFAULT_LIMIT_KOHM + 0.1})

    assert panel.displayed_state("C3") == SUPERA


def test_un_canal_sin_medir_no_lleva_capsula(panel: ImpedancePanel):
    """Una cápsula gris parecería estar afirmando algo sobre una medición que
    no existe, que es lo que el módulo entero evita con «sin medir»."""
    panel.set_channels(["C3"], {})

    assert panel.displayed_state("C3") == SIN_MEDIR
    assert panel.state_color("C3") is None


def test_escribir_un_valor_cambia_su_estado(panel: ImpedancePanel):
    """El estado sale del valor y no se escribe: editar la celda lo rehace."""
    panel.set_channels(["C3"], {})
    panel.tabla.topLevelItem(0).setText(1, "12")

    assert panel.displayed_state("C3") == SUPERA


def test_el_encabezado_dice_cuantos_estan_medidos(panel: ImpedancePanel):
    """Es lo primero que se pregunta al abrir el panel."""
    panel.set_channels(["C3", "C4", "O1"], {"C3": 3.0})

    assert panel.header.caption() == "1 de 3 medidos"


def test_el_encabezado_dice_contra_que_limite(panel: ImpedancePanel):
    """Sin el límite a la vista, «supera» no dice a qué."""
    panel.set_channels(["C3"], {"C3": 3.0})

    assert "5" in panel.header.detail()


# -- La itálica de lo que nadie midió -----------------------------------------


def fila_de(panel: ImpedancePanel, canal: str):
    """La entrada de la tabla que le corresponde a un canal."""
    for numero in range(panel.tabla.topLevelItemCount()):
        entrada = panel.tabla.topLevelItem(numero)
        if entrada.text(0) == canal:
            return entrada
    raise AssertionError(f"no está el canal {canal}")


def test_un_canal_sin_medir_se_escribe_inclinado(panel: ImpedancePanel):
    """**La itálica dice «esto no lo midió nadie»** (hito 43).

    Hasta acá esa diferencia la cargaba el gris, que en este panel ya quiere
    decir otra cosa —«esto es secundario»—, y un valor ausente es lo contrario
    de secundario: es la advertencia más importante de la tabla.
    """
    panel.set_channels(["C3"], {})
    entrada = fila_de(panel, "C3")

    assert entrada.font(1).italic()
    assert entrada.font(2).italic()


def test_un_canal_medido_no_se_inclina(panel: ImpedancePanel):
    """La otra mitad, que es la que le da significado a la primera: si todo
    estuviera inclinado, la inclinación no diría nada."""
    panel.set_channels(["C3"], {"C3": 3.0})
    entrada = fila_de(panel, "C3")

    assert not entrada.font(1).italic()
    assert not entrada.font(2).italic()


def test_escribir_un_valor_endereza_la_fila(panel: ImpedancePanel):
    """Al medirse el canal la fila vuelve a la redonda. Sin esto, «sin medir»
    quedaría inclinado al lado de un número que sí se midió."""
    panel.set_channels(["C3"], {})
    escribir(panel, "C3", "3")

    assert not fila_de(panel, "C3").font(1).italic()
