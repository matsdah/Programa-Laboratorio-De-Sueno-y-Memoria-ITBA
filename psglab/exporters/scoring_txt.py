"""Exportación de "Scoring.txt".

Una línea por ventana, en orden, desde la primera hasta la última del
registro. Cada línea lleva la fase y la presencia de arousal:

    2 0     ->  fase 2, sin arousal
    2 1     ->  fase 2, con arousal

El pliego describe tres campos (número de ventana, fase, arousal) pero su
ejemplo muestra sólo dos, y **vale el ejemplo**: confirmado con el cliente. El
número de ventana queda implícito en el orden de las líneas. El formato sigue
viviendo en `config.SCORING_INCLUDES_WINDOW_NUMBER` para que revertirlo sea
cambiar una línea.

**El archivo no es autodescriptivo, y es una limitación real del formato.**
Los códigos de fase de `nomenclature.STAGE_CODES` no son únicos entre
nomenclaturas: S2 y N2 se escriben los dos como "2", igual que S1/N1, S3/N3 y
REM/R. Una línea que dice "2 0" no alcanza para saber si la ventana es S2 de
Rechtschaffen y Kales o N2 de AASM.

Por eso `readers.scoring_reader.read_scoring()` exige que le pasen la
nomenclatura: este archivo no la trae.

**Decisión tomada con el cliente:** no se agrega una cabecera acá, para no
apartarse del formato del pliego. La nomenclatura se registra en
"Informacion.txt", que ya es un resumen legible y se exporta junto con el
scoring. Quien reimporte un `Scoring.txt` tiene que mirar ese archivo para
saber con qué nomenclatura se generó.

Cubre del pliego: V1_F de "Archivo de salida".
"""

from pathlib import Path

from psglab.config import SCORING_INCLUDES_WINDOW_NUMBER, SCORING_SEPARATOR
from psglab.core.scoring import Scoring


def export_scoring(
    scoring: Scoring,
    path: Path,
    include_window_number: bool = SCORING_INCLUDES_WINDOW_NUMBER,
) -> None:
    """Escribe el scoring completo en un archivo de texto.

    Args:
        scoring: scoring a exportar.
        path: archivo de destino.
        include_window_number: si cada línea arranca con el número de ventana.
            Por defecto toma el valor de `config`, que es el punto único donde
            se decide el formato mientras el cliente no lo confirme.

    Las ventanas sin scorear se exportan igual, con el código de UNSCORED, para
    que el archivo tenga siempre tantas líneas como ventanas el registro. Si se
    salteara las ventanas sin scorear, el número de línea dejaría de coincidir
    con el número de ventana y el archivo se volvería ambiguo.
    """
    raise NotImplementedError("Pendiente: escribir una línea por ventana.")


def format_line(
    window_number: int,
    stage_code: int,
    arousal: bool,
    include_window_number: bool = SCORING_INCLUDES_WINDOW_NUMBER,
    separator: str = SCORING_SEPARATOR,
) -> str:
    """Arma una línea del archivo.

    Args:
        window_number: número de ventana en base 1, como lo cuenta el usuario.
        separator: separador de campos. Por defecto, el de `config`.

    Se separa del recorrido para poder testear el formato exacto sin escribir
    ningún archivo.
    """
    raise NotImplementedError("Pendiente: componer la línea con sus campos.")
