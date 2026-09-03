"""Estadísticas del registro scoreado.

Cálculos puros sobre el scoring y las anotaciones, sin escribir ningún
archivo. Los consume `information_txt.py`, pero se mantienen separados porque
también los va a querer la interfaz para mostrar un resumen en pantalla, y
porque así se pueden testear sin tocar el disco.

Cubre del pliego: alimenta V3_F de "Archivo de salida" (duración por fase,
métricas de tiempo y resumen de anotaciones).
"""

from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import SleepStage
from psglab.core.scoring import Scoring


def stage_window_counts(scoring: Scoring) -> dict[SleepStage, int]:
    """Cantidad de ventanas en cada fase."""
    raise NotImplementedError("Pendiente: contar las ventanas por fase.")


def stage_durations_seconds(scoring: Scoring, window_seconds: float) -> dict[SleepStage, float]:
    """Tiempo total pasado en cada fase, en segundos."""
    raise NotImplementedError("Pendiente: multiplicar las cuentas por la duración de la ventana.")


def stage_episodes(scoring: Scoring) -> dict[SleepStage, list[int]]:
    """Episodios continuos de cada fase, medidos en ventanas.

    Un episodio es un tramo seguido de ventanas de la misma fase. Es lo que
    permite calcular el promedio, el desvío y la mediana que pide el pliego:
    esas métricas se calculan sobre la duración de los episodios, no sobre las
    ventanas sueltas, que todas duran lo mismo y darían desvío cero.
    """
    raise NotImplementedError("Pendiente: recorrer las fases y agrupar los tramos continuos.")


def episode_metrics(episodes: list[int], window_seconds: float) -> dict[str, float]:
    """Promedio, desvío estándar y mediana de la duración de los episodios.

    Returns:
        Diccionario con las claves "promedio", "desvio" y "mediana", en
        segundos. Con menos de dos episodios el desvío no está definido y se
        devuelve 0.0.
    """
    raise NotImplementedError("Pendiente: calcular las métricas de los episodios.")


def annotation_summary(
    annotations: AnnotationSet,
    sampling_rate: float,
) -> dict[str, dict[str, float]]:
    """Resumen de las anotaciones por clase.

    Returns:
        Para cada clase, un diccionario con "cantidad" y "duracion_promedio"
        en segundos.
    """
    raise NotImplementedError("Pendiente: agrupar las anotaciones por clase y promediar.")


def total_recording_time(scoring: Scoring, window_seconds: float) -> float:
    """Duración total del registro en segundos, según la cantidad de ventanas."""
    raise NotImplementedError("Pendiente: multiplicar las ventanas por su duración.")
