# Auditoría del repositorio — 4 de septiembre de 2026

**Este informe no lleva estado.** Es la foto de lo que se encontró ese día,
recorriendo los 51 archivos `.py`, los 15 documentos y la configuración del
repositorio. Qué falta hacer y en qué orden vive en [`TODO.md`](TODO.md), que es
el único documento del proyecto que lleva la cuenta. Duplicarla acá reproduciría
exactamente el problema que este informe describe.

Las referencias van como `ruta:línea` en código, no como enlaces: los números de
línea envejecen con el primer commit que toca el archivo, y un enlace roto haría
fallar el chequeo de enlaces de `tests/test_consistencia.py`.

## Por qué se hizo

El 4 de septiembre de 2026 se cerró el hito 0: ocho decisiones que el pliego
dejaba abiertas y que se confirmaron con el cliente. La noticia llegó a
`psglab/config.py`, a [`TODO.md`](TODO.md) y a
[`EXPLICACION.txt`](EXPLICACION.txt), pero **no a los siete README de carpeta**,
que siguen pidiendo confirmar lo que ya está confirmado.

Eso no debería haber podido pasar: `tests/test_consistencia.py` existe justamente
para atrapar esa deriva, y corre en cada push. La auditoría encontró que tiene
siete huecos por los que la deriva pasa sin despeinarse, y uno de ellos está
tapando una divergencia real desde el día en que se escribió.

## El estado real, medido

| Magnitud | Valor |
|---|---|
| Stubs (`raise NotImplementedError`) | 196 — 170 de la Parte 1 en 29 módulos, 26 en `analysis/` |
| Archivos `.py` en `psglab/` | 50 — 42 módulos más 8 `__init__.py` |
| Módulos de la Parte 1 terminados | 1 — `psglab/core/windows.py` |
| Tests recolectados | 69 (59 funciones `def test_`; la diferencia es un `parametrize`) |
| Resultado de la suite | 34 pasan, 35 se saltean, 0 fallan |
| Archivos de test | 6, de los cuales 4 llevan `pytestmark` |

Lo que está bien y conviene decir explícitamente, porque es lo que hace que el
resto sea barato de arreglar: **cero violaciones de la regla de dependencias**
(ningún import invertido, ningún ciclo, y `core/` y `utils/` no conocen Qt),
**cero enlaces rotos**, **cero identificadores sin type hints**, **cero
registros de participantes versionados**, y los recuentos de stubs de los siete
README de carpeta son exactos uno por uno.

---

## 1. Documentación que quedó atrás del hito 0

Es la familia más numerosa y la más engañosa: son documentos que le piden al
lector confirmar con el cliente algo que el cliente ya confirmó.

**1.1** · `docs/README.md:50-64` lista seis ambigüedades abiertas y encabeza con
*"hay que confirmar con el cliente antes de programarlos"*. **Cinco de las seis
están cerradas** en `TODO.md:86-95` y `EXPLICACION.txt:179-193`: los campos de
`Scoring.txt`, la base de la primera muestra, el conteo de la ocupación
superpuesta, el titular del copyright y el material de prueba. Sigue abierta
sólo la 3, las impedancias. **Correcto: `EXPLICACION.txt` sección 8.**

**1.2** · `psglab/core/README.md:73-77` titula *"Ambigüedad abierta"* y dice que
falta definir si la primera muestra es la 0 o la 1. `psglab/config.py:99-105` ya
dice `ANNOTATION_SAMPLE_BASE = 0`, con el comentario *"Confirmado con el cliente
el 4 de septiembre de 2026"*. **Correcto: el código.**

**1.3** · `psglab/exporters/README.md:40-44` dice *"Ambigüedad abierta … Mientras
no se confirme"* sobre los campos de `Scoring.txt`. `psglab/exporters/scoring_txt.py:11-12`
ya dice *"vale el ejemplo: confirmado con el cliente"*. **Correcto: el código.**

**1.4** · `psglab/exporters/README.md:63-65` repite como abiertas dos preguntas:
la base de la muestra (cerrada, ver 1.2) y si conviene escribir la frecuencia de
muestreo en una cabecera. La segunda también se decidió: `TODO.md:103-108` dice
*"Se aceptó porque falla distinto"*. **Correcto: las dos están cerradas.**

**1.5** · `psglab/exporters/README.md:99-101` declara `annotations_txt.py`
**bloqueado** por el hito 0. `TODO.md:225-226`, `:283` y `:298-299` dicen lo mismo
para `annotations_txt.py`, `occupancy.py` y `annotator.py`. Con el hito 0 cerrado,
**ninguno de los tres está bloqueado**.

**1.6** · `psglab/tools/README.md:101-105` titula *"Ambigüedad abierta —
Ocupación"* sobre si la zona compartida se cuenta una o dos veces.
`psglab/config.py:107-114` dice `OCCUPANCY_COUNTS_OVERLAP_ONCE = False` y
`psglab/tools/occupancy.py:128-132` dice *"Confirmado con el cliente"*.
**Correcto: se cuenta dos veces.**

