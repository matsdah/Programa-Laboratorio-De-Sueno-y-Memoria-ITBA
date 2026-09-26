"""Lectura de registros en formato EDF y EDF+.

EDF es el formato más difundido en polisomnografía. A diferencia de
BrainVision, es un archivo único y autocontenido.

Tres particularidades del formato se resuelven acá y no aguas abajo, y las tres
se midieron sobre el registro de prueba de la Sleep-EDF antes de escribir nada:

**Los canales pueden venir a frecuencias distintas.** El de prueba trae tres a
100 Hz y cuatro a 1 Hz. `Recording` asume una sola, y **MNE ya las unifica
sobremuestreando** —devuelve todo a 100 Hz sin avisar—, así que no hay nada que
remuestrear acá. Lo que sí hay que hacer es **no perder el dato**: un EMG de
1 Hz llevado a 100 Hz es señal repetida en escalones, y sin registrar su
frecuencia real el investigador vería una señal de aspecto normal sin forma de
saberlo. Va en `Channel.original_sampling_rate`, que se lee de la cabecera.

**MNE devuelve volts, no lo que dice la cabecera, pero sólo a veces.** Para los
canales cuya unidad reconoce aplica él mismo la dimensión física y entrega
**volts**: el canal `EEG Fpz-Cz`, que la cabecera declara en ±192 uV, sale como
±0,000192. Los que no reconoce los deja en la unidad del archivo. Por eso el
factor de cada canal **depende de qué hizo MNE con él**, y no sólo de la
unidad declarada:

- si MNE lo llevó a volts, se multiplica de volt a microvolt;
- si lo dejó como venía y la unidad es eléctrica, se convierte desde esa unidad;
- si no es eléctrica —una temperatura en "DegC", un marcador sin unidad— queda
  en su escala nativa, con su unidad.

**La regla de MNE distingue mayúsculas y la de `utils/units.py` no**, y ése fue
el error que encontró la auditoría del hito 33: MNE sólo convierte `uV`, `µV` y
`mV` escritos así, y un canal declarado en `uv` llegaba sin convertir, se
multiplicaba igual de volt a microvolt y quedaba 10⁶ veces más grande. La regla
de MNE está copiada en `_UNIDADES_QUE_MNE_PASA_A_VOLTS`; si una versión futura
la cambia, lo detectan los tests del EDF sintético, que escriben cada grafía.

**El canal de anotaciones de EDF+ no es una señal.** MNE ya lo excluye solo y lo
convierte en `raw.annotations`, así que no hay que descartarlo a mano. Sí hay
que contemplar que un archivo que **sólo** tenga ese canal —un hipnograma, como
el `SC4001EC-Hypnogram.edf` de la Sleep-EDF— vuelva sin ningún canal.

**Un EDF truncado se abre, pero avisa** (hito 33). Una copia interrumpida deja
el archivo más corto de lo que dice su cabecera, y MNE lee los registros de
datos que hay y avisa sólo por consola: sin más, abrir media noche no se
distinguía de abrir una noche entera. Se abre igual, porque lo que llegó puede
ser todo lo que el investigador tiene, y el aviso viaja en
`metadata[IMPORT_WARNINGS_KEY]` para que la ventana lo muestre.

Cubre del pliego: V2_F de "Importación de archivos".
"""

from pathlib import Path

import mne
import numpy as np

from psglab.core.recording import Channel, Recording
from psglab.readers.base import IMPORT_WARNINGS_KEY, MARKS_KEY, Reader, register_reader
from psglab.readers.channel_types import detect_channel_kind
from psglab.utils.errors import UnknownUnitError, UnreadableFileError
from psglab.utils.units import MICROVOLT, conversion_factor, is_electrical

#: Unidad en la que MNE entrega los canales que reconoce como eléctricos. No es
#: la que declara el archivo: es la del SI, que MNE usa internamente.
_UNIDAD_DE_MNE = "V"

