"""Anotación de eventos sobre la señal.

El usuario selecciona un tramo con el mouse, elige una clase de evento de la
lista (Arousal, complejo K, spindle, ...) o crea una clase nueva con el
nombre que quiera, y el tramo queda marcado con una banda de color que ocupa
todo el alto de la ventana de scoring.

Resuelve una de las carencias que motivan el proyecto: en los programas
actuales del laboratorio no se puede anotar la señal.

Cubre del pliego: V1_F de "Anotación de la señal".
"""

from collections.abc import Sequence

from psglab.core.annotations import Annotation
from psglab.utils.errors import InvalidAnnotationError
from psglab.core.session import Session
from psglab.tools.base import Overlay, SpanOverlay, ViewerTool
from psglab.tools.registry import register_tool
from psglab.core.windows import (
    sample_to_seconds_absolute,
    seconds_to_sample_absolute,
    seconds_to_samples,
)


@register_tool
class AnnotatorTool(ViewerTool):
    """Selección de eventos y asignación de clase."""

    name = "annotator"
    label = "Anotar"
    description = "Marcar un evento en la señal y asignarle una clase"

    def __init__(self) -> None:
        self._session: Session | None = None
        self._activa: bool = False
        #: Extremos de la selección en curso, en segundos desde el inicio de la
        #: ventana. `None` cuando el usuario no está arrastrando.
        self._desde: float | None = None
        self._hasta: float | None = None
        #: El tramo ya soltado y todavía sin clase, en muestras del registro.
        #: Lo consulta la ventana principal para preguntar la clase y después
        #: llamar a `create_annotation()`.
        self._pendiente: tuple[int, int] | None = None

    def activate(self, session: Session) -> None:
        """Activa el modo de anotación."""
        self._session = session
        self._activa = True
        self.notify_changed()

    def deactivate(self) -> None:
        """Sale del modo de anotación. Las anotaciones hechas se conservan.

        Viven en el `AnnotationSet` de la sesión, no acá: la herramienta es el
        gesto, no el dato. Por eso desactivarla no borra nada.

        **Suelta la sesión**, como la lupa y la banda de amplitud. Conservarla
        mantenía vivo el registro anterior después de abrir otro, que en una
        noche entera son gigabytes. Apagada no la necesita: las bandas las
        dibuja la ventana con `annotation_bands()` y su propia sesión.
        """
        self._session = None
        self._activa = False
        self._desde = self._hasta = None
        self._pendiente = None
        self.notify_changed()

    def on_mouse_press(
        self, x: float, y: float, button: str, channel_name: str | None = None
    ) -> None:
        """Empieza la selección del evento."""
        if not self._activa or button != "left":
            return
        self._desde = self._hasta = x
        self._pendiente = None
        self.notify_changed()

    def on_mouse_move(
        self, x: float, y: float, channel_name: str | None = None
    ) -> None:
        """Extiende la selección mientras el usuario arrastra."""
        if self._desde is None:
            return
        self._hasta = x
        self.notify_changed()

    def on_mouse_release(
        self, x: float, y: float, button: str, channel_name: str | None = None
    ) -> None:
        """Cierra la selección y pide la clase del evento.

        El ancho de la banda es el que seleccionó el usuario, no uno fijo: un
        arousal y un complejo K duran cosas muy distintas.

        **La herramienta no abre ningún diálogo**: no conoce Qt y no puede. Deja
        el tramo listo en `pending_selection_samples` y avisa; la ventana
        principal pregunta la clase y llama a `create_annotation()`. Es lo mismo
        que hace con el resto de las herramientas, y es lo que permite testear
        el gesto entero sin abrir una ventana.
        """
        if self._desde is None or self._session is None or button != "left":
            return
        desde, hasta = sorted((self._desde, x))
        self._desde = self._hasta = None

        fs = self._session.recording.sampling_rate
        # **Segundos absolutos.** Antes eran segundos desde el inicio de la
        # epoca y habia que sumarlos sobre su borde, que es la cuenta que
        # `seconds_to_sample()` documenta con las 240 de 960 ventanas que
        # fallaban a 256,125 Hz. Sin borde de epoca en el medio, esa deriva es
        # estructuralmente imposible: hay un solo redondeo.
        inicio = seconds_to_sample_absolute(desde, fs)
        fin = seconds_to_sample_absolute(hasta, fs)
        # Una selección sin ancho no es un evento: el pliego pide marcarlo con
        # una banda, y `AnnotationSet` rechaza la duración cero por lo mismo.
        self._pendiente = (inicio, fin - inicio) if fin > inicio else None
        self.notify_changed()

    @property
    def pending_selection_samples(self) -> tuple[int, int] | None:
        """El tramo seleccionado y todavía sin clase, como (inicio, duración).

        En muestras del registro, que es la unidad en la que se guardan las
        anotaciones. Es `None` si el usuario no seleccionó nada, o si lo que
        seleccionó no tiene ancho.
        """
        return self._pendiente

    def create_annotation(self, label: str, onset_sample: int, duration_samples: int) -> Annotation:
        """Crea la anotación y la agrega al conjunto de la sesión.

        Las posiciones se guardan en muestras del registro, no en píxeles ni
        en coordenadas de la ventana: es lo que exige "Anotaciones.txt" y lo
        único que sobrevive a un cambio de zoom.

        Los eventos de mouse llegan en **segundos** desde el inicio de la
        ventana, así que la conversión la hace
        `core.windows.seconds_to_sample()`, que suma el desplazamiento sobre el
        borde real de la ventana. Calcularlo como `ventana * 30 * fs` deja la
        anotación en la ventana de al lado cuando la frecuencia no es redonda.
        """
        if self._session is None:
            raise InvalidAnnotationError(
                "No se puede anotar sin un registro abierto.",
                details="La herramienta de anotación no está activada.",
            )
        anotacion = Annotation(
            label=label,
            onset_sample=onset_sample,
            duration_samples=duration_samples,
        )
        self._session.annotations.add(anotacion)
        self._pendiente = None
        self.notify_changed()
        return anotacion

    def add_label(self, label: str, color: str | None = None) -> None:
        """Registra una clase de evento nueva con el nombre que elija el usuario."""
        if self._session is None:
            raise InvalidAnnotationError(
                "No se puede crear una clase de evento sin un registro abierto.",
                details="La herramienta de anotación no está activada.",
            )
        self._session.annotations.add_label(label, color)
        self.notify_changed()

    def delete_annotation(self, annotation: Annotation) -> None:
        """Elimina una anotación existente."""
        if self._session is None:
            raise InvalidAnnotationError(
                "No se puede borrar una anotación sin un registro abierto.",
                details="La herramienta de anotación no está activada.",
            )
        self._session.annotations.remove(annotation)
        self.notify_changed()

    def annotation_at(self, x: float) -> Annotation | None:
        """La anotación que cae bajo un punto, para borrarla con el clic derecho.

        `x` en segundos desde el inicio del registro, como el resto de los
        eventos de mouse. Si hay varias superpuestas se elige **la más corta**:
        es la única que no se puede señalar en ningún otro lugar, porque la
        larga asoma a los costados de la corta y la corta no asoma de ningún
        lado.

        Returns:
            La anotación, o `None` si no hay ninguna ahí o no hay registro.
        """
        if self._session is None:
            return None
        muestra = seconds_to_sample_absolute(x, self._session.recording.sampling_rate)
        debajo = self._session.annotations.in_range(muestra, muestra + 1)
        if not debajo:
            return None
        return min(debajo, key=lambda anotacion: anotacion.duration_samples)

    def overlays(self) -> Sequence[Overlay]:
        """Las bandas de los eventos de la página, más la selección en curso.

        Las bandas son las de `annotation_bands()`, que la ventana principal
        dibuja también con la herramienta apagada. Lo único propio del gesto es
        la selección que se está arrastrando.
        """
        if self._session is None:
            return ()
        bandas = list(annotation_bands(self._session))

        # La selección en curso se dibuja sin clase todavía: el usuario tiene
        # que ver qué está marcando antes de que se le pregunte qué es.
        if self._desde is not None and self._hasta is not None:
            desde, hasta = sorted((self._desde, self._hasta))
            bandas.append(
                SpanOverlay(
                    tool_name=self.name,
                    start_seconds=desde,
                    end_seconds=hasta,
                    label="",
                )
            )
        return tuple(bandas)