**1.7** · `psglab/readers/README.md:98-100` dice que **falta** un registro de
prueba en BrainVision y en EDF, y remite a `EXPLICACION.txt` sección 8 — donde el
tema ya no figura. El mismo archivo, treinta líneas más abajo (`:112-121`),
explica que **los dos ya están**: Sleep-EDF Expanded para EDF y los archivos de
prueba de MNE-Python para BrainVision. **El archivo se contradice consigo mismo.**

**1.8** · `CLAUDE.md:244-250` dice que el formato de `Scoring.txt` es *"la única
[ambigüedad] que ya afecta al código"* y ordena no hardcodear ninguna variante
*"hasta que el cliente confirme"*. Ya confirmó. La orden de no hardcodear sigue
valiendo, pero por otro motivo (`TODO.md:220-222`: la variante tiene que seguir
siendo alcanzable cambiando una constante), no por falta de confirmación.

**1.9** · La marca `PENDIENTE DE CONFIRMACIÓN` que citan textualmente
`docs/TRAZABILIDAD.md:193`, `docs/README.md:64` y `TODO.md:321` **no existe en
ningún archivo del proyecto**. La marca real es `PENDIENTE DE DEFINICIÓN CON EL
CLIENTE`, y está una sola vez, en `psglab/analysis/impedance.py:7`. El comando
que propone `docs/TRAZABILIDAD.md:196` funciona de casualidad porque busca el
prefijo `PENDIENTE DE`; buscar la frase que los tres documentos prometen no
devuelve nada. **Correcto: el código.**

---

## 2. Cuentas que no cuadran

**2.1** · `docs/EXPLICACION.txt:48` dice *"Quedan 168 funciones"*. Son **170**
(`TODO.md:7` y `psglab/README.md:103` ya dicen 170). Es el único documento con
cuentas que el chequeo automático no mira, porque lee `TODO.md`.

**2.2** · `docs/TODO.md:53` marca el hito 0 con `⬜` mientras `TODO.md:80` dice
*"Cerrado el 4 de septiembre de 2026"*. El chequeo verifica las columnas de
módulos y de stubs, no la de estado.

**2.3** · `docs/TODO.md:54-61`: la columna **Módulos** de la tabla de progreso
suma 30 (4+2+1+5+4+8+6) y la fila de totales dice **29**. Las dos son correctas
según su propia definición y el documento no explicita cuál usa: el hito 1 cuenta
`core/windows.py` entre sus cuatro módulos, y el total cuenta sólo módulos que
todavía tienen stubs. **La columna no suma su propio total.**

**2.4** · `docs/TODO.md:146` dice que `tests/test_windows.py` tiene *"15 tests en
verde"*. Tiene **17**.

**2.5** · `psglab/README.md:82` dice *"los 49 módulos importan"*. Ninguna lectura
da 49: hay **50** archivos `.py` en `psglab/`, y la definición operativa de
"módulo" del proyecto —`modulos_del_paquete()` en `tests/test_consistencia.py:50`,
que excluye los `__init__.py`— da **42**.

**2.6** · `psglab/README.md:85-89` dice *"Cuatro piezas"* y enumera **cinco**.
Además la lista está incompleta: faltan los métodos de evento de `Tool` y
`ViewerTool`, `psglab/config.py` entero, `psglab/core/windows.py` entero y las
cuatro funciones de `tools/registry.py`.

**2.7** · `psglab/README.md` tiene **dos** secciones de estado con contenidos
distintos: `## Estado actual` (`:80-89`, con las cuentas de 2.5 y 2.6) y
`## Estado` (`:101-108`, con las cuentas correctas). Es la duplicación que el
proyecto declara querer evitar, dentro de un mismo archivo.

**2.8** · `tests/README.md:21` dice *"Los 42 tests están desactivados, con esta
línea al tope de cada archivo"* y `:27` dice *"La corrida informa `42 skipped`"*.
Las tres afirmaciones son falsas: son **35** los salteados sobre **69**
recolectados, la línea no está al tope sino después de los imports, y sólo la
llevan **4 de los 6** archivos. La propia tabla de `tests/README.md:38` lista
`test_consistencia.py` como test activo, contradiciendo el "cada archivo".

**2.9** · `tests/README.md:16` dice que la recolección falla en los *"cinco
archivos"*. Son **seis**.

**2.10** · `tests/README.md:120-121` manda **reactivar** `test_windows`. Ya está
reactivado desde que se implementó `core/windows.py`.

**2.11** · `docs/TRAZABILIDAD.md:139` dice *"Estos cinco se rompen hacia todos
lados"* y la tabla que sigue (`:141-149`) tiene **siete** filas. Peor: dos de esas
siete —`psglab/core/recording.py` y `psglab/utils/units.py`— **sí tienen fila
arriba** (`:28-30`, `:39`, `:36`, `:67`), con lo que la frase que introduce la
tabla, *"no tienen fila arriba"*, es falsa para ellas.

**2.12** · `docs/ARQUITECTURA.md:194` dice *"Tres resultados que conviene
explicar"* y enumera **dos** (`:196-201` y `:202-204`).

---

## 3. IDs del pliego y trazabilidad

