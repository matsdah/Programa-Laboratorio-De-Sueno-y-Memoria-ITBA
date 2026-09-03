"""Exportación de "Informacion.txt".

Resumen legible del registro y de lo que se hizo sobre él:

    - nombre del archivo
    - duración total, en horas y en puntos (muestras)
    - duración en cada fase de sueño, si está scoreado
    - métricas de tiempo por fase: promedio, desvío estándar y mediana
    - lista de anotaciones con cantidad y tiempo promedio, si está anotado

Las secciones que no correspondan se omiten con una explicación en vez de
mostrar ceros: un archivo que dice "el registro no está scoreado" es más útil
que uno lleno de "0,00 s", que se puede confundir con un registro scoreado
sin ninguna ventana en esa fase.

Cubre del pliego: V3_F de "Archivo de salida".
"""

from pathlib import Path

from psglab.core.annotations import AnnotationSet
from psglab.core.recording import Recording
from psglab.core.scoring import Scoring


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
    raise NotImplementedError("Pendiente: componer y escribir el archivo completo.")


def build_report(
    recording: Recording,
    scoring: Scoring | None,
    annotations: AnnotationSet | None,
) -> str:
    """Arma el texto completo del informe.

    Separado de la escritura para poder testear el contenido y para poder
    mostrar el mismo informe en pantalla sin generar un archivo.
    """
    raise NotImplementedError("Pendiente: componer el texto del informe.")


def format_duration(seconds: float) -> str:
    """Formatea una duración en horas, minutos y segundos.

    Ejemplo: 3661.5 -> "1 h 01 min 01,50 s".
    """
    raise NotImplementedError("Pendiente: formatear la duración.")
