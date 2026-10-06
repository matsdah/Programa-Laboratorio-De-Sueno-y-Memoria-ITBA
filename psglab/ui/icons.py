"""Los iconos de la interfaz, dibujados por el programa.

Son los de la barra de navegación, el botón de abrir un registro, que ocupa en
la barra de menú el lugar que antes tenía «Archivo», y el de la aplicación, que
lleva la ventana y los accesos directos que crea el instalador de WSL.

**No hay ningún archivo de icono en el repositorio, y es a propósito.** La
referencia visual de este refactor es EDFbrowser, que está bajo GPL-2.0;
copiarle un icono obligaría a relicenciar el proyecto entero, que el pliego pide
MIT. Es exactamente el motivo por el que se eligió PySide6 sobre PyQt, y el
mismo que hace fallar el job de licencias del CI ante cualquier dependencia GPL.

Tomar un set de iconos permisivo —Lucide, Feather, Tabler, todos MIT— habría
sido legítimo, y se descartó por una razón práctica: **son nueve siluetas
hechas de triángulos, barras y un círculo**. Agregar un directorio de
recursos, un `.qrc` y una licencia de terceros más para eso es más
mantenimiento del que ahorran. Dibujarlos
acá los deja además tomando el color del esquema, que un `.png` no puede hacer.

**Reproducir y pausar no pueden parecerse a las flechas de época.** Las
flechas son triángulos llenos, y reproducir —que queda entre ellas desde el
hito 27— lleva el triángulo dentro de un anillo: en una fila de siete, dos
triángulos iguales se confunden. **Era un disco lleno con el triángulo
recortado** hasta el hito 44, cuando el botón dejó de ir relleno con el acento:
sin ese fondo, el disco entintado era una mancha oscura al lado de seis siluetas
finas. Hasta ese hito había además cuatro chevrones
abiertos para mover la página, que se sacaron con sus botones.

Los iconos se dibujan **en el momento**, con el color que se les pida. No se
cachean: se los pide una vez por botón al construir la barra, y volver a
dibujarlos al cambiar de esquema es lo que hace que sigan legibles sobre el
fondo nuevo.

Cubre del pliego: ningún ID. Es presentación.
"""

import math
from typing import Final

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap

from psglab.utils.errors import UnknownIconError

#: Lado del icono en píxeles. Los iconos se dibujan sobre este lienzo y Qt los
#: escala al tamaño del botón; se elige grande para que escalar hacia abajo no
#: los deje dentados.
LADO: Final[int] = 64

#: Qué fracción del lienzo ocupa el dibujo. El resto es margen: un triángulo que
#: toca los bordes se ve más grande que una barra que también los toca, y la
#: barra queda visualmente más chica que el resto.
_MARGEN: Final[float] = 0.18

#: Los nombres que este módulo sabe dibujar. Están acá y no sólo en el `if` de
#: `_camino()` para que el error los pueda enumerar.
NOMBRES: Final[tuple[str, ...]] = (
    "primera",
    "anterior",
    "siguiente",
    "ultima",
    "amplitud-mas",
    "amplitud-menos",
    "abrir",
    "reproducir",
    "pausa",
    "grafico",
)


def icon(name: str, color: str) -> QIcon:
    """El icono pedido, del color pedido.

    Args:
        name: uno de `NOMBRES`.
        color: color de la tinta, como lo entiende `QColor`.

    Raises:
        UnknownIconError: si el nombre no es uno de los que sabe dibujar. El
            mensaje los enumera, porque el nombre lo escribe quien arma la
            barra y un error de tipeo es la causa habitual.
    """
    if not isinstance(name, str) or name not in NOMBRES:
        raise UnknownIconError(
            f"No hay ningún icono llamado «{name}».",
            details=f"Los disponibles son: {', '.join(NOMBRES)}.",
        )

    lienzo = QPixmap(LADO, LADO)
    lienzo.fill(Qt.GlobalColor.transparent)

    pintor = QPainter(lienzo)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pintor.setPen(Qt.PenStyle.NoPen)
    pintor.setBrush(QColor(color))
    pintor.drawPath(_camino(name))
    # **Hay que terminar el pintor antes de construir el `QIcon`.** Con el
    # pintor todavía activo sobre el pixmap, Qt avisa por consola y el icono
    # sale vacío en algunas plataformas.
    pintor.end()

    return QIcon(lienzo)


