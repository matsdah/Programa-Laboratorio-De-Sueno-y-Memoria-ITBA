"""Tests del panel de scoring.

Hasta el hito 26 el panel no tenía test propio y figuraba en `SIN_TEST_PROPIO`:
lo que hacía se verificaba a través de la ventana, en `test_entrega.py`, y su
ancho mínimo en `test_docks.py`, que es donde sigue. Lo que trajo el hito es el
pie con la ventana y su fase, y eso se afirma mejor acá, sin armar una ventana.

Lo que importa del pie es que diga lo mismo que el resto del programa —la
ventana en base 1, la fase con su rótulo— y que **reflejar no sea elegir**: el
panel se actualiza en cada navegación, y si al hacerlo emitiera, navegar
volvería a scorear.
"""

import pytest

pytest.importorskip("PySide6")

from psglab.core.nomenclature import (  # noqa: E402
    Nomenclature,
    SleepStage,
    stage_label,
)
from psglab.ui.scoring_panel import (  # noqa: E402
    ALTO_DEL_BOTON,
    SIN_SCOREAR,
    ScoringPanel,
    status_text,
)
from psglab.ui.panel_header import SIN_REGISTRO  # noqa: E402
from psglab.ui.shortcuts import key_for_stage  # noqa: E402


@pytest.fixture
def panel(qt_app) -> ScoringPanel:
    return ScoringPanel()


# -- El texto del pie ---------------------------------------------------------


def test_el_pie_muestra_la_ventana_en_base_uno():
    assert status_text(136, SleepStage.S2, False) == "Ventana 137 · S2"


def test_una_ventana_sin_scorear_lo_dice_en_palabras():
    """El «-» con que se guarda no se lee como nada en un texto suelto."""
    assert status_text(0, SleepStage.UNSCORED, False) == "Ventana 1 · sin scorear"


def test_el_arousal_se_suma_al_final():
    assert status_text(9, SleepStage.REM, True) == "Ventana 10 · REM · arousal"


def test_el_arousal_sin_fase_tambien_se_muestra():
    """El arousal es independiente de la fase, y el pie no lo esconde."""
    assert status_text(4, SleepStage.UNSCORED, True) == "Ventana 5 · sin scorear · arousal"


@pytest.mark.parametrize("fase", [SleepStage.N1, SleepStage.N2, SleepStage.N3, SleepStage.R])
def test_las_fases_de_aasm_llevan_su_rotulo(fase: SleepStage):
    assert status_text(0, fase, False) == f"Ventana 1 · {fase.value}"


# -- El panel -----------------------------------------------------------------


def test_antes_de_abrir_un_registro_el_pie_lo_dice(panel: ScoringPanel):
    assert panel.status() == SIN_REGISTRO


def test_reflejar_la_ventana_actualiza_el_pie(panel: ScoringPanel):
    panel.set_current(SleepStage.N2, False, 136)

    assert panel.status() == "Ventana 137 · N2"


def test_reflejar_no_emite_ni_la_fase_ni_el_arousal(panel: ScoringPanel):
    emitidas: list[object] = []
    panel.stage_selected.connect(emitidas.append)
    panel.arousal_toggled.connect(emitidas.append)

    panel.set_current(SleepStage.N3, True, 4)

    assert emitidas == []


def test_reflejar_marca_el_boton_de_la_fase(panel: ScoringPanel):
    panel.set_current(SleepStage.R, False, 0)

    marcados = [fase for fase, boton in panel._botones.items() if boton.isChecked()]
    assert marcados == [SleepStage.R]


def test_cambiar_de_nomenclatura_no_borra_el_pie(panel: ScoringPanel):
    panel.set_current(SleepStage.N2, False, 136)

    panel.set_nomenclature(Nomenclature.RK)

    assert panel.status() == "Ventana 137 · N2"


def test_las_fases_van_en_su_propia_fila(panel: ScoringPanel):
    """Separadas del selector y del arousal: es lo que baja el mínimo del panel
    al de la fila más ancha."""
    panel.set_nomenclature(Nomenclature.RK)

    en_la_fila = [panel._fila.itemAt(i).widget() for i in range(panel._fila.count())]

    assert en_la_fila == list(panel._botones.values())
    assert panel._nomenclaturas not in en_la_fila
    assert panel._arousal not in en_la_fila


