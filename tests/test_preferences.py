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

import psglab.ui.fonts as fonts  # noqa: E402
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
    assert preferences.Preferences().scheme() is theme.SERENO


def test_un_archivo_que_no_existe_no_es_un_error(tmp_path: Path):
    """Es lo normal la primera vez que alguien abre el programa."""
    assert preferences.load(tmp_path / "todavia-no-existe.json") == preferences.Preferences()


# -- Guardar y volver a leer -------------------------------------------------


def test_lo_guardado_vuelve_igual(archivo: Path):
    preferences.save(preferences.Preferences().with_scheme(theme.NOCTURNO), archivo)

    assert preferences.load(archivo).scheme() == theme.NOCTURNO


def test_del_esquema_se_guarda_sólo_el_nombre(archivo: Path):
    """Así, mejorar los colores en una versión nueva alcanza a quien ya lo
    tenía elegido, en vez de dejarlo con la copia vieja. **Desde el hito 35 no
    hay otra cosa que guardar**: los esquemas no se editan."""
    preferences.save(preferences.Preferences().with_scheme(theme.NOCTURNO), archivo)

    guardado = json.loads(archivo.read_text(encoding="utf-8"))

    assert guardado["scheme_name"] == "Nocturno"
    assert "custom_scheme" not in guardado


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

    assert preferences.load(archivo).scheme() is theme.SERENO


def test_un_nombre_que_no_es_texto_cae_en_el_de_fabrica(archivo: Path):
    archivo.write_text(json.dumps({"scheme_name": 7}), encoding="utf-8")

    assert preferences.load(archivo).scheme() is theme.SERENO


def test_un_esquema_propio_de_un_archivo_viejo_se_ignora(archivo: Path):
    """**Era un error y ahora es una clave que sobra** (hito 35). Un archivo
    escrito antes trae el esquema que el usuario había editado a mano; los
    esquemas ya no se editan, así que se lee el nombre y lo demás se descarta
    en vez de impedir arrancar."""
    archivo.write_text(
        json.dumps({"scheme_name": "Propio", "custom_scheme": {"background": 3}}),
        encoding="utf-8",
    )

    assert preferences.load(archivo).scheme() is theme.SERENO


def test_los_errores_del_modulo_son_del_programa():
    assert issubclass(InvalidPreferencesError, PsgLabError)


#: Lo que un archivo editado a mano puede traer en cualquier campo: cada tipo de
#: JSON, y las formas casi correctas de una banda o de un esquema.
VALORES_HOSTILES: tuple[object, ...] = (
    [], {}, "x", "", 7, -3, 2.5, True, None,
    [[1]], [["Delta", 0.5]], [["a", 1, 2, 3]], [None], {"a": 1},
    {"background": [1]}, {"name": {}},
)

#: Todos los campos que `load()` lee del archivo.
CAMPOS_GUARDADOS: list[str] = sorted(set(preferences._LECTORES) | {"scheme_name"})


@pytest.mark.parametrize("campo", CAMPOS_GUARDADOS)
def test_ningun_valor_de_un_campo_impide_arrancar(archivo: Path, campo: str):
    """**Hito 33.** El arranque atrapa `PsgLabError` y nada más, en
    `create_application()` y en la ventana, así que `load()` sólo puede elevar
    eso. Una banda de dos números elevaba `IndexError` y **el programa no
    abría** hasta borrar a mano un archivo escondido en el perfil."""
    crudos = []
    for valor in VALORES_HOSTILES:
        archivo.write_text(json.dumps({campo: valor}), encoding="utf-8")
        try:
            preferences.load(archivo)
        except PsgLabError:
            pass
        except Exception as error:  # noqa: BLE001 - es lo que el test busca
            crudos.append(f"{valor!r} → {type(error).__name__}: {error}")

    assert not crudos, "\n".join(crudos)


def test_una_banda_de_dos_numeros_vuelve_a_las_de_fabrica_sin_llevarse_el_resto(
    archivo: Path,
):
    """El caso que encontró la auditoría del 19 de septiembre."""
    archivo.write_text(
        json.dumps({"psd_bands": [["Delta", 0.5]], "font_size": 14}), encoding="utf-8"
    )

    leidas = preferences.load(archivo)

    assert leidas.psd_bands is None
    assert leidas.font_size == 14


