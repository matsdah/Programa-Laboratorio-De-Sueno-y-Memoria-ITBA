"""Conectividad entre canales.

Mide en qué grado la actividad de dos zonas del cerebro está relacionada. En
sueño interesa porque la conectividad cae en el sueño profundo y se
reorganiza en REM.

Sobre la elección del método, que no es un detalle técnico menor: la
coherencia común es sensible al volume conduction, es decir, dos electrodos
pueden parecer conectados simplemente porque están captando la misma fuente
eléctrica desde distintos lugares del cuero cabelludo. Los métodos basados en
la parte imaginaria (imaginary coherence, wPLI) son inmunes a ese artefacto y
son los recomendados por defecto.

Las funciones que reciben `window_index` tienen que traducirlo a muestras con
`psglab.core.windows.window_to_samples()`, que es el único lugar del programa
donde se hace esa conversión. No escribir la cuenta `* 30 * fs` acá: si la
ventana deja de ser de 30 s, este módulo quedaría desincronizado en silencio.

**mne-connectivity trabaja sobre épocas**, no sobre un tramo continuo, así que
cada ventana se parte antes de medir. `EPOCH_SECONDS` fija en cuántas, y es la
decisión análoga al segmento de Welch de `psd.py`: se elige por la resolución
en frecuencia que hace falta para la banda más baja que se va a medir.

**Cuánto cuesta, medido** sobre una ventana de 30 s a 256 Hz con 4 canales, y
extrapolado a las 2650 ventanas de un registro real:

    épocas de  3 s (10 por ventana, 0,33 Hz)   5,9 ms/ventana  ->  0,3 min
    épocas de  5 s ( 6 por ventana, 0,20 Hz)   7,1 ms/ventana  ->  0,3 min
    épocas de  6 s ( 5 por ventana, 0,17 Hz)   9,5 ms/ventana  ->  0,4 min
    épocas de 10 s ( 3 por ventana, 0,10 Hz)  11,7 ms/ventana  ->  0,5 min

El costo es plano, así que la elección se hace por resolución y no por tiempo.

Cubre del pliego: sección "Conectividad de la señal".
"""

from __future__ import annotations

from typing import Final

import numpy as np

from psglab.core.recording import Recording
from psglab.core.windows import count_windows, window_to_samples
from psglab.utils.errors import (
    InvalidBandError,
    InvalidRecordingError,
    UnknownConnectivityMethodError,
    WindowOutOfRangeError,
)

#: Métodos disponibles, del más simple al más robusto frente a volume
#: conduction.
METHODS: Final[tuple[str, ...]] = (
    "coherence",
    "imaginary_coherence",
    "pli",
    "wpli",
    "plv",
)

#: Cómo se llama cada método en mne-connectivity. Los nombres de afuera son los
#: que el pliego y el usuario usan; los de adentro son abreviaturas suyas.
_NOMBRES_DE_MNE: Final[dict[str, str]] = {
    "coherence": "coh",
    "imaginary_coherence": "imcoh",
    "pli": "pli",
    "wpli": "wpli",
    "plv": "plv",
}

#: Duración de cada época en que se parte una ventana, en segundos.
#:
#: Fija la resolución en frecuencia, que es `1 / época`: con 5 s da 0,20 Hz, que
#: alcanza para medir delta desde 0,5 Hz. Con 3 s la resolución sería 0,33 Hz y
#: el borde inferior de delta quedaría a un bin y medio del cero, demasiado
#: cerca para confiar en él.
#:
#: Al mismo tiempo deja **seis épocas por ventana** de 30 s, y wPLI promedia
#: sobre ellas: con épocas de 10 s quedarían tres, y el promedio de tres es
#: ruidoso. Cinco segundos es el punto donde las dos cosas alcanzan.
EPOCH_SECONDS: Final[float] = 5.0


