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
import math
import operator
import re
from dataclasses import dataclass
from typing import Final

from psglab.utils.errors import InvalidAnnotationError, UnknownAnnotationLabelError
from psglab.utils.validation import check_finite, check_index

#: La clase de evento que además es la marca de arousal de su ventana. Ver
#: `is_arousal()`.
AROUSAL_LABEL: Final[str] = "Arousal"

#: Clases de evento ofrecidas por defecto. El usuario puede agregar las suyas.
DEFAULT_LABELS: Final[tuple[str, ...]] = (
    AROUSAL_LABEL,
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


def is_arousal(label: object) -> bool:
    """Si una clase de evento es la del arousal.

    El arousal se registra de dos formas: la marca de la ventana —la tecla A,
    que es la que exportan `Scoring.txt` y las estadísticas— y la clase de
    anotación «Arousal». **La que cuenta es la marca**, y anotar un arousal la
    pone, para que el que se anotó sobre la señal llegue a los archivos de
    salida; ver `Session.mark_arousal_of()`.

    Sin distinguir mayúsculas ni espacios de más: «arousal» escrito a mano en
    el cartel es la misma clase. Lo que no es texto no es la clase.
    """
    return isinstance(label, str) and label.strip().casefold() == AROUSAL_LABEL.casefold()


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
    del clic. **Corregirla es reemplazarla**: `AnnotationSet.replace()` cambia
    una por otra, y no hay ningún camino que la modifique en el lugar.
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

    La lista interna se mantiene **siempre ordenada por muestra de inicio**, y
    dos que empiezan en la misma muestra quedan en el orden en que se
    agregaron. Es lo que deja buscar un tramo con búsqueda binaria
    (`in_range()`) y lo que hace que `all()` salga en el orden en que se
    exportan, sin ordenar en cada pedido.

    **Al lado va la lista de los comienzos**, en el mismo orden, y la duración
    más larga. Con eso agregar, borrar y buscar un tramo son búsquedas
    binarias: importar 20 000 marcas no rearma nada por cada una, y
    `in_range()` no recorre todas en cada repintado.
    """

    def __init__(self, labels: tuple[str, ...] = DEFAULT_LABELS) -> None:
        """Crea un conjunto vacío con las clases de evento indicadas.

        Cada clase recibe un color de `PALETTE` según su posición.
        """
        self._annotations: list[Annotation] = []
        #: La muestra de inicio de cada una, en el mismo orden que
        #: `_annotations`: es la lista sobre la que se busca.
        self._inicios: list[int] = []
        #: La duración más larga, en muestras. Acota hacia atrás lo que puede
        #: solaparse con un tramo: ver `in_range()`.
        self._duracion_maxima: int = 0
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
        """Cambia una anotación por otra: es como se corrige una.

        **Valida la nueva antes de sacar la vieja.** Si la nueva no sirve —una
        clase que no existe, un tramo sin ancho— el conjunto queda como estaba:
        un reemplazo que fallara a la mitad le costaría al investigador el
        evento que quería corregir.

        La nueva se inserta en su lugar por muestra de inicio, que puede no ser
        el de la vieja si se movió su comienzo: es lo que mantiene la promesa
        de orden de la que dependen `in_range()` y `all()`.

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
        # **En muestras enteras**: `Anotaciones.txt` guarda puntos del
        # registro, que son enteros, y 10,5 no es un lugar de la señal.
        for campo, valor in (
            ("onset_sample", annotation.onset_sample),
            ("duration_samples", annotation.duration_samples),
        ):
            try:
                operator.index(valor)
            except TypeError:
                raise InvalidAnnotationError(
                    "Una anotación se guarda en muestras enteras del registro.",
                    details=f"{campo} = {valor!r}.",
                ) from None

    def _insertar(self, annotation: Annotation) -> None:
        """Inserta una anotación ya validada en su lugar por muestra de inicio.

        **Después de las que empiezan en la misma muestra**, como hacía
        siempre: dos anotaciones con el mismo comienzo quedan en el orden en
        que se agregaron.
        """
        posicion = bisect.bisect_right(self._inicios, annotation.onset_sample)
        self._annotations.insert(posicion, annotation)
        self._inicios.insert(posicion, annotation.onset_sample)
        self._duracion_maxima = max(self._duracion_maxima, annotation.duration_samples)

    def _sacar(self, index: int) -> None:
        """Saca la anotación de una posición, con su comienzo.

        Si era la más larga, la duración máxima se vuelve a medir: dejarla
        vieja no daría resultados equivocados, pero `in_range()` revisaría de
        más para siempre.
        """
        sacada = self._annotations.pop(index)
        del self._inicios[index]
        if sacada.duration_samples == self._duracion_maxima:
            self._duracion_maxima = max(
                (a.duration_samples for a in self._annotations), default=0
            )

    def remove(self, annotation: Annotation) -> None:
        """Elimina una anotación.

        Si hay dos anotaciones exactamente iguales —misma clase, mismo inicio,
        misma duración, mismos canales— son indistinguibles por definición y se
        borra la primera.

        Raises:
            InvalidAnnotationError: si la anotación no está en el conjunto. Un
                borrado silencioso escondería un bug del anotador, que es el
                único que llama a esto.
        """
        # Una igual empieza en la misma muestra: se busca sólo entre las que
        # empiezan ahí. La primera de ese tramo es la primera de todas.
        #
        # **Lo que se pide borrar no pasó por la validación**, así que su
        # comienzo puede ser cualquier cosa. Uno que no se compara con un
        # número —un texto— elevaría `TypeError` en la búsqueda; antes
        # `list.remove()` simplemente no la encontraba, y así tiene que seguir.
        if isinstance(annotation, Annotation):
            try:
                desde = bisect.bisect_left(self._inicios, annotation.onset_sample)
                hasta = bisect.bisect_right(self._inicios, annotation.onset_sample)
            except TypeError:
                desde = hasta = 0
            for posicion in range(desde, hasta):
                if self._annotations[posicion] == annotation:
                    self._sacar(posicion)
                    return
        raise InvalidAnnotationError(
            "Se quiso borrar una anotación que no está en el registro.",
            details=f"{annotation!r}",
        )

    def add_label(self, label: str, color: str | None = None) -> None:
        """Registra una clase de evento nueva creada por el usuario (V1_F).

        Sin color, toma el siguiente de `PALETTE` según cuántas clases haya ya.
        Así **toda clase registrada tiene color** y `color_of()` siempre puede
        cumplir su promesa de devolver uno.

        Registrar una clase que ya existe no es un error —es algo que el usuario
        teclea— y si se pasa un color, reemplaza al anterior.

        **El color es exactamente `#rrggbb`**, y no cualquier cosa que
        pyqtgraph sepa dibujar. No es purismo: el visualizador pinta la banda
        de una anotación con `color + "55"`, o sea que le **concatena** la
        transparencia al texto. Con `#e6754a` eso da un color válido; con `red`
        da `red55` y con `#e6754aff` da diez dígitos, y en los dos casos dibujar
        la anotación elevaría un `ValueError` crudo. Lo que llega de un archivo
        de preferencias editado a mano lo normaliza `preferences.py` al leer,
        que es por donde entra texto arbitrario.

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
        # Sólo pueden solaparse las que empiezan antes del final del tramo y
        # después de su comienzo menos la duración más larga: una que empieza
        # antes termina, como mucho, justo donde el tramo empieza.
        hasta = bisect.bisect_left(self._inicios, stop_sample)
        desde = bisect.bisect_right(self._inicios, start_sample - self._duracion_maxima)
        return [
            a
            for a in self._annotations[desde:hasta]
            if a.end_sample > start_sample
        ]

    def all(self) -> list["Annotation"]:
        """Todas las anotaciones, ordenadas por muestra de inicio.

        Es una lista nueva: quien la recibe sólo quiere recorrerla, y prestarle
        la interna lo dejaría desordenarla, y con eso romper la búsqueda de
        `in_range()`.
        """
        return list(self._annotations)


def marks_to_annotations(
    marks: list[tuple[float, float, str]],
    sampling_rate: float,
    n_samples: int,
) -> list[Annotation]:
    """Las marcas que trae el archivo del registro, como anotaciones.

    Un BrainVision trae los marcadores de su `.vmrk` y un EDF+ sus anotaciones:
    los lectores los guardan en segundos, con su descripción. Acá pasan a la
    unidad de las anotaciones, que son muestras del registro.

    - **Una marca sin duración ocupa una muestra**: un marcador de estímulo es
      un instante, y una anotación sin ancho no se podría dibujar.
    - **Una marca fuera del registro se saltea**: la del final de un archivo
      truncado, o la de antes del comienzo, no tienen dónde ir.
    - **La clase es la descripción**, sin los espacios de los bordes. Una sin
      descripción se saltea: no habría con qué nombrarla.

    Args:
        marks: `(inicio en segundos, duración en segundos, descripción)`.
        sampling_rate: la frecuencia del registro.
        n_samples: cuántas muestras tiene el registro.

    Raises:
        InvalidAnnotationError: si las marcas no tienen esa forma, o si la
            frecuencia o la cantidad de muestras no sirven.
    """
    check_finite(
        sampling_rate,
        error=InvalidAnnotationError,
        message="No se pudieron leer las marcas del registro.",
        details="sampling_rate tiene que ser un número finito y positivo.",
    )
    if sampling_rate <= 0:
        raise InvalidAnnotationError(
            "No se pudieron leer las marcas del registro.",
            details=f"sampling_rate = {sampling_rate}, se esperaba un número positivo.",
        )
    check_index(
        n_samples,
        error=InvalidAnnotationError,
        message="No se pudieron leer las marcas del registro.",
        details="n_samples tiene que ser una cantidad entera de muestras.",
    )
    if not isinstance(marks, (list, tuple)):
        raise InvalidAnnotationError(
            "No se pudieron leer las marcas del registro.",
            details=f"marks es {type(marks).__name__}, se esperaba una lista.",
        )

    anotaciones: list[Annotation] = []
    for marca in marks:
        if (
            not isinstance(marca, (list, tuple))
            or len(marca) != 3
            or not isinstance(marca[2], str)
            or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in marca[:2]
            )
        ):
            raise InvalidAnnotationError(
                "No se pudieron leer las marcas del registro.",
                details=f"Se esperaba (inicio, duración, descripción) y se leyó {marca!r}.",
            )
        inicio_s, duracion_s, descripcion = marca
        clase = descripcion.strip()
        inicio = round(inicio_s * sampling_rate)
        if not clase or not 0 <= inicio < n_samples:
            continue
        duracion = max(1, round(duracion_s * sampling_rate))
        anotaciones.append(
            Annotation(clase, inicio, min(duracion, n_samples - inicio))
        )
    return anotaciones
