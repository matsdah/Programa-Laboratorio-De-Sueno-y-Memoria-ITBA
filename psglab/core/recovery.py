"""La copia de recuperación: qué se guarda del trabajo y cómo se vuelve a él.

**El programa no autoguarda**: guardar a escondidas obliga a elegir por el
usuario dónde y en qué formato. Pero scorear una noche lleva horas, y un corte
de luz no se las puede llevar enteras. Por eso hay una copia que **no es un
archivo de salida**: vive en el perfil del usuario, no se exporta ni aparece
en ninguna carpeta, y al reabrir el mismo registro después de un cierre
inesperado el programa ofrece volver a donde estaba.

Este módulo es la regla, sin Qt y sin disco: qué es el trabajo —las fases, los
arousals, las anotaciones con sus clases, las derivaciones y la ventana donde
estaba parado el usuario—, cómo se reconoce que una copia es del registro
original y cómo se vuelve a ella. Cuándo se escribe, dónde y cuándo se borra es de
`ui/work_guard.py`.

**La copia es un diccionario de tipos de JSON** y no un objeto: se escribe y se
lee de un archivo que pudo quedar cortado por el mismo corte de luz, así que
`restore()` desconfía de todo lo que trae y lo rechaza entero antes de tocar la
sesión.

Cubre del pliego: ningún ID; es infraestructura del trabajo del investigador.
"""

from hashlib import sha256
import math
from typing import Any, Final

import numpy as np

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import ChannelKind, Recording
from psglab.core.session import Session
from psglab.core.windows import count_windows
from psglab.utils.errors import PsgLabError, UnreadableRecoveryError

#: La forma de la copia. Las copias de otra versión no coinciden con ésta.
RECOVERY_FORMAT: Final[int] = 2
_HASH_CHUNK_BYTES: Final[int] = 1024 * 1024


