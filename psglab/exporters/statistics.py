"""Estadísticas del registro scoreado.

Cálculos puros sobre el scoring y las anotaciones, sin escribir ningún
archivo. Los consume `information_txt.py`, pero se mantienen separados porque
también los va a querer la interfaz para mostrar un resumen en pantalla, y
porque así se pueden testear sin tocar el disco.

**Dos funciones miden tiempo y no miden lo mismo.** La distinción sobrevivió a
una discusión y conviene no volver a borrarla:

- `stage_durations_seconds()` suma la duración **real** de cada ventana, así que
  la última —que casi siempre está incompleta— aporta lo que dura de verdad. Es
  una tabla que se publica en `Informacion.txt` por fase, y ahí un error se
  imprime.
- `scored_time_seconds()` cuenta **ventanas completas**, a propósito, y por eso
  sobreestima hasta 29,99 segundos. No es un error: es otra magnitud. Su
  docstring explica por qué forzarla a coincidir con `Recording.duration_seconds`
  falsificaría una de las dos.

Cubre del pliego: alimenta V3_F de "Archivo de salida" (duración por fase,
métricas de tiempo y resumen de anotaciones).
"""

# `statistics` acá es la biblioteca estándar y no este mismo módulo: Python 3
# resuelve los imports de forma absoluta, y este archivo es
# `psglab.exporters.statistics`, no `statistics`. El nombre choca sólo a la
# vista.
from statistics import fmean, median, stdev

from psglab.config import WINDOW_SECONDS
from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import SleepStage, stages_of
from psglab.core.scoring import Scoring
from psglab.core.windows import window_duration
from psglab.utils.errors import InvalidRecordingError
from psglab.utils.validation import check_finite


def _filas(scoring: Scoring) -> list[SleepStage]:
    """Las fases que le corresponden a la tabla de este scoring.

    Son las de su nomenclatura, **estén o no presentes**: una fila en cero dice
    que esa noche no tuvo N3, que es información. `UNSCORED` se agrega sólo si
    hay alguna ventana sin scorear, porque "sin scorear" no es una fase y su
    fila sobra en un registro terminado.
    """
    filas = list(stages_of(scoring.nomenclature))
    if SleepStage.UNSCORED in scoring.stages():
        filas.append(SleepStage.UNSCORED)
    return filas


def stage_window_counts(scoring: Scoring) -> dict[SleepStage, int]:
    """Cantidad de ventanas en cada fase."""
    cuentas = {fase: 0 for fase in _filas(scoring)}
    for fase in scoring.stages():
        cuentas[fase] = cuentas.get(fase, 0) + 1
    return cuentas


