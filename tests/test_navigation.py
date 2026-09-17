"""Tests de la barra de navegación.

`navigation.py` estaba en `SIN_TEST_PROPIO` cuando eran dos botones de texto y
un rótulo: no había mucho que verificar sin mirar una pantalla. Dejó de ser
cierto al agregarle la franja de posición, que **traduce un clic a una ventana**
—la misma clase de conversión que el proyecto aísla y testea en todos los demás
lugares donde ocurre—.

Lo que se verifica:

- que la franja convierta bien, sobre todo **en los bordes**, donde un clic a la
  derecha del todo da fracción 1,0 y `int(1,0 × total)` es una ventana que no
  existe;
- que los botones **pidan y no naveguen**, que es el contrato que mantiene en
  `core/` la regla de qué ventana existe;
- que se deshabiliten en los extremos, para que no haya botones que no hacen
  nada;
- desde el hito 24, que los botones de página y de reproducción pidan lo
  suyo, y que el de reproducir no se apague mientras reproduce: es con el
  que se pausa.
"""

import pytest

pytest.importorskip("pyqtgraph")

import psglab.ui.navigation as navigation  # noqa: E402
import psglab.ui.theme as theme  # noqa: E402


@pytest.fixture
def barra(qt_app) -> navigation.NavigationBar:
    widget = navigation.NavigationBar()
    widget.resize(800, 40)
    return widget


@pytest.fixture
def franja(qt_app) -> navigation.PositionStrip:
    widget = navigation.PositionStrip()
    widget.resize(1000, navigation.ALTO_DE_LA_FRANJA)
    return widget


def pedidas(widget) -> list[int]:
    """Las ventanas que el widget pidió, para no repetir el cableado."""
    recibidas: list[int] = []
    widget.window_requested.connect(recibidas.append)
    return recibidas


# -- La franja convierte un clic en una ventana ------------------------------


def test_sin_registro_la_franja_no_pide_nada(franja, qt_app):
    """`int(fracción × 0)` sería 0, y la ventana 0 de un registro que no está
    abierto no existe."""
    recibidas = pedidas(franja)

    franja.set_position(0, 0)
    franja.mousePressEvent(_clic(franja, 0.5))

    assert recibidas == []


@pytest.mark.parametrize(
    "fraccion, esperada",
    [(0.0, 0), (0.25, 240), (0.5, 480), (0.999, 959)],
)
def test_la_franja_convierte_la_posicion_en_ventana(
    franja, fraccion: float, esperada: int
):
    recibidas = pedidas(franja)
    franja.set_position(0, 960)

    franja.mousePressEvent(_clic(franja, fraccion))

    assert recibidas == [esperada]


def test_un_clic_en_el_borde_derecho_no_pide_una_ventana_que_no_existe(franja):
    """Es el mismo recorte que hace `HistogramTool.on_click()`: la fracción 1,0
    multiplicada por el total da el índice siguiente al último."""
    recibidas = pedidas(franja)
    franja.set_position(0, 960)

    franja.mousePressEvent(_clic(franja, 1.0))

    assert recibidas == [959]


def test_la_franja_sin_ancho_no_rompe(qt_app):
    """Pasa durante el armado del layout, antes de que Qt le dé tamaño."""
    franja = navigation.PositionStrip()
    franja.resize(0, navigation.ALTO_DE_LA_FRANJA)
    recibidas = pedidas(franja)
    franja.set_position(0, 100)

    franja.mousePressEvent(_clic(franja, 0.5))

    assert recibidas == []


# -- Los botones piden, no navegan -------------------------------------------


def test_los_botones_piden_la_ventana_vecina(barra):
    recibidas = pedidas(barra)
    barra.set_position(5, 10)

    barra._siguiente.click()
    barra._anterior.click()

    assert recibidas == [6, 4]


def test_los_botones_de_extremo_van_al_principio_y_al_final(barra):
    """Antes no existían: llegar a la última ventana de una noche eran cientos
    de pulsaciones."""
    recibidas = pedidas(barra)
    barra.set_position(5, 10)

    barra._ultima.click()
    barra._primera.click()

    assert recibidas == [9, 0]


