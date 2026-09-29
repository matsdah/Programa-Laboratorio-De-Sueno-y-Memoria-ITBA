"""Deshacer y rehacer los cambios del scoring y de las anotaciones.

Scorear pasa sola a la ventana siguiente, así que una tecla de más scorea la
ventana que viene; confirmar todas las fases sugeridas, o importar un scoring
encima, cambian cientos de ventanas de un golpe. Todo eso se tiene que poder
volver atrás.

## Fotos y no comandos

**Se guardan fotos del trabajo, no las operaciones que lo cambiaron.** Una foto
es la nomenclatura, las fases de cada ventana, las sugeridas y las anotaciones.
Deshacer es volver a la foto anterior. La alternativa —guardar cada operación
con su inversa— obliga a que cada camino que cambia el scoring se acuerde de
registrarse bien, y son muchos: scorear, el arousal, anotar con el mouse o el
teclado, corregir un borde, cambiar la clase, borrar, importar las marcas,
confirmar y descartar sugeridas, cambiar la nomenclatura, importar un scoring.
Con fotos alcanza con llamar a `record()` después de cualquier cambio: si nada
cambió, no se guarda nada.

**Son baratas**: `EpochScore`, `StageSuggestion` y `Annotation` son
inmutables, así que una foto guarda referencias y no copia ventanas. Mil
ventanas son ocho kilobytes de punteros; `HISTORY_LIMIT` fotos, un par de
megas en el peor caso.

## Qué no se deshace

Lo que no es trabajo del investigador: moverse de ventana, la amplitud, los
canales visibles, la señal —filtrar tiene su propio «Volver a la señal
original»— y los colores de las clases, que son preferencias.

Cubre del pliego: ningún ID; es infraestructura del trabajo del investigador.
"""

from typing import Final, NamedTuple

from psglab.core.annotations import Annotation
from psglab.core.nomenclature import Nomenclature
from psglab.core.scoring import EpochScore, StageSuggestion
from psglab.core.session import Session
from psglab.core.windows import sample_to_window
from psglab.utils.errors import PsgLabError

#: Cuántos cambios se pueden deshacer. **Doscientos** alcanzan para volver
#: atrás una tanda de scoring larga sin que la memoria dependa de la noche.
HISTORY_LIMIT: Final[int] = 200


class _Foto(NamedTuple):
    """El trabajo en un momento. Ver «Fotos y no comandos»."""

    nomenclatura: Nomenclature
    ventanas: tuple[EpochScore, ...]
    sugeridas: tuple[StageSuggestion | None, ...]
    anotaciones: tuple[Annotation, ...]


