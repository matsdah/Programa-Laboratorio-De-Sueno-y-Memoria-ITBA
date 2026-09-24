"""Tests del canalón: qué dice de cada canal y dónde queda.

**El dibujo casi no se testea**, como en el visualizador; lo que sí se puede
afirmar es lo que motivó el módulo: que el rótulo de un canal **no ocupa
píxeles del área de trazo**. Ésa es la diferencia con los `pg.TextItem` de
antes, y es estructural —el `ViewBox` arranca después del canalón— así que se
puede medir sin mirar una imagen.

Hay una excepción y es a propósito: la muestra de color sí se busca en el mapa
de bits. Es lo único del rótulo que no es texto, sobrevive al plugin
`offscreen` —que no trae tipografías— y es la pieza que reemplaza al nombre
pintado del color del canal, así que conviene tener una prueba de que se
dibuja.
"""

import pytest
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

pg = pytest.importorskip("pyqtgraph")

from psglab.ui import theme  # noqa: E402
from psglab.ui.channel_axis import (  # noqa: E402
    ANCHO_DEL_CANALON,
    ChannelAxis,
    ChannelLane,
)


@pytest.fixture
def eje(qt_app) -> ChannelAxis:
    """Un canalón suelto, sin gráfico al que colgarse."""
    return ChannelAxis()


def carriles() -> list[ChannelLane]:
    """Dos renglones, como los de un registro de dos canales."""
    return [
        ChannelLane(name="C3", detail="EEG · 100 µV", color="#1b4f9c", position=0.0),
        ChannelLane(name="EMG-menton", detail="EMG · 50 µV", color="#3f7a2e", position=-1.0),
    ]


# -- Lo que dice --------------------------------------------------------------


def test_los_carriles_se_guardan_en_orden(eje: ChannelAxis):
    """El orden es el de apilado, que es el que ve el investigador."""
    eje.set_lanes(carriles())

    assert [carril.name for carril in eje.lanes()] == ["C3", "EMG-menton"]


def test_recibe_estado_completo_y_no_un_delta(eje: ChannelAxis):
    """Volver a llamarlo reemplaza, no agrega: es la misma regla que
    `set_overlays()` y que `grid.set_lines()`."""
    eje.set_lanes(carriles())
    eje.set_lanes(carriles()[:1])

    assert len(eje.lanes()) == 1


def test_arranca_vacio(eje: ChannelAxis):
    """El visualizador se construye antes de que haya ningún registro."""
    assert eje.lanes() == ()


# -- Lo que no dibuja ---------------------------------------------------------


def test_no_pone_ninguna_marca_numerica(eje: ChannelAxis):
    """El eje vertical son carriles, no una escala: marcas en 0, −1 y −2 no
    significan nada para quien mira, y pyqtgraph las pondría solo."""
    assert eje.tickValues(-2.0, 0.5, 400.0) == []


def test_el_esquema_lo_deja_sin_linea(eje: ChannelAxis):
    """El diseño no separa el canalón del gráfico con una regla vertical."""
    eje.apply_scheme(theme.SERENO)

    assert eje.pen().style() == pg.QtCore.Qt.PenStyle.NoPen


def test_las_dos_tintas_salen_del_esquema(eje: ChannelAxis):
    """El nombre en la tinta del texto y el detalle en la secundaria. El color
    del canal no se usa para ninguna de las dos; ver el módulo."""
    eje.apply_scheme(theme.NOCTURNO)

    assert eje._tinta == theme.NOCTURNO.foreground
    assert eje._tinta_secundaria == theme.NOCTURNO.overview_text


# -- Las dos tipografías ------------------------------------------------------


def test_la_segunda_linea_es_mas_chica_que_el_nombre(eje: ChannelAxis):
    """La escala es el dato que se consulta; el nombre es el que se busca.

    **Las dos salen de la escala del programa** desde el hito 43: el nombre es
    «cuerpo» y la escala «lectura secundaria». Antes este módulo achicaba un
    punto por su cuenta y el chip achicaba dos."""
    fuente = QFont("IBM Plex Sans", 12)
    eje.set_fonts(fuente)

    assert eje._fuente_numerica.pointSize() < fuente.pointSize()


def test_una_tipografia_diminuta_no_desaparece(eje: ChannelAxis):
    """Restarle un punto a una de 6 dejaría la segunda línea en 5, que no se
    lee. El piso lo pone la escala."""
    eje.set_fonts(QFont("IBM Plex Sans", 6))

    assert eje._fuente_numerica.pointSize() >= 6


# -- Dónde queda, que es todo el punto ----------------------------------------


def test_el_canalon_reserva_su_ancho(eje: ChannelAxis):
    """Es lo que un `TextItem` no podía hacer: el ancho se le descuenta al área
    de trazo, así que ninguna señal se dibuja encima del rótulo."""
    assert eje.fixedWidth == ANCHO_DEL_CANALON


def test_la_muestra_de_color_se_dibuja_en_el_canalon(qt_app):
    """**Lo único del rótulo que se busca en el mapa de bits.**

    Reemplaza al nombre escrito del color del canal, que era lo que
    identificaba cada carril sin contarlos: el nombre pasó a la tinta del texto
    porque la paleta de canales está verificada como gráfico —3,0— y el color 3
    de Sereno da 3,89 sobre el fondo, por debajo de los 4,5 de WCAG para texto.
    Si la muestra no se dibujara, la identificación por color se habría perdido
    sin que ningún otro test lo notara.
    """
    grafico = pg.PlotWidget(axisItems={"left": ChannelAxis()})
    eje = grafico.getPlotItem().getAxis("left")
    eje.apply_scheme(theme.SERENO)
    eje.set_lanes(carriles())
    grafico.getPlotItem().setYRange(-1.5, 0.5, padding=0)
    grafico.resize(400, 300)
    grafico.show()
    QApplication.processEvents()

    imagen = grafico.grab().toImage()
    ancho = min(ANCHO_DEL_CANALON, imagen.width())
    colores = {
        QColor(imagen.pixel(x, y)).name()
        for x in range(ancho)
        for y in range(imagen.height())
    }

    assert {carril.color for carril in carriles()} <= colores


def test_los_mismos_carriles_no_piden_otro_dibujo(eje: ChannelAxis):
    """**El visualizador los rearma en cada dibujo**, o sea veinticinco veces
    por segundo mientras se reproduce. Repintar el canalón en cada cuadro sería
    lo que el hito 25 le sacó a la grilla: los rótulos cambian al elegir canales
    y al cambiar la amplitud, no al moverse la página."""
    eje.set_lanes(carriles())
    eje.picture = "el dibujo de antes"
    eje.set_lanes(carriles())

    assert eje.picture == "el dibujo de antes"


def test_un_carril_distinto_si_lo_pide(eje: ChannelAxis):
    """La otra mitad: con la escala cambiada hay que redibujar."""
    eje.set_lanes(carriles())
    eje.picture = "el dibujo de antes"
    otra_escala = [carriles()[0], ChannelLane("EMG-menton", "EMG · 200 µV", "#3f7a2e", -1.0)]
    eje.set_lanes(otra_escala)

    assert eje.picture is None