#: Las grafías de unidad que MNE lleva a volts al leer un EDF, **exactamente
#: como las compara él**: con mayúsculas y sin normalizar. Copiadas de
#: `mne/io/edf/edf.py` (MNE 1.12): la mu griega, el signo micro, la mu de
#: Shift-JIS, `uV` y `mV`. `V` se agrega porque ya está en volts: MNE le
#: aplica un factor 1 y el resultado es el mismo.
#:
#: **Es la mitad de la regla que no se puede deducir de `utils/units.py`**, que
#: normaliza a minúscula: `uv` es microvoltios para las dos, pero MNE no lo
#: convierte y entrega los números tal cual. Ver el docstring del módulo.
_UNIDADES_QUE_MNE_PASA_A_VOLTS: frozenset[str] = frozenset(
    {"μV", "µV", "\x83\xcaV", "uV", "mV", "V"}
)

#: Etiquetas de los canales de anotaciones de EDF+ y BDF+. MNE los excluye de
#: la señal comparando la etiqueta exacta, y hay que excluirlos igual para que
#: las posiciones de la cabecera coincidan con las de MNE.
_CANALES_DE_ANOTACIONES: frozenset[str] = frozenset({"EDF Annotations", "BDF Annotations"})

#: Posiciones de la cabecera EDF, en bytes. El formato está congelado desde 1992
#: y por eso conviene leerla a mano: es más estable que apoyarse en los
#: atributos privados de MNE, que son los únicos que exponen estos dos datos.
_OFFSET_BYTES_DE_CABECERA = 184
_OFFSET_CANTIDAD_DE_REGISTROS = 236
_OFFSET_DURACION_REGISTRO = 244
_OFFSET_CANTIDAD_DE_SENALES = 252
_INICIO_CABECERA_DE_SENALES = 256


def _numero(campo: bytes) -> float | None:
    """Un campo numérico de la cabecera, o None si no se puede interpretar."""
    try:
        return float(campo.strip().decode("latin-1"))
    except ValueError:
        return None


def _leer_cabecera(path: Path) -> list[tuple[str, str, float | None]]:
    """Etiqueta, unidad declarada y frecuencia real de cada canal, **en orden**.

    MNE no expone la unidad ni la frecuencia después de leer: la unidad la
    consume al convertir a volts, y la cantidad de muestras por registro sólo
    vive en un atributo privado.

    **Se devuelve por posición y no por nombre** (hito 33). Hasta ahí era un
    diccionario por etiqueta, y un archivo con dos canales `EEG` perdía los dos:
    MNE los renombra `EEG-0` y `EEG-1`, la búsqueda no los encontraba y quedaban
    sin unidad, en volts y fuera del EEG. MNE conserva el orden de la cabecera y
    sólo saca los canales de anotaciones, así que quien llama los saca igual y
    empareja por posición.

    Las etiquetas y las unidades se recortan **como las recorta MNE**, sobre los
    bytes y antes de decodificar, para que las grafías coincidan con las que él
    compara. La frecuencia es accesoria: si su campo no se entiende, queda en
    None y el canal se lee igual.

    Returns:
        Una fila por canal de la cabecera, anotaciones incluidas, o la lista
        vacía si el archivo no se puede leer.
    """
    try:
        with path.open("rb") as archivo:
            archivo.seek(_OFFSET_DURACION_REGISTRO)
            duracion = _numero(archivo.read(8))
            archivo.seek(_OFFSET_CANTIDAD_DE_SENALES)
            cantidad = int(archivo.read(4).strip().decode("latin-1"))

            archivo.seek(_INICIO_CABECERA_DE_SENALES)
            etiquetas = [archivo.read(16).strip().decode("latin-1") for _ in range(cantidad)]
            archivo.seek(_INICIO_CABECERA_DE_SENALES + cantidad * 96)
            unidades = [archivo.read(8).strip().decode("latin-1") for _ in range(cantidad)]
            archivo.seek(_INICIO_CABECERA_DE_SENALES + cantidad * 216)
            muestras = [_numero(archivo.read(8)) for _ in range(cantidad)]
    except (OSError, ValueError):
        return []

    return [
        (
            etiqueta,
            unidad,
            n / duracion if n is not None and duracion is not None and duracion > 0 else None,
        )
        for etiqueta, unidad, n in zip(etiquetas, unidades, muestras)
    ]


