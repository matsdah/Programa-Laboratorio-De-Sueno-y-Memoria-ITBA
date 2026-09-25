"""Análisis de componentes independientes (ICA).

Descompone el registro en componentes independientes para poder identificar y
quitar artefactos: parpadeos, actividad cardíaca, movimiento de electrodos.

Es una herramienta poderosa y peligrosa a la vez: quitar el componente
equivocado modifica la señal de forma irreversible y el usuario puede no
darse cuenta. Por eso el flujo es en tres pasos separados (ajustar, inspeccionar,
aplicar) y `apply` devuelve un registro nuevo en vez de modificar el original.

**Se ajusta sobre los canales EEG y sólo sobre ellos.** Meter un termómetro o un
sensor de flujo en la descomposición no tiene sentido físico —ICA busca fuentes
eléctricas mezcladas en el cuero cabelludo— y ensuciaría todos los componentes.
`apply_ica()` devuelve el registro entero, con los EEG reconstruidos y el resto
intacto.

**Se ajusta sobre una muestra de la noche** (hito 58), repartida a lo largo
del registro: por lo menos `FIT_SAMPLES` muestras por canal y menos del doble,
o todas si son menos. La ICA separa fuentes mezcladas **en el mismo instante**
y no mira el orden de las muestras, así que saltear algunas no filtra nada:
ajusta con menos datos, que sobran. Con la noche entera el ajuste pedía siete copias de la señal —13 GB
con 32 canales y 8 horas— y tardaba minutos; ver `fit_ica()`.

**La semilla es fija**, y no es un detalle: ICA es estocástica, así que sin
semilla el mismo registro da componentes distintos en cada corrida, en otro
orden y con otro signo. Un investigador que rehace un análisis tiene que obtener
lo mismo. `RANDOM_STATE` es esa semilla.

**Sobre la topografía y lo que este módulo no puede dar.** `component_topography()`
devuelve **cuánto pesa cada canal en un componente**, que es el dato con el que
se reconoce un artefacto: un parpadeo tiene peso alto en los frontales y bajo en
los occipitales. Lo que **no** devuelve es un mapa sobre el cuero cabelludo,
porque para dibujarlo harían falta las coordenadas de cada electrodo y `Channel`
no las lleva. Agregarlas es una decisión sobre el modelo de datos de la Parte 1,
no algo para resolver de paso acá. Los pesos por canal alcanzan para reconocer
el artefacto, que es para lo que la vista existe.

Cubre del pliego: V5_F de "Filtración de la señal".
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np

from psglab.analysis.mne_bridge import (
    _factor_hacia_mne,
    _registro_parcial,
    from_raw,
    to_raw,
)
from psglab.core.recording import ChannelKind, Recording
from psglab.core.windows import count_windows, window_to_samples
from psglab.utils.errors import (
    InvalidRecordingError,
    WindowOutOfRangeError,
    memoria_suficiente,
)

#: Semilla del algoritmo. Fija a propósito: ver el docstring del módulo.
RANDOM_STATE: Final[int] = 0

#: Cuántas ventanas de la noche se usan para medir la varianza que explica
#: cada componente. Ver `explained_variance()`.
VARIANCE_SAMPLE_WINDOWS: Final[int] = 40

#: Cuántas muestras por canal se usan para ajustar la descomposición, como
#: mínimo. Ver `fit_ica()`. Doscientas mil son 13 minutos a 256 Hz: un
#: registro más corto se ajusta entero, igual que antes del hito 58.
FIT_SAMPLES: Final[int] = 200_000

#: El piso que pone la cantidad de canales: tantas veces su cuadrado. La regla
#: de uso habitual de la ICA pide entre veinte y treinta; con 32 canales son
#: 30 720 muestras, y `FIT_SAMPLES` ya es más de seis veces eso. Es la que
#: manda recién pasados los 80 canales, que ningún polisomnógrafo trae.
FIT_SAMPLES_PER_SQUARED_CHANNEL: Final[int] = 30

#: Cuántas muestras por tramo se le pasan a MNE al quitar componentes (hito
#: 59). Unos cuatro minutos a 256 Hz: con 32 canales son 16 MB por tramo, y
#: una llamada a MNE por tramo no se nota en el tiempo total.
_MUESTRAS_POR_TRAMO: Final[int] = 65_536

#: Tope de iteraciones antes de darse por vencido. El valor por omisión de MNE
#: ("auto") es bajo para señal ruidosa y deja avisos de no convergencia en
#: mitad de un análisis; con este tope converge y si no lo hace, no convergió.
MAX_ITER: Final[int] = 1000


def _exigir_registro(recording: Recording) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`."""
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede hacer una ICA de eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )


