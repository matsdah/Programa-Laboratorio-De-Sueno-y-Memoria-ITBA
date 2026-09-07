"""Exportación de "Informacion.txt".

Resumen legible del registro y de lo que se hizo sobre él:

    - nombre del archivo
    - frecuencia de muestreo
    - duración del registro, en horas y en puntos (muestras)
    - tiempo scoreado, que **no es lo mismo** y puede ser hasta 30 segundos
      mayor: cuenta ventanas completas y la última puede estar incompleta. Se
      imprimen los dos, rotulados distinto, en vez de elegir uno y que el otro
      contradiga la cuenta de fases.
    - nomenclatura con la que se scoreó, si está scoreado
    - duración en cada fase de sueño, si está scoreado
    - métricas de tiempo por fase: promedio, desvío estándar y mediana
    - lista de anotaciones con cantidad y tiempo promedio, si está anotado

**La frecuencia de muestreo no es un dato decorativo: es lo único que hace
interpretable a "Anotaciones.txt".** Ese archivo guarda las posiciones en
muestras, y sin la frecuencia no se pueden pasar a tiempo.

Ojo con una trampa: V4_F deja exportar **uno solo** de los tres archivos, así
que no se puede dar por sentado que este acompañe a los otros. Por eso
"Scoring.txt" declara su nomenclatura en su propia cabecera en vez de depender
de este archivo. Acá se la repite igual, porque es parte del resumen del
trabajo, pero **la copia que importa para reimportar es la del propio
"Scoring.txt"**.

Las secciones que no correspondan se omiten con una explicación en vez de
mostrar ceros: un archivo que dice "el registro no está scoreado" es más útil
que uno lleno de "0,00 s", que se puede confundir con un registro scoreado
sin ninguna ventana en esa fase.

Cubre del pliego: V3_F de "Archivo de salida".
"""

from pathlib import Path

from psglab.config import WINDOW_SECONDS
from psglab.core.annotations import AnnotationSet
from psglab.core.nomenclature import SleepStage, stage_label
from psglab.core.recording import Recording
from psglab.core.scoring import Scoring
from psglab.exporters.statistics import (
    annotation_summary,
    episode_metrics,
    scored_time_seconds,
    stage_durations_seconds,
    stage_episodes,
    stage_window_counts,
)


