"""Anotaciones de eventos sobre la señal.

El usuario selecciona un evento con el mouse, le asigna una clase de una lista
(Arousal, complejos K, spindles, ...) o crea una clase nueva con el nombre que
quiera, y el evento queda marcado con una banda de color.

Las posiciones se guardan en muestras ("puntos", en el vocabulario del
pliego) y no en segundos ni en píxeles: es lo que exige el formato de
"Anotaciones.txt" y lo único que no se degrada al cambiar el zoom.

Cubre del pliego: V1_F de "Anotación de la señal"; alimenta V2_F de "Archivo
de salida" y la vista de eventos de la herramienta Übersicht.
"""

from dataclasses import dataclass
from typing import Final

#: Clases de evento ofrecidas por defecto. El usuario puede agregar las suyas.
DEFAULT_LABELS: Final[tuple[str, ...]] = (
    "Arousal",
    "Complejo K",
    "Spindle",
)


@dataclass(frozen=True)
class Annotation:
    """Un evento anotado sobre la señal.

    Attributes:
        label: clase del evento, de la lista por defecto o creada por el usuario.
        onset_sample: muestra de inicio ("Puntos_Emp" en el archivo de salida).
        duration_samples: duración en muestras ("Duracion_Puntos").
        channels: canales sobre los que se marcó el evento. Vacío significa
            que la anotación vale para todos los canales mostrados. Es una
            tupla y no una lista para que la anotación entera sea hashable.
        color: color de la banda, en formato "#RRGGBB". Si es None, se usa el
            color asignado a la clase.

    **Inmutable a propósito.** Una anotación es un hecho registrado sobre la
    señal: se crea, se borra, no se edita. Además así se la puede guardar en un
    conjunto y usar como clave, que es lo que necesita el anotador para saber
    cuál está debajo del clic.
    """

    label: str
    onset_sample: int
    duration_samples: int
    channels: tuple[str, ...] = ()
    color: str | None = None

    @property
    def end_sample(self) -> int:
        """Primera muestra posterior al evento."""
        raise NotImplementedError("Pendiente: sumar onset_sample y duration_samples.")


class AnnotationSet:
    """Todas las anotaciones de un registro, más las clases disponibles."""

    def __init__(self, labels: tuple[str, ...] = DEFAULT_LABELS) -> None:
        """Crea un conjunto vacío con las clases de evento indicadas."""
        raise NotImplementedError("Pendiente: inicializar la lista y las clases.")

    def add(self, annotation: Annotation) -> None:
        """Agrega una anotación.

        Raises:
            UnknownAnnotationLabelError: si la clase no está registrada. Para
                usar una clase nueva hay que llamar antes a `add_label`.
        """
        raise NotImplementedError("Pendiente: validar la clase y agregar la anotación.")

    def remove(self, annotation: Annotation) -> None:
        """Elimina una anotación.

        Si hay dos anotaciones exactamente iguales —misma clase, mismo inicio,
        misma duración, mismos canales— son indistinguibles por definición y se
        borra la primera. Para señalar una en particular está `remove_at()`.
        """
        raise NotImplementedError("Pendiente: eliminar la anotación.")

    def remove_at(self, index: int) -> None:
        """Elimina la anotación que ocupa una posición de `all()`.

        Es lo que necesita el anotador cuando el usuario hace clic sobre una
        banda concreta: ahí no quiere borrar "una igual a esta" sino esa.
        """
        raise NotImplementedError("Pendiente: eliminar la anotación de esa posición.")

    def add_label(self, label: str, color: str | None = None) -> None:
        """Registra una clase de evento nueva creada por el usuario (V1_F)."""
        raise NotImplementedError("Pendiente: registrar la clase nueva.")

    def labels(self) -> list[str]:
        """Clases de evento disponibles, las de fábrica y las del usuario."""
        raise NotImplementedError("Pendiente: devolver las clases disponibles.")

    def color_of(self, label: str) -> str:
        """Color asignado a una clase de evento."""
        raise NotImplementedError("Pendiente: devolver el color de la clase.")

    def in_range(self, start_sample: int, stop_sample: int) -> list["Annotation"]:
        """Anotaciones que se solapan con un tramo de señal.

        Lo usa el visualizador para dibujar sólo las bandas de la ventana
        actual, y la Übersicht para mostrar si hay eventos en las ventanas
        vecinas (V1_F de Übersicht).
        """
        raise NotImplementedError("Pendiente: filtrar las anotaciones por rango.")

    def all(self) -> list["Annotation"]:
        """Todas las anotaciones, ordenadas por muestra de inicio."""
        raise NotImplementedError("Pendiente: devolver las anotaciones ordenadas.")

    def count_by_label(self) -> dict[str, int]:
        """Cantidad de anotaciones de cada clase.

        Lo consume "Informacion.txt" (V3_F de "Archivo de salida").
        """
        raise NotImplementedError("Pendiente: contar las anotaciones por clase.")
