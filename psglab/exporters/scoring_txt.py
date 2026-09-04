"""Exportación de "Scoring.txt".

Una línea de cabecera y después una línea por ventana, en orden, desde la
primera hasta la última del registro:

    # AASM  ->  nomenclatura con la que se scoreó
    2 0     ->  fase 2, sin arousal
    2 1     ->  fase 2, con arousal
    -1 0    ->  ventana todavía sin scorear

El pliego describe tres campos (número de ventana, fase, arousal) pero su
ejemplo muestra sólo dos, y **vale el ejemplo**: confirmado con el cliente. El
número de ventana queda implícito en el orden de las líneas. El formato sigue
viviendo en `config.SCORING_INCLUDES_WINDOW_NUMBER` para que revertirlo sea
cambiar una línea.

**Por qué hay una cabecera.** Los códigos de fase de
`nomenclature.STAGE_CODES` no son únicos entre nomenclaturas: S2 y N2 se
escriben los dos como "2", igual que S1/N1, S3/N3 y REM/R. Una línea que dice
"2 0" no alcanza para saber si la ventana es S2 de Rechtschaffen y Kales o N2
de AASM, y reimportarla con la nomenclatura equivocada carga la noche entera
mal traducida **sin ningún error visible**.

La primera decisión fue registrar la nomenclatura sólo en "Informacion.txt".
No alcanza: V4_F deja exportar **uno solo** de los tres archivos, y exportar
nada más que el scoring es el caso más común. Ese archivo salía ambiguo.

La cabecera es una línea de comentario (`config.SCORING_HEADER_PREFIX`), así
que un lector que no la espere la descarta por el prefijo. El pliego muestra
líneas de datos y no prohíbe comentarios. Vive en
`config.SCORING_INCLUDES_NOMENCLATURE_HEADER` para que quitarla siga siendo
cambiar una línea. La nomenclatura se sigue registrando además en
"Informacion.txt", que es donde va el resto del contexto del registro.

**Las ventanas sin scorear se escriben con el código de UNSCORED, que es -1.**
Confirmado con el cliente: no puede confundirse con ninguna fase real, porque
todas son 0 o positivas.

Cubre del pliego: V1_F de "Archivo de salida".
"""

from pathlib import Path

from psglab.config import (
    SCORING_HEADER_PREFIX,
    SCORING_INCLUDES_NOMENCLATURE_HEADER,
    SCORING_INCLUDES_WINDOW_NUMBER,
    SCORING_SEPARATOR,
)
from psglab.core.nomenclature import Nomenclature
from psglab.core.scoring import Scoring


def export_scoring(
    scoring: Scoring,
    path: Path,
    include_window_number: bool = SCORING_INCLUDES_WINDOW_NUMBER,
    include_header: bool = SCORING_INCLUDES_NOMENCLATURE_HEADER,
    separator: str = SCORING_SEPARATOR,
) -> None:
    """Escribe el scoring completo en un archivo de texto.

    Args:
        scoring: scoring a exportar.
        path: archivo de destino.
        include_window_number: si cada línea arranca con el número de ventana.
            Por defecto toma el valor de `config`, que es el punto único donde
            se decide el formato.
        separator: separador entre campos. Se expone acá, y no sólo en
            `format_line`, para que el exportador tenga la misma superficie de
            parámetros que `export_annotations`: los dos escriben un archivo del
            pliego y no hay motivo para que uno deje configurar el separador y
            el otro no.
        include_header: si el archivo arranca con la línea que declara la
            nomenclatura. Por defecto, el de `config`. La nomenclatura sale de
            `scoring.nomenclature`.

    Las ventanas sin scorear se exportan igual, con el código de UNSCORED, para
    que el archivo tenga siempre tantas líneas como ventanas el registro. Si se
    salteara las ventanas sin scorear, el número de línea dejaría de coincidir
    con el número de ventana y el archivo se volvería ambiguo.
    """
    raise NotImplementedError("Pendiente: escribir una línea por ventana.")


def format_header(
    nomenclature: Nomenclature,
    prefix: str = SCORING_HEADER_PREFIX,
) -> str:
    """Arma la línea de cabecera que declara la nomenclatura.

    Ejemplo: `"# AASM"`.

    Se separa del recorrido por el mismo motivo que `format_line`: para poder
    fijar el formato exacto en un test sin escribir ningún archivo. Lo que
    escriba acá tiene que poder volver a leerlo
    `readers.scoring_reader.detect_nomenclature()`.
    """
    raise NotImplementedError("Pendiente: componer la línea de cabecera.")


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
