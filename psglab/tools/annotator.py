"""Anotación de eventos sobre la señal.

El usuario selecciona un tramo con el mouse, elige una clase de evento de la
lista (Arousal, complejo K, spindle, ...) o crea una clase nueva con el
nombre que quiera, y el tramo queda marcado con una banda de color que ocupa
todo el alto de la ventana de scoring.

Resuelve una de las carencias que motivan el proyecto: en los programas
actuales del laboratorio no se puede anotar la señal.

Cubre del pliego: V1_F de "Anotación de la señal".
"""

from psglab.core.annotations import Annotation
from psglab.core.session import Session
from psglab.tools.base import ViewerTool
from psglab.tools.registry import register_tool


@register_tool
class AnnotatorTool(ViewerTool):
    """Selección de eventos y asignación de clase."""

    name = "annotator"
    label = "Anotar"
    description = "Marcar un evento en la señal y asignarle una clase"

    def activate(self, session: Session) -> None:
        """Activa el modo de anotación."""
        raise NotImplementedError("Pendiente: activar el modo de selección.")

    def deactivate(self) -> None:
        """Sale del modo de anotación. Las anotaciones hechas se conservan."""
        raise NotImplementedError("Pendiente: salir del modo de selección.")

    def on_mouse_press(self, x: float, y: float, button: str) -> None:
        """Empieza la selección del evento."""
        raise NotImplementedError("Pendiente: registrar el inicio de la selección.")

    def on_mouse_move(self, x: float, y: float) -> None:
        """Muestra el ancho de la selección mientras el usuario arrastra."""
        raise NotImplementedError("Pendiente: actualizar la vista previa de la banda.")

    def on_mouse_release(self, x: float, y: float, button: str) -> None:
        """Cierra la selección y pide la clase del evento.

        El ancho de la banda es el que seleccionó el usuario, no uno fijo: un
        arousal y un complejo K duran cosas muy distintas.
        """
        raise NotImplementedError("Pendiente: cerrar la selección y abrir el diálogo de clase.")

    def create_annotation(self, label: str, onset_sample: int, duration_samples: int) -> Annotation:
        """Crea la anotación y la agrega al conjunto de la sesión.

        Las posiciones se guardan en muestras del registro, no en píxeles ni
        en coordenadas de la ventana: es lo que exige "Anotaciones.txt" y lo
        único que sobrevive a un cambio de zoom.
        """
        raise NotImplementedError("Pendiente: construir la anotación y agregarla.")

    def add_label(self, label: str, color: str | None = None) -> None:
        """Registra una clase de evento nueva con el nombre que elija el usuario."""
        raise NotImplementedError("Pendiente: registrar la clase en el AnnotationSet.")

    def delete_annotation(self, annotation: Annotation) -> None:
        """Elimina una anotación existente."""
        raise NotImplementedError("Pendiente: quitar la anotación del conjunto.")

    def draw_annotations(self, window_index: int) -> None:
        """Dibuja las bandas de color de los eventos de una ventana.

        Cada banda ocupa todo el alto de la ventana de scoring, como pide el
        pliego, para que se vea sin importar qué canales estén visibles.
        """
        raise NotImplementedError("Pendiente: dibujar las bandas de la ventana.")
