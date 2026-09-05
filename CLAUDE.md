# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Este archivo está en español, como el resto de la documentación del proyecto
(ver "Convenciones" más abajo).

---

## Estado del proyecto

**Esqueleto con los cimientos puestos**, con los hitos 0 y 1 cerrados: `core/`
ya tiene el vocabulario de fases, el modelo del registro y las conversiones de
tiempo, y `utils/` está terminada entera. El resto de la lógica no está escrita.
`python main.py` termina en `NotImplementedError` dentro de `psglab/app.py`: es
el comportamiento esperado, no un bug.

**Las cuentas del avance viven sólo en [`docs/TODO.md`](docs/TODO.md)** —cuántos
stubs quedan, en cuántos módulos, qué hito está abierto— y
`tests/test_consistencia.py` las verifica contra el código en cada corrida. No
repetirlas acá: a este archivo no lo verifica nadie y se desincroniza.

Los tests de los módulos que todavía no están implementados están apagados con
`pytestmark = pytest.mark.skip(...)` cerca del principio del archivo. **Al
implementar un componente hay que borrar esa línea del test correspondiente**, o
el trabajo queda sin verificar; el chequeo
`test_ningun_modulo_terminado_tiene_su_test_salteado` hace fallar la suite si
alguien se olvida.

**Los cinco módulos del hito 1 sirven de modelo de qué se espera de un módulo
cerrado**: `core/windows.py`, `core/nomenclature.py`, `core/recording.py`,
`utils/units.py` y `utils/errors.py`, cada uno con su test corriendo. Mirá
`windows.py` para ver cómo se documenta lo que un módulo **no** valida, y
`recording.py` para el criterio opuesto: rechazar al construir lo que no se
puede arreglar después.

Algunas piezas están implementadas a propósito y **no deben convertirse en
`NotImplementedError`**: los cinco módulos de arriba, los decoradores
`@register_tool` y `@register_reader`, `Reader.can_read`, el despacho de
`read_recording()` con `load_all_readers()`, los métodos de evento de `Tool` y
`ViewerTool`, y `psglab/config.py` entero. Las últimas son infraestructura que
corre en tiempo de importación; si fallaran, ningún módulo del paquete podría
cargarse y los mecanismos enchufables no existirían.

## Por dónde seguir

**[`docs/TODO.md`](docs/TODO.md) es la cola de trabajo** y el único documento
que lleva estado. Ordena los stubs pendientes de la Parte 1 en hitos **por
dependencias reales**, no por sección del pliego.

**No empieces un módulo si su hito anterior no está cerrado**: vas a escribir
contra firmas que todavía elevan `NotImplementedError` y no vas a poder testear
nada. Un módulo está terminado cuando además tiene su test corriendo (borrando
el `pytestmark` si el archivo ya existía), su fila de `docs/TRAZABILIDAD.md`
sigue siendo cierta y el README de su carpeta también.

`docs/TRAZABILIDAD.md` **no lleva estado**: dice dónde va cada requisito, no
qué falta. Duplicar el avance en los dos lugares garantiza que se
desincronicen.

## Comandos

Preparar el entorno, si todavía no está (el detalle está en `README.md`):

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

Hay un tercer archivo, `requirements-analysis.txt`, con las dos dependencias
exclusivas de la Parte 2 (`mne-connectivity` y `antropy`). **No instalarlo salvo
para trabajar en `psglab/analysis/`**: arrastran numba, llvmlite, xarray, pandas
y scikit-learn, y ningún test las importa. El CI las instala sólo en el job de
licencias.

Desde PowerShell se activa el entorno con ese script. **Desde la herramienta
Bash el script de activación no aplica**: conviene llamar al intérprete directo,
`./.venv/Scripts/python.exe -m pytest`.

**Usar siempre `python -m pytest`, nunca `pytest` a secas.** No hay
`pyproject.toml` ni instalación editable, así que `psglab` sólo es importable
porque `python -m` agrega el directorio actual a `sys.path`; `pytest` directo
falla con `ModuleNotFoundError: No module named 'psglab'` en los ocho archivos
que lo importan al cargarse.
Agregar un `pyproject.toml` lo resolvería, pero es una decisión de empaquetado
que nadie tomó todavía.

```bash
python main.py
python -m pytest
python -m pytest tests/test_scoring.py
python -m pytest tests/test_scoring.py::test_el_arousal_es_independiente_de_la_fase
python -m pytest -rs
```

En la consola de Windows los acentos de los mensajes salen como mojibake
(`configuraci�n`) por la codepage cp1252. Es cosmético y no un bug del código:
todo el texto que ve el usuario está en español y los archivos son UTF-8.
`$env:PYTHONUTF8=1` lo corrige para esa corrida.

Verificación de licencias a mano. El CI ya la corre en cada push, así que
esto sirve para mirar el detalle, no para no olvidarse:

