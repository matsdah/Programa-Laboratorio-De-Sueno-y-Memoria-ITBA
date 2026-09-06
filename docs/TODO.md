# TODO — Parte 1 (scorer de polisomnografía)

La cola de trabajo del proyecto. **Este archivo es el único lugar que dice qué
está hecho y qué falta**; `TRAZABILIDAD.md` dice *dónde* va cada requisito y no
lleva estado, para que no haya dos fuentes que se desincronicen.

Quedan **118 stubs** (`raise NotImplementedError`) en 23 módulos de la Parte 1.
Los 26 stubs de `psglab/analysis/` son de la Parte 2 y no entran acá.

## Cómo se usa

Los hitos están **ordenados por dependencias reales**, sacadas del grafo de
importaciones del paquete. No es el orden de `TRAZABILIDAD.md`, que sigue las
secciones del pliego: quien lo lea de arriba abajo arrancaría por
`readers/brainvision.py`, que necesita `core/recording.py` terminado para poder
devolver algo.

**No empieces un módulo si el hito anterior no está cerrado.** Vas a escribir
contra firmas que todavía elevan `NotImplementedError` y no vas a poder testear
nada.

### Lo que el CI verifica solo

Desde que el equipo es de tres, [el workflow](../.github/workflows/ci.yml) corre
en cada push y cada pull request: los tests en los tres sistemas operativos, los
chequeos de consistencia de `tests/test_consistencia.py` y la verificación de
licencias.

Eso quiere decir que **no hace falta acordarse** de que las cuentas de este
archivo cuadren, ni de que los enlaces no se rompan, ni de borrar el
`pytestmark` al terminar un módulo: si algo de eso queda mal, el pull request
falla. Los chequeos corren también con `python -m pytest`, así que conviene
pasarlos antes de pushear.

### Cuándo un ítem está terminado

Las cuatro condiciones, no tres:

1. Los stubs del módulo están implementados.
2. **Su test existe y corre.** Si el archivo de test ya existe, hay que borrar
   la línea `pytestmark = pytest.mark.skip(...)` del principio. Si no existe,
   hay que crearlo (regla del pliego, sección 7: un test por componente).
3. Su fila de `TRAZABILIDAD.md` sigue siendo cierta.
4. El `README.md` de la carpeta sigue siendo cierto.

Mientras el `pytestmark` esté, la suite pasa en verde **sin haber verificado
nada**. Un verde por omisión es peor que un rojo.

## Progreso

