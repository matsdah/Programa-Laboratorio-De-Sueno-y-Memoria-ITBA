"""Cómo se muestran los canales: cuáles, en qué orden, con qué escala y dónde.

Es la parte del estado de trabajo que no sabe de épocas: qué canales se ven,
cuáles están seleccionados, cuántos microvoltios representa el carril de cada
uno y cuánto se le resta antes de dibujarlo.

**No conoce la ventana de scoring.** Lo que mide —centrar, ajustar al panel,
la escala de las clases que no tienen una propia— lo mide sobre un tramo de
muestras que le pasa quien llama. `Session` es quien sabe en qué época está
parado el usuario, la valida y la convierte con `core/windows.py`; acá sólo
llega el tramo. Así la regla de qué es una ventana válida vive en un solo
lugar, y medir sobre la página en vez de la época sería cambiar quién arma el
tramo, no este módulo.

`Session` lo guarda y delega en él desde sus propios métodos públicos, así que
la interfaz sigue hablando sólo con la sesión.

Cubre del pliego: V2_P, V3_P y V5_F de "Visualización de la señal".
"""

import numpy as np

from psglab.config import (
    AMPLITUDE_STEP_FACTOR,
    DEFAULT_SCALE_BY_KIND_UV,
    DEFAULT_SCALE_UV,
    MAX_SCALE_UV,
    MIN_SCALE_UV,
)
from psglab.core.recording import Channel, Recording
from psglab.utils.errors import InvalidRecordingError, InvalidScaleError
from psglab.utils.validation import check_finite, clamp


