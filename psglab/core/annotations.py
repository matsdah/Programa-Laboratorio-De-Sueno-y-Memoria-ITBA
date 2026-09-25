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

import bisect
import re
from dataclasses import dataclass
from typing import Final

from psglab.utils.errors import InvalidAnnotationError, UnknownAnnotationLabelError
from psglab.utils.validation import check_finite, check_index

#: Clases de evento ofrecidas por defecto. El usuario puede agregar las suyas.
DEFAULT_LABELS: Final[tuple[str, ...]] = (
    "Arousal",
    "Complejo K",
    "Spindle",
)

#: Colores de las bandas, asignados por orden de registro de la clase.
#:
#: Están acá y no en `config.py` porque `config.py` guarda lo que **fija el
#: pliego**, y el pliego no dice nada de colores: sólo pide que el evento quede
#: marcado con una banda de color. Elegirlos es del programa.
#:
#: La asignación es por posición, así que es **determinística**: la misma lista
#: de clases da siempre los mismos colores, y dos registros abiertos uno tras
#: otro se ven igual. Si hay más clases que colores, se vuelve a empezar.
#: La forma de un color de clase: numeral y seis dígitos hexadecimales.
_COLOR_DE_CLASE: Final[re.Pattern[str]] = re.compile(r"#[0-9a-fA-F]{6}")


def es_color_de_clase(value: object) -> bool:
    """Si un valor sirve como color de una clase de evento.

    Es más estricta que `theme.is_valid_color()`, que pregunta a pyqtgraph y
    acepta `red` o `#e6754aff`. Ver `AnnotationSet.add_label()` para el motivo:
    el visualizador le concatena la transparencia al texto, y eso sólo da un
    color con seis dígitos.

    No eleva: devuelve falso para cualquier cosa que no sirva.
    """
    return isinstance(value, str) and _COLOR_DE_CLASE.fullmatch(value) is not None


