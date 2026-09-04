"""Exportación de "Anotaciones.txt".

Una línea por anotación, con tres campos separados por barra vertical:

    Label_Annotation | Puntos_Emp | Duracion_Puntos

"Puntos" son muestras del registro, no segundos, como pide el pliego. Guardarlo
así evita perder precisión por redondeo: una posición en muestras es exacta, y
convertirla a segundos y volver no siempre devuelve el mismo número.

El precio es que **el archivo no se puede interpretar sin la frecuencia de
muestreo**, que es lo único que traduce muestras a tiempo. Esa frecuencia se
registra en "Informacion.txt".

La primera muestra del registro es la **0**, confirmado con el cliente: es la
base del programa, la de numpy y la de MNE, así que exportar y reimportar no
necesitan conversión. Vive en `config.ANNOTATION_SAMPLE_BASE` y no se escribe a
mano acá, para que cambiarlo siga siendo cambiar una línea. Ojo si alguien
procesa el archivo en MATLAB, que cuenta desde 1.

No se escribe una cabecera con la frecuencia acá, a diferencia de
"Scoring.txt", que sí declara su nomenclatura: la fase de una ventana se
interpreta mal en silencio, mientras que una posición sin frecuencia
directamente no se puede convertir y el problema salta enseguida.

Cubre del pliego: V2_F de "Archivo de salida".
"""

from pathlib import Path

from psglab.config import ANNOTATION_SAMPLE_BASE, ANNOTATIONS_SEPARATOR
from psglab.core.annotations import Annotation, AnnotationSet


def export_annotations(
    annotations: AnnotationSet,
    path: Path,
    separator: str = ANNOTATIONS_SEPARATOR,
    sample_base: int = ANNOTATION_SAMPLE_BASE,
) -> None:
    """Escribe todas las anotaciones en un archivo de texto.

    Las anotaciones se escriben ordenadas por muestra de inicio, no por orden
    de creación: el archivo se lee de principio a fin de la noche.

    Args:
        separator: separador de campos. Por defecto, el de `config`.
        sample_base: índice de la primera muestra del registro. Se suma a las
            posiciones al escribirlas. Por defecto, el de `config`, que es 0.
    """
    raise NotImplementedError("Pendiente: escribir una línea por anotación.")


def format_line(
    annotation: Annotation,
    separator: str = ANNOTATIONS_SEPARATOR,
    sample_base: int = ANNOTATION_SAMPLE_BASE,
) -> str:
    """Arma una línea del archivo a partir de una anotación.

    Si la etiqueta que puso el usuario contiene el separador, hay que
    reemplazarlo o escaparlo: si no, el archivo queda ilegible para quien lo
    parsee después. El usuario puede escribir lo que quiera en el nombre de
    una clase nueva.
    """
    raise NotImplementedError("Pendiente: componer la línea con sus tres campos.")