class ChannelDisplay:
    """Canales visibles y seleccionados, y la escala y el desplazamiento de cada uno."""

    def __init__(
        self, recording: Recording, default_scale_uv: float = DEFAULT_SCALE_UV
    ) -> None:
        """Arranca con **todos** los canales visibles, en el orden del archivo.

        Ninguno seleccionado, cada uno con la escala de su clase y sin
        desplazamiento. Las clases sin escala propia **no se miden acá**: medir
        necesita un tramo, y el tramo lo decide quien sabe qué se va a ver.
        Ver `fit_unscaled_kinds()`.

        Args:
            default_scale_uv: la escala de las clases que no tienen una propia,
                antes de medirlas. Por defecto, la de `config`.

        Raises:
            InvalidRecordingError: si `recording` no es un `Recording`.
            InvalidScaleError: si la escala no es un número finito.
        """
        if not isinstance(recording, Recording):
            raise InvalidRecordingError(
                "No se pudo preparar la presentación de los canales.",
                details=f"recording es {type(recording).__name__}, se esperaba Recording.",
            )
        # La escala inicial pasa por la misma guarda que `set_scale_uv`, que
        # declara ser el único lugar que recorta. Escribir el diccionario
        # directamente esquivaba el recorte entero: con `0.0` el visualizador
        # divide por cero, y con un valor negativo dibuja toda la señal
        # invertida mientras la escala de la izquierda anuncia "-50 µV".
        check_finite(
            default_scale_uv,
            error=InvalidScaleError,
            message="La escala vertical inicial no es un número válido.",
            details="Se esperaba un número finito.",
        )
        self._recording = recording
        #: La escala de las clases que no tienen una propia, antes de medirlas.
        self._escala_de_fabrica = clamp(default_scale_uv, MIN_SCALE_UV, MAX_SCALE_UV)
        self._visible: list[str] = recording.channel_names()
        self._selected: list[str] = []
        self._scales_uv: dict[str, float] = {
            canal.name: self._escala_inicial(canal) for canal in recording.channels
        }
        #: Cuántos µV se le restan a cada canal antes de dibujarlo. Arranca en
        #: cero para todos, que es el comportamiento que el programa tenía
        #: antes de que el desplazamiento existiera.
        self._offsets_uv: dict[str, float] = {
            nombre: 0.0 for nombre in recording.channel_names()
        }

    def _escala_inicial(self, canal: Channel) -> float:
        """Con qué escala arranca un canal: la de su clase.

        **Cada clase arranca con la suya**, y la escala de fábrica es el piso
        de las que no tienen una propia. Con una sola escala para todos, un
        canal respiratorio a 100 µV se sale de su carril y barre media
        pantalla; ver `DEFAULT_SCALE_BY_KIND_UV`. Las que quedan en el piso se
        miden después, en `fit_unscaled_kinds()`.
        """
        return clamp(
            DEFAULT_SCALE_BY_KIND_UV.get(canal.kind.value, self._escala_de_fabrica),
            MIN_SCALE_UV,
            MAX_SCALE_UV,
        )

    def _check_channels(self, channel_names: list[str]) -> None:
        """Rechaza cualquier nombre que el registro no tenga.

        Se apoya en `Recording.channel_by_name()`, que ya eleva el error con el
        mensaje correcto y la lista de canales disponibles en `details`.
        """
        for nombre in channel_names:
            self._recording.channel_by_name(nombre)

    def replace_recording(self, recording: Recording) -> list[str]:
        """Pasa a mostrar un registro procesado, conservando lo que sobrevive.

        Es la mitad de `Session.set_recording()` que toca a los canales, y la
        regla es conservar lo que sobrevive y no inventar:

        - Los **visibles** que sigan existiendo se conservan en su orden. Si no
          sobrevive ninguno se vuelve a mostrar todo, porque una pantalla vacía
          después de filtrar se lee como que el filtro borró la señal.
        - Los **seleccionados** que sigan existiendo se conservan; el resto se
          descarta en silencio, que es lo mismo que hace `set_visible_channels`
          con una selección que ya no aplica.
        - Las **escalas** y los **desplazamientos** se conservan por nombre de
          canal, y los canales nuevos arrancan con la escala de su clase, igual
          que al abrir el registro: un derivado no hereda la amplitud de nadie,
          pero un EOG derivado es un EOG.

        Returns:
            Los canales que no estaban, en el orden del registro nuevo. Los de
            clase sin escala propia **hay que medirlos** con
            `fit_unscaled_kinds()`, sobre el tramo que se está mirando.

        Raises:
            InvalidRecordingError: si no es un `Recording`.
        """
        if not isinstance(recording, Recording):
            raise InvalidRecordingError(
                "No se pudo reemplazar el registro con lo que se le pasó.",
                details=f"recording es {type(recording).__name__}, se esperaba Recording.",
            )
        nombres = recording.channel_names()
        sobreviven = [n for n in self._visible if n in nombres]
        self._visible = sobreviven if sobreviven else list(nombres)
        self._selected = [n for n in self._selected if n in nombres]
        nuevos = [nombre for nombre in nombres if nombre not in self._scales_uv]
        self._scales_uv = {
            canal.name: self._scales_uv.get(canal.name) or self._escala_inicial(canal)
            for canal in recording.channels
        }
        # Los desplazamientos se conservan **por nombre**, igual que las
        # escalas: un canal que sobrevive a un filtrado sigue apoyado donde el
        # usuario lo dejó.
        self._offsets_uv = {
            nombre: self._offsets_uv.get(nombre, 0.0) for nombre in nombres
        }
        self._recording = recording
        return nuevos

    # -- Canales visibles (V3_P, V4_F de "Visualización") -------------------

    @property
    def visible_channels(self) -> list[str]:
        """Nombres de los canales que se están mostrando, en orden.

        Devuelve una copia: la interfaz sólo quiere recorrerla, y prestarle la
        interna la dejaría reordenar los canales sin pasar por el setter.
        """
        return list(self._visible)

    def set_visible_channels(self, channel_names: list[str]) -> None:
        """Define qué canales se muestran y en qué orden.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
        """
        self._check_channels(channel_names)
        self._visible = list(channel_names)

    @property
    def selected_channels(self) -> list[str]:
        """Canales seleccionados por el usuario.

        Si hay canales seleccionados, los cambios de amplitud se aplican sólo
        a ellos; si no hay ninguno, se aplican a todos los visibles (V5_F).

        Devuelve una copia, por el mismo motivo que `visible_channels`.
        """
        return list(self._selected)

    def set_selected_channels(self, channel_names: list[str]) -> None:
        """Define los canales sobre los que actúan los cambios de amplitud.

        **No se exige que estén visibles.** Visibilidad y selección son ejes
        distintos —qué se dibuja y qué recibe los cambios de amplitud— y el
        pliego no los ata: seleccionar un canal y después ocultarlo deja su
        escala cambiando aunque no se vea, y eso es coherente con que al volver
        a mostrarlo aparezca como el usuario lo dejó.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
        """
        self._check_channels(channel_names)
        self._selected = list(channel_names)

    # -- Amplitud (V2_P, V5_F de "Visualización") ---------------------------

    def scale_uv(self, channel_name: str) -> float:
        """Escala vertical de un canal, en microvoltios.

        Es el número que se muestra en la escala de la izquierda del
        visualizador (V1_P): **cuántos microvoltios representa la altura del
        canal**.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
        """
        self._recording.channel_by_name(channel_name)
        return self._scales_uv[channel_name]

    def _channels_under_amplitude(self) -> list[str]:
        """Canales a los que llega un cambio de amplitud (V5_F).

        Los seleccionados si hay alguno; si no, todos los visibles. **Todas las
        vías que cambian la escala pasan por acá** —las flechas, «µV por
        carril», «Ajustar al panel», centrar y «Offset → 0»—, y el menú no lo
        repite.

        **Sin repetidos.** Mostrar el mismo canal dos veces es un uso soportado
        —`get_segment` lo documenta— y sin esta deduplicación cada pulsación de
        flecha le aplicaba el paso dos veces: el canal se escapaba del resto y
        el usuario no tenía cómo entender por qué.
        """
        elegidos = self._selected or self._visible
        return list(dict.fromkeys(elegidos))

    def _check_amplitude_factor(self, factor: float) -> None:
        """Rechaza un paso de amplitud con el que no se puede escalar.

        Sin esta guarda, un factor que no sea número sale como `TypeError` y el
        cero como `ZeroDivisionError`. Los dos atraviesan el `except
        PsgLabError` de la ventana principal.
        """
        check_finite(
            factor,
            error=InvalidScaleError,
            message="El paso de amplitud no sirve para escalar la señal.",
            details="factor tiene que ser un número finito mayor que cero.",
        )
        if factor <= 0:
            raise InvalidScaleError(
                "El paso de amplitud no sirve para escalar la señal.",
                details=f"factor tiene que ser mayor que cero; se recibió {factor}.",
            )

    def increase_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Aumenta la amplitud (flecha "Arriba").

        Se aplica a los canales seleccionados, o a todos los visibles si no
        hay ninguno seleccionado.

        **Aumentar la amplitud baja el número de `scale_uv`, no lo sube**, y
        conviene tenerlo presente porque parece al revés. `scale_uv` es cuántos
        µV representa la altura del canal: para que la señal se dibuje más
        grande, esa misma altura tiene que representar **menos** µV. Subir el
        número achicaría la onda, que es lo contrario de lo que espera quien
        aprieta la flecha.

        Args:
            factor: cuánto se multiplica la amplitud por cada pulsación. Por
                defecto, el paso de `config`.
        """
        self._check_amplitude_factor(factor)
        for nombre in self._channels_under_amplitude():
            self.set_scale_uv(nombre, self._scales_uv[nombre] / factor)

    def decrease_amplitude(self, factor: float = AMPLITUDE_STEP_FACTOR) -> None:
        """Reduce la amplitud (flecha "Abajo"). Mismo criterio de alcance."""
        self._check_amplitude_factor(factor)
        for nombre in self._channels_under_amplitude():
            self.set_scale_uv(nombre, self._scales_uv[nombre] * factor)

    def set_amplitude_scale(self, scale_uv: float) -> None:
        """Les da la misma escala a los canales bajo amplitud («µV por carril»).

        El alcance es el de las flechas: los seleccionados, o todos los
        visibles si no hay ninguno. Vive acá y no en el menú para que las
        flechas y el menú no puedan discrepar.

        Raises:
            InvalidScaleError: si la escala no es un número finito. Se comprueba
                antes de tocar ningún canal.
        """
        check_finite(
            scale_uv,
            error=InvalidScaleError,
            message="La escala pedida no es un número válido.",
            details="Se esperaba un número finito de microvoltios por carril.",
        )
        for nombre in self._channels_under_amplitude():
            self.set_scale_uv(nombre, scale_uv)

    def set_scale_uv(
        self,
        channel_name: str,
        scale_uv: float,
        minimum_uv: float = MIN_SCALE_UV,
        maximum_uv: float = MAX_SCALE_UV,
    ) -> None:
        """Fija la escala de un canal, recortada a los límites permitidos.

        Los límites existen para que el usuario no pueda dejar la pantalla
        inutilizable a fuerza de flechazos. Por defecto son los de `config`.

        Es el **único lugar que recorta**: las dos flechas y la medición de las
        clases sin escala propia delegan acá en vez de repetir la comprobación,
        para que no puedan discrepar.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
            InvalidScaleError: si la escala no es un número finito. `min(max(nan,
                lo), hi)` devuelve **NaN**, así que la forma corta de recortar no
                recorta nada: el canal dejaría de dibujarse y la escala de la
                izquierda anunciaría "nan µV".
        """
        self._recording.channel_by_name(channel_name)
        check_finite(
            scale_uv,
            error=InvalidScaleError,
            message=f"La escala pedida para el canal «{channel_name}» no es un número válido.",
            details="Se esperaba un número finito.",
        )
        self._scales_uv[channel_name] = clamp(scale_uv, minimum_uv, maximum_uv)

    # -- Desplazamiento vertical --------------------------------------------

    def offset_uv(self, channel_name: str) -> float:
        """Cuántos microvoltios se le restan a un canal antes de dibujarlo.

        Es el equivalente vertical de la escala, y responde a otra pregunta:
        `scale_uv` dice **cuánto se agranda** la señal, y esto **dónde se apoya**
        dentro de su carril.

        Hace falta porque un canal puede tener una línea de base muy lejos del
        cero —un termómetro marca 36, un canal de continua puede quedar
        cientos de µV corrido— y entonces se dibuja pegado al borde de su
        carril o directamente fuera. Antes la única salida era achicar la
        escala hasta que entrara, y con eso se perdía la señal.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
        """
        self._recording.channel_by_name(channel_name)
        return self._offsets_uv.get(channel_name, 0.0)

    def set_offset_uv(self, channel_name: str, offset_uv: float) -> None:
        """Fija el desplazamiento vertical de un canal.

        **No se recorta**, a diferencia de la escala, y la asimetría es
        deliberada: un recorte de la escala impide dejar la pantalla
        inutilizable, pero un offset grande no rompe nada —la señal sale del
        carril y se la vuelve a traer con «Offset → 0»—, y cuál es el valor
        razonable depende del canal: para un EEG son decenas de µV y para un
        termómetro, decenas de miles.

        Raises:
            ChannelNotFoundError: si el registro no tiene ese canal.
            InvalidScaleError: si el desplazamiento no es un número finito. Un
                NaN dejaría el canal sin dibujar y sin ningún cartel.
        """
        self._recording.channel_by_name(channel_name)
        check_finite(
            offset_uv,
            error=InvalidScaleError,
            message=(
                f"El desplazamiento pedido para el canal «{channel_name}» no es "
                "un número válido."
            ),
            details="Se esperaba un número finito.",
        )
        self._offsets_uv[channel_name] = float(offset_uv)

    def reset_offsets(self) -> None:
        """Devuelve al cero el desplazamiento de los canales bajo amplitud.

        Es «Offset → 0» de la referencia, y es la salida cuando el ajuste
        automático dejó un canal en un lugar raro. Mismo alcance que las
        flechas: los seleccionados, o todos los visibles si no hay selección.
        """
        for nombre in self._channels_under_amplitude():
            self._offsets_uv[nombre] = 0.0

    # -- Lo que se mide sobre un tramo --------------------------------------
    #
    # Las tres reciben el tramo en muestras, `[start_sample, stop_sample)`, y
    # no una época: este módulo no sabe de épocas. Un tramo imposible lo
    # rechaza `Recording.get_segment()` con `InvalidRecordingError`.

    def center_offsets(self, start_sample: int, stop_sample: int) -> None:
        """Apoya cada canal bajo amplitud en el centro de su carril.

        Es «Ajustar offset». Le da a cada canal el desplazamiento que lleva su
        promedio a cero **en el tramo que se está mirando**, no en la noche
        entera: la línea de base de un EEG deriva a lo largo de ocho horas, y
        centrar contra el promedio global dejaría la ventana actual corrida.

        Raises:
            InvalidRecordingError: si el tramo no existe en el registro.
        """
        for nombre in self._channels_under_amplitude():
            centro = self._centro(nombre, start_sample, stop_sample)
            if centro is not None:
                self.set_offset_uv(nombre, centro)

    def fit_to_pane(self, start_sample: int, stop_sample: int) -> None:
        """Ajusta la escala de cada canal bajo amplitud para que entre en su carril.

        Es «Ajustar al panel». Toma el mayor apartamiento respecto del
        desplazamiento vigente en el tramo, y lo convierte en la escala del
        canal. Un canal plano no cambia de escala: dividir por cero daría
        infinito y dejaría el canal invisible, y además no hay ninguna escala
        "correcta" para una línea recta.

        **Se mide después de restar el offset**, no antes: si no, un canal
        corrido pediría una escala enorme para entrar y la señal quedaría
        aplastada contra el eje.

        Raises:
            InvalidRecordingError: si el tramo no existe en el registro.
        """
        for nombre in self._channels_under_amplitude():
            apartamiento = self._apartamiento(nombre, start_sample, stop_sample)
            if apartamiento is not None:
                self.set_scale_uv(nombre, apartamiento)

    def fit_unscaled_kinds(
        self, channel_names: list[str], start_sample: int, stop_sample: int
    ) -> None:
        """Centra y mide la escala de los canales cuya clase no tiene una propia.

        Respiratorio y Otro no aparecen en `DEFAULT_SCALE_BY_KIND_UV` y no es
        un olvido: un termómetro rectal y un flujo oro-nasal no comparten ni
        unidad ni orden de magnitud, así que no hay ninguna escala de uso
        corriente que darles. Lo que sí se puede es mirarlos: con la escala de
        un EEG, un flujo respiratorio se sale de su carril y **barre media
        pantalla tapando seis canales**, que es exactamente lo que se veía al
        abrir un registro de verdad.

        Se miden sobre el tramo que se va a ver —la primera época al abrir, la
        actual cuando un análisis agrega un canal— y no sobre el registro
        entero: son ocho horas de señal. Un canal plano o sin datos se deja
        como está, por el mismo motivo que en `fit_to_pane()`.

        **Primero se centra.** Una temperatura de 37 °C que varía una décima,
        medida contra el cero, daría una escala de 37 y una señal pegada al
        borde de su carril, lejos de su nombre y como una línea sin forma.
        Centrada en su media, la escala mide lo que el canal varía.

        Args:
            channel_names: los canales a ajustar; los de clase con escala
                propia se saltean. **No es el alcance de las flechas**: al
                abrir no hay selección que respetar.

        Raises:
            ChannelNotFoundError: si se pide un canal que el registro no tiene.
            InvalidRecordingError: si el tramo no existe en el registro.
        """
        self._check_channels(channel_names)
        for nombre in channel_names:
            canal = self._recording.channel_by_name(nombre)
            if canal.kind.value in DEFAULT_SCALE_BY_KIND_UV:
                continue
            centro = self._centro(nombre, start_sample, stop_sample)
            if centro is not None:
                self.set_offset_uv(nombre, centro)
            apartamiento = self._apartamiento(nombre, start_sample, stop_sample)
            if apartamiento is not None:
                self.set_scale_uv(nombre, apartamiento)

    def _finitos(self, channel_name: str, start_sample: int, stop_sample: int) -> np.ndarray:
        """Las muestras con valor de un canal en un tramo, sin los NaN ni los infinitos.

        **Sin los valores que no son números.** `np.mean` con un solo NaN
        devuelve NaN, y como desplazamiento dejaría el canal sin dibujar y sin
        ningún cartel. Con el máximo pasa lo mismo: el canal quedaría sin
        ajustar aunque el resto del tramo sirviera.
        """
        tramo = self._recording.get_segment(start_sample, stop_sample, [channel_name])
        return tramo[np.isfinite(tramo)]

    def _centro(self, channel_name: str, start_sample: int, stop_sample: int) -> float | None:
        """La media de un canal en un tramo, o `None` si no hay nada que centrar."""
        finitos = self._finitos(channel_name, start_sample, stop_sample)
        if finitos.size == 0:
            return None
        return float(np.mean(finitos))

    def _apartamiento(
        self, channel_name: str, start_sample: int, stop_sample: int
    ) -> float | None:
        """Cuánto se aparta un canal de su desplazamiento en un tramo.

        Es la medida con la que se ajusta una escala, y la usan dos: «Ajustar al
        panel» y la medición de las clases sin escala propia. Devuelve `None`
        cuando no hay nada que medir —un canal plano, uno sin datos, uno todo
        NaN—: no existe ninguna escala "correcta" para una línea recta, y
        dividir por cero dejaría el canal invisible.
        """
        finitos = self._finitos(channel_name, start_sample, stop_sample)
        if finitos.size == 0:
            return None
        apartamiento = float(np.max(np.abs(finitos - self.offset_uv(channel_name))))
        if apartamiento <= 0.0 or not np.isfinite(apartamiento):
            return None
        return apartamiento
