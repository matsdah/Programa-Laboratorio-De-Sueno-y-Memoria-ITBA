"""Importación de un scoring ya existente.

El pliego (V3_F de "Importación de archivos") pide poder abrir una señal ya
scoreada y ver en qué fase está cada ventana. Eso permite dos casos de uso
reales del laboratorio: retomar un trabajo interrumpido y revisar o corregir
el scoring hecho por otra persona.

El formato nativo es el mismo "Scoring.txt" que produce el programa (V1_F de
"Archivo de salida").

Los códigos de fase no son únicos entre nomenclaturas: "2" es S2 en
Rechtschaffen y Kales y N2 en AASM. Leer un archivo con la nomenclatura
equivocada carga la noche entera mal traducida **sin ningún error visible**, así
que el lector no adivina nunca.

Los archivos que produce este programa arrancan con una cabecera que la declara
(`# AASM`), y `detect_nomenclature()` la lee. Para un archivo sin cabecera
—escrito a mano, o por una versión anterior— hay que pasarla por parámetro, y
ahí la responsabilidad es de quien llama.

**Este módulo no es un `Reader` y no entra en el despacho por formato.** No
produce un `Recording`, así que no tiene dónde encajar en `read_recording()`, y
además el scoring nativo se guarda con extensión `.txt`, que ningún lector de
señal reclama. Hay un motivo más concreto, medido sobre el material de prueba:
el hipnograma de la Sleep-EDF es un `.edf`, y si el despacho lo mandara acá
habría que decidir por contenido. Se resolvió al revés: el scoring entra por su
propia opción del menú, y `readers/edf.py` eleva un error que manda a esa opción
cuando le toca un EDF sin ninguna señal.

Cubre del pliego: V3_F de "Importación de archivos".
"""

from pathlib import Path

from psglab.config import SCORING_HEADER_PREFIX
from psglab.core.nomenclature import Nomenclature, stage_from_code
from psglab.core.scoring import Scoring
from psglab.utils.errors import ScoringMismatchError, UnreadableFileError

#: Cómo se puede escribir cada nomenclatura en la cabecera, en minúscula. Se
#: aceptan el nombre corto y el largo porque el archivo lo puede haber escrito
#: una persona: "# RK" y "# Rechtschaffen y Kales" son la misma intención.
_NOMBRES_DE_NOMENCLATURA: dict[str, Nomenclature] = {
    **{n.name.lower(): n for n in Nomenclature},
    **{n.value.lower(): n for n in Nomenclature},
}


def _leer_lineas(path: Path) -> list[str]:
    """El archivo entero, sin decidir todavía qué es cabecera y qué es dato.

    Se prueba UTF-8 y se cae a latin-1, que nunca falla. Un archivo de scoring
    es casi todo dígitos, pero la cabecera puede traer el nombre largo de la
    nomenclatura y el archivo puede venir de cualquier editor.

    Raises:
        UnreadableFileError: si el archivo no existe o no se puede leer.
    """
    try:
        crudo = path.read_bytes()
    except OSError as error:
        raise UnreadableFileError(
            f"No se pudo abrir el archivo de scoring '{path.name}'.",
            details=f"{type(error).__name__}: {error}",
        ) from error

    for codec in ("utf-8", "latin-1"):
        try:
            return crudo.decode(codec).splitlines()
        except UnicodeDecodeError:
            continue
    return crudo.decode("latin-1", errors="replace").splitlines()


def _es_comentario(linea: str) -> bool:
    return linea.lstrip().startswith(SCORING_HEADER_PREFIX)


def _lineas_con_datos(lineas: list[str]) -> list[tuple[int, str]]:
    """Las líneas que traen una ventana, con su número de línea del archivo.

    El número se conserva para poder nombrarlo en el error: "la línea 47 no se
    entiende" es accionable y "el archivo está mal" no.
    """
    return [
        (numero, linea.strip())
        for numero, linea in enumerate(lineas, start=1)
        if linea.strip() and not _es_comentario(linea)
    ]


