"""Control de impedancia de los electrodos.

El usuario define un límite de impedancia y el programa avisa qué canales lo
superan. Una impedancia alta significa mal contacto entre el electrodo y el
cuero cabelludo, y la señal de ese canal no es confiable.

PENDIENTE DE DEFINICIÓN CON EL CLIENTE: de dónde salen las impedancias. Ni
EDF ni BrainVision las traen siempre. Hay tres caminos posibles y hay que
elegir uno antes de implementar:

    1. Leerlas de la cabecera del archivo cuando estén.
    2. Importarlas de un archivo aparte que exporte el equipo de adquisición.
    3. Que el usuario las cargue a mano al abrir el registro.

Cubre del pliego: V1_F de "Impedancia de los electrodos".
"""

from pathlib import Path

from psglab.core.recording import Recording

#: Límite por defecto, en kiloohmios. Es el criterio habitual para EEG.
DEFAULT_LIMIT_KOHM: float = 5.0


def read_impedances(recording: Recording) -> dict[str, float]:
    """Impedancias por canal, en kiloohmios.

    Returns:
        Diccionario canal -> impedancia. Los canales sin dato no aparecen, en
        vez de figurar con cero: no es lo mismo "no medido" que "impedancia
        perfecta", y confundirlos ocultaría un electrodo suelto.
    """
    raise NotImplementedError("Pendiente: extraer las impedancias del registro.")


def load_impedances_from_file(path: Path) -> dict[str, float]:
    """Carga las impedancias desde un archivo externo."""
    raise NotImplementedError("Pendiente: parsear el archivo de impedancias.")


def channels_above_limit(
    impedances: dict[str, float],
    limit_kohm: float = DEFAULT_LIMIT_KOHM,
) -> list[str]:
    """Canales cuya impedancia supera el límite fijado por el usuario."""
    raise NotImplementedError("Pendiente: filtrar los canales que superan el límite.")


def impedance_report(
    impedances: dict[str, float],
    limit_kohm: float = DEFAULT_LIMIT_KOHM,
) -> str:
    """Texto de alerta con los canales problemáticos.

    Distingue tres estados: dentro del límite, por encima del límite y sin
    medición disponible.
    """
    raise NotImplementedError("Pendiente: componer el informe de impedancias.")
