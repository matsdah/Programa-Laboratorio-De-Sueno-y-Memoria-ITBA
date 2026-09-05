"""Scoring del registro: fase y arousal de cada ventana de 30 segundos.

Guarda una entrada por ventana desde el principio, incluso para las ventanas
que el usuario todavía no miró. Eso es lo que permite que el histograma tenga
el tamaño total de la noche desde el arranque y muestre en blanco lo no
anotado (V1_P del histograma), y que el usuario pueda scorear una parte
alejada del registro sin haber pasado por las anteriores.

Cubre del pliego: V1_F, V2_F, V3_F de "Scoring de la señal".
"""

from dataclasses import dataclass, replace

from psglab.core.nomenclature import Nomenclature, SleepStage, convert, is_valid
from psglab.utils.errors import InvalidStageError, WindowOutOfRangeError


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
        if n_windows < 0:
            raise WindowOutOfRangeError(
                "No se puede crear el scoring de un registro con una cantidad "
                "negativa de ventanas.",
                details=f"n_windows = {n_windows}.",
            )
        self._scores: list[EpochScore] = [EpochScore() for _ in range(n_windows)]
        self._nomenclature = nomenclature

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
        if not is_valid(stage, self._nomenclature):
            raise InvalidStageError(
                f"La fase '{stage.value}' no pertenece a la nomenclatura "
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
        """
        self._check_window(window_index)
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
        """
        if target is self._nomenclature:
            return
        self._scores = [
            replace(score, stage=convert(score.stage, target)) for score in self._scores
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