def _camino(name: str) -> QPainterPath:
    """La figura de un icono, en coordenadas del lienzo."""
    borde = LADO * _MARGEN
    util = LADO - 2 * borde

    if name == "anterior":
        return _triangulo(borde, borde, util, hacia_la_derecha=False)
    if name == "siguiente":
        return _triangulo(borde, borde, util, hacia_la_derecha=True)
    if name in ("primera", "ultima"):
        # Un triángulo más angosto, con la barra del lado al que apunta: es el
        # símbolo universal de "ir al extremo" y se lee sin aprenderlo.
        a_la_derecha = name == "ultima"
        ancho_barra = util * 0.18
        ancho_triangulo = util - ancho_barra
        camino = QPainterPath()
        if a_la_derecha:
            camino.addPath(_triangulo(borde, borde, ancho_triangulo, True))
            camino.addRect(
                QRectF(borde + ancho_triangulo, borde, ancho_barra, util)
            )
        else:
            camino.addRect(QRectF(borde, borde, ancho_barra, util))
            camino.addPath(
                _triangulo(borde + ancho_barra, borde, ancho_triangulo, False)
            )
        return camino
    if name == "abrir":
        return _carpeta(borde, util)
    if name == "reproducir":
        return _calado(borde, util, _triangulo_de_reproducir(borde, util))
    if name == "pausa":
        return _calado(borde, util, _barras_de_pausa(borde, util))
    if name == "amplitud-mas":
        return _triangulo_vertical(borde, borde, util, hacia_arriba=True)
    if name == "grafico":
        return _barras(borde, util)
    return _triangulo_vertical(borde, borde, util, hacia_arriba=False)


def _barras(borde: float, util: float) -> QPainterPath:
    """Tres barras de alto creciente sobre una base: «acá va un resultado».

    Es el único icono que no está en un botón: lo usa el cartel de un panel
    vacío, y por eso es la silueta más neutra de todas —no sugiere ninguna
    acción, sólo dice de qué clase de cosa está hablando el cartel—.
    """
    grosor = util * 0.2
    hueco = (util - 3 * grosor) / 2
    base = util * 0.12
    camino = QPainterPath()
    for posicion, fraccion in enumerate((0.42, 0.68, 1.0)):
        alto = (util - base) * fraccion
        camino.addRect(
            QRectF(
                borde + posicion * (grosor + hueco),
                borde + (util - base) - alto,
                grosor,
                alto,
            )
        )
    camino.addRect(QRectF(borde, borde + util - base, util, base * 0.45))
    return camino


def _triangulo(x: float, y: float, lado: float, hacia_la_derecha: bool) -> QPainterPath:
    """Un triángulo apuntando a izquierda o derecha, inscripto en un cuadrado."""
    camino = QPainterPath()
    if hacia_la_derecha:
        camino.moveTo(QPointF(x, y))
        camino.lineTo(QPointF(x + lado, y + lado / 2))
        camino.lineTo(QPointF(x, y + lado))
    else:
        camino.moveTo(QPointF(x + lado, y))
        camino.lineTo(QPointF(x, y + lado / 2))
        camino.lineTo(QPointF(x + lado, y + lado))
    camino.closeSubpath()
    return camino


def _triangulo_vertical(
    x: float, y: float, lado: float, hacia_arriba: bool
) -> QPainterPath:
    """Un triángulo apuntando arriba o abajo, inscripto en un cuadrado."""
    camino = QPainterPath()
    if hacia_arriba:
        camino.moveTo(QPointF(x + lado / 2, y))
        camino.lineTo(QPointF(x + lado, y + lado))
        camino.lineTo(QPointF(x, y + lado))
    else:
        camino.moveTo(QPointF(x, y))
        camino.lineTo(QPointF(x + lado, y))
        camino.lineTo(QPointF(x + lado / 2, y + lado))
    camino.closeSubpath()
    return camino


