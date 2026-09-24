"""Tests de la ayuda de atajos, como tabla agrupada (hito 54).

Era un `QMessageBox` con texto plano y las columnas se desalineaban. Lo que se
afirma es qué filas tiene y en qué grupo: los píxeles no.
"""

import pytest

pytest.importorskip("pyqtgraph")

from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.ui.shortcuts import shortcut_groups  # noqa: E402
from psglab.ui.shortcuts_dialog import ShortcutsDialog  # noqa: E402


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_la_tabla_tiene_una_fila_por_atajo(qt_app, nomenclatura):
    dialogo = ShortcutsDialog(nomenclatura)
    esperadas = [
        (grupo, accion, tecla)
        for grupo, filas in shortcut_groups(nomenclatura)
        for tecla, accion in filas
    ]

    assert dialogo.rows() == esperadas


def test_cada_grupo_lleva_su_rotulo_en_mayusculas(qt_app):
    """Como el de los paneles: escrito en mayúsculas, porque la hoja de estilo
    de Qt no sabe hacer `text-transform`."""
    dialogo = ShortcutsDialog(Nomenclature.AASM)
    rotulos = [
        dialogo.tabla.item(fila, 0).text()
        for fila in range(dialogo.tabla.rowCount())
        if dialogo.tabla.columnSpan(fila, 0) == 2
    ]

    assert rotulos == ["NAVEGACIÓN", "SCORING", "VISUALIZACIÓN", "ARCHIVO"]


def test_la_tecla_va_en_su_propia_columna(qt_app):
    """**Era el defecto**: en el texto plano, la tecla y lo que hace iban en la
    misma línea separadas por espacios, y se desalineaban."""
    dialogo = ShortcutsDialog(Nomenclature.AASM)

    teclas = [
        dialogo.tabla.item(fila, 1).text()
        for fila in range(dialogo.tabla.rowCount())
        if dialogo.tabla.item(fila, 1) is not None
    ]
    assert "Ctrl+O" in teclas
    assert "Espacio" in teclas


def test_el_titulo_es_el_de_la_ayuda(qt_app):
    assert ShortcutsDialog(Nomenclature.AASM).windowTitle() == "Atajos de teclado"