def _canales_eeg(recording: Recording) -> list[str]:
    """Los canales sobre los que se descompone, o un error si no alcanzan.

    Raises:
        InvalidRecordingError: si hay menos de dos. Con un solo canal no hay
            mezcla que separar, y devolver una descomposición de un componente
            haría creer que se hizo algo.
    """
    nombres = [c.name for c in recording.channels_of_kind(ChannelKind.EEG)]
    if len(nombres) < 2:
        raise InvalidRecordingError(
            "La ICA separa fuentes mezcladas entre canales, así que hacen falta "
            "al menos dos canales EEG.",
            details=f"el registro tiene {len(nombres)} EEG: {nombres}.",
        )
    return nombres


def _exigir_ica(ica: Any) -> None:
    """Rechaza como `PsgLabError` lo que no sea una ICA ajustada.

    Sin esto sale un `AttributeError` sobre `.get_components()`, que la ventana
    principal no atrapa.

    Se exige también `ch_names`, que es el atributo con el que `apply_ica()`
    comprueba que la descomposición sea de este registro y con el que
    `component_topography()` rotula los pesos. Pedir dos de los tres dejaba pasar
    un objeto que reventaba más adelante, que es justo lo que esta guarda existe
    para impedir.
    """
    if (
        not hasattr(ica, "get_components")
        or not hasattr(ica, "n_components_")
        or not hasattr(ica, "ch_names")
    ):
        raise InvalidRecordingError(
            "Eso no es una descomposición ICA ajustada.",
            details=(
                f"ica es {type(ica).__name__}; se esperaba el objeto que devuelve "
                "fit_ica()."
            ),
        )


def _exigir_componente(ica: Any, component: int) -> int:
    """Comprueba que el componente exista en esta descomposición."""
    if isinstance(component, bool) or not isinstance(component, int):
        raise InvalidRecordingError(
            "El número de componente tiene que ser un entero.",
            details=f"component es {type(component).__name__}: {component!r}.",
        )
    total = int(ica.n_components_)
    if not 0 <= component < total:
        raise InvalidRecordingError(
            f"La descomposición tiene {total} componentes y se pidió el "
            f"{component + 1}.",
            details=f"component = {component}, válido de 0 a {total - 1}.",
        )
    return component


