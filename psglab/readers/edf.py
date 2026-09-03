"""Lectura de registros en formato EDF y EDF+.

EDF es el formato más difundido en polisomnografía. A diferencia de
BrainVision, es un archivo único y autocontenido.

Ojo con dos particularidades del formato que hay que resolver acá y no
aguas abajo:

    - Los canales pueden tener frecuencias de muestreo distintas entre sí.
      El modelo `Recording` asume una sola frecuencia, así que hay que
      remuestrear o rechazar el archivo de forma explícita.
    - EDF+ guarda las anotaciones en un canal especial ("EDF Annotations")
      que no es una señal y no debe mostrarse como canal.

Cubre del pliego: V2_F de "Importación de archivos".
"""

from pathlib import Path

from psglab.core.recording import Recording
from psglab.readers.base import Reader, register_reader


@register_reader
class EdfReader(Reader):
    """Lector de registros EDF y EDF+."""

    format_name = "European Data Format"
    extensions = (".edf",)

    def read(self, path: Path) -> Recording:
        """Carga un registro EDF.

        Raises:
            UnreadableFileError: si el archivo está corrupto o truncado.
            MixedSamplingRateError: si los canales tienen frecuencias de
                muestreo distintas y no se puede unificarlas.
        """
        raise NotImplementedError("Pendiente: leer el registro EDF con MNE.")
