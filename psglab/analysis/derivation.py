"""Derivaciones: canales nuevos calculados a partir de los existentes.

Una derivación es la diferencia entre dos canales, y es la forma estándar de
nombrar los montajes de polisomnografía: "C3-A2" quiere decir el canal C3
leído respecto del mastoides A2.

El canal derivado se agrega al registro en lugar de reemplazar a los
originales, para que el usuario pueda seguir viendo los canales de base.

Cubre del pliego: sección "Derivar".
"""

from psglab.core.recording import Recording


def derive(
    recording: Recording,
    channel_a: str,
    channel_b: str,
    name: str | None = None,
) -> Recording:
    """Crea un canal derivado como la diferencia de dos canales.

    Args:
        name: nombre del canal nuevo. Si es None, se arma como "A-B".

    Returns:
        Un `Recording` nuevo con el canal derivado agregado al final.

    Raises:
        ChannelNotFoundError: si alguno de los dos canales no existe.
        DuplicateChannelError: si ya hay un canal con ese nombre.
    """
    raise NotImplementedError("Pendiente: restar los canales y agregar el derivado.")


def derive_montage(recording: Recording, pairs: list[tuple[str, str]]) -> Recording:
    """Aplica un montaje completo de una sola vez.

    Args:
        pairs: lista de pares (canal, referencia).
    """
    raise NotImplementedError("Pendiente: aplicar todas las derivaciones del montaje.")
