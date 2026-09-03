"""Filtrado de la señal cruda.

Permite importar un registro sin filtros y aplicarle pasa-altos, pasa-bajos y
notch, con rangos distintos según el tipo de canal. Los rangos por defecto son
los habituales en polisomnografía, pero el usuario los puede cambiar: son
valores de referencia, no una imposición.

El notch es 50 Hz en Argentina (frecuencia de la red eléctrica). En países con
red de 60 Hz hay que cambiarlo, así que queda configurable.

Cubre del pliego: V1_F de "Filtración de la señal".
"""

from dataclasses import dataclass
from typing import Final

from psglab.core.recording import ChannelKind, Recording


@dataclass
class FilterSettings:
    """Filtros a aplicar a un canal.

    Attributes:
        highpass_hz: frecuencia de corte del pasa-altos. None lo desactiva.
        lowpass_hz: frecuencia de corte del pasa-bajos. None lo desactiva.
        notch_hz: frecuencia del notch. None lo desactiva.
    """

    highpass_hz: float | None = None
    lowpass_hz: float | None = None
    notch_hz: float | None = None


#: Rangos habituales por tipo de canal, ofrecidos como punto de partida.
DEFAULT_FILTERS: Final[dict[ChannelKind, FilterSettings]] = {
    ChannelKind.EEG: FilterSettings(highpass_hz=0.3, lowpass_hz=35.0, notch_hz=50.0),
    ChannelKind.EOG: FilterSettings(highpass_hz=0.3, lowpass_hz=15.0, notch_hz=50.0),
    ChannelKind.EMG: FilterSettings(highpass_hz=10.0, lowpass_hz=100.0, notch_hz=50.0),
    ChannelKind.ECG: FilterSettings(highpass_hz=0.5, lowpass_hz=70.0, notch_hz=50.0),
    ChannelKind.RESPIRATORY: FilterSettings(highpass_hz=0.05, lowpass_hz=5.0),
    ChannelKind.OTHER: FilterSettings(),
}


def apply_filters(
    recording: Recording,
    settings: dict[str, FilterSettings],
) -> Recording:
    """Aplica los filtros indicados y devuelve un registro nuevo.

    Args:
        settings: filtros por nombre de canal. Los canales que no aparezcan
            quedan sin filtrar.

    Returns:
        Un `Recording` nuevo. El original queda intacto para poder comparar.

    Raises:
        InvalidFilterError: si una frecuencia de corte supera la frecuencia de
            Nyquist del registro, o si el pasa-altos queda por encima del
            pasa-bajos.
    """
    raise NotImplementedError("Pendiente: aplicar los filtros con MNE y devolver un registro nuevo.")


def default_for(kind: ChannelKind) -> FilterSettings:
    """Filtros sugeridos para un tipo de canal."""
    raise NotImplementedError("Pendiente: devolver los filtros por defecto de la clase.")


def validate(settings: FilterSettings, sampling_rate: float) -> None:
    """Verifica que los filtros sean aplicables al registro.

    Raises:
        InvalidFilterError: con un mensaje explicando el problema en términos
            que el usuario pueda entender.
    """
    raise NotImplementedError("Pendiente: validar las frecuencias contra Nyquist.")