def _exigir_registro(recording: Recording) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`."""
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede medir la conectividad de eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )


def _validar_banda(band: tuple[float, float]) -> tuple[float, float]:
    """Misma comprobación que en `psd.py`, con el mismo criterio."""
    try:
        desde, hasta = band
        desde, hasta = float(desde), float(hasta)
    except (TypeError, ValueError) as error:
        raise InvalidBandError(
            "La banda de frecuencia tiene que ser un par de números (desde, hasta).",
            details=f"se recibió {band!r}: {error}",
        ) from error
    if not np.isfinite(desde) or not np.isfinite(hasta) or desde < 0 or desde >= hasta:
        raise InvalidBandError(
            f"La banda va de {desde} a {hasta} Hz, así que no se puede medir en ella.",
            details="Tienen que ser dos números finitos, el primero menor y no negativo.",
        )
    return desde, hasta


def _en_epocas(tramo: np.ndarray, sampling_rate: float) -> np.ndarray | None:
    """Parte un tramo continuo en épocas, como pide mne-connectivity.

    Returns:
        Array de forma (n_épocas, n_canales, n_muestras), o None si el tramo no
        da ni para una época completa.
    """
    largo = int(EPOCH_SECONDS * sampling_rate)
    cuantas = tramo.shape[1] // largo
    if cuantas < 1:
        return None
    recortado = tramo[:, : cuantas * largo]
    # (canales, épocas, muestras) -> (épocas, canales, muestras), que es el
    # orden en que mne-connectivity espera los datos.
    return recortado.reshape(tramo.shape[0], cuantas, largo).transpose(1, 0, 2)


def compute_connectivity(
    recording: Recording,
    channels: list[str] | None = None,
    band: tuple[float, float] = (0.5, 4.0),
    method: str = "wpli",
    window_index: int | None = None,
) -> np.ndarray:
    """Matriz de conectividad entre los canales pedidos.

    Args:
        band: banda de frecuencia en la que se mide.
        method: uno de `METHODS`.
        window_index: ventana de 30 s a analizar. None analiza todo el registro.

    Returns:
        Matriz cuadrada y simétrica de forma (n_canales, n_canales), con la
        diagonal en cero, y **en valor absoluto**.

        Para `coherence`, `pli`, `wpli` y `plv` tomar el módulo no cambia nada:
        los cuatro son no negativos por definición. **Para
        `imaginary_coherence` sí**, y conviene saberlo: la coherencia imaginaria
        tiene signo, y el signo dice cuál de los dos canales adelanta al otro.
        Acá se pierde.

        Se hace a propósito y el motivo es la promesa de la línea de arriba:
        mne-connectivity devuelve sólo el triángulo inferior, y esta función
        entrega una matriz **simétrica** para que quien la lea no tenga que
        saber de qué lado quedó cada par. Una matriz simétrica no puede llevar
        un signo que significa dirección: `M[i][j]` y `M[j][i]` tendrían que ser
        opuestos. Quien necesite la dirección tiene que pedirle el triángulo con
        signo a mne-connectivity, no a esta función.

    Raises:
        UnknownConnectivityMethodError: si el método no es uno de `METHODS`.
            Elegir uno por omisión daría un resultado que se interpreta al
            revés: la coherencia común y wPLI responden preguntas distintas.
        InvalidBandError: si la banda está mal formada.
        WindowOutOfRangeError: si la ventana no existe.
        InvalidRecordingError: si no hay al menos dos canales, o si el tramo no
            da ni para una época.
        ChannelNotFoundError: si algún canal no existe.
    """
    from mne_connectivity import spectral_connectivity_epochs

    _exigir_registro(recording)
    # Mismo motivo que en `complexity.py`: `not in` hashea la clave.
    if not isinstance(method, str) or method not in _NOMBRES_DE_MNE:
        raise UnknownConnectivityMethodError(
            f"No se conoce el método de conectividad «{method}».",
            details=f"métodos disponibles: {', '.join(METHODS)}.",
        )
    desde, hasta = _validar_banda(band)

    if channels is None:
        nombres = recording.channel_names()
    elif isinstance(channels, (list, tuple)) and all(
        isinstance(n, str) for n in channels
    ):
        nombres = list(channels)
    else:
        raise InvalidRecordingError(
            "Hay que decir entre qué canales medir, con una lista de nombres.",
            details=f"channels es {type(channels).__name__}: {channels!r}.",
        )
    if len(nombres) < 2:
        raise InvalidRecordingError(
            "La conectividad se mide entre canales, así que hacen falta al menos dos.",
            details=f"se pidieron {len(nombres)}: {nombres}.",
        )

    if window_index is None:
        inicio, fin = 0, recording.n_samples
    else:
        total = count_windows(recording.n_samples, recording.sampling_rate)
        if not isinstance(window_index, int) or isinstance(window_index, bool):
            raise WindowOutOfRangeError(
                "El número de ventana tiene que ser un número entero.",
                details=f"window_index es {type(window_index).__name__}.",
            )
        if not 0 <= window_index < total:
            raise WindowOutOfRangeError(
                f"El registro tiene {total} ventanas y se pidió la {window_index + 1}.",
                details=f"window_index = {window_index}, válido de 0 a {total - 1}.",
            )
        inicio, fin = window_to_samples(window_index, recording.sampling_rate)
        fin = min(fin, recording.n_samples)

    tramo = np.array(recording.get_segment(inicio, fin, nombres), copy=True)
    epocas = _en_epocas(tramo, recording.sampling_rate)
    if epocas is None:
        raise InvalidRecordingError(
            "El tramo es más corto que una época, así que no alcanza para medir "
            "la conectividad.",
            details=(
                f"{tramo.shape[1]} muestras contra las "
                f"{int(EPOCH_SECONDS * recording.sampling_rate)} que necesita una "
                f"época de {EPOCH_SECONDS} s."
            ),
        )

    resultado = spectral_connectivity_epochs(
        epocas,
        method=_NOMBRES_DE_MNE[method],
        sfreq=recording.sampling_rate,
        fmin=desde,
        fmax=hasta,
        faverage=True,
        verbose="ERROR",
    )
    matriz = np.asarray(resultado.get_data(output="dense"))[:, :, 0]

    # mne-connectivity devuelve sólo el triángulo inferior. La matriz que este
    # módulo promete es **simétrica**, así que se refleja: quien la lea no
    # tiene por qué saber de qué lado quedó cada par.
    #
    # El módulo es lo que hace posible reflejar. Para cuatro de los cinco
    # métodos no cambia nada —son no negativos por definición— pero para
    # `imcoh` descarta el signo, que codifica dirección. Está en el docstring:
    # una matriz simétrica no puede llevarlo.
    matriz = np.abs(matriz)
    completa = matriz + matriz.T
    np.fill_diagonal(completa, 0.0)
    return completa


def connectivity_by_window(
    recording: Recording,
    channels: list[str],
    band: tuple[float, float],
    method: str = "wpli",
) -> np.ndarray:
    """Conectividad ventana por ventana a lo largo del registro.

    Returns:
        Array de forma (n_ventanas, n_canales, n_canales).

    La primera dimensión es **exactamente `count_windows()`**, y una ventana que
    no da ni para una época queda llena de **NaN**. Es la misma convención que
    fijó `psd.py`: descartarla desalinearía el array del hipnograma.

    Raises:
        Lo mismo que `compute_connectivity()`.
    """
    _exigir_registro(recording)
    total = count_windows(recording.n_samples, recording.sampling_rate)
    # La misma comprobación que hace `compute_connectivity()`, repetida acá
    # porque el largo de `nombres` se usa **antes** de llamarla: sin esto,
    # `list(channels)` con un número eleva `TypeError` al armar el array de
    # salida, y eso escaparía del `except` de la ventana principal.
    # **`None` es "todos" y `[]` es "ninguno".** Antes `[]` caía en la primera
    # rama y se convertía en "todos", mientras `compute_connectivity()` la
    # rechazaba por no llegar a dos canales: la misma lista significaba cosas
    # opuestas en dos funciones hermanas.
    if channels is None:
        nombres = recording.channel_names()
    elif isinstance(channels, (list, tuple)) and all(
        isinstance(n, str) for n in channels
    ):
        nombres = list(channels)
    else:
        raise InvalidRecordingError(
            "Hay que decir entre qué canales medir, con una lista de nombres.",
            details=f"channels es {type(channels).__name__}: {channels!r}.",
        )
    if len(nombres) < 2:
        raise InvalidRecordingError(
            "La conectividad se mide entre canales, así que hacen falta al menos dos.",
            details=f"se pidieron {len(nombres)}: {nombres}.",
        )
    salida = np.full((total, len(nombres), len(nombres)), np.nan)

    for ventana in range(total):
        try:
            salida[ventana] = compute_connectivity(
                recording,
                channels=nombres,
                band=band,
                method=method,
                window_index=ventana,
            )
        except InvalidRecordingError:
            # La ventana no da ni para una época. Queda en NaN, que es como se
            # inicializó. Cualquier otro error sí sube: una banda mal formada o
            # un método desconocido son del llamador, no de la ventana.
            continue
    return salida


def average_connectivity(matrix: np.ndarray) -> float:
    """Conectividad promedio de una matriz, ignorando la diagonal.

    Resume la matriz en un solo número para poder graficarlo contra el
    hipnograma.

    **La diagonal se ignora de verdad**, no se le resta: un canal consigo mismo
    no es una conexión, y promediarla metería un 1 —o lo que la biblioteca haya
    dejado ahí— en cada fila.

    Raises:
        InvalidRecordingError: si no es una matriz cuadrada de al menos 2×2.
    """
    try:
        datos = np.asarray(matrix, dtype=float)
    except (TypeError, ValueError) as error:
        raise InvalidRecordingError(
            "La conectividad promedio se calcula sobre una matriz de números.",
            details=f"matrix es {type(matrix).__name__}: {error}",
        ) from error
    if datos.ndim != 2 or datos.shape[0] != datos.shape[1] or datos.shape[0] < 2:
        raise InvalidRecordingError(
            "La conectividad promedio necesita una matriz cuadrada de al menos "
            "dos canales.",
            details=f"matrix tiene forma {datos.shape}.",
        )

    fuera = ~np.eye(datos.shape[0], dtype=bool)
    valores = datos[fuera]
    # `nanmean` y no `mean`: una ventana sin medir llega llena de NaN, y con
    # `mean` un solo NaN contamina el promedio de toda la matriz.
    if np.all(np.isnan(valores)):
        return float("nan")
    return float(np.nanmean(valores))


__all__ = [
    "EPOCH_SECONDS",
    "METHODS",
    "average_connectivity",
    "compute_connectivity",
    "connectivity_by_window",
]