# -- El botón de fase (hito 34) ----------------------------------------------


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_cada_boton_muestra_su_tecla(panel: ScoringPanel, nomenclatura: Nomenclature):
    """La tecla existía desde el principio y no se veía en ningún lado: quien
    no leía la ayuda scoreaba la noche entera a golpe de mouse."""
    panel.set_nomenclature(nomenclatura)

    for fase, boton in panel._botones.items():
        lineas = boton.text().splitlines()
        assert lineas[0] == stage_label(fase)
        assert lineas[-1] == key_for_stage(fase)


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_si_la_tecla_es_la_etiqueta_se_escribe_una_vez(
    panel: ScoringPanel, nomenclatura: Nomenclature
):
    """**Hasta el hito 51 el botón de W decía «W» sobre «W»**, y el de R lo
    mismo: la tecla es la inicial de la etiqueta, que ahí es la etiqueta
    entera. Donde difieren —«N2» y «2»— siguen las dos líneas."""
    panel.set_nomenclature(nomenclatura)

    for fase, boton in panel._botones.items():
        repetida = key_for_stage(fase).casefold() == stage_label(fase).casefold()
        assert len(boton.text().splitlines()) == (1 if repetida else 2)


def test_la_tecla_no_se_escribe_en_el_panel(panel: ScoringPanel):
    """Sale de `shortcuts`, que es el único lugar que dice qué tecla hace qué:
    escribirla al lado del control es como se desincronizan."""
    panel.set_nomenclature(Nomenclature.AASM)

    assert panel._botones[SleepStage.N2].text().endswith(
        key_for_stage(SleepStage.N2)
    )


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_cada_boton_declara_su_fase(panel: ScoringPanel, nomenclatura: Nomenclature):
    """Es lo que le deja a la hoja de estilo pintarlo con el color de su fase
    sin que el panel conozca ningún color."""
    panel.set_nomenclature(nomenclatura)

    for fase, boton in panel._botones.items():
        assert boton.property("fase") == fase.value


def test_los_botones_de_fase_tienen_alto_propio(panel: ScoringPanel):
    """Es el control que más se aprieta en toda la noche, uno por época."""
    for boton in panel._botones.values():
        assert boton.minimumHeight() == ALTO_DEL_BOTON


def test_cambiar_de_nomenclatura_no_deja_botones_viejos(panel: ScoringPanel):
    """Con la propiedad `fase` puesta, un botón que sobreviviera se seguiría
    pintando con el color de una fase que ya no existe."""
    panel.set_nomenclature(Nomenclature.RK)
    panel.set_nomenclature(Nomenclature.AASM)

    en_la_fila = [panel._fila.itemAt(i).widget() for i in range(panel._fila.count())]
    assert [b.property("fase") for b in en_la_fila] == [
        f.value for f in panel._botones
    ]


# -- La itálica de lo que nadie eligió ----------------------------------------


def test_el_pie_inclina_la_ausencia(panel: ScoringPanel):
    """**La itálica dice «esto no lo eligió nadie»** (hito 43). Es la misma
    clase de dato que el «sin medir» de la tabla de impedancias, y hasta acá
    los dos se apoyaban en el gris, que ya quiere decir «esto es secundario»."""
    panel.set_current(SleepStage.UNSCORED, False, window_index=340)

    assert f"<i>{SIN_SCOREAR}</i>" in panel._pie.text()


def test_el_pie_no_inclina_la_ventana(panel: ScoringPanel):
    """**Se inclina la ausencia y no el renglón.** Inclinar «Ventana 341»
    diría que la ventana tampoco la eligió nadie, que es falso."""
    panel.set_current(SleepStage.UNSCORED, False, window_index=340)

    assert "<i>Ventana" not in panel._pie.text()
    assert panel._pie.text().startswith("Ventana 341")


def test_scorearla_endereza_el_pie(panel: ScoringPanel):
    """La otra mitad: si todo estuviera inclinado, la inclinación no diría
    nada, y «Ventana 341 · N2» no es ninguna ausencia."""
    panel.set_current(SleepStage.N2, False, window_index=340)

    assert "<i>" not in panel._pie.text()


def test_el_pie_se_contesta_en_texto_pelado(panel: ScoringPanel):
    """`status()` es lo que compara el resto del programa, y el rótulo guarda
    el suyo con marcas: `text()` no sirve para contestarlo."""
    panel.set_current(SleepStage.UNSCORED, False, window_index=340)

    assert panel.status() == status_text(340, SleepStage.UNSCORED, False)
    assert "<" not in panel.status()


# -- Accesibilidad (hito 63) --------------------------------------------------


def test_el_selector_de_nomenclatura_tiene_nombre(panel: ScoringPanel):
    """Un lector de pantalla lee el tooltip como descripción: sin nombre se
    anunciaba como «combo, AASM» sin decir de qué."""
    assert panel._nomenclaturas.accessibleName() == "Nomenclatura"


def test_la_casilla_de_arousal_se_puede_apuntar(panel: ScoringPanel):
    """Medía 15 px de alto; WCAG 2.5.8 pide 24."""
    panel.show()

    assert panel._arousal.height() >= 24
