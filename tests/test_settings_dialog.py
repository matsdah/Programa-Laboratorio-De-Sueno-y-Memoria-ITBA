"""Tests de la ventana de configuración.

Se miran las preferencias que la ventana **entrega**, no los píxeles. Que esas
preferencias lleguen a donde tienen efecto lo verifica `test_entrega.py`, por la
ventana principal.

Lo que más se cuida acá es una sola cosa: **mostrar no es elegir**. Abrir la
ventana, o reflejar en ella las preferencias vigentes, no puede avisar ningún
cambio; si lo hiciera, abrir la configuración volvería a aplicar todo.
"""

import json
from pathlib import Path

import pytest

pytest.importorskip("pyqtgraph")

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QColorDialog  # noqa: E402

from psglab.analysis.psd import DEFAULT_BANDS  # noqa: E402
from psglab.config import VIEW_TIMESCALE_PRESETS  # noqa: E402
from psglab.ui import fonts, theme  # noqa: E402
from psglab.ui.preferences import Preferences  # noqa: E402
from psglab.ui.settings_dialog import (  # noqa: E402
    TAB_TITLES,
    ColorButton,
    SettingsDialog,
)
from psglab.utils.errors import PsgLabError  # noqa: E402

CLASES = {"Arousal": "#4a90e6", "Spindle": "#6cb04a"}


@pytest.fixture
def cambios() -> list[Preferences]:
    return []


@pytest.fixture
def errores() -> list[PsgLabError]:
    return []


@pytest.fixture
def dialogo(qt_app, cambios: list[Preferences], errores: list[PsgLabError]):
    ventana = SettingsDialog(Preferences(), dict(CLASES))
    ventana.on_change = cambios.append
    ventana.on_error = errores.append
    yield ventana
    ventana.deleteLater()


#: El esquema con el que arranca el diálogo, que es el de fábrica. **Se pide
#: por `DEFAULT_SCHEME_NAME` y no por su nombre**: estos tests hablan del
#: esquema con que se abre la ventana de configuración, y escribirlo a mano los
#: hacía fallar el día que cambió —de «Claro» a «Sereno», en el rediseño de la
#: pantalla principal—.
DE_FABRICA = theme.scheme_by_name(theme.DEFAULT_SCHEME_NAME)


def ultima(cambios: list[Preferences]) -> Preferences:
    assert cambios, "la ventana no avisó ningún cambio"
    return cambios[-1]


# -- Qué solapas hay ------------------------------------------------------------


def test_tiene_las_cinco_solapas_con_contenido(dialogo: SettingsDialog):
    assert dialogo.tab_titles() == list(TAB_TITLES)


def test_no_tiene_las_solapas_que_no_configurarian_nada(dialogo: SettingsDialog):
    """**Decisión, no olvido.** No hay reglas ni conversión a milímetros: una
    solapa de cursores o de calibración sería una promesa sin cumplir."""
    assert "Cursores" not in dialogo.tab_titles()
    assert "Calibración" not in dialogo.tab_titles()


# -- Mostrar no es elegir ---------------------------------------------------------


def test_abrir_la_ventana_no_avisa_nada(dialogo: SettingsDialog, cambios):
    assert cambios == []


def test_reflejar_otras_preferencias_no_avisa_nada(dialogo: SettingsDialog, cambios):
    """Es lo que hace la ventana principal cada vez que la abre."""
    otras = (
        Preferences()
        .with_scheme(theme.NOCTURNO)
        .with_changes(psd_method="multitaper", psd_log_power=False, font_size=14)
        .with_bands({"Huso": (11.0, 16.0)})
        .with_annotation_color("Spindle", "#ff0000")
    )

    dialogo.set_preferences(otras)

    assert cambios == []
    assert dialogo.preferences == otras


def test_lo_reflejado_es_lo_que_se_muestra(dialogo: SettingsDialog):
    otras = Preferences().with_scheme(theme.NOCTURNO).with_changes(
        psd_method="multitaper"
    )

    dialogo.set_preferences(otras)

    assert dialogo.psd_method.currentData() == "multitaper"
    assert dialogo.preferences.scheme() is theme.NOCTURNO


def test_reflejar_algo_que_no_son_preferencias_avisa(dialogo: SettingsDialog):
    with pytest.raises(PsgLabError):
        dialogo.set_preferences({"font_size": 12})


# -- El botón de color ----------------------------------------------------------------