# -- Esquemas en archivos sueltos --------------------------------------------


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


# -- Lo que agregó la ventana de configuración -------------------------------------


def test_los_campos_nuevos_arrancan_en_su_valor_de_fabrica():
    """Sin haber tocado nada, el programa se comporta como antes de la ventana
    de configuración: página de 30 s, AASM, espectro de Welch en logarítmico."""
    valores = preferences.Preferences()

    # **Era `None` —la del sistema— hasta el hito 34.** Ahora arranca en la que
    # el programa empaqueta, que es la del diseño; quien prefiera otra la elige
    # en Configuración → Tipografía, y quien ya tenga preferencias guardadas
    # conserva la suya, porque el archivo siempre escribe este campo.
    assert valores.font_family == fonts.UI_FONT_FAMILY
    assert valores.psd_method == "welch"
    assert valores.psd_log_power is True
    assert valores.bands() == dict(preferences.DEFAULT_BANDS)
    assert valores.open_view_seconds == preferences.DEFAULT_VIEW_SECONDS
    assert valores.nomenclature().name == "AASM"


def test_todo_lo_de_la_configuracion_vuelve_igual(archivo: Path):
    """La ida y vuelta completa, con cada campo nuevo fuera de su valor de
    fábrica. Si uno no se guardara, este test lo encuentra."""
    elegidas = (
        preferences.Preferences()
        .with_changes(
            font_family="DejaVu Sans",
            font_size=13,
            psd_method="multitaper",
            psd_log_power=False,
            open_view_seconds=300.0,
            open_nomenclature="RK",
            open_clock_axis=True,
            overview_before=3,
            overview_after=0,
            amplitude_band_uv=100.0,
            magnifier_radius_seconds=2.5,
            magnifier_zoom=8.0,
        )
        .with_bands({"Lenta": (0.3, 1.0), "Huso": (11.0, 16.0)})
        .with_annotation_color("Spindle", "#ff8800")
    )

    preferences.save(elegidas, archivo)

    assert preferences.load(archivo) == elegidas


def test_las_bandas_convencionales_se_guardan_como_ninguna(archivo: Path):
    """Si una versión nueva corrige las bandas de fábrica, la corrección tiene
    que alcanzar a quien nunca las tocó."""
    valores = preferences.Preferences().with_bands(dict(preferences.DEFAULT_BANDS))

    assert valores.psd_bands is None


def test_una_banda_invertida_se_rechaza_al_construir():
    """La regla de qué banda es válida es la del análisis, no una copia."""
    with pytest.raises(InvalidPreferencesError, match="Sigma"):
        preferences.Preferences().with_bands({"Sigma": (16.0, 12.0)})


def test_dos_bandas_no_pueden_llamarse_igual():
    with pytest.raises(InvalidPreferencesError):
        preferences.Preferences().with_changes(
            psd_bands=(("Delta", 0.5, 4.0), ("Delta", 1.0, 3.0))
        )


def test_un_color_de_clase_que_no_se_puede_dibujar_se_rechaza():
    """Es el mismo error que un esquema con «gris oscuro»: aceptarlo acá
    termina en una traza al dibujar la anotación."""
    with pytest.raises(InvalidPreferencesError):
        preferences.Preferences().with_annotation_color("Spindle", "naranja clarito")


def test_cambiar_el_color_de_una_clase_reemplaza_el_anterior():
    valores = (
        preferences.Preferences()
        .with_annotation_color("Spindle", "#ff0000")
        .with_annotation_color("Spindle", "#00ff00")
    )

    assert valores.annotation_color("Spindle") == "#00ff00"
    assert len(valores.annotation_colors) == 1


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("font_size", 3),
        ("font_size", 200),
        ("font_size", True),
        ("font_family", ""),
        ("psd_method", "fourier"),
        ("psd_log_power", "si"),
        ("open_view_seconds", 0.0),
        ("open_view_seconds", float("nan")),
        ("open_nomenclature", "AASM 2007"),
        ("open_clock_axis", 1),
        ("overview_before", -1),
        ("overview_after", preferences.MAX_OVERVIEW_WINDOWS + 1),
        ("overview_before", 1.5),
        ("overview_after", True),
        ("amplitude_band_uv", 0.0),
        ("amplitude_band_uv", float("inf")),
        ("amplitude_band_uv", preferences.MAX_AMPLITUDE_BAND_UV + 1),
        ("magnifier_radius_seconds", 0.0),
        ("magnifier_zoom", 0.5),
        ("magnifier_zoom", "grande"),
    ],
)
def test_un_valor_que_no_se_puede_usar_se_rechaza(campo: str, valor: object):
    with pytest.raises(InvalidPreferencesError):
        preferences.Preferences().with_changes(**{campo: valor})


