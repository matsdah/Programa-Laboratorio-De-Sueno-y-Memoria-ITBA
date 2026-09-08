"""Control de impedancia de los electrodos.

El usuario define un límite de impedancia y el programa avisa qué canales lo
superan. Una impedancia alta significa mal contacto entre el electrodo y el
cuero cabelludo, y la señal de ese canal no es confiable.

PENDIENTE DE DEFINICIÓN CON EL CLIENTE: de dónde salen las impedancias. Ni
EDF ni BrainVision las traen siempre. Hay tres caminos posibles y hay que
elegir uno antes de implementar:

    1. Leerlas de la cabecera del archivo cuando estén.
    2. Importarlas de un archivo aparte que exporte el equipo de adquisición.
    3. Que el usuario las cargue a mano al abrir el registro.

**Las tres están implementadas**, porque no son excluyentes. Lo que falta saber
es cuál usa el laboratorio, y eso decide qué se le ofrece primero al usuario,
no qué se puede hacer. Lo que sí quedó medido, y responde la mitad de la
pregunta:

- **BrainVision las trae.** El `.vhdr` tiene una tabla
  `Impedance [kOhm] at hh:mm:ss :` en su sección `[Comment]`, ya en kΩ, y MNE
  la parsea. `readers/brainvision.py` la guarda ahora en
  `Recording.metadata`, que es de donde la lee `read_impedances()`.
- **EDF no puede traerlas.** El estándar no tiene ningún campo de impedancia,
  ni en EDF ni en EDF+. Verificado contra la especificación y contra lo que MNE
  expone. Para un EDF, `read_impedances()` devuelve `{}` **siempre**, y no es
  un fallo: es lo que el formato permite. Por eso la vía del archivo aparte no
  es un extra sino la única disponible para la mitad del material.

**"No medido" no es "0 kΩ", y el módulo entero está construido alrededor de esa
distinción.** Un electrodo suelto que nadie midió es el caso peligroso: si
apareciera como 0 kΩ pasaría por perfecto. Por eso `read_impedances()` omite
los canales sin dato en vez de darles un número, y por eso el informe distingue
**tres** estados y no dos.

Cubre del pliego: V1_F de "Impedancia de los electrodos".
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

from psglab.core.recording import Recording
from psglab.utils.errors import InvalidRecordingError, UnreadableFileError

#: Límite por defecto, en kiloohmios. Es el criterio habitual para EEG.
DEFAULT_LIMIT_KOHM: Final[float] = 5.0

#: Dónde busca `read_impedances()` lo que dejó el lector.
METADATA_KEY: Final[str] = "brainvision_impedances"

#: Con qué empieza una línea de comentario en el archivo de impedancias. El
#: mismo que usa `readers/scoring_reader.py` para el archivo de scoring: es la
#: convención más difundida y no hay motivo para estrenar otra.
COMMENT_PREFIX: Final[str] = "#"

#: Unidades que se aceptan en el archivo, y por cuánto hay que multiplicar para
#: llegar a kΩ. Un valor en ohmios leído como kiloohmios da mil veces menos y
#: **ningún canal parecería fallar nunca**, que es la peor forma de fallar.
_A_KILOOHMIOS: Final[dict[str, float]] = {
    "kohm": 1.0,
    "kω": 1.0,
    "k": 1.0,
    "ohm": 0.001,
    "ω": 0.001,
}


def read_impedances(recording: Recording) -> dict[str, float]:
    """Impedancias por canal, en kiloohmios.

    Returns:
        Diccionario canal -> impedancia. Los canales sin dato no aparecen, en
        vez de figurar con cero: no es lo mismo "no medido" que "impedancia
        perfecta", y confundirlos ocultaría un electrodo suelto.

    Devuelve `{}` cuando el formato no las trae, que es **siempre** en EDF. No
    es un error: es lo que el estándar permite. Para esos registros hay que
    usar `load_impedances_from_file()` o cargarlas a mano.

    Raises:
        InvalidRecordingError: si no se le pasa un registro.
    """
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se pueden leer impedancias de eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )

    guardadas = recording.metadata.get(METADATA_KEY)
    if not isinstance(guardadas, dict):
        return {}
    conocidos = set(recording.channel_names())
    return {
        nombre: float(valor)
        for nombre, valor in guardadas.items()
        if nombre in conocidos
        and isinstance(valor, (int, float))
        and not math.isnan(float(valor))
    }


def load_impedances_from_file(path: Path) -> dict[str, float]:
    """Carga las impedancias desde un archivo externo.

    El formato es el mismo que el del scoring, por la misma razón: es un
    archivo que puede tener que escribir una persona.

        # Las líneas que empiezan con almohadilla se ignoran.
        C3    4.2
        C4    3.8 kOhm
        O1    12000 Ohm

    Un valor por línea: **nombre de canal, valor, y opcionalmente la unidad**.
    Sin unidad se asumen kiloohmios, que es lo que declara el equipo de
    adquisición y lo que usa todo el módulo.

    **La unidad no se adivina cuando está.** `readers/scoring_reader.py` fijó
    ese criterio para la nomenclatura y vale igual acá: un valor en ohmios
    interpretado como kiloohmios da mil veces menos y ningún canal parecería
    fallar nunca.

    Returns:
        Diccionario canal -> impedancia en kΩ.

    Raises:
        UnreadableFileError: si el archivo no se puede leer, si una línea no
            tiene el formato esperado, o si trae una unidad desconocida. El
            mensaje **nombra la línea**: "la línea 47 no se entiende" es
            accionable y "el archivo está mal" no.
    """
    if not isinstance(path, Path):
        raise UnreadableFileError(
            "Hay que decir qué archivo de impedancias abrir.",
            details=f"path es {type(path).__name__}: {path!r}.",
        )
    try:
        crudo = path.read_bytes()
    except OSError as error:
        raise UnreadableFileError(
            f"No se pudo abrir el archivo de impedancias «{path.name}».",
            details=f"{type(error).__name__}: {error}",
        ) from error

    # La misma cascada que `scoring_reader.py`: latin-1 nunca falla, así que
    # sirve de última red y el archivo siempre se puede leer.
    for codificacion in ("utf-8", "latin-1"):
        try:
            texto = crudo.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - latin-1 acepta cualquier byte
        texto = crudo.decode("latin-1", errors="replace")

    medidas: dict[str, float] = {}
    for numero, linea in enumerate(texto.splitlines(), start=1):
        limpia = linea.strip()
        if not limpia or limpia.startswith(COMMENT_PREFIX):
            continue
        campos = limpia.split()
        if len(campos) not in (2, 3):
            raise UnreadableFileError(
                f"La línea {numero} de «{path.name}» no tiene el formato "
                "esperado de canal, valor y opcionalmente la unidad.",
                details=f"Se leyó {linea!r}.",
            )
        nombre, crudo_valor = campos[0], campos[1]
        try:
            valor = float(crudo_valor.replace(",", "."))
        except ValueError as error:
            raise UnreadableFileError(
                f"La línea {numero} de «{path.name}» no trae un número donde "
                "tendría que ir la impedancia.",
                details=f"Se leyó {crudo_valor!r}: {error}",
            ) from error
        if valor < 0:
            raise UnreadableFileError(
                f"La línea {numero} de «{path.name}» tiene una impedancia "
                "negativa, que no existe.",
                details=f"Se leyó {valor}.",
            )

        factor = 1.0
        if len(campos) == 3:
            unidad = campos[2].lower()
            if unidad not in _A_KILOOHMIOS:
                raise UnreadableFileError(
                    f"La línea {numero} de «{path.name}» trae una unidad que no "
                    "se reconoce.",
                    details=(
                        f"Se leyó {campos[2]!r}; se esperaba una de "
                        f"{sorted(_A_KILOOHMIOS)}."
                    ),
                )
            factor = _A_KILOOHMIOS[unidad]
        medidas[nombre] = valor * factor

    return medidas


def _validar_limite(limit_kohm: float) -> float:
    """Rechaza como `PsgLabError` un límite que no sea un número positivo."""
    if isinstance(limit_kohm, bool) or not isinstance(limit_kohm, (int, float)):
        raise InvalidRecordingError(
            "El límite de impedancia tiene que ser un número.",
            details=f"limit_kohm es {type(limit_kohm).__name__}: {limit_kohm!r}.",
        )
    if not math.isfinite(limit_kohm) or limit_kohm <= 0:
        raise InvalidRecordingError(
            "El límite de impedancia tiene que ser mayor que cero.",
            details=f"limit_kohm = {limit_kohm}.",
        )
    return float(limit_kohm)


def _validar_medidas(impedances: dict[str, float]) -> dict[str, float]:
    """Rechaza como `PsgLabError` lo que no sea un diccionario de números."""
    if not isinstance(impedances, dict):
        raise InvalidRecordingError(
            "Las impedancias se dan como un diccionario de canal a kiloohmios.",
            details=f"impedances es {type(impedances).__name__}: {impedances!r}.",
        )
    limpias: dict[str, float] = {}
    for nombre, valor in impedances.items():
        if not isinstance(nombre, str) or isinstance(valor, bool):
            raise InvalidRecordingError(
                "Cada impedancia es el nombre de un canal y un número en kΩ.",
                details=f"se recibió {nombre!r}: {valor!r}.",
            )
        if not isinstance(valor, (int, float)):
            raise InvalidRecordingError(
                f"La impedancia de «{nombre}» no es un número.",
                details=f"se recibió {valor!r}.",
            )
        limpias[nombre] = float(valor)
    return limpias


def channels_above_limit(
    impedances: dict[str, float],
    limit_kohm: float = DEFAULT_LIMIT_KOHM,
) -> list[str]:
    """Canales cuya impedancia supera el límite fijado por el usuario.

    Returns:
        Los nombres, en el orden en que venían.

    **El límite es inclusivo**: exactamente 5 kΩ con un límite de 5 kΩ **pasa**.
    El límite es el máximo aceptable, no el primer valor rechazado, que es como
    lo lee cualquiera que escriba "impedancia menor a 5". Sólo se informa lo que
    lo supera de verdad.

    Un canal sin medir **no aparece acá**, porque no está en el diccionario. No
    es lo mismo que estar dentro del límite: para eso está `impedance_report()`,
    que sí distingue los tres estados.

    Raises:
        InvalidRecordingError: si las impedancias o el límite no son válidos.
    """
    medidas = _validar_medidas(impedances)
    limite = _validar_limite(limit_kohm)
    return [nombre for nombre, valor in medidas.items() if valor > limite]


def impedance_report(
    impedances: dict[str, float],
    limit_kohm: float = DEFAULT_LIMIT_KOHM,
    channels: list[str] | None = None,
) -> str:
    """Texto de alerta con los canales problemáticos.

    Distingue tres estados: dentro del límite, por encima del límite y sin
    medición disponible.

    Args:
        channels: todos los canales del registro. **Hace falta para el tercer
            estado y por eso se agregó**: con el diccionario solo, esta función
            no puede cumplir su propia promesa. `read_impedances()` omite los
            canales sin dato —a propósito, para no confundirlos con 0 kΩ—, así
            que lo que falta no está en ninguna parte del diccionario. Sin este
            argumento el informe habla nada más de lo que sí se midió, que es
            correcto pero incompleto.

    Returns:
        El texto, listo para mostrarle al investigador.

    Raises:
        InvalidRecordingError: si las impedancias, el límite o la lista de
            canales no son válidos.
    """
    medidas = _validar_medidas(impedances)
    limite = _validar_limite(limit_kohm)
    if channels is not None and (
        not isinstance(channels, (list, tuple))
        or not all(isinstance(nombre, str) for nombre in channels)
    ):
        raise InvalidRecordingError(
            "Los canales del registro se dan como una lista de nombres.",
            details=f"channels es {type(channels).__name__}: {channels!r}.",
        )

    altos = channels_above_limit(medidas, limite)
    bien = [nombre for nombre in medidas if nombre not in set(altos)]
    sin_medir = (
        [nombre for nombre in channels if nombre not in medidas]
        if channels is not None
        else []
    )

    lineas = [f"IMPEDANCIA DE LOS ELECTRODOS (límite: {_kohm(limite)})", ""]

    if altos:
        lineas.append(f"Por encima del límite ({len(altos)}):")
        lineas += [f"  {nombre} — {_kohm(medidas[nombre])}" for nombre in altos]
        lineas.append("")
        lineas.append(
            "La señal de esos canales no es confiable: una impedancia alta "
            "significa mal contacto con el cuero cabelludo."
        )
        lineas.append("")

    if bien:
        lineas.append(f"Dentro del límite ({len(bien)}):")
        lineas += [f"  {nombre} — {_kohm(medidas[nombre])}" for nombre in bien]
        lineas.append("")

    if sin_medir:
        lineas.append(f"Sin medición disponible ({len(sin_medir)}):")
        lineas += [f"  {nombre}" for nombre in sin_medir]
        lineas.append("")
        # **El estado que un informe descuidado pierde.** Decir "0 kΩ" o no
        # mencionarlos los haría pasar por buenos, que es exactamente el
        # electrodo suelto que este módulo existe para encontrar.
        lineas.append(
            "De esos canales no hay dato. **No quiere decir que estén bien**: "
            "quiere decir que nadie los midió."
        )
        lineas.append("")

    if not medidas:
        # **Cuando no hay ninguna medida, el informe tiene que decir qué
        # hacer.** Listar los canales sin medir y callarse deja al investigador
        # mirando una lista sin salida — y es el caso de todo EDF, donde el
        # formato no puede traerlas. Se dice aunque `sin_medir` tenga
        # contenido: que falten todas no es lo mismo que faltar algunas.
        lineas.append(
            "No hay ninguna impedancia cargada. Se pueden importar de un "
            "archivo del equipo de adquisición, o cargarlas a mano."
        )

    return "\n".join(lineas).rstrip() + "\n"


def _kohm(valor: float) -> str:
    """Un valor en kΩ, con la coma decimal del idioma del programa."""
    return f"{valor:.1f} kΩ".replace(".", ",")


__all__ = [
    "COMMENT_PREFIX",
    "DEFAULT_LIMIT_KOHM",
    "METADATA_KEY",
    "channels_above_limit",
    "impedance_report",
    "load_impedances_from_file",
    "read_impedances",
]
