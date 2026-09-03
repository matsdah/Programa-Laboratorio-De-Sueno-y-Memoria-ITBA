"""Exportación de "Anotaciones.txt".

Una línea por anotación, con tres campos separados por barra vertical:

    Label_Annotation | Puntos_Emp | Duracion_Puntos

"Puntos" son muestras del registro, no segundos. Guardarlo así evita perder
precisión por redondeo y no depende de la frecuencia de muestreo del archivo.

PENDIENTE DE CONFIRMACIÓN: si el índice de la primera muestra es 0 o 1, y si
conviene escribir también la frecuencia de muestreo en una cabecera para que
el archivo se pueda interpretar sin tener el registro al lado.

Cubre del pliego: V2_F de "Archivo de salida".
"""

from pathlib import Path

from psglab.config import ANNOTATIONS_SEPARATOR
from psglab.core.annotations import Annotation, AnnotationSet


def export_annotations(
    annotations: AnnotationSet,
    path: Path,
    separator: str = ANNOTATIONS_SEPARATOR,
) -> None:
    """Escribe todas las anotaciones en un archivo de texto.

    Las anotaciones se escriben ordenadas por muestra de inicio, no por orden
    de creación: el archivo se lee de principio a fin de la noche.

    Args:
        separator: separador de campos. Por defecto, el de `config`.
    """
    raise NotImplementedError("Pendiente: escribir una línea por anotación.")


def format_line(annotation: Annotation, separator: str = ANNOTATIONS_SEPARATOR) -> str:
    """Arma una línea del archivo a partir de una anotación.

    Si la etiqueta que puso el usuario contiene el separador, hay que
    reemplazarlo o escaparlo: si no, el archivo queda ilegible para quien lo
    parsee después. El usuario puede escribir lo que quiera en el nombre de
    una clase nueva.
    """
    raise NotImplementedError("Pendiente: componer la línea con sus tres campos.")