PALETTE: Final[tuple[str, ...]] = (
    "#e6754a",  # naranja
    "#4a90e6",  # azul
    "#6cb04a",  # verde
    "#b04ae6",  # violeta
    "#e6c04a",  # amarillo
    "#4ab0a8",  # turquesa
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

    **Inmutable a propósito.** Así se la puede guardar en un conjunto y usar
    como clave, que es lo que necesita el anotador para saber cuál está debajo
    del clic. **Corregirla es reemplazarla** (hito 52): `AnnotationSet.replace()`
    cambia una por otra, y no hay ningún camino que la modifique en el lugar.
    Hasta ese hito se decía que una anotación «se crea, se borra, no se edita»,
    y para corregir una clase equivocada había que borrarla y rehacer el gesto.
    """

    label: str
    onset_sample: int
    duration_samples: int
    channels: tuple[str, ...] = ()
    color: str | None = None

    @property
    def end_sample(self) -> int:
        """Primera muestra posterior al evento."""
        return self.onset_sample + self.duration_samples


class AnnotationSet:
    """Todas las anotaciones de un registro, más las clases disponibles.

    La lista interna se mantiene **siempre ordenada por muestra de inicio**. No
    es una optimización: es lo que hace que el índice de `remove_at()` signifique
    lo mismo que la posición en `all()`. Si se guardaran por orden de creación y
    `all()` ordenara al salir, los dos índices divergirían y el anotador
    terminaría borrando una banda distinta de la que el usuario señaló.
    """

    def __init__(self, labels: tuple[str, ...] = DEFAULT_LABELS) -> None:
        """Crea un conjunto vacío con las clases de evento indicadas.

        Cada clase recibe un color de `PALETTE` según su posición.
        """
        self._annotations: list[Annotation] = []
        self._colors: dict[str, str] = {}
        for label in labels:
            self.add_label(label)

    def add(self, annotation: Annotation) -> None:
        """Agrega una anotación, manteniendo el orden por muestra de inicio.

        Acá es donde la anotación entra al modelo, y por eso es acá donde se
        valida y no en `Annotation`: la dataclass se deja construir libremente
        para que el anotador pueda armar candidatas mientras el usuario arrastra
        el mouse, sin que exploten a mitad del gesto.

        Raises:
            UnknownAnnotationLabelError: si la clase no está registrada. Para
                usar una clase nueva hay que llamar antes a `add_label`.
            InvalidAnnotationError: si la posición o la duración no son números
                finitos, si la posición es negativa, o si la duración no cubre
                ninguna muestra. **La duración cero se rechaza a
                propósito**: el pliego pide marcar el evento con una banda sobre
                la señal, y una banda sin ancho no se puede dibujar ni solapar
                con nada.
        """
        self._validar(annotation)
        self._insertar(annotation)

    def replace(self, old: Annotation, new: Annotation) -> None:
        """Cambia una anotación por otra: es como se corrige una (hito 52).

        **Valida la nueva antes de sacar la vieja.** Si la nueva no sirve —una
        clase que no existe, un tramo sin ancho— el conjunto queda como estaba:
        un reemplazo que fallara a la mitad le costaría al investigador el
        evento que quería corregir.

        La nueva se inserta en su lugar por muestra de inicio, que puede no ser
        el de la vieja si se movió su comienzo: es lo que mantiene la promesa
        de orden de la que depende `remove_at()`.

        Raises:
            InvalidAnnotationError: si `old` no está en el conjunto, o si `new`
                no es una anotación válida (ver `add()`).
            UnknownAnnotationLabelError: si la clase de `new` no está
                registrada.
        """
        self._validar(new)
        self.remove(old)
        self._insertar(new)

    def _validar(self, annotation: Annotation) -> None:
        """Las reglas de `add()`, aparte para que `replace()` las use antes de
        tocar nada."""
        if not isinstance(annotation, Annotation):
            raise InvalidAnnotationError(
                "Se quiso guardar algo que no es una anotación.",
                details=f"annotation es {type(annotation).__name__}, se esperaba Annotation.",
            )
        # La etiqueta se usa como clave del diccionario de colores: una que no
        # sea `str` —una lista, un diccionario— elevaba `TypeError: unhashable`
        # en la línea de abajo, antes de poder explicar nada.
        if not isinstance(annotation.label, str):
            raise InvalidAnnotationError(
                "La clase del evento anotado no es un nombre.",
                details=(
                    f"annotation.label es {type(annotation.label).__name__}, "
                    "se esperaba str."
                ),
            )
        if annotation.label not in self._colors:
            raise UnknownAnnotationLabelError(
                f"La clase de evento «{annotation.label}» no está registrada, así que "
                "no se puede anotar con ella.",
                details=f"Clases disponibles: {', '.join(self.labels())}.",
            )
        check_finite(
            annotation.onset_sample,
            error=InvalidAnnotationError,
            message="La anotación empieza antes del comienzo del registro.",
            details="Se esperaba una muestra de inicio finita y no negativa.",
            minimum=0,
        )
        check_finite(
            annotation.duration_samples,
            error=InvalidAnnotationError,
            message=(
                "La anotación no cubre ninguna muestra del registro, así que no se "
                "podría ni dibujar."
            ),
            details="Se esperaba una duración finita de 1 muestra o más.",
            minimum=1,
        )

    def _insertar(self, annotation: Annotation) -> None:
        """Inserta una anotación ya validada en su lugar por muestra de inicio."""
        posicion = bisect.bisect_right(
            [a.onset_sample for a in self._annotations], annotation.onset_sample
        )
        self._annotations.insert(posicion, annotation)

    def remove(self, annotation: Annotation) -> None:
        """Elimina una anotación.

        Si hay dos anotaciones exactamente iguales —misma clase, mismo inicio,
        misma duración, mismos canales— son indistinguibles por definición y se
        borra la primera. Para señalar una en particular está `remove_at()`.

        Raises:
            InvalidAnnotationError: si la anotación no está en el conjunto. Un
                borrado silencioso escondería un bug del anotador, que es el
                único que llama a esto.
        """
        try:
            self._annotations.remove(annotation)
        except ValueError:
            raise InvalidAnnotationError(
                "Se quiso borrar una anotación que no está en el registro.",
                details=f"{annotation!r}",
            ) from None

    def remove_at(self, index: int) -> None:
        """Elimina la anotación que ocupa una posición de `all()`.

        Es lo que necesita el anotador cuando el usuario hace clic sobre una
        banda concreta: ahí no quiere borrar "una igual a esta" sino esa.

        Raises:
            InvalidAnnotationError: si la posición no existe. Se rechazan también
                los índices negativos: en Python cuentan desde el final, así que
                sin la guarda `remove_at(-1)` borraría la última anotación de la
                noche en vez de avisar que el índice está mal.
        """
        check_index(
            index,
            error=InvalidAnnotationError,
            message="Se quiso borrar una anotación que no existe.",
            details="Se esperaba una posición entera.",
        )
        if not 0 <= index < len(self._annotations):
            raise InvalidAnnotationError(
                "Se quiso borrar una anotación que no existe.",
                details=f"index = {index}, hay {len(self._annotations)} anotaciones.",
            )
        del self._annotations[index]

    def add_label(self, label: str, color: str | None = None) -> None:
        """Registra una clase de evento nueva creada por el usuario (V1_F).

        Sin color, toma el siguiente de `PALETTE` según cuántas clases haya ya.
        Así **toda clase registrada tiene color** y `color_of()` siempre puede
        cumplir su promesa de devolver uno.

        Registrar una clase que ya existe no es un error —es algo que el usuario
        teclea— y si se pasa un color, reemplaza al anterior.

        **El color es exactamente `#rrggbb`** (hito 48), y no cualquier cosa
        que pyqtgraph sepa dibujar. No es purismo: el visualizador pinta la
        banda de una anotación con `color + "55"`, o sea que le **concatena** la
        transparencia al texto. Con `#e6754a` eso da un color válido; con `red`
        da `red55` y con `#e6754aff` da diez dígitos, y en los dos casos dibujar
        la anotación eleva un `ValueError` crudo. Hasta este hito se aceptaba
        cualquier cosa, y un archivo de preferencias editado a mano con `red`
        llegaba hasta ahí. Lo normaliza `preferences.py` al leer, que es por
        donde entra texto arbitrario.

        Raises:
            InvalidAnnotationError: si la etiqueta está vacía —una clase sin
                nombre no se puede elegir en ninguna lista— o si el color no
                tiene la forma `#rrggbb`.
        """
        if color is not None and not es_color_de_clase(color):
            raise InvalidAnnotationError(
                "El color de una clase de evento no es válido.",
                details=(
                    f"color = {color!r}; se esperaba la forma #rrggbb, que es la "
                    "que el visualizador sabe volver transparente."
                ),
            )
        if not isinstance(label, str):
            raise InvalidAnnotationError(
                "Una clase de evento necesita un nombre escrito.",
                details=f"label es {type(label).__name__}, se esperaba str.",
            )
        if not label.strip():
            raise InvalidAnnotationError(
                "Una clase de evento necesita un nombre.",
                details=f"label = {label!r}.",
            )
        if color is None and label in self._colors:
            return
        if color is None:
            color = PALETTE[len(self._colors) % len(PALETTE)]
        self._colors[label] = color

    def labels(self) -> list[str]:
        """Clases de evento disponibles, las de fábrica y las del usuario.

        En orden de registro, que es el que decide los colores.
        """
        return list(self._colors)

    def color_of(self, label: str) -> str:
        """Color asignado a una clase de evento.

        Raises:
            UnknownAnnotationLabelError: si la clase no está registrada. Toda
                clase registrada tiene color, así que es el único motivo por el
                que esto puede fallar.
        """
        if not isinstance(label, str) or label not in self._colors:
            raise UnknownAnnotationLabelError(
                f"La clase de evento «{label}» no está registrada.",
                details=f"Clases disponibles: {', '.join(self.labels())}.",
            )
        return self._colors[label]

    def in_range(self, start_sample: int, stop_sample: int) -> list["Annotation"]:
        """Anotaciones que se solapan con un tramo de señal.

        Lo usa el visualizador para dibujar sólo las bandas de la ventana
        actual, y la Übersicht para mostrar si hay eventos en las ventanas
        vecinas (V1_F de Übersicht).

        El tramo es **semiabierto**, igual que `windows.window_to_samples()`:
        una anotación que termina justo donde empieza el tramo no entra, y
        tampoco la que empieza justo donde el tramo termina. Es lo que evita que
        una anotación se dibuje en dos ventanas seguidas.
        """
        for nombre, valor in (("start_sample", start_sample), ("stop_sample", stop_sample)):
            check_finite(
                valor,
                error=InvalidAnnotationError,
                message="No se pudo buscar anotaciones en ese tramo de señal.",
                details=f"{nombre} tiene que ser un número finito de muestras.",
            )
        return [
            a
            for a in self._annotations
            if a.onset_sample < stop_sample and a.end_sample > start_sample
        ]

    def all(self) -> list["Annotation"]:
        """Todas las anotaciones, ordenadas por muestra de inicio.

        Es una lista nueva: quien la recibe sólo quiere recorrerla, y prestarle
        la interna lo dejaría desordenarla, que es justo lo que le da sentido al
        índice de `remove_at()`.
        """
        return list(self._annotations)

    def count_by_label(self) -> dict[str, int]:
        """Cantidad de anotaciones de cada clase.

        Lo consume "Informacion.txt" (V3_F de "Archivo de salida").

        **Sólo aparecen las clases que tienen al menos una anotación.** El
        informe declara que las secciones que no corresponden se omiten con una
        explicación y no con ceros, así que una clase registrada y sin usar no
        tiene por qué ocupar una línea.
        """
        cuentas: dict[str, int] = {}
        for anotacion in self._annotations:
            cuentas[anotacion.label] = cuentas.get(anotacion.label, 0) + 1
        return cuentas
