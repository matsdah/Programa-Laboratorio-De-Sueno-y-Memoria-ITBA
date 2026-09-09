"""Densidad espectral de potencia (PSD).

Calcula cuánta potencia tiene la señal en cada banda de frecuencia. Es la
métrica más usada del análisis de sueño: la potencia delta cuantifica la
profundidad del sueño lento y la potencia sigma sigue a los husos.

El usuario elige las bandas. Las de abajo son las convencionales y sirven de
punto de partida, pero los límites varían entre laboratorios y entre trabajos
publicados, así que son editables.

Las funciones que reciben `window_index` tienen que traducirlo a muestras con
`psglab.core.windows.window_to_samples()`, que es el único lugar del programa
donde se hace esa conversión. No escribir la cuenta `* 30 * fs` acá: si la
ventana deja de ser de 30 s, este módulo quedaría desincronizado en silencio.

**La unidad de la PSD es µV²/Hz**, porque el registro está en microvoltios. No
hace falta convertir nada: `utils/units.py` ya dejó la señal en µV al importar.

**La última ventana del registro casi siempre está incompleta**, y este módulo
es el primero que recorre ventanas, así que acá se fija la convención que
copian `complexity.py` y `connectivity.py`:

    Una ventana más corta que el segmento de Welch devuelve **NaN**, no un
    número.

Las tres alternativas eran calcular igual, descartarla o devolver NaN. Calcular
igual da un valor con otra resolución de frecuencia, indistinguible de los
demás en el array y comparable con ellos por error. Descartarla desalinea el
array del hipnograma, que es justamente para lo que sirve —un valor por ventana,
igual que el scoring—. NaN conserva el largo y dice que ahí no se midió, que es
la verdad.

Cubre del pliego: V1_F de "Power Spectral Density (PSD)".
"""

from __future__ import annotations

from typing import Final

import numpy as np

from psglab.core.recording import Recording
from psglab.core.windows import count_windows, window_to_samples
from psglab.utils.errors import (
    InvalidBandError,
    InvalidRecordingError,
    UnknownPsdMethodError,
    WindowOutOfRangeError,
)

#: Bandas de frecuencia convencionales, en Hz.
DEFAULT_BANDS: Final[dict[str, tuple[float, float]]] = {
    "Delta": (0.5, 4.0),
    "Theta": (4.0, 8.0),
    "Alpha": (8.0, 12.0),
    "Sigma": (12.0, 16.0),
    "Beta": (16.0, 30.0),
    "Gamma": (30.0, 45.0),
}

#: Métodos de estimación aceptados.
METHODS: Final[tuple[str, ...]] = ("welch", "multitaper")

#: Duración del segmento de Welch, en segundos.
#:
#: Fija la resolución en frecuencia, que es `1 / segmento`: con 4 s da 0,25 Hz.
#: Es lo que hace falta para separar el borde inferior de delta, que está en
#: 0,5 Hz — con segmentos de 1 s la resolución sería 1 Hz y delta empezaría
#: donde el análisis no puede mirar. Más largo daría mejor resolución y menos
#: promediado, que es lo que Welch hace para bajar la varianza.
WELCH_SEGMENT_SECONDS: Final[float] = 4.0


