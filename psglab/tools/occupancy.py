"""Herramienta de ocupación de la página.

El usuario dibuja líneas con el mouse sobre la ventana y la herramienta
calcula qué porcentaje del ancho de la pantalla ocupan, sumando el aporte de
todas.

La definición del pliego es una **proyección sobre el eje horizontal**, no el
largo de la línea:

    - una línea vertical ocupa 0 %
    - una línea de borde izquierdo a borde derecho ocupa 100 %
    - una línea horizontal de media pantalla ocupa 50 %
    - la misma línea en diagonal ocupa menos que 50 %, porque lo que cuenta
      es su sombra sobre el eje horizontal

Es decir: para una línea de extremos (x1, y1) y (x2, y2), el aporte es
|x2 - x1| dividido por el ancho de la ventana. El ángulo no entra en la
cuenta como tal; entra a través de la diferencia de las x.

Cubre del pliego: V1_F, V2_F, V3_F, V4_F, V5_F de "Herramienta de ocupación
de la página".
"""

from collections.abc import Sequence
from dataclasses import dataclass

from psglab.config import OCCUPANCY_COUNTS_OVERLAP_ONCE
from psglab.core.session import Session
from psglab.core.windows import seconds_to_window_fraction, window_fraction_to_seconds
from psglab.tools.base import Overlay, SegmentOverlay, ViewerTool
from psglab.tools.registry import register_tool

#: Cuan cerca de una linea hay que hacer clic para borrarla, en microvoltios.
#: Es una afinacion de interfaz y no una regla del pliego: el numero que hace
#: comodo el gesto se termina de decidir con la ventana abierta, en el hito 6.
TOLERANCIA_DE_CLIC_UV: float = 10.0


@dataclass(frozen=True)
class OccupancyLine:
    """Una línea dibujada por el usuario.

    **`x` se guarda en fracción del ancho de la ventana, de 0 a 1**, y no en
    píxeles: así el porcentaje sigue siendo correcto si el usuario redimensiona
    la ventana del programa.

    **`y` se guarda en microvoltios**, tal como lo entrega el mouse, y los dos
    ejes no usan la misma unidad a propósito. Pasar `y` a fracción del alto
    exigiría saber con qué escala está dibujado el canal —`Session.scale_uv()`
    es por canal— y `SegmentOverlay` no lleva ninguno. Como **`y` no entra en la
    medición**, que es una proyección sobre el eje horizontal, convertirlo sería
    pagar una imprecisión a cambio de nada: sólo sirve para volver a dibujar la
    línea donde el usuario la trazó.

    **Ojo con la unidad.** Los métodos de mouse de `ViewerTool` reciben `x` en
    **segundos** (0 a 30), que no es lo que esta clase guarda. La conversión la
    hace `core.windows.seconds_to_window_fraction()` y hay que aplicarla en los
    métodos de mouse, antes de construir la línea. Si se le pasan segundos
    crudos, `horizontal_fraction` devuelve hasta 30 en vez de 1 y
    `line_percentage` informa 3000 %: un número plausible y equivocado, que no
    falla de forma visible.

    Es inmutable (`frozen=True`) para poder guardarla en un conjunto y para que
    borrar "la línea que está debajo del clic" sea inequívoco.
    """

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def horizontal_fraction(self) -> float:
        """Fracción del ancho que ocupa la proyección de la línea (0 a 1).

        El sentido del trazo no cambia el resultado: se dibuje de izquierda a
        derecha o al revés, la sombra sobre el eje es la misma.
        """
        return abs(self.x2 - self.x1)


