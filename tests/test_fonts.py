"""Tests de las tipografías que el programa trae consigo.

Lo que importa es que estén, que la licencia viaje con ellas, que el esquema que
las nombra nombre una que existe, y que **si faltan el programa arranque
igual**: una tipografía es una preferencia visual, no una dependencia.
"""

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

import psglab.ui.fonts as fonts  # noqa: E402
from psglab.ui import theme  # noqa: E402


def test_registra_las_dos_familias(qt_app):
    familias = fonts.register_bundled_fonts()

    assert "IBM Plex Sans" in familias
    assert "IBM Plex Mono" in familias


def test_registrar_dos_veces_no_las_vuelve_a_cargar(qt_app):
    """Qt no deduplica: el mismo archivo registrado dos veces se carga dos."""
    primera = fonts.register_bundled_fonts()
    cargados = dict(fonts._registradas)

    segunda = fonts.register_bundled_fonts()

    assert segunda == primera
    assert fonts._registradas == cargados


def test_la_tipografia_de_papel_es_una_que_el_programa_trae(qt_app):
    """Si el esquema nombrara una que no está, Qt usaría otra sin avisar."""
    assert theme.PAPEL.numeric_font in fonts.register_bundled_fonts()


def test_una_carpeta_que_no_existe_no_impide_arrancar(qt_app, tmp_path: Path):
    assert fonts.register_bundled_fonts(tmp_path / "no-existe") == []


def test_un_archivo_roto_se_saltea(qt_app, tmp_path: Path):
    (tmp_path / fonts.FONT_FILES[0]).write_bytes(b"esto no es una tipografia")

    assert fonts.register_bundled_fonts(tmp_path) == []


def test_estan_todos_los_archivos():
    faltan = [nombre for nombre in fonts.FONT_FILES if not (fonts.FONTS_DIR / nombre).is_file()]

    assert faltan == []


def test_la_licencia_viaja_con_los_archivos():
    """La OFL permite empaquetarlas con un programa MIT a condición de esto."""
    licencia = (fonts.FONTS_DIR / "OFL.txt").read_text(encoding="utf-8")

    assert "SIL OPEN FONT LICENSE Version 1.1" in licencia
