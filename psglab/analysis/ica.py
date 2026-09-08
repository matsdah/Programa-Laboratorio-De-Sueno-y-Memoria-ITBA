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

from psglab.analysis.mne_bridge import from_raw, to_raw
from psglab.core.recording import ChannelKind, Recording
from psglab.utils.errors import InvalidRecordingError

#: Semilla del algoritmo. Fija a propósito: ver el docstring del módulo.
RANDOM_STATE: Final[int] = 0

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
    """
    if not hasattr(ica, "get_components") or not hasattr(ica, "n_components_"):
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

    raw = to_raw(recording)
    ica = ICA(
        n_components=cuantos,
        random_state=RANDOM_STATE,
        max_iter=MAX_ITER,
        verbose="ERROR",
    )
    try:
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


def component_time_course(
    ica: Any, component: int, recording: Recording
) -> np.ndarray:
    """Serie temporal de un componente, para inspeccionarla junto a la señal.

    Returns:
        Array de una dimensión con un valor por muestra del registro, en las
        unidades arbitrarias del componente. Es lo que se dibuja debajo de la
        señal para ver **cuándo** ocurre el artefacto: un parpadeo aparece como
        picos aislados y el ruido de línea como una oscilación constante.

    Raises:
        InvalidRecordingError: si no es una ICA ajustada, si el componente no
            existe, o si el registro no es el que se descompuso.
    """
    _exigir_ica(ica)
    numero = _exigir_componente(ica, component)
    _exigir_registro(recording)

    # `get_sources()` no acepta `verbose`, a diferencia de `fit` y `apply`.
    fuentes = ica.get_sources(to_raw(recording))
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

    Raises:
        InvalidRecordingError: si no es una ICA ajustada, si algún índice de
            `exclude` no existe, o si no se le pasa un registro.
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

    raw = to_raw(recording)
    # `ica.apply` modifica el `Raw` que recibe, y por eso se le pasa el que
    # acaba de armar el puente y no algo del registro: el original no se toca.
    ica.apply(raw, exclude=list(exclude), verbose="ERROR")
    return from_raw(raw, recording)


__all__ = [
    "MAX_ITER",
    "RANDOM_STATE",
    "apply_ica",
    "component_time_course",
    "component_topography",
    "fit_ica",
]