def test_en_la_primera_ventana_no_se_puede_retroceder(barra):
    barra.set_position(0, 10)

    assert not barra._anterior.isEnabled()
    assert not barra._primera.isEnabled()
    assert barra._siguiente.isEnabled()


def test_en_la_ultima_ventana_no_se_puede_avanzar(barra):
    barra.set_position(9, 10)

    assert not barra._siguiente.isEnabled()
    assert not barra._ultima.isEnabled()
    assert barra._anterior.isEnabled()


def test_sin_registro_no_hay_ningun_boton_habilitado(barra):
    """Un botón que se puede apretar y no hace nada es peor que uno apagado."""
    barra.set_position(0, 0)

    habilitados = [
        b
        for b in (
            barra._primera,
            barra._anterior,
            barra._siguiente,
            barra._ultima,
            barra._mas_amplitud,
            barra._menos_amplitud,
            barra._pagina_atras,
            barra._media_atras,
            barra._reproducir,
            barra._media_adelante,
            barra._pagina_adelante,
        )
        if b.isEnabled()
    ]

    assert habilitados == []


def test_la_amplitud_se_pide_sin_decir_cuanto(barra):
    """Cuánto cambia por paso lo decide `Session`, no un widget."""
    subidas: list[int] = []
    bajadas: list[int] = []
    barra.amplitude_up_requested.connect(lambda: subidas.append(1))
    barra.amplitude_down_requested.connect(lambda: bajadas.append(1))
    barra.set_position(0, 10)

    barra._mas_amplitud.click()
    barra._menos_amplitud.click()

    assert (len(subidas), len(bajadas)) == (1, 1)


# -- Los indicadores ---------------------------------------------------------


def test_la_posicion_se_muestra_en_base_uno(barra):
    """La ventana 0 interna es la 1 para el usuario, y éste es el único lugar
    donde se suma ese 1."""
    barra.set_position(0, 960)

    assert barra._posicion.text() == "Ventana 1 de 960"


def test_sin_registro_lo_dice_en_vez_de_mostrar_cero(barra):
    barra.set_position(0, 0)

    assert barra._posicion.text() == "Sin registro"


def test_el_horario_se_oculta_si_el_registro_no_lo_informa(barra):
    """Un horario vacío en pantalla invita a leerlo como medianoche."""
    barra.set_clock_time("23:41:00")
    assert barra._horario.text() == "23:41:00"

    barra.set_clock_time(None)

    assert barra._horario.text() == ""
    assert barra._horario.isHidden()


def test_cambiar_de_esquema_repinta_los_iconos(barra):
    """Un icono es un mapa de bits ya pintado: sin repintarlo, pasar de oscuro
    a claro deja los triángulos claros sobre fondo claro."""
    antes = barra._siguiente.icon().cacheKey()
    antes_de_reproducir = barra._reproducir.icon().cacheKey()

    theme.set_current(theme.OSCURO)
    try:
        barra.apply_scheme()
    finally:
        theme.set_current(theme.CLARO)

    assert barra._siguiente.icon().cacheKey() != antes
    assert barra._reproducir.icon().cacheKey() != antes_de_reproducir


def _clic(widget, fraccion: float):
    """Un evento de clic izquierdo a esa fracción del ancho del widget.

    Se construye con las tres posiciones —local, de la ventana y global— igual
    que el helper de `test_entrega.py`: la forma corta está deprecada en Qt 6 y
    llena la corrida de advertencias.
    """
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    punto = QPointF(fraccion * widget.width(), widget.height() / 2)
    return QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        punto,
        punto,
        punto,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# -- La página y la reproducción (hito 24) ---------------------------------------


def con_registro(barra, al_principio=False, al_final=False, entera=False):
    barra.set_position(3, 10)
    barra.set_page_bounds(al_principio, al_final, entera)
    return barra