```bash
pip-licenses --format=markdown --order=license
```

## Lo que se verifica solo

`tests/test_consistencia.py` no testea el programa sino **el repositorio**, y
corre con `python -m pytest` como cualquier otro test. Conviene saber qué va a
rechazar antes de dar por terminado un cambio:

- Las **tres** cuentas de stubs de `docs/TODO.md` —el resumen del principio, las
  filas de la tabla de progreso y la fila de totales— tienen que coincidir con
  el código. **Implementar un stub obliga a actualizar el TODO en el mismo
  commit.**
- Todo módulo de `psglab/` lleva `Cubre del pliego:` en su docstring, y sus IDs
  coinciden con `docs/TRAZABILIDAD.md` **en las dos direcciones**. Los módulos de
  infraestructura también la llevan, declarando que no cubren ningún ID.
- Ningún enlace ni ancla de ningún `.md` versionado apunta a la nada, **este
  archivo incluido**. Renombrar un encabezado rompe los enlaces que lo apuntaban.
- `docs/EXPLICACION.txt` se mantiene en ASCII, sin acentos.
- `core/` y `utils/` no importan `psglab.ui`, `PySide6` ni `pyqtgraph`.
- Todas las firmas llevan type hints.
- Ningún módulo terminado tiene su test salteado.
- Cada archivo de `tests/` tiene su fila en el diccionario `COBERTURA_DE_TESTS`
  del propio test, que dice qué módulos cubre. **Agregar un archivo de test
  obliga a agregar esa fila**; si no, quedaría fuera del chequeo anterior.
- Todos los módulos del paquete se pueden importar. Es lo único que ejercita la
  capa `ui/`.

El [workflow de CI](.github/workflows/ci.yml) corre en cada push y cada pull
request contra `Add` y `Master`: los tests en Windows, macOS y Linux con Python
3.11 y 3.14 —la única prueba real de que el programa es multiplataforma—, esos
chequeos de consistencia, y la verificación de licencias, que falla si entra una
dependencia GPL. Contempla que PySide6 declara una licencia disyuntiva
(`LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`), así que un chequeo ingenuo de
"GPL" fallaría contra la dependencia principal del proyecto.

## Arquitectura

**Cada carpeta tiene su propio `README.md`** con el mapa de sus archivos, las
reglas que la gobiernan y cómo extenderla. Leé el de la carpeta que vas a tocar
antes de escribir código en ella:
[`psglab/`](psglab/README.md) ·
[`core/`](psglab/core/README.md) ·
[`readers/`](psglab/readers/README.md) ·
[`ui/`](psglab/ui/README.md) ·
[`tools/`](psglab/tools/README.md) ·
[`exporters/`](psglab/exporters/README.md) ·
[`analysis/`](psglab/analysis/README.md) ·
[`utils/`](psglab/utils/README.md) ·
[`tests/`](tests/README.md) ·
[`docs/`](docs/README.md)

Al agregar un módulo o cambiar una regla de una carpeta, **actualizar el README
de esa carpeta en el mismo commit**, igual que `docs/TRAZABILIDAD.md`.

Las dependencias apuntan en una sola dirección:

```
utils ← core ← { readers, tools, exporters, analysis }
              ui ← core + tools
```

**`core/` nunca importa nada de `ui/`.** No es estética: es lo que permite
testear modelo, scoring, estadísticas y exportadores sin levantar una ventana.
Regla de bolsillo: si una regla de negocio quedó en `ui/`, está en el lugar
equivocado. Mostrar la ventana 0 como "Ventana 1" es presentación y va en
`ui/`; impedir que se scoree la ventana 500 de un registro de 400 es regla y va
en `core/`.

`psglab/core/session.py` (`Session`) es el estado central: qué registro está
abierto, su scoring y anotaciones, en qué ventana está parado el usuario, qué
canales ve y con qué amplitud. La interfaz lo consulta para dibujarse y lo
modifica ante cada acción.

**Dos puntos de extensión.** Agregar funcionalidad no debe obligar a tocar
`main.py`, la ventana principal ni ningún archivo existente:

- **Herramienta** — crear el archivo en `psglab/tools/`, heredar de
  `ViewerTool` (actúa con el mouse sobre la señal; coordenadas en segundos
  desde el inicio de la ventana y en µV) o de `Tool` (panel con su propio
  sistema de coordenadas, como el histograma), y decorar con `@register_tool`.
  La barra se arma recorriendo el registro. Los dos contratos existen porque
  las coordenadas no son las mismas; ver `psglab/tools/base.py`.
- **Formato de archivo** — crear el archivo en `psglab/readers/`, heredar de
  `Reader` y decorar con `@register_reader`. El formato aparece solo en el
  diálogo de apertura. El resto del programa sólo llama a `read_recording()` y
  nunca sabe de qué formato vino la señal.