def _carpeta(borde: float, lado: float) -> QPainterPath:
    """Una carpeta: la pestaña arriba a la izquierda y el cuerpo debajo.

    Es el símbolo con que casi todos los programas dicen "abrir un archivo", y
    por eso reemplaza al rótulo «Archivo» sin tener que aprenderlo. El cuerpo
    es más ancho que alto, como una carpeta de verdad, y queda centrado en el
    lienzo para no verse corrido respecto de las flechas.
    """
    alto = lado * 0.78
    arriba = borde + (lado - alto) / 2
    pestana_alto = alto * 0.18
    radio = lado * 0.06
    camino = QPainterPath()
    camino.addRoundedRect(
        QRectF(borde, arriba, lado * 0.45, pestana_alto * 2), radio, radio
    )
    camino.addRoundedRect(
        QRectF(borde, arriba + pestana_alto, lado, alto - pestana_alto), radio, radio
    )
    # La unión de las dos figuras, para que el borde compartido no quede como
    # una línea sin pintar.
    return camino.simplified()


#: Qué parte del radio ocupa el trazo del anillo de reproducir y pausar.
_GROSOR_DEL_ANILLO: Final[float] = 0.09


def _calado(borde: float, lado: float, figura: QPainterPath) -> QPainterPath:
    """Un anillo con la figura adentro, las dos del mismo color.

    **Era un círculo lleno con la figura recortada** hasta el hito 44, y tenía
    sentido mientras el botón iba relleno con el acento: sobre ese fondo, el
    disco entintado era la silueta y el hueco se leía como el símbolo. Al
    quedar el botón como los otros seis, el mismo dibujo pasó a ser una mancha
    oscura con un triángulo diminuto adentro, que es justo lo que el usuario
    señaló.

    **El anillo conserva lo que el disco resolvía**, que está en el docstring
    del módulo: en una fila de siete, reproducir no puede ser un triángulo más
    entre las dos flechas de época. Con el anillo la silueta sigue siendo
    redonda y el símbolo se lee sin aprenderlo.

    El agujero sale de la regla de relleno par-impar, que es la que usa
    `QPainterPath` por omisión: un punto entre las dos elipses queda dentro de
    un solo contorno y se pinta; uno del centro, dentro de dos, y no.
    """
    grosor = lado * _GROSOR_DEL_ANILLO
    camino = QPainterPath()
    camino.setFillRule(Qt.FillRule.OddEvenFill)
    camino.addEllipse(QRectF(borde, borde, lado, lado))
    camino.addEllipse(
        QRectF(borde + grosor, borde + grosor, lado - 2 * grosor, lado - 2 * grosor)
    )
    camino.addPath(figura)
    return camino


def _triangulo_de_reproducir(borde: float, lado: float) -> QPainterPath:
    """El triángulo de «reproducir», corrido a la derecha del centro.

    Un triángulo centrado por su caja se ve corrido a la izquierda, porque su
    peso está en el lado vertical: se lo corre para que se vea centrado.
    """
    alto = lado * 0.46
    ancho = alto * 0.87
    x = borde + (lado - ancho) / 2 + ancho * 0.12
    y = borde + (lado - alto) / 2
    camino = QPainterPath()
    camino.moveTo(QPointF(x, y))
    camino.lineTo(QPointF(x + ancho, y + alto / 2))
    camino.lineTo(QPointF(x, y + alto))
    camino.closeSubpath()
    return camino


def _barras_de_pausa(borde: float, lado: float) -> QPainterPath:
    """Las dos barras de «pausa», centradas."""
    alto = lado * 0.44
    ancho = lado * 0.12
    hueco = lado * 0.12
    x = borde + (lado - (2 * ancho + hueco)) / 2
    y = borde + (lado - alto) / 2
    camino = QPainterPath()
    camino.addRect(QRectF(x, y, ancho, alto))
    camino.addRect(QRectF(x + ancho + hueco, y, ancho, alto))
    return camino


# -- El icono de la aplicación ------------------------------------------------