El proyecto cruza automáticamente la línea `Cubre del pliego:` del docstring
contra `TRAZABILIDAD.md`, en las dos direcciones. Los README de carpeta **no**
entran en ese cruce, y por eso son los que divergieron.

**3.1** · `psglab/core/README.md:24` omite **V4_F del Histograma** para
`session.py`. El docstring (`psglab/core/session.py:11-13`), la tabla
(`docs/TRAZABILIDAD.md:86`) y `TODO.md:175-176` sí se lo asignan.

**3.2** · `psglab/ui/README.md:37` y `TODO.md:250-251` omiten **V1_F de
"Anotación de la señal"** para `signal_view.py`, que el docstring
(`psglab/ui/signal_view.py:18-20`) y `docs/TRAZABILIDAD.md:107` sí le asignan.

**3.3** · `psglab/readers/README.md:15` y `TODO.md:198` dicen que
`readers/base.py` es la base de **V1_F a V3_F**. El docstring
(`psglab/readers/base.py:18`) y la tabla dicen **V1_F y V2_F**. V3_F lo resuelve
`scoring_reader.py`, que no pasa por el despacho de `read_recording()`.
**Correcto: V1_F y V2_F.**

**3.4** · La Parte 2 tiene un hueco de numeración sin explicar:
`docs/TRAZABILIDAD.md:124-125` salta de *Filtración V1_F* a *Filtración **V5_F***,
sin V2_F, V3_F ni V4_F en ningún documento ni docstring. Y cuatro secciones
—Rereferenciar, Derivar, Complejidad, Conectividad— figuran con `—` en vez de ID.
Es el único hueco del repositorio y no hay nota que diga si el pliego numera así o
si faltan tres requisitos. **Requiere consultar el pliego.**

**3.5** · Los nombres de sección del pliego se escriben distinto entre la tabla y
los docstrings: *"Filtración"* contra *"Filtración de la señal"*
(`psglab/analysis/filters.py:11`), *"Impedancia"* contra *"Impedancia de los
electrodos"* (`impedance.py:15`), *"PSD"* contra *"Power Spectral Density (PSD)"*
(`psd.py:16`), *"Conectividad"* contra *"Conectividad de la señal"*
(`connectivity.py:19`). Importa porque `docs/TRAZABILIDAD.md:8-9` establece que
**el nombre de la sección es lo que desambigua los IDs repetidos**; si el nombre
varía, la convención se debilita. El chequeo compara IDs, no nombres.

---

## 4. Reglas enunciadas de dos maneras

**4.1** · **La sección del pliego que pide el testeo: ¿7 u 11?** Dicen **7**:
`TODO.md:42`, `tests/README.md:102`, `README.md:86-93` y
`docs/TRAZABILIDAD.md:153-166`, que titula *"Requisitos técnicos (sección 7 del
pliego)"* e incluye ahí "Testeos recurrentes por componente". Dicen **11**:
`docs/ARQUITECTURA.md:49`, `psglab/core/README.md:14`, `psglab/core/__init__.py:6`
y `psglab/README.md:23`, los cuatro con la misma frase copiada, lo que sugiere una
única fuente propagada. **Parece correcto 7, pero hay que confirmarlo contra el
pliego**, que no está en el repositorio.

**4.2** · **La regla de dependencias se dibuja mal en un lugar.**
`README.md:74-76`, `CLAUDE.md:151-153` y la prosa del propio
`docs/ARQUITECTURA.md:45-50` dicen `ui → core + tools`. El diagrama de
`docs/ARQUITECTURA.md:36-42` cuelga `ui` **únicamente de `tools`**, sin flecha
propia a `core`. El código le da la razón a la prosa: seis de los siete módulos de
`ui/` importan de `core/`. **Correcto: `ui → core + tools`.**

**4.3** · `psglab/tools/README.md:70-73` dice que las herramientas exclusivas son
**dos**, *"la lupa y el anotador"*. `psglab/tools/base.py:41-45` dice **tres**, y
suma el medidor de ocupación — que efectivamente deja `exclusive` en su valor por
defecto `True`. **Correcto: tres.**

**4.4** · `psglab/exporters/README.md:60-61` dice que guardar las anotaciones en
muestras *"no depende de la frecuencia de muestreo del archivo"*.
`psglab/exporters/annotations_txt.py:11-13` dice lo contrario y con razón: *"el
archivo no se puede interpretar sin la frecuencia de muestreo"*, que es la que
vive en `Informacion.txt`. **Correcto: el código.**

**4.5** · `psglab/analysis/README.md:36-44` dice que `mne` y `scipy` se instalan
con `requirements-dev.txt` y **no** con `requirements.txt`. Es al revés: los dos
están en `requirements.txt`. En el dev sólo están `mne-connectivity` y `antropy`.

**4.6** · `README.md:28` manda `cd "Lab Del Sueño"`. La carpeta real es
`Programa-Laboratorio-De-Sueno-y-Memoria-ITBA`. Además `docs/README.md:60` todavía
lista "nombre del repositorio" como pendiente, aunque el ítem del hito 0 que lo
contenía se cerró por su otra mitad, el titular del copyright.

**4.7** · `psglab/ui/README.md:104-108` y `:118-120` repiten el mismo párrafo casi
palabra por palabra dentro del mismo archivo.

