"""Tests de la página visible.

La página es lo que se está mirando, y desde el refactor de la interfaz ya no
coincide con la época de scoring de 30 s. Lo que se verifica acá son las cuatro
promesas de las que cuelga todo lo demás:

- **es inmutable**, así que repartirla entre el visualizador, las herramientas y
  la sesión es seguro;
- **`clamped()` es el único lugar que recorta**, igual que `set_scale_uv()` para
  la escala vertical;
- **`containing()` devuelve la misma página si el tramo ya está dentro**, que es
  lo que hace que avanzar de época con una página de cuatro horas no sacuda el
  dibujo;
- lo que **no** se puede recortar —un NaN, un ancho cero— sale como
  `PsgLabError` y no como una traza.

No hace falta Qt: la página es aritmética.
"""

import dataclasses

import pytest

from psglab.config import MIN_VIEW_SECONDS
from psglab.core.viewport import Viewport
from psglab.utils.errors import InvalidViewportError, PsgLabError

#: Una noche de ocho horas, que es el caso real del laboratorio.
NOCHE: float = 8 * 3600.0


@pytest.fixture
def pagina() -> Viewport:
    """Una época de 30 s al principio de una noche de ocho horas."""
    return Viewport.clamped(0.0, 30.0, NOCHE)


# -- Lo que no se puede construir --------------------------------------------


@pytest.mark.parametrize("hostil", [float("nan"), float("inf"), float("-inf")])
def test_una_pagina_con_un_numero_que_no_es_numero_se_rechaza(hostil: float):
    """`min` y `max` propagan el NaN en silencio, así que recortar no alcanza."""
    with pytest.raises(InvalidViewportError):
        Viewport.clamped(hostil, 30.0, NOCHE)


def test_una_pagina_sin_ancho_se_rechaza():
    """Una página de ancho cero no tiene fracciones, y la ocupación divide por
    su ancho."""
    with pytest.raises(InvalidViewportError):
        Viewport(0.0, 0.0, NOCHE)


def test_una_pagina_que_empieza_antes_del_registro_se_rechaza():
    with pytest.raises(InvalidViewportError):
        Viewport(-1.0, 30.0, NOCHE)


def test_un_registro_sin_duracion_se_rechaza():
    with pytest.raises(InvalidViewportError):
        Viewport(0.0, 30.0, 0.0)


def test_el_error_es_del_programa():
    """La ventana principal atrapa una sola clase."""
    assert issubclass(InvalidViewportError, PsgLabError)


