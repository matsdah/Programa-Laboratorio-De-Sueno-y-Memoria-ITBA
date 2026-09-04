"""Archivos de salida del programa.

Tres archivos de texto, uno por módulo: `Scoring.txt`, `Anotaciones.txt` e
`Informacion.txt`. El usuario elige cuál exportar (V4_F).

Los formatos son texto plano y fáciles de leer con cualquier herramienta.
Eso es deliberado: los archivos de salida son la vía por la que el scoring
entra a los análisis estadísticos del laboratorio, y no deberían necesitar
este programa para poder leerse.

Cubre del pliego: ningún ID propio del paquete. Los tres archivos de salida
los cubren sus módulos.
"""

from typing import Final

from psglab.config import (
    ANNOTATIONS_FILENAME,
    INFORMATION_FILENAME,
    SCORING_FILENAME,
)

#: Nombre de archivo propuesto para cada tipo de exportación. Lo usa el
#: diálogo de guardado de la ventana principal (V4_F de "Archivo de salida")
#: para sugerir el nombre que fija el pliego. Las claves son las que recibe
#: `MainWindow.export`.
DEFAULT_FILENAMES: Final[dict[str, str]] = {
    "scoring": SCORING_FILENAME,
    "annotations": ANNOTATIONS_FILENAME,
    "information": INFORMATION_FILENAME,
}
