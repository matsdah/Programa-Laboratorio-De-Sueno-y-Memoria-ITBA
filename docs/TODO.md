# TODO — Parte 1 (scorer de polisomnografía)

La cola de trabajo del proyecto. **Este archivo es el único lugar que dice qué
está hecho y qué falta**; `TRAZABILIDAD.md` dice *dónde* va cada requisito y no
lleva estado, para que no haya dos fuentes que se desincronicen.

Quedan **0 stubs** (`raise NotImplementedError`) en 0 módulos de la Parte 1:
**la Parte 1 está terminada**, con los hitos 0 a 7 cerrados. Falta el hito 8,
que es una lista de comprobación y no código nuevo.
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
| [4. Importación](#hito-4-importación) | — | 0 | ✅ cerrado |
| [5. Exportadores](#hito-5-exportadores) | — | 0 | ✅ cerrado |
| [6. Interfaz](#hito-6-interfaz) | — | 0 | ✅ cerrado |
| [7. Herramientas](#hito-7-herramientas) | — | 0 | ✅ cerrado |
| [8. Cierre](#hito-8-cierre-de-la-parte-1) | — | 0 | ⬜ |
| | **0** | **0** | |

### Los tres cortes que importan

- **Al cerrar el hito 3** toda la capa de negocio funciona y se puede testear
  sin abrir una ventana.
- **Al cerrar el hito 5** el programa hace su trabajo completo desde un script
  —leer un EDF, scorear, exportar los tres archivos— **todavía sin interfaz
  gráfica**. Es el pago concreto de que `core/` no importe `ui/`.
- **Al cerrar el hito 6** `python main.py` abre algo usable por primera vez.
  Ya no termina en `NotImplementedError`.

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
  matriz, y se daba por sentado que había que remuestrear acá.
  **Medido en el hito 4: no hace falta.** MNE unifica solo, sobremuestreando al
  máximo, y devuelve una única frecuencia sin avisar. Lo que sí hacía falta era
  no perder el dato, y por eso el hito agregó `Channel.original_sampling_rate`.
  `MixedSamplingRateError` **quedó sin usar**: sigue definido para un formato
  futuro que sí tenga que rechazar, pero ningún lector lo eleva hoy.
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
  - Test: `tests/test_nomenclature.py`, **45 tests en verde**. Los ocho
    últimos son de `stage_from_code()`, que agregó el hito 4.
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
  - Test: `tests/test_recording.py`, **36 tests en verde**, sobre la fixture
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
  - Test: `tests/test_session.py`, **60 tests en verde**. Navegación y amplitud
    son testeables sin GUI: ese es el motivo de que `Session` viva en `core/`.
  - `set_scoring()` se agregó en el hito 6, para V3_F: importar un scoring no
    es abrir otro registro, así que sustituye adentro en vez de armar otra
    `Session`. Armar otra devolvía al usuario a la ventana 0 y le tiraba los
    canales y las amplitudes, y además dejaba a las herramientas ya activadas
    apuntando a la sesión vieja **sin que nada fallara**.
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

- [x] **`psglab/readers/channel_types.py`** · ~~3 stubs~~ · V4_F "Visualización"
  - Test: `tests/test_channel_types.py`, **63 tests en verde**. Los siete
    nombres del registro de prueba van como **texto**, así que corre también en
    el CI, donde `data/` no existe.
  - **Tres de los siete fallaban.** La comparación era por prefijo del nombre
    entero, y así `"Temp rectal"` empieza con `"t"` —que `EEG_POSITIONS` trae
    suelto— y salía EEG, mientras que `"EEG Fpz-Cz"` empieza con `"e"` y no
    coincidía con nada: los dos canales de EEG del único registro real, que son
    la señal que se scorea, caían en OTHER. Ahora se compara **token por
    token**, así que la posición de `"EEG Fpz-Cz"` es `Fpz` y `"Temp rectal"` no
    tiene ninguna.
  - El parámetro `unit` por fin se usa, como **segunda** línea de defensa: una
    unidad que no es eléctrica degrada a OTHER las clases que sí lo son. No
    alcanza a RESPIRATORY, o `"Resp oro-nasal"` —que no declara unidad— dejaría
    esa clase inalcanzable.
  - `unit=None` significa "el formato no lo dice" y **no veta**; una unidad
    vacía sí. Confundirlas fue un error real de la primera versión del test.
- [x] **`psglab/readers/base.py`** · ~~1 stub~~ (`file_dialog_filter`) · base de
      V1_F/V2_F "Importación"
  - La primera entrada del filtro junta las extensiones de todos los formatos,
    que es la que el diálogo ofrece por defecto. Devuelve **sólo texto**: no
    importa Qt, que en `readers/` está prohibido y verificado.
  - V3_F no pasa por acá: lo resuelve `scoring_reader.py`, que lee un scoring
    ya existente y no despacha por formato.
  - El resto del módulo ya está implementado a propósito: `can_read`,
    `register_reader`, `read_recording` y `load_all_readers` corren al
    importar. **No convertirlos en stubs.**
  - Test: `tests/test_readers.py`, **38 tests en verde**, que cubre este módulo
    y los dos de abajo. El autodescubrimiento y el despacho se testean con un
    lector de mentira, sin ningún archivo real.
- [x] **`psglab/readers/edf.py`** · ~~1 stub~~ · V2_F "Importación"
  - Test: `tests/test_readers.py`. Sobre el registro real: 7 canales, 22,1 h,
    100 Hz, las clases de los siete y sus frecuencias originales.
  - **El test que justifica el archivo** compara la amplitud contra el rango
    físico que declara la cabecera, leyéndola por su cuenta: con el parser del
    propio lector, un error de offsets se cancelaría solo.
  - **Las tres suposiciones del hito se midieron y dos eran falsas.**
    `MixedSamplingRateError` no se usa: **MNE ya unifica sobremuestreando**, así
    que no hay nada que remuestrear. Y no hay que descartar `EDF Annotations` a
    mano, porque MNE también lo excluye solo.
  - **MNE devuelve volts**, no la unidad de la cabecera, para los canales cuya
    unidad reconoce; los demás los deja nativos. La conversión de acá es de
    volt a microvolt y **no** la que correspondería al archivo: aplicar
    `conversion_factor("uV")`, que vale 1, dejaría la señal un millón de veces
    más chica y con autoescala seguiría pareciendo una señal. Comprobado contra
    el rango físico de la cabecera: ±192 uV declarados, −192 a 170,6 leídos.
  - La frecuencia original de cada canal se lee de la cabecera a mano. MNE sólo
    la expone en un atributo privado, y el formato EDF está congelado desde
    1992: es más estable el parseo propio.
  - Un EDF **sin ninguna señal** —un hipnograma, que es un EDF+ de anotaciones—
    eleva `UnreadableFileError` mandando al importador de scoring, en vez de
    dejar que `Recording` diga "no tiene ningún canal" y haga creer que el
    archivo del usuario está roto.
- [x] **Decidido cómo corre `tests/test_readers.py` en el CI: partido en dos.**
      El despacho, el registro y el filtro del diálogo se prueban con un lector
      de mentira y corren en todos lados; la lectura de archivos reales se
      saltea con un motivo explícito, visible en `pytest -rs`. Bajar la
      Sleep-EDF en el workflow se descartó: ataría el verde a que PhysioNet esté
      disponible y metería 48 MB de descarga en un job que tarda segundos.
      **En esta máquina no se saltea ninguno**, porque `data/` existe: el skip
      es del CI, no del desarrollo.
- [x] **`psglab/readers/brainvision.py`** · ~~1 stub~~ · V1_F "Importación"
  - Test: `tests/test_readers.py`. 32 canales, 1000 Hz, 26 detectados como EEG
    y los 13 marcadores del `.vmrk`. Hay un test que afirma que `FP1` y `FP2`
    están en la misma escala: es como se encontró el bug del `Codepage`.
  - **La unidad omitida significa µV**, por convención del formato, y MNE la
    aplica. Tratar el campo vacío como "no sé" —lo correcto en EDF— dejaba un
    canal de EEG sin convertir entre sus vecinos.
  - **Hay que respetar el `Codepage=` que declara la cabecera.** Leerla como
    latin-1 a ciegas convertía la unidad "µV" en dos caracteres, y con eso 23
    canales de EEG quedaban sin convertir **y** clasificados como OTHER, porque
    el veto de la unidad se los comía. Costó un ciclo encontrarlo.
  - Límite conocido: para unidades que no son de voltaje MNE aplica el prefijo
    SI de forma inconsistente —escaló `µS` y no `uS`— así que la etiqueta de un
    canal auxiliar con prefijo puede quedar corrida en un factor. Los canales
    que el programa mide son de voltaje y para ésos la conversión es exacta.
- [x] **`psglab/readers/scoring_reader.py`** · ~~3 stubs~~ · V3_F "Importación"
  - Test: `tests/test_scoring_reader.py`, **29 tests en verde**. El archivo lo
    escribe el propio test, así que no necesita `data/`.
  - `detect_nomenclature()` lee la cabecera que escribirá
    `exporters/scoring_txt.py::format_header()`. Acepta el nombre corto y el
    largo, sin distinguir mayúsculas: el archivo lo puede haber escrito una
    persona.
  - **La cabecera gana sobre el parámetro**, y sólo deja de buscarla al llegar
    a la primera línea de datos: un comentario a mitad del archivo cambiaría la
    interpretación de las líneas que ya se leyeron.
  - Hizo falta `nomenclature.stage_from_code()`, la inversa de `stage_code()`
    que no existía. Vive al lado de su gemela y **deriva** la correspondencia de
    `stages_of()`: así el código 4 (S4) y el 6 (MT) se rechazan solos en AASM,
    que no los tiene.

### Lo que la auditoría dejó medido para este hito

**Las cuatro quedaron resueltas.** Se anota qué se decidió, y sobre todo qué
encontró la ejecución real, porque en dos casos difiere de lo que la auditoría
había previsto leyendo el código.

- [x] **V3_F entra por su propio punto de entrada**, no por el despacho de
      formatos. `read_scoring()` no es un `Reader` porque no produce un
      `Recording`, así que no tiene dónde encajar en `read_recording()`.
      Se resolvió además el síntoma concreto: un EDF **sin ninguna señal** —el
      hipnograma— eleva `UnreadableFileError` mandando al importador de scoring,
      en vez de dejar que `Recording` diga "no tiene ningún canal" y le haga
      creer al investigador que su archivo está roto. El diálogo que lo ofrece
      se construye en el hito 6.
- [x] **`Channel.original_sampling_rate` agregado**, con default `None` para
      no romper ningún constructor existente, y poblado por los dos lectores.
      Hizo falta por un motivo distinto del previsto: no hubo que remuestrear
      —MNE unifica solo— pero justamente por eso el dato se perdía sin que nada
      avisara.
- [x] **Quedó sin efecto, y no por casualidad.** `EDF Annotations` no hay que
      descartarlo: **MNE ya lo excluye solo** y lo convierte en
      `raw.annotations`. Y `Event marker` **no se descarta**, porque es un canal
      legítimo que el pliego pide mostrar. Como no se saca ninguno, los canales
      se construyen con `enumerate` sobre la lista que devuelve MNE y los
      índices son contiguos por construcción.
- [x] **Resuelto, y la auditoría se había quedado corta.** Era cierto que
      `"Temp rectal"` salía EEG por el prefijo `"t"`, pero al probar los siete
      nombres reales apareció el error inverso y más caro: **`"EEG Fpz-Cz"` y
      `"EEG Pz-Oz"` no coincidían con nada** —empiezan con `"e"`— y caían en
      OTHER. Son la señal que se scorea.
      Se compara **token por token** en vez de por prefijo del nombre entero, y
      el parámetro `unit` por fin se usa, como segunda línea de defensa. Los
      siete nombres reales están en `tests/test_channel_types.py`.

---

## Hito 5: Exportadores

> **Medido en la auditoría:** `stage_durations_seconds()` y
> `scored_time_seconds()` **no pueden ser correctas con la firma que tienen**.
> Reciben `scoring` y `window_seconds`, y con eso sólo saben multiplicar; para
> la **última ventana, que casi siempre está incompleta**, hace falta
> `window_duration()`, que pide `n_samples` y `sampling_rate`. Son las que
> alimentan la tabla de tiempos de `Informacion.txt`, así que el error se
> publica. Cambiar la firma es parte de este hito, no de otro.

- [x] **`psglab/exporters/statistics.py`** · ~~6 stubs~~ · alimenta V3_F
      "Archivo de salida"
  - No escribe archivos: por eso se puede testear sin tocar el disco.
  - Test: **falta**, se extiende `tests/test_exporters.py` al reactivarlo.
  - **`stage_durations_seconds()` cambió de firma**, que era lo que la auditoría
    pedía: recibe `n_samples` y `sampling_rate` y suma
    `windows.window_duration()` ventana por ventana. Verificado sobre un
    registro de 4 ventanas cuya última dura 10 s: la tabla por fase suma
    exactamente la duración real, y multiplicar la cuenta le habría atribuido
    20 s de más a la fase de esa ventana.
  - **`scored_time_seconds()` no se tocó**, y ahí la auditoría se equivocaba: su
    docstring ya declara que contar ventanas completas es deliberado. Sobre el
    mismo caso da 120 s contra 100 s de duración real. Son dos magnitudes, y
    `Informacion.txt` publica las dos rotuladas distinto.
  - `episode_metrics()` tampoco cambia: mide la estructura del sueño, no un
    total publicado.
- [x] **`psglab/exporters/scoring_txt.py`** · ~~3 stubs~~ · V1_F "Archivo de salida"
  - Los 7 tests que ya estaban escritos en `tests/test_exporters.py` pasaron
    **sin tocarlos**: eran la especificación del formato, con el ejemplo textual
    del pliego.
  - Las dos variantes siguen alcanzables desde `config`, y hay un test por cada
    una que lo verifica en vez de confiar en que nadie escriba un `if`.
  - `format_header()` escribe el **nombre corto** del enum: "# AASM", "# RK".
    `detect_nomenclature()` acepta también el largo, así que el contrato cierra
    por los dos lados.
- [x] **`psglab/exporters/annotations_txt.py`** · ~~2 stubs~~ · V2_F "Archivo de
      salida"
  - El índice de los puntos sale de `config.ANNOTATION_SAMPLE_BASE`, no se
    escribe a mano.
  - El separador dentro de una etiqueta **se reemplaza, no se escapa**: escapar
    obliga a que todo programa que lea el archivo conozca la convención, y este
    archivo existe para que lo consuman análisis de terceros. Perder una barra
    en un nombre es barato; una línea de cuatro campos rompe el parseo de la
    noche entera. El salto de línea recibe el mismo trato.
- [x] **`psglab/exporters/information_txt.py`** · ~~3 stubs~~ · V3_F "Archivo de
      salida"
  - Las secciones que no correspondan se omiten con una explicación, no con
    ceros.
  - Publica **las dos** medidas de tiempo rotuladas distinto, que es lo que su
    docstring pedía: la duración real del registro y el tiempo que abarcan las
    ventanas.
  - Agrega una sección de canales que **avisa cuándo un canal venía a otra
    frecuencia**. Sin eso, un canal de 1 Hz sobremuestreado por MNE se leería
    como si tuviera la resolución del EEG.
  - `format_duration()` no cumplía su propio ejemplo en la primera versión: le
    faltaba el cero adelante de los segundos. Hay un test parametrizado contra
    el ejemplo del docstring.
- [x] Test de los cuatro: `tests/test_exporters.py`, **34 tests en verde**, sin
      `pytestmark`. Con esto la suite baja de 14 salteados a 7: los que quedan
      son los de `test_occupancy`, del hito 7.
- [x] **Test de ida y vuelta de la cabecera**, que cruza este hito y el 4:
      exportar, releer sin pasar la nomenclatura, y verificar que sale la misma.
      Parametrizado sobre las dos. Se verifica además que las fases y los
      arousals sobrevivan el viaje, porque que la cabecera vuelva no alcanza.

> **Cerrado el hito 5, el programa hace su trabajo entero desde un script, sin
> interfaz.** Quedó como test y no como script suelto —
> `test_el_programa_hace_su_trabajo_entero_desde_un_script`— para que corra solo
> en cada push: lee el EDF real, scorea, exporta los tres archivos y los relee.
> Se saltea sin `data/`, con el mismo patrón del hito 4.

---

## Hito 6: Interfaz

Primera vez que el programa se puede abrir. La capa se mantiene delgada y toda
la regla vive en `core/`.

> **Acotado en este hito: `ui/` sí lleva algunos tests.** La regla de "sin tests
> unitarios" se había fijado con la carpeta vacía. Al escribirla se vio que tres
> piezas **no dibujan nada** y son justo donde algo se rompe callado: las teclas
> de fase de `shortcuts.py`, las posiciones de `grid.py` y —sobre todo— los tres
> conversores de `signal_view.py`, el único lugar del programa que traduce entre
> píxeles, segundos, fracción de ventana y muestras. Confundirlos da números
> plausibles y equivocados. Ésos se testean, con una `QApplication` sin pantalla.
> **El dibujo sigue sin testear**, y esa parte de la regla no cambió.

> **Resuelto: `Session` avisa sola.** Gana `add_window_listener()`, y las tres
> puertas que cambian de ventana avisan desde adentro. El hito 7 volvió urgente
> la decisión: hay **tres** herramientas que dependen de enterarse —la ocupación
> borra sus líneas (V5_F), la Übersicht se recentra y el histograma mueve su
> indicador— y dejar esa obligación en la única capa sin tests significaba que
> un olvido las rompía a las tres sin que nada fallara de forma visible.
>
> No avisa cuando la ventana **no cambió**: llegar al final con la flecha
> derecha, o hacer clic en el histograma sobre la ventana actual, le borraría al
> usuario las líneas que acaba de dibujar sin que se haya movido a ningún lado.

- [x] **`psglab/ui/grid.py`** · ~~4 stubs~~ · V1_P, V2_F "Diseño de la interfaz"
  - Test: `tests/test_grid.py`, **13 tests en verde**. No dibuja píxeles:
    calcula posiciones, así que se puede afirmar sobre la grilla sin mirar una
    pantalla.
  - Las posiciones **se multiplican, no se acumulan**: sumar 0,5 sesenta veces
    corre la última línea del borde, que es el mismo error que `core/windows.py`
    documenta para las ventanas.
- [x] **`psglab/ui/signal_view.py`** · ~~13 stubs~~ · V1_P, V2_P, V4_F, V5_F
      "Visualización" (+ el dibujo de V3_P), V1_F "Anotación de la señal"
  - Test: `tests/test_signal_view.py`, **19 tests en verde**. **El dibujo no se
    testea**; sí los tres conversores, que es de donde salen las unidades con
    las que trabajan todas las herramientas.
  - Los píxeles de los bordes se le **preguntan al `ViewBox`** en vez de
    escribirse a mano: el gráfico tiene márgenes y ejes, así que el píxel 0 del
    widget no es el segundo 0 de la ventana.
  - Los dos conversores derivados son píxel→segundos y después `core.windows`:
    la aritmética entre unidades no gráficas no se reimplementa acá.
  - Un píxel fuera del área de dibujo **se recorta**. Sin eso, del margen del
    gráfico sale una muestra fuera del registro.
  - La banda de amplitud se dibuja con la escala de **su** canal, que es el dato
    que el hito 7 le agregó a `BandOverlay`: por eso 75 µV miden en pantalla lo
    mismo que 75 µV de la onda.
- [x] **`psglab/ui/navigation.py`** · ~~5 stubs~~ · V1_F "Navegación"
  - **Es el único lugar donde se suma el 1** para mostrar la ventana en base 1.
    Adentro son base 0 de punta a punta; convertir al mostrar y no antes evita
    que la cuenta se corra en algún camino intermedio.
  - Los botones **piden, no navegan**: emiten la señal y quien la escucha
    decide. La regla de qué ventana existe sigue en `core/`.
- [x] **`psglab/ui/channel_selector.py`** · ~~6 stubs~~ · V3_P, V4_F
      "Visualización"
  - Agrupa por clase y permite mostrar u ocultar **toda una clase de una vez**,
    que es el atajo que pide el pliego para los EOG y los EMG.
  - Los canales se devuelven en el **orden del archivo** y no en el del árbol:
    el árbol los agrupa por clase, y el visualizador los apila como se grabaron.
  - Visibilidad y selección son ejes independientes, igual que en `Session`.
- [x] **`psglab/ui/scoring_panel.py`** · ~~3 stubs~~ · V1_F, V2_F, V3_F
      "Scoring"
  - Los botones salen de `stages_of()`, igual que los atajos de teclado y por el
    mismo motivo.
  - **Reflejar no es elegir.** Mientras el panel muestra el scoring de la
    ventana a la que se navegó, los controles no emiten: si lo hicieran, llegar
    a una ventana ya scoreada la volvería a scorear y llegar a una sin scorear
    borraría lo que hubiera.
  - El aviso de que cambiar de nomenclatura pierde información **no se da acá**:
    el panel emite y la ventana principal decide si pregunta, porque el panel no
    conoce el scoring.
- [x] **`psglab/ui/shortcuts.py`** · ~~3 stubs~~ · flechas y teclas de fase
  - Test: `tests/test_shortcuts.py`, **17 tests en verde**. Las dos funciones que
    importan se llaman **sin ninguna `QApplication`**.
  - Los de fase salen de la nomenclatura: **la tecla se deriva del código de la
    fase**, así que una fase nueva trae su tecla sola. Hay un test que verifica
    que no choquen con los fijos, que es el motivo por el que todos los atajos
    viven en un solo archivo.
  - `FIXED_SHORTCUTS` es lo que lee el usuario y `ACTIONS` el cableado, separados
    para que cambiar un texto de ayuda no desconecte una tecla; un test exige que
    cubran las mismas teclas.
- [x] **`psglab/ui/main_window.py`** · ~~10 stubs~~ · V4_F "Archivo de salida"
  - Conecta, no implementa. Acá se cablean a mano los callbacks de las
    herramientas, que no usan señales de Qt: `on_changed` lleva los overlays a
    la pantalla y `on_window_requested` lleva el clic del hipnograma a la
    sesión. **Se asignan sobre la instancia y nunca sobre la clase**, o quedarían
    como método ligado y la llamada pasaría un argumento de más.
  - La barra de herramientas se arma recorriendo `available_tools()`, así que
    una herramienta nueva aparece sola sin tocar este archivo.
  - V4_F son **tres** acciones de exportación separadas, no un "exportar todo":
    el pliego pide poder elegir cuál de los tres archivos se escribe.
  - `_show_error()` es el único lugar que convierte un `PsgLabError` en un
    cartel: el mensaje en español arriba y `details` en la parte desplegable.
- [x] **`psglab/app.py`** · ~~2 stubs~~ · infraestructura
  - Con esto `python main.py` deja de terminar en `NotImplementedError`.
  - Carga los dos registros —herramientas y lectores— **antes** de construir la
    ventana: la barra y el filtro del diálogo de apertura se arman recorriéndolos.

---

## Hito 7: Herramientas

Las seis son independientes entre sí: **se pueden repartir**. Todas se pueden
testear sin GUI, porque `Tool` y `ViewerTool` no heredan de `QObject`.

Antes de escribir una, leé [`tools/README.md`](../psglab/tools/README.md): el
sistema de coordenadas de `ViewerTool` (segundos y µV) no es el de `Tool`
(coordenadas propias del panel).

> **Resuelto:** `BandOverlay` lleva ahora `channel_name`. La otra salida que
> planteaba la auditoría —definir la banda en coordenadas de pantalla—
> contradecía el pliego: en píxeles deja de medir microvoltios, y adaptarse a la
> amplitud elegida por el usuario es todo el sentido de la herramienta (V1_F).
> Se agregó antes de que `signal_view.py` exista, que era el momento barato.

- [x] **`psglab/tools/amplitude_band.py`** · ~~5 stubs~~ · V1_F "Herramienta de
      amplitud" · `ViewerTool`
  - Test: `tests/test_amplitude_band.py`, **23 tests en verde**. Los 75 µV salen
    de `config.AMPLITUDE_BAND_UV`, y también el texto que ve el usuario en la
    barra: un literal ahí le mentiría el día que alguien cambie la constante.
  - **Resuelve el hallazgo de la auditoría sobre `BandOverlay`**, que no llevaba
    canal. Ver más abajo.
  - El canal sobre el que va la banda es **el seleccionado**, que es lo que pide
    el pliego al decir que se adapte a "la amplitud de la señal elegida por el
    usuario". Sin ninguno seleccionado cae al primero visible, para que la
    herramienta sirva apenas se abre un registro.
- [x] **`psglab/tools/occupancy.py`** · ~~13 stubs~~ · V1_F–V5_F "Ocupación" ·
      `ViewerTool`
  - Test: `tests/test_occupancy.py`, **29 tests en verde**, sin `pytestmark`.
    Los 7 que ya estaban escritos —los ejemplos numéricos literales del
    pliego— pasaron **sin tocarlos**. **Con esto la suite queda sin ningún
    salteado.**
  - La superposición se cuenta dos veces, de `config`, y hay un test de cada
    variante: revertir la decisión del hito 0 sigue siendo cambiar una línea.
    **El total puede pasar del 100 % y eso es lo buscado.**
  - **`x` se guarda en fracción y `y` en microvoltios**, y los dos ejes no usan
    la misma unidad a propósito: pasar `y` a fracción del alto exigiría un canal
    que `SegmentOverlay` no lleva, y como `y` no entra en la medición sería
    pagar imprecisión a cambio de nada.
  - Hay un test que fija la conversión de segundos a fracción: sin ella una
    línea de 15 segundos informaría 1500 %, que es un número plausible y
    equivocado.
  - Borrar una línea compara la altura del clic con la de la línea **en esa
    posición horizontal**, interpolando. Con un rectángulo envolvente, una
    diagonal larga se borraría desde muy lejos de donde está dibujada.
- [x] **`psglab/tools/magnifier.py`** · ~~9 stubs~~ · V1_F, V2_F "Lupa" ·
      `ViewerTool`
  - Test: `tests/test_magnifier.py`, **25 tests en verde**. El contador se
    testea sin dibujar nada, que es el motivo de que la herramienta no herede
    de `QObject`.
  - **No dibuja antes de que el mouse entre al visualizador**: un círculo en una
    posición inventada aparecería al activarla, lejos de donde el usuario mira.
  - El botón derecho descuenta y **el contador no baja de cero**: una cuenta de
    picos negativa no significa nada.
  - Desactivarla **conserva la cuenta**. El usuario apaga la lupa para ver la
    señal sin el círculo encima y vuelve; reiniciar ahí le perdería el trabajo.
- [x] **`psglab/tools/overview.py`** · ~~6 stubs~~ · V1_F, V2_F, V3_F
      "Übersicht" · `Tool`
  - Test: `tests/test_overview.py`, **23 tests en verde**. La cantidad de
    vecinas es configurable y asimétrica, y se recorta contra los bordes del
    registro: en la primera ventana no hay anterior.
  - **`_draw_window()` no dibuja: describe.** `tools/` no conoce Qt, así que
    arma el dato que la interfaz pinta. Hizo falta agregar `windows()`, porque
    sin un accesor el panel era de sólo escritura y no había con qué dibujarlo.
- [x] **`psglab/tools/histogram.py`** · ~~7 stubs~~ · V1_P, V2_F, V3_F, V4_F
      "Histograma" · `Tool`
  - Test: `tests/test_histogram.py`, **28 tests en verde**.
  - Su `on_click(x_fraction)` es propio: un clic cae en una ventana de la noche,
    no en un segundo de la ventana actual. **El borde derecho es el caso que se
    rompe solo**: `int(1.0 * n)` da una ventana que no existe, así que se
    recorta.
  - Pedir el eje en hora real sobre un registro que no informa su horario de
    inicio **falla en vez de inventarlo**: el investigador leería el eje como si
    fuera real.
  - Igual que el Übersicht, hizo falta un accesor —`bars()`— para que la
    interfaz tenga qué dibujar.
- [x] **`psglab/tools/annotator.py`** · ~~9 stubs~~ · V1_F "Anotación" ·
      `ViewerTool`
  - Test: `tests/test_annotator.py`, **18 tests en verde**.
  - **La conversión a muestras es lo que más importa** y tiene su test: en la
    ventana 1, el segundo 5 es la muestra 3500. Escribir la cuenta a mano deja
    la anotación en la ventana de al lado cuando la frecuencia no es redonda, y
    nada lo hace visible: la banda se dibuja igual, sólo que en otro lado.
  - **La herramienta no abre ningún diálogo**, porque no conoce Qt. Deja el
    tramo en `pending_selection_samples` y avisa; la ventana principal pregunta
    la clase y llama a `create_annotation()`. Es lo que permite testear el gesto
    entero sin abrir una ventana.
  - Las anotaciones viven en el `AnnotationSet` de la sesión y no en la
    herramienta: es el gesto, no el dato. Por eso desactivarla no borra nada,
    pero sí descarta una selección a medias.

`tools/base.py` y `tools/registry.py` **ya están implementados** y no tienen
stubs, pero eso no es lo mismo que estar verificados:

- [x] **`psglab/tools/registry.py` y `psglab/tools/base.py`** · 0 pendientes ·
      `tests/test_registry.py`, **20 tests en verde**
  - Va **antes** que las seis herramientas y no después: es el mecanismo del que
    cuelgan todas, y si estuviera roto el síntoma aparecería en seis lugares y
    en ninguno se vería la causa.
  - Quedan fijados el rechazo por nombre repetido, el autodescubrimiento de las
    seis, que cargar dos veces no duplique, y que los métodos de evento **no
    hagan nada por defecto** en vez de elevar, que es decisión de
    `ARQUITECTURA.md`.
  - También que `on_changed` se asigne **sobre la instancia y no sobre la
    clase**: en la clase Python lo convertiría en un método ligado y la llamada
    pasaría `self` de más. Lo advertía un comentario de `base.py` y ahora hay un
    test que lo sostiene.
  - Y que sólo sean exclusivas las tres que compiten por el mouse. Marcar
    exclusivo un panel apagaría al anotador cada vez que el usuario mira el
    histograma.

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
