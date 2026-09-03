"""Detección automática de la clase de cada canal.

El pliego (V4_F de "Visualización de la señal") pide que el software detecte
solo si un canal es EEG, EOG, EMG, ECG u otra cosa, y que lo muestre junto al
nombre del canal. Sin esto, el usuario tendría que clasificar a mano decenas
de canales en cada registro.

La detección se basa en el nombre del canal, porque es lo único que traen
todos los formatos de forma confiable. Se usan dos fuentes:

    1. Los nombres estándar del sistema 10-20 (C3, C4, Fz, O1, ...).
    2. Patrones habituales en los registros del laboratorio (EOG, EMG, ECG,
       Chin, Resp, ...).

Si el nombre no coincide con nada, el canal se clasifica como OTHER y se
muestra igual: el pliego pide explícitamente que no haya limitación de tipo.

Cubre del pliego: V4_F de "Visualización de la señal".
"""

from typing import Final

from psglab.core.recording import ChannelKind

#: Nombres del sistema internacional 10-20, en minúscula y sin el número.
#: Un canal como "C3" o "Fp1-A2" se reconoce por su prefijo.
EEG_POSITIONS: Final[tuple[str, ...]] = (
    "fp", "af", "f", "ft", "fc", "t", "c", "tp", "cp", "p", "po", "o", "iz",
)

#: Patrones por clase de señal. Se evalúan en orden: el primero que coincide
#: gana, así que los patrones más específicos van primero.
KIND_PATTERNS: Final[tuple[tuple[ChannelKind, str], ...]] = (
    (ChannelKind.EOG, r"eog|loc|roc|e[12]\b|ojo"),
    (ChannelKind.EMG, r"emg|chin|menton|tib|barbilla"),
    (ChannelKind.ECG, r"ecg|ekg|cardio"),
    (ChannelKind.RESPIRATORY, r"resp|flow|flujo|thor|abdo|snore|ronqu|sao2|spo2"),
)


def detect_channel_kind(name: str, unit: str | None = None) -> ChannelKind:
    """Deduce la clase de un canal a partir de su nombre.

    Args:
        name: nombre del canal tal como viene en el archivo.
        unit: unidad declarada en el archivo, si la hay. Ayuda a descartar
            falsos positivos (un canal en °C no es un EEG).

    Returns:
        La clase detectada, o `ChannelKind.OTHER` si no se reconoce.
    """
    raise NotImplementedError("Pendiente: aplicar los patrones y devolver la clase.")


def detect_all(names: list[str], units: list[str] | None = None) -> list[ChannelKind]:
    """Detecta la clase de una lista de canales de una sola vez."""
    raise NotImplementedError("Pendiente: aplicar detect_channel_kind a cada canal.")


def is_eeg_position(name: str) -> bool:
    """Indica si el nombre corresponde a una posición del sistema 10-20."""
    raise NotImplementedError("Pendiente: comparar contra EEG_POSITIONS.")
