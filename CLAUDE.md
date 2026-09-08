# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Este archivo está en español, como el resto de la documentación del proyecto
(ver "Convenciones" más abajo).

---

## Estado del proyecto

**Parte 1 terminada**, con los hitos 0 a 7 cerrados: `python main.py` abre la
ventana, lee un EDF o un BrainVision, se navega y se scorea con el teclado, las
seis herramientas andan y los tres archivos de salida se escriben. Queda el
hito 8, que es una lista de comprobación, y el hito 9, que salió de correrla:
seis requisitos que estaban hechos en `tools/` y que `ui/` no consumía. Los dos
están cerrados y **la Parte 1 está terminada**.

**La Parte 2 también está terminada**, con los hitos 10 a 16: `psglab/analysis/`
no eleva `NotImplementedError` en ningún módulo. Tiene dependencias propias que
el CI instala sólo en algunos jobs; ver "Comandos".

**Las cuentas del avance viven sólo en [`docs/TODO.md`](docs/TODO.md)** —cuántos
stubs quedan, en cuántos módulos, qué hito está abierto— y
`tests/test_consistencia.py` las verifica contra el código en cada corrida. No
repetirlas acá: a este archivo no lo verifica nadie y se desincroniza.

Hoy no queda ningún test salteado, pero la convención sigue en pie para la
Parte 2: los tests de un módulo sin implementar se apagan con
`pytestmark = pytest.mark.skip(...)` cerca del principio del archivo, y **al
implementar el componente hay que borrar esa línea**, o el trabajo queda sin
verificar. El chequeo `test_ningun_modulo_terminado_tiene_su_test_salteado`
hace fallar la suite si alguien se olvida.

**Los módulos de `core/` y `utils/` son el modelo de qué se espera de un módulo
terminado.** Mirá `windows.py` para ver cómo se documenta lo que un módulo
**no** valida, y `recording.py` para el criterio opuesto: rechazar al construir
lo que no se puede arreglar después.

Nada de la Parte 1 **debe volver a ser `NotImplementedError`**, y en particular
tampoco los decoradores
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

Las dos auditorías tampoco: [`docs/AUDITORIA.md`](docs/AUDITORIA.md) (4 de
septiembre) y
[`docs/AUDITORIA-2026-09-07.md`](docs/AUDITORIA-2026-09-07.md) (7 de
septiembre, al cerrarse la Parte 1) son fotos fechadas de lo que se encontró
revisando el repositorio entero. Antes de abrir un hito conviene
leer sus bloques "Medido en la auditoría", que están citados dentro del TODO en
el hito al que le tocan. No son bugs abiertos sino decisiones que ese hito tiene
que tomar: firmas que no pueden ser correctas en `statistics.py`, `Session` sin
mecanismo de notificación, `BandOverlay` sin canal al que referir sus 75 µV.

## Comandos

Preparar el entorno, si todavía no está (el detalle está en `README.md`):

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

Hay un tercer archivo, `requirements-analysis.txt`, con las dos dependencias
exclusivas de la Parte 2 (`mne-connectivity` y `antropy`), que arrastran numba,
llvmlite, xarray, pandas y scikit-learn. **Hay que instalarlo**: desde el hito
10 hay tests que las importan, así que sin él `test_complexity.py`,
`test_connectivity.py` y parte de `test_entrega.py` fallan.

```bash
pip install -r requirements-analysis.txt
```

Los imports son diferidos a nivel de función, así que la recolección pasa y el
fallo sale recién al correr el test, con un `ModuleNotFoundError` que no dice
que falta un requirements. El CI las instala en los dos jobs.

En macOS y Linux la activación es `source .venv/bin/activate`, y en Debian,
Ubuntu y WSL el intérprete se llama `python3`. **Windows y WSL no pueden
compartir un mismo `.venv`**: el segundo pisa el `pyvenv.cfg` del primero y lo
deja inservible sin avisar en el momento. El README explica el síntoma y cómo se
repara sin reinstalar los paquetes.

