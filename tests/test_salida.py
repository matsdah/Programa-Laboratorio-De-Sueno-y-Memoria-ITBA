"""Tests de cómo termina el proceso de la suite (hito 80).

`conftest.py` termina con `os._exit()` en cuanto pytest informó, para que el
intérprete no desarme las ventanas de Qt que dejan los tests: en el CI eso
cayó con un `Segmentation fault` con todos los tests en verde. Lo que no se
puede perder al salir así es **el código de salida y el resumen**, que son lo
que lee el CI. Se verifica corriendo pytest en otro proceso, sobre un test que
pasa y otro que falla, con `conftest.py` cargado como plugin.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

CARPETA_DE_TESTS = Path(__file__).resolve().parent
RAIZ = CARPETA_DE_TESTS.parent


def correr(tmp_path: Path, cuerpo: str) -> subprocess.CompletedProcess[str]:
    """Corre pytest sobre un archivo con ese cuerpo, con el `conftest.py` de la suite."""
    archivo = tmp_path / "test_de_la_salida.py"
    archivo.write_text(cuerpo, encoding="utf-8")
    entorno = dict(os.environ)
    entorno["PYTHONPATH"] = os.pathsep.join([str(RAIZ), str(CARPETA_DE_TESTS)])
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(archivo), "-p", "conftest", "-q",
         "-p", "no:cacheprovider", "--rootdir", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=entorno,
        timeout=120,
    )


def test_una_suite_en_verde_sale_con_cero_y_lo_dice(tmp_path: Path):
    resultado = correr(tmp_path, "def test_pasa():\n    assert True\n")

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "1 passed" in resultado.stdout


def test_una_suite_con_un_fallo_sale_con_uno_y_lo_dice(tmp_path: Path):
    """El caso que importa: saliendo antes, el fallo no se puede perder."""
    resultado = correr(tmp_path, "def test_falla():\n    assert False\n")

    assert resultado.returncode == pytest.ExitCode.TESTS_FAILED, resultado.stdout
    assert "1 failed" in resultado.stdout


def test_con_qt_abierto_tambien_sale_con_el_codigo_de_la_sesion(tmp_path: Path):
    """Con una ventana armada y sin cerrar, que es lo que deja la suite."""
    resultado = correr(
        tmp_path,
        "from PySide6.QtWidgets import QWidget\n\n"
        "def test_deja_una_ventana(qt_app):\n"
        "    ventana = QWidget()\n"
        "    ventana.show()\n"
        "    assert ventana.isVisible()\n",
    )

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "1 passed" in resultado.stdout
