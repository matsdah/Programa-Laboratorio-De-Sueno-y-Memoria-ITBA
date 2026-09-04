"""Importación de un scoring ya existente.

El pliego (V3_F de "Importación de archivos") pide poder abrir una señal ya
scoreada y ver en qué fase está cada ventana. Eso permite dos casos de uso
reales del laboratorio: retomar un trabajo interrumpido y revisar o corregir
el scoring hecho por otra persona.

El formato nativo es el mismo "Scoring.txt" que produce el programa (V1_F de
"Archivo de salida").

Los códigos de fase no son únicos entre nomenclaturas: "2" es S2 en
Rechtschaffen y Kales y N2 en AASM. Leer un archivo con la nomenclatura
equivocada carga la noche entera mal traducida **sin ningún error visible**, así
que el lector no adivina nunca.

Los archivos que produce este programa arrancan con una cabecera que la declara
(`# AASM`), y `detect_nomenclature()` la lee. Para un archivo sin cabecera
—escrito a mano, o por una versión anterior— hay que pasarla por parámetro, y
ahí la responsabilidad es de quien llama.

Cubre del pliego: V3_F de "Importación de archivos".
"""

from pathlib import Path

from psglab.core.nomenclature import Nomenclature
from psglab.core.scoring import Scoring


def read_scoring(
    path: Path,
    n_windows: int,
    nomenclature: Nomenclature | None = None,
) -> Scoring:
    """Carga un archivo de scoring y lo asocia a un registro.

    Args:
        path: archivo de scoring, con el formato de "Scoring.txt".
        n_windows: cantidad de ventanas del registro abierto. Sirve para
            detectar que el scoring no corresponde a este registro.
        nomenclature: nomenclatura con la que interpretar los códigos de fase.
            **La cabecera del archivo tiene prioridad sobre este parámetro**:
            el archivo sabe mejor que quien lo abre con qué se escribió. Sólo
            se usa si el archivo no la declara, y si no la declara y tampoco se
            pasa, se eleva un error en vez de adivinar.

    Returns:
        El scoring cargado. Las ventanas ausentes del archivo quedan como
        UNSCORED, para que el usuario pueda completar un scoring parcial. Las
        que el archivo marca con el código de UNSCORED (-1) también.

    Raises:
        ScoringMismatchError: si el archivo tiene más ventanas que el registro.
        UnreadableFileError: si alguna línea no respeta el formato esperado, o
            si no hay forma de saber la nomenclatura.
    """
    raise NotImplementedError("Pendiente: parsear el archivo de scoring.")


def detect_nomenclature(path: Path) -> Nomenclature | None:
    """Lee la nomenclatura declarada en la cabecera del archivo.

    Es la contraparte de `exporters.scoring_txt.format_header()`: lo que aquél
    escribe, éste lo tiene que poder volver a leer.

    Returns:
        La nomenclatura declarada, o None si el archivo no tiene cabecera. None
        no es un error: un archivo escrito a mano o por una versión anterior
        del programa es válido, sólo que hay que decirle al lector con qué
        nomenclatura interpretarlo.
    """
    raise NotImplementedError("Pendiente: leer la cabecera y reconocer la nomenclatura.")


def detect_line_format(path: Path) -> bool:
    """Detecta si el archivo incluye el número de ventana en cada línea.

    Se confirmó que el formato propio lleva dos campos, pero el lector acepta
    igual las dos variantes: un archivo de tres campos sigue siendo legible sin
    ambigüedad, y aceptarlo no cuesta nada. Decide mirando la primera línea con
    datos, salteando la cabecera.

    Returns:
        True si las líneas empiezan con el número de ventana.
    """
    raise NotImplementedError("Pendiente: inspeccionar la primera línea con datos.")
