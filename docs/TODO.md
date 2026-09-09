# TODO — scorer de polisomnografía

La cola de trabajo del proyecto. **Este archivo es el único lugar que dice qué
está hecho y qué falta**; `TRAZABILIDAD.md` dice *dónde* va cada requisito y no
lleva estado, para que no haya dos fuentes que se desincronicen.

Quedan **0 stubs** (`raise NotImplementedError`) en 0 módulos. Con el hito 17
cierra la **Parte 2**, y el 18 atendió lo que ése había dejado medido y sin
tocar: **los hitos 0 a 18 están cerrados** y ningún módulo de `psglab/` eleva
`NotImplementedError`.

Con el **[hito 19](#hito-19-lo-que-la-interfaz-no-consumía)** cierran los
**caminos muertos**, que no son stubs y por eso `contar_stubs()` no los veía:
tres funciones públicas de `analysis/` que la interfaz no consumía. Son
**veintiún hitos**, del 0 al 20, que son las filas de la tabla de progreso, y
están todos cerrados. El **[hito 20](#hito-20-la-red)** es la red que evita que
esto vuelva a pasar: tres chequeos automáticos sobre lo que hasta acá se
encontraba a mano.

**La Parte 1 está terminada**, con los hitos 0 a 9 cerrados. Sus 34 requisitos
se pueden usar desde el programa corriendo, no sólo desde sus módulos, que es la
distinción que este resumen no puede dar y que costó el hito 9.

Hasta el hito 10 este archivo **excluía la Parte 2 a propósito** y sus cuentas
la ignoraban activamente. Cerrada la Parte 1, el TODO pasa a ser la cola de la
Parte 2: era eso o estrenar una segunda fuente de estado, que es justo lo que
este archivo existe para evitar.

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
los tests en los tres sistemas operativos, los chequeos de consistencia de
`tests/test_consistencia.py` y la verificación de licencias.

**Pero no corre en cualquier push.** `ci.yml` filtra los dos eventos por rama
—`branches: [Add, Master]`—, así que un push a una rama de trabajo **no dispara
nada** hasta que se abra la pull request contra alguna de esas dos. En el día a
día el único control es `python -m pytest` local, y conviene correrlo entero: el
chequeo de las cuentas de tests se saltea si se le pasa un archivo suelto.

Esto no es teórico y ya costó caro: el [hito 17](#hito-17-cierre-de-la-parte-2)
encontró que los PR #19 y #20 estaban apilados sobre ramas de trabajo y **tenían
cero checks**. Dos de los cuatro hitos que quedaban sin mergear nunca se habían
verificado fuera de una máquina Windows. Y reapuntar un PR no alcanza para
disparar el CI: `pull_request` corre con `opened`, `synchronize` y `reopened`, y
cambiar la base es `edited`; hay que cerrarlo y reabrirlo.

Con la pull request abierta sí quiere decir que **no hace falta acordarse** de
que las cuentas de este archivo cuadren, ni de que los enlaces no se rompan, ni
de borrar el `pytestmark` al terminar un módulo: si algo de eso queda mal, el
pull request falla.

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
| [8. Cierre](#hito-8-cierre-de-la-parte-1) | — | 0 | ✅ cerrado |
| [9. Lo que la interfaz no consume](#hito-9-lo-que-la-interfaz-no-consume) | — | 0 | ✅ cerrado |
| [10. Cimientos de la Parte 2](#hito-10-cimientos-de-la-parte-2) | — | 0 | ✅ cerrado |
| [11. Derivar y re-referenciar](#hito-11-derivar-y-re-referenciar) | — | 0 | ✅ cerrado |
| [12. Filtración](#hito-12-filtración) | — | 0 | ✅ cerrado |
| [13. PSD](#hito-13-psd) | — | 0 | ✅ cerrado |
| [14. Complejidad y conectividad](#hito-14-complejidad-y-conectividad) | — | 0 | ✅ cerrado |
| [15. ICA](#hito-15-ica) | — | 0 | ✅ cerrado |
| [16. Impedancia](#hito-16-impedancia) | — | 0 | ✅ cerrado |
| [17. Cierre de la Parte 2](#hito-17-cierre-de-la-parte-2) | — | 0 | ✅ cerrado |
| [18. Escala](#hito-18-escala) | — | 0 | ✅ cerrado |
| [19. Lo que la interfaz no consumía](#hito-19-lo-que-la-interfaz-no-consumía) | — | 0 | ✅ cerrado |
| [20. La red](#hito-20-la-red) | — | 0 | ✅ cerrado |
| | **0** | **0** | |

**La columna de stubs nunca midió el hito 9**, y por eso el hito 9 existió: sus
seis ítems eran código escrito que nadie llamaba. `contar_stubs()` cuenta
`raise NotImplementedError`, no caminos muertos, y con esa medida los hitos 6 y
7 se dieron por cerrados con la mitad de la interfaz sin conectar.

### Los tres cortes que importan

- **Al cerrar el hito 3** toda la capa de negocio funciona y se puede testear
  sin abrir una ventana.
- **Al cerrar el hito 5** el programa hace su trabajo completo desde un script
  —leer un EDF, scorear, exportar los tres archivos— **todavía sin interfaz
  gráfica**. Es el pago concreto de que `core/` no importe `ui/`.
- **Al cerrar el hito 6** `python main.py` abre algo usable por primera vez.
  Ya no termina en `NotImplementedError`. Usable no es completo: lo que quedó
  sin cablear es el [hito 9](#hito-9-lo-que-la-interfaz-no-consume).

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

- [ ] **Origen de las impedancias.** La pregunta se acotó al implementar el
  [hito 16](#hito-16-impedancia): las tres vías están hechas, así que lo único
  que falta saber es **cuál usa el laboratorio**, y de eso depende qué se le
  ofrece primero al investigador.
  - **BrainVision las trae**, en la sección `[Comment]` del `.vhdr` y ya en kΩ.
  - **EDF no puede**: el estándar no tiene el campo, ni en EDF ni en EDF+. Para
    esos registros la única vía es el archivo aparte o la carga a mano.
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
  - Test: `tests/test_errors.py`, **14 tests en verde**.
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
  - Test: `tests/test_session.py`, **76 tests en verde**. Navegación y amplitud
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
  - Test: `tests/test_readers.py`, **45 tests en verde**, que cubre este módulo
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
  - Test: `tests/test_signal_view.py`, **32 tests en verde**. **El dibujo no se
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
  - Test: `tests/test_occupancy.py`, **34 tests en verde**, sin `pytestmark`.
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

Correr esta lista fue lo que destapó el [hito 9](#hito-9-lo-que-la-interfaz-no-consume):
seis requisitos hechos en `tools/` y sin consumir en `ui/`. Se cerró primero
aquél y después éste, que es el orden que corresponde: la lista de comprobación
no puede tildarse a sí misma.

- [x] **Ningún test salteado por falta de implementación.** ~~Ningún test
      salteado.~~ El ítem decía eso y no se podía cumplir: los quince tests que
      leen el registro real de `data/` se saltean en el CI, y **tienen que
      hacerlo**, porque el `.gitignore` excluye datos de participantes a
      propósito. La distinción que importa es la que ya hace
      `test_ningun_modulo_terminado_tiene_su_test_salteado`: ningún módulo
      terminado puede tener su test apagado.
      ```bash
      python -m pytest -rs
      ```
      El hito agregó además un BrainVision **sintético** (`conftest.py`,
      `brainvision_sintetico`), para que el lector se ejercite también donde no
      hay registros: antes no corría en ninguna de las seis combinaciones del
      CI.
- [x] **Ningún stub de Parte 1.** Da 0.
      ```bash
      grep -r "raise NotImplementedError" psglab --include=*.py | grep -v "/analysis/" | wc -l
      ```
- [x] **Los 34 requisitos de la Parte 1 de
      [`TRAZABILIDAD.md`](TRAZABILIDAD.md) están cerrados**, y cada fila apunta
      al archivo correcto. Los seis que faltaban fueron el hito 9.
      - Son 34 pares (sección, ID), no 34 cadenas distintas: `V1_F` solo
        aparece en nueve secciones. Los archivos que nombran las filas existen
        todos y los IDs coinciden con los docstrings en las dos direcciones.
      - **Revisar que la fila apunte al archivo correcto no alcanza**: las seis
        que faltaban apuntaban al archivo correcto y el requisito no funcionaba
        igual, porque la otra mitad no existía. Lo que cerró el hito fue
        recorrer cada requisito **por la ventana**, que es lo que hoy hace
        `tests/test_entrega.py`.
- [x] **Las ambigüedades de la Parte 1, documentadas** en `EXPLICACION.txt`
      sección 8. ~~y los módulos que decían "PENDIENTE DE DEFINICIÓN CON EL
      CLIENTE" ya no lo dicen.~~ Acotado a la Parte 1: la única marca que queda
      es la de `psglab/analysis/impedance.py`, que es de la Parte 2 y sigue
      abierta con razón, así que el ítem entero era intildeable.
- [x] **Licencias verificadas**, sin ninguna GPL. El resultado quedó como
      bloque fechado en [`ARQUITECTURA.md`](ARQUITECTURA.md).
      ```bash
      python -m piplicenses --format=markdown --order=license
      ```
      ~~`pip-licenses --format=markdown`~~ era la forma de lanzador, que
      `CLAUDE.md` y `ARQUITECTURA.md` explican que no hay que usar: depende de
      que `Scripts/` esté en el PATH y de que nadie haya movido la carpeta.
- [x] **El programa se abre, scorea una noche y exporta los tres archivos**, y
      ahora es repetible: `tests/test_entrega.py`. La parte de anotar está
      marcada `xfail` apuntando al hito 9, así que el día que se cierre, la
      suite avisa sola.

---

## Hito 9: Lo que la interfaz no consume

Encontrado al correr la lista del hito 8, revisando fila por fila la
trazabilidad. **La capa `tools/` está completa y testeada, y falta la mitad de
`ui/` que la consume**: seis requisitos del pliego existen como modelo, tienen
sus tests en verde, y no hay ningún camino en el programa que los ejecute.

Ni el TODO ni ningún README lo registraban. Los hitos 6 y 7 se dieron por
cerrados porque sus módulos no tenían stubs, y "sin stubs" no es lo mismo que
"conectado": es exactamente el hueco que `contar_stubs()` no puede ver.

- [x] **`psglab/ui/main_window.py`** · el cableado del anotador · V1_F de
      "Anotación de la señal"
  - `annotator.py` deja el tramo en `pending_selection_samples` y espera que la
    ventana pregunte la clase y llame a `create_annotation()`. **Nadie la
    llama**: cero referencias en `psglab/ui/`. En el programa corriendo se puede
    arrastrar una selección y no pasa nada.
  - Arrastra a V2_F de "Archivo de salida": `Anotaciones.txt` se exporta
    siempre vacío, porque no hay forma de crear una anotación.
- [x] **Un panel para la Übersicht** · V1_F, V2_F, V3_F de "Übersicht"
  - `OverviewTool` no se menciona en `psglab/ui/`, y ni el layout ni el
    diagrama del README tienen una zona para ella. El modelo está entero
    —`OverviewWindow.is_current`, `set_span()` con `before` y `after`
    independientes— y no lo dibuja nadie. `set_size()` (V2_F) tampoco se llama.
- [x] **Mostrar el porcentaje de ocupación** · V3_F de "Ocupación"
  - `line_percentage()` y `total_percentage()` calculan bien y no los lee
    nadie. El cálculo (V2_F, V4_F) está cerrado; lo que falta es mostrarlo.
- [x] **La lupa tiene que ampliar** · V1_F, V2_F de "Lupa"
  - `MagnifierTool` publica `CircleOverlay(radius_seconds, zoom)` y
    `signal_view._dibujar_overlay()` lo pinta como un `ScatterPlotItem` de
    tamaño fijo, **descartando los dos campos**. El círculo sigue al mouse y no
    amplía nada. El contador de picos (`click_count`) tampoco se muestra.
- [x] **El eje del histograma** · V2_F del histograma
  - `set_time_axis()` prende un booleano que nadie lee, y
    `_redraw_histogram()` grafica `range(len(barras))`: índices base 0, sin
    ticks y sin `window_to_clock_time()`. Falta el eje en hora real **y** el de
    1 a VENMAX. De paso viola la regla de base 1 al mostrar.
- [x] **La `y` que reciben las herramientas está en la unidad equivocada**
  - `main_window.eventFilter()` pasa `vista.mapSceneToView(...).y()`, que son
    unidades del gráfico, y `ViewerTool.on_mouse_press` documenta
    **microvoltios**. Después `signal_view._a_carril()` vuelve a dividir por
    `scale_uv`. Hay un comentario al lado afirmando que ninguna herramienta usa
    la `y`, y la usan tres: la banda de amplitud, la ocupación y la lupa.
  - El síntoma peor es de la ocupación: `TOLERANCIA_DE_CLIC_UV = 10.0` se
    compara contra un rango de carril de 0 a 1, así que **cualquier clic dentro
    del rango horizontal de una línea la borra** en vez de empezar otra.
  - No afecta la medición del porcentaje, que proyecta sobre `x`.

> **Cómo se encontró, y por qué no lo vio nadie antes.** La corrida de punta a
> punta del hito 6 anotó un evento **llamando a la herramienta directamente
> desde el script**, no por la interfaz, así que el hueco no se manifestó. Es el
> mismo error de método que la auditoría describe para la documentación:
> verificar la pieza en vez del camino.

---

# Parte 2 — Módulo de análisis de bioseñales

Ocho módulos, 26 stubs, y las firmas y los docstrings ya escritos desde el
esqueleto. Van **ordenados por dependencias reales**, igual que la Parte 1.

**Cada análisis se lleva hasta la pantalla, no hasta su módulo.** Es la lección
del [hito 9](#hito-9-lo-que-la-interfaz-no-consume): seis requisitos con sus
tests en verde que la interfaz no consumía, y `contar_stubs()` no puede ver un
camino muerto. Un hito de la Parte 2 no se cierra con el módulo terminado.

> **Pregunta abierta con el cliente, anotada antes de empezar.** Los IDs de
> "Filtración" saltan de **V1_F a V5_F**: no hay V2_F, V3_F ni V4_F en ningún
> documento ni en ningún docstring. La primera auditoría lo marcó como
> "requiere consultar el pliego" y sigue sin resolverse. Pueden ser tres
> requisitos que el proyecto nunca registró. Lo que **sí** está especificado no
> está en duda, así que el riesgo es trabajo adicional y no trabajo a rehacer;
> por eso los hitos 11 y 13 van antes que el 12.

---

## Hito 10: Cimientos de la Parte 2

Sin stubs: es la infraestructura que la Parte 2 necesita y que no existía. Se
hizo de una vez y no módulo por módulo.

- [x] **La maquinaria de cuentas de este archivo**, que excluía la Parte 2.
      `stubs_de_la_parte_1()` filtraba `analysis/`, el regex de la tabla exigía
      un hito de **un solo dígito** —un "hito 10" no matcheaba y sus stubs
      desaparecían de la suma en silencio— y el chequeo de "todo módulo tiene
      test" también la salteaba.
- [x] **`analysis` y `tools` en `CAPAS_SIN_INTERFAZ`.** La regla de que no
      importen Qt estaba escrita en tres documentos y no la verificaba nadie.
- [x] **`test_contratos.py` extendido a `analysis/`.** Encontró tres fugas en
      el primer módulo que le tocó: `to_raw`, `from_raw` y `unidad_de_salida`
      dejaban salir `AttributeError` crudo, que la ventana principal no atrapa.
      La exigencia aparece módulo por módulo, porque los que tienen stubs se
      saltean.
- [x] **`registro_sintetico`**, la fixture que faltaba. Ninguna devolvía un
      `Recording` y **todas** las funciones de `analysis/` reciben uno.
      Verificada con Welch: los cuatro canales dan su pico donde la fixture
      promete.
- [x] **`requirements-analysis.txt` en el job de tests del CI.** Verificado en
      seco que resuelve: 14 paquetes, sin conflicto y sin degradar numpy.
- [x] **El adaptador `Recording` ↔ `mne.io.Raw`**
      (`psglab/analysis/mne_bridge.py`). No existía y lo necesitan tres
      módulos: MNE se usaba en una sola dirección, `Raw → Recording`, en los
      dos lectores.
  - **La unidad era el problema.** MNE trabaja en volts y el `Recording` en
    microvoltios, pero **sólo se escala lo eléctrico**: `Channel.unit` es la
    fuente de verdad, y un termómetro multiplicado por un millón no da un error
    visible, da una temperatura absurda que alguien lee como señal.
  - **Copia explícita de los datos**, que resuelve la primera decisión
    transversal: `get_segment()` devuelve un array de sólo lectura y MNE
    escribe sobre el buffer que recibe. Sin copiar, filtrar reventaba con un
    error de numpy tres capas más abajo.
  - Ida y vuelta devuelve lo mismo, que es la propiedad de la que hereda su
    corrección todo lo que se apoye acá.
  - Test: `tests/test_mne_bridge.py`, **14 tests en verde**.
- [x] **La pregunta del hueco V2_F–V4_F**, escrita en
      [`TRAZABILIDAD.md`](TRAZABILIDAD.md) junto a la de las impedancias.

Dos decisiones transversales **no se toman acá a propósito**, porque tomarlas
sin nada de qué colgarlas sería especular. Se toman donde se necesitan por
primera vez y las demás las copian:

- **Qué se hace con la última ventana incompleta** → hito 13, que es el primero
  que recorre ventanas. `window_to_samples()` devuelve un final posterior al
  registro y `get_segment()` acorta el tramo **en silencio**; la fixture da 20
  ventanas exactas, así que hay que escribir el caso a propósito.
- **Las excepciones que faltan** → cada módulo trae la suya al terminarse.
  `utils/errors.py` tiene una sola de análisis, `InvalidFilterError`, y 21 de
  los 26 stubs no declaran ningún `Raises:`. `tests/test_errors.py` las cubre
  solas con `inspect.getmembers`.

---

## Hito 11: Derivar y re-referenciar

Los dos módulos que **no dependen de nada**: ni de MNE, ni de las bibliotecas
que faltan, ni de ninguna pieza nueva. Aritmética sobre `Recording`, y por eso
los primeros: son de resultado exactamente conocido.

**Cerrado con su interfaz**, que es lo que el hito pedía: los dos análisis se
piden desde el menú Análisis, que hasta acá estaba dibujado en el esquema de la
ventana y no existía.

- [x] **`Session.set_recording()`**, que no existía y sin el cual ningún
      análisis podía llegar a la pantalla. Mismo argumento que
      `set_scoring()` —procesar la señal no es abrir otro archivo—, más el caso
      que aquél no tenía: **los canales pueden cambiar**. Conserva los visibles
      que sobreviven, descarta la selección que ya no aplica, y las escalas se
      conservan por nombre mientras los canales nuevos arrancan con la de
      fábrica. Rechaza un registro de otra duración, porque el scoring ya hecho
      dejaría de corresponder.
- [x] **El menú Análisis**, con derivar, re-referenciar y referencia promedio.
- [x] **Volver a la señal original**, que es lo que hace reversible el menú
      entero. Sin eso, un filtro mal elegido obligaría a reabrir el archivo y
      con él se perdería el scoring que el usuario venía haciendo.
  - **Un test encontró que el canal derivado se creaba y no se veía.**
    `set_recording()` conserva los visibles que sobreviven, y un canal nuevo no
    sobrevive: nace. Mostrarlo es presentación —el usuario acaba de pedirlo— así
    que la decisión quedó en `ui/` y no en `core/`.

- [x] **`psglab/analysis/derivation.py`** · ~~2 stubs~~ · sección "Derivar"
  - `derive()` es una resta elemento a elemento, y `derive_montage()` se define
    sobre ella. El canal derivado se agrega **al final** y se llama `"A-B"` si
    no le dan nombre.
  - **Las tres decisiones que el esqueleto dejaba abiertas**, tomadas y
    escritas en el docstring del módulo: la **unidad** tiene que coincidir o se
    rechaza —restar grados de microvoltios da un número plausible que no
    significa nada, y no falla solo—; la **clase** se hereda si los dos canales
    la comparten y si no queda en `OTHER`, porque un "C3-EMG" no es ni una ni
    otra y decir que sí lo haría filtrar con los parámetros equivocados; y la
    **frecuencia original** se conserva si coinciden y si no queda en `None`.
  - **`derive_montage()` es atómico**: si un par falla no se aplica ninguno. Un
    montaje a medias le muestra al usuario algunos canales derivados y otros
    no, sin nada que le diga cuáles. Sale gratis de que `derive()` no modifique
    su entrada: lo que se descarta es el acumulador.
  - Test: `tests/test_derivation.py`, **29 tests en verde**.
- [x] **`psglab/analysis/reference.py`** · ~~2 stubs~~ · sección "Rereferenciar"
  - Con un solo canal de referencia, ese canal queda **idénticamente en cero**;
    con varios se resta el promedio, que es el caso de las mastoides A1+A2.
  - `average_reference(kind_only=True)` promedia sólo los EEG, y la prueba de
    que el flag sirve son **dos** tests y no uno: meter un EMG no cambia el
    resultado, y con `kind_only=False` **sí** lo cambia. Sin el segundo, el
    flag podría no estar haciendo nada.
  - **Lo que no es eléctrico no se toca**, que era la decisión pendiente.
    Restarle a un termómetro un promedio de microvoltios no falla: produce una
    temperatura falsa. `Channel.unit` es la fuente de verdad, igual que en el
    resto del programa.
  - El canal de referencia **se conserva** aunque quede plano: borrarlo en
    silencio le cambiaría al usuario la lista de canales sin avisarle.
  - Test: `tests/test_reference.py`, **20 tests en verde**.

---

## Hito 12: Filtración

- [x] **`psglab/analysis/filters.py`** · ~~3 stubs~~ · V1_F de "Filtración"
  - **`validate()` rechaza más de lo que rechaza MNE, y eso salió de medir.**
    Con un pasa-altos de 40 Hz y un pasa-bajos de 10, MNE **acepta el par, arma
    en silencio una banda eliminada y no emite ningún aviso**. Es una función
    legítima suya, pero acá los dos números salen de dos campos rotulados
    "pasa-altos" y "pasa-bajos", así que es un error de tipeo. Con la señal de
    prueba el resultado volvía **sin atenuar nada**: el investigador cree que
    filtró y está mirando la señal cruda. Por lo mismo se rechaza el cero, que
    MNE lee como "sin filtro".
  - **Y aun así hay un `except` alrededor de MNE**, que no es una guarda de
    más: la comprobación de Nyquist no alcanza para el notch, porque el notch
    se arma como una banda y esa banda puede pasarse aunque la frecuencia no.
    Medido: a 101 Hz de muestreo un notch de 50 Hz está por debajo de Nyquist
    (50,5) y MNE lo rechaza igual, porque el borde de su banda cae en 50,625.
  - **Se verifica por PSD y como razón de atenuación**, como decía el plan,
    pero **con otras frecuencias**: un pasa-bajos de 35 Hz atenúa la componente
    de 40 Hz apenas **7 veces**, porque cae dentro de su banda de transición
    —MNE la calcula como un cuarto del corte—. Un test sobre esa pareja estaría
    midiendo el ancho de la transición de MNE y no que el filtro filtre. Con la
    componente en 50 Hz la razón es de seis órdenes de magnitud.
  - **Todo o nada**: se valida el pedido entero antes de tocar un dato. Media
    señal filtrada y media cruda no se distingue a simple vista de una entera.
  - **Un canal que no se pidió filtrar vuelve idéntico bit a bit**, y hubo que
    hacerlo a propósito: el viaje µV → V → µV del puente del hito 10 deja error
    de punto flotante hasta en las filas que MNE no tocó. Lo encontró el test
    que afirmaba justamente eso.
  - **Poder deshacer**: ya estaba, porque el filtrado entra por
    `_aplicar_analisis()` como todo el menú, y "Volver a la señal original" lo
    deshace igual que a una derivación.
  - Ganó una función que el esqueleto no tenía, `settings_for_kinds()`: V1_F
    pide filtrar **por tipo de canal** y `apply_filters()` recibe filtros por
    **nombre**, que es la firma general. Traducir de una a la otra es la regla
    del pliego, así que va en `analysis/` y no en el diálogo.
  - Test: `tests/test_filters.py`, **53 tests en verde**.
- [x] **`psglab/ui/filter_panel.py`** · una fila por clase de canal
  - Sólo aparecen las clases que el registro tiene: ofrecer una fila de ECG en
    un registro sin ECG le pide al usuario que decida sobre algo que no existe.
  - **La celda vacía desactiva ese filtro, y es la única forma**, porque el
    cero está rechazado río abajo.
  - **Abrir el panel no filtra nada.** Un menú que filtre con sólo abrirse le
    cambiaría la señal a alguien que entró a mirar qué había.
  - Test: `tests/test_filter_panel.py`, **19 tests en verde**, más seis por la
    ventana en `tests/test_entrega.py`.

---

## Hito 13: PSD

- [x] **`psglab/analysis/psd.py`** · ~~3 stubs~~ · V1_F de "Power Spectral Density"
  - **El caso de test más limpio del proyecto**, y el que `conftest.py` usa
    para explicar por qué la señal sintética es mejor que un registro real: una
    onda de 10 Hz da un pico en 10 Hz. Los cuatro canales de la fixture están
    en frecuencias distintas, así que cada uno es su propio testigo y una
    permutación de canales se vería.
  - **La convención de la última ventana incompleta, fijada acá**: una ventana
    más corta que el segmento de Welch devuelve **NaN**, no un número. Calcular
    igual daría un valor con otra resolución, indistinguible de los demás en el
    array y comparable con ellos por error; descartarla desalinearía el array
    del hipnograma, que es justamente para lo que sirve. NaN conserva el largo y
    dice que ahí no se midió. La copian `complexity.py` y `connectivity.py`.
  - **La banda es semiabierta `[desde, hasta)`.** Las convencionales se tocan
    —delta termina en 4 Hz y theta empieza ahí— y con los dos extremos incluidos
    ese bin se contaría dos veces, con lo cual las potencias relativas sumarían
    más de 1 sin que nada fallara.
  - `WELCH_SEGMENT_SECONDS = 4.0` fija la resolución en 0,25 Hz, que es lo que
    hace falta para mirar delta desde 0,5 Hz. Con segmentos de 1 s la
    resolución sería 1 Hz y delta empezaría donde el análisis no puede mirar.
  - `relative` normaliza contra **toda la PSD calculada** y no contra la suma de
    las bandas: depende de lo que se midió y no de qué bandas eligió el usuario.
  - Dos excepciones nuevas: `UnknownPsdMethodError` —Welch y multitaper no dan
    lo mismo, así que elegir uno en silencio daría un resultado que el usuario
    no pidió y no puede distinguir del que pidió— e `InvalidBandError`.
  - Test: `tests/test_psd.py`, **38 tests en verde**.
- [x] **`psglab/ui/psd_panel.py`** · el panel del espectro
  - **Acá sí se usa pyqtgraph**, a diferencia del panel de la Übersicht, que se
    pinta con `QPainter`: un espectro es una curva sobre ejes con escala, y
    aquél son rectángulos sin sistema de coordenadas.
  - **El eje de potencia va en logarítmico**, y no es preferencia: la potencia
    delta de una ventana de sueño lento es de dos a tres órdenes de magnitud
    mayor que la gamma de la misma ventana.
  - **Un test encontró que eso se escapaba del panel.** Con el eje logarítmico,
    `PlotDataItem.getData()` devuelve el log₁₀ de lo que se dibujó, así que una
    potencia de 1e-6 volvía como -6. El panel guarda ahora la magnitud en su
    unidad, que es la misma solución que `signal_view.py` usa con los píxeles.
  - Test: `tests/test_psd_panel.py`, **19 tests en verde**.

---

## Hito 14: Complejidad y conectividad

Los dos que traen dependencias nuevas, juntos porque comparten forma: producen
**un número por ventana**, igual que el scoring, y por eso tienen dónde
mostrarse.

- [x] **`psglab/analysis/complexity.py`** · ~~5 stubs~~ · sección "Complejidad"
  - Las cuatro medidas son de antropy, que **expone exactamente los parámetros
    que las firmas del esqueleto prometían** —incluida la tolerancia de la
    entropía de muestra, cuyo valor por omisión es 0,2 × desvío estándar, la
    convención documentada—. Se verificó antes de comprometerse.
  - **Las anclas teóricas se cumplen exactas**: una rampa monótona da entropía
    de permutación 0,000000 y una recta da dimensión de Higuchi 1,0000. Las
    cuatro se verificaron contra la implementación **antes** de escribirlas
    como tests.
  - **Dos van normalizadas y dos no.** Lempel-Ziv y la entropía de permutación
    sí, porque sin normalizar dependen del largo de la ventana y dos registros
    a frecuencias distintas no se podrían comparar. Higuchi va de 1 a 2 por
    construcción y normalizarla sería inventarle un techo.
  - `MEASURES` es la constante que faltaba: sin ella el módulo aceptaba
    cualquier cadena y fallaba tarde, con un `KeyError`.
  - **Una señal constante da NaN** en Higuchi y en la entropía de muestra, y es
    correcto: la dimensión fractal de algo sin variación no está definida. Un
    canal desconectado es un caso real, así que está documentado que ahí el NaN
    significa "esta medida no existe para esta señal" y no "faltaron datos".
  - Test: `tests/test_complexity.py`, **34 tests en verde**.
- [x] **`psglab/analysis/connectivity.py`** · ~~3 stubs~~ · sección "Conectividad"
  - **La predicción del plan era falsa y medirla lo mostró.** Se esperaba que
    dos canales idénticos dieran wPLI 0; dan 0,39. Con señales exactamente
    iguales la parte imaginaria del espectro cruzado es cero, wPLI **divide por
    ella**, y lo que sale es ruido numérico.
  - La afirmación correcta no es sobre un caso degenerado sino sobre el
    escenario real que el docstring describe: dos electrodos que captan la
    misma fuente con su propio ruido dan **coherencia 0,74 y wPLI 0,39**, y dos
    señales con desfase real dan **coherencia 0,79 y wPLI 1,00**. La coherencia
    no las distingue y wPLI sí, que es exactamente la inmunidad al volume
    conduction que justifica el módulo. Son dos tests, uno por mitad.
  - `EPOCH_SECONDS = 5.0` se eligió por resolución y no por tiempo: el costo es
    plano entre 3 y 10 s, y 5 s dan 0,20 Hz —alcanza para delta desde 0,5 Hz— y
    seis épocas por ventana para que wPLI promedie sobre algo.
  - mne-connectivity devuelve sólo el triángulo inferior; el módulo lo refleja,
    porque promete una matriz simétrica y quien la lea no tiene por qué saber
    de qué lado quedó cada par.
  - Test: `tests/test_connectivity.py`, **33 tests en verde**.
- [x] **`psglab/ui/metric_panel.py`** · una métrica por ventana a lo largo de la
      noche
  - **Sirve a los dos módulos**, porque los dos producen esa forma. Es lo que
    los dos docstrings piden: poder cruzarla con el hipnograma.
  - **Los NaN se dibujan como hueco y no como cero**, que es lo que hace
    utilizable la convención de la ventana incompleta: un cero es un valor de
    complejidad plausible y bajo, indistinguible a ojo de una medición real.
  - El eje va en **base 1**, como el histograma: desde 0 quedaría desplazado una
    ventana respecto de él.
  - Test: `tests/test_metric_panel.py`, **14 tests en verde**.
- [x] **`psglab/ui/connectivity_panel.py`** · el mapa de calor de la matriz
  - **La matriz es la salida real del requisito**: mostrar sólo su promedio
    diría cuánta conectividad hay pero no entre qué canales.
  - Los ejes llevan **los nombres de los canales**: sin eso el mapa es un cuadro
    de colores.
  - **La escala de color es fija de 0 a 1.** Con escala automática, dos ventanas
    con conectividades muy distintas se verían iguales, y comparar ventanas es
    justamente lo que el investigador hace.
  - Test: `tests/test_connectivity_panel.py`, **10 tests en verde**.

> **Lo que costó cada medida, medido** sobre una ventana de 30 s a 256 Hz y
> extrapolado a las 2650 de un registro real. Es lo que decidió la interfaz:
>
>     higuchi_fractal_dimension     0,07 ms/ventana  ->    0,2 s la noche
>     permutation_entropy           0,14 ms/ventana  ->    0,4 s la noche
>     lempel_ziv_complexity         1,69 ms/ventana  ->    4,5 s la noche
>     conectividad (wPLI)           7,10 ms/ventana  ->    0,3 min la noche
>     sample_entropy              124,31 ms/ventana  ->  5,5 min la noche
>
> **Sólo la entropía de muestra es lenta**, así que la respuesta fue acotarla y
> no montar infraestructura de hilos: `complexity_by_window()` la acepta —es
> una función de biblioteca y un script puede esperar— y la interfaz no la
> ofrece para el barrido. La política es de la interfaz, no del módulo.

---

## Hito 15: ICA

- [x] **`psglab/analysis/ica.py`** · ~~4 stubs~~ · V5_F de "Filtración"
  - **El hueco del modelo de datos se resolvió sin tocarlo.**
    `component_topography()` devuelve **los pesos por canal** del componente,
    normalizados, que es el dato con el que se reconoce un artefacto: un
    parpadeo tiene peso alto en los frontales y bajo en los occipitales. Lo que
    no devuelve es un mapa sobre el cuero cabelludo, porque eso necesitaría las
    coordenadas de cada electrodo y `Channel` no las lleva. Agregarlas es una
    decisión sobre el modelo de datos de la Parte 1, no algo para resolver de
    paso; los pesos alcanzan para lo que la vista existe.
  - **El test que importa no verifica que MNE devuelva algo, sino que devuelva
    lo que se puso.** Se mezclan dos fuentes conocidas —alfa de 10 Hz y un
    parpadeo de 0,3 Hz— con pesos conocidos por canal, y se comprueba que ICA
    recupere esos pesos con tolerancia 0,15. Después se quita el componente del
    parpadeo y se mide **por PSD** que su potencia caiga diez veces sin que el
    alfa se mueva. Sin la segunda mitad, un `apply_ica()` que borrara todo
    pasaría la primera.
  - **La semilla es fija** (`RANDOM_STATE`). ICA es estocástica: sin ella el
    mismo registro da componentes distintos en cada corrida, en otro orden y
    con otro signo, y un investigador que rehace un análisis tiene que obtener
    lo mismo. Hay un test que corre la descomposición dos veces.
  - Ni el **orden** ni el **signo** de los componentes se afirman: son
    arbitrarios por construcción. Los tests buscan "el componente frontal" en
    vez de suponer que es el 0, y comparan valores absolutos.
  - **Se ajusta sobre los EEG y sólo sobre ellos**: meter un termómetro en la
    descomposición no tiene sentido físico y ensuciaría todos los componentes.
    `apply_ica()` devuelve el registro entero con el resto intacto.
  - Test: `tests/test_ica.py`, **36 tests en verde**.
- [x] **`psglab/ui/ica_panel.py`** · el panel de inspección
  - Diseñado alrededor de la advertencia del módulo: quitar el componente
    equivocado modifica la señal de forma irreversible. De ahí salen sus tres
    reglas: **ninguno viene marcado de fábrica** —sugerir cuál quitar sería
    adivinar por el usuario—, **nada se aplica solo**, y la topografía se
    muestra antes de poder marcar nada.
  - **Base 1 al mostrar, base 0 al devolver**, que es lo que `apply_ica()`
    espera: equivocar esa conversión quitaría un componente distinto del que el
    usuario marcó, que es justamente el error irreversible.
  - Recargar **desmarca lo de antes**: una marca de una descomposición vieja
    aplicada a otra quitaría un componente que el usuario nunca miró.
  - Pasa por `_aplicar_analisis()`, el camino único del menú, así que se puede
    volver a la señal original. Es la única red que hay.
  - Test: `tests/test_ica_panel.py`, **20 tests en verde**.

---

## Hito 16: Impedancia

Último porque es el único que arranca con una decisión del cliente sin cerrar.

- [x] **`psglab/analysis/impedance.py`** · ~~4 stubs~~ · V1_F de "Impedancia"
  - **Media pregunta del cliente quedó respondida midiendo, no preguntando**:
    **BrainVision sí las trae** —el `.vhdr` tiene una tabla
    `Impedance [kOhm] at hh:mm:ss :` en su sección `[Comment]`, ya en kΩ, y MNE
    la parsea en `raw.impedances`— y **EDF no puede traerlas**: el estándar no
    tiene ningún campo de impedancia, ni en EDF ni en EDF+. Para un EDF
    `read_impedances()` devuelve `{}` **siempre**, y eso convierte la vía del
    archivo aparte de extra en obligatoria: es la única disponible para la
    mitad del material.
  - **Las tres vías están implementadas**, que era lo decidido. La marca
    `PENDIENTE DE` **no se saca**: falta saber cuál usa el laboratorio, y eso
    decide qué se le ofrece primero al usuario, no qué se puede hacer.
  - **"No medido" no es "0 kΩ", y el módulo entero gira alrededor de eso.** Un
    electrodo suelto que nadie midió es el caso peligroso, porque cero es el
    mejor valor posible: si apareciera como cero pasaría por perfecto. El
    `.vhdr` los escribe `???` y MNE los entrega como `nan`; se omiten.
  - **El límite es inclusivo**: exactamente 5 kΩ con un límite de 5 kΩ pasa. El
    límite es el máximo aceptable, no el primer valor rechazado, que es como lo
    lee cualquiera que escriba "impedancia menor a 5".
  - **`impedance_report()` ganó un argumento**, y es una decisión de firma como
    la de `stage_durations_seconds()` en el hito 5: prometía distinguir tres
    estados y **con el diccionario solo no podía**, porque los canales sin dato
    se omiten a propósito. `channels` es lo que le permite saber qué falta.
  - Test: `tests/test_impedance.py`, **48 tests en verde**.
- [x] **`psglab/readers/brainvision.py`** · guarda las impedancias
  - Ignoraba la sección `[Comment]` entera. Ahora vuelca lo que MNE parsea a
    `Recording.metadata`, que es donde `core/recording.py` ya anticipaba que
    `impedance.py` las buscaría.
  - Filtra tres cosas: los `nan` de los no medidos, **`Ref` y `Gnd`** —que MNE
    incluye y no son canales del registro—, y las unidades que no sean kΩ,
    porque leer ohmios como kiloohmios daría mil veces menos y ningún canal
    parecería fallar nunca.
- [x] **`psglab/ui/impedance_panel.py`** · la tabla y el informe
  - Es donde vive **la tercera vía**: `analysis/` no conoce Qt, así que cargar
    a mano sólo puede estar acá.
  - La celda sin valor dice **"sin medir"**, ni "0" ni en blanco: un cero
    pasaría por el mejor valor posible y una celda vacía se lee como un olvido
    de la pantalla, no del electrodo.
  - Importar de un archivo **agrega, no reemplaza**: un laboratorio puede tener
    medido medio montaje.
  - Test: `tests/test_impedance_panel.py`, **16 tests en verde**.

> **Lo que sigue abierto, y ahora está mejor planteado.** La pregunta ya no es
> "de dónde salen" sino **cuál de las tres usa el laboratorio**, y de eso
> depende únicamente qué se le ofrece primero al investigador. El día que se
> conteste: sacar la marca `PENDIENTE DE` del docstring, y **reescribir en el
> mismo commit** la sección "Ambigüedad abierta" de
> [`analysis/README.md`](../psglab/analysis/README.md) —que sólo pasa el
> chequeo porque nombra este módulo— y la sección 8 de
> [`EXPLICACION.txt`](EXPLICACION.txt).

---

## Hito 17: Cierre de la Parte 2

La lista equivalente a la del [hito 8](#hito-8-cierre-de-la-parte-1), y por el
mismo motivo: **la Parte 2 se dio por terminada porque no quedaban stubs, que
es exactamente la medida que este archivo advierte que no sirve**. La Parte 1
se dio por cerrada con esa misma medida y estaba mal: el hito 9 fueron seis
requisitos hechos en `tools/` que `ui/` no consumía.

Correrla destapó lo suyo antes de terminar de escribirse, y es de la misma
clase.

- [x] **El CI, corrido por primera vez sobre los hitos 16 y 12.**
      `.github/workflows/ci.yml` dispara con `pull_request` contra `Add` y
      `Master`, y los PR #19 y #20 estaban apilados sobre ramas de trabajo:
      **tenían cero checks**. Dos de los cuatro hitos que quedaban sin mergear
      nunca se habían verificado fuera de una máquina Windows.
      - Las seis combinaciones en verde, y las licencias también.
      - **Reapuntar un PR no alcanza para disparar el CI**: `pull_request` corre
        con `opened`, `synchronize` y `reopened`, y cambiar la base es `edited`.
        Hay que cerrarlo y reabrirlo.
- [x] **Ningún stub, y ningún test salteado por falta de implementación.**
      ```bash
      grep -r "raise NotImplementedError" psglab --include=*.py | wc -l
      ./.venv/Scripts/python.exe -m pytest -rs
      ```
- [x] **Los requisitos de la Parte 2 de [`TRAZABILIDAD.md`](TRAZABILIDAD.md),
      recorridos por la ventana.** Los ocho tienen su sección en
      `tests/test_entrega.py` —el menú Análisis, deshacer, PSD, complejidad y
      conectividad, ICA, impedancia y filtración—.
      - **Es la diferencia con el hito 8, y por eso esta lista encontró menos
        de ese lado**: allá las pruebas de entrega se escribieron al final y
        destaparon seis huecos de golpe; en la Parte 2 se fueron escribiendo
        hito por hito, así que el hueco no llegó a acumularse.
- [x] **Cada análisis, sobre el registro real de `data/`** — 22 h, 7 canales,
      100 Hz. **Es el ítem que encontró todo lo demás**, y ningún chequeo
      automático puede sustituirlo: el `.gitignore` excluye los registros de
      participantes a propósito, así que se corre a mano.
      - **Filtrar con los valores sugeridos fallaba**, y es el hallazgo del
        hito. Ver abajo.
      - Lo demás anda: PSD de la noche 4,6 s · re-referenciar 0,3 s · derivar
        0,2 s · ICA 4,9 s · conectividad de una ventana 1,4 s.
      - **Ningún test de `analysis/` tocaba ese registro.** Los quince que lo
        leen son de lectura, tipado de canal y exportación: la Parte 2 entera
        se había verificado sobre diez minutos de senoides sintéticas.
- [x] **Los sugeridos de filtrado, adaptados al registro.** *(El hallazgo, y es
      de la clase del hito 9: cada mitad correcta y el conjunto sin funcionar.)*
      - El registro es de 100 Hz, Nyquist cae en 50 y **el notch sugerido es
        exactamente 50**, así que `validate()` lo rechaza con razón. El
        investigador abría el panel, veía los valores cargados, apretaba
        Aplicar sin tocar nada y recibía un cartel de error. El pasa-bajos de
        100 Hz del EMG tiene el mismo problema por debajo de 200 Hz.
      - **100 Hz no es un caso raro**: es lo que usa buena parte del
        equipamiento clínico. Toda la suite usaba 256 Hz, así que nada lo veía.
      - `default_for()` gana un segundo argumento opcional, la frecuencia de
        muestreo, y **descarta lo que no entra en vez de recortarlo**. El motivo
        es físico: por encima de Nyquist el registro no contiene nada, así que
        el filtro no filtraría nada aunque MNE pudiera construirlo. Recortarlo
        a un valor arbitrario sería inventarle al investigador un criterio
        clínico que nadie eligió, disfrazado de valor por defecto.
      - El panel dice a qué frecuencia se muestreó el registro y hasta dónde
        llega. Sin eso, **una celda vacía por imposibilidad se lee igual que una
        que el usuario borró**, que es la misma distinción que el hito 16 hizo
        con "sin medir".
      - Ocho tests lo atrapan, en las tres capas, y se los vio fallar antes de
        darlos por buenos.
- [x] **La deriva de `requirements-analysis.txt`, en seis archivos.** Decían que
      **ningún test importa** esas dependencias y que el CI las instala **sólo
      en el job de licencias**. Las dos mitades son falsas desde el hito 10.
      - **La consecuencia era cara**: quien siguiera el `README.md` e instalara
        sólo los dos primeros requirements se comía `ModuleNotFoundError` en
        `test_complexity.py`, `test_connectivity.py` y parte de
        `test_entrega.py`. Los imports son diferidos a nivel de función, así que
        la recolección pasa y el fallo sale recién al ejecutarse el test, sin
        decir que falta un requirements.
      - `ci.yml` se contradecía consigo mismo: el comentario del job de
        licencias decía "que el job de tests no instala" y el job de tests las
        instala.
- [x] **Licencias verificadas**, que el pliego pide antes de cada release. El
      bloque nuevo, fechado, en [`ARQUITECTURA.md`](ARQUITECTURA.md).
      ```bash
      python -m piplicenses --format=markdown --order=license
      ```
- [x] **[`EXPLICACION.txt`](EXPLICACION.txt), sección 8.** Decía *"Ni EDF ni
      BrainVision las traen siempre"*. El hito 16 midió algo más fuerte: **EDF
      no puede traerlas nunca**, porque el estándar no tiene el campo. Es el
      documento que lee el cliente y la frase le ocultaba media respuesta.

### Lo que este hito midió y no arregló

Dos cosas quedan con números y sin tocar, porque son trabajo de diseño y cada
una merece su hito.

- [x] **La memoria.** *(Atendida en el [hito 18](#hito-18-escala): las copias
      evitables se sacaron y el `MemoryError` ya sale como cartel. Lo que
      sigue abierto está anotado allá.)* La señal vive entera como `float64`
      en RAM y filtrar llegaba
      a tener **cinco copias completas vivas a la vez** —`mne_bridge.py` dos,
      más la que sostiene la ventana principal como "señal original" y la que se
      está viendo—. Medido sobre el registro real: 445 MB por copia, **1337 MB
      de pico**. Proyectado a los 32 canales que declara `data/test.vhdr`, un
      registro de 8 horas daría entre 9 y 37 GB.
      - Y **`MemoryError` no hereda de `PsgLabError`**, así que atravesaría el
        `except` de `_aplicar_analisis()` y saldría como traza de Python, que es
        justo lo que todo el proyecto se esfuerza en evitar.
      - Detalle barato de ahí: `apply_filters()` con todos los filtros
        desactivados paga tres copias completas para no hacer nada.
- [x] **Los 21 s de calentamiento de numba.** *(Atendidos en el
      [hito 18](#hito-18-escala): no se pueden eliminar sin hilos, pero ya no
      parecen un cuelgue.)* La primera llamada de complejidad
      de cada sesión congela la ventana ~21 s compilando, **cualquiera sea la
      medida**. La tabla de costos de `complexity.py` mide sólo el cálculo, y
      `MEDIDAS_RAPIDAS` se eligió justamente para que la ventana no se congele:
      el calentamiento la congela igual.
      - Ya en caliente, sobre las 2650 ventanas reales y un canal: permutación
        1,2 s · Higuchi 0,4 s · Lempel-Ziv 11,6 s · entropía de muestra 128 s
        —esta última es la que ya está fuera del menú, y con razón—.

---

## Hito 18: Escala

Los dos números que el [hito 17](#hito-17-cierre-de-la-parte-2) dejó medidos y
sin tocar. El problema de fondo no cambia —la señal vive entera en memoria como
`float64`— pero sí cambia **cuántas veces se la copia para no nada** y, sobre
todo, **cómo falla cuando no entra**.

### Lo que costaba, y lo que cuesta

Medido sobre `data/SC4001E0-PSG.edf` (22 h, 7 canales, 100 Hz), donde una copia
son **445 MB**:

| Operación | Antes | Ahora |
|---|---|---|
| `apply_filters`, todos los canales | 3,0 copias · 1337 MB | **2,3 · 1019 MB** |
| `apply_filters`, un canal | 3,0 · 1336 MB | **2,0 · 890 MB** |
| `apply_filters`, sin ningún filtro activo | 3,0 · 1336 MB | **1,0 · 445 MB** |
| `derive_montage`, 4 pares | 3,1 · 1399 MB | **2,1 · 954 MB** |
| `average_reference` | 1,1 | 1,1 |

- [x] **La copia que `from_raw()` hacía de más.** `raw.get_data()` ya devuelve
      un array fresco e independiente del buffer de MNE —medido: no comparte
      memoria con `raw._data` y escribirle no lo toca—, así que el
      `np.array(..., copy=True)` que venía después **duplicaba una copia recién
      hecha**. Es la que subía el pico de `apply_filters()` de dos a tres.
- [x] **Filtrar sin filtros costaba tres copias para no cambiar nada.** Abrir el
      panel, vaciar las celdas y aplicar es una forma legítima de decir "dejala
      como está", y hacía el viaje entero de ida y vuelta por MNE. Ahora se
      copia y listo.
- [x] **`derive_montage()` copiaba el registro una vez por par.** Encadenaba
      `derive()`, y cada llamada hacía su propio `np.vstack` de la matriz
      entera, cada vez más grande. Ahora acumula las filas nuevas y arma la
      matriz **una sola vez**.
      - **Se conservó poder derivar de una derivación anterior**, que era lo que
        el encadenado daba gratis y que ningún test cubría. Ahora sí lo cubren
        dos.
- [x] **`MemoryError` salía como traza de Python**, y era el único error del
      programa que rompía la promesa de `utils/errors.py`. No hereda de
      `PsgLabError`, así que atravesaba el `except` de la ventana principal —los
      catorce que hay—. Y es el más probable de todos en un registro grande.
      - `RecordingTooLargeError` y el contextmanager `memoria_suficiente()`, que
        envuelve las cinco reservas grandes del programa: el puente con MNE en
        las dos direcciones, el filtrado, el re-referenciado y las derivaciones.
      - **Atraparlo y seguir es seguro acá**, y no siempre lo es: lo que falla es
        una sola reserva de numpy, que se libera al fallar, y ninguna función de
        `analysis/` modifica su entrada. El cartel lo dice: *"El registro sigue
        abierto y sin cambios"*, y hay un test que lo verifica.
- [x] **Los 21 s de calentamiento de numba, hechos legibles.** No se pueden
      eliminar sin meter hilos, que el programa no tiene en ninguna parte. Lo
      que sí se puede es que **no parezca que se colgó**: cursor de espera y
      aviso en la barra de estado mientras dura el cálculo.
      - Es la misma preocupación que llevó a sacar la entropía de muestra del
        menú (`MEDIDAS_RAPIDAS`), y elegir medidas rápidas no alcanzaba: el
        calentamiento lo paga la primera llamada de cada sesión, sea cual sea la
        medida.

### `float32` se evaluó y se descartó, con medición

Habría partido la memoria al medio, y **la decisión fue que no**. El motivo no
es la precisión —16 bits de ADC entran de sobra en la mantisa de 24— sino que
**MNE trabaja siempre en `float64`**: al pasarle un array `float32` lo convierte,
y esa conversión es una copia completa más.

```
RawArray desde float32: pico 224 MB, queda en float64
RawArray desde float64: pico  28 MB, queda en float64   (reusa el array)
```

O sea que `float32` **baja lo que está en reposo y sube el pico**, que es
justamente donde ocurre el `MemoryError`. Mueve el problema hacia el peor lado.
Queda anotado en [`ARQUITECTURA.md`](ARQUITECTURA.md) para que no se vuelva a
proponer sin este número.

### Lo que sigue sin resolverse

- [ ] **La señal sigue entera en memoria, y la ventana principal guarda dos.**
      El registro original —el que hace posible "Volver a la señal original"— y
      el que se está viendo. Sobre 32 canales y 8 horas son 1,9 GB cada uno
      antes de empezar a analizar. Bajarlo de verdad pide otra cosa: leer por
      tramos, o releer el archivo al deshacer en vez de guardarlo. Las dos son
      decisiones de diseño con su propio costo.
- [ ] **Nada corre fuera del hilo de la interfaz.** El cursor de espera avisa,
      pero la ventana sigue congelada. Un `QThread` para los barridos de la
      noche es la solución de fondo, y hoy el programa no tiene ninguno.

---

## Hito 19: Lo que la interfaz no consumía

**Es el hito 9 otra vez, del lado de la Parte 2.** La auditoría del 8 de
septiembre de 2026 encontró **tres funciones públicas de `analysis/` que no
tienen ningún camino desde la ventana**: código correcto, con sus tests en
verde, que ningún usuario puede ejecutar. Y una decisión de interfaz que un
comentario difirió "al hito 6" y que nunca se tomó.

La lista de cierre del hito 17 no lo vio, y el motivo es preciso: **recorrió los
ocho requisitos de `TRAZABILIDAD.md` por la ventana, no las funciones
públicas**. Un requisito puede estar cubierto a medias —el espectro se dibuja,
la potencia por banda no se muestra— y la comprobación por requisito lo da por
bueno. `contar_stubs()` tampoco los ve: no son stubs, son caminos muertos.

### Las cuatro decisiones, y por qué

Se tomaron con el cliente y se anotan acá antes de escribir una línea, que es lo
que este archivo existe para sostener.

- [x] **`derive_montage()` queda como API de biblioteca**, no va al menú.
      Está implementado, es atómico, tiene 29 tests y el hito 18 lo optimizó de
      3,1 a 2,1 copias, pero derivar un montaje entero de una vez es un pedido
      que todavía nadie hizo desde el programa. Es el mismo criterio que
      `sample_entropy` y `MEDIDAS_RAPIDAS`: una función de biblioteca que un
      script del laboratorio puede llamar, y una interfaz que no la ofrece.
      **Lo que sí se corrige es el import muerto de `ui/main_window.py`**, que
      es la huella de un cableado que se empezó y no se terminó, y que hacía
      parecer consumido lo que no lo estaba.
- [x] **La curva temporal del componente ICA se dibuja.** `component_time_course()`
      promete en su docstring que "es lo que se dibuja debajo de la señal para
      ver **cuándo** ocurre el artefacto", y no lo dibujaba nadie. Es la mitad
      del criterio con el que se reconoce un componente: la topografía dice
      **dónde** pesa y la curva dice **cuándo** ocurre; con una sola, el
      investigador decide a ciegas sobre una operación irreversible.
      **De la ventana actual**, por el mismo motivo que el espectro y la
      conectividad: la serie de las ocho horas no se puede mirar, y calcularla
      entera cuesta una copia completa de la señal.
- [x] **La potencia por banda se muestra.** El panel del espectro **sombreaba**
      las bandas y nunca decía cuánta potencia tenía cada una, mientras
      `TRAZABILIDAD.md` asigna a V1_F "PSD por banda de frecuencia elegida".
      Van las dos: la absoluta y la **relativa**, que es la que el módulo
      documenta como "la que permite comparar entre participantes" y la que hoy
      no se veía en ningún lado.
- [x] **La tolerancia de clic de la ocupación pasa a ser una fracción del
      carril.** `TOLERANCIA_DE_CLIC_UV = 10.0` era fija en microvoltios y no
      escala con la amplitud: con la escala en su mínimo cubre 4,5 carriles y
      **cualquier clic borra la línea** —el síntoma que el hito 9 dice haber
      corregido—, y con la escala en su máximo la línea es imposible de borrar.
      El hito 9 arregló la **unidad**; la dependencia de la escala quedó. La
      decisión que el comentario difería "al hito 6" es ésta, y se toma ahora.

### Lo que además se documenta

Dos decisiones científicas que el código ya tomaba y no tenía escritas. No
cambian nada; el proyecto escribe sus motivos.

- [x] **`compute_connectivity()` devuelve el valor absoluto**, y para
      `imaginary_coherence` eso no es una operación nula: la coherencia
      imaginaria tiene signo y el signo dice cuál canal adelanta a cuál. Se
      toma el módulo porque la matriz se promete **simétrica**, y hay que
      decirlo.
- [x] **`average_reference(kind_only=True)` promedia sólo los EEG pero le resta
      ese promedio a todo lo eléctrico**, también al EOG, al EMG y al ECG. Es
      distinto de lo que hace `set_eeg_reference()` de MNE, que toca sólo los
      canales del tipo pedido. El docstring promete la propiedad del promedio y
      no dice hasta dónde llega la resta.

---

## Hito 20: La red

Los tres chequeos que la auditoría del 8 de septiembre de 2026 dejó pedidos, y
que existen por un motivo que ya se repitió: **cada hallazgo de este proyecto se
encontró a mano, y las dos veces que se buscó a mano se escapó algo.** El hito 9
salió de recorrer requisitos por la ventana; el 19, de otra revisión completa.
Entre uno y otro pasaron diez hitos con el mismo hueco abierto.

`tests/test_consistencia.py` verifica muy bien lo que tiene números —stubs,
tests recolectados, IDs, enlaces, ASCII, capas sin Qt— y su propio docstring
declara los dos huecos por los que se cuela todo lo demás: **la prosa sin
números y el camino muerto**. Estos tres los cierran donde se puede.

- [x] **Toda función pública de `analysis/` llega a la ventana, o figura en
      `SOLO_BIBLIOTECA` con su motivo.**
      Habría atrapado los tres hallazgos del hito 19. Lo que mira es que el
      nombre **se use** en `psglab/ui/`: un `from x import y` produce un nodo
      `alias` y no un `Name`, así que un import sin llamada no cuenta, que es
      exactamente la forma que tenía el camino muerto de `derive_montage()`.
      La tabla arranca con doce filas, y ninguna es un pendiente disfrazado:
      cuatro son las medidas de complejidad, que se despachan por nombre; tres
      son el puente con MNE; el resto, funciones que llama otra del mismo
      módulo, más las dos decisiones del hito 19.
- [x] **La cuenta de hitos que declaran los documentos es la de la tabla de
      progreso.** Cuatro decían "diecisiete" con diecinueve filas. La
      convención que fija el chequeo es **el número y el rango** —"veintiún
      hitos, del 0 al 20"—, por dos motivos: un numeral suelto no se distingue
      de los históricos ("los cuatro hitos que entraron en dos días") y el rango
      dice desde dónde se cuenta, que era la ambigüedad de fondo, porque el
      hito 0 existe.
- [x] **Lo que los documentos dicen del CI coincide con `ci.yml`.** `README.md`
      prometía que "cada push y cada pull request" lo disparan, y el workflow
      filtra por rama. La comprobación es **por sección** y no por archivo: la
      primera versión buscaba las ramas en el documento entero y no atrapaba
      nada, porque `README.md` nombra `Add` y `Master` en "Cómo contribuir",
      que habla de otra cosa. Se lo vio fallar con la frase vieja antes de
      darlo por bueno.

### Lo que el primer chequeo encontró al escribirse

- [ ] **El barrido de conectividad a lo largo de la noche no está en el menú.**
      `connectivity_by_window()` produce una matriz por ventana, `MetricPanel`
      existe y sirve para esa forma de dato —lo dice su propio docstring— y no
      hay ningún camino que los junte. Es el mismo hueco que el hito 19 cerró
      para la curva de la ICA y la potencia por banda, y quedó porque **es una
      decisión de producto y no se toma escribiendo un chequeo**: hay que saber
      si el investigador quiere ver la conectividad de la noche entera o le
      alcanza con la de la ventana.

      Está anotado como tal en `SOLO_BIBLIOTECA`, con esas palabras. Una
      exención que disfrace un hueco de decisión tomada es peor que el hueco:
      lo vuelve invisible y encima parece revisado.

---

## Al agregar o cerrar un ítem

Actualizá en el mismo commit: este archivo, la fila de `TRAZABILIDAD.md` y el
`README.md` de la carpeta que tocaste. Los PR van a la branch **`Add`**, nunca
a `Master`, y vienen comentados.