def fingerprint(original_recording: Recording) -> dict[str, Any]:
    """Calcula una identidad estable del registro fuente, incluido todo su contenido.

    Se recorre la matriz en bloques para no crear una segunda copia grande de
    una noche completa en memoria. La identidad resultante sólo contiene JSON.
    """
    if not isinstance(original_recording, Recording):
        raise PsgLabError(
            "No se pudo identificar el registro para recuperación.",
            details=f"original_recording es {type(original_recording).__name__}, se esperaba Recording.",
        )
    digest = sha256()
    elementos = max(1, _HASH_CHUNK_BYTES // original_recording.data.dtype.itemsize)
    for bloque in np.nditer(
        original_recording.data,
        flags=["external_loop", "buffered"],
        op_flags=["readonly"],
        order="C",
        buffersize=elementos,
    ):
        # `external_loop` may expose a strided view when the input matrix is
        # non-contiguous. Convert just this bounded buffer to C-order bytes.
        digest.update(bloque.tobytes(order="C"))
    return {
        "archivo": original_recording.file_path.name,
        "inicio": (
            original_recording.start_time.isoformat()
            if original_recording.start_time is not None
            else None
        ),
        "frecuencia": float(original_recording.sampling_rate),
        "muestras": int(original_recording.n_samples),
        "canales": [
            [c.name, c.kind.name, c.unit, c.original_sampling_rate]
            for c in original_recording.channels
        ],
        "dtype": original_recording.data.dtype.str,
        "sha256": digest.hexdigest(),
    }


def snapshot(session: Session, source_identity: dict[str, Any] | None = None) -> dict[str, Any]:
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
    if source_identity is None:
        source_identity = fingerprint(session.recording)
    _validate_identity(source_identity)
    scoring = session.scoring
    ventanas = [scoring.get(i) for i in range(scoring.n_windows)]
    anotaciones = session.annotations
    return {
        "formato": RECOVERY_FORMAT,
        "registro": source_identity,
        "derivaciones": [
            [*channel.derived_from, channel.name, channel.kind.name]
            for channel in session.recording.channels
            if getattr(channel, "derived_from", None) is not None
        ],
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


def matches(data: object, source_identity: dict[str, Any] | Recording) -> bool:
    """Si la copia es de este registro, y de esta forma de copia.

    Compara la identidad del registro fuente, incluida una huella SHA-256 de
    toda la señal y los metadatos que fijan tiempo, frecuencia y canales.

    Raises:
        PsgLabError: si `recording` no es un registro. Una copia rota no eleva:
            simplemente no coincide.
    """
    if isinstance(source_identity, Recording):
        source_identity = fingerprint(source_identity)
    if not isinstance(source_identity, dict):
        raise PsgLabError(
            "No se pudo comparar la copia de recuperación con el registro.",
            details=f"source_identity es {type(source_identity).__name__}, se esperaba dict.",
        )
    _validate_identity(source_identity)
    if not isinstance(data, dict):
        return False
    return data.get("formato") == RECOVERY_FORMAT and data.get("registro") == source_identity


def summary(data: object) -> tuple[int, int]:
    """Cuántas ventanas con trabajo y cuántas anotaciones trae la copia.

    Es lo que la pregunta le muestra al usuario, y lo que dice si vale la pena
    preguntar: una copia con cero y cero no tiene nada que recuperar.

    Raises:
        UnreadableRecoveryError: si la copia no tiene la forma esperada.
    """
    fases, arousals, _clases, anotaciones = _partes(data)
    if not all(
        isinstance(indice, int)
        and not isinstance(indice, bool)
        and 0 <= indice < len(fases)
        for indice in arousals
    ):
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details="Los arousals de la copia no son índices de ventana válidos.",
        )
    con_fase = {i for i, fase in enumerate(fases) if fase != SleepStage.UNSCORED.name}
    return len(con_fase | set(arousals)), len(anotaciones)


def preflight(
    session: Session,
    data: object,
    source_identity: dict[str, Any] | None = None,
    recording: Recording | None = None,
) -> None:
    """Valida íntegramente una copia contra el registro candidato, sin mutar nada."""
    _validate_restore(session, data, source_identity, recording)


def restore(
    session: Session, data: object, source_identity: dict[str, Any] | None = None
) -> None:
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
    if source_identity is None:
        source_identity = fingerprint(session.recording)
    _validate_restore(session, data, source_identity, session.recording)
    copia: dict[str, Any] = data if isinstance(data, dict) else {}
    scoring = session.scoring
    nomenclatura_antes = scoring.nomenclature
    colores_antes = dict(session.annotations._colors)
    ventana_antes = session.current_window
    fases, arousals, clases, anotaciones = _partes(copia)
    nomenclatura = Nomenclature[copia["nomenclatura"]]
    etapas = [SleepStage[nombre] for nombre in fases]
    ventana = copia["ventana"]
    recuperadas = [Annotation(etiqueta, inicio, duracion, tuple(canales), color)
                   for etiqueta, inicio, duracion, canales, color in anotaciones]

    try:
        scoring.change_nomenclature(nomenclatura)
        for indice, etapa in enumerate(etapas):
            if etapa is not SleepStage.UNSCORED:
                scoring.set_stage(indice, etapa)
        for indice in arousals:
            scoring.set_arousal(indice, True)
        for clase, color in clases:
            if clase not in session.annotations.labels():
                session.annotations.add_label(clase, color)
        for anotacion in recuperadas:
            session.annotations.add(anotacion)
        if scoring.n_windows:
            session.go_to_window(ventana)
    except Exception as error:
        _deshacer(session)
        scoring.change_nomenclature(nomenclatura_antes)
        session.annotations._colors = colores_antes
        if scoring.n_windows:
            session.go_to_window(ventana_antes)
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details=f"{type(error).__name__}: {error}",
        ) from error


def _validate_restore(
    session: Session,
    data: object,
    source_identity: dict[str, Any] | None,
    recording: Recording | None,
) -> None:
    """Comprueba todos los datos y su relación con el candidato antes de escribir."""
    if not isinstance(session, Session):
        raise PsgLabError(
            "No se pudo recuperar el trabajo.",
            details=f"session es {type(session).__name__}, se esperaba Session.",
        )
    if recording is None:
        recording = session.recording
    if not isinstance(recording, Recording):
        raise PsgLabError("No se pudo validar la recuperación contra el registro.", details="recording debe ser Recording.")
    if source_identity is None:
        source_identity = fingerprint(recording)
    _validate_identity(source_identity)
    if not matches(data, source_identity):
        raise UnreadableRecoveryError(
            "La copia de recuperación no es de este registro.",
            details="matches() dio False: otro archivo, otra forma de copia o una copia rota.",
        )
    # `matches()` ya comprobó que es un diccionario; esto sólo lo nombra.
    copia: dict[str, Any] = data  # type: ignore[assignment]
    scoring = session.scoring
    if count_windows(recording.n_samples, recording.sampling_rate) != scoring.n_windows:
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede aplicar a este montaje.",
            details="La cantidad de ventanas del registro candidato no coincide con el scoring.",
        )
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
    canales = set(recording.channel_names())
    if not all(
        isinstance(a.onset_sample, int)
        and isinstance(a.duration_samples, int)
        and 0 <= a.onset_sample
        and a.end_sample <= recording.n_samples
        and all(isinstance(canal, str) for canal in a.channels)
        and set(a.channels) <= canales
        for a in recuperadas
    ):
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details="Una anotación cae fuera del registro o sobre un canal que no tiene.",
        )
    _validar_derivaciones(copia.get("derivaciones"), recording)
    # Emula las validaciones del conjunto real, sobre uno temporal. Así una
    # etiqueta/color/anotación malformada nunca llega a la primera escritura.
    temporal = AnnotationSet()
    try:
        for clase, color in clases:
            if not isinstance(clase, str) or (color is not None and not isinstance(color, str)):
                raise ValueError("clase o color no es texto")
            if clase not in temporal.labels():
                temporal.add_label(clase, color)
        for etiqueta, inicio, duracion, canales_evento, color in anotaciones:
            temporal.add(Annotation(etiqueta, inicio, duracion, tuple(canales_evento), color))
    except (PsgLabError, TypeError, ValueError) as error:
        raise UnreadableRecoveryError(
            "La copia de recuperación no se puede leer.",
            details=f"Clase, color o anotación inválida: {error!r}",
        ) from error