def test_la_pagina_no_se_puede_modificar(pagina: Viewport):
    """Si alguno de los que la reciben pudiera escribirle encima, el resto
    quedaría dibujando una página que ya no es la elegida, sin que nada avise."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        pagina.span_seconds = 60.0  # type: ignore[misc]


# -- El recorte --------------------------------------------------------------


def test_una_pagina_mas_larga_que_el_registro_se_recorta(pagina: Viewport):
    assert Viewport.clamped(0.0, 1e9, NOCHE).span_seconds == NOCHE


def test_una_pagina_mas_corta_que_el_minimo_se_recorta():
    assert Viewport.clamped(0.0, 1e-9, NOCHE).span_seconds == MIN_VIEW_SECONDS


def test_un_registro_mas_corto_que_el_minimo_se_muestra_entero():
    """Existe: el BrainVision de prueba dura 7,9 segundos. El piso no puede
    pasar de la duración, o la página quedaría más larga que el registro."""
    corto = Viewport.clamped(0.0, 30.0, 0.005)

    assert corto.span_seconds == 0.005


def test_una_pagina_que_se_pasa_del_final_se_trae_para_atras(pagina: Viewport):
    """No se recorta el ancho: se corre el comienzo. Achicar la página al llegar
    al final haría que la escala cambiara sola."""
    corrida = pagina.with_start(1e9)

    assert corrida.end_seconds == NOCHE
    assert corrida.span_seconds == pagina.span_seconds


def test_un_comienzo_negativo_se_lleva_a_cero(pagina: Viewport):
    assert pagina.with_start(-100.0).start_seconds == 0.0


# -- Las transformaciones ----------------------------------------------------


def test_cambiar_la_escala_conserva_el_centro():
    """Con el comienzo fijo, cada «÷2» correría hacia la derecha lo que se está
    mirando, y acercarse no se sentiría como acercarse."""
    pagina = Viewport.clamped(1000.0, 60.0, NOCHE)

    achicada = pagina.zoomed(0.5)

    assert achicada.center_seconds == pytest.approx(pagina.center_seconds)
    assert achicada.span_seconds == 30.0


def test_la_escala_va_y_vuelve(pagina: Viewport):
    ida = pagina.zoomed(2.0)

    assert ida.zoomed(0.5).span_seconds == pytest.approx(pagina.span_seconds)


@pytest.mark.parametrize("hostil", [0.0, -1.0, float("nan"), float("inf")])
def test_un_factor_de_escala_que_no_sirve_avisa(pagina: Viewport, hostil: float):
    with pytest.raises(InvalidViewportError):
        pagina.zoomed(hostil)


def test_desplazar_no_cambia_la_duracion(pagina: Viewport):
    assert pagina.panned(600.0).span_seconds == pagina.span_seconds


def test_el_registro_entero_se_reconoce(pagina: Viewport):
    entera = pagina.whole_recording()

    assert entera.shows_whole_recording
    assert not pagina.shows_whole_recording


def test_cambiar_de_registro_recorta_la_pagina():
    """Filtrar puede acortar la duración por debajo de una época sin que
    `n_windows` cambie, y una página que se pasa del final dibujaría un tramo
    que no existe."""
    pagina = Viewport.clamped(7000.0, 60.0, NOCHE)

    encogida = pagina.for_duration(3600.0)

    assert encogida.end_seconds <= 3600.0


# -- `containing()`: lo que hace que navegar no sacuda el dibujo -------------


def test_un_tramo_que_ya_esta_dentro_devuelve_la_misma_pagina(pagina: Viewport):
    """**Devuelve el mismo objeto**, no uno igual: es lo que permite que
    `Session.set_viewport()` vuelva temprano y no avise a nadie."""
    assert pagina.containing(5.0, 10.0) is pagina


def test_con_una_pagina_larga_la_epoca_ya_esta_dentro():
    """Con cuatro horas en pantalla, apretar la flecha derecha mueve el
    resaltado y no mueve la página. Es la razón de ser de este método."""
    cuatro_horas = Viewport.clamped(0.0, 4 * 3600.0, NOCHE)

    assert cuatro_horas.containing(3600.0, 3630.0) is cuatro_horas


def test_un_tramo_a_la_derecha_trae_la_pagina_lo_minimo(pagina: Viewport):
    """Lo mínimo, no centrado: centrar en cada flecha haría saltar la pantalla
    media página por vez."""
    movida = pagina.containing(100.0, 130.0)

    assert movida.end_seconds == pytest.approx(130.0)
    assert movida.span_seconds == pagina.span_seconds


def test_un_tramo_a_la_izquierda_lleva_la_pagina_a_su_comienzo():
    pagina = Viewport.clamped(1000.0, 30.0, NOCHE)

    movida = pagina.containing(100.0, 130.0)

    assert movida.start_seconds == pytest.approx(100.0)


def test_un_tramo_que_empieza_adentro_y_termina_afuera_trae_la_pagina():
    """**El caso que faltaba**, y lo encontró la auditoría de los tests: los
    cinco tests de `containing()` usaban tramos totalmente adentro o totalmente
    afuera, nunca uno a medias.

    Es el caso normal cuando la página es apenas más larga que la época. Con
    `and` cambiado por `or` en la guarda, la página no se movería y la época
    quedaría cortada al medio; la suite entera lo atrapa por otro lado, pero
    ningún test de este método lo hacía.
    """
    pagina = Viewport.clamped(0.0, 40.0, NOCHE)

    movida = pagina.containing(20.0, 50.0)

    assert movida is not pagina, "la página no siguió a la época"
    assert movida.end_seconds == pytest.approx(50.0)
    assert movida.span_seconds == pytest.approx(pagina.span_seconds)


def test_un_tramo_que_termina_adentro_y_empieza_afuera_tambien():
    """La simétrica, por el borde izquierdo."""
    pagina = Viewport.clamped(100.0, 40.0, NOCHE)

    movida = pagina.containing(90.0, 120.0)

    assert movida.start_seconds == pytest.approx(90.0)


def test_un_tramo_mas_largo_que_la_pagina_se_alinea_por_el_comienzo():
    """Mostrar la primera mitad de la época que se va a scorear es más útil que
    mostrar el final de la anterior."""
    pagina = Viewport.clamped(0.0, 10.0, NOCHE)

    movida = pagina.containing(100.0, 130.0)

    assert movida.start_seconds == pytest.approx(100.0)


# -- Los extremos (hito 24) ------------------------------------------------------


def test_la_primera_pagina_esta_al_principio(pagina: Viewport):
    assert pagina.at_start
    assert not pagina.at_end


def test_la_ultima_pagina_esta_al_final():
    ultima = Viewport.clamped(NOCHE, 30.0, NOCHE)

    assert ultima.at_end
    assert not ultima.at_start


def test_el_final_tolera_el_redondeo_de_la_resta():
    """`clamped()` calcula el comienzo como duración − página, y con una
    duración que no es redonda la suma puede quedar un pelo corta. Sin
    tolerancia, la reproducción no se detendría nunca."""
    duracion = 79_500.0 + 1 / 3
    ultima = Viewport.clamped(duracion, 0.1, duracion)

    assert ultima.at_end


def test_una_pagina_del_medio_no_esta_en_ningun_extremo(pagina: Viewport):
    medio = pagina.panned(3600.0)

    assert not medio.at_start
    assert not medio.at_end


def test_el_registro_entero_esta_en_los_dos_extremos(pagina: Viewport):
    entera = pagina.whole_recording()

    assert entera.at_start and entera.at_end


def test_a_un_microsegundo_del_final_no_se_considera_final():
    """La tolerancia es de un microsegundo; una muestra de un registro de sueño
    dura por lo menos mil veces más."""
    casi = Viewport(NOCHE - 30.0 - 0.001, 30.0, NOCHE)

    assert not casi.at_end


# -- `Viewport.replaced()` (hito 48) ---------------------------------------------
#
# **Su docstring dice que existe «para los tests», y ningún test la
# usaba.** Tenía sólo una fila en `test_contratos.py`, que la ejercita con
# valores hostiles y no verifica que haga lo correcto con los buenos. Lo encontró la auditoría de los tests, y
# desde entonces lo exige `test_consistencia.py`.


def test_reemplazar_un_campo_da_otra_pagina_con_ese_campo(pagina: Viewport):
    otra = pagina.replaced(start_seconds=120.0)

    assert otra.start_seconds == 120.0
    assert otra.span_seconds == pagina.span_seconds


def test_reemplazar_no_toca_la_original(pagina: Viewport):
    """Es inmutable: todo lo que la «cambia» devuelve otra."""
    antes = pagina.start_seconds

    pagina.replaced(start_seconds=120.0)

    assert pagina.start_seconds == antes


def test_reemplazar_no_recorta_a_proposito():
    """**Es la diferencia con `clamped()`**, y la razón de que exista: construir
    una página exacta, aunque se salga del registro, para poder probar qué hace
    el resto del programa con ella."""
    pagina = Viewport.clamped(0.0, 30.0, NOCHE)

    afuera = pagina.replaced(start_seconds=NOCHE + 100.0)

    assert afuera.start_seconds == NOCHE + 100.0


# -- Acercar con la rueda: un instante queda quieto (hito 56) ---------------


def test_acercar_deja_quieto_el_instante_elegido():
    """**Es lo que hace la rueda**: el instante bajo el mouse sigue bajo el
    mouse. Con el centro fijo, acercarse a un huso del borde lo sacaba de la
    pantalla."""
    pagina = Viewport.clamped(1000.0, 60.0, NOCHE)

    acercada = pagina.zoomed_at(0.5, 1015.0)

    assert acercada.span_seconds == pytest.approx(30.0)
    # Estaba a un cuarto de la página y sigue a un cuarto.
    assert acercada.start_seconds == pytest.approx(1015.0 - 30.0 / 4)


def test_alejar_y_acercar_en_el_mismo_instante_vuelve_a_la_misma_pagina():
    pagina = Viewport.clamped(1000.0, 60.0, NOCHE)

    vuelta = pagina.zoomed_at(2.0, 1040.0).zoomed_at(0.5, 1040.0)

    assert vuelta.start_seconds == pytest.approx(pagina.start_seconds)
    assert vuelta.span_seconds == pytest.approx(pagina.span_seconds)


def test_en_el_borde_del_registro_la_pagina_se_recorta(pagina: Viewport):
    """Alejar desde el comienzo no puede dejar una página que empiece antes del
    registro: se recorta, y el instante se corre."""
    alejada = pagina.zoomed_at(4.0, 20.0)

    assert alejada.start_seconds == 0.0
    assert alejada.span_seconds == pytest.approx(120.0)


def test_en_el_minimo_el_ancho_no_baja_y_el_instante_no_se_mueve():
    """Ubicar el comienzo con el ancho pedido y no con el que queda correría
    la página al llegar al mínimo."""
    pagina = Viewport.clamped(100.0, MIN_VIEW_SECONDS * 1.5, NOCHE)
    instante = pagina.start_seconds + pagina.span_seconds / 3

    tope = pagina.zoomed_at(0.1, instante)

    assert tope.span_seconds == pytest.approx(MIN_VIEW_SECONDS)
    assert tope.start_seconds == pytest.approx(instante - MIN_VIEW_SECONDS / 3)


def test_un_instante_fuera_de_la_pagina_se_lleva_a_su_borde():
    """Anclar en algo que no se ve correría la página entera fuera de lo que
    se estaba mirando."""
    pagina = Viewport.clamped(1000.0, 60.0, NOCHE)

    acercada = pagina.zoomed_at(0.5, 5000.0)

    assert acercada.end_seconds == pytest.approx(pagina.end_seconds)


@pytest.mark.parametrize("hostil", [0.0, -1.0, float("nan"), float("inf")])
def test_el_factor_de_la_rueda_se_valida_igual(pagina: Viewport, hostil: float):
    with pytest.raises(InvalidViewportError):
        pagina.zoomed_at(hostil, 10.0)


@pytest.mark.parametrize("hostil", [float("nan"), float("inf"), None, "10"])
def test_un_instante_que_no_es_numero_avisa(pagina: Viewport, hostil: object):
    with pytest.raises(InvalidViewportError):
        pagina.zoomed_at(0.5, hostil)  # type: ignore[arg-type]
