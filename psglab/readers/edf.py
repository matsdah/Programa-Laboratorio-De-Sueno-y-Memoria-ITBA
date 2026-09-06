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

**MNE devuelve volts, no lo que dice la cabecera.** Para los canales cuya unidad
reconoce aplica él mismo la dimensión física y entrega **volts**: el canal
`EEG Fpz-Cz`, que la cabecera declara en ±192 uV, sale como ±0,000192. Los que
no reconoce —una temperatura en "DegC", un marcador sin unidad— los deja en su
escala nativa. Por eso la conversión de acá es siempre **de volt a microvolt** y
no la que correspondería a la unidad del archivo: aplicar
`conversion_factor("uV")`, que vale 1, dejaría la señal en volts, un millón de
veces más chica, y en pantalla con autoescala seguiría pareciendo una señal.

**El canal de anotaciones de EDF+ no es una señal.** MNE ya lo excluye solo y lo
convierte en `raw.annotations`, así que no hay que descartarlo a mano. Sí hay
que contemplar que un archivo que **sólo** tenga ese canal —un hipnograma, como
el `SC4001EC-Hypnogram.edf` de la Sleep-EDF— vuelva sin ningún canal.

Cubre del pliego: V2_F de "Importación de archivos".
"""

from pathlib import Path

import mne
import numpy as np

from psglab.core.recording import Channel, Recording
from psglab.readers.base import Reader, register_reader
from psglab.readers.channel_types import detect_channel_kind
from psglab.utils.errors import UnreadableFileError
from psglab.utils.units import MICROVOLT, is_electrical, to_microvolts

#: Unidad en la que MNE entrega los canales que reconoce como eléctricos. No es
#: la que declara el archivo: es la del SI, que MNE usa internamente.
_UNIDAD_DE_MNE = "V"

#: Posiciones de la cabecera EDF, en bytes. El formato está congelado desde 1992
#: y por eso conviene leerla a mano: es más estable que apoyarse en los
#: atributos privados de MNE, que son los únicos que exponen estos dos datos.
_OFFSET_DURACION_REGISTRO = 244
_OFFSET_CANTIDAD_DE_SENALES = 252
_INICIO_CABECERA_DE_SENALES = 256


def _leer_cabecera(path: Path) -> dict[str, tuple[str, float | None]]:
    """Unidad declarada y frecuencia real de cada canal, leídas del archivo.

    MNE no expone ninguna de las dos después de unificar las frecuencias: la
    unidad la consume al convertir a volts, y la cantidad de muestras por
    registro sólo vive en un atributo privado.

    Se indexa **por nombre y no por posición**: si el archivo trae un canal
    "EDF Annotations", MNE lo excluye y las posiciones dejan de coincidir.

    Devuelve un diccionario vacío si la cabecera no se puede interpretar. **No
    es un error**: son datos accesorios, y perderlos es mejor que no poder abrir
    un archivo que MNE sí sabe leer.
    """
    try:
        with path.open("rb") as archivo:
            archivo.seek(_OFFSET_DURACION_REGISTRO)
            duracion = float(archivo.read(8))
            archivo.seek(_OFFSET_CANTIDAD_DE_SENALES)
            cantidad = int(archivo.read(4))

            archivo.seek(_INICIO_CABECERA_DE_SENALES)
            nombres = [archivo.read(16).decode("latin-1").strip() for _ in range(cantidad)]
            archivo.seek(_INICIO_CABECERA_DE_SENALES + cantidad * 96)
            unidades = [archivo.read(8).decode("latin-1").strip() for _ in range(cantidad)]
            archivo.seek(_INICIO_CABECERA_DE_SENALES + cantidad * 216)
            muestras = [int(archivo.read(8)) for _ in range(cantidad)]
    except (OSError, ValueError, UnicodeDecodeError):
        return {}

    if duracion <= 0:
        return {nombre: (unidad, None) for nombre, unidad in zip(nombres, unidades)}
    return {
        nombre: (unidad, n / duracion)
        for nombre, unidad, n in zip(nombres, unidades, muestras)
    }


@register_reader
class EdfReader(Reader):
    """Lector de registros EDF y EDF+."""

    format_name = "European Data Format"
    extensions = (".edf",)

    def read(self, path: Path) -> Recording:
        """Carga un registro EDF.

        Raises:
            UnreadableFileError: si el archivo está dañado o truncado, o si no
                trae ninguna señal —el caso de un hipnograma, que es un EDF+ de
                anotaciones y no un registro—.
        """
        try:
            crudo = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
        except Exception as error:  # noqa: BLE001 - MNE eleva de todo
            raise UnreadableFileError(
                f"No se pudo leer el registro '{path.name}': el archivo está dañado o "
                "no tiene el formato EDF esperado.",
                details=f"{type(error).__name__}: {error}",
            ) from error

        if not crudo.ch_names:
            raise UnreadableFileError(
                f"El archivo '{path.name}' no trae ninguna señal, así que no es un "
                "registro. Si es un scoring o un hipnograma, se importa desde la "
                "opción de importar un scoring y no desde la de abrir un registro.",
                details="El EDF sólo contiene el canal de anotaciones de EDF+.",
            )

        cabecera = _leer_cabecera(path)
        datos = np.asarray(crudo.get_data(), dtype=float)

        canales: list[Channel] = []
        for posicion, nombre in enumerate(crudo.ch_names):
            unidad_declarada, frecuencia_original = cabecera.get(nombre, ("", None))
            if is_electrical(unidad_declarada):
                # MNE ya aplicó la dimensión física del archivo y entregó volts.
                datos[posicion] = to_microvolts(datos[posicion], _UNIDAD_DE_MNE)
                unidad_de_la_fila = MICROVOLT
            else:
                unidad_de_la_fila = unidad_declarada
            canales.append(
                Channel(
                    name=nombre,
                    # La clase se deduce de la unidad **declarada**, no de la de
                    # la fila: es la del archivo la que dice que un canal en
                    # grados no puede ser un EEG.
                    kind=detect_channel_kind(nombre, unidad_declarada),
                    unit=unidad_de_la_fila,
                    index=posicion,
                    original_sampling_rate=frecuencia_original,
                )
            )

        metadatos: dict[str, object] = {}
        if len(crudo.annotations):
            metadatos["edf_annotations"] = [
                (float(a["onset"]), float(a["duration"]), str(a["description"]))
                for a in crudo.annotations
            ]

        return Recording(
            file_path=path,
            channels=canales,
            data=datos,
            sampling_rate=float(crudo.info["sfreq"]),
            start_time=crudo.info.get("meas_date"),
            metadata=metadatos,
        )
