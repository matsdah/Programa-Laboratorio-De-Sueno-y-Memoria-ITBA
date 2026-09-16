"""La página visible del registro: qué tramo se está mirando.

Hasta el refactor de la interfaz había **una** noción horizontal, la ventana de
30 s del pliego, que era cuatro cosas a la vez: la unidad de scoring, la página
de dibujo, el origen de coordenadas de las herramientas y el denominador de la
ocupación. Este módulo separa dos de ellas:

- **Época de scoring** (`WINDOW_SECONDS`, 30 s) — la unidad de `Scoring`, la
  base de `count_windows()`, del histograma y de la Übersicht. **No cambia.**
- **Página visible** (`Viewport`) — qué tramo se dibuja. Libre, de diez
  milisegundos al registro entero.

Las dos conviven en un tercer sistema, que es el que las hace compatibles:
**segundos absolutos desde el inicio del registro**.

## Por qué es un valor inmutable y no un objeto que se muta

Si `Session.viewport` devolviera algo mutable, `session.viewport.zoom(2)`
cambiaría el estado **sin avisarle a nadie**, que es exactamente el fallo que
`Session.add_window_listener()` documenta querer impedir. Devolver una copia
tampoco alcanza: el llamador mutaría la copia y no pasaría nada, en silencio.

Siendo inmutable, la única forma de cambiar la página es pasar por
`Session.set_viewport()`, que es el único lugar que avisa. Es además el gusto
de la casa: `Overlay`, `OccupancyLine`, `OverviewWindow` y `Channel` son todos
congelados, y el de `OccupancyLine` justifica la decisión con el mismo
argumento.

## Por qué segundos y no muestras

La escala que el usuario elige está en segundos —"÷2", "×2", "una hora por
página"—. En muestras, cada división de un span impar mete un redondeo que hay
que definir en cada operación; en segundos hay **un solo** redondeo, el de
`core/windows.py` al pedir el tramo, que ya está definido y testeado contra
frecuencias no redondas.

Cubre del pliego: ningún ID. El pliego fija la ventana de 30 s y la cubre
`core/windows.py`; esto es la extensión que agregó el refactor de la interfaz.
"""

from dataclasses import dataclass, replace

from psglab.config import MIN_VIEW_SECONDS
from psglab.utils.errors import InvalidViewportError
from psglab.utils.validation import check_finite


def _check_seconds(nombre: str, valor: float) -> None:
    """Rechaza un valor con el que no se puede hacer aritmética de tiempo.

    Hace falta **antes** de cualquier cuenta, y no alcanza con que `clamped()`
    valide al final: `centro - span / 2` con una cadena o un `None` eleva
    `TypeError` una línea antes de llegar ahí, y ése atraviesa el `except` de
    la ventana principal y sale como traza de Python.

    Raises:
        InvalidViewportError: si no es un número finito.
    """
    check_finite(
        valor,
        error=InvalidViewportError,
        message="No se pudo cambiar la porción de registro que se está mostrando.",
        details=f"{nombre} tiene que ser un número finito; se recibió {valor!r}.",
    )


