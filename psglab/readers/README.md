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
| `base.py` | La clase `Reader`, el registro de formatos y `read_recording()`. | Base de V1_F y V2_F de "Importación" |
| `brainvision.py` | Formato BrainVision (`.vhdr` + `.vmrk` + `.eeg`). | V1_F de "Importación" |
| `edf.py` | Formato EDF y EDF+. | V2_F de "Importación" |
| `scoring_reader.py` | Un scoring ya existente, para ver o corregir la fase de cada ventana. Elige el lector por la extensión y lee él mismo el `.txt`. | V3_F de "Importación" |
| `scoring_formats.py` | Un scoring en CSV, EDF+ o XML del NSRR, escrito por este programa o por otro. | V3_F de "Importación" |
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

`warm_up()` tampoco hace nada por defecto. Sobrescribilo **si tu formato paga
algo caro la primera vez**, para que lo pague el hilo de precalentamiento y no
el usuario: los dos lectores que hay importan ahí el módulo que `mne.io` carga
recién al usarlo, que eran 8,65 de los 9,2 s de la primera apertura de cada
sesión (hito 33). Se adelantan importaciones, nunca lecturas: no toca el disco
del usuario.

**No hace falta acordarse de importar el módulo nuevo**: `load_all_readers()`
recorre el paquete e importa lo que encuentre, y `read_recording()` y
`file_dialog_filter()` la llaman antes de consultar el registro.

Eso es lo que hace que agregar un formato no obligue a tocar ningún archivo
existente, ni siquiera el `__init__.py` de esta carpeta. Es a propósito que ahí
no haya una lista de importaciones: sería exactamente el archivo que habría que
editar cada vez.

## El contrato de `read()`

Lo que devolvés tiene que cumplir dos cosas, porque ninguna capa posterior las
vuelve a verificar:

1. **La señal va en microvoltios.** La conversión se hace acá, una sola vez, con
   [`psglab/utils/units.py`](../utils/README.md). A partir de este punto nadie
   más se pregunta por la unidad.

   **Si el lector se apoya en MNE, el factor depende de qué hizo MNE con cada
   canal**, y no sólo de la unidad declarada: MNE lleva a volts las grafías que
   reconoce, comparándolas con mayúsculas, y deja las demás como vienen. Los
   dos lectores copian esa regla en `_UNIDADES_QUE_MNE_PASA_A_VOLTS`, leen la
   cabecera como la lee MNE y la emparejan con sus canales **por posición**,
   porque MNE renombra los repetidos. Confundir las dos cosas dejaba un canal en
   `uv` un millón de veces más grande (hito 33).
2. **La clase de cada canal ya viene detectada**, con
   `channel_types.detect_channel_kind()`.

Si el archivo está corrupto, elevá `UnreadableFileError` con un mensaje en
español; si ningún lector registrado maneja la extensión, `read_recording()` ya
eleva `UnsupportedFormatError` por su cuenta.

**Si se pudo leer pero con reservas** —un archivo que trae menos de lo que
declara su cabecera—, no se eleva: se devuelve lo que hay y se agrega un
mensaje para el investigador a la lista `metadata[IMPORT_WARNINGS_KEY]`, de
`base.py`. La ventana los muestra después de abrir el registro, sin saber de
qué formato vino. Hoy lo usa el EDF truncado (hito 33).

**Lo que no depende del formato no lo revisa cada lector.** Las muestras sin
valor —NaN o infinito— las cuenta `read_recording()` sobre el registro ya
armado, con `Recording.non_finite_channels()`, y suma su aviso a los que el
lector haya dejado. Así vale para cualquier formato, el que se agregue mañana
incluido: el EDF guarda enteros y no puede traerlas, pero un BrainVision en
`IEEE_FLOAT_32` sí. Cuesta el 3 % de lo que tarda abrir un registro de 22 h,
medido en el hito 33.

## El scoring de otros programas

`scoring_formats.py` lee un hipnograma como el de la Sleep-EDF, un XML del
NSRR o una planilla con punto y coma. **La nomenclatura no se adivina**: se
usa la que el archivo declara, o la única compatible con lo que trae; si las
dos son posibles, eleva `UndeclaredNomenclatureError` y la ventana le
pregunta al usuario. **Lo que escribe este programa la declara siempre**
(hito 69): el CSV en su columna `nomenclatura` y el EDF+ en la cabecera,
después del equipo `PSGLab`, que es lo único que hace creerle a ese subcampo.
Un CSV con una ventana repetida se rechaza, como el `.txt`. Los eventos con inicio y duración se pasan a épocas con
`core.windows.windows_in_span()`, por el punto medio de cada una.

Ninguno de los dos módulos de scoring es un `Reader`, y `load_all_readers()`
los saltea.

**Las marcas que trae el archivo** —los marcadores del `.vmrk`, las
anotaciones de un EDF+— se guardan en `metadata[MARKS_KEY]`, una sola clave
para los dos formatos, como `(inicio en segundos, duración, descripción)`. La
ventana las ofrece como anotaciones a pedido (hito 73).

## `channel_types.py`

Resuelve V4_F: aceptar **cualquier canal, sin límite de tipo**, y saber de qué
tipo es. La detección usa el nombre (las posiciones del sistema 10-20 como
"C3" o "Fz" son EEG; el prefijo "EMG" es EMG) y la unidad declarada.

Es una heurística sobre nombres que escribió una persona, así que va a fallar
en algún registro.

**Hoy no se puede corregir a mano, y es una limitación conocida.** `Channel` es
inmutable (`@dataclass(frozen=True)`) y
[`ui/channel_selector.py`](../ui/README.md) agrupa por clase pero no reasigna
ninguna. El daño está acotado: la clase decide cómo se agrupan los canales en el
selector y qué dice la etiqueta, no cómo se lee ni cómo se dibuja la señal, así
que un canal mal clasificado se ve y se scorea igual.

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

Pendientes **0 stubs** en 0 módulos: la carpeta está terminada. Era el
[hito 4 del TODO](../../docs/TODO.md#hito-4-importación). Dependían de
`core/recording.py`, terminado en el hito 1.

`can_read()`, `register_reader`, `read_recording()` y `load_all_readers()` ya
estaban implementados antes del hito 4 y a propósito: sostienen el punto de
extensión y **no deben convertirse en stubs**.

Sus dos tests, `test_readers.py` y `test_scoring_reader.py`, cierran el hito y
están corriendo. `scoring_formats.py`, del hito 23, tiene el suyo:
`test_scoring_formats.py`.

`available_readers()` devuelve **clases**, no instancias, igual que
`tools.registry.available_tools()`. Los dos son los puntos de extensión del
proyecto y se consumen de la misma forma.

**EDF ya tiene registro de prueba**: la Sleep-EDF Expanded de PhysioNet, abierta
y con hipnogramas en Rechtschaffen y Kales. Va en `data/`, que el `.gitignore`
excluye. El enlace y la licencia están en el
[hito 0](../../docs/TODO.md#hito-0-desbloquear).

**BrainVision** usa los archivos de prueba de MNE-Python (BSD-3): una tripleta
`.vhdr` + `.vmrk` + `.eeg` de 32 canales con nombres 10-20. Son **7,9 segundos,
no una noche**: alcanzan para verificar que el lector entiende el formato, no
para probar el programa de punta a punta. Un registro real del laboratorio
sigue siendo deseable.