def test_el_boton_abre_el_selector_y_toma_lo_elegido(qt_app, monkeypatch):
    elegidos: list[str] = []
    boton = ColorButton("#000000")
    boton.on_chosen = elegidos.append
    monkeypatch.setattr(
        QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor("#ff8800"))
    )

    boton.click()

    assert elegidos == ["#ff8800"]
    assert boton.color() == "#ff8800"


def test_cancelar_el_selector_no_cambia_el_color(qt_app, monkeypatch):
    elegidos: list[str] = []
    boton = ColorButton("#000000")
    boton.on_chosen = elegidos.append
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor()))

    boton.click()

    assert elegidos == []
    assert boton.color() == "#000000"


def test_fijar_un_color_no_avisa(qt_app):
    elegidos: list[str] = []
    boton = ColorButton("#000000")
    boton.on_chosen = elegidos.append

    boton.set_color("#ffffff")

    assert elegidos == []


def test_un_color_que_no_se_puede_dibujar_se_ignora(qt_app):
    elegidos: list[str] = []
    boton = ColorButton("#000000")
    boton.on_chosen = elegidos.append

    boton.choose("naranja clarito")

    assert elegidos == []
    assert boton.color() == "#000000"


# -- Editor de anotaciones --------------------------------------------------------------


def test_muestra_las_clases_que_le_pasan_con_su_color(dialogo: SettingsDialog):
    assert set(dialogo.annotation_buttons) == set(CLASES)
    assert dialogo.annotation_buttons["Spindle"].color() == CLASES["Spindle"]


def test_elegir_el_color_de_una_clase(dialogo: SettingsDialog, cambios):
    dialogo.annotation_buttons["Arousal"].choose("#ff0000")

    assert ultima(cambios).annotation_color("Arousal") == "#ff0000"


def test_una_clase_con_color_guardado_aparece_aunque_no_se_la_pasen(
    dialogo: SettingsDialog,
):
    """Es la clase que el usuario definió en otro registro."""
    dialogo.set_preferences(Preferences().with_annotation_color("Apnea", "#00aa88"))

    assert dialogo.annotation_buttons["Apnea"].color() == "#00aa88"


def test_el_color_guardado_manda_sobre_el_de_la_sesion(dialogo: SettingsDialog):
    dialogo.set_preferences(Preferences().with_annotation_color("Spindle", "#111111"))

    assert dialogo.annotation_buttons["Spindle"].color() == "#111111"


# -- Espectro de potencia --------------------------------------------------------------


def test_elegir_el_metodo(dialogo: SettingsDialog, cambios):
    dialogo.psd_method.setCurrentIndex(dialogo.psd_method.findData("multitaper"))

    assert ultima(cambios).psd_method == "multitaper"


def test_apagar_el_eje_logaritmico(dialogo: SettingsDialog, cambios):
    dialogo.log_power.setChecked(False)

    assert ultima(cambios).psd_log_power is False


def test_arranca_con_las_bandas_convencionales(dialogo: SettingsDialog):
    nombres = [
        dialogo.bands_table.item(fila, 0).text()
        for fila in range(dialogo.bands_table.rowCount())
    ]
    assert nombres == list(DEFAULT_BANDS)


def _fila_de(dialogo: SettingsDialog, nombre: str) -> int:
    for fila in range(dialogo.bands_table.rowCount()):
        if dialogo.bands_table.item(fila, 0).text() == nombre:
            return fila
    raise AssertionError(f"no hay banda {nombre}")


def test_editar_una_banda_la_aplica(dialogo: SettingsDialog, cambios):
    fila = _fila_de(dialogo, "Sigma")

    dialogo.bands_table.item(fila, 2).setText("15")

    assert ultima(cambios).bands()["Sigma"] == (12.0, 15.0)
    assert dialogo.bands_notice.text() == ""


def test_se_acepta_la_coma_decimal(dialogo: SettingsDialog, cambios):
    """Es como lo escribe un investigador en español."""
    fila = _fila_de(dialogo, "Delta")

    dialogo.bands_table.item(fila, 1).setText("0,75")

    assert ultima(cambios).bands()["Delta"] == (0.75, 4.0)


def test_una_banda_invertida_no_se_aplica_y_se_explica(dialogo: SettingsDialog, cambios):
    """**No es un cartel**: se escribe en una tabla, y un diálogo modal por cada
    celda a medio escribir sería insoportable."""
    fila = _fila_de(dialogo, "Sigma")

    dialogo.bands_table.item(fila, 2).setText("10")

    assert cambios == []
    assert "Sigma" in dialogo.bands_notice.text()