`psglab/config.py` es el punto único de verdad de las constantes del pliego
(ventana de 30 s, grilla de 0,5 s y 3 s, banda de 75 µV, nombres de los tres
archivos de salida). No repetir esos números en ningún otro módulo.

`psglab/core/windows.py` es el único lugar donde se convierte entre ventanas,
muestras y hora de la noche, para que no aparezcan cuentas de `* 30 * fs`
repartidas por el código. Los índices de ventana son **base 0 internamente** y
base 1 al mostrarlos y exportarlos; la conversión se hace al mostrar.

## Convenciones

- Identificadores y nombres de archivo en **inglés**; comentarios, docstrings,
  documentación y todo texto que ve el usuario, en **español**.
- Cada módulo abre con un docstring que dice de qué se ocupa y **qué IDs del
  pliego cubre**. Esa línea es la que alimenta `docs/TRAZABILIDAD.md`.
- Type hints en todas las firmas.
- Los errores que ve el usuario heredan de `PsgLabError`
  (`psglab/utils/errors.py`): mensaje en español dirigido a un investigador, no
  a un programador, y la causa técnica aparte en `details`.
- **Todo el programa trabaja en microvoltios.** La conversión se hace una sola
  vez al importar, en `psglab/utils/units.py`; ninguna otra capa vuelve a
  preguntarse por la unidad.
- Al agregar una funcionalidad: **su fila en `docs/TRAZABILIDAD.md` en el mismo
  commit**, y su test en `tests/`.

## Restricciones duras

- **Nunca agregar PyQt5 ni PyQt6.** Son GPL y obligarían a relicenciar el
  proyecto entero, que el pliego pide MIT. PySide6 (LGPL) se eligió
  exactamente por eso.
- **Nunca commitear registros de participantes.** El `.gitignore` ya excluye
  `data/`, `registros/`, `*.edf`, `*.vhdr`, `*.vmrk`, `*.eeg` y los tres
  archivos de salida. En `data/` hay registros de prueba locales (un EDF y un
  BrainVision) que sirven para probar la importación a mano; **ningún test debe
  leerlos**, por la regla de abajo.
- Los tests usan **señal sintética generada en el momento** (fixtures en
  `tests/conftest.py`), nunca registros reales. Además de la privacidad, un
  registro sintético tiene resultado conocido de antemano: una onda de 10 Hz
  debe dar un pico de PSD en 10 Hz, y eso se puede afirmar en un test.
- Los pull requests van a la branch **`Add`, nunca a `Master`**, y vienen
  comentados explicando qué cambió y por qué. `Master` es el trunk y la rama por
  defecto del repositorio. **No existe una rama `main`**: el repo nació con una,
  sin relación con esta historia (era el commit stub de GitHub, con otro
  `LICENSE`), y se retiró. Si alguna herramienta la da por sentada, está
  equivocada.
- `main.py` se mantiene mínimo: la lógica nueva va al módulo que corresponde.

## Decisiones ya cerradas — no re-litigar

- **REM es fase de primera clase** en las dos nomenclaturas (REM en
  Rechtschaffen y Kales, R en AASM), aunque el listado del pliego no la
  mencione. Confirmado con el cliente.
- **La unidad es µV**, aunque el pliego escriba "mV".
- `Tool` y `ViewerTool` **no heredan de `QObject`**: avisan por callbacks para
  poder testearse sin GUI. Sus métodos de evento no hacen nada por defecto en
  vez de elevar `NotImplementedError`, porque si el método base fallara,
  activar una herramienta y navegar rompería el programa.
- **pyqtgraph y no matplotlib** para las ondas: hay que redibujar decenas de
  canales por cada pulsación de flecha.

Los motivos completos están en `docs/ARQUITECTURA.md`. Si alguna decisión se
revisa, actualizar ese archivo con el motivo del cambio.

## Ambigüedades del pliego

**Se cerraron el 4 de septiembre de 2026**, en el hito 0. La lista de qué se
preguntó y en qué constante vive cada respuesta está en `docs/TODO.md`, hito 0.
Queda una sola abierta y es de la Parte 2: de dónde salen las impedancias
(`psglab/analysis/impedance.py`, marcada `PENDIENTE DE DEFINICIÓN CON EL
CLIENTE`).

Que estén cerradas **no las hardcodea**. Las respuestas viven en
`psglab/config.py` —`SCORING_INCLUDES_WINDOW_NUMBER`,
`ANNOTATION_SAMPLE_BASE`, `OCCUPANCY_COUNTS_OVERLAP_ONCE`,
`SCORING_INCLUDES_NOMENCLATURE_HEADER`— y **revertir cualquiera tiene que
seguir siendo cambiar una línea**. Un `if` que dé por sentada una de las
variantes rompe esa propiedad aunque hoy acierte.
