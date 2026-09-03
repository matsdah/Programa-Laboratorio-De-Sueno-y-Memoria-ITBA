"""Análisis de componentes independientes (ICA).

Descompone el registro en componentes independientes para poder identificar y
quitar artefactos: parpadeos, actividad cardíaca, movimiento de electrodos.

Es una herramienta poderosa y peligrosa a la vez: quitar el componente
equivocado modifica la señal de forma irreversible y el usuario puede no
darse cuenta. Por eso el flujo es en tres pasos separados (ajustar, inspeccionar,
aplicar) y `apply` devuelve un registro nuevo en vez de modificar el original.

Cubre del pliego: V5_F de "Filtración de la señal".
"""

from typing import Any

from psglab.core.recording import Recording


def fit_ica(recording: Recording, n_components: int | None = None) -> Any:
    """Ajusta la descomposición ICA sobre el registro.

    Args:
        n_components: cantidad de componentes. Si es None, se estima a partir
            de la cantidad de canales.

    Returns:
        El objeto ICA ajustado, para inspeccionarlo antes de aplicarlo.
    """
    raise NotImplementedError("Pendiente: ajustar la ICA con MNE.")


def component_topography(ica: Any, component: int) -> Any:
    """Datos para dibujar la topografía de un componente.

    Es la vista que permite reconocer un artefacto: un parpadeo se ve como
    actividad concentrada en los electrodos frontales.
    """
    raise NotImplementedError("Pendiente: extraer la topografía del componente.")


def component_time_course(ica: Any, component: int, recording: Recording) -> Any:
    """Serie temporal de un componente, para inspeccionarla junto a la señal."""
    raise NotImplementedError("Pendiente: extraer la serie temporal del componente.")


def apply_ica(recording: Recording, ica: Any, exclude: list[int]) -> Recording:
    """Reconstruye la señal sin los componentes excluidos.

    Args:
        exclude: índices de los componentes a quitar.

    Returns:
        Un `Recording` nuevo. El original queda intacto, porque esta operación
        no se puede deshacer sobre los datos ya transformados.
    """
    raise NotImplementedError("Pendiente: aplicar la ICA y devolver un registro nuevo.")
