"""Lectura de registros en formato BrainVision.

BrainVision reparte el registro en tres archivos que van siempre juntos:

    .vhdr  cabecera: canales, frecuencia de muestreo, unidades
    .vmrk  marcadores y eventos
    .eeg   la señal en sí

El usuario abre el `.vhdr` y los otros dos se cargan solos, porque la
cabecera los referencia por nombre.

Cubre del pliego: V1_F de "Importación de archivos".
"""

from pathlib import Path

from psglab.core.recording import Recording
from psglab.readers.base import Reader, register_reader


@register_reader
class BrainVisionReader(Reader):
    """Lector de registros BrainVision (VHDR/VMRK/EEG)."""

    format_name = "BrainVision"
    extensions = (".vhdr",)

    def read(self, path: Path) -> Recording:
        """Carga un registro BrainVision a partir de su archivo .vhdr.

        La lectura se apoya en MNE-Python. Los marcadores del .vmrk se
        conservan en `Recording.metadata` para poder convertirlos en
        anotaciones si el usuario lo pide.

        Raises:
            UnreadableFileError: si falta el .eeg o el .vmrk que referencia la
                cabecera, o si el archivo está corrupto.
        """
        raise NotImplementedError("Pendiente: leer el registro BrainVision con MNE.")