def _duracion_declarada_si_falta(path: Path) -> float | None:
    """Los segundos que declara la cabecera, si el archivo trae menos que eso.

    Compara la cantidad de registros de datos que dice la cabecera con los que
    entran en el tamaño del archivo: cada registro ocupa dos bytes por muestra
    de cada canal, anotaciones incluidas.

    Returns:
        La duración declarada, o None si el archivo está entero o si no se puede
        saber: mientras un equipo graba, la cantidad de registros vale -1, y
        entonces el propio formato dice que se deduce del tamaño.
    """
    try:
        with path.open("rb") as archivo:
            archivo.seek(_OFFSET_BYTES_DE_CABECERA)
            bytes_de_cabecera = int(archivo.read(8).strip().decode("latin-1"))
            archivo.seek(_OFFSET_CANTIDAD_DE_REGISTROS)
            declarados = int(archivo.read(8).strip().decode("latin-1"))
            archivo.seek(_OFFSET_DURACION_REGISTRO)
            duracion = _numero(archivo.read(8))
            archivo.seek(_OFFSET_CANTIDAD_DE_SENALES)
            cantidad = int(archivo.read(4).strip().decode("latin-1"))
            archivo.seek(_INICIO_CABECERA_DE_SENALES + cantidad * 216)
            por_registro = sum(
                int(archivo.read(8).strip().decode("latin-1")) for _ in range(cantidad)
            )
        tamano = path.stat().st_size
    except (OSError, ValueError):
        return None
    if declarados <= 0 or por_registro <= 0 or duracion is None or duracion <= 0:
        return None
    presentes = (tamano - bytes_de_cabecera) // (2 * por_registro)
    if presentes >= declarados:
        return None
    return declarados * duracion


def _duracion_legible(segundos: float) -> str:
    """Una duración para un cartel: 7 h 58 min, 12 min 30 s o 45 s."""
    total = int(round(segundos))
    horas, resto = divmod(total, 3600)
    minutos, sueltos = divmod(resto, 60)
    if horas:
        return f"{horas} h {minutos:02d} min"
    if minutos:
        return f"{minutos} min {sueltos:02d} s"
    return f"{sueltos} s"


def _factor_a_microvoltios(unidad: str) -> float | None:
    """Por cuánto multiplicar la fila que entregó MNE para tenerla en µV.

    Returns:
        El factor, o None si el canal no es eléctrico y queda en su escala.
        **Una unidad eléctrica ambigua también da None** —"MV", que puede ser
        mega o mili—: `conversion_factor()` se niega a adivinarla, y el canal
        queda como vino y con su unidad a la vista en vez de impedir abrir el
        registro entero por uno solo.
    """
    if unidad in _UNIDADES_QUE_MNE_PASA_A_VOLTS:
        return conversion_factor(_UNIDAD_DE_MNE)
    if not is_electrical(unidad):
        return None
    try:
        return conversion_factor(unidad)
    except UnknownUnitError:
        return None