def stage_durations_seconds(
    scoring: Scoring,
    n_samples: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> dict[SleepStage, float]:
    """Tiempo total pasado en cada fase, en segundos.

    **Suma la duración real de cada ventana en vez de multiplicar la cuenta.**
    La última ventana del registro casi siempre está incompleta, y multiplicar
    le atribuiría a su fase hasta 30 segundos que el registro no tiene. El
    número se publica en `Informacion.txt`, así que el error se publicaría con
    él.

    Por eso pide `n_samples` y `sampling_rate`, que es lo que necesita
    `windows.window_duration()`. Van sueltos y no como `Recording` para no
    romper el estilo del módulo: `annotation_summary()` ya recibe la frecuencia
    suelta.

    Raises:
        InvalidRecordingError: si el registro que se describe no es coherente.
    """
    check_finite(
        n_samples,
        error=InvalidRecordingError,
        message="No se pudo calcular el tiempo en cada fase.",
        details="n_samples tiene que ser una cantidad de muestras finita y no negativa.",
        minimum=0,
    )
    check_finite(
        sampling_rate,
        error=InvalidRecordingError,
        message="No se pudo calcular el tiempo en cada fase.",
        details="sampling_rate tiene que ser un número finito y positivo.",
    )
    if sampling_rate <= 0:
        raise InvalidRecordingError(
            "No se pudo calcular el tiempo en cada fase.",
            details=f"sampling_rate = {sampling_rate}, se esperaba un número positivo.",
        )

    duraciones = {fase: 0.0 for fase in _filas(scoring)}
    for indice, fase in enumerate(scoring.stages()):
        real = window_duration(indice, int(n_samples), sampling_rate, window_seconds)
        duraciones[fase] = duraciones.get(fase, 0.0) + real.total_seconds()
    return duraciones


def stage_episodes(scoring: Scoring) -> dict[SleepStage, list[int]]:
    """Episodios continuos de cada fase, medidos en ventanas.

    Un episodio es un tramo seguido de ventanas de la misma fase. Es lo que
    permite calcular el promedio, el desvío y la mediana que pide el pliego:
    esas métricas se calculan sobre la duración de los episodios, no sobre las
    ventanas sueltas, que todas duran lo mismo y darían desvío cero.
    """
    episodios: dict[SleepStage, list[int]] = {fase: [] for fase in _filas(scoring)}
    anterior: SleepStage | None = None
    largo = 0

    for fase in scoring.stages():
        if fase is anterior:
            largo += 1
            continue
        if anterior is not None:
            episodios.setdefault(anterior, []).append(largo)
        anterior, largo = fase, 1

    if anterior is not None:
        episodios.setdefault(anterior, []).append(largo)
    return episodios


def episode_metrics(
    episodes: list[int],
    window_seconds: float = WINDOW_SECONDS,
) -> dict[str, float]:
    """Promedio, desvío estándar y mediana de la duración de los episodios.

    **Mantiene la firma en ventanas completas, a diferencia de
    `stage_durations_seconds()`.** Mide la estructura del sueño —qué tan largos
    son los tramos— y no un total publicado: que el último episodio de la noche
    termine unos segundos antes no cambia si los episodios de N2 duran diez
    minutos o dos.

    Returns:
        Diccionario con las claves "promedio", "desvio" y "mediana", en
        segundos. Con menos de dos episodios el desvío no está definido y se
        devuelve 0.0.
    """
    if not episodes:
        return {"promedio": 0.0, "desvio": 0.0, "mediana": 0.0}

    duraciones = [episodio * window_seconds for episodio in episodes]
    return {
        "promedio": fmean(duraciones),
        # `stdev` de la biblioteca estándar eleva con un solo dato. Con un solo
        # episodio el desvío no está indefinido por un problema de cálculo sino
        # porque no hay dispersión que medir.
        "desvio": stdev(duraciones) if len(duraciones) > 1 else 0.0,
        "mediana": median(duraciones),
    }


def annotation_summary(
    annotations: AnnotationSet,
    sampling_rate: float,
) -> dict[str, dict[str, float]]:
    """Resumen de las anotaciones por clase.

    Las anotaciones se guardan en muestras, así que la frecuencia es lo único
    que las convierte a tiempo. Es el mismo motivo por el que
    `Informacion.txt` la imprime siempre: `Anotaciones.txt` no la lleva.

    Returns:
        Para cada clase, un diccionario con "cantidad" y "duracion_promedio"
        en segundos. Sólo aparecen las clases **con anotaciones**: una clase
        registrada y sin usar no es parte del resumen del trabajo.

    Raises:
        InvalidRecordingError: si la frecuencia no sirve para convertir.
    """
    check_finite(
        sampling_rate,
        error=InvalidRecordingError,
        message="No se pudo resumir las anotaciones.",
        details="sampling_rate tiene que ser un número finito y positivo.",
    )
    if sampling_rate <= 0:
        raise InvalidRecordingError(
            "No se pudo resumir las anotaciones.",
            details=f"sampling_rate = {sampling_rate}, se esperaba un número positivo.",
        )

    por_clase: dict[str, list[float]] = {}
    for anotacion in annotations.all():
        por_clase.setdefault(anotacion.label, []).append(
            anotacion.duration_samples / sampling_rate
        )

    return {
        etiqueta: {"cantidad": float(len(duraciones)), "duracion_promedio": fmean(duraciones)}
        for etiqueta, duraciones in por_clase.items()
    }


def scored_time_seconds(
    scoring: Scoring,
    window_seconds: float = WINDOW_SECONDS,
) -> float:
    """Segundos abarcados por las ventanas del scoring.

    **No es la duración del registro y no hay que confundirlas.** Ésta cuenta
    ventanas completas, y la última del registro puede estar incompleta: para un
    registro que termina a mitad de ventana, este número **sobreestima hasta
    29,99 segundos**. La duración real la da `Recording.duration_seconds`, que
    es `n_samples / sampling_rate`.

    Se llamaba `total_recording_time`, y con ese nombre `Informacion.txt` iba a
    imprimir dos números distintos —éste y el de `Recording`— presentados los
    dos como "duración total", sin que nada explicara por qué no cerraban.
    Miden cosas distintas y las dos son correctas; forzarlas a coincidir
    falsificaría una.
    """
    return scoring.n_windows * window_seconds
