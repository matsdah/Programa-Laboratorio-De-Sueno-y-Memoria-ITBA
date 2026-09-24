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


def test_reproducir_es_un_anillo_y_no_un_disco(qt_app):
    """**Era un disco lleno con el triángulo recortado** hasta el hito 44, y
    servía mientras el botón iba relleno con el acento: sobre ese fondo el
    disco era la silueta y el hueco, el símbolo. Con el botón como los otros
    seis pasó a ser una mancha oscura, que es lo que el usuario señaló.

    Se miran tres puntos, que es lo que distingue un anillo de un disco y de
    un triángulo suelto: el trazo entintado, el aire entre el trazo y el
    símbolo, y el símbolo. Si la regla de relleno no fuera par-impar, los tres
    estarían pintados y el icono sería un disco.
    """
    imagen = icons.icon("reproducir", "#000000").pixmap(
        QSize(icons.LADO, icons.LADO)
    ).toImage()
    medio = icons.LADO // 2

    trazo = imagen.pixelColor(medio, int(icons.LADO * 0.19))
    aire = imagen.pixelColor(medio, int(icons.LADO * 0.28))
    simbolo = imagen.pixelColor(medio, medio)

    assert trazo.alpha() > 0
    assert aire.alpha() == 0
    assert simbolo.alpha() > 0


@pytest.mark.parametrize(
    "nombre", ["pagina-atras", "media-atras", "media-adelante", "pagina-adelante"]
)
def test_los_chevrones_de_pagina_ya_no_existen(nombre: str):
    """Se sacaron con sus botones en el hito 27. Un icono que nadie pide es un
    dibujo que nadie ve, y dejarlo haría creer que la barra todavía lo usa."""
    with pytest.raises(PsgLabError):
        icons.icon(nombre, "#000000")