def test_cambiar_un_campo_que_no_existe_avisa():
    """Un error de tipeo en la ventana de configuración no puede crear un
    campo nuevo en silencio."""
    with pytest.raises(InvalidPreferencesError) as error:
        preferences.Preferences().with_changes(tamano_de_letra=12)

    # El nombre va en el detalle técnico, no en el mensaje para el investigador.
    assert "tamano_de_letra" in error.value.details


def test_un_campo_roto_no_arrastra_a_los_demas(archivo: Path):
    """**Perder la tipografía porque una banda quedó mal escrita sería
    desproporcionado.** Cada campo nuevo vuelve a su valor de fábrica por
    separado."""
    archivo.write_text(
        json.dumps(
            {
                "version": 1,
                "font_size": 14,
                "psd_bands": [["Sigma", 16.0, 12.0]],
                "open_view_seconds": "mucho",
                "annotation_colors": {"Spindle": "#123456"},
            }
        ),
        encoding="utf-8",
    )

    leidas = preferences.load(archivo)

    assert leidas.font_size == 14
    assert leidas.psd_bands is None
    assert leidas.open_view_seconds == preferences.DEFAULT_VIEW_SECONDS
    assert leidas.annotation_color("Spindle") == "#123456"


def test_un_archivo_de_la_version_anterior_sigue_cargando(archivo: Path):
    """Un archivo escrito antes de la ventana de configuración no tiene ninguno
    de los campos nuevos, y no por eso está roto."""
    archivo.write_text(json.dumps({"version": 1, "scheme_name": "Oscuro"}), encoding="utf-8")

    leidas = preferences.load(archivo)

    # **«Oscuro» es uno de los seis que se fueron en el hito 35**, así que el
    # nombre se conserva tal como estaba escrito y el esquema cae en el de
    # fábrica: quedarse sin colores no es motivo para no arrancar.
    assert leidas.scheme() is theme.SERENO
    assert leidas == preferences.Preferences(scheme_name="Oscuro")


# -- La disposición de paneles ya no se guarda (hito 24) -------------------------


def test_un_archivo_de_antes_con_disposicion_se_lee_igual(archivo: Path):
    """Los archivos anteriores al hito 24 traen `window_state`. Se ignora sin
    error: el programa abre siempre con la vista de fábrica."""
    archivo.write_text(
        json.dumps(
            {"version": 1, "scheme_name": "Oscuro", "window_state": "AAAA/wAAAAD9"}
        ),
        encoding="utf-8",
    )

    leidas = preferences.load(archivo)

    assert leidas.scheme() is theme.SERENO
    assert not hasattr(leidas, "window_state")


def test_la_disposicion_no_se_escribe(archivo: Path):
    preferences.save(preferences.Preferences(), archivo)

    assert "window_state" not in json.loads(archivo.read_text(encoding="utf-8"))


def test_la_ubersicht_arranca_con_los_vecinos_de_config():
    """Sin haber tocado nada, el contexto es el de siempre: una de cada lado."""
    from psglab.config import OVERVIEW_WINDOWS_AFTER, OVERVIEW_WINDOWS_BEFORE

    valores = preferences.Preferences()
    assert (valores.overview_before, valores.overview_after) == (
        OVERVIEW_WINDOWS_BEFORE,
        OVERVIEW_WINDOWS_AFTER,
    )


def test_las_herramientas_arrancan_con_sus_valores_de_siempre():
    """La banda, la del pliego; la lupa, la de la herramienta."""
    from psglab.config import AMPLITUDE_BAND_UV
    from psglab.tools.magnifier import RADIO_INICIAL_SEGUNDOS, ZOOM_INICIAL

    valores = preferences.Preferences()
    assert valores.amplitude_band_uv == AMPLITUDE_BAND_UV
    assert valores.magnifier_radius_seconds == RADIO_INICIAL_SEGUNDOS
    assert valores.magnifier_zoom == ZOOM_INICIAL
