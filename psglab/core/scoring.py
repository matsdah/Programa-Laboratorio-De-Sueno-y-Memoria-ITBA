"""Scoring del registro: fase y arousal de cada ventana de 30 segundos.

Guarda una entrada por ventana desde el principio, incluso para las ventanas
que el usuario todavía no miró. Eso es lo que permite que el histograma tenga
el tamaño total de la noche desde el arranque y muestre en blanco lo no
anotado (V1_P del histograma), y que el usuario pueda scorear una parte
alejada del registro sin haber pasado por las anteriores.

**Las fases sugeridas viven al lado y no adentro** (hito 75). Un clasificador
puede proponer la fase de cada ventana, y esa propuesta se guarda en una capa
aparte: `EpochScore.stage` sigue queriendo decir «la eligió una persona». Así
los exportadores, las estadísticas y el trabajo sin exportar no tienen que
distinguir nada —leen `stage`, que una sugerencia nunca toca— y una sugerencia
no puede pisar una fase puesta a mano porque no escribe donde vive ésa.

Cubre del pliego: V1_F, V2_F, V3_F de "Scoring de la señal".
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from psglab.core.nomenclature import (
    Nomenclature,
    SleepStage,
    check_nomenclature,
    convert,
    is_valid,
)
from psglab.utils.errors import InvalidStageError, WindowOutOfRangeError
from psglab.utils.validation import check_index


@dataclass(frozen=True)
class EpochScore:
    """Scoring de una única ventana de 30 segundos.

    **Inmutable a propósito.** `Scoring.get()` devuelve uno de estos, y si se
    pudiera escribir encima —`scoring.get(i).stage = SleepStage.N2`— se
    esquivaría `Scoring.set_stage()`, que es la única guarda que impide asignar
    una fase ajena a la nomenclatura activa. Para cambiar el scoring de una
    ventana hay que pasar por `set_stage()` o `set_arousal()`.

    Attributes:
        stage: fase de sueño. UNSCORED si el usuario todavía no la scoreó.
        arousal: presencia de un arousal en la ventana (V2_F). Es
            independiente de la fase: una ventana puede ser S2 con arousal.
    """

    stage: SleepStage = SleepStage.UNSCORED
    arousal: bool = False

    @property
    def is_scored(self) -> bool:
        """Indica si la ventana ya fue scoreada por el usuario."""
        return self.stage is not SleepStage.UNSCORED


@dataclass(frozen=True)
class StageSuggestion:
    """La fase que propone un clasificador para una ventana (hito 75).

    **No es scoring**: nadie la eligió. Se confirma con
    `Scoring.accept_suggestions()` o scoreando la ventana a mano.

    Attributes:
        stage: la fase propuesta. Nunca `UNSCORED`: no sugerir nada se dice
            con `None` en la lista de `Scoring.set_suggestions()`.
        confidence: la probabilidad que el clasificador le da a esa fase, de
            0 a 1.
    """

    stage: SleepStage
    confidence: float


class Scoring:
    """Scoring completo de un registro.

    Se crea con tantas entradas como ventanas tenga el registro, todas en
    UNSCORED.
    """

    def __init__(self, n_windows: int, nomenclature: Nomenclature) -> None:
        """Crea un scoring vacío.

        Args:
            n_windows: cantidad total de ventanas del registro (VENMAX). **Cero
                es válido** y da un scoring vacío: es lo que corresponde a un
                registro sin muestras, y no hay nada incoherente en él.
            nomenclature: nomenclatura elegida por el usuario.

        Raises:
            WindowOutOfRangeError: si `n_windows` es negativo. Un scoring con
                menos de cero ventanas no describe ningún registro.
        """
        if not isinstance(n_windows, int) or isinstance(n_windows, bool) or n_windows < 0:
            raise WindowOutOfRangeError(
                "No se puede crear el scoring de un registro con esa cantidad de "
                "ventanas.",
                details=f"n_windows = {n_windows!r}, se esperaba un entero no negativo.",
            )
        # Sin esta guarda, una nomenclatura equivocada se acepta y explota mucho
        # después, con un `KeyError` crudo desde `nomenclature.stages_of()` la
        # primera vez que alguien asigna una fase. Es el fallo lejos del bug que
        # el resto del modelo existe para evitar.
        if not isinstance(nomenclature, Nomenclature):
            raise InvalidStageError(
                "El scoring se pidió con una nomenclatura que no existe.",
                details=f"nomenclature es {type(nomenclature).__name__}, se esperaba Nomenclature.",
            )
        self._scores: list[EpochScore] = [EpochScore() for _ in range(n_windows)]
        self._nomenclature = nomenclature
        self._suggestions: list[StageSuggestion | None] = [None] * n_windows

    @property
    def n_windows(self) -> int:
        """Cantidad total de ventanas."""
        return len(self._scores)

    @property
    def nomenclature(self) -> Nomenclature:
        """Nomenclatura activa."""
        return self._nomenclature

    def _check_window(self, window_index: int) -> None:
        """Rechaza un índice que no corresponde a ninguna ventana.

        Se comprueba el borde negativo además del superior. En Python un índice
        negativo cuenta desde el final, así que sin esta guarda pedir la ventana
        −1 devolvería la última de la noche como si fuera la primera: un
        resultado plausible y equivocado, que es la peor forma de fallar.
        """
        check_index(
            window_index,
            error=WindowOutOfRangeError,
            message="Se pidió una ventana que no se puede ubicar en el registro.",
            details="Se esperaba un número de ventana entero.",
        )
        if not 0 <= window_index < self.n_windows:
            raise WindowOutOfRangeError(
                f"La ventana {window_index + 1} no existe en este registro, que "
                f"tiene {self.n_windows}.",
                details=f"window_index = {window_index} (base 0), n_windows = {self.n_windows}.",
            )

    def get(self, window_index: int) -> EpochScore:
        """Scoring de una ventana (índice base 0).

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro.
        """
        self._check_window(window_index)
        return self._scores[window_index]

    def set_stage(self, window_index: int, stage: SleepStage) -> None:
        """Asigna la fase de una ventana (V1_F).

        `UNSCORED` es una asignación válida: es como el usuario **borra** el
        scoring de una ventana que marcó por error.

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro. Se
                comprueba **antes** que la fase: si los dos están mal, "esa
                ventana no existe" es la respuesta más útil.
            InvalidStageError: si la fase no pertenece a la nomenclatura activa.
        """
        self._check_window(window_index)
        # El tipo antes de la pertenencia: `is_valid("N2", ...)` devuelve False
        # correctamente, y el mensaje que explica el rechazo era el que explotaba
        # con un AttributeError al pedirle `.value` a una cadena.
        if not isinstance(stage, SleepStage):
            raise InvalidStageError(
                "Se quiso asignar algo que no es una fase de sueño.",
                details=f"stage es {type(stage).__name__}, se esperaba SleepStage.",
            )
        if not is_valid(stage, self._nomenclature):
            raise InvalidStageError(
                f"La fase «{stage.value}» no pertenece a la nomenclatura "
                f"{self._nomenclature.value}, así que no se puede asignar.",
                details=(
                    f"stage = {stage.name}, nomenclatura = {self._nomenclature.name}."
                ),
            )
        self._scores[window_index] = replace(self._scores[window_index], stage=stage)

    def set_arousal(self, window_index: int, arousal: bool) -> None:
        """Marca o desmarca la presencia de un arousal en una ventana (V2_F).

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro.
            InvalidStageError: si `arousal` no es un booleano. `EpochScore` es
                inmutable justamente para que toda escritura pase por acá, y
                dejar entrar una cadena haría que `Scoring.txt` escriba `"si"` en
                la columna del arousal, o que la exportación falle al final de la
                sesión con la noche entera scoreada.
        """
        self._check_window(window_index)
        if not isinstance(arousal, bool):
            raise InvalidStageError(
                "La marca de arousal sólo puede estar puesta o no puesta.",
                details=f"arousal es {type(arousal).__name__}, se esperaba bool.",
            )
        self._scores[window_index] = replace(self._scores[window_index], arousal=arousal)

    def change_nomenclature(self, target: Nomenclature) -> None:
        """Cambia la nomenclatura y traduce todas las fases ya scoreadas (V3_F).

        La traducción puede perder información (ver `nomenclature.convert`), así
        que la interfaz debe avisarle al usuario antes de llamar a este método
        sobre un registro ya scoreado.

        **Los arousals se conservan**: no dependen de la nomenclatura, y
        perderlos al cambiarla haría desaparecer V2_F sin que nadie lo pida.

        Cambiar a la nomenclatura que ya está activa no hace nada, pero tampoco
        es un error: la interfaz puede llamar sin preguntar.

        **La guarda es propia y no la de `convert()`** (hito 48). La validación
        vivía adentro de la comprensión de abajo, que corre una vez por ventana
        scoreada: sobre un scoring **sin scorear** el bucle no itera, así que
        una nomenclatura inventada se guardaba tal cual. El objeto quedaba con
        una cadena donde va un enum, y el siguiente `export_scoring()` moría con
        un `AttributeError` crudo —que atraviesa el `except PsgLabError` de la
        ventana y le deja al investigador una traza de Python—.

        Lo encontró la auditoría de los tests: la fila de `CONTRATOS` de este
        método construye justamente un scoring recién creado, así que
        certificaba como seguro el único camino en el que la guarda no
        disparaba.
        """
        check_nomenclature(target)
        if target is self._nomenclature:
            return
        self._scores = [
            replace(score, stage=convert(score.stage, target)) for score in self._scores
        ]
        # Las sugeridas también: una N3 sugerida sobre R&K tiene que ser S3, o
        # confirmarla después asignaría una fase ajena a la nomenclatura.
        self._suggestions = [
            None if sugerida is None else replace(sugerida, stage=convert(sugerida.stage, target))
            for sugerida in self._suggestions
        ]
        self._nomenclature = target

    def scored_windows(self) -> int:
        """Cantidad de ventanas ya scoreadas.

        Sirve para mostrarle al usuario el avance y para que el histograma
        sepa cuánto dejar en blanco.
        """
        return sum(1 for score in self._scores if score.is_scored)

    def stages(self) -> list[SleepStage]:
        """Lista de fases, una por ventana, en orden.

        Es lo que consume el histograma para dibujarse.

        Devuelve una **lista nueva** en cada llamada, no la interna: quien la
        recibe sólo quiere leerla, y prestarle la de adentro dejaría que el
        histograma corrompiera el scoring sin pasar por `set_stage()`.
        """
        return [score.stage for score in self._scores]

    # -- Fases sugeridas (hito 75) -------------------------------------------

    def set_suggestions(self, suggestions: Sequence[StageSuggestion | None]) -> None:
        """Guarda las fases que propone un clasificador, una por ventana.

        **Reemplaza las anteriores enteras**, y no toca ninguna fase elegida a
        mano: las sugerencias viven en otra capa (ver el docstring del módulo).

        **Se traducen a la nomenclatura activa**, en vez de rechazarse como hace
        `set_stage()`. El clasificador propone en AASM porque así fue entrenado,
        y no es un error de quien llama que el usuario esté scoreando en R&K;
        la traducción es la misma de `change_nomenclature()`, con la misma
        pérdida: N3 pasa a S3.

        **Se valida todo antes de guardar nada**, así que una lista con un solo
        elemento malo deja las sugerencias como estaban.

        Args:
            suggestions: una entrada por ventana, `None` donde no hay
                propuesta. Tiene que tener exactamente `n_windows` entradas: una
                lista corrida en una ventana sugiere toda la noche desfasada,
                y eso es plausible y equivocado.

        Raises:
            WindowOutOfRangeError: si la lista no tiene una entrada por ventana.
            InvalidStageError: si alguna entrada no es una sugerencia válida.
        """
        if isinstance(suggestions, (str, bytes)) or not isinstance(suggestions, Sequence):
            raise InvalidStageError(
                "Las fases sugeridas llegaron en un formato que no se puede leer.",
                details=f"suggestions es {type(suggestions).__name__}, se esperaba una lista.",
            )
        if len(suggestions) != self.n_windows:
            raise WindowOutOfRangeError(
                f"Se sugirieron fases para {len(suggestions)} ventanas y el registro "
                f"tiene {self.n_windows}.",
                details="set_suggestions() espera una entrada por ventana.",
            )
        traducidas: list[StageSuggestion | None] = []
        for posicion, sugerida in enumerate(suggestions):
            if sugerida is None:
                traducidas.append(None)
                continue
            _check_suggestion(sugerida, posicion)
            traducidas.append(
                replace(sugerida, stage=convert(sugerida.stage, self._nomenclature))
            )
        self._suggestions = traducidas

    def suggestion(self, window_index: int) -> StageSuggestion | None:
        """La fase sugerida para una ventana **que todavía nadie scoreó**.

        Sobre una ventana scoreada devuelve `None` aunque haya una guardada: lo
        que eligió una persona gana, y mostrar al lado lo que el clasificador
        pensaba sólo invita a dudar de una decisión ya tomada. Si la fase se
        borra, la sugerencia vuelve a aparecer.

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro.
        """
        self._check_window(window_index)
        if self._scores[window_index].is_scored:
            return None
        return self._suggestions[window_index]

    def pending_suggestions(self) -> int:
        """Cuántas ventanas sin scorear tienen una fase sugerida."""
        return sum(
            1
            for score, sugerida in zip(self._scores, self._suggestions)
            if sugerida is not None and not score.is_scored
        )

    def accept_suggestions(self, min_confidence: float = 0.0) -> int:
        """Confirma las sugerencias pendientes con al menos esa confianza.

        Confirmar es escribirlas como fase, por `set_stage()`, así que desde
        ahí son scoring como cualquier otro: se exportan y cuentan como trabajo
        sin exportar. **Sólo sobre ventanas sin scorear**: una fase puesta a
        mano no se pisa nunca.

        Args:
            min_confidence: de 0 a 1. Con 0 se confirman todas.

        Returns:
            Cuántas ventanas se confirmaron.

        Raises:
            InvalidStageError: si `min_confidence` no es un número entre 0 y 1.
        """
        if (
            isinstance(min_confidence, bool)
            or not isinstance(min_confidence, (int, float))
            or not 0.0 <= min_confidence <= 1.0
        ):
            raise InvalidStageError(
                "La confianza mínima para confirmar las fases sugeridas tiene que "
                "estar entre 0 y 100 %.",
                details=f"min_confidence = {min_confidence!r}.",
            )
        confirmadas = 0
        for indice, sugerida in enumerate(self._suggestions):
            if sugerida is None or self._scores[indice].is_scored:
                continue
            if sugerida.confidence >= min_confidence:
                self.set_stage(indice, sugerida.stage)
                confirmadas += 1
        return confirmadas

    def clear_suggestions(self) -> None:
        """Descarta todas las fases sugeridas. Las elegidas a mano quedan."""
        self._suggestions = [None] * self.n_windows


def _check_suggestion(sugerida: object, posicion: int) -> None:
    """Rechaza lo que no sea una sugerencia que se pueda confirmar después.

    Se revisa al guardar y no al confirmar: una confianza `NaN` guardada haría
    que ninguna comparación contra el umbral fuera cierta, y la sugerencia no
    se confirmaría nunca sin que nada dijera por qué. **El rango la rechaza
    sin guarda propia**: `0 <= nan <= 1` es falso, igual que con un infinito.
    """
    donde = f"ventana {posicion + 1}"
    if not isinstance(sugerida, StageSuggestion):
        raise InvalidStageError(
            "Una de las fases sugeridas no se puede leer.",
            details=f"{donde}: es {type(sugerida).__name__}, se esperaba StageSuggestion.",
        )
    if not isinstance(sugerida.stage, SleepStage) or sugerida.stage is SleepStage.UNSCORED:
        raise InvalidStageError(
            "Una de las fases sugeridas no es una fase de sueño.",
            details=f"{donde}: stage = {sugerida.stage!r}.",
        )
    confianza = sugerida.confidence
    if (
        isinstance(confianza, bool)
        or not isinstance(confianza, (int, float))
        or not 0.0 <= confianza <= 1.0
    ):
        raise InvalidStageError(
            "Una de las fases sugeridas trae una confianza que no es una probabilidad.",
            details=f"{donde}: confidence = {confianza!r}, se esperaba un número entre 0 y 1.",
        )