def _validate_identity(identity: object) -> None:
    if not isinstance(identity, dict):
        valido = False
    else:
        canales = identity.get("canales")
        frecuencia = identity.get("frecuencia")
        muestras = identity.get("muestras")
        digest = identity.get("sha256")
        valido = (
            isinstance(identity.get("archivo"), str)
            and (identity.get("inicio") is None or isinstance(identity.get("inicio"), str))
            and isinstance(frecuencia, (int, float))
            and not isinstance(frecuencia, bool)
            and math.isfinite(frecuencia)
            and frecuencia > 0
            and isinstance(muestras, int)
            and not isinstance(muestras, bool)
            and muestras > 0
            and isinstance(canales, list)
            and all(
                isinstance(c, list)
                and len(c) == 4
                and isinstance(c[0], str)
                and isinstance(c[1], str)
                and c[1] in ChannelKind.__members__
                and isinstance(c[2], str)
                and (c[3] is None or isinstance(c[3], (int, float)))
                for c in canales
            )
            and isinstance(identity.get("dtype"), str)
            and isinstance(digest, str)
            and len(digest) == 64
            and all(ch in "0123456789abcdef" for ch in digest)
        )
    if not valido:
        raise PsgLabError(
            "No se pudo guardar la copia de recuperación.",
            details="source_identity no tiene la forma de fingerprint().",
        )


def _validar_derivaciones(derivaciones: object, recording: Recording) -> None:
    if not isinstance(derivaciones, list):
        raise UnreadableRecoveryError("La copia de recuperación no se puede leer.", details="La receta de derivaciones no es una lista.")
    actuales = [
        [*channel.derived_from, channel.name, channel.kind.name]
        for channel in recording.channels
        if getattr(channel, "derived_from", None) is not None
    ]
    if derivaciones != actuales:
        raise UnreadableRecoveryError("La copia de recuperación no corresponde al montaje.", details="Las derivaciones del registro no coinciden con la copia.")
    disponibles = {c.name for c in recording.channels if getattr(c, "derived_from", None) is None}
    vistos: set[str] = set()
    for entrada in derivaciones:
        if not isinstance(entrada, list) or len(entrada) != 4 or not all(isinstance(v, str) for v in entrada):
            raise UnreadableRecoveryError("La copia de recuperación no se puede leer.", details="Una derivación no tiene la forma esperada.")
        fuente_a, fuente_b, nombre, clase = entrada
        if nombre in vistos or fuente_a not in disponibles or fuente_b not in disponibles:
            raise UnreadableRecoveryError("La copia de recuperación no se puede leer.", details="Las fuentes u orden de derivación no son válidos.")
        if clase not in ChannelKind.__members__:
            raise UnreadableRecoveryError("La copia de recuperación no se puede leer.", details="Tipo de canal derivado desconocido.")
        disponibles.add(nombre)
        vistos.add(nombre)

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

    Quien llama restaura después la nomenclatura y los colores previos.
    """
    scoring = session.scoring
    for indice in range(scoring.n_windows):
        scoring.set_stage(indice, SleepStage.UNSCORED)
        scoring.set_arousal(indice, False)
    for anotacion in session.annotations.all():
        session.annotations.remove(anotacion)