def annotation_bands(session: Session) -> tuple[SpanOverlay, ...]:
    """Las bandas de las anotaciones que caen en la página visible.

    **Es una función y no un método** porque se dibujan siempre, esté o no
    activa la herramienta: una anotación es un dato del registro, no parte del
    gesto que la creó. Hasta que se separó, sólo se veían con «Anotar» activo, y
    desaparecían al activar la lupa.

    Cada banda ocupa todo el alto del gráfico, como pide el pliego, para que se
    vea sin importar qué canales estén visibles; por eso un `SpanOverlay` sólo
    lleva el tramo horizontal y no una altura. Las posiciones se guardan en
    muestras y se devuelven en segundos absolutos.
    """
    fs = session.recording.sampling_rate
    # **El filtro es la pagina visible, no la epoca.** Con una pagina de
    # cuatro horas, filtrar por la epoca dibujaria solo las bandas de una de
    # las 480 que hay en pantalla y las otras 479 apareceria vacias aunque
    # tengan eventos: la herramienta mintiendo sobre lo que hay.
    pagina = session.viewport
    inicio, fin = seconds_to_samples(
        pagina.start_seconds,
        pagina.end_seconds,
        fs,
        session.recording.n_samples,
    )
    conjunto = session.annotations
    return tuple(
        SpanOverlay(
            tool_name=AnnotatorTool.name,
            start_seconds=sample_to_seconds_absolute(anotacion.onset_sample, fs),
            end_seconds=sample_to_seconds_absolute(anotacion.end_sample, fs),
            label=anotacion.label,
            color=anotacion.color or conjunto.color_of(anotacion.label),
        )
        for anotacion in conjunto.in_range(inicio, fin)
    )
