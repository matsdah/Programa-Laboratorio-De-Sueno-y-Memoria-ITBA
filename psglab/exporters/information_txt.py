"""Exportación de "Informacion.txt".

Resumen legible del registro y de lo que se hizo sobre él:

    - nombre del archivo
    - frecuencia de muestreo
    - duración total, en horas y en puntos (muestras)
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

    La nomenclatura sale de `scoring.nomenclature`. La frecuencia de muestreo
    tiene que aparecer siempre: es lo único que permite convertir a segundos
    los "puntos" de "Anotaciones.txt", y ese archivo no la lleva.
    """
    raise NotImplementedError("Pendiente: componer el texto del informe.")


def format_duration(seconds: float) -> str:
    """Formatea una duración en horas, minutos y segundos.

    Ejemplo: 3661.5 -> "1 h 01 min 01,50 s".
    """
    raise NotImplementedError("Pendiente: formatear la duración.")
