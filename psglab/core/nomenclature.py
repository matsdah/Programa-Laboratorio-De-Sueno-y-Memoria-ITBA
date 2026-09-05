"""Nomenclaturas de scoring: Rechtschaffen y Kales, y AASM.

El pliego (V3_F de "Scoring de la señal") pide poder elegir entre las dos
nomenclaturas y que el histograma se adapte (V3_F del histograma). Este
módulo define las fases, qué fases pertenecen a cada nomenclatura y cómo se
convierte una en otra.

Confirmado con el cliente: **REM es una fase de primera clase en las dos
nomenclaturas**, aunque el listado del pliego la omitiera.

    Rechtschaffen y Kales : W, S1, S2, S3, S4, REM, MT
    AASM                  : W, N1, N2, N3, R

Cubre del pliego: V1_F, V3_F de "Scoring de la señal"; V3_F del histograma.
"""

from enum import Enum
from typing import Final


class Nomenclature(Enum):
    """Sistema de clasificación de fases elegido por el usuario."""

    RK = "Rechtschaffen y Kales"
    AASM = "AASM"


class SleepStage(Enum):
    """Fase de sueño de una ventana de 30 segundos.

    Se define un vocabulario único con las fases de las dos nomenclaturas. La
    ventana sin scorear tiene su propia fase (UNSCORED) para poder distinguir
    "todavía no lo miré" de "lo miré y es Wake"; el histograma lo necesita
    para dejar en blanco lo no anotado (V1_P).
    """

    UNSCORED = "-"
    WAKE = "W"
    # Rechtschaffen y Kales
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"
    MT = "MT"  # Movement Time
    # AASM
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    # Sueño REM: presente en las dos nomenclaturas, con distinta etiqueta
    REM = "REM"
    R = "R"


#: Fases válidas de cada nomenclatura, en el orden en que se muestran de
#: arriba hacia abajo en el histograma (pliego, V1_P del histograma).
STAGES_BY_NOMENCLATURE: Final[dict[Nomenclature, tuple[SleepStage, ...]]] = {
    Nomenclature.RK: (
        SleepStage.WAKE,
        SleepStage.REM,
        SleepStage.S1,
        SleepStage.S2,
        SleepStage.S3,
        SleepStage.S4,
        SleepStage.MT,
    ),
    Nomenclature.AASM: (
        SleepStage.WAKE,
        SleepStage.R,
        SleepStage.N1,
        SleepStage.N2,
        SleepStage.N3,
    ),
}

#: Código numérico de cada fase para el archivo "Scoring.txt" (V1_F de
#: "Archivo de salida").
#:
#: El pliego sólo fija un código: su ejemplo escribe la fase 2 como "2". El
#: resto sigue la convención habitual de los archivos de scoring
#: (0=W, 1..4=S1..S4, 5=REM, 6=MT), que es la que esperan los scripts de
#: análisis del laboratorio. Confirmado con el cliente el 4 de septiembre de
#: 2026, incluidos los códigos de REM y de MT.
#:
#: La tabla **no es inyectiva a propósito**: S1 y N1 comparten el 1, igual que
#: S2/N2, S3/N3 y REM/R. Codificar está bien; decodificar exige saber la
#: nomenclatura, que por eso queda registrada en "Informacion.txt".
STAGE_CODES: Final[dict[SleepStage, int]] = {
    SleepStage.WAKE: 0,
    SleepStage.S1: 1,
    SleepStage.S2: 2,
    SleepStage.S3: 3,
    SleepStage.S4: 4,
    SleepStage.REM: 5,
    SleepStage.MT: 6,
    SleepStage.N1: 1,
    SleepStage.N2: 2,
    SleepStage.N3: 3,
    SleepStage.R: 5,
    SleepStage.UNSCORED: -1,
}


