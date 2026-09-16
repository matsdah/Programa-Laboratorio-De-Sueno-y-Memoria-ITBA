"""Tests de lo que el programa recuerda entre una sesión y la siguiente.

Todo se escribe y se lee en `tmp_path`: **ningún test toca el archivo real del
usuario**. No es una formalidad —sería lo mismo que leer un registro de `data/`
desde un test— sino la diferencia entre una suite reproducible y una que pasa o
falla según quién la corra.

La decisión que más se testea acá es una sola: **un archivo roto no puede
impedir que el programa arranque**. Hay tres formas de estar roto —ausente,
ilegible, con basura adentro— y las tres tienen que terminar en el usuario
viendo el programa, no una traza.
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("pyqtgraph")

import psglab.ui.preferences as preferences  # noqa: E402
import psglab.ui.theme as theme  # noqa: E402
from psglab.utils.errors import (  # noqa: E402
    InvalidPreferencesError,
    PsgLabError,
    UnknownColorSchemeError,
)


@pytest.fixture
def archivo(tmp_path: Path) -> Path:
    return tmp_path / "preferencias.json"


# -- Los valores de fábrica --------------------------------------------------


def test_sin_haber_guardado_nada_se_usa_el_esquema_de_fabrica():
    assert preferences.Preferences().scheme() is theme.CLARO


def test_un_archivo_que_no_existe_no_es_un_error(tmp_path: Path):
    """Es lo normal la primera vez que alguien abre el programa."""
    assert preferences.load(tmp_path / "todavia-no-existe.json") == preferences.Preferences()


# -- Guardar y volver a leer -------------------------------------------------


def test_lo_guardado_vuelve_igual(archivo: Path):
    preferences.save(preferences.Preferences().with_scheme(theme.OSCURO), archivo)

    assert preferences.load(archivo).scheme() == theme.OSCURO


def test_de_un_esquema_de_fabrica_se_guarda_solo_el_nombre(archivo: Path):
    """Así, mejorar los colores de un esquema en una versión nueva alcanza a
    quien ya lo tenía elegido, en vez de dejarlo con la copia vieja."""
    preferences.save(preferences.Preferences().with_scheme(theme.ECG), archivo)

    guardado = json.loads(archivo.read_text(encoding="utf-8"))

    assert guardado["scheme_name"] == "ECG"
    assert "custom_scheme" not in guardado


def test_un_esquema_modificado_se_guarda_entero(archivo: Path):
    propio = theme.ColorScheme(**{**theme.scheme_to_dict(theme.OSCURO), "background": "#123456"})  # type: ignore[arg-type]
    preferences.save(preferences.Preferences().with_scheme(propio), archivo)

    assert preferences.load(archivo).scheme().background == "#123456"


def test_el_archivo_declara_su_version(archivo: Path):
    """Hoy no se lee para decidir nada. Existe para que una versión futura que
    cambie el formato pueda reconocer los archivos viejos en vez de adivinar."""
    preferences.save(preferences.Preferences(), archivo)

    assert json.loads(archivo.read_text(encoding="utf-8"))["version"] == preferences.FORMAT_VERSION


def test_guardar_crea_la_carpeta_si_no_esta(tmp_path: Path):
    destino = tmp_path / "ni" / "esta" / "carpeta" / "preferencias.json"

    preferences.save(preferences.Preferences(), destino)

    assert destino.exists()


def test_guardar_no_deja_el_archivo_temporal(archivo: Path):
    """Se escribe en un temporal y se reemplaza, para que apagar el programa en
    el momento justo no deje un JSON truncado."""
    preferences.save(preferences.Preferences(), archivo)

    assert list(archivo.parent.iterdir()) == [archivo]


def test_guardar_algo_que_no_son_preferencias_avisa(archivo: Path):
    with pytest.raises(InvalidPreferencesError):
        preferences.save({"scheme_name": "Oscuro"}, archivo)  # type: ignore[arg-type]


# -- Un archivo roto no puede impedir arrancar -------------------------------


def test_un_archivo_con_basura_avisa_en_vez_de_romper(archivo: Path):
    archivo.write_text("esto no es json", encoding="utf-8")

    with pytest.raises(InvalidPreferencesError):
        preferences.load(archivo)


def test_un_json_que_no_es_un_objeto_avisa(archivo: Path):
    archivo.write_text('["Oscuro"]', encoding="utf-8")

    with pytest.raises(InvalidPreferencesError):
        preferences.load(archivo)


def test_un_esquema_que_ya_no_existe_cae_en_el_de_fabrica(archivo: Path):
    """El nombre puede venir de otra versión del programa. Quedarse sin colores
    no es motivo para no arrancar, así que esto **no** eleva."""
    archivo.write_text(json.dumps({"scheme_name": "Fluorescente"}), encoding="utf-8")

    assert preferences.load(archivo).scheme() is theme.CLARO


def test_un_nombre_que_no_es_texto_cae_en_el_de_fabrica(archivo: Path):
    archivo.write_text(json.dumps({"scheme_name": 7}), encoding="utf-8")

    assert preferences.load(archivo).scheme() is theme.CLARO


def test_un_esquema_propio_ilegible_avisa(archivo: Path):
    archivo.write_text(
        json.dumps({"scheme_name": "Propio", "custom_scheme": {"background": 3}}),
        encoding="utf-8",
    )

    with pytest.raises(UnknownColorSchemeError):
        preferences.load(archivo)


def test_los_errores_del_modulo_son_del_programa():
    assert issubclass(InvalidPreferencesError, PsgLabError)


# -- Esquemas en archivos sueltos --------------------------------------------


def test_un_esquema_guardado_aparte_vuelve_igual(tmp_path: Path):
    """Es lo que permite que el laboratorio se pase un esquema por correo y que
    todas las máquinas se vean igual."""
    destino = tmp_path / "laboratorio.json"

    preferences.save_scheme(destino, theme.AZUL_SOBRE_GRIS)

    assert preferences.load_scheme(destino) == theme.AZUL_SOBRE_GRIS


def test_cargar_un_esquema_que_no_esta_avisa(tmp_path: Path):
    with pytest.raises(InvalidPreferencesError):
        preferences.load_scheme(tmp_path / "no-existe.json")


def test_cargar_un_esquema_con_basura_avisa(tmp_path: Path):
    destino = tmp_path / "roto.json"
    destino.write_text("{", encoding="utf-8")

    with pytest.raises(InvalidPreferencesError):
        preferences.load_scheme(destino)


# -- Dónde vive el archivo ---------------------------------------------------


def test_la_carpeta_sale_del_sistema(monkeypatch, tmp_path: Path):
    """En Windows es `%APPDATA%` y en el resto `$XDG_CONFIG_HOME`. Se resuelve a
    mano y no con `QStandardPaths` para no depender de Qt."""
    import os

    if os.name == "nt":
        monkeypatch.setenv("APPDATA", str(tmp_path))
    else:
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert preferences.config_dir() == tmp_path / preferences.APP_DIRNAME


def test_el_archivo_esta_dentro_de_esa_carpeta():
    assert preferences.preferences_path().parent == preferences.config_dir()
    assert preferences.preferences_path().name == preferences.FILENAME