#: Los tamaños en que se dibuja el icono de la aplicación. **Cada uno se dibuja a
#: su medida** y no se escala desde el grande: achicado, el trazo de la onda
#: queda por debajo de un píxel y la luna se desdibuja.
TAMANOS_DE_LA_APLICACION: Final[tuple[int, ...]] = (16, 24, 32, 48, 64, 128, 256)

#: El lado más chico que tiene sentido pedir: es el de la barra de tareas.
_LADO_MINIMO_DE_LA_APLICACION: Final[int] = 16

#: La luna. Es el único color del icono que no sale del esquema Sereno.
_AMBAR_DE_LA_LUNA: Final[str] = "#f2c14e"


def app_icon_image(side: int) -> QImage:
    """El icono de la aplicación, de `side` × `side` píxeles.

    Una luna creciente en ámbar sobre una onda clara, en un cuadrado de esquinas
    redondeadas con el acento de Sereno: sueño y señal. **Los colores son fijos
    y no siguen el esquema elegido**, porque el icono también vive en accesos
    directos que el sistema dibuja una sola vez y no se enteran de que el
    usuario pasó a Nocturno. Fuera del cuadrado el fondo es transparente.

    Lo usan la ventana, por `app_icon()`, y el instalador de WSL, que lo guarda
    como PNG y como ICO para los accesos directos: por eso devuelve una
    `QImage`, que se puede guardar sin una aplicación con ventanas.

    Raises:
        UnknownIconError: si `side` no es un entero o es menor que 16.
    """
    if isinstance(side, bool) or not isinstance(side, int) or side < _LADO_MINIMO_DE_LA_APLICACION:
        raise UnknownIconError(
            f"No se puede dibujar el icono de la aplicación de «{side}» píxeles.",
            details=f"El lado tiene que ser un entero de {_LADO_MINIMO_DE_LA_APLICACION} o más.",
        )

    from psglab.ui.theme import SERENO

    lado = float(side)
    imagen = QImage(side, side, QImage.Format.Format_ARGB32_Premultiplied)
    imagen.fill(Qt.GlobalColor.transparent)

    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    borde = lado * 0.06
    fondo = QPainterPath()
    fondo.addRoundedRect(
        QRectF(borde, borde, lado - 2 * borde, lado - 2 * borde), lado * 0.2, lado * 0.2
    )
    pintor.fillPath(fondo, QColor(SERENO.accent))

    disco = QPainterPath()
    disco.addEllipse(QPointF(lado * 0.40, lado * 0.36), lado * 0.17, lado * 0.17)
    mordida = QPainterPath()
    mordida.addEllipse(QPointF(lado * 0.48, lado * 0.30), lado * 0.15, lado * 0.15)
    pintor.fillPath(disco.subtracted(mordida), QColor(_AMBAR_DE_LA_LUNA))

    pluma = QPen(QColor(SERENO.background), max(lado * 0.05, 1.5))
    pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
    pluma.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pintor.setPen(pluma)
    pintor.drawPath(_onda_de_la_aplicacion(lado))
    pintor.end()
    return imagen


def app_icon() -> QIcon:
    """El icono de la aplicación en todos sus tamaños, para la ventana."""
    icono = QIcon()
    for lado in TAMANOS_DE_LA_APLICACION:
        icono.addPixmap(QPixmap.fromImage(app_icon_image(lado)))
    return icono


def _onda_de_la_aplicacion(lado: float) -> QPainterPath:
    """Tres ondulaciones que crecen hacia el medio, en la mitad de abajo."""
    x0, x1, centro = lado * 0.18, lado * 0.82, lado * 0.70
    puntos = 160
    camino = QPainterPath()
    for k in range(puntos + 1):
        t = k / puntos
        x = x0 + t * (x1 - x0)
        envolvente = 0.6 + 0.4 * math.sin(t * math.pi)
        y = centro - lado * 0.07 * math.sin(t * 2 * math.pi * 3.0) * envolvente
        if k == 0:
            camino.moveTo(x, y)
        else:
            camino.lineTo(x, y)
    return camino
