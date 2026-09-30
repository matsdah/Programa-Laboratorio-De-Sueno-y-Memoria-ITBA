"""Escribir un archivo de salida entero o conservar el anterior.

Cada exportación se escribe en un archivo exclusivo al lado del destino y se
renombra recién al terminar. El descriptor permanece abierto durante todas las
escrituras; si algo falla, se cierra y se borra el provisorio.

El destino anterior queda intacto ante un error de escritura, como un disco
lleno, antes del reemplazo. El nombre aleatorio y la creación exclusiva evitan
que un sobrante de una exportación previa o dos exportaciones simultáneas
compartan el archivo temporal. Los permisos 0666 sujetos a `umask` mantienen
los permisos habituales de los archivos compartidos del laboratorio.

La carpeta de destino debe ser de confianza: otro proceso con permiso para
renombrar archivos dentro de ella podría sustituir el provisorio después de
cerrarlo y antes de `os.replace()`. En Windows hay que cerrarlo para renombrar.

Cubre del pliego: ningún ID; es infraestructura de los archivos de salida.
"""

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, TextIO


@contextmanager
def atomic_destination(
    path: Path,
    mode: str = "w",
    *,
    encoding: str | None = "utf-8",
    newline: str | None = None,
) -> Iterator[TextIO | BinaryIO]:
    """Dar un flujo abierto y reemplazar el destino al terminar bien.

    Se crea con permisos normales (0666 sujetos a `umask`). Un nombre aleatorio
    evita que archivos viejos o exportaciones simultáneas compartan provisorio.
    El descriptor abierto evita que un enlace simbólico desvíe la escritura.
    """
    if mode not in {"w", "wb"}:
        raise ValueError("El modo de exportación debe ser «w» o «wb».")

    path = Path(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0)
    temporary: Path | None = None
    descriptor: int | None = None
    for _ in range(100):
        candidate = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            descriptor = os.open(candidate, flags, 0o666)
            temporary = candidate
            break
        except FileExistsError:
            continue
    if descriptor is None or temporary is None:
        raise FileExistsError(f"No se pudo crear un provisorio al lado de {path}.")

    try:
        kwargs = {} if "b" in mode else {"encoding": encoding, "newline": newline}
        with os.fdopen(descriptor, mode, **kwargs) as stream:
            descriptor = None
            yield stream
            stream.flush()
        os.replace(temporary, path)
    except BaseException:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            temporary.unlink()
        except OSError:
            pass
        raise


def write_text_atomically(path: Path, text: str) -> None:
    """Escribir texto UTF-8 completo o conservar el destino anterior."""
    with atomic_destination(path) as stream:
        stream.write(text)