**4.8** · `psglab/exporters/README.md:22` escribe el enlace `psglab/config.py`
apuntando a `../README.md`. El destino existe, así que el chequeo de enlaces no lo
ve, pero el enlace lleva a otro archivo del que anuncia.

---

## 5. Falsos verdes del chequeo de consistencia

`tests/test_consistencia.py` es la mejor idea del repositorio y la que más
sorprende auditar: casi todas las incongruencias de las secciones 1 a 4 conviven
hoy con una suite en verde. `TODO.md:29-31` afirma que *"no hace falta acordarse
de que las cuentas de este archivo cuadren, ni de que los enlaces no se rompan…
si algo de eso queda mal, el pull request falla"*. De los hallazgos de este
informe, el chequeo habría atrapado **sólo** los que tocan las tres cuentas de
stubs.

**5.1 · Dos defectos que se cancelan, y por eso ninguno se ve.**
`ids_declarados()` (`tests/test_consistencia.py:81-86`) extrae los IDs con
`re.findall(r"V\d+_[PF]")` sobre la **prosa** del docstring. Y
`psglab/config.py:14-17` dice literalmente *"Cubre del pliego: ningún ID propio.
Es infraestructura: sostiene los valores de V1_P y V2_F de 'Diseño de la
interfaz', V1_F de 'Herramienta de amplitud'…"*. El regex extrae tres IDs de una
frase que afirma no tener ninguno.

Eso debería hacer fallar `test_los_ids_coinciden_en_las_dos_direcciones`, y no lo
hace por un segundo defecto: la salida de emergencia de `:220-221`,

```python
if not (declara and asigna):
    continue
```

que exime a todo módulo con cualquiera de los dos lados vacío. Verificado
recorriendo los 42 módulos: **exime a 9**, de los cuales 8 son legítimos
(`declara = ∅` y `asigna = ∅`) y uno —`psglab/config.py`— es una divergencia
real. El test que existe porque *"el chequeo manual sólo miraba docstring → tabla,
y por eso informó en verde dos divergencias reales"* informa en verde ésta.
**Arreglar uno solo de los dos pone el CI en rojo.**

**5.2 · El mismo defecto en espejo, que hoy acierta de casualidad.**
`psglab/utils/units.py:19-22` también dice *"ningún ID propio"* y a continuación
nombra V1_P y V1_F — que la tabla **sí** le asigna. El regex acierta; la prosa
miente. No rompe nada, y va a romper el día que alguien corrija la prosa.

**5.3 · `test_core_y_utils_no_conocen_la_interfaz` no ve la forma de import más
común.** `tests/test_consistencia.py:293` sólo inspecciona `ast.ImportFrom`. Un
`import pyqtgraph as pg` o un `import PySide6` a secas —que es exactamente cómo lo
importan `psglab/ui/grid.py:16` y `psglab/ui/signal_view.py:25`— no dispara nada.
La regla que el propio test llama *"la que sostiene todo lo demás"* se puede violar
con la sintaxis más habitual. Además `:290` filtra por `parent.name in
("core","utils")`: un subpaquete de `core/` quedaría fuera, y `exporters/` y
`readers/` no están cubiertos, pese a que el corte del hito 5 —el programa
haciendo su trabajo entero sin interfaz— depende de que ellos tampoco conozcan Qt.

**5.4 · `test_todas_las_firmas_llevan_type_hints` sólo mira `nodo.args.args`**
(`:306`). Quedan afuera `posonlyargs`, `kwonlyargs`, `*args` y `**kwargs`: una
firma `def f(*, umbral, **opciones) -> None:` pasa con cero anotaciones. Como es
el único sustituto de un verificador de tipos en el proyecto, el hueco pesa.

**5.5 · `test_ningun_modulo_terminado_tiene_su_test_salteado` tiene dos escapes.**
`:335` detecta la desactivación con `if "pytestmark" not in texto`, que encuentra
la palabra hasta en un comentario y, al revés, no detecta
`pytest.skip(allow_module_level=True)` ni `@pytest.mark.skip` test por test. Y
`:338` usa `all(n == 0 …)`: para `test_exporters.py`, que cubre cuatro módulos,
basta con que **uno** conserve un stub para que sus siete tests sigan apagados
legítimamente. Es el agujero exacto que el test dice cerrar, abierto justo para el
archivo que cubre más módulos.

**5.6 · `contar_stubs` cuenta texto, no código** (`:62-65`). Un comentario que
mencione la frase infla el conteo y hace fallar el chequeo de cuentas por un
motivo que no es el real. Hoy se salva de raya: `psglab/tools/registry.py:17` dice
*"Si elevara NotImplementedError"* sin la palabra `raise`.

**5.7 · `test_cada_modulo_aparece_en_la_trazabilidad` hace grep plano** (`:196`),
sin exigir que la mención esté en una fila de tabla. Un módulo nombrado sólo en un
párrafo cuenta como trazado.