def _muestra_para_ajustar(recording: Recording, nombres: list[str]) -> Recording:
    """Los canales EEG, con una de cada `paso` muestras a lo largo del registro.

    **Repartida y no un tramo**: una hora seguida puede ser toda vigilia, y un
    componente de parpadeo ajustado ahí no es el de la noche. Una de cada
    `paso` pasa por todas las fases.

    **Sólo se copia lo que se usa.** Se toma la vista con el paso antes de
    elegir los canales: al revés, `data[filas]` copiaría los EEG enteros para
    después descartar casi todo, y el pico volvería a ser la señal completa.

    La muestra declara la frecuencia que tiene de verdad, `fs / paso`: MNE
    ajusta igual y la aplica después sobre la señal a la frecuencia original.
    """
    cuantas = max(FIT_SAMPLES, FIT_SAMPLES_PER_SQUARED_CHANNEL * len(nombres) ** 2)
    # **Hacia abajo**, para que `cuantas` sea un mínimo: hacia arriba, un
    # registro apenas más largo que el tope se ajustaba con la mitad.
    paso = max(1, recording.n_samples // cuantas)
    filas = [recording.channel_by_name(nombre).index for nombre in nombres]
    datos = np.ascontiguousarray(recording.data[:, ::paso][filas])
    return _registro_parcial(
        recording, nombres, datos, sampling_rate=recording.sampling_rate / paso
    )


def fit_ica(recording: Recording, n_components: int | None = None) -> Any:
    """Ajusta la descomposición ICA sobre el registro.

    Args:
        n_components: cantidad de componentes. Si es None, se estima a partir
            de la cantidad de canales.

    Returns:
        El objeto ICA ajustado, para inspeccionarlo antes de aplicarlo.

    **Sin `n_components` se usan tantos como canales EEG haya.** No se puede
    separar más fuentes que sensores, así que ése es el techo, y usarlo entero
    es lo que no descarta información antes de que el usuario mire.

    Es **reproducible**: con la misma señal devuelve la misma descomposición,
    porque la semilla está fija en `RANDOM_STATE`.

    **Se ajusta sobre una muestra**, y es la decisión del hito 58: una de cada
    `paso` muestras, por lo menos `FIT_SAMPLES` por canal. Medido con
    `tests/medir_memoria.py`, sobre la noche entera el ajuste pedía **siete
    copias** de la señal —seis eran de MNE, que copia los canales, los
    blanquea en otra copia y arma una matriz del tamaño de la señal para la
    descomposición en componentes principales—. Su propio `decim` no
    alcanzaba: copia la señal entera antes de descartar, y dejaba el pico en
    3,2. Con un octavo de las muestras eran 0,9 copias y 8 s en vez de 88.

    Raises:
        InvalidRecordingError: si no hay al menos dos canales EEG, o si se piden
            más componentes que canales.
    """
    from mne.preprocessing import ICA

    _exigir_registro(recording)
    nombres = _canales_eeg(recording)

    if n_components is None:
        cuantos = len(nombres)
    else:
        if isinstance(n_components, bool) or not isinstance(n_components, int):
            raise InvalidRecordingError(
                "La cantidad de componentes tiene que ser un número entero.",
                details=f"n_components es {type(n_components).__name__}.",
            )
        if not 1 <= n_components <= len(nombres):
            raise InvalidRecordingError(
                f"No se pueden separar {n_components} fuentes con {len(nombres)} "
                "canales EEG: no se puede pedir más componentes que sensores.",
                details=f"n_components = {n_components}, canales = {len(nombres)}.",
            )
        cuantos = n_components

    raw = to_raw(_muestra_para_ajustar(recording, nombres))
    ica = ICA(
        n_components=cuantos,
        random_state=RANDOM_STATE,
        max_iter=MAX_ITER,
        verbose="ERROR",
    )
    try:
        with memoria_suficiente("calcular la ICA"):
            ica.fit(raw, picks=nombres, verbose="ERROR")
    except (ValueError, np.linalg.LinAlgError) as error:
        # **Una señal sin variación no se puede descomponer.** Es un caso real
        # —canales planos, un electrodo desconectado toda la noche— y MNE lo
        # rechaza con "array must not contain infs or NaNs", que sale de dividir
        # por una varianza cero al blanquear. Ese mensaje no le dice nada a un
        # investigador, y además `ValueError` no hereda de `PsgLabError`: se
        # escaparía del `except` de la ventana principal. Lo encontró
        # `test_contratos.py`.
        raise InvalidRecordingError(
            "No se pudo descomponer la señal: puede que algún canal EEG esté "
            "plano o tenga valores inválidos.",
            details=f"{type(error).__name__}: {error}",
        ) from error
    return ica


def component_topography(ica: Any, component: int) -> dict[str, float]:
    """Datos para dibujar la topografía de un componente.

    Es la vista que permite reconocer un artefacto: un parpadeo se ve como
    actividad concentrada en los electrodos frontales.

    Returns:
        Canal -> cuánto pesa ese canal en el componente, **normalizado** para
        que el mayor valga 1. Sin normalizar, los números dependen de la escala
        que ICA le haya dado al componente, que es arbitraria: lo que se lee es
        la forma, no la magnitud.

    **No devuelve un mapa sobre el cuero cabelludo**, y el motivo está en el
    docstring del módulo: haría falta la posición de cada electrodo, que el
    modelo de datos no lleva.

    Raises:
        InvalidRecordingError: si no es una ICA ajustada, o si el componente no
            existe en ella.
    """
    _exigir_ica(ica)
    numero = _exigir_componente(ica, component)

    pesos = np.asarray(ica.get_components())[:, numero]
    mayor = float(np.max(np.abs(pesos)))
    # Un componente que salió todo en cero no tiene forma que normalizar. No
    # debería pasar con una ICA convergida, pero dividir por cero acá dejaría
    # NaN en toda la topografía.
    escala = mayor if mayor > 0 else 1.0
    return {
        nombre: float(peso / escala) for nombre, peso in zip(ica.ch_names, pesos)
    }


def explained_variance(ica: Any, recording: Recording) -> list[float]:
    """Qué fracción de la varianza de los canales EEG explica cada componente.

    **Es la pista de cuál pesa más** antes de quitar nada (hito 54): el
    prototipo la mostraba al lado de cada componente, y sin ella la lista son
    nombres iguales. Un parpadeo suele explicar mucho; un componente que
    explica el 1 % rara vez es lo que molesta.

    **Se mide con la definición de MNE** (`get_explained_variance_ratio`), que
    reconstruye la señal desde cada componente solo. Se probó sacarla de las
    normas de la matriz de mezcla, sin tocar la señal, y **no coincide**: con
    cinco canales sintéticos daba 51 % donde MNE da 62 %, porque
    `get_components()` no está en las unidades del sensor.

    **La definición es la de MNE, la cuenta no** (hito 61). MNE reconstruye la
    muestra una vez por componente —32 reconstrucciones con 32 canales— y era
    el paso más lento del menú: 24 s y 2,4 copias de la señal sobre una hora.
    Acá se calculan las fuentes una sola vez y la varianza de lo que queda al
    quitar cada una sale de sumas sobre ellas; ver `_varianza_de_una_vez()`.
    Coincide con MNE hasta el redondeo, y un test lo compara en cada corrida.

    **Sobre una muestra de la noche y no la noche entera**: reconstruir una
    vez por componente cuesta una copia de la señal cada vez, casi 2 GB por
    componente con 32 canales y ocho horas. Se usan hasta
    `VARIANCE_SAMPLE_WINDOWS` ventanas repartidas a lo largo del registro,
    todas si son menos. Es una estimación, y por eso el número se muestra
    redondeado.

    Returns:
        Una fracción por componente, en orden, entre 0 y 1. Con tantos
        componentes como canales suman 1; con menos, lo que falta es lo que la
        descomposición dejó afuera.

    Raises:
        InvalidRecordingError: si no es una ICA ajustada o no hay registro.
    """
    _exigir_ica(ica)
    _exigir_registro(recording)

    total = count_windows(recording.n_samples, recording.sampling_rate)
    cuantas = min(total, VARIANCE_SAMPLE_WINDOWS)
    elegidas = np.unique(np.linspace(0, total - 1, cuantas).round().astype(int))
    # **Sólo los canales de la descomposición**, que son los que la varianza
    # mira: MNE la mide sobre los EEG, y la ICA se ajustó sobre ellos.
    nombres = list(ica.ch_names)
    limites = []
    for ventana in elegidas:
        inicio, fin = window_to_samples(int(ventana), recording.sampling_rate)
        limites.append((inicio, min(fin, recording.n_samples)))
    # **Un solo arreglo, llenado época por época**: juntarlas en una lista y
    # después concatenar tenía la muestra dos veces a la vez.
    muestra = np.empty((len(nombres), sum(fin - inicio for inicio, fin in limites)))
    posicion = 0
    for inicio, fin in limites:
        muestra[:, posicion : posicion + fin - inicio] = recording.get_segment(
            inicio, fin, nombres
        )
        posicion += fin - inicio

    if _se_puede_de_una_vez(ica):
        # **En volts y sin pasar por un `Raw`**, que la volvería a copiar: la
        # escala es la del puente, que es el único que sabe cuál es.
        muestra *= np.array(
            [_factor_hacia_mne(recording.channel_by_name(nombre)) for nombre in nombres]
        )[:, None]
        return _varianza_de_una_vez(ica, muestra)
    raw = to_raw(_registro_parcial(recording, nombres, muestra))
    fracciones = []
    for numero in range(int(ica.n_components_)):
        razon = ica.get_explained_variance_ratio(
            raw, components=[numero], ch_type="eeg"
        )
        fracciones.append(float(razon["eeg"]))
    return fracciones


def _se_puede_de_una_vez(ica: Any) -> bool:
    """Si la descomposición tiene la forma que `_varianza_de_una_vez()` supone.

    Es la que deja `fit_ica()`: sin matriz de ruido —el blanqueo previo es una
    escala por canal— y sin proyectores. Otra cosa se mide con la cuenta de
    MNE, que es la definición.
    """
    blanqueo = np.asarray(getattr(ica, "pre_whitener_", np.empty((0, 0))))
    return (
        getattr(ica, "noise_cov", None) is None
        and blanqueo.ndim == 2
        and blanqueo.shape == (len(ica.ch_names), 1)
        and not ica.info.get("projs")
    )


def _varianza_de_una_vez(ica: Any, x: np.ndarray) -> list[float]:
    """La varianza explicada de MNE, con las fuentes calculadas una sola vez.

    MNE, para el componente `k`, reconstruye la señal sólo con él y compara
    lo que queda al restarla, `d = x - x_k`, contra la señal `x`: la varianza
    **entre canales** en cada instante, promediada en el tiempo. La razón es
    `1 - var(d) / var(x)`.

    Con `y` la señal blanqueada y centrada, `s = U y` las fuentes, `p` el
    blanqueo por canal y `m_k` la columna `k` de la mezcla, lo que queda es
    `d = p·y - (p·m_k) s_k`. Llamando `a = p·y` y `b = p·m_k`, la varianza
    entre canales de `a - b s_k`, promediada en el tiempo, se abre en sumas
    que no dependen de `k` —la de `a²`— o que salen de un solo producto de
    matrices —`a sᵀ`—. **Ninguna reconstruye la señal**, y eso es todo el
    ahorro: una pasada en vez de una por componente.

    **Trabaja sobre el arreglo de la muestra y no hace otro del mismo
    tamaño**: además de él sólo están las fuentes. Lo pisa: al terminar, `x`
    queda blanqueada y centrada.

    Args:
        x: la muestra en las unidades de MNE, un canal por fila en el orden de
            `ica.ch_names`.
    """
    n_canales, n_muestras = x.shape
    # La varianza de la señal, antes de pisarla: por instante, entre canales.
    media = x.mean(axis=0)
    var_x = float(np.mean(np.einsum("ij,ij->j", x, x) / n_canales - media * media))

    blanqueo = np.asarray(ica.pre_whitener_)
    x /= blanqueo
    if ica.pca_mean_ is not None:
        x -= ica.pca_mean_[:, None]
    y = x  # la misma memoria, ya blanqueada y centrada

    cuantos = int(ica.n_components_)
    pca = ica.pca_components_[:cuantos]
    fuentes = (ica.unmixing_matrix_ @ pca) @ y
    b = blanqueo * (pca.T @ ica.mixing_matrix_)
    p2 = (blanqueo * blanqueo)[:, 0]

    # Los promedios en el tiempo que necesita la cuenta, sin armar `a = p·y`.
    a2 = float(p2 @ np.einsum("ij,ij->i", y, y)) / (n_canales * n_muestras)
    a_por_fuente = blanqueo * (y @ fuentes.T) / n_muestras
    a_media = (blanqueo[:, 0] @ y) / n_canales
    s2 = np.einsum("ij,ij->i", fuentes, fuentes) / n_muestras

    cruzado = (b * a_por_fuente).sum(axis=0) / n_canales
    primer_momento = a2 - 2 * cruzado + (b * b).mean(axis=0) * s2
    b_media = b.mean(axis=0)
    segundo_momento = (
        float(a_media @ a_media) / n_muestras
        - 2 * b_media * (fuentes @ a_media) / n_muestras
        + b_media * b_media * s2
    )
    return [float(1 - v / var_x) for v in primer_momento - segundo_momento]


def _recorte_de_ventana(recording: Recording, window_index: int) -> Recording:
    """Un `Recording` con una sola ventana de 30 s del original.

    Existe para que `component_time_course()` pueda mirar una ventana sin
    reconstruir las fuentes de la noche entera. `to_raw()` copia lo que recibe,
    así que darle el registro completo cuesta una copia completa de la señal
    —445 MB en el registro real de 22 h— para dibujar 30 segundos.

    Raises:
        WindowOutOfRangeError: si la ventana no existe en el registro.
    """
    total = count_windows(recording.n_samples, recording.sampling_rate)
    if isinstance(window_index, bool) or not isinstance(window_index, int):
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
    # `fin` puede pasarse del final en la última ventana; `get_segment` acorta.
    tramo = recording.get_segment(inicio, min(fin, recording.n_samples))
    return Recording(
        file_path=recording.file_path,
        channels=list(recording.channels),
        data=np.asarray(tramo),
        sampling_rate=recording.sampling_rate,
        start_time=recording.start_time,
        metadata=dict(recording.metadata),
    )


def component_time_course(
    ica: Any,
    component: int,
    recording: Recording,
    window_index: int | None = None,
) -> np.ndarray:
    """Serie temporal de un componente, para inspeccionarla junto a la señal.

    Args:
        window_index: ventana de 30 s a reconstruir. `None` devuelve el registro
            entero, que es la firma con la que nació.

    Returns:
        Array de una dimensión con un valor por muestra, en las unidades
        arbitrarias del componente. Es lo que se dibuja debajo de la señal para
        ver **cuándo** ocurre el artefacto: un parpadeo aparece como picos
        aislados y el ruido de línea como una oscilación constante.

    **Por qué ganó el argumento**, que es una decisión de firma como la de
    `filters.default_for()` en el hito 17: hasta el hito 19 esta función existía
    y **no la llamaba nadie**, así que su promesa de dibujo no se cumplía. Al
    cablearla apareció el motivo por el que no alcanzaba con la firma vieja:
    reconstruir la noche entera cuesta una copia completa de la señal y devuelve
    millones de puntos que no se pueden mirar. El panel pide **la ventana que el
    investigador está mirando**, igual que el espectro y la conectividad.

    Raises:
        InvalidRecordingError: si no es una ICA ajustada, si el componente no
            existe, o si no se le pasa un registro.
        WindowOutOfRangeError: si la ventana no existe en el registro.
    """
    _exigir_ica(ica)
    numero = _exigir_componente(ica, component)
    _exigir_registro(recording)

    tramo = recording if window_index is None else _recorte_de_ventana(
        recording, window_index
    )
    # `get_sources()` no acepta `verbose`, a diferencia de `fit` y `apply`.
    fuentes = ica.get_sources(to_raw(tramo))
    return np.asarray(fuentes.get_data()[numero])


def apply_ica(recording: Recording, ica: Any, exclude: list[int]) -> Recording:
    """Reconstruye la señal sin los componentes excluidos.

    Args:
        exclude: índices de los componentes a quitar.

    Returns:
        Un `Recording` nuevo. El original queda intacto, porque esta operación
        no se puede deshacer sobre los datos ya transformados.

    **Sólo cambian los canales EEG**, que son sobre los que se ajustó la
    descomposición. El resto del registro vuelve idéntico.

    Con `exclude` vacío devuelve la señal reconstruida sin quitar nada, que es
    prácticamente la original: sirve para comprobar que la descomposición no
    está rompiendo la señal antes de confiarle un componente.

    **Se aplica por tramos de tiempo** (hito 59), y da exactamente lo mismo que
    de una vez: quitar un componente es una cuenta con las matrices que dejó
    el ajuste, muestra por muestra, y no mira el resto de la señal. De una vez
    pedía cuatro copias de la señal —MNE la copia a la ida, la transforma y la
    copia a la vuelta—; así, la salida y un tramo. **Los canales que no son
    EEG no pasan por MNE**: salen del original sin el viaje de ida y vuelta.

    **La descomposición tiene que ser de este registro**, y acá sólo se puede
    comprobar la mitad que se ve: que los canales sobre los que se ajustó sigan
    existiendo. Una ICA ajustada sobre la señal **sin filtrar** y aplicada a la
    **filtrada** tiene los mismos nombres de canal y esta guarda no la ve; ésa la
    tiene que impedir quien sostiene la descomposición entre el ajuste y la
    aplicación, que es la ventana principal (ver `MainWindow._olvidar_ica`).
    Esto cubre el otro caso: abrir otro registro y aplicarle la ICA del anterior.

    Raises:
        InvalidRecordingError: si no es una ICA ajustada, si algún índice de
            `exclude` no existe, si no se le pasa un registro, o si el registro
            no tiene los canales sobre los que se ajustó la descomposición.
    """
    _exigir_registro(recording)
    _exigir_ica(ica)
    if not isinstance(exclude, (list, tuple)):
        raise InvalidRecordingError(
            "Los componentes a quitar se dan como una lista de números.",
            details=f"exclude es {type(exclude).__name__}: {exclude!r}.",
        )
    for indice in exclude:
        _exigir_componente(ica, indice)

    presentes = set(recording.channel_names())
    faltantes = [nombre for nombre in ica.ch_names if nombre not in presentes]
    if faltantes:
        raise InvalidRecordingError(
            "Esta descomposición se calculó sobre otros canales, así que no se "
            "puede aplicar a este registro.",
            details=(
                f"la ICA se ajustó sobre {list(ica.ch_names)} y el registro no "
                f"tiene {faltantes}."
            ),
        )

    nombres = list(ica.ch_names)
    filas = [recording.channel_by_name(nombre).index for nombre in nombres]
    with memoria_suficiente("quitar componentes"):
        salida = np.array(recording.data, dtype=float, copy=True)
    for desde in range(0, recording.n_samples, _MUESTRAS_POR_TRAMO):
        hasta = min(desde + _MUESTRAS_POR_TRAMO, recording.n_samples)
        tramo = _registro_parcial(recording, nombres, recording.data[filas, desde:hasta])
        # `ica.apply` modifica el `Raw` que recibe, y por eso se le pasa el que
        # acaba de armar el puente y no algo del registro: el original no se
        # toca.
        raw = to_raw(tramo)
        ica.apply(raw, exclude=list(exclude), verbose="ERROR")
        salida[filas, desde:hasta] = from_raw(raw, tramo).data
    return Recording(
        file_path=recording.file_path,
        channels=list(recording.channels),
        data=salida,
        sampling_rate=recording.sampling_rate,
        start_time=recording.start_time,
        metadata=dict(recording.metadata),
    )


__all__ = [
    "FIT_SAMPLES",
    "FIT_SAMPLES_PER_SQUARED_CHANNEL",
    "MAX_ITER",
    "RANDOM_STATE",
    "apply_ica",
    "component_time_course",
    "component_topography",
    "fit_ica",
]