def test_los_botones_de_pagina_piden_su_fraccion(barra):
    """Una página entera o media, hacia cada lado. Mover es de la ventana."""
    con_registro(barra)
    recibidas: list[float] = []
    barra.page_pan_requested.connect(recibidas.append)

    for boton in (
        barra._pagina_atras,
        barra._media_atras,
        barra._media_adelante,
        barra._pagina_adelante,
    ):
        boton.click()

    assert recibidas == [-1.0, -0.5, 0.5, 1.0]


def test_los_botones_de_pagina_no_piden_una_ventana(barra):
    """Mueven lo que se ve, no la época que se scorea."""
    con_registro(barra)
    ventanas = pedidas(barra)

    barra._pagina_adelante.click()
    barra._media_atras.click()

    assert ventanas == []


def test_al_principio_no_se_puede_retroceder_la_pagina(barra):
    con_registro(barra, al_principio=True)

    assert not barra._pagina_atras.isEnabled()
    assert not barra._media_atras.isEnabled()
    assert barra._media_adelante.isEnabled()
    assert barra._reproducir.isEnabled()


def test_al_final_no_se_puede_avanzar_ni_reproducir(barra):
    con_registro(barra, al_final=True)

    assert barra._pagina_atras.isEnabled()
    assert not barra._pagina_adelante.isEnabled()
    assert not barra._media_adelante.isEnabled()
    assert not barra._reproducir.isEnabled()


def test_con_el_registro_entero_no_se_puede_reproducir(barra):
    con_registro(barra, al_principio=True, al_final=True, entera=True)

    assert not barra._reproducir.isEnabled()


def test_reproduciendo_el_boton_sigue_habilitado_en_el_final(barra):
    """Es el botón con que se pausa."""
    con_registro(barra)
    barra.set_playing(True)

    barra.set_page_bounds(False, True, False)

    assert barra._reproducir.isEnabled()


def test_al_pausar_en_el_final_el_boton_se_apaga(barra):
    """Los límites se calcularon mientras todavía reproducía."""
    con_registro(barra)
    barra.set_playing(True)
    barra.set_page_bounds(False, True, False)

    barra.set_playing(False)

    assert not barra._reproducir.isEnabled()


def test_reproducir_pide_y_no_reproduce(barra):
    con_registro(barra)
    pedidos: list[bool] = []
    barra.playback_toggle_requested.connect(lambda: pedidos.append(True))

    barra._reproducir.click()

    assert pedidos == [True]
    assert barra._reproducir.toolTip() == "Reproducir"


def test_reproduciendo_el_boton_dice_pausar(barra):
    antes = barra._reproducir.icon().cacheKey()

    barra.set_playing(True)

    assert barra._reproducir.toolTip() == "Pausar"
    assert barra._reproducir.icon().cacheKey() != antes
    barra.set_playing(False)
    assert barra._reproducir.toolTip() == "Reproducir"


def test_el_selector_ofrece_las_velocidades_y_arranca_en_tiempo_real(barra):
    from psglab.ui.playback import DEFAULT_SPEED, PLAYBACK_SPEEDS

    opciones = [
        barra.speed_selector.itemData(i) for i in range(barra.speed_selector.count())
    ]

    assert opciones == list(PLAYBACK_SPEEDS)
    assert barra.speed_selector.currentData() == DEFAULT_SPEED
    assert barra.speed_selector.currentText() == "1×"


def test_elegir_una_velocidad_la_pide(barra):
    recibidas: list[float] = []
    barra.playback_speed_changed.connect(recibidas.append)

    barra.speed_selector.setCurrentIndex(barra.speed_selector.findText("30×"))

    assert recibidas == [30.0]


def test_un_clic_en_un_boton_no_le_saca_el_foco_a_la_senal(barra):
    """Si se lo sacara, Espacio dejaría de reproducir después de cualquier
    clic. Con Tab se siguen alcanzando."""
    from PySide6.QtCore import Qt

    for boton in (barra._reproducir, barra._pagina_adelante, barra._siguiente):
        assert boton.focusPolicy() == Qt.FocusPolicy.TabFocus