Desde PowerShell se activa el entorno con ese script. **Desde la herramienta
Bash el script de activación no aplica**: conviene llamar al intérprete directo,
`./.venv/Scripts/python.exe -m pytest`.

Esa forma tiene dos ventajas más, que valen también en PowerShell: esquiva la
Execution Policy —que de fábrica bloquea `Activate.ps1`— y no puede instalar en
el Python equivocado si la activación falló sin que nadie lo notara. El README
explica por qué eso último es más caro que el error visible.

**Usar siempre `python -m pytest`, nunca `pytest` a secas.** No hay
`pyproject.toml` ni instalación editable, así que `psglab` sólo es importable
porque `python -m` agrega el directorio actual a `sys.path`; `pytest` directo
falla con `ModuleNotFoundError: No module named 'psglab'` en los archivos que lo
importan al cargarse, que hoy son casi todos. La cuenta exacta la lleva
`tests/README.md`, que sí tiene un chequeo que la verifica.
Agregar un `pyproject.toml` lo resolvería, pero es una decisión de empaquetado
que nadie tomó todavía.

Hay una segunda razón, independiente del `sys.path`: `python -m` no pasa por los
lanzadores de `Scripts/`, que quedan rotos si alguien renombra o mueve la carpeta
del proyecto. El README explica el síntoma y cómo se repara.

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
python -m piplicenses --format=markdown --order=license
```

Por módulo y no por el comando `pip-licenses`, igual que hace el CI: los
lanzadores de `Scripts/` llevan grabada la ruta absoluta del intérprete, así que
dependen de que ese directorio esté en el PATH y de que el entorno no se haya
movido.

## Lo que se verifica solo

`tests/test_consistencia.py` no testea el programa sino **el repositorio**, y
corre con `python -m pytest` como cualquier otro test. Conviene saber qué va a
rechazar antes de dar por terminado un cambio:

- Las **cuatro** cuentas de stubs de `docs/TODO.md` —el resumen del principio,
  los ítems `· N stubs` de cada módulo, las filas de la tabla de progreso y la
  fila de totales— tienen que coincidir con el código. **Implementar un stub
  obliga a actualizar el TODO en el mismo commit.**
- Todo módulo de `psglab/` lleva `Cubre del pliego:` en su docstring, y sus IDs
  coinciden con `docs/TRAZABILIDAD.md` **en las dos direcciones**. Los módulos de
  infraestructura también la llevan, declarando que no cubren ningún ID.
- Ningún enlace ni ancla de ningún `.md` versionado apunta a la nada, **este
  archivo incluido**. Renombrar un encabezado rompe los enlaces que lo apuntaban.
- `docs/EXPLICACION.txt` se mantiene en ASCII, sin acentos.
- **Cuatro** capas no importan `psglab.ui`, `PySide6` ni `pyqtgraph`: `core/`,
  `utils/`, `readers/` y `exporters/` (`CAPAS_SIN_INTERFAZ`, en el test). Las dos
  últimas están en la lista porque de ellas depende el corte del hito 5 —leer un
  registro, scorearlo y exportar los tres archivos desde un script, sin abrir una
  ventana—, que es exactamente lo que se pierde si entra Qt.
- Todas las firmas llevan type hints.
- Ningún módulo terminado tiene su test salteado.
- Cada archivo de `tests/` tiene su fila en el diccionario `COBERTURA_DE_TESTS`
  del propio test, que dice qué módulos cubre. **Agregar un archivo de test
  obliga a agregar esa fila**; si no, quedaría fuera del chequeo anterior.
- Cada `README.md` de carpeta declara sus pendientes con la frase literal
  `Pendientes **N stubs**`, que es obligatoria; el `en M módulos` es opcional y
  se verifica **sólo si está** —hoy lo omiten `core/`, `utils/` y `analysis/`—.
  En
  el hito 1 hubo cuatro commits seguidos que corrigieron el de stubs y ninguno
  el de módulos, que quedó en 29 cuando ya eran 26.
- `tests/README.md` también: su tabla tiene que nombrar todos los archivos de
  test y ninguno que ya no exista, decir cuáles llevan `pytestmark` y en cuántos
  archivos falla la recolección con `pytest` a secas.
- Las cuentas de tests de `docs/TODO.md` —`**N tests en verde**`— se comparan
  contra lo que pytest recolecta de verdad, no contra los `def test_` del
  archivo: hay `parametrize` y los números no coinciden.
- Un módulo que importe `config` no puede escribir a mano los números del pliego
  en el texto que ve el usuario: "30 s", "3 segundos", "0,5 segundos" y "75 µV"
  salen de la constante. Los docstrings quedan afuera, porque ahí nombrar el
  número es a propósito.
- Ningún `.md` versionado repite un párrafo largo dentro de sí mismo, **este
  archivo incluido**. Explicar lo mismo dos veces en un archivo garantiza que
  alguien corrija una sola.
- Todo módulo de la Parte 1 tiene test, figura en `SIN_TEST_PROPIO` —`ui/`
  entero, `app.py` y `config.py`— o el TODO promete el suyo **por nombre de
  archivo**. Un módulo nuevo sin ninguna de las tres cosas hace fallar la suite.
- Todo método público de `core/` y `utils/` que reciba argumentos tiene su fila
  en `CONTRATOS` de `tests/test_contratos.py`, o figura en `SIN_CONTRATO` con el
  motivo. Es lo que obliga a verificar que una entrada hostil salga como
  `PsgLabError` y no como una traza en la cara del investigador.
- `COBERTURA_DE_TESTS` no puede declarar un módulo que el test no importe.
  Declararlo sin importarlo ya contó nueve stubs como verificados mientras nadie
  exigía un test para ellos.
- Todos los módulos del paquete se pueden importar. Es lo único que ejercita la
  capa `ui/`.

### El otro test transversal

`tests/test_contratos.py` tampoco cubre un módulo: verifica una promesa que
cruza todos los implementados. La ventana principal atrapa **una sola** clase,
`PsgLabError`, así que un `AttributeError` o un `KeyError` crudo la atraviesa y
el investigador termina viendo una traza de Python. Una auditoría encontró seis
caminos así, y todos tenían la misma forma: la guarda funcionaba y el `raise`
era el que explotaba al armar el mensaje.

Son dos tablas porque una sola dejaba un hueco. `CONTRATOS` afirma que lo que se
rechaza sale como `PsgLabError` —no exige rechazar todo: un 3,5 de escala es un
número válido—, y `RECHAZOS_OBLIGATORIOS` fija las guardas que **no pueden**
aceptar. La segunda salió de generar mutantes del árbol de sintaxis: cuatro
guardas de tipo se podían borrar enteras, cambiando `if not isinstance(...)` por
`if False`, sin que la suite lo notara.

**Al implementar un módulo hay que agregar una fila por método público**, y hay
red que lo exige: `test_cada_metodo_publico_de_negocio_tiene_su_fila_de_contrato`
recorre `core/` y `utils/` y hace fallar la suite si falta alguna. Las
excepciones se declaran en `SIN_CONTRATO` **con el motivo** —hoy `windows.py` y
`clamp`, que documentan que no validan porque quien llama ya validó—, nunca se
saltean en silencio.

El [workflow de CI](.github/workflows/ci.yml) corre en cada push y cada pull
request contra `Add` y `Master`: los tests en Windows, macOS y Linux con Python
3.11 y 3.14 —la única prueba real de que el programa es multiplataforma—, esos
chequeos de consistencia, y la verificación de licencias, que falla si entra una
dependencia GPL. Contempla que PySide6 declara una licencia disyuntiva
(`LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`), así que un chequeo ingenuo de
"GPL" fallaría contra la dependencia principal del proyecto.

**Sólo dispara en `Add` y `Master`.** Un push a una rama de trabajo no corre
nada hasta que se abra la pull request, así que en el día a día el único control
es `python -m pytest` local, y conviene correrlo entero: el chequeo de las
cuentas de tests se saltea si se le pasa un archivo suelto.

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