def read_scoring(
    path: Path,
    n_windows: int,
    nomenclature: Nomenclature | None = None,
) -> Scoring:
    """Carga un archivo de scoring y lo asocia a un registro.

    Args:
        path: archivo de scoring, con el formato de "Scoring.txt".
        n_windows: cantidad de ventanas del registro abierto. Sirve para
            detectar que el scoring no corresponde a este registro.
        nomenclature: nomenclatura con la que interpretar los códigos de fase.
            **La cabecera del archivo tiene prioridad sobre este parámetro**:
            el archivo sabe mejor que quien lo abre con qué se escribió. Sólo
            se usa si el archivo no la declara, y si no la declara y tampoco se
            pasa, se eleva un error en vez de adivinar.

    Returns:
        El scoring cargado. Las ventanas ausentes del archivo quedan como
        UNSCORED, para que el usuario pueda completar un scoring parcial. Las
        que el archivo marca con el código de UNSCORED (-1) también.

    Raises:
        ScoringMismatchError: si el archivo tiene más ventanas que el registro.
        UnreadableFileError: si alguna línea no respeta el formato esperado, o
            si no hay forma de saber la nomenclatura.
    """
    # **El archivo se lee una sola vez.** Antes `read_scoring()` llamaba a
    # `_leer_lineas()` y despues a `detect_nomenclature()` y
    # `detect_line_format()`, que la llaman de nuevo: tres lecturas del disco
    # en tres momentos distintos. Si el archivo cambiaba entre ellas, la
    # nomenclatura y el formato de linea podian no corresponder al contenido
    # que ya se habia leido.
    lineas = _leer_lineas(path)
    datos = _lineas_con_datos(lineas)

    elegida = _nomenclatura_de(lineas) or nomenclature
    if elegida is None:
        raise UnreadableFileError(
            f"No se sabe con qué nomenclatura se escribió '{path.name}', y adivinarla "
            "cargaría toda la noche mal traducida sin que se note: el código 2 es S2 "
            "en Rechtschaffen y Kales y N2 en AASM.",
            details=(
                "El archivo no declara la nomenclatura en su cabecera y no se pasó "
                "ninguna por parámetro."
            ),
        )

    lleva_numero = _lleva_numero_de_ventana(datos)
    scoring = Scoring(n_windows, elegida)

    for posicion, (numero_de_linea, linea) in enumerate(datos):
        campos = linea.split()
        esperados = 3 if lleva_numero else 2
        if len(campos) != esperados:
            raise UnreadableFileError(
                f"La línea {numero_de_linea} de '{path.name}' no tiene el formato "
                f"esperado de {esperados} campos.",
                details=f"Se leyó {linea!r}, con {len(campos)} campo(s).",
            )

        try:
            numeros = [int(c) for c in campos]
        except ValueError as error:
            raise UnreadableFileError(
                f"La línea {numero_de_linea} de '{path.name}' tiene un valor que no es "
                "un número entero.",
                details=f"Se leyó {linea!r}.",
            ) from error

        if lleva_numero:
            # El número de ventana del archivo es base 1, como todo lo que ve
            # el usuario; adentro del programa las ventanas son base 0.
            indice = numeros[0] - 1
            codigo, arousal = numeros[1], numeros[2]
        else:
            indice = posicion
            codigo, arousal = numeros[0], numeros[1]

        if not 0 <= indice < n_windows:
            raise ScoringMismatchError(
                f"El scoring de '{path.name}' no corresponde a este registro: nombra la "
                f"ventana {indice + 1} y el registro tiene {n_windows}.",
                details=f"Línea {numero_de_linea}: {linea!r}.",
            )

        try:
            fase = stage_from_code(codigo, elegida)
        except UnreadableFileError:  # pragma: no cover - defensivo
            raise
        except Exception as error:
            raise UnreadableFileError(
                f"La línea {numero_de_linea} de '{path.name}' no se pudo interpretar "
                f"con la nomenclatura {elegida.value}.",
                details=str(error),
            ) from error

        scoring.set_stage(indice, fase)
        scoring.set_arousal(indice, bool(arousal))

    return scoring


def detect_nomenclature(path: Path) -> Nomenclature | None:
    """Lee la nomenclatura declarada en la cabecera del archivo.

    Es la contraparte de `exporters.scoring_txt.format_header()`: lo que aquél
    escribe, éste lo tiene que poder volver a leer.

    Se aceptan el nombre corto y el largo —"AASM", "RK", "Rechtschaffen y
    Kales"— sin distinguir mayúsculas, porque el archivo puede haberlo escrito
    una persona y no el programa.

    Returns:
        La nomenclatura declarada, o None si el archivo no tiene cabecera. None
        no es un error: un archivo escrito a mano o por una versión anterior
        del programa es válido, sólo que hay que decirle al lector con qué
        nomenclatura interpretarlo.
    """
    return _nomenclatura_de(_leer_lineas(path))


def _nomenclatura_de(lineas: list[str]) -> Nomenclature | None:
    """Lo mismo que `detect_nomenclature()`, sobre líneas ya leídas.

    Existe para que `read_scoring()` no vuelva a abrir el archivo. La función
    pública conserva su firma —recibe una ruta— porque es API del módulo y la
    usa quien todavía no leyó nada.
    """
    for linea in lineas:
        if not linea.strip():
            continue
        if not _es_comentario(linea):
            # Las cabeceras van arriba de todo: en cuanto aparece un dato, no
            # hay más que buscar. Seguir leyendo haría que un comentario suelto
            # a mitad del archivo cambiara la interpretación de las líneas de
            # más arriba, que ya se leyeron con otra.
            return None
        etiqueta = linea.lstrip().lstrip(SCORING_HEADER_PREFIX).strip().lower()
        if etiqueta in _NOMBRES_DE_NOMENCLATURA:
            return _NOMBRES_DE_NOMENCLATURA[etiqueta]
    return None


def detect_line_format(path: Path) -> bool:
    """Detecta si el archivo incluye el número de ventana en cada línea.

    Se confirmó que el formato propio lleva dos campos, pero el lector acepta
    igual las dos variantes: un archivo de tres campos sigue siendo legible sin
    ambigüedad, y aceptarlo no cuesta nada. Decide mirando la primera línea con
    datos, salteando la cabecera.

    Returns:
        True si las líneas empiezan con el número de ventana.
    """
    return _lleva_numero_de_ventana(_lineas_con_datos(_leer_lineas(path)))


def _lleva_numero_de_ventana(datos: list[tuple[int, str]]) -> bool:
    """Lo mismo que `detect_line_format()`, sobre líneas ya leídas.

    Mismo motivo que `_nomenclatura_de()`: que `read_scoring()` lea el archivo
    una sola vez.
    """
    if not datos:
        return False
    return len(datos[0][1].split()) >= 3
