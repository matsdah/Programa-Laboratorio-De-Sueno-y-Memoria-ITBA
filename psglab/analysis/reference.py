"""Re-referenciación de la señal.

El EEG mide diferencias de potencial, así que todo canal se lee siempre
respecto de alguna referencia. Cambiarla cambia lo que se ve, y es una
operación de rutina: los husos se ven mejor con una referencia y las ondas
lentas con otra.

Cubre del pliego: sección "Rereferenciar".
"""

from psglab.core.recording import Recording


def rereference(recording: Recording, reference_channels: list[str]) -> Recording:
    """Re-referencia el registro a uno o varios canales.

    Args:
        reference_channels: canales que forman la referencia nueva. Con más de
            uno se usa su promedio, que es lo habitual al referenciar a los
            mastoides (A1 y A2).

    Returns:
        Un `Recording` nuevo, con el original intacto.

    Raises:
        ChannelNotFoundError: si alguno de los canales de referencia no existe.
    """
    raise NotImplementedError("Pendiente: restar la referencia y devolver un registro nuevo.")


def average_reference(recording: Recording, kind_only: bool = True) -> Recording:
    """Re-referencia al promedio de todos los canales.

    Args:
        kind_only: si es True, promedia sólo los canales EEG. Meter en el
            promedio un EMG o un ECG lo contaminaría todo, así que el valor
            por defecto es el seguro.
    """
    raise NotImplementedError("Pendiente: calcular el promedio y re-referenciar.")
