"""Importación de un scoring ya existente.

El pliego (V3_F de "Importación de archivos") pide poder abrir una señal ya
scoreada y ver en qué fase está cada ventana. Eso permite dos casos de uso
reales del laboratorio: retomar un trabajo interrumpido y revisar o corregir
el scoring hecho por otra persona.

El formato nativo es el mismo "Scoring.txt" que produce el programa (V1_F de
"Archivo de salida").

**La simetría entre exportar e importar es incompleta, y hay que saberlo.** El
archivo guarda códigos numéricos que no son únicos entre nomenclaturas: "2" es
S2 en Rechtschaffen y Kales y N2 en AASM. El archivo no dice cuál de las dos se
usó, así que `read_scoring()` obliga a pasar la nomenclatura por parámetro y
confía en que quien lo llama sepa con cuál se generó. Si se equivoca, el scoring
se carga entero con las fases mal traducidas y sin ningún error visible.

Escribir la nomenclatura en una cabecera lo resolvería, pero se apartaría del
formato del pliego. Es una de las preguntas abiertas del hito 0 (ver
`docs/TODO.md`).

Cubre del pliego: V3_F de "Importación de archivos".
"""

from pathlib import Path

from psglab.core.nomenclature import Nomenclature
from psglab.core.scoring import Scoring


def read_scoring(
    path: Path,
    n_windows: int,
    nomenclature: Nomenclature,
) -> Scoring:
    """Carga un archivo de scoring y lo asocia a un registro.

    Args:
        path: archivo de scoring, con el formato de "Scoring.txt".
        n_windows: cantidad de ventanas del registro abierto. Sirve para
            detectar que el scoring no corresponde a este registro.
        nomenclature: nomenclatura con la que interpretar los códigos de fase.

    Returns:
        El scoring cargado. Las ventanas ausentes del archivo quedan como
        UNSCORED, para que el usuario pueda completar un scoring parcial.

    Raises:
        ScoringMismatchError: si el archivo tiene más ventanas que el registro.
        UnreadableFileError: si alguna línea no respeta el formato esperado.
    """
    raise NotImplementedError("Pendiente: parsear el archivo de scoring.")


def detect_line_format(path: Path) -> bool:
    """Detecta si el archivo incluye el número de ventana en cada línea.

    Existe porque el pliego describe tres campos (ventana, fase, arousal) pero
    su ejemplo muestra dos ("2 0"). Mientras el cliente no lo confirme, el
    lector acepta las dos variantes y decide mirando la primera línea con
    datos.

    Returns:
        True si las líneas empiezan con el número de ventana.
    """
    raise NotImplementedError("Pendiente: inspeccionar la primera línea con datos.")
