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
    sample_to_seconds,
    seconds_to_sample,
    window_to_samples,
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
        """
        self._activa = False
        self._desde = self._hasta = None
        self._pendiente = None
        self.notify_changed()

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Empieza la selección del evento."""
        if not self._activa or button != "left":
            return
        self._desde = self._hasta = x
        self._pendiente = None
        self.notify_changed()

    def on_mouse_move(self, x: float, y: float) -> None:
        """Extiende la selección mientras el usuario arrastra."""
        if self._desde is None:
            return
        self._hasta = x
        self.notify_changed()

    def on_mouse_release(self, x: float, y: float, button: str) -> None:
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
        ventana = self._session.current_window
        inicio = seconds_to_sample(ventana, desde, fs)
        fin = seconds_to_sample(ventana, hasta, fs)
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

    def overlays(self) -> Sequence[Overlay]:
        """Las bandas de los eventos de la ventana actual, más la selección en curso.

        Cada banda ocupa todo el alto de la ventana de scoring, como pide el
        pliego, para que se vea sin importar qué canales estén visibles; por eso
        un `SpanOverlay` sólo lleva el tramo horizontal y no una altura.

        Las anotaciones guardadas vienen en muestras y se devuelven en segundos
        desde el inicio de la ventana, con
        `core.windows.sample_to_seconds()`.
        """
        if self._session is None:
            return ()

        fs = self._session.recording.sampling_rate
        ventana = self._session.current_window
        inicio, fin = window_to_samples(ventana, fs)
        conjunto = self._session.annotations

        bandas = [
            SpanOverlay(
                tool_name=self.name,
                start_seconds=sample_to_seconds(ventana, anotacion.onset_sample, fs),
                end_seconds=sample_to_seconds(ventana, anotacion.end_sample, fs),
                label=anotacion.label,
                color=anotacion.color or conjunto.color_of(anotacion.label),
            )
            for anotacion in conjunto.in_range(inicio, fin)
        ]

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