def test_un_numero_que_no_se_entiende_no_se_aplica(dialogo: SettingsDialog, cambios):
    dialogo.bands_table.item(_fila_de(dialogo, "Beta"), 1).setText("dieciseis")

    assert cambios == []
    assert "Beta" in dialogo.bands_notice.text()


def test_dos_bandas_con_el_mismo_nombre_no_se_aplican(dialogo: SettingsDialog, cambios):
    dialogo.bands_table.item(_fila_de(dialogo, "Beta"), 0).setText("Alpha")

    assert cambios == []
    assert "Alpha" in dialogo.bands_notice.text()


def test_una_banda_sin_nombre_no_se_aplica(dialogo: SettingsDialog, cambios):
    dialogo.bands_table.item(_fila_de(dialogo, "Beta"), 0).setText("  ")

    assert cambios == []
    assert dialogo.bands_notice.text()


def test_corregir_la_banda_borra_la_explicacion(dialogo: SettingsDialog, cambios):
    fila = _fila_de(dialogo, "Sigma")
    dialogo.bands_table.item(fila, 2).setText("10")

    dialogo.bands_table.item(fila, 2).setText("17")

    assert ultima(cambios).bands()["Sigma"] == (12.0, 17.0)
    assert dialogo.bands_notice.text() == ""


def test_agregar_una_banda_la_deja_valida(dialogo: SettingsDialog, cambios):
    dialogo.add_band_button.click()

    bandas = ultima(cambios).bands()
    assert len(bandas) == len(DEFAULT_BANDS) + 1
    assert "Banda 1" in bandas


def test_quitar_una_banda(dialogo: SettingsDialog, cambios):
    dialogo.bands_table.setCurrentCell(_fila_de(dialogo, "Gamma"), 0)

    dialogo.remove_band_button.click()

    assert "Gamma" not in ultima(cambios).bands()


def test_siempre_queda_al_menos_una_banda(dialogo: SettingsDialog, cambios):
    dialogo.set_preferences(Preferences().with_bands({"Huso": (11.0, 16.0)}))

    assert not dialogo.remove_band_button.isEnabled()
    dialogo.remove_band()

    assert dialogo.bands_table.rowCount() == 1
    assert cambios == []


def test_volver_a_las_convencionales(dialogo: SettingsDialog, cambios):
    dialogo.set_preferences(Preferences().with_bands({"Huso": (11.0, 16.0)}))

    dialogo.restore_bands_button.click()

    assert ultima(cambios).psd_bands is None
    assert dialogo.bands_table.rowCount() == len(DEFAULT_BANDS)


# -- Otras --------------------------------------------------------------------------------


def test_ofrece_las_paginas_de_la_escala_de_tiempo(dialogo: SettingsDialog):
    ofrecidas = [dialogo.open_view.itemData(i) for i in range(dialogo.open_view.count())]
    assert ofrecidas == list(VIEW_TIMESCALE_PRESETS)


def test_elegir_la_pagina_al_abrir(dialogo: SettingsDialog, cambios):
    dialogo.open_view.setCurrentIndex(dialogo.open_view.findData(300.0))

    assert ultima(cambios).open_view_seconds == 300.0


def test_una_pagina_fuera_de_la_lista_se_muestra_igual(dialogo: SettingsDialog, cambios):
    """Elegir otra en silencio sería cambiar la preferencia sin que nadie lo
    pida."""
    dialogo.set_preferences(Preferences().with_changes(open_view_seconds=45.0))

    assert dialogo.open_view.currentData() == 45.0
    assert cambios == []


def test_elegir_la_nomenclatura_al_abrir(dialogo: SettingsDialog, cambios):
    dialogo.open_nomenclature.setCurrentIndex(dialogo.open_nomenclature.findData("RK"))

    assert ultima(cambios).open_nomenclature == "RK"


def test_la_nomenclatura_se_muestra_con_su_nombre_completo(dialogo: SettingsDialog):
    textos = [
        dialogo.open_nomenclature.itemText(i)
        for i in range(dialogo.open_nomenclature.count())
    ]
    assert "Rechtschaffen y Kales" in textos


def test_elegir_el_histograma_en_hora_real(dialogo: SettingsDialog, cambios):
    dialogo.open_clock_axis.setChecked(True)

    assert ultima(cambios).open_clock_axis is True


# -- Tipografía ------------------------------------------------------------------------


def test_no_se_elige_la_familia(dialogo: SettingsDialog):
    """**La solapa perdió la lista en el hito 43.** Ofrecía las ciento y pico
    de familias instaladas, así que las dos que el programa empaqueta eran un
    valor por omisión y no una garantía. Es el mismo argumento que dejó los
    colores en dos esquemas."""
    assert not hasattr(dialogo, "font_family")
    assert not hasattr(dialogo.preferences, "font_family")