**5.8 · `test_todos_los_modulos_del_paquete_se_pueden_importar` se puede saltear
módulos en silencio.** `:370` usa `pkgutil.walk_packages` sin `onerror`, que
**suprime** el `ImportError` de un subpaquete para poder seguir enumerando. Si
`psglab/ui/__init__.py` fallara al importarse, sus submódulos dejan de emitirse,
la lista de fallos queda vacía y el test pasa. El único test que ejercita `ui/` y
la única prueba de que PySide6 funciona se pone verde justo en el escenario que
dice cubrir.

**5.9 · El chequeo de enlaces da resultados distintos según el sistema
operativo.** `:252-256` usa `Path.resolve()` y `exists()`. En Windows y macOS el
sistema de archivos no distingue mayúsculas, así que un enlace a `TODO.md`
escrito como `todo.md` existe y el test pasa; en `ubuntu-latest` no existe y
falla. Es divergencia que sólo aparece en el CI, sobre 15 archivos.

**5.10 · `archivos_markdown()` audita artefactos generados** (`:109-115`): sólo
excluye `.venv` y `.git`, así que hoy incluye `.pytest_cache/README.md`, que está
en `.gitignore:33` y lo escribe pytest. Pasa porque ese archivo sólo tiene enlaces
`https://`. El mismo hueco deja entrar `htmlcov/`, `build/`, `dist/` y un
entorno virtual llamado `venv/`.

**5.11 · Ningún chequeo audita las cuentas de tests**, sólo las de stubs. Es la
causa raíz directa de 2.4, 2.8, 2.9 y 2.10.

**5.12 · Las dos fixtures principales de `tests/conftest.py` no las usa nadie.**
`synthetic_signal` (`:22`) y `channel_names` (`:47`) están documentadas en
`tests/README.md:83-98` con una tabla de frecuencias por canal, y no las consume
ni un test. Todo ese contrato está sin verificar. No es un defecto —son el
material del hito 4— pero conviene que el documento lo diga.

---

## 6. Riesgos de la integración continua

`.github/workflows/ci.yml` hace lo correcto y hace falta. Lo que sigue es lo que
lo va a romper, o lo que hoy deja pasar.

**6.1 · `antropy → numba → llvmlite` es el eslabón que va a romper el build
solo.** `requirements.txt:9` dice `numpy>=1.24` **sin techo**, y `numba` fija
`numpy<2.6`. Cuando salga numpy 2.6, el resolvedor va a tener que retroceder en
las seis combinaciones del job de tests y en el de licencias. Es la causa número
uno de un CI rojo sin que nadie toque el código.

**6.2 · El CI instala tres dependencias pesadas que ningún test usa.** Verificado:
**ningún módulo de `psglab/` importa `mne`, `mne-connectivity` ni `antropy`**, y
ningún test las toca. `mne` arrastra `matplotlib`, `pooch`, `tqdm` y `jinja2`;
`mne-connectivity` arrastra `netCDF4`, `xarray`, `pandas` y `scikit-learn`. Se
pagan en siete jobs a cambio de cero verificación, y son las que materializan 6.1.

**6.3 · Las bibliotecas de Qt de Linux son un subconjunto apretado.**
`ci.yml:52-53` instala `libegl1`, `libgl1`, `libxkbcommon0`, `libdbus-1-3` y
`libglib2.0-0`, pero no `libfontconfig1` ni `libfreetype6`, de los que `libQt6Gui`
depende directamente. Hoy vienen preinstaladas en la imagen; con
`--no-install-recommends` no hay red de contención si cambia.

**6.4 · El script de licencias acepta lo desconocido.** `ci.yml:112` termina en
`return True`, así que un paquete con licencia `UNKNOWN`, vacía, o con el texto de
la GPL sin la sigla, pasa el control. Hoy no hay ninguno —verificado: 53 paquetes,
0 incompatibles, 0 desconocidos— pero el portón que el pliego exige antes de cada
release está abierto por defecto en vez de cerrado.

**6.5 · El job de licencias mira una sola resolución** (ubuntu + Python 3.14). Las
otras cinco combinaciones pueden resolver versiones, y por lo tanto licencias,
distintas.

**6.6 · `cache: pip` no indexa `requirements-dev.txt`.** `actions/setup-python`
sin `cache-dependency-path` usa `**/requirements.txt` para la clave, así que
cambiar el archivo donde viven pytest, pip-licenses, antropy y mne-connectivity
reutiliza un caché viejo.

**6.7 · Higiene del workflow.** Sin `concurrency` (un push con PR abierto dispara
las seis combinaciones dos veces), sin `timeout-minutes` (una resolución con
retroceso puede consumir el máximo de seis horas), sin bloque `permissions:`, y
sin `workflow_dispatch`.

**6.8 · Sin fijación de versiones ni lockfile.** Todo es `>=`. Una publicación
aguas arriba puede romper un pull request que no tocó nada, y es lo que convierte
6.1 en cuestión de cuándo y no de si.

**6.9 · `data/` es inalcanzable desde el CI.** El directorio entero está en
`.gitignore:6` —correcto, y verificado que no se filtró nada— pero eso significa
que el `tests/test_readers.py` que pide `TODO.md:203-204` no va a tener con qué
correr en GitHub Actions. Va a haber que saltearlo, reintroduciendo el verde por
omisión que el proyecto combate. No hay nota en el workflow que lo contemple.

