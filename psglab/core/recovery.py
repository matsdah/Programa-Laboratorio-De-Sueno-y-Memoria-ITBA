"""La copia de recuperación: qué se guarda del trabajo y cómo se vuelve a él.

**El programa no autoguarda**, por decisión del hito 33: guardar a escondidas
obliga a elegir por el usuario dónde y en qué formato. Pero scorear una noche
lleva horas, y un corte de luz se las llevaba enteras. El 26 de septiembre de
2026 el usuario decidió una copia que **no es un archivo de salida**: vive en
su perfil, no se exporta ni aparece en ninguna carpeta, y al reabrir el mismo
registro después de un cierre inesperado el programa ofrece volver a donde
estaba.

Este módulo es la regla, sin Qt y sin disco: qué es el trabajo —las fases, los
arousals, las anotaciones con sus clases y la ventana donde estaba parado el
usuario—, cómo se reconoce que una copia es del registro abierto y cómo se
vuelve a ella. Cuándo se escribe, dónde y cuándo se borra es de
`ui/work_guard.py`.

**La copia es un diccionario de tipos de JSON** y no un objeto: se escribe y se
lee de un archivo que pudo quedar cortado por el mismo corte de luz, así que
`restore()` desconfía de todo lo que trae y lo rechaza entero antes de tocar la
sesión.

Cubre del pliego: ningún ID; es infraestructura del trabajo del investigador.
"""

from typing import Any, Final

from psglab.core.annotations import Annotation
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Recording
from psglab.core.session import Session
from psglab.utils.errors import PsgLabError, UnreadableRecoveryError

#: La forma de la copia. Si cambia, una copia vieja se descarta en vez de
#: leerse mal: `matches()` la compara.
RECOVERY_FORMAT: Final[int] = 1


def snapshot(session: Session) -> dict[str, Any]:
    """El trabajo de la sesión, listo para escribirse como JSON.

    Las fases van por el nombre de su `SleepStage` y la nomenclatura por el de
    su `Nomenclature`, que no cambian si cambia cómo se muestran. Las
    sugeridas no van: son del clasificador, se vuelven a pedir en minutos, y
    nadie las confirmó.

    Raises:
        PsgLabError: si no es una sesión.
    """
    if not isinstance(session, Session):
        raise PsgLabError(
            "No se pudo guardar la copia de recuperación.",
            details=f"session es {type(session).__name__}, se esperaba Session.",
        )
    scoring = session.scoring
    ventanas = [scoring.get(i) for i in range(scoring.n_windows)]
    anotaciones = session.annotations
    return {
        "formato": RECOVERY_FORMAT,
        "registro": _huella(session.recording),
        "ventana": session.current_window,
        "nomenclatura": scoring.nomenclature.name,
        "fases": [ventana.stage.name for ventana in ventanas],
        "arousals": [i for i, ventana in enumerate(ventanas) if ventana.arousal],
        "clases": [[clase, anotaciones.color_of(clase)] for clase in anotaciones.labels()],
        "anotaciones": [
            [a.label, a.onset_sample, a.duration_samples, list(a.channels), a.color]
            for a in anotaciones.all()
        ],
    }


