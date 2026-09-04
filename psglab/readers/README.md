# `readers/` — importación de archivos

Todo lector recibe una ruta y devuelve un `Recording`. **El resto del programa
sólo llama a `read_recording()` y nunca sabe de qué formato vino la señal.**

Este es uno de los dos puntos de extensión del proyecto (el otro es
[`tools/`](../tools/README.md)). Es lo que hace alcanzable el objetivo del
pliego de importar "cualquier formato de archivo de registro de
polisomnografía": los formatos se suman de a uno sin rediseñar nada.

## Los archivos

| Archivo | De qué se ocupa | Pliego |
|---|---|---|
| `base.py` | La clase `Reader`, el registro de formatos y `read_recording()`. | Base de V1_F–V3_F de "Importación" |
| `brainvision.py` | Formato BrainVision (`.vhdr` + `.vmrk` + `.eeg`). | V1_F de "Importación" |
| `edf.py` | Formato EDF y EDF+. | V2_F de "Importación" |
| `scoring_reader.py` | Un scoring ya existente, para ver o corregir la fase de cada ventana. | V3_F de "Importación" |
| `channel_types.py` | Detección automática de la clase de cada canal (EEG, EOG, EMG, otro). | V4_F de "Visualización" |

## Cómo agregar un formato

No hace falta modificar ningún archivo existente:

```python
# psglab/readers/mi_formato.py
from pathlib import Path

from psglab.core.recording import Recording
from psglab.readers.base import Reader, register_reader


@register_reader
class MiFormatoReader(Reader):
    """Lectura de registros en formato Tal.

    Cubre del pliego: VN_F de "Importación de archivos".
    """

    format_name = "Formato Tal"
    extensions = (".tal",)

    def read(self, path: Path) -> Recording:
        ...
```

El formato aparece solo en el diálogo de apertura, porque el filtro se
construye recorriendo el registro (`file_dialog_filter()`).

`can_read()` ya viene implementado y compara la extensión contra `extensions`.
Sobrescribilo sólo si tu formato necesita inspeccionar el contenido del archivo
para decidir.

**No hace falta acordarse de importar el módulo nuevo**: `read_recording()`
consulta el registro y el paquete se recorre solo.

## El contrato de `read()`

Lo que devolvés tiene que cumplir dos cosas, porque ninguna capa posterior las
vuelve a verificar:

1. **La señal va en microvoltios.** La conversión se hace acá, una sola vez, con
   [`psglab/utils/units.py`](../utils/README.md). A partir de este punto nadie
   más se pregunta por la unidad.
2. **La clase de cada canal ya viene detectada**, con
   `channel_types.detect_channel_kind()`.

Si el archivo está corrupto o incompleto, elevá `UnreadableFileError` con un
mensaje en español; si ningún lector registrado maneja la extensión,
`read_recording()` ya eleva `UnsupportedFormatError` por su cuenta.

## `channel_types.py`

Resuelve V4_F: aceptar **cualquier canal, sin límite de tipo**, y saber de qué
tipo es. La detección usa el nombre (las posiciones del sistema 10-20 como
"C3" o "Fz" son EEG; el prefijo "EMG" es EMG) y la unidad declarada.

Es una heurística sobre nombres que escribió una persona, así que va a fallar
en algún registro. Por eso la clase detectada es un punto de partida que el
usuario puede corregir desde
[`ui/channel_selector.py`](../ui/README.md), no una decisión definitiva.

## Por qué MNE-Python

Cubre BrainVision y EDF de fábrica más una veintena de formatos, y ya trae
filtrado, ICA y re-referenciado, que son requisitos de la Parte 2. Escribir esos
parsers a mano sería reimplementar, con menos horas de revisión, algo que la
comunidad científica ya validó. Es BSD-3, compatible con la licencia MIT del
proyecto.

## Nota sobre los datos

**Los registros de participantes nunca se suben al repositorio.** El
`.gitignore` ya excluye `data/`, `registros/`, `*.edf`, `*.vhdr`, `*.vmrk` y
`*.eeg`. Los tests usan señal sintética generada en el momento, no registros
reales: ver [`tests/README.md`](../../tests/README.md).

**Los dos formatos ya tienen registro de prueba**, conseguidos al cerrar el
[hito 0](../../docs/TODO.md#hito-0-desbloquear); el detalle está más abajo, en
"Estado". Lo que sigue faltando es un registro **real del laboratorio**: el de
BrainVision dura 7,9 segundos y no alcanza para probar la importación de punta a
punta.

## Estado

Pendientes **9 stubs**, en el
[hito 4 del TODO](../../docs/TODO.md#hito-4-importación). Dependen de que
`core/recording.py` esté terminado (hito 1).

De `base.py` sólo falta `file_dialog_filter()`. `can_read()`,
`register_reader` y `read_recording()` ya están implementados a propósito:
corren en tiempo de importación y **no deben convertirse en stubs**.

**EDF ya tiene registro de prueba**: la Sleep-EDF Expanded de PhysioNet, abierta
y con hipnogramas en Rechtschaffen y Kales. Va en `data/`, que el `.gitignore`
excluye. El enlace y la licencia están en el
[hito 0](../../docs/TODO.md#hito-0-desbloquear).

**BrainVision** usa los archivos de prueba de MNE-Python (BSD-3): una tripleta
`.vhdr` + `.vmrk` + `.eeg` de 32 canales con nombres 10-20. Son **7,9 segundos,
no una noche**: alcanzan para verificar que el lector entiende el formato, no
para probar el programa de punta a punta. Un registro real del laboratorio
sigue siendo deseable.