def _numero(valor: float, decimales: int = 2) -> str:
    """Un número con coma decimal, que es la convención del idioma del informe."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def export_information(
    recording: Recording,
    scoring: Scoring | None,
    annotations: AnnotationSet | None,
    path: Path,
) -> None:
    """Escribe el archivo de información del registro.

    Args:
        scoring: None si el registro todavía no está scoreado.
        annotations: None si no hay anotaciones.
    """
    path.write_text(build_report(recording, scoring, annotations), encoding="utf-8")


def build_report(
    recording: Recording,
    scoring: Scoring | None,
    annotations: AnnotationSet | None,
) -> str:
    """Arma el texto completo del informe.

    Separado de la escritura para poder testear el contenido y para poder
    mostrar el mismo informe en pantalla sin generar un archivo.

    La nomenclatura sale de `scoring.nomenclature`. La frecuencia de muestreo
    tiene que aparecer siempre: es lo único que permite convertir a segundos
    los "puntos" de "Anotaciones.txt", y ese archivo no la lleva.
    """
    lineas: list[str] = [
        "INFORMACIÓN DEL REGISTRO",
        "========================",
        "",
        f"Archivo: {recording.file_path.name}",
        f"Frecuencia de muestreo: {_numero(recording.sampling_rate, 1)} Hz",
        f"Canales: {recording.n_channels}",
        f"Duración del registro: {format_duration(recording.duration_seconds)} "
        f"({recording.n_samples} puntos)",
    ]
    if recording.start_time is not None:
        lineas.append(f"Inicio: {recording.start_time:%Y-%m-%d %H:%M:%S}")

    lineas += ["", "CANALES", "-------"]
    for canal in recording.channels:
        origen = ""
        if (
            canal.original_sampling_rate is not None
            and canal.original_sampling_rate != recording.sampling_rate
        ):
            # Un canal remuestreado hacia arriba tiene menos resolución real que
            # la que sugiere la matriz. Callarlo haría que se lo lea como si
            # fuera igual de fino que el EEG.
            origen = f", original {_numero(canal.original_sampling_rate, 1)} Hz"
        unidad = canal.unit if canal.unit else "sin unidad"
        lineas.append(f"  {canal.name} — {canal.kind.value} [{unidad}]{origen}")

    lineas += ["", "SCORING", "-------"]
    if scoring is None:
        lineas.append("El registro todavía no está scoreado.")
    else:
        lineas += _seccion_de_scoring(recording, scoring)

    lineas += ["", "ANOTACIONES", "-----------"]
    if annotations is None or not annotations.all():
        lineas.append("El registro no tiene anotaciones.")
    else:
        resumen = annotation_summary(annotations, recording.sampling_rate)
        for etiqueta, datos in sorted(resumen.items()):
            cantidad = int(datos["cantidad"])
            promedio = format_duration(datos["duracion_promedio"])
            lineas.append(f"  {etiqueta}: {cantidad}, duración promedio {promedio}")

    return "\n".join(lineas) + "\n"


def _seccion_de_scoring(recording: Recording, scoring: Scoring) -> list[str]:
    """El bloque de scoring, que es el que tiene las dos medidas de tiempo.

    Se separa porque es lo más largo del informe y porque `build_report()` se
    lee mejor viendo qué secciones hay que qué dice cada una.
    """
    abarcado = scored_time_seconds(scoring)
    lineas = [
        f"Nomenclatura: {scoring.nomenclature.value}",
        f"Ventanas: {scoring.n_windows}, de {_numero(WINDOW_SECONDS, 0)} s cada una",
        f"Ventanas scoreadas: {scoring.scored_windows()} de {scoring.n_windows}",
        # Los dos números de tiempo, rotulados distinto a propósito: el de
        # arriba es la duración real del registro y éste cuenta ventanas
        # completas, así que sobreestima hasta una ventana. Los dos son
        # correctos y miden cosas distintas.
        f"Tiempo abarcado por las ventanas: {format_duration(abarcado)}",
    ]

    duraciones = stage_durations_seconds(
        scoring, recording.n_samples, recording.sampling_rate
    )
    cuentas = stage_window_counts(scoring)
    lineas += ["", "Tiempo en cada fase:"]
    for fase, segundos in duraciones.items():
        cantidad = cuentas.get(fase, 0)
        lineas.append(
            f"  {stage_label(fase):5} {format_duration(segundos):>22}"
            f"   ({cantidad} {'ventana' if cantidad == 1 else 'ventanas'})"
        )

    lineas += [
        "",
        "Métricas por fase, sobre episodios continuos:",
        f"  {'fase':5} {'promedio':>18} {'desvío':>18} {'mediana':>18}",
    ]
    for fase, episodios in stage_episodes(scoring).items():
        # Las ventanas sin scorear sí cuentan en la tabla de tiempos —dicen
        # cuánto falta— pero no acá: un tramo de "todavía no lo miré" no es una
        # estructura del sueño, y ponerlo entre los episodios de N2 y N3 invita
        # a leerlo como si lo fuera.
        if not episodios or fase is SleepStage.UNSCORED:
            continue
        metricas = episode_metrics(episodios)
        lineas.append(
            f"  {stage_label(fase):5} "
            f"{format_duration(metricas['promedio']):>18} "
            f"{format_duration(metricas['desvio']):>18} "
            f"{format_duration(metricas['mediana']):>18}"
        )
    return lineas


def format_duration(seconds: float) -> str:
    """Formatea una duración en horas, minutos y segundos.

    Ejemplo: 3661.5 -> "1 h 01 min 01,50 s".
    """
    horas, resto = divmod(float(seconds), 3600)
    minutos, segundos = divmod(resto, 60)
    # Los segundos van con cero adelante, como los minutos: alinea las columnas
    # del informe y es lo que fija el ejemplo de arriba.
    return f"{int(horas)} h {int(minutos):02d} min {segundos:05.2f} s".replace(".", ",")