@dataclass(frozen=True)
class Viewport:
    """El tramo del registro que se está mirando.

    Attributes:
        start_seconds: dónde empieza la página, en segundos desde el inicio del
            registro.
        span_seconds: cuánto dura la página.
        duration_seconds: cuánto dura el registro entero. Se guarda acá y no se
            consulta al `Recording` para que este objeto sea autosuficiente:
            recortar una página necesita saber contra qué, y un valor que hay
            que ir a buscar afuera convierte cada transformación en una
            consulta más.
    """

    start_seconds: float
    span_seconds: float
    duration_seconds: float

    def __post_init__(self) -> None:
        """Rechaza una página con la que no se puede dibujar.

        Raises:
            InvalidViewportError: si alguno de los tres no es un número finito,
                si la página no tiene ancho positivo, si el registro no tiene
                duración positiva, o si la página empieza antes del registro.
        """
        for nombre, valor in (
            ("start_seconds", self.start_seconds),
            ("span_seconds", self.span_seconds),
            ("duration_seconds", self.duration_seconds),
        ):
            check_finite(
                valor,
                error=InvalidViewportError,
                message="La porción de registro que se pidió mostrar no es válida.",
                details=f"{nombre} tiene que ser un número finito; se recibió {valor!r}.",
            )
        if self.span_seconds <= 0:
            raise InvalidViewportError(
                "La porción de registro que se pidió mostrar no tiene ancho.",
                details=f"span_seconds = {self.span_seconds}; tiene que ser mayor que cero.",
            )
        if self.duration_seconds <= 0:
            raise InvalidViewportError(
                "El registro no tiene duración, así que no hay nada que mostrar.",
                details=f"duration_seconds = {self.duration_seconds}.",
            )
        if self.start_seconds < 0:
            raise InvalidViewportError(
                "La porción de registro que se pidió mostrar empieza antes del registro.",
                details=f"start_seconds = {self.start_seconds}.",
            )

    # -- Derivados. Ninguno se almacena: dos fuentes de verdad se desincronizan.

    @property
    def end_seconds(self) -> float:
        """Dónde termina la página."""
        return self.start_seconds + self.span_seconds

    @property
    def center_seconds(self) -> float:
        """El segundo que queda en el medio de la pantalla."""
        return self.start_seconds + self.span_seconds / 2

    @property
    def shows_whole_recording(self) -> bool:
        """Si la página cubre el registro entero.

        Lo consulta el visualizador para decidir si vale la pena avisar que el
        dibujo va a tardar, y el menú para poder tildar "Registro entero".
        """
        return self.start_seconds <= 0 and self.span_seconds >= self.duration_seconds

    # -- Construcción con recorte -------------------------------------------

    @classmethod
    def clamped(
        cls,
        start_seconds: float,
        span_seconds: float,
        duration_seconds: float,
        minimum_span_seconds: float = MIN_VIEW_SECONDS,
    ) -> "Viewport":
        """Arma una página recortándola contra el registro.

        Es el **único lugar que recorta**, igual que `Session.set_scale_uv()` lo
        es para la escala vertical: las transformaciones de abajo delegan todas
        acá en vez de repetir la comprobación, para que no puedan discrepar.

        El span se recorta primero y el comienzo después, en ese orden: al revés,
        un comienzo válido para la página vieja puede dejar de serlo con la
        nueva y quedaría fuera del registro.

        Raises:
            InvalidViewportError: sólo por lo que **no** se puede recortar; ver
                `__post_init__`. Un NaN llega hasta acá porque `min` y `max` lo
                propagan en silencio, así que se comprueba antes de recortar.
        """
        for nombre, valor in (
            ("start_seconds", start_seconds),
            ("span_seconds", span_seconds),
            ("duration_seconds", duration_seconds),
            ("minimum_span_seconds", minimum_span_seconds),
        ):
            check_finite(
                valor,
                error=InvalidViewportError,
                message="La porción de registro que se pidió mostrar no es válida.",
                details=f"{nombre} tiene que ser un número finito; se recibió {valor!r}.",
            )

        piso = max(minimum_span_seconds, 0.0)
        if piso <= 0:
            raise InvalidViewportError(
                "La página mínima tiene que ser mayor que cero.",
                details=f"minimum_span_seconds = {minimum_span_seconds}.",
            )
        # Un registro más corto que la página mínima existe —un BrainVision de
        # prueba dura 7,9 s— y mostrarlo entero es lo correcto, así que el piso
        # no puede pasar de la duración.
        span = min(max(span_seconds, min(piso, duration_seconds)), duration_seconds)
        inicio = min(max(start_seconds, 0.0), max(0.0, duration_seconds - span))
        return cls(inicio, span, duration_seconds)

    # -- Transformaciones. Todas devuelven una página nueva y recortada. -----

    def with_span(self, span_seconds: float) -> "Viewport":
        """Otra duración de página, **conservando el centro**.

        Conservar el centro y no el comienzo es lo que hace que acercarse se
        sienta como acercarse: con el comienzo fijo, cada `÷2` corre hacia la
        derecha lo que se estaba mirando.
        """
        _check_seconds("span_seconds", span_seconds)
        centro = self.center_seconds
        return Viewport.clamped(
            centro - span_seconds / 2, span_seconds, self.duration_seconds
        )

    def with_start(self, start_seconds: float) -> "Viewport":
        """La misma página empezando en otro segundo."""
        return Viewport.clamped(
            start_seconds, self.span_seconds, self.duration_seconds
        )

    def with_center(self, center_seconds: float) -> "Viewport":
        """La misma página centrada en otro segundo."""
        _check_seconds("center_seconds", center_seconds)
        return self.with_start(center_seconds - self.span_seconds / 2)

    def zoomed(self, factor: float) -> "Viewport":
        """Multiplica la duración de la página. "Escala ÷2" es `zoomed(0.5)`.

        Raises:
            InvalidViewportError: si el factor no es finito y mayor que cero.
        """
        check_finite(
            factor,
            error=InvalidViewportError,
            message="No se pudo cambiar la escala de tiempo.",
            details=f"El factor tiene que ser un número finito; se recibió {factor!r}.",
        )
        if factor <= 0:
            raise InvalidViewportError(
                "No se pudo cambiar la escala de tiempo.",
                details=f"El factor tiene que ser mayor que cero; se recibió {factor}.",
            )
        return self.with_span(self.span_seconds * factor)

    def panned(self, delta_seconds: float) -> "Viewport":
        """Desplaza la página, sin cambiar su duración."""
        _check_seconds("delta_seconds", delta_seconds)
        return self.with_start(self.start_seconds + delta_seconds)

    def whole_recording(self) -> "Viewport":
        """La página que muestra el registro entero."""
        return Viewport.clamped(0.0, self.duration_seconds, self.duration_seconds)

    def containing(self, start_seconds: float, end_seconds: float) -> "Viewport":
        """La misma página, desplazada **lo mínimo** para que un tramo entre.

        **Devuelve `self` si el tramo ya está dentro, y eso es todo el punto**:
        es lo que hace que avanzar de época con una página de cuatro horas no
        mueva la pantalla. Con 480 épocas visibles, apretar la flecha derecha
        mueve el resaltado y no sacude el dibujo.

        Si el tramo es más largo que la página, se alinea su comienzo con el de
        la página: mostrar la primera mitad de la época que se va a scorear es
        más útil que mostrar el final de la anterior.

        Raises:
            InvalidViewportError: si alguno de los dos extremos no es un número
                finito. **Hay que comprobarlo antes de comparar**: `>=` contra
                `None` o contra una cadena eleva `TypeError`, que atraviesa el
                `except` de la ventana principal y sale como traza.
        """
        for nombre, valor in (
            ("start_seconds", start_seconds),
            ("end_seconds", end_seconds),
        ):
            check_finite(
                valor,
                error=InvalidViewportError,
                message="No se pudo ubicar en pantalla la porción de registro pedida.",
                details=f"{nombre} tiene que ser un número finito; se recibió {valor!r}.",
            )
        if start_seconds >= self.start_seconds and end_seconds <= self.end_seconds:
            return self
        if end_seconds - start_seconds >= self.span_seconds:
            return self.with_start(start_seconds)
        if start_seconds < self.start_seconds:
            return self.with_start(start_seconds)
        return self.with_start(end_seconds - self.span_seconds)

    def for_duration(self, duration_seconds: float) -> "Viewport":
        """La misma página sobre un registro de otra duración.

        La usa `Session.set_recording()`: filtrar o derivar puede cambiar la
        duración por debajo de una época sin que `n_windows` cambie, y una
        página que se pasa del final dibujaría un tramo que no existe.
        """
        return Viewport.clamped(
            self.start_seconds, self.span_seconds, duration_seconds
        )

    def replaced(self, **cambios: float) -> "Viewport":
        """Otra página con algunos campos cambiados, sin recortar.

        Existe para los tests y para quien necesite construir una página exacta.
        **El camino normal es `clamped()` y las transformaciones**, que recortan.
        """
        return replace(self, **cambios)