| Hito | Módulos con stubs | Stubs | Estado |
|---|---|---|---|
| [0. Desbloquear](#hito-0-desbloquear) | — | 0 | ✅ cerrado |
| [1. Cimientos](#hito-1-cimientos) | — | 0 | ✅ cerrado |
| [2. Scoring y anotaciones](#hito-2-scoring-y-anotaciones) | — | 0 | ✅ cerrado |
| [3. Sesión](#hito-3-sesión) | — | 0 | ✅ cerrado |
| [4. Importación](#hito-4-importación) | 5 | 9 | ⬜ |
| [5. Exportadores](#hito-5-exportadores) | 4 | 14 | ⬜ |
| [6. Interfaz](#hito-6-interfaz) | 8 | 46 | ⬜ |
| [7. Herramientas](#hito-7-herramientas) | 6 | 49 | ⬜ |
| [8. Cierre](#hito-8-cierre-de-la-parte-1) | — | 0 | ⬜ |
| | **23** | **118** | |

### Los tres cortes que importan

- **Al cerrar el hito 3** toda la capa de negocio funciona y se puede testear
  sin abrir una ventana.
- **Al cerrar el hito 5** el programa hace su trabajo completo desde un script
  —leer un EDF, scorear, exportar los tres archivos— **todavía sin interfaz
  gráfica**. Es el pago concreto de que `core/` no importe `ui/`.
- **Al cerrar el hito 6** `python main.py` abre algo usable por primera vez.

**Los hitos 4 y 5 no dependen de `ui/`.** Una vez cerrado el 3, dos personas
pueden ir en paralelo: una por 4 y 5, otra por 6.

---

## Hito 0: Desbloquear

**Cerrado el 4 de septiembre de 2026.** Eran las preguntas que el pliego dejaba
abiertas y el material de prueba que faltaba. Queda una sola sin responder, y es
de la Parte 2.

### Decidido con el cliente

| Pregunta | Decisión | Dónde vive |
|---|---|---|
| Formato de `Scoring.txt`: ¿dos campos o tres? | **Dos**, como el ejemplo: `"2 0"`. El nº de ventana queda implícito en el orden. | `config.SCORING_INCLUDES_WINDOW_NUMBER` |
| Índice de los "puntos": ¿0 o 1? | **Base 0**, la del programa, numpy y MNE. | `config.ANNOTATION_SAMPLE_BASE` |
| Códigos de fase: ¿REM=5, MT=6? | **Sí**, la convención habitual: 0=W, 1..4=S1..S4, 5=REM, 6=MT. | `core/nomenclature.py::STAGE_CODES` |
| Ocupación: ¿la superposición cuenta una o dos veces? | **Dos**: se suman los aportes sin descontar. El total puede pasar del 100 % y eso es lo buscado. | `config.OCCUPANCY_COUNTS_OVERLAP_ONCE` |
| ¿Cómo se sabe con qué nomenclatura se generó un `Scoring.txt`? | **Cabecera comentada** en el propio archivo: `# AASM`. Se registra además en `Informacion.txt`. | `config.SCORING_INCLUDES_NOMENCLATURE_HEADER` |
| ¿Qué código lleva una ventana sin scorear? | **`-1`.** No puede confundirse con ninguna fase real, porque todas son 0 o positivas. | `core/nomenclature.py::STAGE_CODES` |
| ¿El scoring automático entra en el alcance? | **No.** Queda como funcionalidad futura, junto al potencial evocado y el acoplamiento de husos. | `TRAZABILIDAD.md` |
| Titular del copyright | **Confirmado** tal como está: Laboratorio de Sueño y Memoria, ITBA. | `LICENSE` |

La decisión de la nomenclatura se revisó una vez y conviene saber por qué. La
primera versión la registraba **sólo** en `Informacion.txt`, dando por sentado
que los tres archivos viajaban juntos. No es así: **V4_F deja exportar uno
solo**, y exportar nada más que el scoring es el caso más común. Ese archivo
salía ambiguo, porque "2" es S2 en R&K y N2 en AASM.

Por eso `Scoring.txt` declara su nomenclatura en su propia cabecera. Queda una
dependencia parecida sin resolver del todo: **`Anotaciones.txt` guarda
posiciones en muestras y no lleva la frecuencia de muestreo**, que vive en
`Informacion.txt`. Se aceptó porque falla distinto: una fase mal interpretada
pasa desapercibida, una posición sin frecuencia directamente no se puede
convertir y el problema salta enseguida.

### Material de prueba

- [x] **EDF** — [Sleep-EDF Database Expanded](https://physionet.org/content/sleep-edfx/1.0.0/)
  de PhysioNet, bajo [ODC-By v1.0](https://www.physionet.org/content/sleep-edfx/view-license/1.0.0/).
  Registro real de noche completa: 7 canales y 22 h, con hipnograma scoreado en
  Rechtschaffen y Kales. **Ojo con las frecuencias: son mixtas.** Verificado
  leyendo la cabecera: `EEG Fpz-Cz`, `EEG Pz-Oz` y `EOG horizontal` van a
  100 Hz, y `Resp oro-nasal`, `EMG submental`, `Temp rectal` y `Event marker`
  van a 1 Hz. `core/recording.py` exige **una sola** frecuencia para toda la
  matriz, así que este archivo no entra tal cual en el modelo: es lo primero
  que hay que resolver en el hito 4, y `MixedSamplingRateError` existe para
  eso.
- [x] **BrainVision** — los archivos de prueba de
  [MNE-Python](https://github.com/mne-tools/mne-python/tree/main/mne/io/brainvision/tests/data)
  (BSD-3): tripleta `.vhdr` + `.vmrk` + `.eeg`, 32 canales con nombres 10-20,
  1000 Hz. **Son 7,9 segundos, no una noche**: sirven para verificar que el
  lector entiende el formato, no para probar el programa de punta a punta.
  Conseguir un registro real del laboratorio sigue siendo deseable.

Los dos viven en `data/`, que **el `.gitignore` excluye**: no van al
repositorio.

### Sigue abierta

- [ ] **Origen de las impedancias** (cabecera del archivo, archivo aparte o
  carga manual). Es de la **Parte 2**, así que no frena nada de este TODO.
  Ver `analysis/impedance.py`.

---

## Hito 1: Cimientos

**Cerrado el 4 de septiembre de 2026.** Eran los cuatro módulos que **no
importan nada interno**, así que se podían hacer en cualquier orden.

Con esto `core/` ya tiene el vocabulario (`SleepStage`, `Nomenclature`), el
modelo (`Recording`) y las conversiones de tiempo (`windows`), que es
exactamente lo que consumen `scoring.py` y `annotations.py` del hito 2. Y
`utils/` queda terminada entera.

- [x] **`psglab/utils/units.py`** · ~~4 stubs~~ · sostiene la escala en µV de
      V1_P "Visualización" y la banda de V1_F "Herramienta de amplitud"
  - Test: `tests/test_units.py`, **27 tests en verde**.
  - La mitad de los tests son de **entrada sucia**, no de aritmética: las
    cabeceras de EDF y BrainVision escriben la unidad de formas variadas, y
    confundir "no reconozco esto" con "esto vale 1" deja la señal mal escalada
    de punta a punta sin que nada se vea raro en pantalla.
  - Los dos caracteres "mu" (U+03BC y U+00B5) se ven idénticos, así que un test
    afirma sus puntos de código: si alguien los intercambiara al editar el
    módulo, la normalización dejaría de hacer nada y ningún otro test lo notaría.
- [x] **`psglab/core/windows.py`** · ~~5 stubs~~ · sostiene V1_P "Visualización"
      (nº de ventana y total), V1_F "Navegación", V2_F "Histograma"
  - Test: `tests/test_windows.py`, **35 tests en verde**.
  - Los bordes se calculan desde el índice de la ventana, nunca acumulando un
    paso redondeado: con una frecuencia no redonda (256,125 Hz en EDF) acumular
    corre la ventana 960 casi tres segundos. Hay tres tests que lo fijan.
  - Convierte entre las cuatro unidades no gráficas: ventanas, muestras,
    segundos dentro de la ventana y fracción de ventana. Las herramientas
    piden acá en vez de escribir la cuenta; los píxeles son de
    `ui/signal_view.py`, que es lo único que conoce el ancho de la pantalla.
- [x] **`psglab/core/nomenclature.py`** · ~~5 stubs~~ · V3_F "Scoring",
      V3_F "Histograma"
  - Test: `tests/test_nomenclature.py`, **37 tests en verde**.
  - REM va en las dos nomenclaturas. El test ya lo verificaba: no se tocó.
  - `is_valid(UNSCORED, ...)` da **`True`** aunque `stages_of()` no la incluya.
    Es el punto donde las dos funciones dejan de responder lo mismo:
    `stages_of()` da las filas del histograma y "sin scorear" no es una fila,
    pero sí es asignable, porque es como se **borra** el scoring de una ventana
    marcada por error. Si diera `False`, despuntuar sería imposible.
  - Las equivalencias entre nomenclaturas se escriben en las dos direcciones,
    sin derivar una de la otra: no son simétricas, y derivarlas escondería que
    S3 y S4 caen los dos en N3 y que volver no puede distinguirlos.
- [x] **`psglab/core/recording.py`** · ~~7 stubs~~ · soporte de V1_F/V2_F/V3_F
      "Importación" y V4_F "Visualización"
  - Test: `tests/test_recording.py`, **33 tests en verde**, sobre la fixture
    `synthetic_signal` de `conftest.py`.
  - **`__post_init__` rechaza un registro incoherente consigo mismo**: matriz
    que no es 2-D, canales que no coinciden con las filas, frecuencia no
    positiva, `Channel.index` que no es su posición, o nombres repetidos. El
    error salta en el lector, que es donde está el bug, y no tres capas arriba.
  - `get_segment` con un `stop` posterior al final devuelve un tramo **más
    corto, en silencio**. Es el caso normal de la última ventana incompleta, no
    un error: `windows.window_to_samples` devuelve justamente eso.

`psglab/utils/errors.py` ya está implementado y no tiene stubs, pero tampoco
tiene test:

- [x] **`psglab/utils/errors.py`** · 0 pendientes · ya tiene su test
  - Test: `tests/test_errors.py`, **9 tests en verde**.
  - Verifica que `PsgLabError` guarde el mensaje y la causa técnica por
    separado, y que las subclases se atrapen con un solo `except PsgLabError`.
    Es la promesa sobre la que se apoya todo el manejo de errores que ve el
    investigador.
  - Dos de los tests **recorren el módulo** en vez de enumerar las clases: una
    excepción nueva que se olvide de heredar de `PsgLabError` los hace fallar,
    cosa que una lista escrita a mano no vería.
  - Se agregó `InvalidRecordingError`, que usa `core/recording.py` para rechazar
    un registro incoherente. No es `UnreadableFileError`: el archivo se leyó
    bien, lo que quedó mal es lo que armó el lector.

---

## Hito 2: Scoring y anotaciones

**Cerrado el 5 de septiembre de 2026.** Con esto `core/` tiene todo lo que
`session.py` recibe en su constructor, que es el hito 3 y el corte donde la capa
de negocio entera funciona sin abrir una ventana.

- [x] **`psglab/core/scoring.py`** · ~~10 stubs~~ · V1_F, V2_F, V3_F "Scoring"
  - Test: `tests/test_scoring.py`, **25 tests en verde**.
  - Un scoring nuevo arranca entero en `UNSCORED`: el histograma tiene el
    tamaño de la noche desde el principio.
  - `set_stage` acepta `UNSCORED`, que es cómo el usuario **borra** el scoring
    de una ventana marcada por error. Se apoya en que
    `nomenclature.is_valid(UNSCORED, ...)` sea `True`, decidido en el hito 1.
  - **El índice se valida antes que la fase.** Con los dos mal, "esa ventana no
    existe" manda al usuario al problema correcto.
  - `stages()` devuelve una copia: prestarle la lista interna al histograma lo
    dejaría corromper el scoring sin pasar por `set_stage`.
- [x] **`psglab/core/annotations.py`** · ~~11 stubs~~ · V1_F "Anotación de la señal"
  - Test: `tests/test_annotations.py`, **37 tests en verde**.
  - Las anotaciones se guardan en muestras, no en segundos.
  - **La lista interna se mantiene ordenada por muestra de inicio.** No es una
    optimización: es lo que hace que el índice de `remove_at()` signifique lo
    mismo que la posición en `all()`. Con orden de creación, el anotador
    borraría una banda distinta de la que el usuario señaló.
  - **La duración cero se rechaza.** El pliego pide marcar el evento con una
    banda, y una sin ancho no se dibuja ni la devuelve nunca `in_range`: el
    usuario la crearía y no la vería jamás.
  - `in_range` usa intervalo semiabierto, igual que `windows.window_to_samples`,
    para que una anotación no se dibuje en dos ventanas seguidas.
  - Los colores salen de `PALETTE`, en `annotations.py` y no en `config.py`:
    el pliego pide una banda de color pero no dice cuáles, así que elegirlos es
    del programa. La asignación es por orden de registro, o sea determinística.

---

## Hito 3: Sesión

**Cerrado el 5 de septiembre de 2026.** Con esto **`core/` queda terminada
entera** y la capa de negocio funciona sin abrir una ventana. Los hitos 4 y 5 no
dependen de `ui/`, así que desde acá se puede trabajar en paralelo.

- [x] **`psglab/core/session.py`** · ~~19 stubs~~ · V1_F "Navegación";
      V2_P, V3_P, V4_F "Histograma", V5_F "Visualización"
  - Test: `tests/test_session.py`, **42 tests en verde**. Navegación y amplitud
    son testeables sin GUI: ese es el motivo de que `Session` viva en `core/`.
  - `n_windows` sale de `windows.count_windows()` sobre el registro, que es la
    fuente de verdad, y `__init__` eleva `ScoringMismatchError` si el scoring no
    mide lo mismo. Sin ese chequeo, un scoring importado de otro registro daría
    un histograma de largo equivocado sin ningún error visible.
  - **Aumentar la amplitud BAJA el número de `scale_uv`.** Parece al revés:
    `scale_uv` es cuántos µV representa la altura del canal, así que para que la
    señal se vea más grande esa altura tiene que representar menos µV. Hay un
    test que lo dice con todas las letras.
  - Las dos flechas delegan en `set_scale_uv`, que es el único lugar que recorta
    contra los topes de `config`.
  - `active_tool` significa **la herramienta exclusiva del mouse**: la banda de
    amplitud y los dos paneles declaran `exclusive = False` y están activos a la
    vez, así que los gestiona la ventana principal. `Session` tampoco valida el
    nombre: importar `tools/registry.py` desde `core/` cerraría un ciclo.
  - Visibilidad y selección son ejes independientes y los dos validan contra el
    registro. No se exige que lo seleccionado esté visible: el pliego no los ata.
  - `visible_channels` arranca con **todos** los canales. El subconjunto inicial
    de V1_P (ojos, C3, C4, EMG) necesita `readers/channel_types.py`, del hito 4,
    y es un default de la interfaz, no de `core/`.

> **Cerrado el hito 3, toda la capa de negocio funciona sin abrir una ventana.**

---

## Hito 4: Importación

- [ ] **`psglab/readers/channel_types.py`** · 3 stubs · V4_F "Visualización"
  - Test: **crear** `tests/test_channel_types.py`. Los nombres de
    `conftest.py` ya sirven: `C3` debe dar EEG por 10-20 y `EMG-menton` por
    prefijo.
- [ ] **`psglab/readers/base.py`** · 1 stub (`file_dialog_filter`) · base de
      V1_F/V2_F "Importación"
  - V3_F no pasa por acá: lo resuelve `scoring_reader.py`, que lee un scoring
    ya existente y no despacha por formato.
  - El resto del módulo ya está implementado a propósito: `can_read`,
    `register_reader`, `read_recording` y `load_all_readers` corren al
    importar. **No convertirlos en stubs.**
  - Test: **crear** `tests/test_readers.py`, que cubre este módulo y los dos de
    abajo. El autodescubrimiento y el despacho se pueden testear con un lector
    de mentira, sin ningún archivo real.
- [ ] **`psglab/readers/edf.py`** · 1 stub · V2_F "Importación"
  - Test: `tests/test_readers.py`. Necesita el registro de prueba del hito 0.
- [ ] **Decidir cómo corre `tests/test_readers.py` en el CI.** Los registros de
      prueba viven en `data/`, que el `.gitignore` excluye entero y con razón,
      así que en GitHub Actions **no van a estar**. Saltear el test ahí
      reintroduce el verde por omisión que este proyecto combate. Las salidas
      razonables son bajar la Sleep-EDF en un paso del workflow, o partir el
      test en dos: el despacho y el registro con un lector de mentira, que
      corren en cualquier lado, y la lectura real, que se saltea con un motivo
      explícito y visible en `pytest -rs`.
- [ ] **`psglab/readers/brainvision.py`** · 1 stub · V1_F "Importación"
  - Test: `tests/test_readers.py`. Necesita el registro de prueba del hito 0.
  - `read()` devuelve la señal **ya en µV** y con la clase de canal detectada.
    Ninguna capa posterior lo vuelve a verificar.
- [ ] **`psglab/readers/scoring_reader.py`** · 3 stubs · V3_F "Importación"
  - Test: **crear** `tests/test_scoring_reader.py`.
  - Incluye `detect_nomenclature()`, que lee la cabecera que escribe
    `exporters/scoring_txt.py::format_header()`. Lo que uno escribe el otro lo
    tiene que poder volver a leer.

### Lo que la auditoría dejó medido para este hito

Cuatro cosas que hoy no fallan porque nadie las ejecuta todavía, y que se
verificaron leyendo el código y el material de prueba. No son bugs abiertos:
son decisiones que este hito tiene que tomar.

- [ ] **V3_F es el único ID sin camino desde su propio material de prueba.** El
      hipnograma de la Sleep-EDF es un `.edf` —un EDF+ de anotaciones—, y
      `Reader.can_read()` despacha por extensión, así que `read_recording()` se
      lo entrega al `EdfReader`, que va a intentar leerlo como señal.
      `read_scoring()` recibe un `Path` pero **no hay nada que enrute hasta
      ella**. Decidir si el scoring entra por su propio diálogo —lo más
      probable, porque V3_F es "importar un scoring existente" y no un
      formato más— o si el despacho tiene que mirar el contenido.
- [ ] **`Channel` no tiene dónde anotar la frecuencia original.** Si el hito
      resuelve las frecuencias mixtas remuestreando, el registro pierde el dato
      de a qué frecuencia venía cada canal, que es justo lo que hay que mostrar
      para que el investigador sepa qué está mirando. Agregar el campo es
      barato ahora y caro después: `Channel` es `frozen` y lo construye cada
      lector.
- [ ] **Descartar un canal obliga a renumerar `Channel.index`.** El EDF de
      prueba trae `Event marker`, y un EDF+ trae además `EDF Annotations`.
      Sacarlos del medio de la lista sin renumerar hace que
      `Recording.__post_init__` eleve `InvalidRecordingError` hablando de
      "canales cuya posición declarada no coincide con la fila que ocupan":
      un mensaje correcto que le hace creer al usuario que su archivo está
      roto. El lector renumera, o no descarta.
- [ ] **Los prefijos 10-20 de `channel_types.py` son voraces.** `EEG_POSITIONS`
      incluye `"t"`, `"c"`, `"f"`, `"p"` y `"o"` sueltos, y ningún patrón de
      `KIND_PATTERNS` atrapa la temperatura: **`"Temp rectal"`, que está en el
      registro de prueba, empieza con `"t"` y se clasificaría como EEG**. El
      parámetro `unit` de `detect_channel_kind()` existe para esto —un canal en
      °C no es un EEG—, pero hoy nada obliga a usarlo. El test tiene que
      incluir los siete nombres reales del archivo.

---

## Hito 5: Exportadores

> **Medido en la auditoría:** `stage_durations_seconds()` y
> `scored_time_seconds()` **no pueden ser correctas con la firma que tienen**.
> Reciben `scoring` y `window_seconds`, y con eso sólo saben multiplicar; para
> la **última ventana, que casi siempre está incompleta**, hace falta
> `window_duration()`, que pide `n_samples` y `sampling_rate`. Son las que
> alimentan la tabla de tiempos de `Informacion.txt`, así que el error se
> publica. Cambiar la firma es parte de este hito, no de otro.

- [ ] **`psglab/exporters/statistics.py`** · 6 stubs · alimenta V3_F
      "Archivo de salida"
  - No escribe archivos: por eso se puede testear sin tocar el disco.
  - Test: **extender** `tests/test_exporters.py`, que hoy **no lo importa**.
    Figuraba como cubierto en `COBERTURA_DE_TESTS` sin estarlo, y eso hacía que
    nadie exigiera un test para sus 6 stubs.
- [ ] **`psglab/exporters/scoring_txt.py`** · 3 stubs · V1_F "Archivo de salida"
  - **Las variantes de formato tienen que seguir siendo alcanzables** cambiando
    sólo la constante de `config`: el nº de ventana por línea y la cabecera de
    nomenclatura.
  - `format_header()` escribe la cabecera que lee
    `readers/scoring_reader.py::detect_nomenclature()`.
- [ ] **`psglab/exporters/annotations_txt.py`** · 2 stubs · V2_F "Archivo de
      salida"
  - El índice de los puntos lo fijó el hito 0 en 0: sale de
    `config.ANNOTATION_SAMPLE_BASE`, no se escribe a mano.
- [ ] **`psglab/exporters/information_txt.py`** · 3 stubs · V3_F "Archivo de
      salida"
  - Las secciones que no correspondan se omiten con una explicación, no con
    ceros.
  - Test: **extender** `tests/test_exporters.py`, que hoy **no lo importa**.
    Mismo caso que `statistics.py`.
- [ ] Test de los cuatro: `tests/test_exporters.py` → **borrar el
      `pytestmark`** y extenderlo a `statistics`.
- [ ] **Test de ida y vuelta de la cabecera**, que cruza este hito y el 4:
      exportar un scoring en AASM, releerlo con `read_scoring()` sin pasarle la
      nomenclatura, y verificar que sale AASM. Es un contrato entre dos módulos
      de hitos distintos, del tipo que se rompe en silencio si nadie lo fija.

> **Cerrado el hito 5, el programa hace su trabajo entero desde un script, sin
> interfaz.** Vale la pena escribir ese script y guardarlo como verificación.

---

## Hito 6: Interfaz

Primera vez que el programa se puede abrir. `ui/` **no lleva tests unitarios**:
por eso la capa se mantiene delgada y toda la regla vive en `core/`. No es un
olvido.

> **Medido en la auditoría:** `Session` **no tiene mecanismo de notificación**
> —ni callbacks, ni observadores, ni señales—, así que V5_F depende por entero
> de que `main_window.py` se acuerde de llamar a `Tool.on_window_changed()`
> después de cada `go_to_window()`, `next_window()` y `previous_window()`.
> Son 10 stubs y la única capa sin tests: es el peor lugar posible para dejar
> una obligación que nadie verifica. Decidir acá si `Session` avisa sola.

- [ ] **`psglab/ui/grid.py`** · 4 stubs · V1_P, V2_F "Diseño de la interfaz"
- [ ] **`psglab/ui/signal_view.py`** · 13 stubs · V1_P, V2_P, V4_F, V5_F
      "Visualización" (+ el dibujo de V3_P), V1_F "Anotación de la señal"
  - Incluye `seconds_at_pixel`, `window_fraction_at_pixel` y `sample_at_pixel`: es el **único**
    lugar que traduce entre píxeles, segundos, fracción de ventana y muestras.
    Ver el contrato en `psglab/tools/base.py`.
- [ ] **`psglab/ui/navigation.py`** · 5 stubs · V1_F "Navegación"
- [ ] **`psglab/ui/channel_selector.py`** · 6 stubs · V3_P, V4_F "Visualización"
- [ ] **`psglab/ui/scoring_panel.py`** · 3 stubs · V1_F, V2_F, V3_F "Scoring"
- [ ] **`psglab/ui/shortcuts.py`** · 3 stubs · flechas y teclas de fase
  - Los atajos se declaran **sólo acá**. Los de fase salen de la nomenclatura,
    no de un diccionario a mano.
- [ ] **`psglab/ui/main_window.py`** · 10 stubs · V4_F "Archivo de salida"
  - Conecta, no implementa. Acá se cablean a mano los callbacks de las
    herramientas, que no usan señales de Qt.
- [ ] **`psglab/app.py`** · 2 stubs · infraestructura
  - Con esto `python main.py` deja de terminar en `NotImplementedError`.

---

## Hito 7: Herramientas

Las seis son independientes entre sí: **se pueden repartir**. Todas se pueden
testear sin GUI, porque `Tool` y `ViewerTool` no heredan de `QObject`.

Antes de escribir una, leé [`tools/README.md`](../psglab/tools/README.md): el
sistema de coordenadas de `ViewerTool` (segundos y µV) no es el de `Tool`
(coordenadas propias del panel).

> **Medido en la auditoría:** `BandOverlay` lleva `y_center_uv` y `height_uv`
> pero **no lleva canal**, y `Session.scale_uv()` es por canal. Con dos canales
> a escalas distintas, esos 75 µV no tienen una única traducción a píxeles y
> `signal_view.py` no tiene con qué elegir. O el overlay dice sobre qué canal
> va, o la banda se define en coordenadas de pantalla y deja de ser 75 µV.

- [ ] **`psglab/tools/amplitude_band.py`** · 5 stubs · V1_F "Herramienta de
      amplitud" · `ViewerTool`
  - Test: **crear** `tests/test_amplitude_band.py`. Los 75 µV salen de
    `config.AMPLITUDE_BAND_UV`.
- [ ] **`psglab/tools/occupancy.py`** · 13 stubs · V1_F–V5_F "Ocupación" ·
      `ViewerTool`
  - V2_F y V4_F: el hito 0 fijó que la superposición se cuenta **dos veces**,
    y sale de `config.OCCUPANCY_COUNTS_OVERLAP_ONCE`.
  - Test: `tests/test_occupancy.py` → **borrar el `pytestmark`**.
- [ ] **`psglab/tools/magnifier.py`** · 9 stubs · V1_F, V2_F "Lupa" ·
      `ViewerTool`
  - Test: **crear** `tests/test_magnifier.py` (el contador de picos es
    testeable sin dibujar nada).
- [ ] **`psglab/tools/overview.py`** · 6 stubs · V1_F, V2_F, V3_F "Übersicht" ·
      `Tool`
  - Test: **crear** `tests/test_overview.py`. La cantidad de vecinas es
    configurable y asimétrica.
- [ ] **`psglab/tools/histogram.py`** · 7 stubs · V1_P, V2_F, V3_F, V4_F
      "Histograma" · `Tool`
  - Test: **crear** `tests/test_histogram.py`.
  - Su `on_click(x_fraction)` es propio: un clic cae en una ventana de la
    noche, no en un segundo de la ventana actual.
- [ ] **`psglab/tools/annotator.py`** · 9 stubs · V1_F "Anotación" ·
      `ViewerTool`
  - El índice de los puntos lo fijó el hito 0 en 0: sale de
    `config.ANNOTATION_SAMPLE_BASE`.
  - Test: **crear** `tests/test_annotator.py`.

`tools/base.py` y `tools/registry.py` **ya están implementados** y no tienen
stubs, pero eso no es lo mismo que estar verificados:

- [ ] **`psglab/tools/registry.py` y `psglab/tools/base.py`** · 0 pendientes ·
      les falta el test: **crear** `tests/test_registry.py`
  - Que `@register_tool` eleve `DuplicateToolError` con dos herramientas del
    mismo nombre, que `get_tool` eleve `UnknownToolError`, que `load_all_tools`
    encuentre las seis y no se rompa si se la llama dos veces, y que los
    métodos de evento de `Tool` y `ViewerTool` no hagan nada por defecto en vez
    de elevar. Es el mecanismo del que dependen las seis herramientas y hoy no
    lo verifica nada.

---

## Hito 8: Cierre de la Parte 1

- [ ] **Ningún test salteado.** `python -m pytest` no debe informar ningún
      `skipped`:
      ```bash
      python -m pytest -rs
      ```
- [ ] **Ningún stub de Parte 1.** Tiene que dar 0:
      ```bash
      grep -r "raise NotImplementedError" psglab --include=*.py | grep -v "/analysis/" | wc -l
      ```
- [ ] **Los 34 IDs de la Parte 1 de [`TRAZABILIDAD.md`](TRAZABILIDAD.md) están
      cerrados**, y cada fila apunta al archivo correcto.
- [ ] **Las ambigüedades resueltas quedaron documentadas** en
      `EXPLICACION.txt` sección 8, y los módulos que decían "PENDIENTE DE
      DEFINICIÓN CON EL CLIENTE" ya no lo dicen.
- [ ] **Licencias verificadas**, sin ninguna GPL:
      ```bash
      pip-licenses --format=markdown --order=license
      ```
- [ ] **El programa se abre, scorea una noche y exporta los tres archivos.**

---

## Al agregar o cerrar un ítem

Actualizá en el mismo commit: este archivo, la fila de `TRAZABILIDAD.md` y el
`README.md` de la carpeta que tocaste. Los PR van a la branch **`Add`**, nunca
a `Master`, y vienen comentados.
