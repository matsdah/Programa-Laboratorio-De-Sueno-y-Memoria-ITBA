"""Tests de los iconos dibujados por el programa.

**No se testea cómo se ven.** Un triángulo es un triángulo y compararlo píxel a
píxel contra una imagen de referencia ataría la suite a la versión de Qt y a la
plataforma, que es exactamente lo que este proyecto evita.

Lo que sí se verifica son las tres cosas que fallan en silencio: que el icono
no salga vacío —el modo de fallo si alguien olvida cerrar el pintor—, que el
color pedido sea el que se usa, y que un nombre equivocado avise en vez de
devolver un cuadrado transparente que nadie va a notar hasta ver la barra.
"""

import pytest
from PySide6.QtCore import QSize

pytest.importorskip("pyqtgraph")

import psglab.ui.icons as icons  # noqa: E402
from psglab.utils.errors import PsgLabError, UnknownIconError  # noqa: E402


@pytest.mark.parametrize("nombre", list(icons.NOMBRES))
def test_cada_icono_se_dibuja(qt_app, nombre: str):
    resultado = icons.icon(nombre, "#ff0000")

    assert not resultado.isNull()


@pytest.mark.parametrize("nombre", list(icons.NOMBRES))
def test_ningun_icono_sale_vacio(qt_app, nombre: str):
    """Es el modo de fallo si alguien olvida `pintor.end()` antes de construir
    el `QIcon`: Qt avisa por consola y devuelve un icono transparente."""
    imagen = icons.icon(nombre, "#ff0000").pixmap(QSize(icons.LADO, icons.LADO)).toImage()

    pintados = sum(
        1
        for x in range(imagen.width())
        for y in range(imagen.height())
        if imagen.pixelColor(x, y).alpha() > 0
    )

    assert pintados > 0


def test_el_icono_usa_el_color_pedido(qt_app):
    """Es lo que permite que los iconos sigan legibles al cambiar de esquema,
    que un archivo `.png` no podría hacer."""
    imagen = icons.icon("siguiente", "#ff0000").pixmap(QSize(icons.LADO, icons.LADO)).toImage()

    colores = {
        imagen.pixelColor(x, y).name()
        for x in range(imagen.width())
        for y in range(imagen.height())
        if imagen.pixelColor(x, y).alpha() == 255
    }

    assert colores == {"#ff0000"}


def test_dos_colores_dan_dos_iconos_distintos(qt_app):
    claro = icons.icon("anterior", "#ffffff").pixmap(QSize(16, 16)).toImage()
    oscuro = icons.icon("anterior", "#000000").pixmap(QSize(16, 16)).toImage()

    assert claro != oscuro


def test_las_flechas_opuestas_no_son_el_mismo_dibujo(qt_app):
    """Si `_camino()` ignorara la dirección, la barra tendría cuatro botones
    idénticos y nadie lo notaría hasta usarla."""
    izquierda = icons.icon("anterior", "#000000").pixmap(QSize(32, 32)).toImage()
    derecha = icons.icon("siguiente", "#000000").pixmap(QSize(32, 32)).toImage()

    assert izquierda != derecha


def test_ir_al_extremo_no_es_lo_mismo_que_ir_al_vecino(qt_app):
    """«Primera» lleva la barra que «anterior» no tiene: sin ella los dos
    botones serían el mismo triángulo."""
    primera = icons.icon("primera", "#000000").pixmap(QSize(32, 32)).toImage()
    anterior = icons.icon("anterior", "#000000").pixmap(QSize(32, 32)).toImage()

    assert primera != anterior


def test_un_nombre_que_no_existe_avisa_y_enumera_los_que_si(qt_app):
    """El nombre lo escribe quien arma la barra, así que un error de tipeo es
    la causa habitual y el mensaje tiene que ayudar a corregirlo."""
    with pytest.raises(UnknownIconError) as fallo:
        icons.icon("retroceder", "#000000")

    assert "retroceder" in str(fallo.value)
    assert "anterior" in (fallo.value.details or "")


def test_pedir_un_icono_con_algo_que_no_es_texto_avisa(qt_app):
    with pytest.raises(UnknownIconError):
        icons.icon(3, "#000000")  # type: ignore[arg-type]


def test_el_error_del_modulo_es_del_programa():
    """Si escapara crudo atravesaría el `except` de la ventana principal."""
    assert issubclass(UnknownIconError, PsgLabError)


def test_reproducir_no_se_confunde_con_la_flecha_de_epoca(qt_app):
    """Comparten fila: el de reproducir lleva el triángulo calado en un
    círculo, el de época es un triángulo lleno."""
    reproducir = icons.icon("reproducir", "#000000").pixmap(QSize(32, 32)).toImage()
    siguiente = icons.icon("siguiente", "#000000").pixmap(QSize(32, 32)).toImage()
    pausa = icons.icon("pausa", "#000000").pixmap(QSize(32, 32)).toImage()

    assert reproducir != siguiente
    assert reproducir != pausa


def test_el_centro_de_reproducir_esta_calado(qt_app):
    """Si la regla de relleno no fuera par-impar, el icono sería un círculo
    lleno y los dos estados se verían iguales."""
    imagen = icons.icon("reproducir", "#000000").pixmap(
        QSize(icons.LADO, icons.LADO)
    ).toImage()

    centro = imagen.pixelColor(icons.LADO // 2, icons.LADO // 2)
    borde = imagen.pixelColor(icons.LADO // 2, int(icons.LADO * 0.22))

    assert centro.alpha() == 0
    assert borde.alpha() > 0


@pytest.mark.parametrize(
    "atras, adelante",
    [("media-atras", "media-adelante"), ("pagina-atras", "pagina-adelante")],
)
def test_los_chevrones_opuestos_son_espejos(qt_app, atras: str, adelante: str):
    """Con margen: el suavizado de los bordes no cae exactamente igual de los
    dos lados, y eso no es un icono distinto."""
    from PySide6.QtCore import Qt

    izquierda = icons.icon(atras, "#000000").pixmap(QSize(32, 32)).toImage()
    derecha = icons.icon(adelante, "#000000").pixmap(QSize(32, 32)).toImage()
    espejada = izquierda.flipped(Qt.Orientation.Horizontal)

    distintos = sum(
        1
        for x in range(32)
        for y in range(32)
        if abs(espejada.pixelColor(x, y).alpha() - derecha.pixelColor(x, y).alpha()) > 64
    )
    assert izquierda != derecha
    assert distintos == 0


def test_una_pagina_no_es_media(qt_app):
    media = icons.icon("media-adelante", "#000000").pixmap(QSize(32, 32)).toImage()
    pagina = icons.icon("pagina-adelante", "#000000").pixmap(QSize(32, 32)).toImage()

    assert media != pagina