def matches(data: object, recording: Recording) -> bool:
    """Si la copia es de este registro, y de esta forma de copia.

    Se compara el nombre del archivo, la frecuencia, cuántas muestras y qué
    canales tiene, que es lo que haría que las fases cayeran en otras
    ventanas o las anotaciones en otros canales. **No la ruta entera**: la
    carpeta pudo cambiar de nombre, y eso no cambia el registro.

    Raises:
        PsgLabError: si `recording` no es un registro. Una copia rota no eleva:
            simplemente no coincide.
    """
    if not isinstance(recording, Recording):
        raise PsgLabError(
            "No se pudo comparar la copia de recuperación con el registro.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )
    if not isinstance(data, dict):
        return False
    return data.get("formato") == RECOVERY_FORMAT and data.get("registro") == _huella(
        recording
    )


def summary(data: object) -> tuple[int, int]:
    """Cuántas ventanas scoreadas y cuántas anotaciones trae la copia.

    Es lo que la pregunta le muestra al usuario, y lo que dice si vale la pena
    preguntar: una copia con cero y cero no tiene nada que recuperar.

    Raises:
        UnreadableRecoveryError: si la copia no tiene la forma esperada.
    """
    fases, _arousals, _clases, anotaciones = _partes(data)
    scoreadas = sum(1 for fase in fases if fase != SleepStage.UNSCORED.name)
    return scoreadas, len(anotaciones)


def restore(session: Session, data: object) -> None:
    """Vuelve a poner en la sesión el trabajo de la copia.

    **Sobre una sesión recién abierta**: se ofrece al abrir el registro, antes
    de que el usuario haga nada. Si ya tiene fases o anotaciones, se rechaza
    en vez de mezclar.

    **Lo recuperado sigue sin exportar**, y es lo correcto: no está en ningún
    archivo de salida, así que cerrar tiene que seguir preguntando. Por eso se
    escribe sobre el scoring y las anotaciones de la sesión en vez de
    reemplazarlos con `set_scoring()`, que lo daría por exportado.

    **Todo o nada.** Se valida la copia entera antes de tocar la sesión: una
    copia cortada por el corte de luz no puede dejar la noche a medias.

    Raises:
        PsgLabError: si no es una sesión, o si ya tiene trabajo.
        UnreadableRecoveryError: si la copia no es de este registro o no se
            puede leer.
    """
    if not isinstance(session, Session):
        raise PsgLabError(
            "No se pudo recuperar el trabajo.",
            details=f"session es {type(session).__name__}, se esperaba Session.",
        )
    if not matches(data, session.recording):
        raise UnreadableRecoveryError(
            "La copia de recuperación no es de este registro.",
            details="matches() dio False: otro archivo, otra forma de copia o una copia rota.",
        )
    # `matches()` ya comprobó que es un diccionario; esto sólo lo nombra.
    copia: dict[str, Any] = data if isinstance(data, dict) else {}
    scoring = session.scoring
    if scoring.scored_windows() or session.annotations.all():
        raise PsgLabError(
            "El trabajo se recupera sobre el registro recién abierto, antes de scorear.",
            details="La sesión ya tiene fases o anotaciones.",
        )

    fases, arousals, clases, anotaciones = _partes(copia)
    try:
        nomenclatura = Nomenclature[copia["nomenclatura"]]
        etapas = [SleepStage[nombre] for nombre in fases]
    except (KeyError, TypeError) as error:
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details=f"Nomenclatura o fase desconocida: {error!r}",
        ) from error
    ventana = copia.get("ventana")
    if (
        len(etapas) != scoring.n_windows
        or not isinstance(ventana, int)
        or isinstance(ventana, bool)
        or not 0 <= ventana < max(scoring.n_windows, 1)
        or any(
            not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < scoring.n_windows
            for i in arousals
        )
    ):
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details="Las ventanas de la copia no son las del registro.",
        )
    try:
        recuperadas = [
            Annotation(etiqueta, inicio, duracion, tuple(canales), color)
            for etiqueta, inicio, duracion, canales, color in anotaciones
        ]
    except (TypeError, ValueError) as error:
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details=f"Una anotación no tiene la forma esperada: {error!r}",
        ) from error
    # **Adentro del registro y sobre sus canales.** `AnnotationSet` no conoce
    # el registro, así que no lo comprueba; y la copia es de este registro
    # —lo dijo `matches()`—, así que una anotación fuera de él es una copia
    # rota y no un evento.
    canales = set(session.recording.channel_names())
    if not all(
        isinstance(a.onset_sample, int)
        and isinstance(a.duration_samples, int)
        and 0 <= a.onset_sample
        and a.end_sample <= session.recording.n_samples
        and set(a.channels) <= canales
        for a in recuperadas
    ):
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details="Una anotación cae fuera del registro o sobre un canal que no tiene.",
        )

    # **Recién acá se toca la sesión.** Lo que queda puede rechazar todavía
    # —una anotación fuera del registro, un color inválido—, y entonces se
    # deshace lo hecho para no dejar la noche a medias.
    try:
        scoring.change_nomenclature(nomenclatura)
        for indice, etapa in enumerate(etapas):
            if etapa is not SleepStage.UNSCORED:
                scoring.set_stage(indice, etapa)
        for indice in arousals:
            scoring.set_arousal(indice, True)
        # **Sólo las clases que falten**: las que ya están traen el color que
        # el usuario eligió en sus preferencias, que pudo cambiar desde que se
        # escribió la copia.
        for clase, color in clases:
            if clase not in session.annotations.labels():
                session.annotations.add_label(clase, color)
        for anotacion in recuperadas:
            session.annotations.add(anotacion)
    except (PsgLabError, TypeError, ValueError) as error:
        _deshacer(session)
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details=f"{type(error).__name__}: {error}",
        ) from error
    if scoring.n_windows:
        session.go_to_window(ventana)


def _huella(recording: Recording) -> dict[str, Any]:
    """Lo que identifica a un registro para la copia. Ver `matches()`."""
    return {
        "archivo": recording.file_path.name,
        "frecuencia": float(recording.sampling_rate),
        "muestras": int(recording.n_samples),
        "canales": recording.channel_names(),
    }


def _partes(data: object) -> tuple[list[Any], list[Any], list[Any], list[Any]]:
    """Las cuatro listas de la copia, comprobando que sean listas de lo esperado.

    Raises:
        UnreadableRecoveryError: si falta alguna o no tiene la forma esperada.
    """
    if not isinstance(data, dict):
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details=f"La copia es {type(data).__name__}, se esperaba un diccionario.",
        )
    partes = [data.get(clave) for clave in ("fases", "arousals", "clases", "anotaciones")]
    fases, arousals, clases, anotaciones = partes
    if (
        not all(isinstance(parte, list) for parte in partes)
        or not all(isinstance(fase, str) for fase in fases)
        or not all(isinstance(clase, list) and len(clase) == 2 for clase in clases)
        or not all(isinstance(a, list) and len(a) == 5 for a in anotaciones)
    ):
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details="Falta una de sus partes, o no tiene la forma esperada.",
        )
    return fases, arousals, clases, anotaciones


def _deshacer(session: Session) -> None:
    """Deja la sesión sin fases, arousals ni anotaciones, como estaba al abrir.

    La nomenclatura queda como la dejó la copia: sin nada scoreado, no hay
    nada que se interprete distinto.
    """
    scoring = session.scoring
    for indice in range(scoring.n_windows):
        scoring.set_stage(indice, SleepStage.UNSCORED)
        scoring.set_arousal(indice, False)
    for anotacion in session.annotations.all():
        session.annotations.remove(anotacion)