**6.10 · Lo que el CI no cubre**, para que conste: no hay linter, formateador,
verificador de tipos ni medición de cobertura. `python -m pytest -v` informa verde
con 35 salteados y nada exige que ese número baje.

---

## 7. Defectos de contrato del código

Ninguno rompe nada hoy, porque casi todo es un stub. Todos van a romper algo
cuando se abra el hito correspondiente, y arreglarlos ahora cuesta una firma.

**7.1 · `read_recording()` no encuentra ningún lector, nunca.** Reproducido:

```
>>> read_recording(Path("data/test.vhdr"))
UnsupportedFormatError: No se puede abrir 'test.vhdr': el formato no está soportado.
details: Extensiones conocidas: ninguna
```

`psglab/readers/base.py:100-117` recorre `available_readers()`, que lee
`_REGISTRY`; `_REGISTRY` sólo se llena al importar `edf.py` o `brainvision.py`, y
`psglab/readers/__init__.py` **no importa ninguno**. No existe el
`load_all_readers()` análogo a `psglab/tools/registry.py:83`. Contradice a
`psglab/readers/README.md:54-55` (*"No hace falta acordarse de importar el módulo
nuevo"*), a `psglab/readers/base.py:12` (*"No hace falta modificar ningún archivo
existente"*) y a `psglab/app.py:33-36`, que promete registrar los lectores sin que
exista la función que lo haga. **Es el defecto más concreto del informe: de los
dos puntos de extensión del proyecto, uno no funciona.**

**7.2 · `core/windows.py` promete un error que dos de sus cuatro funciones no
elevan.** `psglab/core/windows.py:22-23` dice *"con frecuencia cero, elevan
`ZeroDivisionError`"*. Verificado: `sample_to_window` y `count_windows` lo hacen;
`window_to_samples(5, 0.0)` devuelve `(0, 0)` y `window_duration(5, 1000, 0.0)`
devuelve `timedelta(0)`, **en silencio**. En el módulo que `CLAUDE.md` presenta
como modelo de módulo terminado, una frecuencia corrupta leída de un EDF produce
una ventana vacía en vez del error prometido. `tests/test_windows.py:167` sólo
ejercita la mitad verdadera de la promesa.

**7.3 · Tres definiciones de "duración total" que no van a cerrar.**
`psglab/core/recording.py:92` da `n_samples / sampling_rate`;
`psglab/core/windows.py:115` da la duración real de la ventana, que en la última
puede ser menor a 30 s; `psglab/exporters/statistics.py:69` da `n_windows × 30`.
Como la última ventana se cuenta aunque esté incompleta, el tercero **sobreestima
hasta 29,99 s**. Los dos números que `Informacion.txt` promete imprimir no van a
coincidir entre sí.

**7.4 · Las herramientas no pueden cumplir su propio docstring.**
`psglab/tools/base.py:57` da `activate(self, session: Session)` como único punto
de entrada, y `Session` no expone nada gráfico — ni debe. Pero los seis módulos de
herramienta prometen *"crear y mostrar la banda"* (`amplitude_band.py:35`),
*"crear el círculo de zoom"* (`magnifier.py:29`), *"crear y mostrar el panel"*
(`overview.py:32`), *"crear el panel del histograma"* (`histogram.py:44`),
*"dibujar las bandas de la ventana"* (`annotator.py:75`) y *"actualizar la vista
previa de la línea"* (`occupancy.py:86`). No hay parámetro, atributo ni callback
que les dé acceso a nada dibujable.

**7.5 · Las coordenadas no llegan en la unidad que las herramientas necesitan.**
`psglab/tools/base.py:79-93` entrega **segundos**. `OccupancyLine`
(`psglab/tools/occupancy.py:36-45`) exige **fracciones 0–1** y su propio docstring
advierte que con segundos crudos informaría 3000 %.
`psglab/tools/annotator.py:52` necesita **muestras**. La conversión la haría
`SignalView`, pero como `on_mouse_press(x, y, button)` no lleva ningún canal por
donde viaje el resultado, **la conversión documentada no tiene punto de
aplicación**: o la ventana principal reinterpreta `x` rompiendo el contrato, o la
herramienta recibe segundos y produce el 3000 % que ella misma anticipa.

**7.6 · Faltan las conversiones que harían falta para 7.5.**
`psglab/core/windows.py` ofrece ventana↔muestras y ventana↔hora, pero **no**
segundos↔muestras ni fracción↔ventana. Los tres consumidores que las necesitan
—`signal_view.py:109`, `:118` y `histogram.py:76`— van a tener que escribir la
cuenta a mano, contra `psglab/core/README.md:42-50` (*"llamá a este módulo en vez
de escribir la cuenta"*).

**7.7 · Dos módulos reclaman ser el único lugar de conversión.**
`psglab/core/windows.py:5-7` dice *"Este módulo es el único lugar donde se hacen
esas conversiones"*; `psglab/ui/signal_view.py:88-90` dice que el visualizador es
*"el único que sabe traducir entre las cuatro unidades horizontales"*. Los dos
cubren píxeles → muestras y píxeles → segundos.

**7.8 · `install_shortcuts` exige una `Session` que en ese momento no existe.**
`psglab/ui/shortcuts.py:50` pide `session: Session`, no opcional, pero
`psglab/ui/main_window.py:38` construye la ventana *"todavía sin registro
abierto"* y `:100` declara `session -> Session | None`.

**7.9 · `Scoring.get()` permite esquivar la única guarda de la nomenclatura.**
`psglab/core/scoring.py:62` devuelve el `EpochScore` vivo, y es un dataclass
mutable (`:17-28`). Un consumidor puede hacer `scoring.get(i).stage = N2` sobre un
scoring en Rechtschaffen y Kales y saltear el `InvalidStageError` de `set_stage`
(`:70-76`).

**7.10 · Nada obliga a que el scoring y el registro hablen del mismo registro.**
`psglab/core/session.py:30-43` recibe `Recording` y `Scoring` sueltos, y los dos
prometen por su lado ser la cantidad de ventanas del registro. `go_to_window`
valida contra uno solo.

**7.11 · Constantes del pliego escritas a mano en texto que ve el usuario**, en
archivos que **ya importan la constante**: `psglab/tools/amplitude_band.py:27`
(*"Banda de 75 µV…"*, mientras la línea 15 importa `AMPLITUDE_BAND_UV`),
`psglab/ui/grid.py:25` (*"Líneas cada 3 segundos"*) y `:26` (*"Líneas cada 3 y 0,5
segundos"*), con `COARSE_GRID_SECONDS` y `FINE_GRID_SECONDS` importadas en la
línea 18. Si mañana el laboratorio quiere ventanas de 20 s —el ejemplo que da
`psglab/config.py:11`— los tres textos mienten.

**7.12 · La tabla de unidades no cubre la letra que más aparece.**
`psglab/utils/units.py:27-34` tiene `"µv"` con el **signo micro U+00B5**, y no la
**mu griega U+03BC**, que es la que escriben muchas cabeceras EDF y BrainVision.
Tampoco tiene `"volt"`, `"volts"` ni `"millivolt"`. La cobertura depende
enteramente de que `normalize_unit_name` unifique las dos, cosa que sólo está
dicha en prosa.

**7.13 · Los dos puntos de extensión son asimétricos.**
`psglab/readers/base.py:86` devuelve **instancias**;
`psglab/tools/registry.py:63` devuelve **clases**. Quien los consuma va a tener
que tratarlos distinto pese a ser "los dos puntos de extensión".

**7.14 · Superficie de parámetros despareja entre exportadores.**
`psglab/exporters/scoring_txt.py:54` no expone `separator` aunque su `format_line`
(`:96`) sí lo tiene; `psglab/exporters/annotations_txt.py:35` sí lo expone.

**7.15 · `Annotation` y `OccupancyLine` no son hashables** (dataclasses mutables,
`__hash__ = None`). `AnnotationSet.remove()` (`psglab/core/annotations.py:68`)
borraría la primera anotación *igual*, no necesariamente la señalada, y ninguna de
las dos puede ir en un conjunto. Afecta directo a `occupancy.on_mouse_press`, que
tiene que borrar *"la que está debajo"*.

**7.16 · `AnnotationSet.color_of()` devuelve `str` no opcional**
(`psglab/core/annotations.py:80`), pero `add_label` admite `color=None` y
`Annotation.color` es `str | None`. Sin `Raises:` documentado para una etiqueta
sin color ni para una desconocida.

**7.17 · `navigation.set_clock_time(label: str | None)`**
(`psglab/ui/navigation.py:36`) espera el horario ya formateado, y **nadie lo
formatea**: `window_to_clock_time` devuelve `datetime` y no hay ninguna función de
formato de hora en el paquete.

**7.18 · Detalles de convención.** `psglab/readers/base.py:113` usa la variable
`conocidas`, único identificador en español del paquete
(`psglab/README.md:93-94` los exige en inglés). Y `main.py` y los ocho
`__init__.py` no llevan la línea `Cubre del pliego` que
`psglab/README.md:95-96` exige a *"cada módulo"* — el chequeo automático no los
mira, porque `modulos_del_paquete()` excluye los `__init__.py` y no sale de
`psglab/`.

---

## 8. Cobertura de tests

**8.1 · Dos tests apagados van a fallar el día que se implemente el módulo tal
como está documentado.** `tests/test_exporters.py:42` llama a `export_scoring`
con todos los valores por defecto y afirma que 20 ventanas dan **20 líneas**; como
`psglab/config.py:129` fija `SCORING_INCLUDES_NOMENCLATURE_HEADER = True`, el
archivo va a tener **21**. Y `:62` pasa explícitamente `include_window_number=False`
—con un comentario que explica por qué no confía en `config`— pero **olvida
`include_header=False`**, con lo que la primera línea sería `# AASM` y el primer
campo `#`. El razonamiento correcto se aplicó a una de las dos constantes de
formato. Están apagados, así que nadie los verá hasta el hito 5 y van a parecer un
bug del exportador.

**8.2 · `tests/test_exporters.py:108` fija una decisión que el código dice que
está abierta.** `psglab/exporters/annotations_txt.py:61-64` dice que al separador
dentro de una etiqueta *"hay que reemplazarlo o escaparlo"*, dejando las dos
opciones. El test hace `split("|")` y exige tres campos, lo que sólo se cumple si
se **reemplaza**.

**8.3 · `tests/test_occupancy.py:37-45` no discrimina lo que dice discriminar.**
Su docstring afirma *"Las dos líneas miden lo mismo"*, y no es cierto: la
horizontal mide 0,5 y la diagonal 0,495. Como la diagonal es más corta, una
implementación que devolviera el **largo** en vez de la **proyección horizontal**
también pasaría. El test que el archivo presenta como el que fija la semántica es
el único de los siete que no la fija.

**8.4 · `tests/test_nomenclature.py:41-45` verifica dos de siete posiciones.** Su
docstring afirma que el pliego fija el orden W, REM, S1, S2, S3, S4, MT, y sólo
comprueba las dos primeras.

**8.5 · Cobertura declarada que no existe.** `COBERTURA_DE_TESTS` asigna
`information_txt.py` y `statistics.py` a `tests/test_exporters.py`, que **ni
siquiera los importa**. Son nueve stubs contados como cubiertos.

**8.6 · Comportamiento documentado sin ningún test**: la conversión de MT
(`nomenclature.py:117-118`, que la trata como W y pierde información),
`stage_label()` y `stage_code()` —el que produce los números de `Scoring.txt`—,
la no-inyectividad deliberada de `STAGE_CODES` (documentada en tres archivos),
`format_header()` —que `TODO.md:223-224` describe como un contrato entre dos
módulos—, la escritura de `-1` para las ventanas sin scorear, y la rama de unión
de intervalos de `total_percentage(counts_overlap_once=True)`.

**8.7 · Dos módulos ya implementados no tienen ningún test**:
`psglab/tools/registry.py` (que eleva `DuplicateToolError` por un camino que nada
ejercita) y `psglab/utils/errors.py`. `TODO.md:302-303` dice de ellos *"No hay
nada que hacer"*, lo que en la práctica los saca de la regla del pliego de un test
por componente.

**8.8 · `tests/test_nomenclature.py` está apagado sobre datos ya
implementados.** `STAGES_BY_NOMENCLATURE` y `STAGE_CODES` son literales, no
stubs. El archivo abre diciendo que existe para que la omisión de REM *"no vuelva
a colarse"*, y con el `pytestmark` puesto no lo evita: hoy se puede borrar
`SleepStage.REM` y la suite sigue en verde.

---

## 9. Lo que se revisó y está sano

Vale la pena dejarlo escrito, porque un informe que sólo enumera problemas da una
impresión falsa del repositorio.

- **La regla de dependencias se cumple al 100 %.** Cero imports invertidos, cero
  ciclos, ningún bloque `TYPE_CHECKING` escondiendo nada, y `core/` y `utils/` sin
  una sola referencia a `psglab.ui`, `PySide6` ni `pyqtgraph`.
- **Cero enlaces y cero anclas rotas** en los 15 documentos, incluidas las
  `#hito-N` de `TODO.md`. Es la única familia de deriva que el chequeo automático
  sí cubre, y se nota.
- **Cero firmas sin type hints** en los 51 archivos, verificado por AST.
- **Ningún registro de participante versionado.** `git ls-files data/` está vacío
  y no hay ningún archivo ignorado que además esté en el índice, sobre 48 MB de
  material sensible en el árbol de trabajo.
- **Los recuentos de stubs de los siete README de carpeta son exactos**, uno por
  uno, y suman 170 y 196.
- **Ningún riesgo real de compatibilidad entre Python 3.11 y 3.14** en el código:
  ni PEP 695, ni `datetime.UTC`, ni `itertools.batched`, ni `StrEnum`. Todos los
  `X | Y` evaluados en runtime son PEP 604, válidos desde 3.10.
- **La corrección de `window_to_samples` para frecuencias no redondas funciona**:
  verificado con 2000 ventanas a 256,125 Hz, ida y vuelta exacta, sin solapamiento
  ni hueco.
- **El heredoc del job de licencias está bien formado** y su lógica de licencia
  disyuntiva es correcta: verificada contra el entorno local, 53 paquetes, ninguno
  obliga a relicenciar.
- **`main.py` cumple el requisito de mínimo** y `.gitattributes` resuelve bien el
  problema multiplataforma de los finales de línea.

---

## Anexo: dos hallazgos que necesitan al cliente o el pliego

Todo lo demás de este informe se resuelve dentro del repositorio. Estos dos no:

1. **El hueco de numeración de la Parte 2** (hallazgo 3.4): si el pliego numera
   V2_F a V4_F de "Filtración", faltan tres requisitos en el catálogo.
2. **Sección 7 u 11** para el requisito de testeo (hallazgo 4.1): cuatro
   documentos dicen una cosa y cuatro la otra, y el pliego no está en el
   repositorio.

La única ambigüedad del pliego que sigue genuinamente abierta —de dónde salen las
impedancias— está registrada en `EXPLICACION.txt:205-209` y marcada en
`psglab/analysis/impedance.py:7`. Es de la Parte 2 y no frena ningún hito.