@register_reader
class EdfReader(Reader):
    """Lector de registros EDF y EDF+."""

    format_name = "European Data Format"
    extensions = (".edf",)

    @classmethod
    def warm_up(cls) -> None:
        """Importa el lector de EDF de MNE, que `mne.io` carga recién al usarlo.

        Ver `Reader.warm_up()`: es la mayor parte de los 9 s que tardaba la
        primera apertura de cada sesión del programa.
        """
        import mne.io.edf  # noqa: F401 - importarlo es el trabajo

    def read(self, path: Path) -> Recording:
        """Carga un registro EDF.

        Raises:
            UnreadableFileError: si el archivo está dañado o truncado, o si no
                trae ninguna señal —el caso de un hipnograma, que es un EDF+ de
                anotaciones y no un registro—.
        """
        if not path.exists():
            # Antes caía en el `except` de abajo y se informaba como dañado, que
            # manda a buscar el problema al lugar equivocado (hito 33).
            raise UnreadableFileError(
                f"No se encontró el archivo «{path.name}».",
                details=f"No existe {path}.",
            )
        try:
            crudo = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
        except Exception as error:  # noqa: BLE001 - MNE eleva de todo
            raise UnreadableFileError(
                f"No se pudo leer el registro «{path.name}»: el archivo está dañado o "
                "no tiene el formato EDF esperado.",
                details=f"{type(error).__name__}: {error}",
            ) from error

        if not crudo.ch_names:
            raise UnreadableFileError(
                f"El archivo «{path.name}» no trae ninguna señal, así que no es un "
                "registro. Si es un scoring o un hipnograma, se importa desde la "
                "opción de importar un scoring y no desde la de abrir un registro.",
                details="El EDF sólo contiene el canal de anotaciones de EDF+.",
            )

        # Los canales de señal de la cabecera, en el orden en que los entrega
        # MNE: el de la cabecera sin los de anotaciones.
        cabecera = [
            (unidad, frecuencia)
            for etiqueta, unidad, frecuencia in _leer_cabecera(path)
            if etiqueta not in _CANALES_DE_ANOTACIONES
        ]
        if len(cabecera) != len(crudo.ch_names):
            # **La unidad no es un dato accesorio**: sin ella no se sabe si la
            # fila está en volts o en la unidad del archivo, y adivinar deja la
            # señal corrida en un factor mil o un millón. Hasta el hito 33 este
            # caso seguía con todo sin convertir.
            raise UnreadableFileError(
                f"No se pudo leer el registro «{path.name}»: no se entiende en qué "
                "unidad está cada canal.",
                details=(
                    f"La cabecera describe {len(cabecera)} canales de señal y MNE "
                    f"leyó {len(crudo.ch_names)}."
                ),
            )
        datos = np.asarray(crudo.get_data(), dtype=float)

        canales: list[Channel] = []
        for posicion, nombre in enumerate(crudo.ch_names):
            unidad_declarada, frecuencia_original = cabecera[posicion]
            factor = _factor_a_microvoltios(unidad_declarada)
            if factor is not None:
                # **En sitio**: `to_microvolts()` devuelve un array nuevo, y sobre
                # el registro de prueba eso eran 42 ms por canal en copias que se
                # descartaban enseguida.
                datos[posicion] *= factor
                unidad_de_la_fila = MICROVOLT
            else:
                unidad_de_la_fila = unidad_declarada
            canales.append(
                Channel(
                    name=nombre,
                    # La clase se deduce de la unidad del archivo: es la que dice
                    # que un canal en grados no puede ser un EEG. Si el canal se
                    # convirtió se le pasa µV, porque MNE reconoce grafías —la mu
                    # de Shift-JIS— que la detección no, y el veto de la unidad
                    # dejaría fuera del EEG un canal que sí lo es.
                    kind=detect_channel_kind(
                        nombre, MICROVOLT if factor is not None else unidad_declarada
                    ),
                    unit=unidad_de_la_fila,
                    index=posicion,
                    original_sampling_rate=frecuencia_original,
                )
            )

        metadatos: dict[str, object] = {}
        if len(crudo.annotations):
            metadatos[MARKS_KEY] = [
                (float(a["onset"]), float(a["duration"]), str(a["description"]))
                for a in crudo.annotations
            ]
        declarada = _duracion_declarada_si_falta(path)
        if declarada is not None:
            leida = datos.shape[1] / float(crudo.info["sfreq"])
            metadatos[IMPORT_WARNINGS_KEY] = [
                f"«{path.name}» está incompleto: trae {_duracion_legible(leida)} de "
                f"los {_duracion_legible(declarada)} que declara su cabecera. Se abrió "
                "lo que hay; el resto no está en el archivo, probablemente porque se "
                "copió o se grabó a medias."
            ]

        return Recording(
            file_path=path,
            channels=canales,
            data=datos,
            sampling_rate=float(crudo.info["sfreq"]),
            start_time=crudo.info.get("meas_date"),
            metadata=metadatos,
        )
