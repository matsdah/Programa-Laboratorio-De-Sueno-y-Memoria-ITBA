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

**El informe de sueño estándar** (`sleep_summary()`) es lo que un laboratorio
busca primero y el pliego no pide: tiempo en cama, tiempo total de sueño,
eficiencia, latencias, vigilia después del inicio, porcentaje de cada fase e
índice de arousals. Se agregó en el hito 79 como una sección al final de
`Informacion.txt`, sin tocar lo que ya traía, y **sus definiciones las tiene que
confirmar el laboratorio**: están escritas en el docstring de la función.

Cubre del pliego: alimenta V3_F de "Archivo de salida" (duración por fase,
métricas de tiempo y resumen de anotaciones).
"""

# `statistics` acá es la biblioteca estándar y no este mismo módulo: Python 3
# resuelve los imports de forma absoluta, y este archivo es
# `psglab.exporters.statistics`, no `statistics`. El nombre choca sólo a la
# vista.
from dataclasses import dataclass
from statistics import fmean, median, stdev
from typing import Final

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


def _exigir_registro_coherente(n_samples: int, sampling_rate: float, que: str) -> None:
    """Rechaza una cantidad de muestras o una frecuencia que no sirven."""
    check_finite(
        n_samples,
        error=InvalidRecordingError,
        message=f"No se pudo calcular {que}.",
        details="n_samples tiene que ser una cantidad de muestras finita y no negativa.",
        minimum=0,
    )
    check_finite(
        sampling_rate,
        error=InvalidRecordingError,
        message=f"No se pudo calcular {que}.",
        details="sampling_rate tiene que ser un número finito y positivo.",
    )
    if sampling_rate <= 0:
        raise InvalidRecordingError(
            f"No se pudo calcular {que}.",
            details=f"sampling_rate = {sampling_rate}, se esperaba un número positivo.",
        )


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
    _exigir_registro_coherente(n_samples, sampling_rate, "el tiempo en cada fase")

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


# -- El informe de sueño estándar (hito 79) ------------------------------------

#: Las fases que son sueño, de las dos nomenclaturas. **MT no lo es**: el
#: tiempo de movimiento de Rechtschaffen y Kales no se puede asignar a ninguna
#: fase, y contarlo como sueño inflaría el tiempo total con lo que justamente
#: no se pudo leer.
SLEEP_STAGES: Final[frozenset[SleepStage]] = frozenset(
    {
        SleepStage.S1, SleepStage.S2, SleepStage.S3, SleepStage.S4,
        SleepStage.N1, SleepStage.N2, SleepStage.N3,
        SleepStage.REM, SleepStage.R,
    }
)

#: El sueño REM, con la etiqueta de cada nomenclatura.
REM_STAGES: Final[frozenset[SleepStage]] = frozenset({SleepStage.REM, SleepStage.R})


@dataclass(frozen=True)
class SleepSummary:
    """El informe de sueño estándar, en segundos salvo que diga otra cosa.

    Lo que no existe vale `None` y no cero: una noche sin REM no tiene
    latencia de REM, y un cero diría que el REM empezó con el sueño.

    Attributes:
        time_in_bed: el registro entero.
        total_sleep_time: la suma de las ventanas de sueño.
        sleep_efficiency: el tiempo de sueño sobre el tiempo en cama, en %.
        sleep_latency: desde el comienzo del registro hasta la primera
            ventana de sueño.
        rem_latency: desde la primera ventana de sueño hasta la primera de REM.
        sleep_period_time: desde la primera ventana de sueño hasta el final de
            la última.
        wake_after_sleep_onset: la vigilia dentro del período de sueño.
        stage_percent: el porcentaje de cada fase de sueño de la nomenclatura
            sobre el tiempo total de sueño, en el orden de la nomenclatura.
        arousals: las ventanas de sueño con arousal marcado.
        arousal_index: arousals por hora de sueño.
        unscored_windows: las ventanas sin scorear, que no son ni sueño ni
            vigilia y hacen incompleto todo lo de arriba.
    """

    time_in_bed: float
    total_sleep_time: float
    sleep_efficiency: float | None
    sleep_latency: float | None
    rem_latency: float | None
    sleep_period_time: float
    wake_after_sleep_onset: float | None
    stage_percent: dict[SleepStage, float]
    arousals: int
    arousal_index: float | None
    unscored_windows: int


def sleep_summary(
    scoring: Scoring,
    n_samples: int,
    sampling_rate: float,
    window_seconds: float = WINDOW_SECONDS,
) -> SleepSummary:
    """Calcula el informe de sueño estándar de un registro scoreado.

    **Las definiciones, para que el laboratorio las confirme** (decisión 7
    del hito 79):

    - **Tiempo en cama** es el registro entero: el programa no tiene marcas
      de luces apagadas y encendidas, y el registro es lo más cercano.
    - **Sueño** son S1 a S4, N1 a N3 y REM. MT no, ni lo sin scorear.
    - **Las latencias se cuentan hasta el comienzo de la ventana**: la de
      sueño desde el comienzo del registro, la de REM desde la primera
      ventana de sueño. Es la definición de la AASM.
    - **La vigilia después del inicio** es la vigilia entre la primera y la
      última ventana de sueño; la del final de la noche, después de
      despertarse, no cuenta. Es el período de sueño menos el tiempo de sueño
      cuando todo está scoreado.
    - **Los arousals son ventanas marcadas**, no eventos: dos arousals en la
      misma ventana cuentan uno, que es lo que guarda `Scoring`. Se cuentan
      los de las ventanas de sueño, porque un arousal es por definición
      desde el sueño.

    Todas las duraciones usan la duración real de cada ventana, como
    `stage_durations_seconds()`: la última, incompleta, aporta lo que dura.

    Raises:
        InvalidRecordingError: si el registro que se describe no es coherente.
    """
    _exigir_registro_coherente(n_samples, sampling_rate, "el informe de sueño")
    fases = scoring.stages()
    duraciones = [
        window_duration(i, int(n_samples), sampling_rate, window_seconds).total_seconds()
        for i in range(len(fases))
    ]
    de_sueno = [i for i, fase in enumerate(fases) if fase in SLEEP_STAGES]
    en_cama = sum(duraciones)
    sueno = sum(duraciones[i] for i in de_sueno)

    latencia = latencia_rem = vigilia = None
    periodo = 0.0
    if de_sueno:
        inicio, fin = de_sueno[0], de_sueno[-1]
        latencia = sum(duraciones[:inicio])
        periodo = sum(duraciones[inicio : fin + 1])
        vigilia = sum(
            duraciones[i] for i in range(inicio, fin + 1) if fases[i] is SleepStage.WAKE
        )
        primer_rem = next((i for i in de_sueno if fases[i] in REM_STAGES), None)
        if primer_rem is not None:
            latencia_rem = sum(duraciones[inicio:primer_rem])

    por_fase = {
        fase: sum(duraciones[i] for i in de_sueno if fases[i] is fase)
        for fase in stages_of(scoring.nomenclature)
        if fase in SLEEP_STAGES
    }
    arousals = sum(1 for i in de_sueno if scoring.get(i).arousal)
    return SleepSummary(
        time_in_bed=en_cama,
        total_sleep_time=sueno,
        sleep_efficiency=100.0 * sueno / en_cama if en_cama > 0 else None,
        sleep_latency=latencia,
        rem_latency=latencia_rem,
        sleep_period_time=periodo,
        wake_after_sleep_onset=vigilia,
        stage_percent={
            fase: (100.0 * segundos / sueno if sueno > 0 else 0.0)
            for fase, segundos in por_fase.items()
        },
        arousals=arousals,
        arousal_index=arousals / (sueno / 3600.0) if sueno > 0 else None,
        unscored_windows=sum(1 for fase in fases if fase is SleepStage.UNSCORED),
    )
