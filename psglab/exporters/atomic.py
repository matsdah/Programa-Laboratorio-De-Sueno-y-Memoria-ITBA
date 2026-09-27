"""Escribir un archivo de salida entero o no escribirlo.

Los exportadores escribían directo sobre el destino, así que un corte de luz,
el disco lleno o un error a mitad de camino dejaban el archivo **truncado**:
un `Scoring.txt` con la mitad de la noche, que se lee sin error y le da a los
análisis del laboratorio un resultado plausible y equivocado. Y si el destino
ya existía —la exportación de ayer—, se perdía también esa.

Acá se escribe en un archivo provisorio **al lado del destino**, en la misma
carpeta y por eso en el mismo disco, y recién al terminar se lo renombra con
`os.replace()`, que es una operación de un solo paso: o queda el archivo
nuevo entero, o el que había. Es lo mismo que ya hacían las preferencias y la
copia de recuperación.

**El provisorio tiene un nombre fijo y no uno de `tempfile`.** `mkstemp()` lo
crea con permisos 0600, y el renombrado los conserva: el archivo exportado
quedaría ilegible para el resto del laboratorio en una carpeta compartida.
Con un nombre fijo se crea como cualquier otro archivo; si quedó uno de un
corte anterior, se pisa, porque es nuestro.

Cubre del pliego: ningún ID; es infraestructura de los tres archivos de salida.
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def provisional_path(path: Path) -> Path:
    """Dónde se escribe antes de renombrar: al lado del destino, oculto.

    «Scoring.txt» se escribe primero en «.Scoring.txt.tmp».
    """
    return path.with_name(f".{path.name}.tmp")


@contextmanager
def atomic_destination(path: Path) -> Iterator[Path]:
    """Da la ruta donde escribir; al salir bien, la pone en el lugar de `path`.

    Si lo que escribe eleva —o el renombrado falla—, el provisorio se borra y
    `path` queda como estaba: sin crear si no existía, con lo de antes si
    existía. El error sale igual, para que quien exporta lo muestre.

    Ejemplo::

        with atomic_destination(destino) as provisorio:
            provisorio.write_text(texto, encoding="utf-8")
    """
    provisorio = provisional_path(Path(path))
    try:
        yield provisorio
        os.replace(provisorio, path)
    except BaseException:
        try:
            provisorio.unlink()
        except OSError:
            pass
        raise


def write_text_atomically(path: Path, text: str) -> None:
    """Escribe un texto en UTF-8, entero o nada. Ver `atomic_destination()`."""
    with atomic_destination(path) as provisorio:
        provisorio.write_text(text, encoding="utf-8")