def test_arranca_con_el_tamano_del_programa(dialogo: SettingsDialog):
    """Lo que sí se elige es el tamaño, que es lo que hace falta para ver de
    lejos. La casilla arranca tildada porque el tamaño de fábrica es el del
    sistema."""
    assert dialogo.system_font.isChecked()
    assert not dialogo.font_size.isEnabled()


def test_dejar_el_del_sistema_aplica_el_elegido(dialogo: SettingsDialog, cambios):
    dialogo.system_font.setChecked(True)
    cambios.clear()
    dialogo.font_size.setValue(15)
    assert cambios == [], "con el del sistema, tocar el tamaño no cambia nada"

    dialogo.system_font.setChecked(False)

    assert ultima(cambios).font_size == 15


def test_cambiar_el_tamano_con_una_tipografia_propia(dialogo: SettingsDialog, cambios):
    dialogo.system_font.setChecked(False)

    dialogo.font_size.setValue(20)

    assert ultima(cambios).font_size == 20


def test_volver_al_del_sistema(dialogo: SettingsDialog, cambios):
    dialogo.system_font.setChecked(False)

    dialogo.system_font.setChecked(True)

    assert ultima(cambios).font_size is None


def test_la_muestra_usa_el_tamano_elegido(dialogo: SettingsDialog):
    dialogo.system_font.setChecked(False)
    dialogo.font_size.setValue(22)

    assert dialogo.font_preview.font().pointSize() == 22


def test_la_muestra_lleva_las_tres_voces(dialogo: SettingsDialog):
    """**Con una sola, cambiar el tamaño no decía nada de la escala.** Son la
    de leer, la de medir y la de lo que nadie midió.

    Las tipografías se registran acá adentro: la suite no pasa por
    `create_application()`, que es quien lo hace al arrancar, y sin registrar
    `font_for()` deja la familia de la base —que es lo correcto: una familia
    que Qt no tiene no se pide—."""
    fonts.register_bundled_fonts()
    dialogo.system_font.setChecked(False)
    dialogo.font_size.setValue(14)

    assert dialogo.numeric_preview.font().family() == fonts.NUMERIC_FONT_FAMILY
    assert dialogo.absent_preview.font().italic()
    assert not dialogo.font_preview.font().italic()


# -- El panel de contexto (V3_F de la Übersicht) ---------------------------------


def test_elegir_las_ventanas_vecinas_por_separado(dialogo: SettingsDialog, cambios):
    """El pliego pide la cantidad configurable **y asimétrica**."""
    dialogo.overview_before.setValue(3)
    dialogo.overview_after.setValue(0)

    assert (ultima(cambios).overview_before, ultima(cambios).overview_after) == (3, 0)


def test_las_ventanas_vecinas_se_muestran_sin_avisar(dialogo: SettingsDialog, cambios):
    dialogo.set_preferences(Preferences().with_changes(overview_before=4, overview_after=2))

    assert (dialogo.overview_before.value(), dialogo.overview_after.value()) == (4, 2)
    assert cambios == []


def test_no_se_pueden_pedir_mas_vecinas_que_el_tope(dialogo: SettingsDialog):
    from psglab.ui.preferences import MAX_OVERVIEW_WINDOWS

    assert dialogo.overview_before.maximum() == MAX_OVERVIEW_WINDOWS
    assert dialogo.overview_after.minimum() == 0


# -- Los ajustes de las herramientas (hito 32) ------------------------------------


@pytest.mark.parametrize(
    "control, campo, valor",
    [
        ("amplitude_band", "amplitude_band_uv", 100.0),
        ("magnifier_radius", "magnifier_radius_seconds", 2.5),
        ("magnifier_zoom", "magnifier_zoom", 8.0),
    ],
)
def test_cada_ajuste_de_herramienta_se_aplica(
    dialogo: SettingsDialog, cambios, control: str, campo: str, valor: float
):
    getattr(dialogo, control).setValue(valor)

    assert getattr(ultima(cambios), campo) == pytest.approx(valor)


def test_los_ajustes_de_herramienta_se_muestran_sin_avisar(dialogo: SettingsDialog, cambios):
    dialogo.set_preferences(
        Preferences().with_changes(amplitude_band_uv=120.0, magnifier_zoom=6.0)
    )

    assert dialogo.amplitude_band.value() == 120.0
    assert dialogo.magnifier_zoom.value() == 6.0
    assert cambios == []