def _exigir_registro(recording: Recording) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`."""
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede calcular la PSD de eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )


def _nombres_de_canal(
    recording: Recording, channels: list[str] | None
) -> list[str]:
    """Los canales pedidos, o todos. Rechaza lo que no sea una lista de nombres.

    Sin esta guarda, `list(channels)` con un número elevaba `TypeError`, que no
    hereda de `PsgLabError` y escaparía del `except` de la ventana principal.
    Lo encontró `test_contratos.py`.
    """
    if channels is None:
        return recording.channel_names()
    if not isinstance(channels, (list, tuple)) or not all(
        isinstance(nombre, str) for nombre in channels
    ):
        raise InvalidRecordingError(
            "Hay que decir qué canales analizar, con una lista de nombres.",
            details=f"channels es {type(channels).__name__}: {channels!r}.",
        )
    # **La lista vacía se rechaza, y no es lo mismo que `None`.** `None` dice
    # "todos"; `[]` dice "ninguno", y sobre ninguno no hay nada que medir. Sin
    # esta guarda `compute_psd(channels=[])` devolvía en silencio un espectro de
    # cero canales, y `band_powers_by_window()` hacía lo contrario —tratarla
    # como "todos"—, así que la misma lista significaba dos cosas opuestas en
    # funciones hermanas.
    if not channels:
        raise InvalidRecordingError(
            "Hay que decir qué canales analizar: la lista vino vacía.",
            details="channels = []; para analizarlos todos se pasa None.",
        )
    return list(channels)


def _tramo(
    recording: Recording, channels: list[str] | None, window_index: int | None
) -> np.ndarray:
    """Los datos a analizar, ya recortados a la ventana pedida.

    Devuelve una **copia**: `get_segment()` entrega un array de sólo lectura y
    scipy escribe sobre lo que recibe.
    """
    nombres = _nombres_de_canal(recording, channels)
    if window_index is None:
        return np.array(recording.get_segment(0, recording.n_samples, nombres), copy=True)

    total = count_windows(recording.n_samples, recording.sampling_rate)
    if not isinstance(window_index, int) or isinstance(window_index, bool):
        raise WindowOutOfRangeError(
            "El número de ventana tiene que ser un número entero.",
            details=f"window_index es {type(window_index).__name__}.",
        )
    if not 0 <= window_index < total:
        raise WindowOutOfRangeError(
            f"El registro tiene {total} ventanas y se pidió la "
            f"{window_index + 1}.",
            details=f"window_index = {window_index}, válido de 0 a {total - 1}.",
        )
    inicio, fin = window_to_samples(window_index, recording.sampling_rate)
    # `fin` puede pasarse del final en la última ventana: `get_segment` recorta
    # y devuelve un tramo más corto, que es justo el caso que este módulo trata
    # con NaN. Ver el docstring del módulo.
    return np.array(
        recording.get_segment(inicio, min(fin, recording.n_samples), nombres), copy=True
    )


def compute_psd(
    recording: Recording,
    channels: list[str] | None = None,
    window_index: int | None = None,
    method: str = "welch",
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula la PSD de uno o varios canales.

    Args:
        channels: canales a analizar. None significa todos.
        window_index: ventana de 30 s a analizar. None analiza el registro
            completo.
        method: "welch" o "multitaper".

    Returns:
        Tupla (frecuencias, potencias), con potencias de forma
        (n_canales, n_frecuencias), en µV²/Hz.

    Raises:
        UnknownPsdMethodError: si el método no es uno de `METHODS`. Elegir uno
            por defecto en silencio le daría al usuario un resultado que no
            pidió y que no puede distinguir del que pidió.
        WindowOutOfRangeError: si la ventana no existe en el registro.
        ChannelNotFoundError: si algún canal no existe.
        InvalidRecordingError: si no se le pasa un registro, o si el tramo es
            más corto que el segmento de Welch.
    """
    _exigir_registro(recording)
    if method not in METHODS:
        raise UnknownPsdMethodError(
            f"No se conoce el método «{method}» para calcular la PSD.",
            details=f"métodos disponibles: {', '.join(METHODS)}.",
        )

    datos = _tramo(recording, channels, window_index)
    frecuencia = recording.sampling_rate
    por_segmento = int(WELCH_SEGMENT_SECONDS * frecuencia)

    if datos.shape[1] < por_segmento:
        raise InvalidRecordingError(
            "El tramo es más corto que el segmento con el que se estima la PSD, "
            "así que no alcanza para medir.",
            details=(
                f"{datos.shape[1]} muestras contra {por_segmento} que necesita un "
                f"segmento de {WELCH_SEGMENT_SECONDS} s a {frecuencia} Hz."
            ),
        )

    if method == "welch":
        from scipy import signal as sp

        return sp.welch(datos, fs=frecuencia, nperseg=por_segmento, axis=-1)

    from mne.time_frequency import psd_array_multitaper

    potencias, frecuencias = psd_array_multitaper(
        datos, sfreq=frecuencia, verbose="ERROR"
    )
    return frecuencias, potencias


def band_power(
    frequencies: np.ndarray,
    psd: np.ndarray,
    band: tuple[float, float],
    relative: bool = False,
) -> np.ndarray:
    """Potencia dentro de una banda de frecuencia.

    Args:
        relative: si es True, devuelve la fracción de la potencia total en vez
            del valor absoluto. La potencia relativa es la que permite
            comparar entre participantes: la absoluta depende del grosor del
            cráneo y de la impedancia, que varían de persona a persona.

    Returns:
        La potencia integrada, con la misma forma que `psd` sin su último eje:
        un array de (n_canales,) para la salida de `compute_psd`, y un escalar
        para una PSD de un solo canal.

    **La banda es semiabierta, `[desde, hasta)`.** Las bandas convencionales se
    tocan —delta termina en 4 Hz y theta empieza ahí— y con los dos extremos
    incluidos ese bin se contaría dos veces, con lo cual las potencias relativas
    sumarían más de 1 sin que nada fallara.

    `relative` normaliza contra **toda la PSD calculada**, no contra la suma de
    `DEFAULT_BANDS`: es lo que dice "fracción de la potencia total", y depende
    sólo de lo que se midió y no de qué bandas eligió el usuario.

    Raises:
        InvalidBandError: si la banda está invertida, tiene un extremo negativo
            o no es un par de números.
    """
    desde, hasta = _validar_banda(band)
    frecuencias = np.asarray(frequencies, dtype=float)
    potencias = np.asarray(psd, dtype=float)

    dentro = (frecuencias >= desde) & (frecuencias < hasta)
    if not dentro.any():
        # Una banda que no contiene ningún bin no tiene potencia que integrar.
        # Pasa con una banda más angosta que la resolución, que es un pedido
        # legítimo aunque no se pueda responder con más que cero.
        parcial = np.zeros(potencias.shape[:-1])
    else:
        parcial = np.trapezoid(potencias[..., dentro], frecuencias[dentro], axis=-1)

    if not relative:
        return parcial
    total = np.trapezoid(potencias, frecuencias, axis=-1)
    # Un canal plano tiene potencia total cero y su fracción no está definida.
    # Cero es la respuesta que no miente: no hay potencia en la banda.
    return np.divide(
        parcial, total, out=np.zeros_like(parcial), where=np.asarray(total) != 0
    )


def _validar_banda(band: tuple[float, float]) -> tuple[float, float]:
    """Comprueba que la banda se pueda integrar, y devuelve sus extremos."""
    try:
        desde, hasta = band
        desde, hasta = float(desde), float(hasta)
    except (TypeError, ValueError) as error:
        raise InvalidBandError(
            "La banda de frecuencia tiene que ser un par de números (desde, hasta).",
            details=f"se recibió {band!r}: {error}",
        ) from error
    if not np.isfinite(desde) or not np.isfinite(hasta):
        raise InvalidBandError(
            "La banda de frecuencia tiene que estar formada por números finitos.",
            details=f"desde = {desde}, hasta = {hasta}.",
        )
    if desde < 0:
        raise InvalidBandError(
            "Una banda de frecuencia no puede empezar en un número negativo.",
            details=f"desde = {desde}.",
        )
    if desde >= hasta:
        raise InvalidBandError(
            f"La banda va de {desde} a {hasta} Hz, así que no contiene nada.",
            details="El primer número tiene que ser menor que el segundo.",
        )
    return desde, hasta


def band_powers_by_window(
    recording: Recording,
    channels: list[str],
    bands: dict[str, tuple[float, float]] | None = None,
) -> dict[str, dict[str, np.ndarray]]:
    """Potencia por banda para cada ventana de 30 segundos del registro.

    Es lo que permite ver la evolución del espectro a lo largo de la noche y
    cruzarla con el hipnograma.

    Returns:
        Diccionario canal -> banda -> array con un valor por ventana.

    Los arrays tienen **exactamente `count_windows()` elementos**, uno por
    ventana del registro, para que se puedan graficar contra el hipnograma sin
    alinear nada. Una ventana demasiado corta para medir queda en **NaN**: ver
    la convención en el docstring del módulo.

    Raises:
        InvalidRecordingError: si no se le pasa un registro.
        ChannelNotFoundError: si algún canal no existe.
        InvalidBandError: si alguna banda está mal formada.
    """
    _exigir_registro(recording)
    # Sin el `if channels` de antes: `None` sigue siendo "todos" y `[]` pasa a
    # rechazarse, que es lo que hace `compute_psd()` y lo que evita que la misma
    # lista signifique cosas opuestas en las dos.
    nombres = _nombres_de_canal(recording, channels)
    # Se validan antes de empezar: fallar en la ventana 900 de 960 después de
    # varios minutos de cuenta, por una banda invertida que se sabía desde el
    # principio, sería tiempo tirado.
    if bands is None:
        definiciones = dict(DEFAULT_BANDS)
    elif isinstance(bands, dict):
        definiciones = dict(bands)
    else:
        # `dict(bands)` con un número o una cadena eleva `TypeError` o
        # `ValueError`, que no heredan de `PsgLabError` y escaparían del
        # `except` de la ventana principal. Lo encontró `test_contratos.py`.
        raise InvalidBandError(
            "Las bandas se dan como un diccionario de nombre a (desde, hasta).",
            details=f"bands es {type(bands).__name__}: {bands!r}.",
        )
    for banda in definiciones.values():
        _validar_banda(banda)

    total = count_windows(recording.n_samples, recording.sampling_rate)
    resultado: dict[str, dict[str, np.ndarray]] = {
        nombre: {banda: np.full(total, np.nan) for banda in definiciones}
        for nombre in nombres
    }

    for ventana in range(total):
        try:
            frecuencias, potencias = compute_psd(
                recording, channels=nombres, window_index=ventana
            )
        except InvalidRecordingError:
            # La ventana es más corta que el segmento de Welch. Queda en NaN,
            # que es como se inicializó el array.
            continue
        for banda, extremos in definiciones.items():
            valores = band_power(frecuencias, potencias, extremos)
            for posicion, nombre in enumerate(nombres):
                resultado[nombre][banda][ventana] = valores[posicion]

    return resultado
