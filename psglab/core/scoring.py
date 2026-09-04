"""Scoring del registro: fase y arousal de cada ventana de 30 segundos.

Guarda una entrada por ventana desde el principio, incluso para las ventanas
que el usuario todavía no miró. Eso es lo que permite que el histograma tenga
el tamaño total de la noche desde el arranque y muestre en blanco lo no
anotado (V1_P del histograma), y que el usuario pueda scorear una parte
alejada del registro sin haber pasado por las anteriores.

Cubre del pliego: V1_F, V2_F, V3_F de "Scoring de la señal".
"""

from dataclasses import dataclass

from psglab.core.nomenclature import Nomenclature, SleepStage


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
        raise NotImplementedError("Pendiente: comparar la fase con UNSCORED.")


class Scoring:
    """Scoring completo de un registro.

    Se crea con tantas entradas como ventanas tenga el registro, todas en
    UNSCORED.
    """

    def __init__(self, n_windows: int, nomenclature: Nomenclature) -> None:
        """Crea un scoring vacío.

        Args:
            n_windows: cantidad total de ventanas del registro (VENMAX).
            nomenclature: nomenclatura elegida por el usuario.
        """
        raise NotImplementedError("Pendiente: inicializar la lista de EpochScore.")

    @property
    def n_windows(self) -> int:
        """Cantidad total de ventanas."""
        raise NotImplementedError("Pendiente: devolver la cantidad de ventanas.")

    @property
    def nomenclature(self) -> Nomenclature:
        """Nomenclatura activa."""
        raise NotImplementedError("Pendiente: devolver la nomenclatura activa.")

    def get(self, window_index: int) -> EpochScore:
        """Scoring de una ventana (índice base 0).

        Raises:
            WindowOutOfRangeError: si el índice cae fuera del registro.
        """
        raise NotImplementedError("Pendiente: devolver el scoring de la ventana.")

    def set_stage(self, window_index: int, stage: SleepStage) -> None:
        """Asigna la fase de una ventana (V1_F).

        Raises:
            InvalidStageError: si la fase no pertenece a la nomenclatura activa.
        """
        raise NotImplementedError("Pendiente: validar y asignar la fase.")

    def set_arousal(self, window_index: int, arousal: bool) -> None:
        """Marca o desmarca la presencia de un arousal en una ventana (V2_F)."""
        raise NotImplementedError("Pendiente: asignar el arousal.")

    def change_nomenclature(self, target: Nomenclature) -> None:
        """Cambia la nomenclatura y traduce todas las fases ya scoreadas (V3_F).

        La traducción puede perder información (ver `nomenclature.convert`), así
        que la interfaz debe avisarle al usuario antes de llamar a este método
        sobre un registro ya scoreado.
        """
        raise NotImplementedError("Pendiente: convertir todas las fases y cambiar la nomenclatura.")

    def scored_windows(self) -> int:
        """Cantidad de ventanas ya scoreadas.

        Sirve para mostrarle al usuario el avance y para que el histograma
        sepa cuánto dejar en blanco.
        """
        raise NotImplementedError("Pendiente: contar las ventanas scoreadas.")

    def stages(self) -> list[SleepStage]:
        """Lista de fases, una por ventana, en orden.

        Es lo que consume el histograma para dibujarse.
        """
        raise NotImplementedError("Pendiente: devolver la lista de fases.")
