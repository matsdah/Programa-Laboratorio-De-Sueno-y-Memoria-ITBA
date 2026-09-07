"""Tests de los atajos de teclado.

`ui/` no lleva tests unitarios de sus widgets, y eso sigue igual. Estas dos
funciones son la excepción por un motivo concreto: **no necesitan Qt de ninguna
clase** —se llaman sin `QApplication`— y lo que hacen es exactamente lo que se
rompe en silencio.

Los atajos no son un accesorio: son la vía principal de quien scorea una noche
entera, que son cientos de ventanas. Y los de fase **se derivan de la
nomenclatura**, así que agregar una fase o cambiar de sistema tiene que traer su
tecla solo. Una tabla escrita a mano se desincroniza sin que nada avise: el
usuario aprieta una tecla y no pasa nada.
"""

import pytest

from psglab.core.nomenclature import Nomenclature, stages_of
from psglab.ui.shortcuts import (
    ACTIONS,
    FIXED_SHORTCUTS,
    shortcuts_help_text,
    stage_shortcuts,
)


# -- Los atajos de fase se derivan, no se escriben ---------------------------


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_cada_fase_de_la_nomenclatura_tiene_su_tecla(nomenclatura: Nomenclature):
    """Ni una de más ni una de menos.

    Es la promesa del módulo: agregar una fase no puede obligar a tocar un
    diccionario a mano.
    """
    assert len(stage_shortcuts(nomenclatura)) == len(stages_of(nomenclatura))


def test_las_teclas_de_rechtschaffen_y_kales():
    """W, 1, 2, 3, 4, R y M: las siete fases del sistema clásico."""
    assert set(stage_shortcuts(Nomenclature.RK)) == {"W", "1", "2", "3", "4", "R", "M"}


def test_las_teclas_de_aasm():
    """AASM no tiene S4 ni movimiento corporal, así que tampoco sus teclas."""
    assert set(stage_shortcuts(Nomenclature.AASM)) == {"W", "1", "2", "3", "R"}


def test_cambiar_de_nomenclatura_cambia_las_teclas():
    """El 4 y la M existen en una y no en la otra.

    Si la tabla estuviera escrita a mano, el usuario en AASM apretaría el 4 y
    scorearía una fase que su nomenclatura no tiene.
    """
    assert "4" in stage_shortcuts(Nomenclature.RK)
    assert "4" not in stage_shortcuts(Nomenclature.AASM)


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_ninguna_tecla_de_fase_se_repite(nomenclatura: Nomenclature):
    """Dos fases con la misma tecla harían inalcanzable a una de las dos."""
    teclas = list(stage_shortcuts(nomenclatura))
    assert len(teclas) == len(set(teclas))


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_cada_atajo_de_fase_dice_que_hace(nomenclatura: Nomenclature):
    """El texto va a la ayuda, así que tiene que nombrar la fase."""
    for texto in stage_shortcuts(nomenclatura).values():
        assert texto.strip()


# -- Que no choquen entre sí -------------------------------------------------


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_las_teclas_de_fase_no_chocan_con_las_fijas(nomenclatura: Nomenclature):
    """**El motivo por el que todos los atajos viven en un solo archivo.**

    Una colisión se detecta leyendo un módulo, y acá además la detecta un test:
    si alguien agregara `Ctrl+R` para otra cosa, o una fase nueva cayera sobre
    la `A` del arousal, el usuario perdería una de las dos funciones sin que
    nada avisara.
    """
    assert not set(stage_shortcuts(nomenclatura)) & set(FIXED_SHORTCUTS)


def test_cada_atajo_fijo_sabe_a_que_metodo_va():
    """`FIXED_SHORTCUTS` es lo que **lee el usuario** y `ACTIONS` el cableado.

    Están separados para que cambiar un texto de ayuda no pueda desconectar una
    tecla, pero tienen que cubrir las mismas teclas: una sin acción sería un
    atajo que no hace nada, y una acción sin atajo, código inalcanzable.
    """
    assert set(ACTIONS) == set(FIXED_SHORTCUTS)


def test_las_flechas_y_el_arousal_estan_declarados():
    """Son los del pliego: navegación (V1_F), amplitud (V2_P y V5_F) y arousal
    (V2_F de "Scoring")."""
    for tecla in ("Left", "Right", "Up", "Down", "A"):
        assert tecla in FIXED_SHORTCUTS


# -- La ayuda ----------------------------------------------------------------


@pytest.mark.parametrize("nomenclatura", list(Nomenclature))
def test_la_ayuda_lista_todos_los_atajos(nomenclatura: Nomenclature):
    """Se arma desde los diccionarios del módulo, así que no puede quedar
    desactualizada: es el motivo de que exista la función."""
    texto = shortcuts_help_text(nomenclatura)
    for tecla in FIXED_SHORTCUTS:
        assert tecla in texto
    for tecla in stage_shortcuts(nomenclatura):
        assert tecla in texto


def test_la_ayuda_dice_de_que_nomenclatura_son_las_fases():
    """El mismo "2" es S2 o N2 según el sistema; la ayuda tiene que decir cuál."""
    assert Nomenclature.AASM.value in shortcuts_help_text(Nomenclature.AASM)
    assert Nomenclature.RK.value in shortcuts_help_text(Nomenclature.RK)


def test_la_ayuda_cambia_con_la_nomenclatura():
    """El usuario que cambia de sistema tiene que ver la lista nueva sin que
    nadie edite nada."""
    assert shortcuts_help_text(Nomenclature.RK) != shortcuts_help_text(
        Nomenclature.AASM
    )