class History:
    """Las fotos del trabajo de una sesión, para ir y volver entre ellas."""

    def __init__(self, session: Session, limit: int = HISTORY_LIMIT) -> None:
        """Empieza con la foto de cómo está el trabajo ahora.

        Args:
            session: la sesión cuyo scoring y anotaciones se siguen.
            limit: cuántos cambios se pueden deshacer, de 1 en adelante.

        Raises:
            PsgLabError: si no es una sesión o el límite no es un entero
                positivo.
        """
        if not isinstance(session, Session):
            raise PsgLabError(
                "No se pudo preparar el historial de cambios.",
                details=f"session es {type(session).__name__}, se esperaba Session.",
            )
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise PsgLabError(
                "No se pudo preparar el historial de cambios.",
                details=f"limit = {limit!r}, se esperaba un entero positivo.",
            )
        self._session = session
        self._limite = limit
        #: Las fotos hasta la actual, que es la última.
        self._pasado: list[_Foto] = [self._foto()]
        #: Lo que se deshizo, para rehacerlo; la próxima a rehacer es la última.
        self._futuro: list[_Foto] = []
        self._ventana: int | None = None

    @property
    def changed_window(self) -> int | None:
        """Dónde está lo último que se deshizo o rehízo, para ir a verlo.

        Una fase o un arousal, en su ventana; una anotación, en la de su
        comienzo. None si fue sólo la nomenclatura o las sugeridas, que no
        están en ninguna ventana en particular.
        """
        return self._ventana

    @property
    def can_undo(self) -> bool:
        """Si hay algún cambio para deshacer, contando el que no se registró."""
        return len(self._pasado) > 1 or self._foto() != self._pasado[-1]

    @property
    def can_redo(self) -> bool:
        """Si hay algo deshecho para rehacer, y nada cambió desde entonces."""
        return bool(self._futuro) and self._foto() == self._pasado[-1]

    def record(self) -> bool:
        """Guarda cómo está el trabajo, si cambió desde la última foto.

        Se llama después de cualquier cambio. **Un cambio nuevo borra lo que
        se podía rehacer**, como en cualquier programa: rehacer después de
        haber hecho otra cosa aplicaría un cambio sobre un trabajo que ya no es
        el suyo.

        Returns:
            Si se guardó una foto nueva.
        """
        foto = self._foto()
        if foto == self._pasado[-1]:
            return False
        self._pasado.append(foto)
        self._futuro.clear()
        # La foto actual no cuenta: `limit` son los cambios que se deshacen.
        del self._pasado[: -(self._limite + 1)]
        return True

    def undo(self) -> bool:
        """Vuelve a como estaba el trabajo antes del último cambio.

        Registra antes el cambio que hubiera sin registrar, así que deshacer
        siempre deshace lo último que se hizo. Dónde estaba el cambio queda en
        `changed_window`.

        Returns:
            Si había algo que deshacer.
        """
        self.record()
        if len(self._pasado) < 2:
            return False
        actual = self._pasado.pop()
        self._futuro.append(actual)
        anterior = self._pasado[-1]
        self._aplicar(anterior)
        self._ventana = self._donde_cambio(actual, anterior)
        return True

    def redo(self) -> bool:
        """Vuelve a hacer el último cambio deshecho.

        Returns:
            Si había algo que rehacer: no, si algo cambió después de deshacer.
        """
        self.record()
        if not self._futuro:
            return False
        siguiente = self._futuro.pop()
        actual = self._pasado[-1]
        self._pasado.append(siguiente)
        self._aplicar(siguiente)
        self._ventana = self._donde_cambio(actual, siguiente)
        return True

    def reset(self) -> None:
        """Olvida lo que se podía deshacer y rehacer, y parte de cómo está.

        Para un trabajo que no se hizo en esta sesión, como el que se recupera
        de la copia: deshacerlo sería perderlo.
        """
        self._pasado = [self._foto()]
        self._futuro = []

    def _foto(self) -> _Foto:
        scoring = self._session.scoring
        return _Foto(
            scoring.nomenclature,
            tuple(scoring.get(i) for i in range(scoring.n_windows)),
            scoring.suggestions(),
            tuple(self._session.annotations.all()),
        )

    def _aplicar(self, foto: _Foto) -> None:
        """Deja el trabajo de la sesión como estaba en la foto.

        **Se escribe sobre el scoring y las anotaciones de la sesión**, sin
        reemplazarlos: la ventana y las herramientas los tienen tomados, y
        `Session.set_scoring()` además los daría por exportados. La foto salió
        de esta misma sesión, así que todo lo que trae es válido.
        """
        scoring = self._session.scoring
        if scoring.nomenclature is not foto.nomenclatura:
            scoring.change_nomenclature(foto.nomenclatura)
        for indice, ventana in enumerate(foto.ventanas):
            if scoring.get(indice) != ventana:
                scoring.set_stage(indice, ventana.stage)
                scoring.set_arousal(indice, ventana.arousal)
        scoring.set_suggestions(foto.sugeridas)
        anotaciones = self._session.annotations
        actuales = set(anotaciones.all())
        for sobrante in actuales - set(foto.anotaciones):
            anotaciones.remove(sobrante)
        for faltante in foto.anotaciones:
            # Su clase sigue estando: `AnnotationSet` no tiene cómo borrar una.
            if faltante not in actuales:
                anotaciones.add(faltante)

    def _donde_cambio(self, antes: _Foto, despues: _Foto) -> int | None:
        """La primera ventana en que difieren dos fotos. Ver `changed_window`."""
        for indice, (uno, otro) in enumerate(zip(antes.ventanas, despues.ventanas)):
            if uno != otro:
                return indice
        distintas = set(antes.anotaciones) ^ set(despues.anotaciones)
        if distintas:
            primera = min(distintas, key=lambda a: a.onset_sample)
            return sample_to_window(
                primera.onset_sample, self._session.recording.sampling_rate
            )
        return None
