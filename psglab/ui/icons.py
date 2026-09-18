"""Los iconos de la interfaz, dibujados por el programa.

Son los de la barra de navegación y el botón de abrir un registro, que ocupa en
la barra de menú el lugar que antes tenía «Archivo».

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
hito 27— lleva el triángulo calado en un círculo: en una fila de siete, dos
triángulos iguales se confunden. Hasta ese hito había además cuatro chevrones
abiertos para mover la página, que se sacaron con sus botones.

Los iconos se dibujan **en el momento**, con el color que se les pida. No se
cachean: se los pide una vez por botón al construir la barra, y volver a
dibujarlos al cambiar de esquema es lo que hace que sigan legibles sobre el
fondo nuevo.

Cubre del pliego: ningún ID. Es presentación.
"""

from typing import Final

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap

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
    return _triangulo_vertical(borde, borde, util, hacia_arriba=False)


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


def _calado(borde: float, lado: float, figura: QPainterPath) -> QPainterPath:
    """Un círculo lleno con la figura recortada adentro.

    El recorte sale de la regla de relleno par-impar, que es la que usa
    `QPainterPath` por omisión: donde la figura se superpone al círculo, el
    punto queda dentro de dos contornos y no se pinta.
    """
    camino = QPainterPath()
    camino.setFillRule(Qt.FillRule.OddEvenFill)
    camino.addEllipse(QRectF(borde, borde, lado, lado))
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