#: Cómo se traduce cada fase ajena a la nomenclatura de destino.
#:
#: Se escriben las dos direcciones explícitamente en vez de derivar una de la
#: otra, porque **no son simétricas** y una tabla derivada escondería justamente
#: eso: S3 y S4 caen los dos en N3, y volver no puede distinguirlos.
_EQUIVALENCIAS: Final[dict[Nomenclature, dict[SleepStage, SleepStage]]] = {
    Nomenclature.AASM: {
        SleepStage.S1: SleepStage.N1,
        SleepStage.S2: SleepStage.N2,
        SleepStage.S3: SleepStage.N3,
        SleepStage.S4: SleepStage.N3,
        SleepStage.REM: SleepStage.R,
        # MT no existe en AASM. Se trata como W, que es la convención habitual:
        # un tramo de movimiento no es sueño.
        SleepStage.MT: SleepStage.WAKE,
    },
    Nomenclature.RK: {
        SleepStage.N1: SleepStage.S1,
        SleepStage.N2: SleepStage.S2,
        # N3 se mapea a S3 porque hay que elegir uno: la información de si era
        # S3 o S4 se perdió al convertir en la otra dirección.
        SleepStage.N3: SleepStage.S3,
        SleepStage.R: SleepStage.REM,
    },
}


def stages_of(nomenclature: Nomenclature) -> tuple[SleepStage, ...]:
    """Fases válidas de una nomenclatura, en orden de histograma.

    No incluye `UNSCORED`, que no es una fila del histograma sino la ausencia
    de una: el pliego (V1_P) pide que lo no anotado quede **en blanco**.
    """
    return STAGES_BY_NOMENCLATURE[nomenclature]


def is_valid(stage: SleepStage, nomenclature: Nomenclature) -> bool:
    """Indica si una fase se le puede asignar a una ventana en esta nomenclatura.

    **`UNSCORED` es válido en todas**, aunque no aparezca en `stages_of()`. Las
    dos funciones responden preguntas distintas y es acá donde dejan de
    coincidir: `stages_of()` da las filas del histograma, y "sin scorear" no es
    una fila; pero sí es un valor asignable, porque es como el usuario **borra**
    el scoring de una ventana que había marcado por error.

    Si esta función dijera que no, `Scoring.set_stage(UNSCORED)` elevaría
    `InvalidStageError` y despuntuar una ventana sería imposible.
    """
    return stage is SleepStage.UNSCORED or stage in stages_of(nomenclature)


def convert(stage: SleepStage, target: Nomenclature) -> SleepStage:
    """Traduce una fase a la nomenclatura pedida.

    La conversión NO es simétrica y hay que tenerlo presente:

    - R&K → AASM pierde información: S3 y S4 se funden en N3, y MT no tiene
      equivalente (se trata como W, que es la convención habitual).
    - AASM → R&K es ambigua: N3 puede corresponder a S3 o a S4, y no hay forma
      de recuperar cuál era. Se mapea a S3.

    - UNSCORED se devuelve tal cual en las dos direcciones: "todavía no lo
      miré" no es una fase y no se traduce.

    Por eso el cambio de nomenclatura sobre un registro ya scoreado debe
    avisarle al usuario antes de aplicarse.

    Una fase que ya pertenece a la nomenclatura pedida se devuelve sin tocar,
    así que convertir dos veces a lo mismo no cambia nada.
    """
    if is_valid(stage, target):
        return stage
    return _EQUIVALENCIAS[target][stage]


def stage_label(stage: SleepStage) -> str:
    """Etiqueta que se muestra al usuario para una fase.

    Es el valor del enum: las etiquetas del pliego ("W", "S1", "REM", "N2") son
    justamente los nombres con los que se define cada fase, así que no hay una
    segunda tabla que pueda desincronizarse.
    """
    return stage.value


def stage_code(stage: SleepStage) -> int:
    """Código numérico de la fase para "Scoring.txt".

    La tabla no es inyectiva: S1 y N1 comparten el 1, igual que S2/N2, S3/N3 y
    REM/R. Codificar está bien; **decodificar exige saber la nomenclatura**, que
    por eso viaja en la cabecera del propio archivo.
    """
    return STAGE_CODES[stage]
