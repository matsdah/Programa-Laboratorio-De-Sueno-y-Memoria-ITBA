"""Anotación de eventos sobre la señal.

El usuario selecciona un tramo con el mouse, elige una clase de evento de la
lista (Arousal, complejo K, spindle, ...) o crea una clase nueva con el
nombre que quiera, y el tramo queda marcado con una banda de color que ocupa
todo el alto de la ventana de scoring.

Resuelve una de las carencias que motivan el proyecto: en los programas
actuales del laboratorio no se puede anotar la señal.

**Una anotación hecha se puede corregir** desde el hito 52: con la herramienta
activa, arrastrar cerca del borde de una banda mueve ese borde en vez de
empezar una selección nueva, y `change_label()` le cambia la clase. Las dos
cosas terminan en `AnnotationSet.replace()`: la anotación sigue siendo
inmutable y corregirla es cambiarla por otra.

Cubre del pliego: V1_F de "Anotación de la señal".
"""

import dataclasses
from collections.abc import Sequence
from typing import Final, Literal

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


#: Qué borde de una banda: su comienzo o su final.
Edge = Literal["start", "end"]

#: A cuántos segundos de un borde se lo toma por ese borde, mientras la ventana
#: no fije otra cosa. La ventana la fija en píxeles —ver `set_edge_tolerance()`—
#: porque un segundo son cientos de píxeles con una página de 5 s y ninguno con
#: la noche entera.
_TOLERANCIA_POR_DEFECTO_S: Final[float] = 0.1


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
        #: El borde que se está arrastrando: de qué anotación, cuál, y por
        #: dónde va el mouse, en segundos absolutos. `None` si no se arrastra.
        self._borde: tuple[Annotation, Edge] | None = None
        self._x_del_borde: float = 0.0
        #: La anotación que dejó el último arrastre de un borde, para que la
        #: ventana diga qué pasó. Se olvida al apretar de nuevo.
        self._movida: Annotation | None = None
        self._tolerancia_s: float = _TOLERANCIA_POR_DEFECTO_S

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
        self._borde = None
        self._movida = None
        self.notify_changed()

    def on_mouse_press(
        self, x: float, y: float, button: str, channel_name: str | None = None
    ) -> None:
        """Empieza la selección del evento, o el arrastre de un borde.

        **Cerca del borde de una banda se arrastra el borde** (hito 52); en
        cualquier otro lugar empieza una selección nueva, como siempre. Cerca
        es a menos de `set_edge_tolerance()`.
        """
        if not self._activa or button != "left":
            return
        self._pendiente = None
        self._movida = None
        borde = self.edge_at(x)
        if borde is not None:
            self._borde = borde
            self._x_del_borde = x
        else:
            self._desde = self._hasta = x
        self.notify_changed()

    def on_mouse_move(
        self, x: float, y: float, channel_name: str | None = None
    ) -> None:
        """Extiende la selección, o lleva el borde, mientras el usuario arrastra."""
        if self._borde is not None:
            self._x_del_borde = x
            self.notify_changed()
            return
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
        if self._borde is not None and self._session is not None and button == "left":
            anterior, _ = self._borde
            nueva = self._con_el_borde_en(x)
            self._borde = None
            if nueva != anterior:
                self._session.annotations.replace(anterior, nueva)
                self._movida = nueva
            self.notify_changed()
            return
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

    def change_label(self, annotation: Annotation, label: str) -> Annotation:
        """Le cambia la clase a una anotación ya hecha (hito 52).

        El tramo no se toca: es la corrección del error más común, elegir mal
        la clase en la lista. La clase tiene que estar registrada; una nueva se
        registra antes con `add_label()`, igual que al anotar.

        Returns:
            La anotación que quedó en lugar de la anterior.

        Raises:
            InvalidAnnotationError: sin un registro abierto, o si la anotación
                no está en el registro.
            UnknownAnnotationLabelError: si la clase no está registrada.
        """
        if self._session is None:
            raise InvalidAnnotationError(
                "No se puede corregir una anotación sin un registro abierto.",
                details="La herramienta de anotación no está activada.",
            )
        nueva = dataclasses.replace(annotation, label=label)
        self._session.annotations.replace(annotation, nueva)
        self.notify_changed()
        return nueva

    def set_edge_tolerance(self, seconds: float) -> None:
        """A cuántos segundos de un borde se lo toma por ese borde.

        La fija la ventana en cada evento, a partir de unos pocos píxeles: la
        herramienta no conoce la pantalla, y la tolerancia que tiene sentido es
        en píxeles —un borde se agarra con el mouse, no con el reloj—.
        """
        self._tolerancia_s = max(0.0, float(seconds))

    def edge_at(self, x: float) -> tuple[Annotation, Edge] | None:
        """El borde de banda que está bajo un punto, si hay alguno cerca.

        `x` en segundos desde el inicio del registro. Entre varios bordes
        cercanos gana **el más cercano**: dos anotaciones pegadas comparten un
        punto, y el mouse está de un lado o del otro.

        Returns:
            La anotación y cuál de sus bordes, o `None` si no hay ninguno a
            menos de la tolerancia o no hay registro.
        """
        if self._session is None:
            return None
        fs = self._session.recording.sampling_rate
        desde = seconds_to_sample_absolute(max(0.0, x - self._tolerancia_s), fs)
        hasta = seconds_to_sample_absolute(x + self._tolerancia_s, fs) + 1
        candidatos: list[tuple[float, Annotation, Edge]] = []
        for anotacion in self._session.annotations.in_range(desde, hasta):
            for lado, muestra in (("start", anotacion.onset_sample), ("end", anotacion.end_sample)):
                distancia = abs(sample_to_seconds_absolute(muestra, fs) - x)
                if distancia <= self._tolerancia_s:
                    candidatos.append((distancia, anotacion, lado))
        if not candidatos:
            return None
        _, anotacion, lado = min(candidatos, key=lambda c: c[0])
        return anotacion, lado

    @property
    def moved_annotation(self) -> Annotation | None:
        """La anotación que dejó el último arrastre de un borde, o `None`.

        La consulta la ventana al soltar el mouse para decir qué se corrigió; es
        la contraparte de `pending_selection_samples` para una anotación nueva.
        """
        return self._movida

    def _con_el_borde_en(self, x: float) -> Annotation:
        """La anotación que se arrastra, con su borde llevado a `x`.

        **Los bordes no se cruzan**: llevar el comienzo más allá del final lo
        deja una muestra antes del final, y al revés. Una anotación de duración
        cero no se puede dibujar y el conjunto la rechaza; invertirla en
        silencio cambiaría cuál borde tiene el usuario en la mano. Tampoco se
        sale del registro.
        """
        assert self._borde is not None and self._session is not None
        anotacion, lado = self._borde
        registro = self._session.recording
        muestra = seconds_to_sample_absolute(max(0.0, x), registro.sampling_rate)
        muestra = min(muestra, registro.n_samples)
        if lado == "start":
            inicio = min(muestra, anotacion.end_sample - 1)
            return dataclasses.replace(
                anotacion,
                onset_sample=inicio,
                duration_samples=anotacion.end_sample - inicio,
            )
        fin = max(muestra, anotacion.onset_sample + 1)
        return dataclasses.replace(anotacion, duration_samples=fin - anotacion.onset_sample)

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

        # **El borde que se arrastra se ve donde va a quedar**, no donde
        # estaba: la banda vieja se reemplaza por la que resultaría de soltar
        # acá, con los bordes ya recortados para no cruzarse.
        if self._borde is not None:
            anterior, _ = self._borde
            fs = self._session.recording.sampling_rate
            vieja = (
                sample_to_seconds_absolute(anterior.onset_sample, fs),
                sample_to_seconds_absolute(anterior.end_sample, fs),
            )
            nueva = self._con_el_borde_en(self._x_del_borde)
            bandas = [
                dataclasses.replace(
                    banda,
                    start_seconds=sample_to_seconds_absolute(nueva.onset_sample, fs),
                    end_seconds=sample_to_seconds_absolute(nueva.end_sample, fs),
                )
                if (banda.start_seconds, banda.end_seconds) == vieja
                and banda.label == anterior.label
                else banda
                for banda in bandas
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