@register_tool
class OccupancyTool(ViewerTool):
    """Medidor de ocupación horizontal por líneas dibujadas a mano."""

    name = "occupancy"
    label = "Ocupación"
    description = "Dibujar líneas y medir qué porcentaje del ancho ocupan"

    def __init__(self) -> None:
        self._session: Session | None = None
        self._activa: bool = False
        self._lineas: list[OccupancyLine] = []
        #: La que el usuario está arrastrando ahora mismo. Se dibuja, pero no
        #: cuenta para el total hasta que suelte el botón.
        self._en_curso: OccupancyLine | None = None

    def activate(self, session: Session) -> None:
        """Activa el modo de dibujo de líneas (V1_F)."""
        self._session = session
        self._activa = True
        self.notify_changed()

    def deactivate(self) -> None:
        """Sale del modo de dibujo. Las líneas dibujadas se conservan.

        Conservarlas es deliberado: el usuario puede querer mirar la señal sin
        la herramienta activa y volver, y perder las mediciones al desactivar
        sería una sorpresa desagradable. Las borra el cambio de ventana (V5_F),
        que es cuando dejan de significar algo.
        """
        self._activa = False
        self._en_curso = None
        self.notify_changed()

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Empieza una línea nueva, o borra una existente si se hizo clic encima.

        El pliego pide las dos cosas con el mismo gesto (V1_F y V5_F): si el
        clic cae sobre una línea ya dibujada, la borra; si no, empieza una
        línea nueva.
        """
        if not self._activa:
            return
        debajo = self._linea_debajo(x, y)
        if debajo is not None:
            self._lineas.remove(debajo)
            self._en_curso = None
            self.notify_changed()
            return

        fraccion = seconds_to_window_fraction(x)
        self._en_curso = OccupancyLine(fraccion, y, fraccion, y)
        self.notify_changed()

    def on_mouse_move(self, x: float, y: float) -> None:
        """Extiende la línea en curso mientras el usuario arrastra.

        Convierte los segundos que recibe a fracción de ventana con
        `core.windows.seconds_to_window_fraction()`: es la conversión que
        `OccupancyLine` exige y sin la que informaría 3000 %.
        """
        if self._en_curso is None:
            return
        self._en_curso = OccupancyLine(
            self._en_curso.x1,
            self._en_curso.y1,
            seconds_to_window_fraction(x),
            y,
        )
        self.notify_changed()

    def on_mouse_release(self, x: float, y: float, button: str) -> None:
        """Cierra la línea y actualiza el porcentaje mostrado (V3_F).

        Una línea sin ancho no se guarda: es el clic que no arrastró nada.
        Aportaría 0 % a la suma, pero ensuciaría la lista y el dibujo.
        """
        if self._en_curso is None:
            return
        terminada, self._en_curso = self._en_curso, None
        if terminada.horizontal_fraction > 0:
            self._lineas.append(terminada)
        self.notify_changed()

    def on_window_changed(self, window_index: int) -> None:
        """Borra las líneas al cambiar de ventana (V5_F).

        Las líneas miden algo de la ventana que se estaba mirando, así que no
        tienen sentido en la siguiente.
        """
        self.clear()

    def add_line(self, line: OccupancyLine) -> None:
        """Agrega una línea ya construida.

        Existe además del dibujo con el mouse para poder testear el cálculo del
        porcentaje sin simular gestos del mouse.
        """
        self._lineas.append(line)
        self.notify_changed()

    def lines(self) -> list[OccupancyLine]:
        """Líneas dibujadas en la ventana actual.

        Devuelve una copia: prestarle la lista interna a quien la consulte lo
        dejaría agregar y quitar líneas sin pasar por la herramienta, y el total
        mostrado dejaría de corresponderse con lo dibujado.
        """
        return list(self._lineas)

    def line_percentage(self, line: OccupancyLine) -> float:
        """Porcentaje de ocupación horizontal de una línea (V2_F)."""
        return line.horizontal_fraction * 100.0

    def total_percentage(
        self,
        counts_overlap_once: bool = OCCUPANCY_COUNTS_OVERLAP_ONCE,
    ) -> float:
        """Porcentaje sumado de todas las líneas de la ventana (V4_F).

        Args:
            counts_overlap_once: si dos líneas se pisan en horizontal, True
                cuenta la zona compartida una sola vez —hay que unir los
                intervalos antes de sumar— y False suma los aportes por
                separado. Por defecto, el de `config`.

        Confirmado con el cliente: se suman los aportes sin descontar la zona
        compartida, que es "sumar la distancia horizontal total" leído al pie
        de la letra. **Con ese criterio el total puede pasar del 100 %**, y eso
        es lo buscado, no un error de cálculo: la interfaz tiene que poder
        mostrarlo sin romperse. Ver `config.OCCUPANCY_COUNTS_OVERLAP_ONCE`.
        """
        if not counts_overlap_once:
            return sum(self.line_percentage(linea) for linea in self._lineas)

        # La otra variante: unir los intervalos antes de sumar, para que la zona
        # que dos líneas comparten cuente una sola vez. Se recorren en orden de
        # comienzo y se van fundiendo los que se tocan.
        intervalos = sorted(
            (min(linea.x1, linea.x2), max(linea.x1, linea.x2))
            for linea in self._lineas
        )
        total = 0.0
        inicio_actual: float | None = None
        fin_actual = 0.0
        for inicio, fin in intervalos:
            if inicio_actual is None:
                inicio_actual, fin_actual = inicio, fin
            elif inicio <= fin_actual:
                fin_actual = max(fin_actual, fin)
            else:
                total += fin_actual - inicio_actual
                inicio_actual, fin_actual = inicio, fin
        if inicio_actual is not None:
            total += fin_actual - inicio_actual
        return total * 100.0

    def clear(self) -> None:
        """Borra todas las líneas."""
        self._lineas.clear()
        self._en_curso = None
        self.notify_changed()

    def overlays(self) -> Sequence[Overlay]:
        """Las líneas dibujadas, más la que el usuario está arrastrando.

        Se devuelven en segundos y microvoltios, que es lo que entiende el
        visualizador; internamente se guardan en fracción, que es lo que hace
        correcto el porcentaje. La vuelta la hace
        `core.windows.window_fraction_to_seconds()`.
        """
        dibujables = [*self._lineas]
        if self._en_curso is not None:
            dibujables.append(self._en_curso)
        return tuple(
            SegmentOverlay(
                tool_name=self.name,
                x1_seconds=window_fraction_to_seconds(linea.x1),
                y1_uv=linea.y1,
                x2_seconds=window_fraction_to_seconds(linea.x2),
                y2_uv=linea.y2,
            )
            for linea in dibujables
        )

    def _linea_debajo(self, x_seconds: float, y_uv: float) -> OccupancyLine | None:
        """La línea que está debajo del clic, si hay alguna (V5_F).

        Se compara la altura del clic contra la de la línea **en esa misma
        posición horizontal**, interpolando. Con un rectángulo envolvente, una
        diagonal larga se borraría haciendo clic muy lejos de donde está
        dibujada.

        La tolerancia es una afinación de interfaz y no una regla del pliego:
        ver `TOLERANCIA_DE_CLIC_UV`.
        """
        fraccion = seconds_to_window_fraction(x_seconds)
        candidatas = []
        for linea in self._lineas:
            izquierda, derecha = sorted((linea.x1, linea.x2))
            if not izquierda <= fraccion <= derecha:
                continue
            if linea.x2 == linea.x1:
                altura = (linea.y1 + linea.y2) / 2
            else:
                avance = (fraccion - linea.x1) / (linea.x2 - linea.x1)
                altura = linea.y1 + avance * (linea.y2 - linea.y1)
            candidatas.append((abs(altura - y_uv), linea))

        if not candidatas:
            return None
        distancia, linea = min(candidatas, key=lambda par: par[0])
        return linea if distancia <= TOLERANCIA_DE_CLIC_UV else None
