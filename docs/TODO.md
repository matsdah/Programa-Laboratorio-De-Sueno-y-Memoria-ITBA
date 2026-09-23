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
tres funciones públicas de `analysis/` que la interfaz no consumía. El
**[hito 20](#hito-20-la-red)** es la red que evita que esto vuelva a pasar:
tres chequeos automáticos sobre lo que hasta acá se encontraba a mano.

El **[hito 22](#hito-22-refactor-de-la-interfaz)** llevó la interfaz a un
visualizador al estilo de EDFbrowser, en diez fases, y el
**[hito 23](#hito-23-ajustes-de-la-barra-de-menú)** ajustó su barra de menú y
sumó el scoring en CSV, EDF+ y XML. El
**[hito 24](#hito-24-vista-inicial-y-reproducción)** dejó la señal sola al
abrir y agregó la reproducción, y el
**[hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar)** la hizo el doble
de rápida. El **[hito 26](#hito-26-el-diseño-de-la-ventana)** llevó al programa
lo que propuso y midió un lienzo de diseño: el reparto de los paneles, un
esquema nuevo y dos detalles. El **[hito 27](#hito-27-la-navegación-desde-el-medio)**
dejó ocho controles en la barra y hace que la reproducción se cuente desde el
medio del gráfico, y el **[hito 28](#hito-28-un-solo-menú-de-herramientas)**
fundió «Paneles» con «Herramientas». El
**[hito 29](#hito-29-verificación-de-las-herramientas)** recorrió nueve
herramientas buscando caminos muertos y fugas, y el
**[hito 30](#hito-30-las-decisiones-de-la-verificación)** tomó las cuatro
decisiones que dejó. El **[hito 31](#hito-31-el-recorrido-manual)** corrigió lo
que encontró el usuario al recorrer el programa con un registro real, y el
**[hito 32](#hito-32-los-pendientes-del-todo)** resolvió los pendientes que
quedaban. El **[hito 33](#hito-33-la-auditoría-del-19-de-septiembre)**, abierto,
ordena lo que encontró la auditoría del 19 de septiembre, y el
**[hito 34](#hito-34-el-rediseño-de-la-pantalla-principal)** llevó a la ventana
el diseño que el usuario aprobó, y el
**[hito 35](#hito-35-dos-esquemas-y-ninguna-perilla)** dejó los colores en dos
esquemas y sacó la solapa que los editaba. El
**[hito 36](#hito-36-las-dos-barras)** rehízo la barra de menú y la de
navegación, que eran lo que quedaba del diseño sin llevar a la ventana, y el
**[hito 37](#hito-37-el-canalón)** sacó el nombre de cada canal de encima de su
propia señal. El **[hito 38](#hito-38-lo-que-faltaba-del-prototipo)** cerró el
área central contra el prototipo: la escala de cada clase, el eje en hora y el
selector de canales. El
**[hito 39](#hito-39-la-carrocería-de-los-paneles)** empezó por lo que los seis
paneles de análisis comparten, y el
**[hito 40](#hito-40-lo-que-cada-panel-dice-de-lo-suyo)** siguió con lo que
cada uno tiene que decir de lo suyo, y el
**[hito 41](#hito-41-los-seis-paneles-y-no-cuatro)** se lo puso a los dos que
faltaban. El **[hito 42](#hito-42-lo-largo-deja-de-congelar-la-ventana)** sacó
del hilo de la interfaz el cálculo más caro del menú, y el
**[hito 43](#hito-43-una-tipografía-y-su-hermana-de-ancho-fijo)** dejó la
tipografía en dos familias emparentadas, con una escala en un solo lugar. El
**[hito 44](#hito-44-tres-cosas-que-se-vieron-en-la-pantalla)** atendió lo que
el usuario encontró mirando el programa andar, y el
**[hito 45](#hito-45-la-banda-no-se-dibujaba-y-la-lupa-miraba-un-solo-canal)**
cerró los dos huecos que quedaban entre una herramienta y la pantalla, y el
**[hito 46](#hito-46-tres-cabos-sueltos)** ató los tres cabos que habían
quedado anotados, y el
**[hito 47](#hito-47-lo-caro-era-ajustar-y-no-cambia-la-señal)** sacó del hilo
de la interfaz lo último que quedaba largo, y el
**[hito 48](#hito-48-la-auditoría-de-los-tests)** auditó los tests por primera
vez desde que empezó el proyecto, y el
**[hito 49](#hito-49-la-envolvente-se-calcula-una-vez)** hizo que la envolvente se calcule una vez, con lo que cerró el 33, y el
**[hito 50](#hito-50-los-pendientes-revisados)** revisó las casillas que habían quedado sin tachar dentro de los
hitos cerrados, y el **[hito 51](#hito-51-la-übersicht-muestra-la-señal)** terminó la Übersicht, que no dibujaba señal, y el
**[hito 52](#hito-52-una-anotación-se-puede-corregir)** permitió corregir una anotación hecha, y el
**[hito 53](#hito-53-cuatro-defectos-que-encontró-el-prototipo)** arregló lo que encontró la comparación con el prototipo, y el
**[hito 54](#hito-54-lo-que-faltaba-del-prototipo)** sumó lo que le faltaba de peso medio, y el
**[hito 55](#hito-55-lo-último-del-prototipo)** lo de peso bajo. El
**[hito 56](#hito-56-la-rueda-y-el-panel-táctil-sobre-la-señal)** hace que la rueda del mouse cambie la escala de tiempo
y desplace la página. El **[hito 57](#hito-57-cuánta-memoria-cuesta-cada-cosa)** midió cuánta memoria cuesta cada cosa, y el
**[hito 58](#hito-58-la-ica-se-ajusta-sobre-una-muestra-de-la-noche)** bajó lo más caro: ajustar la ICA.
Son **cincuenta y nueve hitos**, del 0 al 58, que son las filas de la tabla de
progreso; **no queda ninguno abierto**, y lo que sigue pendiente de cada uno
está anotado dentro del hito al que le toca.

**Del 34 al 48 se hicieron con el 33 abierto**, y lo cerró el 49. Decía acá
que el 34 era «la única vez que pasa» y dejó de ser cierto en el 35: es
exactamente la clase de prosa que este archivo se desincroniza. Lo que le
quedaba al 33 no era código contra el que se pudiera escribir de más —eran dos
ítems de rendimiento que terminaron siendo los hitos 42, 47 y 49—. La regla
existe para no escribir contra algo que todavía no se puede testear, y ahí no
era el caso.

**La Parte 1 está terminada**, con los hitos 0 a 9 cerrados. Al cerrarla, sus
34 requisitos se podían usar desde el programa corriendo, no sólo desde sus
módulos, que es la distinción que este resumen no puede dar y que costó el
hito 9. **Desde el hito 23 hay dos que no**: Anotaciones.txt e
Informacion.txt salieron del menú por decisión del usuario, y falta
confirmarlo con el cliente.

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
| [21. Limpieza](#hito-21-limpieza) | — | 0 | ✅ cerrado |
| [22. Refactor de la interfaz](#hito-22-refactor-de-la-interfaz) | — | 0 | ✅ cerrado |
| [23. Ajustes de la barra de menú](#hito-23-ajustes-de-la-barra-de-menú) | — | 0 | ✅ cerrado |
| [24. Vista inicial y reproducción](#hito-24-vista-inicial-y-reproducción) | — | 0 | ✅ cerrado |
| [25. Rendimiento](#hito-25-rendimiento-al-abrir-y-al-desplazar) | — | 0 | ✅ cerrado |
| [26. El diseño de la ventana](#hito-26-el-diseño-de-la-ventana) | — | 0 | ✅ cerrado |
| [27. La navegación desde el medio](#hito-27-la-navegación-desde-el-medio) | — | 0 | ✅ cerrado |
| [28. Un solo menú de herramientas](#hito-28-un-solo-menú-de-herramientas) | — | 0 | ✅ cerrado |
| [29. Verificación de las herramientas](#hito-29-verificación-de-las-herramientas) | — | 0 | ✅ cerrado |
| [30. Las decisiones de la verificación](#hito-30-las-decisiones-de-la-verificación) | — | 0 | ✅ cerrado |
| [31. El recorrido manual](#hito-31-el-recorrido-manual) | — | 0 | ✅ cerrado |
| [32. Los pendientes del TODO](#hito-32-los-pendientes-del-todo) | — | 0 | ✅ cerrado |
| [33. La auditoría del 19 de septiembre](#hito-33-la-auditoría-del-19-de-septiembre) | — | 0 | ✅ cerrado |
| [34. El rediseño de la pantalla principal](#hito-34-el-rediseño-de-la-pantalla-principal) | — | 0 | ✅ cerrado |
| [35. Dos esquemas y ninguna perilla](#hito-35-dos-esquemas-y-ninguna-perilla) | — | 0 | ✅ cerrado |
| [36. Las dos barras](#hito-36-las-dos-barras) | — | 0 | ✅ cerrado |
| [37. El canalón](#hito-37-el-canalón) | — | 0 | ✅ cerrado |
| [38. Lo que faltaba del prototipo](#hito-38-lo-que-faltaba-del-prototipo) | — | 0 | ✅ cerrado |
| [39. La carrocería de los paneles](#hito-39-la-carrocería-de-los-paneles) | — | 0 | ✅ cerrado |
| [40. Lo que cada panel dice de lo suyo](#hito-40-lo-que-cada-panel-dice-de-lo-suyo) | — | 0 | ✅ cerrado |
| [41. Los seis paneles, y no cuatro](#hito-41-los-seis-paneles-y-no-cuatro) | — | 0 | ✅ cerrado |
| [42. Lo largo deja de congelar la ventana](#hito-42-lo-largo-deja-de-congelar-la-ventana) | — | 0 | ✅ cerrado |
| [43. Una tipografía, y su hermana de ancho fijo](#hito-43-una-tipografía-y-su-hermana-de-ancho-fijo) | — | 0 | ✅ cerrado |
| [44. Tres cosas que se vieron en la pantalla](#hito-44-tres-cosas-que-se-vieron-en-la-pantalla) | — | 0 | ✅ cerrado |
| [45. La banda no se dibujaba y la lupa miraba un solo canal](#hito-45-la-banda-no-se-dibujaba-y-la-lupa-miraba-un-solo-canal) | — | 0 | ✅ cerrado |
| [46. Tres cabos sueltos](#hito-46-tres-cabos-sueltos) | — | 0 | ✅ cerrado |
| [47. Lo caro era ajustar, y no cambia la señal](#hito-47-lo-caro-era-ajustar-y-no-cambia-la-señal) | — | 0 | ✅ cerrado |
| [48. La auditoría de los tests](#hito-48-la-auditoría-de-los-tests) | — | 0 | ✅ cerrado |
| [49. La envolvente se calcula una vez](#hito-49-la-envolvente-se-calcula-una-vez) | — | 0 | ✅ cerrado |
| [50. Los pendientes, revisados](#hito-50-los-pendientes-revisados) | — | 0 | ✅ cerrado |
| [51. La Übersicht muestra la señal](#hito-51-la-übersicht-muestra-la-señal) | — | 0 | ✅ cerrado |
| [52. Una anotación se puede corregir](#hito-52-una-anotación-se-puede-corregir) | — | 0 | ✅ cerrado |
| [53. Cuatro defectos que encontró el prototipo](#hito-53-cuatro-defectos-que-encontró-el-prototipo) | — | 0 | ✅ cerrado |
| [54. Lo que faltaba del prototipo](#hito-54-lo-que-faltaba-del-prototipo) | — | 0 | ✅ cerrado |
| [55. Lo último del prototipo](#hito-55-lo-último-del-prototipo) | — | 0 | ✅ cerrado |
| [56. La rueda y el panel táctil sobre la señal](#hito-56-la-rueda-y-el-panel-táctil-sobre-la-señal) | — | 0 | ✅ cerrado |
| [57. Cuánta memoria cuesta cada cosa](#hito-57-cuánta-memoria-cuesta-cada-cosa) | — | 0 | ✅ cerrado |
| [58. La ICA se ajusta sobre una muestra de la noche](#hito-58-la-ica-se-ajusta-sobre-una-muestra-de-la-noche) | — | 0 | ✅ cerrado |
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
  - Test: `tests/test_units.py`, **47 tests en verde**.
  - La mitad de los tests son de **entrada sucia**, no de aritmética: las
    cabeceras de EDF y BrainVision escriben la unidad de formas variadas, y
    confundir "no reconozco esto" con "esto vale 1" deja la señal mal escalada
    de punta a punta sin que nada se vea raro en pantalla.
  - Los dos caracteres "mu" (U+03BC y U+00B5) se ven idénticos, así que un test
    afirma sus puntos de código: si alguien los intercambiara al editar el
    módulo, la normalización dejaría de hacer nada y ningún otro test lo notaría.
- [x] **`psglab/core/windows.py`** · ~~5 stubs~~ · sostiene V1_P "Visualización"
      (nº de ventana y total), V1_F "Navegación", V2_F "Histograma"
  - Test: `tests/test_windows.py`, **65 tests en verde**.
  - Los bordes se calculan desde el índice de la ventana, nunca acumulando un
    paso redondeado: con una frecuencia no redonda (256,125 Hz en EDF) acumular
    corre la ventana 960 casi tres segundos. Hay tres tests que lo fijan.
  - Convierte entre las cuatro unidades no gráficas: ventanas, muestras,
    segundos dentro de la ventana y fracción de ventana. Las herramientas
    piden acá en vez de escribir la cuenta; los píxeles son de
    `ui/signal_view.py`, que es lo único que conoce el ancho de la pantalla.
- [x] **`psglab/core/nomenclature.py`** · ~~5 stubs~~ · V3_F "Scoring",
      V3_F "Histograma"
  - Test: `tests/test_nomenclature.py`, **51 tests en verde**. Los ocho
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
  - Test: `tests/test_recording.py`, **53 tests en verde**, sobre la fixture
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
  - Test: `tests/test_scoring.py`, **28 tests en verde**.
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
  - Test: `tests/test_annotations.py`, **60 tests en verde**.
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
  - Test: `tests/test_session.py`, **156 tests en verde**. Navegación y amplitud
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
  - Test: `tests/test_readers.py`, **88 tests en verde**, que cubre este módulo
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
  - Test: `tests/test_scoring_reader.py`, **38 tests en verde**. El archivo lo
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
  - Test: `tests/test_grid.py`, **19 tests en verde**. No dibuja píxeles:
    calcula posiciones, así que se puede afirmar sobre la grilla sin mirar una
    pantalla.
  - Las posiciones **se multiplican, no se acumulan**: sumar 0,5 sesenta veces
    corre la última línea del borde, que es el mismo error que `core/windows.py`
    documenta para las ventanas.
- [x] **`psglab/ui/signal_view.py`** · ~~13 stubs~~ · V1_P, V2_P, V4_F, V5_F
      "Visualización" (+ el dibujo de V3_P), V1_F "Anotación de la señal"
  - Test: `tests/test_signal_view.py`, **92 tests en verde**. **El dibujo no se
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
  - Test: `tests/test_shortcuts.py`, **35 tests en verde**. Las dos funciones que
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
  - Test: `tests/test_occupancy.py`, **51 tests en verde**, sin `pytestmark`.
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
  - Test: `tests/test_magnifier.py`, **30 tests en verde**. El contador se
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
  - Test: `tests/test_overview.py`, **34 tests en verde**. La cantidad de
    vecinas es configurable y asimétrica, y se recorta contra los bordes del
    registro: en la primera ventana no hay anterior.
  - **`_draw_window()` no dibuja: describe.** `tools/` no conoce Qt, así que
    arma el dato que la interfaz pinta. Hizo falta agregar `windows()`, porque
    sin un accesor el panel era de sólo escritura y no había con qué dibujarlo.
- [x] **`psglab/tools/histogram.py`** · ~~7 stubs~~ · V1_P, V2_F, V3_F, V4_F
      "Histograma" · `Tool`
  - Test: `tests/test_histogram.py`, **33 tests en verde**.
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
  - Test: `tests/test_annotator.py`, **41 tests en verde**.
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
  - Test: `tests/test_mne_bridge.py`, **15 tests en verde**.
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
  - Test: `tests/test_filters.py`, **54 tests en verde**.
- [x] **`psglab/ui/filter_panel.py`** · una fila por clase de canal
  - Sólo aparecen las clases que el registro tiene: ofrecer una fila de ECG en
    un registro sin ECG le pide al usuario que decida sobre algo que no existe.
  - **La celda vacía desactiva ese filtro, y es la única forma**, porque el
    cero está rechazado río abajo.
  - **Abrir el panel no filtra nada.** Un menú que filtre con sólo abrirse le
    cambiaría la señal a alguien que entró a mirar qué había.
  - Test: `tests/test_filter_panel.py`, **26 tests en verde**, más seis por la
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
  - Test: `tests/test_psd.py`, **56 tests en verde**.
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
  - Test: `tests/test_psd_panel.py`, **27 tests en verde**.

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
  - Test: `tests/test_complexity.py`, **36 tests en verde**.
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
  - Test: `tests/test_connectivity.py`, **40 tests en verde**.
- [x] **`psglab/ui/metric_panel.py`** · una métrica por ventana a lo largo de la
      noche
  - **Sirve a los dos módulos**, porque los dos producen esa forma. Es lo que
    los dos docstrings piden: poder cruzarla con el hipnograma.
  - **Los NaN se dibujan como hueco y no como cero**, que es lo que hace
    utilizable la convención de la ventana incompleta: un cero es un valor de
    complejidad plausible y bajo, indistinguible a ojo de una medición real.
  - El eje va en **base 1**, como el histograma: desde 0 quedaría desplazado una
    ventana respecto de él.
  - Test: `tests/test_metric_panel.py`, **29 tests en verde**.
- [x] **`psglab/ui/connectivity_panel.py`** · el mapa de calor de la matriz
  - **La matriz es la salida real del requisito**: mostrar sólo su promedio
    diría cuánta conectividad hay pero no entre qué canales.
  - Los ejes llevan **los nombres de los canales**: sin eso el mapa es un cuadro
    de colores.
  - **La escala de color es fija de 0 a 1.** Con escala automática, dos ventanas
    con conectividades muy distintas se verían iguales, y comparar ventanas es
    justamente lo que el investigador hace.
  - Test: `tests/test_connectivity_panel.py`, **24 tests en verde**.

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
  - Test: `tests/test_ica.py`, **51 tests en verde**.
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
  - Test: `tests/test_ica_panel.py`, **30 tests en verde**.

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
  - Test: `tests/test_impedance.py`, **54 tests en verde**.
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
  - Test: `tests/test_impedance_panel.py`, **27 tests en verde**.

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
      el que se está viendo.
      - **Medido en el [hito 57](#hito-57-cuánta-memoria-cuesta-cada-cosa): guarda dos sólo después de un análisis**, y
        lo caro es otra cosa: ajustar la ICA, con 7 copias de pico. Las dos
        decisiones que salieron de medir están anotadas allá. Sobre 32 canales y 8 horas son 1,9 GB cada uno
      antes de empezar a analizar. Bajarlo de verdad pide otra cosa: leer por
      tramos, o releer el archivo al deshacer en vez de guardarlo. Las dos son
      decisiones de diseño con su propio costo.
- [x] **Nada corre fuera del hilo de la interfaz.** El cursor de espera avisa,
      pero la ventana sigue congelada. Un `QThread` para los barridos de la
      noche es la solución de fondo, y hoy el programa no tiene ninguno.
      - **Ya no es cierto**: la conectividad de la noche corre en otro hilo
        desde el [hito 42](#hito-42-lo-largo-deja-de-congelar-la-ventana), y
        ajustar la ICA desde el
        [hito 47](#hito-47-lo-caro-era-ajustar-y-no-cambia-la-señal). Lo que
        sigue en el de la interfaz cuesta décimas de segundo.

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

- [x] **El barrido de conectividad a lo largo de la noche no estaba en el menú.**
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

      **Se cerró en la fase 9 del refactor de la interfaz**, que lo ofrece:
      «Conectividad de la noche…» mide época por época y grafica en el panel de
      métrica el promedio de cada matriz, que es un número por época y se
      compara contra el hipnograma. Un test comprueba que cada época vale lo
      mismo que la conectividad de esa ventana pedida por el otro menú. La
      exención salió de `SOLO_BIBLIOTECA`.

### Lo que el chequeo sigue sin ver

- [ ] **El chequeo de caminos muertos recorre `analysis/`, y el camino muerto
      de hoy está en `exporters/`.** Desde el
      [hito 23](#hito-23-ajustes-de-la-barra-de-menú) ninguna acción de la
      barra llega a las ramas `annotations` ni `information` de
      `MainWindow.export()`: es la forma del hito 19 una capa más abajo, y la
      encontró leer el programa, no la red.
      - **La de anotaciones tiene camino desde el hito 33**, por el cartel del
        trabajo sin exportar; la de Informacion.txt sigue sin ninguno. Cerrarlo
        depende de lo que diga el cliente sobre el menú, en el hito 23.
        Revisado en el [hito 50](#hito-50-los-pendientes-revisados).

      **Extender la tabla a `exporters/` no lo habría atrapado**, y ésa es la
      parte que importa. `export_annotations` y `export_information` sí se
      llaman en `psglab/ui/`, dentro de ese método; lo que no existe es un
      camino desde un menú o un atajo hasta esa llamada. El chequeo mide uso
      del nombre en la capa, que es barato y alcanzaba para `derive_montage()`;
      medir esto otro es recorrer el grafo desde las acciones de `ui/menus.py`
      y `ui/shortcuts.py` hasta el método, y ahí hay que decidir cuánta
      indirección se sigue.

      Los tests tampoco lo señalan, y por una razón que conviene anotar:
      `tests/test_entrega.py` llama a `ventana.export("annotations", destino)`
      directamente, así que el requisito queda verificado sobre un camino que
      el investigador no puede recorrer.

      **Antes de escribir el chequeo hay que saber si esos dos archivos vuelven
      al menú**, que es lo que espera la respuesta del cliente anotada en el
      hito 23. Si vuelven, no queda ningún caso conocido y la pregunta pasa a
      ser si el chequeo se justifica igual.

---

## Hito 21: Limpieza

Los quince hallazgos menores de la auditoría del 8 de septiembre de 2026, que
son los que **ninguno solo justificaba un hito** y juntos sí. Ninguno rompía el
programa; casi todos eran de la misma clase: algo que dejó de ser cierto y nadie
volvió a mirar.

### Lo que se veía mal en la pantalla

- [x] **El hipnograma no dejaba en blanco lo no scoreado**, que es lo que pide
      V1_P. `altura.get(fase, 0)` mapeaba `UNSCORED` a cero, así que se dibujaba
      como una línea en la base y un tramo sin mirar se leía como una fase más.
      El `connect="finite"` que ya estaba puesto era **código muerto por
      construcción**: ningún valor podía ser no finito. Ahora se dibuja `NaN`,
      que es exactamente lo que ese parámetro omite.
- [x] **Tres slots sin `except`.** `_set_arousal`, `_set_visible_channels` y
      `_set_selected_channels` llamaban a `core/` sin atrapar `PsgLabError`, a
      diferencia de los otros catorce caminos. Desde un slot de Qt eso sale por
      consola y el usuario no ve nada, que es peor que un cartel.
- [x] **Dos cálculos largos sin cursor de espera**, con los números del hito 17:
      ICA 4,9 s y conectividad de una ventana 1,4 s sobre el registro real.

### Lo que estaba escrito de más o de menos

- [x] **La clave de las impedancias, escrita tres veces**, con la constante que
      existe para eso sin usar. Renombrarla habría cortado el enlace
      lector–escritor sin que ningún test lo notara.
- [x] **Cuatro imports muertos**, uno de ellos engañoso:
      `WindowOutOfRangeError` en `complexity.py` sugería una condición de error
      que ese módulo no puede producir.
- [x] **El único `assert` a nivel de módulo del proyecto**, que desaparece con
      `python -O`. La invariante que sostenía ahora tiene su test.
- [x] **`MIN_SAMPLES` no es "el equivalente del segmento de Welch"**: uno está
      en segundos y sube con la frecuencia, el otro es un número fijo de
      muestras, y por eso los dos módulos no descartan las mismas ventanas.
- [x] **`[]` significaba cosas opuestas en funciones hermanas.** Ahora `None` es
      "todos" y la lista vacía se rechaza en las cuatro.
- [x] **`read_scoring()` leía el archivo tres veces**, en tres momentos
      distintos.
- [x] **Siete frases de documentación**: los "tres conversores" que son cuatro,
      los dos diagramas de la ventana sin la barra de navegación, el docstring
      que atribuía una guarda al método equivocado, el chequeo de contratos que
      decía cubrir dos capas y cubre tres, el diagrama de capas con `analysis`
      suelto —y su texto, que decía que `ui/` tiene "dos dependencias" cuando
      son siete—, los "ocho módulos" de `analysis/` que son nueve, y la única
      frase agramatical del repositorio.

### El CI

- [x] **El `concurrency` no deduplicaba lo que su comentario decía.** Agrupaba
      por `github.ref`, que para un `push` vale `refs/heads/Add` y para un
      `pull_request` vale `refs/pull/N/merge`: grupos distintos, las dos
      corridas hasta el final. Ahora sale de la rama de origen.
- [x] **Los techos de versión, evaluados y descartados**, con el razonamiento
      escrito en `requirements.txt`. El `numpy<2.6` no es una protección
      preventiva sino una restricción que numba ya declara río arriba; no hay
      ninguna equivalente para PySide6, mne, scipy ni pyqtgraph. Un techo por
      las dudas bloquea actualizaciones de seguridad, necesita mantenimiento sin
      fecha y **no evita la rotura: la esconde**. La red que lo hace tolerable
      es el CI resolviendo de nuevo sobre seis combinaciones.

### Lo que este hito no toca

La deuda de diseño sigue anotada donde estaba, en el
[hito 18](#lo-que-sigue-sin-resolverse): la señal vive entera en memoria y la
ventana principal guarda dos copias, y nada corre fuera del hilo de la interfaz.
**No son limpieza.** Leer por tramos, releer el archivo al deshacer o meter un
`QThread` son decisiones de diseño con su propio costo, y cada una merece su
hito.

---

## Hito 22: Refactor de la interfaz

**Cerrado el 16 de septiembre de 2026.** Llevó la interfaz de una columna rígida
de paneles sobre fondo blanco a un visualizador al estilo de EDFbrowser: la
señal al centro, un color por canal, paneles acoplables, menús por dominio,
escala de tiempo libre y una ventana de configuración que el programa recuerda.

Se hizo en **diez fases**, cada una con la suite en verde, y entró en tres pull
requests: el #34 trae las fases 0 a 5 y las dos primeras partes de la 6; el
#36, el resto de la 6, la 7, un arreglo y la 8; el #38, la 9. La suite pasó de
2106 a 2683 tests.

**No tiene stubs que contar**: todo lo que entró es nuevo o reorganiza lo que ya
andaba. Lo que sí vale es la lección del [hito 9](#hito-9-lo-que-la-interfaz-no-consume):
cada fase se probó por la ventana y con el registro real de `data/`, y dos de
los errores de abajo aparecieron sólo así.

### Lo que se decidió antes de empezar

| Decisión | Elegido | Por qué |
|---|---|---|
| Qué se toma de EDFbrowser | La disposición y los nombres, nada más | Está bajo **GPL-2.0**: copiarle código o un icono obligaría a relicenciar el proyecto, que el pliego pide MIT. Es el mismo motivo por el que se descartó PyQt. Los iconos se dibujan con `QPainterPath`. |
| Escala de tiempo | Libre, de 10 ms al registro entero | La época de 30 s sigue siendo la unidad de scoring: lo que se separó es la página visible. |
| Menús | Sólo los que tienen contenido | «Timesync» y «Window» de la referencia no se crearon: un menú vacío es peor que ninguno. |
| Paneles | Acoplables | La señal a pantalla completa; todo lo demás se mueve, se apila o se cierra. |
| Preferencias | Un JSON en el perfil del usuario | No es `config.py`: aquél guarda lo que fija el pliego, y esto es lo que elige el usuario. |

Y tres constantes de la escala de tiempo, **confirmadas con el cliente** y
guardadas en `config.py` para que revertir cualquiera sea cambiar una línea:
`OCCUPANCY_CLEARS_ON_PAN` —desplazar la vista reancla las líneas de ocupación en
vez de borrarlas—, `MIN_VIEW_SECONDS` —10 ms— y `VIEW_TIMESCALE_PRESETS`
—de 0,2 s a una hora, y no las veintiocho de un visor universal—.

### Las fases

- [x] **Fase 0 — La red de seguridad.** Una lista congelada de la superficie
      pública de la ventana, que hasta ahí existía sólo implícita en las 1610
      líneas de `test_entrega.py`. Y la primera medición de cuánto tarda
      dibujar: 92 ms con 64 canales a 1000 Hz, cinco veces por debajo del
      umbral de usabilidad. Las tablas están en `docs/ARQUITECTURA.md`.
  - Test: `tests/test_main_window_layout.py`, **8 tests en verde**.
- [x] **Fase 1 — Esquemas de color y preferencias.** Cinco esquemas de fábrica
      —Claro, Oscuro, NK, Azul sobre gris y ECG— y un archivo que los recuerda.
      Las curvas no tenían pluma y salían todas del mismo gris; ahora cada
      canal toma su color. **El esquema Claro deja el programa exactamente como
      era.**
  - Test: `tests/test_theme.py`, **78 tests en verde**.
  - Test: `tests/test_preferences.py`, **68 tests en verde**.
- [x] **Fase 2 — Menús por dominio.** «Análisis» era el cajón de toda la Parte 2
      y se repartió: Montaje cambia de dónde viene cada canal, Filtrar cambia la
      forma de la señal y Analizar sólo mide. El test que miraba que existiera
      un menú «&Análisis» se reescribió para verificar cada acción, que es lo
      que protegía.
  - Test: `tests/test_menus.py`, **44 tests en verde**.
- [x] **Fase 3 — Paneles acoplables.** La señal es el widget central y los otros
      diez paneles se mueven, se apilan o se cierran; la disposición se guarda
      al cerrar. Los seis paneles de análisis conservaron el nombre de su
      atributo —un `QDockWidget` responde a `windowTitle()` igual que un
      diálogo— y **los 102 tests de `test_entrega.py` pasaron sin tocar
      ninguno**.
  - Test: `tests/test_docks.py`, **39 tests en verde**.
- [x] **Fase 4 — La barra inferior.** Primera, anterior, siguiente, última,
      amplitud y una franja que salta a cualquier punto de la noche.
      `navigation.py` salió de `SIN_TEST_PROPIO`. **Con esta fase cerró el MVP
      visual sin haber tocado `core/` ni `tools/`.**
  - Test: `tests/test_navigation.py`, **42 tests en verde**.
  - Test: `tests/test_icons.py`, **33 tests en verde**.
- [x] **Fase 5 — El menú Amplitud.** La primera fase que tocó `core/`: `Session`
      ganó el desplazamiento vertical por canal, para los que tienen la línea
      de base lejos del cero. El menú habla de «µV por carril» y no de
      «amplitud», porque subir ese número achica la onda.
- [x] **Fase 6 — Escala de tiempo libre.** La página visible pasó a ser un
      objeto propio, separado de la época. **Los métodos de mouse de
      `ViewerTool` reciben ahora segundos desde el inicio del registro**, y no
      desde el inicio de la ventana: el anotador filtraba por la época, y con
      una página de cuatro horas habría dibujado las bandas de una sola de las
      480. Sin borde de época en la cuenta, la deriva que hacía fallar 240 de
      960 ventanas a 256,125 Hz dejó de poder existir. Las flechas siguen
      siendo la época, que es V1_F de «Navegación»; desplazar tiene sus
      propias teclas.
  - Test: `tests/test_viewport.py`, **51 tests en verde**.
- [x] **Fase 7 — La envolvente.** Mínimo y máximo por columna de píxeles, que no
      puede perder un pico. El registro entero de prueba —22 horas— bajó de
      1749 ms a 444 ms la primera vez y a 14 ms las siguientes.
  - Test: `tests/test_decimation.py`, **41 tests en verde**.
- [x] **Fase 8 — La ventana de configuración.** Cinco solapas: Colores, Editor
      de anotaciones, Espectro de potencia, Otras y Tipografía. Todo se aplica
      en el momento. `psd.validate_band()` pasó a ser pública, para que la regla
      de qué banda es válida siga siendo una sola.
  - Test: `tests/test_settings_dialog.py`, **48 tests en verde**.
- [x] **Fase 9 — Cierre.** La conectividad de la noche entera, que era el
      pendiente del [hito 20](#hito-20-la-red). Los menús muestran los atajos
      sin registrarlos otra vez, F6 recorre los paneles, y el contraste de los
      esquemas se verifica contra WCAG 2.1.

### Lo que se encontró en el camino

Seis errores. **Dos venían de antes del refactor**, y la fase 0 los encontró al
armar la red:

- [x] **La tecla `2` dejaba de scorear después de cambiar de nomenclatura.**
      `install_shortcuts()` se llama tres veces y cada vez dejaba vivos los
      atajos anteriores; dos atajos con la misma tecla hacen que Qt no ejecute
      ninguno.
- [x] **Las curvas de complejidad del segundo canal en adelante eran
      invisibles.** `mkPen(None)` no es «el color por omisión» sino ninguna
      pluma.

**Los otros cuatro los introdujo el propio refactor**, y los encontró una fase
posterior:

- [x] **Desde la segunda época no se veía ningún nombre de canal.** Los nombres
      quedaban en x = 0, y con el eje en segundos absolutos el cero salía de la
      pantalla. Lo introdujo la fase 6; se escapó porque todos los tests de la
      vista miraban la época 0, que es la única donde no aparece.
- [x] **Un esquema con un color mal escrito terminaba en una traza.** Se
      comprobaba sólo que el color fuera texto, así que «gris oscuro» se
      cargaba sin quejas. Venía de la fase 1; lo encontró la 8, al agregar
      «Cargar esquema».
- [x] **Correr los tests podía pisar las preferencias reales** de quien los
      corría: elegir un esquema escribía el archivo sin mirar quién había
      abierto la ventana. Fase 1; lo encontró la 8.
- [x] **Dos esquemas de fábrica no llegaban al contraste mínimo**: el azul del
      Oscuro daba 2,42 y el dorado de Azul sobre gris, 2,41. Fase 1; lo
      encontró la 9, al medirlo por primera vez.

### Lo que sigue abierto

La ventana de configuración de la referencia tiene siete solapas y la de este
programa, cinco. **Las dos que faltan faltan a propósito**: una solapa que no
configura nada es una promesa que el programa no cumple. Cada una entra con lo
que configura, en su propio hito.

- [ ] **Cursores.** Configuraría las reglas que miden Δt y ΔµV sobre la señal,
      y esas reglas no existen. Entran como herramienta nueva en `tools/`,
      registrada con `@register_tool`.
- [ ] **Calibración.** Haría que un milímetro de pantalla sea un milímetro de
      papel, y nada del programa convierte todavía a milímetros.

**La deuda de diseño del [hito 18](#lo-que-sigue-sin-resolverse) sigue donde
estaba, con un cambio.** Dibujar una página ya no copia la señal, que es lo que
volvió dibujable el registro entero; pero la ventana principal sigue guardando
dos copias, y nada corre fuera del hilo de la interfaz. La conectividad de la
noche tarda 25 s sobre el registro de prueba con la ventana congelada: el
cursor de espera vuelve legible esa espera, no la acorta.

---

## Hito 23: Ajustes de la barra de menú

**Cerrado el 16 de septiembre de 2026.** Salió de probar el programa después
del [hito 22](#hito-22-refactor-de-la-interfaz): la barra de menú tenía
entradas que no agregaban nada, dos rutas demasiado profundas y una barra de
herramientas que repetía un menú. Y el scoring sólo entraba y salía en `.txt`.

**No tiene stubs que contar**, igual que el 22: todo lo que entró es nuevo o
reorganiza lo que ya andaba.

### Lo que cambió en la barra

- [x] **«Archivo» es un botón.** Le quedaba una sola acción —«Salir» se quitó,
      porque lo hace la cruz de la ventana—, así que es un icono de carpeta en
      la esquina izquierda, con realce al pasar el mouse y el atajo en el
      tooltip. La carpeta se dibuja en `ui/icons.py`, como las flechas.
- [x] **«Sesión» pasó a llamarse «Scoring»** e importa y exporta en `.txt`,
      `.csv`, `.edf` y `.xml`.
- [x] **Escala de tiempo** perdió «Acercar» y «Alejar», que siguen en Ctrl++ y
      Ctrl+-. En Escala de tiempo y en Amplitud, «Definida por el usuario…»
      pasó a «Personalizado…».
- [x] **«Paneles» es una entrada propia**, con «Restaurar la disposición», que
      antes estaba en «Ver». Mostrar u ocultar un panel quedaba a tres clics.
- [x] **No hay barra de herramientas.** Repetía el menú Herramientas justo
      debajo de la barra de menú; ahora ese menú es la única vía.
- [x] **«Configuración» abre su ventana de un clic.** El submenú de esquemas
      repetía la solapa Colores de esa misma ventana.
- [x] **La barra de menú deja de ser la nativa**, para que en macOS no
      desaparezcan el botón de abrir ni «Configuración», que no tiene submenú.
  - Test: `tests/test_menus.py`, **44 tests en verde**.
  - Test: `tests/test_icons.py`, **33 tests en verde**.

### El scoring en cuatro formatos

- [x] **`psglab/exporters/scoring_formats.py`** · V1_F "Archivo de salida"
  - CSV con el rótulo de la fase, que dice solo la nomenclatura; EDF+ de sólo
    anotaciones con los rótulos de la Sleep-EDF; y el XML del NSRR con un
    `<Nomenclature>` que sus lectores ignoran. **El EDF+ se escribe a mano**:
    MNE sólo lo exporta con `edfio`, y desde un `Raw`, que no puede tener cero
    canales.
- [x] **`psglab/readers/scoring_formats.py`** · V3_F "Importación"
  - Lee también lo que escriben otros programas. **Probado con el hipnograma
    real de la Sleep-EDF**: da las 2650 ventanas del registro, reconoce R&K
    por el estadio 4 sin preguntar, y descarta el «Sleep stage ?» del final,
    que se pasa de la señal casi dos horas.
  - Test: `tests/test_scoring_formats.py`, **65 tests en verde**.
- [x] **La nomenclatura se pregunta.** Un archivo que no la dice —incluido un
      `.txt` sin cabecera, que antes se rechazaba— eleva
      `UndeclaredNomenclatureError`, y la ventana ofrece las dos con la del
      registro abierto elegida. Adivinar sigue sin ser una opción.
  - Test: `tests/test_scoring_reader.py`, **38 tests en verde**.
- [x] `core/windows.py` ganó las dos conversiones entre un tramo de épocas y un
      evento en segundos. **Una época pertenece al evento que cubre su punto
      medio**, así que un redondeo del archivo no arrastra la vecina.
  - Test: `tests/test_windows.py`, **65 tests en verde**.

### Lo que se encontró en el camino

- [x] **Con el esquema Claro y Windows en modo oscuro, los iconos de la barra
      de navegación salían negros sobre negro.** Claro no aplica hoja de estilo
      y deja el aspecto nativo, que sigue al sistema. `theme.icon_ink()` elige
      la tinta, y la usan los dos lugares que dibujan iconos. Venía del hito
      22; apareció al dibujar el icono de abrir.
  - Test: `tests/test_theme.py`, **78 tests en verde**.

### Lo que queda por confirmar

- [ ] **Anotaciones.txt e Informacion.txt no están en el menú.** Se sacaron
      por decisión del usuario el 16 de septiembre, aunque el pliego los pide
      (V2_F, V3_F y V4_F de "Archivo de salida"). `MainWindow.export()` los
      sigue escribiendo y `test_entrega.py` lo verifica, pero del menú no se
      piden. **Hay que confirmarlo con el cliente**; devolverlos es una entrada
      por archivo en `ui/menus.py`.
      - **`Anotaciones.txt` tiene una vía desde que cerró el
        [hito 33](#hito-33-la-auditoría-del-19-de-septiembre)**: el cartel del
        trabajo sin exportar ofrece guardarlas antes de perderlas. Es una
        salida de emergencia y no un camino para pedirlas cuando uno quiere, así
        que no reemplaza la entrada de menú ni cierra este punto.
        `Informacion.txt` sigue sólo para un script.
- [ ] **Un EDF+ de R&K sin S4 ni MT pregunta la nomenclatura al volver a
      leerlo.** El EDF+ no tiene dónde declararla y «Sleep stage 2» se usa en
      las dos. AASM no pregunta, porque escribe «Sleep stage N2».

---

## Hito 24: Vista inicial y reproducción

**Cerrado el 17 de septiembre de 2026.** Tres pedidos del usuario después de
usar el programa con el [hito 23](#hito-23-ajustes-de-la-barra-de-menú): que
abra con la señal a pantalla casi completa, que haya botones para mover la
vista y no sólo la época, y un «play» que recorra el registro solo, como en
EDFbrowser.

**No tiene stubs que contar.** Lo que más costó no estaba pedido: al medir la
reproducción aparecieron dos errores del hito 22, abajo.

### Lo que se decidió

| Decisión | Elegido | Por qué |
|---|---|---|
| Vista al abrir | La señal y Canales, **siempre** | Pedido del usuario. Scoring, hipnograma y Übersicht le quitaban un cuarto de la pantalla; se abren desde «Paneles» |
| Recordar la disposición | **Ya no se recuerda** | Revisa la decisión del hito 22: con la vista limpia en cada apertura, guardarla no tenía quién la usara. `Preferences.window_state` se quitó, y un archivo de antes que la trae se sigue leyendo |
| Qué mueve «play» | Sólo la página | Pedido del usuario: reproducir es mirar, como Mayús+→. La época resaltada, que es lo que se scorea, no se mueve |
| Velocidades | 0,5× a 60×, arranca en 1× | 1× es la de EDFbrowser; a 30× pasa una época por segundo |
| Teclado | Espacio, **sólo con el foco en la señal** | En el resto de la ventana Espacio tilda una casilla o aprieta un botón |

### Lo que se hizo

- [x] **La vista inicial.** `ui/docks.py` oculta tres paneles más al armarlos;
      `apply_saved_layout()` pasó a `apply_saved_preferences()` y ya no
      restaura nada, y la ventana dejó de guardar la disposición al cerrar.
  - Test: `tests/test_docks.py`, **39 tests en verde**.
  - Test: `tests/test_preferences.py`, **68 tests en verde**.
- [x] **Los botones de página.** ≪ ‹ › ≫ en la barra de abajo, con chevrones
      para que no se confundan con los triángulos de la época.
      `Viewport.at_start` y `Viewport.at_end` dicen cuándo apagarlos.
  - Test: `tests/test_navigation.py`, **42 tests en verde**.
  - Test: `tests/test_icons.py`, **33 tests en verde**.
  - Test: `tests/test_viewport.py`, **51 tests en verde**.
- [x] **`psglab/ui/playback.py`** · V1_F "Navegación"
  - Un reloj que mide el tiempo real y avisa cuánto avanzar; mover la página
    es de la ventana, con `Viewport.panned()`. **Mide en vez de contar
    pasos**: si dibujar tarda más que el paso, la velocidad sigue siendo la
    pedida. El paso se limita a un segundo, para que una pausa de la máquina
    no haga saltar la vista.
  - Se detiene al llegar al final, al abrir otro registro y cuando un
    análisis cambia la señal. No arranca con el registro entero en pantalla.
  - Test: `tests/test_playback.py`, **31 tests en verde**.
  - Test: `tests/test_shortcuts.py`, **35 tests en verde**.
  - Test: `tests/test_main_window_layout.py`, **8 tests en verde**.

### Lo que se encontró en el camino

La primera medición dio **4,4 cuadros por segundo** con una página de 30 s
del registro real, que tiene siete canales a 100 Hz: la reproducción se veía
a saltos. Y la captura para verificarla mostró la señal cortada.

- [x] **La grilla se recreaba entera en cada movimiento de la página.** Setenta
      líneas borradas y setenta creadas: 45 de los 52 ms de cada paso. Ahora
      se reusan y sólo cambian de lugar. Quedaron además **debajo de la
      señal** y no encima, con un `zValue` por serie: al reusarlas, el orden de
      creación dejó de ser una garantía. Venía del hito 22.
- [x] **La señal se dibujaba cortada al 75 % de la página, con una recta al
      final.** `min_max_envelope()` calculaba el tamaño de cubeta con división
      entera: 3000 muestras sobre 1120 columnas daban cubetas de 2 que cubrían
      2240, y los últimos 7,6 s quedaban reducidos a dos puntos. Se redondea
      hacia arriba. Venía de la fase 7 del hito 22, y se escapó porque los
      tests usaban señales que dividían justo.
  - Test: `tests/test_decimation.py`, **41 tests en verde**.

Con las dos correcciones, un paso tarda **48 ms con una página de 30 s y 63
ms con una de 5 min o una hora**: unos 21 y 16 cuadros por segundo, medidos
sobre el registro de `data/`.

### Lo que sigue abierto

- [x] **La reproducción corre en el hilo de la interfaz**, como todo el
      dibujo; es la deuda del [hito 18](#lo-que-sigue-sin-resolverse). Con 32
      canales a 1000 Hz no hay medición todavía, y el reloj compensa con pasos
      más largos, así que se vería menos fluida pero a la velocidad elegida.
      - **La medición existe desde el hito 49**, y lo que queda es el mismo
        pendiente que «Un registro denso llega justo», del [hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar), donde se
        sigue. Revisado en el [hito 50](#hito-50-los-pendientes-revisados).
- [x] **El hipnograma quedaba angosto al abrir los tres paneles de abajo.**
      `docks.py` les pedía 250, 400 y 900 px, pero la Übersicht no bajaba de
      480 y el scoring de 690: en una pantalla de 1400 px el hipnograma recibía
      unos 230. Pasaba desde el hito 22. **Resuelto el mismo día**, en tres
      partes:
      - El ancho de la Übersicht (V2_F) es el preferido y no el mínimo, que
        bajó a 120 px.
      - El scoring tiene mínimos propios —40 px por botón, 72 el selector— y
        el selector muestra «R&K» en vez del nombre entero, que queda en el
        tooltip. Pasó de 868 px a unos 460 con Rechtschaffen y Kales.
      - Qt no recordaba el reparto pedido mientras los paneles estaban
        ocultos, así que `repartir_abajo()` lo vuelve a aplicar cada vez que
        uno aparece.

      Con 1400 px el hipnograma recibe ahora unos 690, el más ancho de los
      tres.
  - Test: `tests/test_docks.py`, **39 tests en verde**.

---

## Hito 25: Rendimiento al abrir y al desplazar

**Cerrado el 17 de septiembre de 2026.** La reproducción del
[hito 24](#hito-24-vista-inicial-y-reproducción) se veía a saltos y abrir un
registro congela la ventana varios segundos sin avisar nada.

**No tiene stubs que contar.** Lo que tiene es una medición: sin ella, dos de
las tres cosas que se hicieron habrían sido las equivocadas.

### Lo que se midió antes de tocar nada

Con el registro real de `data/` —7 canales a 100 Hz, 22 h— en una ventana de
1400×800, un paso de reproducción de una página de 30 s tardaba **113 ms**. El
mismo paso, con el fondo «sin líneas», **57 ms**: o sea que **la grilla sola se
llevaba la mitad**, unos 0,8 ms por línea y por cuadro. Cada línea era una
`pg.InfiniteLine`, y cada objeto de pyqtgraph recalcula su rectángulo, consulta
la escala del gráfico y se pinta por separado.

En un banco aparte, sin nada del programa, mover 72 líneas y el eje cuesta
**67,5 ms** como objetos sueltos y **22,1 ms** dibujadas en uno solo.

Arreglada la grilla quedaba un segundo hallazgo, y éste no se veía sin
contar repintados: **la señal se repintaba dos veces por cuadro**. La
bisección, con un filtro de eventos sobre el visualizador, dio una sola
línea: `_marcar_epoca()` sacaba la banda de la escena y armaba otra en cada
dibujo, y el segundo cambio de escena llega cuando el primer repintado ya
empezó. Un `LinearRegionItem` es además un ítem compuesto, así que eran tres
objetos por cuadro para mover un rectángulo que casi nunca cambia: la época
no se mueve al reproducir.

Con eso, lo único que quedaba pesando eran **las curvas**: un paso sin
dibujarlas cuesta 0,1 ms y con ellas 28. Ahí la pregunta era cuál de las dos
clases de pyqtgraph usar. `PlotDataItem` es un envoltorio que además maneja
puntos, relleno y decimación propia, y nada de eso se usa acá.

### Lo que se hizo

- [x] **La grilla es un solo objeto de la escena.** `GridBackground` arma una
      lista de `GridLine` —dónde cae cada una, en qué sentido y de qué color— y
      un único `_LineasDeFondo` las dibuja todas en su `paint()`. **Las líneas
      de cero de los canales se mudaron ahí**: eran otra `InfiniteLine` por
      canal, con el mismo costo.
  - Test: `tests/test_grid.py`, **19 tests en verde**, con el de regresión que
    exige que sea **un** objeto y no uno por línea.
- [x] **La banda de la época se mueve, no se rehace.** Se crea una vez y
      después sólo se le pide el rango, que además casi siempre es el mismo.
      Con eso el repintado por cuadro pasó de 2,00 a 1,00, medido con el
      filtro de eventos.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.
- [x] **Las curvas son `PlotCurveItem` y no `PlotDataItem`.** Medido
      intercalando las dos clases en el mismo proceso, que es la única forma
      de comparar en una máquina que varía: 28 ms contra 19 con el registro
      de prueba, y 68 contra 58 con 32 canales a 1000 Hz. El dibujo es el
      mismo píxel por píxel.
- [x] **La conversión a microvoltios de los lectores es en sitio.**
      `to_microvolts()` devolvía un array nuevo por canal; sobre el registro de
      prueba son 286 ms de copias que se descartan enseguida, contra 61 ms
      multiplicando en sitio. El factor sale del mismo lugar de siempre,
      `utils.units.conversion_factor()`.
- [x] **Abrir un registro avisa.** `open_recording()` usa el mismo
      `_trabajando()` que los análisis: cursor de espera y el nombre del
      archivo en la barra de estado. La espera no se acorta —MNE se lleva 2,6
      de los 4,3 s—, pero deja de leerse como que el programa se colgó.
- [x] **`tests/medir_rendimiento.py`**, el banco de medición. No es un test y
      pytest no lo recolecta: se corre con `python -m tests.medir_rendimiento`
      e imprime una tabla. Los tiempos dependen de la máquina, así que **una
      cota en segundos como test se pondría roja en la máquina de otro sin que
      nadie sepa si empeoró el programa o el día**.

### Lo que se ganó, medido con el banco

Mediana de 40 cuadros, misma máquina, misma ventana de 1400×800:

Las dos corridas, una detrás de la otra y con la máquina en el mismo estado.
**Eso último no es un detalle**: la misma medición dio 118 ms con el equipo
ocupado sincronizando archivos y 56 con el equipo libre, así que un número de
este banco sólo vale contra otro de la misma tanda.

| Página | Antes | Después |
|---|---|---|
| 7 canales a 100 Hz, 5 s | 32,7 ms | 11,5 ms |
| 7 canales a 100 Hz, **30 s** | **56,3 ms** | **17,5 ms** |
| 7 canales a 100 Hz, 5 min | 16,6 ms | 14,3 ms |
| 7 canales a 100 Hz, registro entero | 24,1 ms | 21,0 ms |
| 32 canales a 1000 Hz, 5 s | 71,5 ms | 37,8 ms |
| 32 canales a 1000 Hz, **30 s** | **109,1 ms** | **44,4 ms** |
| 32 canales a 1000 Hz, 5 min | 37,4 ms | 28,1 ms |
| 32 canales a 1000 Hz, registro entero | 46,2 ms | 30,6 ms |

La página de 30 s es la que importa: es la que el programa abre y la que se
usa para scorear. Pasó de 17,8 a **57 cuadros por segundo** con el registro de
prueba, y el reloj de la reproducción pide 25. Con 32 canales a 1000 Hz quedan
22,5, que es casi.

### Lo que sigue abierto

- [ ] **Un registro denso llega justo** —y desde el
      [hito 49](#hito-49-la-envolvente-se-calcula-una-vez) es lo único que le
      queda: calcular la envolvente dejó de pesar—: 44 ms por cuadro con 32
      canales a 1000 Hz, contra los 40 que pide el reloj. Casi todo eso es rasterizar
      71 000 puntos de trazo. Las dos salidas que quedan son dibujar menos
      puntos —una pareja de envolvente cada dos píxeles en vez de cada uno, que
      **se midió en −25 % y se descartó**: bajar la resolución horizontal del
      trazado es una decisión clínica y el usuario eligió no tomarla— o sacar
      el dibujo del hilo de la interfaz.
- [x] (Decidido en el hito 25: no se usa.) **OpenGL se probó y no sirvió.** `useOpenGL` dio 30 ms contra 19 con el
      registro de prueba y 66 contra 58 con el denso: en este dibujo —muchas
      polilíneas cortas— el camino por GPU cuesta más de lo que ahorra. Queda
      anotado para que no se vuelva a proponer sin medirlo.
- [x] (Decidido en el hito 25: por ahora no.) **La lectura sigue siendo de
      MNE**, 2,6 s de los 4,3. Un lector propio
      con numpy para el caso simple bajaría eso a medio segundo, y es un parser
      nuevo que hay que mantener: **la decisión fue no hacerlo por ahora**.
      La copia que hace `crudo.get_data()` —300 ms— tampoco se puede evitar:
      la versión de MNE que fija `requirements.txt` no ofrece leer sin copiar,
      y leerle el array privado sería atarse a un detalle interno suyo.

---

## Hito 26: El diseño de la ventana

**Cerrado el 18 de septiembre de 2026.** Salió de un lienzo de diseño,
«Disposición de la ventana principal», que retrató la ventana en sus tres
estados —al abrir, scoreando y analizando— y midió cuánto recibe cada panel con
`tests/medir_reparto.py`. **Casi todo lo que dibujó ya existía**; lo que midió
dejó dos problemas de verdad, y además propuso un aspecto y dos detalles. Se
implementaron las cuatro cosas.

**No tiene stubs que contar.** Lo que tiene son mediciones de antes y después,
todas con el registro de prueba en una ventana nativa: los mínimos salen de
métricas de fuente y el plugin offscreen de la suite daría otros.

### El reparto de abajo

- [x] **El scoring va en dos filas**: el selector y el arousal arriba, las fases
      debajo y un pie al final. En una sola fila el mínimo era la suma de todo,
      más de lo que `ANCHOS_DE_ABAJO` le pedía, así que el scoring se quedaba
      siempre en su mínimo y **el 400 de la proporción no se usaba nunca**.
      Apilado, el mínimo es el de la fila más ancha.

      | | Antes | Ahora |
      |---|---|---|
      | Mínimo del scoring, R&K | 464 px | 312 px |
      | Mínimo del scoring, AASM | 376 px | 224 px |
      | Ventana de 1400: Übersicht, scoring, hipnograma | 203 / 464 / 729 | 225 / 360 / 811 |
      | Ventana de 1280 | 177 / 464 / 635 | 206 / 329 / 741 |

      A 1400 y 1280 manda la proporción entera. El mínimo del scoring recién
      aparece por debajo de unos 1210 px.
  - Test: `tests/test_docks.py`, **39 tests en verde**, con el hipnograma como
    el más ancho también a 1280.

### La pila de análisis

- [x] **`repartir_derecha()` le da el 30 % del ancho** al abrir un panel de
      análisis. Hasta acá lo decidía Qt, y le daba a la pila más lugar que a
      la señal que el panel estaba explicando:

      | | Pila | Señal |
      |---|---|---|
      | 1400, antes | 640 px | 478 px |
      | 1400, ahora | 420 px | 698 px |
      | 1280, antes | 640 px | 358 px |
      | 1280, ahora | 384 px | 614 px |

      El mínimo del panel manda si es mayor: el de Impedancia, el más ancho de
      los seis, es de 380. **El pedido va en la vuelta siguiente del ciclo de
      eventos**: la primera vez que la pila aparece, Qt todavía no la ubicó
      cuando llega el aviso, y su primer acomodo pisaba lo pedido.
  - El banco `tests/medir_reparto.py` mide ahora también la derecha.

### El aspecto del lienzo

- [x] **El esquema «Papel»**: las áreas de dibujo en blanco y la ventana
      alrededor en un gris cálido. **No reemplaza a Claro**, que sigue sin hoja
      de estilo y sigue siendo el de fábrica. `ColorScheme` gana `chrome`, el
      fondo de la ventana, y `numeric_font`, la tipografía de las lecturas
      numéricas; vacíos, la hoja de estilo sale idéntica a la de antes.
      Intercalados en el mismo proceso, un paso de reproducción de 30 s dio
      17,5–22,2 ms con Claro y 13,1–21,0 con Papel: la hoja no cuesta
      repintado.
  - Test: `tests/test_theme.py`, **78 tests en verde**.
  - Test: `tests/test_settings_dialog.py`, **48 tests en verde**, con el
    botón nuevo de «Fondo de la ventana».
- [x] **Las tipografías IBM Plex**, Sans y Mono, en `psglab/resources/fonts/`
      con su licencia, la OFL 1.1. `ui/fonts.py` las registra al arrancar; si
      faltan, el programa arranca igual. El control de licencias del CI no las
      ve, porque sólo mira pip: están anotadas en `docs/ARQUITECTURA.md`.
  - Test: `tests/test_fonts.py`, **19 tests en verde**.

### Los detalles

- [x] **El pie del scoring**: «Ventana 137 · S2», «sin scorear» en vez del
      guion con que se guarda, y «· arousal» si está marcado. Repite lo que
      dicen las barras de navegación y de estado a propósito: el panel se puede
      sacar a otra pantalla, donde ninguna de las dos se ve.
      `scoring_panel.py` sale de `SIN_TEST_PROPIO`.
  - Test: `tests/test_scoring_panel.py`, **27 tests en verde**.
- [x] **El espectro dice con qué se estimó**: «Welch · segmentos de 4 s · Hann
      · solape 50 %». La ventana y el solape de Welch pasan a ser constantes
      explícitas —son los valores por defecto de scipy, así que el espectro no
      cambia, y hay un test que lo compara— y `describe_method()` arma la línea
      con ellas. Del multitaper no afirma un ancho de banda, porque lo fija MNE.
  - Test: `tests/test_psd.py`, **56 tests en verde**.
  - Test: `tests/test_psd_panel.py`, **27 tests en verde**.

### Lo que sigue abierto

- [x] **Papel dibuja todas las señales en negro**, como el lienzo, y Claro las
      varía por canal. Es una decisión visual: el interruptor está en Colores,
      y si el laboratorio prefiere colores, es cambiar un campo del esquema.
      - **Ya no existe**: el [hito 35](#hito-35-dos-esquemas-y-ninguna-perilla)
        dejó dos esquemas, Sereno y Nocturno, sin solapa Colores. Revisado en
        el [hito 50](#hito-50-los-pendientes-revisados).
- [x] (Decidido en el hito 24: la disposición no se guarda.) **Un ancho de
      pila arrastrado a mano vuelve al 30 %** al abrir otro panel
      de análisis, igual que abajo vuelve la proporción. Recordarlo sería
      guardar la disposición, que el hito 24 decidió no hacer.

---

## Hito 27: La navegación desde el medio

**Cerrado el 18 de septiembre de 2026.** Dos pedidos del usuario sobre la barra
de abajo: que queden sólo ocho controles —primera ventana, anterior,
reproducir/pausar, siguiente, última, velocidad, menos y más amplitud— y que
**el recorrido de la reproducción se cuente desde el medio del gráfico**. Al
aclararlo decidió cuatro cosas: la época sigue al medio mientras se reproduce;
anterior y siguiente centran sólo reproduciendo; los atajos de página se
quedan; y el cursor recorre también los bordes del registro.

**Revierte una decisión del [hito 24](#hito-24-vista-inicial-y-reproducción)**:
«reproducir no toca la época». La fijaba un test,
`test_reproducir_avanza_la_pagina_y_no_la_epoca`, que pasó a afirmar lo
contrario. En pausa sigue valiendo lo de siempre: las flechas mueven la página
lo mínimo.

**No tiene stubs que contar.**

### La barra

- [x] **Ocho controles, en el orden pedido**, con reproducir entre las dos
      flechas. Salieron los cuatro botones de página (≪ ‹ › ≫), su señal
      `page_pan_requested` y `set_page_bounds()`, que sólo existían para
      apagarlos, y sus cuatro chevrones de `icons.py`. Reproducir queda
      habilitado siempre que haya registro. Mover la vista sin mover la época
      sigue en Mayús+← → y Ctrl+← →.
  - Test: `tests/test_navigation.py`, **42 tests en verde**.
  - Test: `tests/test_icons.py`, **33 tests en verde**.

### El cursor

- [x] **`Session.move_playhead()`**: la página se centra en el instante —en los
      bordes la recorta el `Viewport` y el instante queda adentro, fuera del
      medio— y la época actual es la que lo contiene. Avisa del cambio de época
      una sola vez y devuelve el instante recortado, para que la interfaz no
      repita el recorte. No llama a `_seguir_a_la_epoca()`: con una página de
      menos de 30 s, `containing()` la sacaría del medio.
  - Test: `tests/test_session.py`, **156 tests en verde**.
  - Test: `tests/test_contratos.py`, **1043 tests en verde**, con su
    fila en `CONTRATOS` y en `RECHAZOS_OBLIGATORIOS`: un NaN no puede pasar.
- [x] **Una línea marca el cursor**, creada una vez y después movida, por la
      regla del hito 25. `mark_window()` mueve la banda de la época sin tocar la
      página, y **mientras se ve el cursor `show_window()` no mueve la
      página**: con la de 30 s centrada, la época no entra entera, y scorear o
      cambiar la amplitud la sacaban del medio hasta el paso siguiente.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.
- [x] **La ventana**: la reproducción arranca en el centro de la época actual
      —con la página de 30 s no salta—, cada paso lleva el cursor y redibuja
      sólo lo que cambió, y se detiene al final del registro y no al de la
      página. Reproduciendo, las flechas, la franja, el hipnograma y los atajos
      de página llevan el cursor y la reproducción sigue. `refresh()` se partió:
      `_reflejar_epoca()` es la mitad que la reproducción necesita sola.
  - Test: `tests/test_entrega.py`, **316 tests en verde**.

### Lo que se midió

Intercalando los dos bancos en la misma corrida, un paso con 7 canales a
100 Hz: con la página de 30 s, 13,8 ms antes y 15,8 y 15,6 después; con la de
300 s, 14,7 contra 17,2 y 16,6. **El cursor cuesta unos 2 ms por cuadro**,
lejos de los 40 que pide el reloj. Con 32 canales la diferencia queda dentro
del ruido.

**El banco tuvo que cambiar.** `tests/medir_rendimiento.py` avanza con
`_avanzar_reproduccion()` sin arrancar la reproducción, así que el cursor
quedaba de una escala a la siguiente, llegaba al final del registro y el paso
no dibujaba nada: medía 0,0 ms. Ahora cada escala arranca con el cursor en el
medio de la página y avanza un quincuagésimo de página por paso, sin llegar al
borde.

### Lo que sigue abierto

- [x] **Con 32 canales a 1000 Hz, un paso con página de 5 min cuesta unos
      90 ms** —resuelto en el [hito 49](#hito-49-la-envolvente-se-calcula-una-vez)—, antes y después de este hito: más del doble de lo que pide el
      reloj. Lo destapó el banco corregido. El de antes llegaba al final del
      registro a los ocho pasos y medía el redibujo de una página quieta, que
      sale de la caché de envolventes: de ahí los 28 ms de la tabla del
      [hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar).
- [ ] **Reproducir arranca desde la época actual y no desde lo que se ve.** Si
      en pausa se movió la vista con Mayús+→, la reproducción vuelve a la
      época que se está scoreando. Es a propósito —la época es lo que se
      scorea— y queda anotado por si el laboratorio prefiere lo otro.

---

## Hito 28: Un solo menú de herramientas

**Cerrado el 18 de septiembre de 2026.** Pedido del usuario: los menús
«Paneles» y «Herramientas» se repetían, y tenían que quedar en uno solo,
llamado «Herramientas». La Übersicht estaba en los dos, y el hipnograma también,
con dos nombres —«Histograma» en uno, «Hipnograma» en el otro—.

**No era sólo una repetición: los dos menús decían cosas distintas.**
`OverviewTool` y `HistogramTool` son herramientas-panel (`exclusive = False`) y
se prenden solas al abrir un registro, pero desde el
[hito 24](#hito-24-vista-inicial-y-reproducción) sus paneles arrancan ocultos.
Así, «Herramientas» las mostraba tildadas y «Paneles» destildadas, y apagar la
herramienta con el panel a la vista lo dejaba vacío.

Al aclararlo el usuario eligió el nombre «Hipnograma», que los seis paneles de
análisis se queden en su propio bloque, un menú plano con separadores y que
«Herramientas» conserve su lugar en la barra.

**No tiene stubs que contar.**

- [x] **Un menú en cuatro bloques**: los modos del mouse —Anotar, Lupa,
      Ocupación, Banda de amplitud—, los paneles de trabajo —Canales,
      Übersicht, Scoring, Hipnograma—, los de análisis y «Restaurar la
      disposición». La barra pasa de once menús a diez.
- [x] **La regla que evita el duplicado no es una lista**: una herramienta que
      se llama igual que una clave de `window.docks` se muestra con su panel y
      no recibe entrada propia. `menus._herramientas()` pone los paneles
      recorriendo los docks, y `_build_tools_menu()` inserta arriba los modos
      que salen del registro. Una herramienta con panel que se agregue cae sola
      en la misma regla.
- [x] **Las herramientas-panel quedan siempre prendidas con un registro
      abierto**, como ya hacía `_activate_panel_tools()`. Lo que se prende y se
      apaga es el panel, y desaparece el estado «panel a la vista con la
      herramienta apagada».
- [x] `HistogramTool.label` pasa a «Hipnograma». El módulo, la clase y los IDs
      del pliego siguen diciendo «histograma»: son identificadores y
      trazabilidad.
  - Test: `tests/test_menus.py`, **44 tests en verde**, con que
    ningún texto se repita y que la Übersicht y el hipnograma sean las acciones
    de sus paneles.
  - Test: `tests/test_entrega.py`, **316 tests en verde**: tildar
    un panel desde Herramientas lo muestra con contenido, y destildarlo sólo lo
    oculta.

### Corrección: la selección de «Anotar» arrancaba a la derecha del mouse

Reportado por el usuario al probar la herramienta. **Afectaba a todas las
herramientas del mouse, no sólo al anotador**, y al clic del hipnograma.
`MainWindow.eventFilter()` tomaba `evento.scenePosition()` como si fuera la
escena de pyqtgraph, y en un `QMouseEvent` de widget es la **ventana de primer
nivel**: traía sumado todo lo que hay a la izquierda del gráfico. Con el
selector de canales abierto eran 280 px, unos 7,5 s en una página de 30 s. En
vertical pasaba lo mismo con la barra de menú, así que la lupa y la banda de
amplitud también quedaban corridas.

- [x] **La posición la convierte la vista**, con `_en_escena()`, que es
      `mapToScene(evento.position())`. Se usa en el visualizador y en el
      hipnograma.
- [x] **El test no podía verlo**: `arrastrar()` armaba el evento con las tres
      posiciones iguales. Ahora lo arma como Qt, con `scenePosition()` relativa
      a la ventana.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con que la
    anotación empiece y termine a un píxel del mouse. Falla sin la corrección,
    corrida 7,5 s.

### Las anotaciones, de punta a punta

Revisando si el anotador funcionaba entero aparecieron tres huecos más. El
usuario decidió que **las anotaciones se ven siempre** y que **se borran con el
clic derecho**.

- [x] **Las bandas no seguían a la página.** Sólo se repintaban cuando una
      herramienta avisaba, y el anotador no escucha `on_view_changed()`: al
      pasar de época con la flecha quedaban las de la página anterior. La
      ventana escucha ahora el cambio de página y **redibuja sólo si cambió qué
      bandas van**. La reproducción mueve la página en cada cuadro, y las
      bandas están en segundos absolutos, así que en general no cambian.
- [x] **Se veía lo de la última herramienta que avisó**, aunque estuviera
      apagada: activar la lupa, o que la ocupación se reanclara al desplazarse,
      borraba las anotaciones de la pantalla. `_redibujar_overlays()` compone
      siempre las bandas de `annotation_bands()` con los overlays de la
      herramienta activa.
- [x] **No se podía borrar una anotación desde la ventana**:
      `AnnotatorTool.delete_annotation()` existía y nada de `ui/` la llamaba.
      Con «Anotar» activo, el clic derecho sobre una banda la borra, previa
      confirmación porque no hay deshacer. Entre dos superpuestas se borra la
      más corta, que es la que no se puede señalar en ningún otro lugar.
  - Test: `tests/test_annotator.py`, **41 tests en verde**, con
    `annotation_at()` y las bandas sin la herramienta activada.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con eventos de Qt
    de verdad: las bandas al ir y volver de época con cada herramienta, y el
    clic derecho con la confirmación aceptada, rechazada y con otra
    herramienta activa. Fallan con la ventana anterior.

### Lo que sigue abierto

- [x] **Una anotación no se puede corregir**, sólo borrar y volver a hacer:
      cambiarle la clase o arrastrar sus bordes queda para cuando el
      laboratorio lo pida.
      - **Lo hizo el [hito 52](#hito-52-una-anotación-se-puede-corregir)**: el clic derecho abre un menú para cambiar la
        clase, y con «Anotar» activo los bordes se arrastran.
- [x] **La red del hito 20 no mira `tools/`.** Recorre las funciones públicas
      de `analysis/`, así que `delete_annotation()` quedó sin
      ningún camino desde la ventana sin que nada fallara.
      - **La cerró el [hito 30](#hito-30-las-decisiones-de-la-verificación)**,
        que extendió la red a los métodos de `tools/` y de los paneles.
        Revisado en el [hito 50](#hito-50-los-pendientes-revisados).

---

## Hito 29: Verificación de las herramientas

**Cerrado el 19 de septiembre de 2026.** Pedido del usuario: verificar que la
Übersicht, el scoring, el hipnograma y los seis paneles de análisis funcionen,
no tengan fugas y no tengan implementaciones que nadie use. Lo motivó el
anotador, que parecía terminado y tenía cuatro fallas que la suite no veía (ver
el [hito 28](#hito-28-un-solo-menú-de-herramientas)).

**Cómo se buscó**, porque es lo que se puede repetir: una red automática de
métodos públicos sin llamada, ahora también en `tools/` y en los paneles; un
recorrido por la ventana con clics mandados por la ventana nativa y no
fabricados; y tres clases de fuga. Las tres son memoria —un `weakref` al
registro anterior después de abrir otro, y veinte ciclos con `tracemalloc`—,
estado que pasa de un registro a otro, y excepciones que salen de un slot de Qt,
capturadas con `sys.excepthook` porque PySide6 las imprime y sigue.

**Lo que anda.** Ninguna traza sin atrapar con canal plano, un solo EEG, un
registro más corto que una época, 100 Hz o un archivo de impedancias mal
formado. Veinte ciclos de abrir y usar todo dejan estables los atajos, los
listeners, los ítems de cada gráfico y la memoria. Las tres vías de impedancia
llegan a la ventana.

**No tiene stubs que contar.**

- [x] **Abrir otro registro dejaba vivo el anterior.** El anotador y la
      ocupación guardaban la sesión al apagarse; con dos noches grandes, el
      doble de memoria. Ahora la sueltan, como las otras cuatro. La regla quedó
      en `psglab/tools/README.md`.
- [x] **Las líneas de la ocupación pasaban al registro nuevo**, con su
      porcentaje, aunque eran fracciones de una página de otra señal. Se
      descartan al activarla sobre otro registro, y se conservan si es el mismo.
- [x] **Los paneles de análisis mostraban el registro anterior.** El espectro
      decía «Espectro de «C3»» sobre un registro sin C3; la tabla de
      impedancias listaba los canales viejos con el informe de los nuevos; y el
      panel de filtros conservaba los sugeridos, así que en un registro de
      100 Hz «Aplicar» pedía el notch de 50 Hz. Al abrir un registro se vacían
      los resultados y se cargan filtros e impedancias del nuevo. Los
      `clear_*()` de los paneles existían y sólo los llamaban los tests.
- [x] **«Aplicar» sin ningún filtro reemplazaba la señal** por una copia
      idéntica: decía «Se filtró la señal», habilitaba volver a la original y
      descartaba la ICA ya ajustada. Pasaba al mostrar el panel desde
      «Herramientas» sin cargarlo. Ahora avisa y no toca nada; la regla es
      `FilterSettings.is_empty`.
- [x] **El clic del hipnograma no tenía ningún test con eventos**, y tenía el
      mismo error que el anotador hasta el hito 28: con los tres paneles de
      abajo a la vista, caía en la época 4 en vez de la 3.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con dos registros
    de verdad. Los cinco fallan sin su corrección.
  - Test: `tests/test_occupancy.py`, **51 tests en verde**.
  - Test: `tests/test_annotator.py`, **41 tests en verde**.
  - Test: `tests/test_filters.py`, **54 tests en verde**.

### Lo que sigue abierto

Cuatro decisiones de comportamiento, con la recomendación que se le hizo al
usuario:

- [x] **Übersicht V3_F no tenía camino desde la ventana** (resuelto en el
      [hito 30](#hito-30-las-decisiones-de-la-verificación)).
      `OverviewTool.set_span()` no lo llama nadie: la cantidad de ventanas
      vecinas sólo se cambia editando `config.py`, y el pliego la pide
      configurable y asimétrica. Se recomendó llevarla a la ventana de
      configuración. `set_size()` tampoco se llama, pero V2_F se cumple
      arrastrando el borde del panel.
- [x] **Los resultados de análisis sobrevivían a un cambio de la señal**
      (resuelto en el hito 30).
      Después de filtrar, derivar o volver a la original, el espectro, la
      métrica y la conectividad siguen mostrando lo calculado sobre la señal
      anterior, sin decirlo. La ICA ya se descarta en ese caso; se recomendó
      hacer lo mismo con los otros tres.
- [x] **Espectro, métrica, conectividad e ICA se mostraban vacíos desde
      «Herramientas»** (resuelto en el hito 30), sin decir desde qué menú se piden. Se recomendó un
      texto que lo diga.
- [x] **La red de caminos muertos no miraba `tools/` ni los paneles**
      (resuelto en el hito 30).
      El script de este hito la extendió y encontró `set_span()` y
      `set_size()`; convertirlo en test exige una tabla de exenciones para los
      accesores de sólo lectura que usan los tests.
- [x] (Resuelto en el [hito 32](#hito-32-los-pendientes-del-todo).)
      **Resultados silenciosos con un canal plano**, sin traza pero sin
      explicación: el espectro sale vacío en escala logarítmica, Higuchi da
      `NaN` en todas las ventanas y la conectividad lo cuenta con 0 y baja el
      promedio. Importar un archivo de impedancias vacío no hace nada ni avisa.

---

## Hito 30: Las decisiones de la verificación

**Cerrado el 19 de septiembre de 2026.** Las cuatro decisiones que dejó abiertas
el [hito 29](#hito-29-verificación-de-las-herramientas). El usuario las tomó
todas con la recomendación que se le hizo.

**No tiene stubs que contar.**

- [x] **V3_F de la Übersicht, desde la configuración.** «Otras» tiene ahora dos
      grupos: lo que se aplica al abrir un registro y el panel de contexto, que
      se aplica enseguida. Ventanas anteriores y posteriores se eligen por
      separado, porque el pliego la pide asimétrica, de 0 a
      `MAX_OVERVIEW_WINDOWS` (5): con más, las ventanas del panel ya no se
      distinguen. Se guardan en las preferencias y `_aplicar_preferencias()`
      llama a `OverviewTool.set_span()`, que no tenía ningún camino.
- [x] **Cambiar la señal vacía los resultados.** Filtrar, derivar,
      re-referenciar, aplicar la ICA o volver a la original llama a
      `_olvidar_resultados()`, que vacía el espectro, la métrica y la
      conectividad con sus títulos. Es la regla que `_olvidar_ica()` ya aplicaba
      a la descomposición. Se vacían en vez de recalcularse, porque recalcular es
      trabajo que nadie pidió.
- [x] **Un panel vacío dice desde dónde se pide.** Espectro, métrica,
      conectividad e ICA muestran «Se pide desde Analizar › …» como título
      mientras no tienen resultado. La ruta se lee del menú armado con
      `menus.menu_path()` y no se escribe a mano, y un test la sigue en el menú
      de verdad: renombrar una entrada no puede dejar al panel mandando a buscar
      algo que no existe.
- [x] **La red de caminos muertos mira también `tools/` y los paneles**, con
      métodos y no sólo funciones: son `SIN_CAMINO_A_PROPOSITO` y
      `HUECOS_ABIERTOS` en `tests/test_consistencia.py`. Un hueco abierto no se
      exime: tiene que figurar por su nombre en este archivo.
  - Test: `tests/test_entrega.py`, **316 tests en verde**. Los siete nuevos
    fallan con la ventana anterior.
  - Test: `tests/test_preferences.py`, **68 tests en verde**.
  - Test: `tests/test_settings_dialog.py`, **48 tests en verde**.
  - Test: `tests/test_menus.py`, **44 tests en verde**.
  - Test: `tests/test_psd_panel.py`, **27 tests en verde**; y dos por panel en
    `tests/test_metric_panel.py` (**18 tests en verde**),
    `tests/test_connectivity_panel.py` (**16 tests en verde**) y
    `tests/test_ica_panel.py` (**22 tests en verde**).

### Lo que sigue abierto

La red nueva encontró cuatro métodos de herramientas sin camino desde la
ventana. **Son `HUECOS_ABIERTOS`**: hacen algo que el usuario podría querer, y
decidir si lo ofrece es del usuario.

- [x] (Resuelto en el hito 32.) **La lupa: `reset_count()`.** El contador de picos no se podía poner en
      cero, aunque `deactivate()` promete que para eso está. Además la cuenta
      pasa de un registro al siguiente, como pasaban las líneas de la ocupación
      hasta el hito 29.
- [x] (Resuelto en el hito 32.) **La banda de amplitud: `set_height_uv()`.** Su docstring la deja
      configurable porque hay criterios con otros umbrales que 75 µV, y la
      ventana no la ofrece.
- [x] (Resuelto en el hito 32.) **La lupa: `set_radius_seconds()` y `set_zoom()`.** El tamaño del círculo
      y el aumento no se pueden cambiar.

---

## Hito 31: El recorrido manual

**Cerrado el 19 de septiembre de 2026.** El usuario recorrió el programa con un
registro real después de los hitos 28 a 30. Anotar, el espectro y los filtros
anduvieron bien. Reportó cuatro cosas, y todas tenían una causa concreta que la
suite no podía ver: dependían del menú real, del arrastre del mouse o del
tiempo.

**No tiene stubs que contar.**

- [x] **Los nombres de «Herramientas» cambiaban al calcular algo.** La ventana
      le ponía al dock un título como «Espectro de «C3» — ventana 1», y Qt usa
      ese título como texto de la entrada del panel en el menú. La descripción
      va ahora en el gráfico, con `set_caption()` en los paneles de espectro,
      métrica y conectividad, donde el hito 30 ya ponía la pista con el panel
      vacío. Con más de seis canales, la conectividad de la noche los cuenta en
      vez de nombrarlos.
- [x] **La barra de color de la conectividad saltaba.** `ColorBarItem`
      redondea los extremos a enteros por omisión, y la escala va de 0 a 1:
      todo arrastre volvía a su lugar o saltaba al otro extremo. Ahora va de a
      centésimos y sin salir del rango. La imagen se dibuja con los niveles de
      la barra, así que el contraste que elige el usuario se conserva al pedir
      otra ventana; vaciar el panel lo vuelve a 0–1.
- [x] **Se podía editar el nombre de la fila en Filtrar**, y también en
      Impedancia, donde era un bug: `values()` toma el nombre del canal de esa
      celda, así que renombrarla asignaba la impedancia a un canal inexistente.
      `QTreeWidgetItem` no tiene permisos por columna; `FixedColumnDelegate`
      deja la primera columna fija en los dos paneles.
- [x] **La primera métrica congelaba la ventana.** `antropy` compila con
      `numba` al importarse: 7,3 s medidos en esta máquina, 21 s en la del
      hito 17. El usuario eligió precalentar: `main.py` pide
      `create_main_window(warm_up=True)`, que importa `antropy` en un hilo al
      arrancar. Medido: mientras compila, el hilo de la interfaz sigue
      respondiendo, con tirones ocasionales de hasta 65 ms, y leer dos
      registros tarda 3,4 s contra 3,3 s sin compilar. La suite no lo prende.
      **Lo que gana**, con el registro de `data/` (2650 épocas): la primera
      entropía de permutación tardaba 6,4 s y, con la compilación terminada,
      tarda 0,3 s. Pedida apenas abierto el registro todavía espera lo que le
      falta a la compilación: 4,6 s. Lempel-Ziv tarda 2,7 s por el cálculo en
      sí, compilado o no.
  - Test: `tests/test_entrega.py`, **316 tests en verde**: el menú no cambia
    después de los cuatro análisis, y `main.py` precalienta y la suite no.
  - Test: `tests/test_connectivity_panel.py`, **24 tests en verde**.
  - Test: `tests/test_filter_panel.py`, **26 tests en verde**, y
    `tests/test_impedance_panel.py`, **27 tests en verde**.
  - Test: `tests/test_complexity.py`, **36 tests en verde**.

### Lo que sigue abierto

- [x] (Decidido en el hito 32: se quedan así.) **Las demás operaciones largas siguen congelando la ventana**: leer un
      registro, la conectividad de la noche, la ICA. El usuario eligió
      precalentar y nada más; moverlas a otro hilo quedó descartado por ahora.
- [ ] **El hipnograma y la Übersicht no los pudo verificar el usuario**, porque
      no conoce su funcionamiento. Se le explicó cómo probarlos; queda por
      confirmar.
      - **Al probar la Übersicht encontró que no dibujaba señal**, y la
        terminó el [hito 51](#hito-51-la-übersicht-muestra-la-señal). Falta que confirme esa versión, y el hipnograma.

---

## Hito 32: Los pendientes del TODO

**Cerrado el 19 de septiembre de 2026.** Los pendientes que dejaron abiertos los
hitos 29 a 31. El usuario tomó las cuatro decisiones con la recomendación que se
le hizo, y mantuvo afuera las operaciones largas.

**No tiene stubs que contar.**

- [x] **El contador de la lupa es del registro.** Activarla sobre otro lo
      vuelve a cero, con la misma referencia débil que usa la ocupación; apagarla
      y prenderla lo conserva. «Poner en cero el contador de la lupa» está en
      «Herramientas», en el último bloque junto a «Restaurar la disposición»:
      las dos vuelven algo a su estado inicial, y ninguna es un modo del mouse.
- [x] **La altura de la banda y el radio y el aumento de la lupa se eligen en
      Configuración › Otras**, en un grupo «Herramientas» que se aplica
      enseguida. Por omisión siguen los de siempre, y la banda, la del pliego.
      La descripción de la banda dice ahora cuál es la de fábrica en vez de
      afirmar la vigente.
- [x] **Los paneles explican el canal plano.** La regla es
      `Recording.flat_channels()`: exactamente constante en el tramo, sin
      umbral, porque un umbral sería una decisión clínica. El espectro, la
      conectividad de la ventana y las dos medidas de la noche lo dicen en su
      descripción; los números no cambian. Recorrer la noche para contar las
      épocas planas suma 41 ms con un canal y 177 ms con siete, en el registro
      de `data/`.
- [x] **Importar un archivo de impedancias vacío avisa.** La biblioteca sigue
      devolviendo un diccionario vacío, que es lo que fija su test; el cartel
      es de la ventana.
- [x] **`HUECOS_ABIERTOS` queda vacía**: los cuatro métodos que encontró la red
      del hito 30 tienen camino desde la ventana.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con un registro que
    tiene un canal en cero.
  - Test: `tests/test_recording.py`, **53 tests en verde**, y
    `tests/test_contratos.py`, **1043 tests en verde**.
  - Test: `tests/test_magnifier.py`, **30 tests en verde**;
    `tests/test_preferences.py`, **68 tests en verde**;
    `tests/test_settings_dialog.py`, **48 tests en verde**.

### Lo que sigue abierto

- [x] **`Recording.get_segment()` no valida el tipo de sus extremos.** Lo
      encontró la red de contratos al probar `flat_channels()`: un `None` como
      `start_sample` sale como `TypeError` crudo. `flat_channels()` lo valida
      antes de llamarlo; `get_segment()` no tiene fila en `CONTRATOS` para ese
      argumento, y los que lo llaman hoy le pasan enteros.
      - **Lo arregló el [hito 50](#hito-50-los-pendientes-revisados).**
- [x] **El hipnograma y la Übersicht** siguen esperando la confirmación del
      usuario (ver el hito 31).
      - **Era el mismo pendiente dos veces**: se sigue sólo en el
        [hito 31](#hito-31-el-recorrido-manual). Revisado en el [hito 50](#hito-50-los-pendientes-revisados).

---

## Hito 33: La auditoría del 19 de septiembre

**Abierto el 19 de septiembre de 2026 y cerrado el 22**, con el
[hito 49](#hito-49-la-envolvente-se-calcula-una-vez). Una auditoría del backend y de cómo
llega a la ventana, pedida por el usuario: la suite entera, recorridos por la
ventana con eventos de Qt, archivos sintéticos con casos límite, memoria y
rendimiento. **No tiene archivo propio**, como la del 8 de septiembre: sus
hallazgos viven acá, en el orden en que conviene atacarlos.

**Lo que quedó probado que anda.** La suite pasa entera, sin salteados en una
máquina con `data/`. Doce escenarios de memoria —abrir registros, navegar,
reproducir, anotar, prender herramientas, abrir paneles, analizar y exportar,
cientos de veces— no crecen después del calentamiento, y ningún registro ni
ninguna ventana sobrevive a su reemplazo. Los cuatro formatos de scoring
vuelven idénticos, y un archivo roto no toca la sesión abierta.

**Una regresión de rendimiento que no era.** El banco dio el doble de tiempo
por cuadro que en el hito 27; corriendo los dos árboles intercalados, midieron
lo mismo. La máquina llegó a enlentecerse dos veces y media **dentro de una
misma corrida**, así que un número del banco sólo vale contra otro intercalado
con él, que es lo que el [hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar)
ya advertía.

**No tiene stubs que contar.**

- [x] **Un EDF sintético para el CI.** `escribir_edf()`, en
      `tests/conftest.py`, es el gemelo de `escribir_brainvision()`: cada canal
      en su propia unidad y a su propia frecuencia. Hasta acá el lector de EDF
      sólo corría contra `data/`, que el CI no tiene, así que la conversión a µV
      no se ejercitaba en ninguna de las seis combinaciones. Es lo que deja
      testear los tres ítems que siguen: el escritor ya reproduce los dos
      primeros.
  - Test: `tests/test_readers.py`, **88 tests en verde**. Este ítem sumó
    once que no dependen de `data/`, y el arreglo de la escala, dieciocho más.
- [x] **La escala dependía de cómo se escribiera la unidad.** `is_electrical()`
      no distingue mayúsculas y MNE sí: sólo convierte `uV`, `µV` y `mV`
      escritos así. Un canal que declaraba `uv` llegaba 10⁶ veces más grande,
      uno en `mv`, 10³, y un canal de BrainVision en `nV` quedaba en volts con
      la etiqueta `nV`. Pasaba en los dos lectores.
      - **El factor sale ahora de lo que hizo MNE con cada canal**: si lo llevó
        a volts, de volt a microvolt; si lo dejó como venía y la unidad es
        eléctrica, desde su unidad; si no, queda nativo. La regla de MNE está
        copiada en `_UNIDADES_QUE_MNE_PASA_A_VOLTS` de cada lector, carácter por
        carácter, y los tests escriben cada grafía: si una versión de MNE la
        cambia, fallan.
      - `utils/units.py` reconoce los nanovoltios, y una unidad eléctrica
        ambigua —«MV»— deja el canal como vino, con su unidad, en vez de
        inventarle un factor o impedir abrir el registro entero.
      - **Encontrado en el camino**: un `.vhdr` sin `Codepage` escrito en UTF-8
        dejaba **todos** los canales en volts, con la unidad «ÂµV» y fuera del
        EEG. MNE lo decodifica en UTF-8 y el lector en latin-1. El lector
        decodifica y parsea ahora como MNE: UTF-8 por omisión, sólo
        `[Channel Infos]`, y la unidad sin recortar.
      - Queda preguntarle al laboratorio cómo escriben la unidad sus equipos:
        dice si algún registro ya scoreado se vio con otra escala.
  - Test: `tests/test_units.py`, **47 tests en verde**, con los nanovoltios.
- [x] **Dos canales de un EDF con la misma etiqueta quedaban en volts.** MNE
      los renombra (`EEG-0`, `EEG-1`), `_leer_cabecera()` los buscaba por
      nombre, no los encontraba, y el lector los dejaba sin unidad, sin
      convertir y como `OTHER`. La cabecera se empareja ahora **por posición**,
      sacando los canales de anotaciones como los saca MNE; y si no se puede
      emparejar, el registro no se abre, porque sin la unidad no hay escala
      que no sea adivinada. El BrainVision también empareja por posición.
  - Con los lectores anteriores fallan diecisiete de los tests nuevos.
- [x] **Un EDF truncado se abría sin avisar.** Con la mitad del archivo salía
      la mitad de la noche: `verbose="ERROR"` calla el aviso de MNE. **Se abre
      igual y avisa**, que era la recomendación: lo que llegó puede ser todo lo
      que el investigador tiene. Si el laboratorio prefiere rechazarlo, es
      elevar en vez de avisar en el mismo lugar.
      - El lector compara los registros de datos que declara la cabecera con
        los que entran en el tamaño del archivo. Una cabecera que declara -1,
        que es lo que escribe un equipo mientras graba, no avisa: el formato
        dice que se deducen del tamaño.
      - El aviso viaja en `metadata[IMPORT_WARNINGS_KEY]`, una clave de
        `readers/base.py` que puede usar cualquier lector, y la ventana lo
        muestra después de abrir con su propio cartel, que no es el de error:
        «trae 4 h 10 min de los 8 h 00 min que declara su cabecera».
  - Test: `tests/test_readers.py`, **88 tests en verde**, con el truncado, el
    entero y el de -1 registros.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, abriéndolos por la
    ventana.
- [x] **Una fila de bandas mal formada en las preferencias impedía arrancar.**
      `_leer_bandas()` elevaba `IndexError`, que no estaba entre lo que
      `_con_campos_nuevos()` atrapa, y `create_application()` sólo atrapa
      `PsgLabError`. Alcanzaba con `{"psd_bands": [["Delta", 0.5]]}`, y el
      módulo supone que el archivo se edita a mano.
      - `_leer_bandas()` comprueba la forma de cada fila, y cada campo atrapa
        todo lo que un valor de JSON puede provocar: un campo roto vuelve al de
        fábrica, como ya prometía el docstring.
      - **Un archivo dañado ahora se avisa al arrancar.** `load()` armaba el
        mensaje para el investigador y nadie lo mostraba; lo muestra
        `apply_saved_preferences()` con la ventana ya a la vista.
  - Test: `tests/test_preferences.py`, **68 tests en verde**, con un barrido
    que le pone a cada campo guardado todos los tipos de JSON y exige que
    `load()` no eleve nada que no sea `PsgLabError`. Con el módulo anterior
    falla sólo `psd_bands`, con cuatro de esos valores.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el arranque
    y el cartel. El del cartel encontró que el `except ... as error` borra la
    variable antes de que el temporizador la use.
- [x] **Abrir otro registro o cerrar la ventana descartaba el scoring sin
      preguntar.** No había `closeEvent` ni ninguna marca de cambios sin
      exportar. El usuario eligió **un cartel con Exportar…, Descartar y
      Cancelar, sin autoguardado**: guardar a escondidas obliga a elegir por él
      dónde y en qué formato.
      - La regla es de `core/`: `Session.has_unexported_scoring()` compara el
        scoring contra cómo estaba la última vez que quedó en un archivo —al
        abrir, al importar, al exportar—, así que deshacer un cambio no cuenta
        y un scoring vacío no tiene nada que perder. `export()` llama a
        `mark_scoring_exported()` sólo si escribir anduvo.
      - «Exportar…» abre el mismo diálogo que Ctrl+S y sigue sólo si el
        scoring quedó escrito: cancelar el diálogo o que falle escribir deja
        todo como estaba. Exportar es el botón por omisión y Escape cancela.
      - Al abrir otro registro se pregunta **después de leerlo**: si el archivo
        nuevo está roto, la sesión anterior sigue y no hay nada que preguntar.
  - Test: `tests/test_session.py`, **156 tests en verde**, con nueve sobre qué
    cuenta como trabajo sin exportar.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con doce por la
    ventana: cerrar y abrir otro registro con cada una de las tres
    respuestas, un guardado cancelado o fallido, y el cartel de verdad con sus
    tres botones. Con la ventana anterior fallan once; el que pasa igual es el
    que afirma que sin nada scoreado no se pregunta.
- [x] **Importar un scoring encima de uno sin exportar lo reemplazaba sin
      preguntar.** La misma pérdida que arriba por el tercer camino, que quedó
      fuera del pedido del hito —nombraba cerrar y abrir otro registro—.
      `open_scoring()` pregunta con el mismo cartel.
      - **Después de leer el archivo**, por el mismo motivo que al abrir un
        registro: uno que no se puede importar no pisa nada, así que no hay
        nada que preguntar. Acá se puede porque `read_scoring()` ya rechaza el
        scoring que no es de este registro, así que lo que se leyó bien se
        importa seguro.
      - El cartel dice «se pierden al importar «Scoring.txt»», con el nombre
        del archivo que se está por traer.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con los tres
    botones, con que lo ya exportado no pregunte y con que un archivo ilegible
    tampoco. Seis fallan sin la corrección, cuatro de ellos el viaje de ida y
    vuelta de cada formato, que importa justamente sobre trabajo sin exportar.
- [x] **La conectividad dejaba escapar un `ValueError` de MNE** cuando la
      banda no tenía ninguna frecuencia que medir: una banda del usuario de 55
      a 90 Hz sobre un registro de 100 Hz. No salía ningún cartel y la traza iba
      a la consola.
      - `_exigir_frecuencias_en_la_banda()` arma la misma grilla que
        mne-connectivity —la de una época, con los dos extremos incluidos— y
        rechaza antes con `InvalidBandError`, diciendo por qué: la banda está
        por encima de Nyquist, o es más angosta que la resolución de 0,2 Hz.
      - Es `InvalidBandError` y no `InvalidRecordingError` a propósito:
        `connectivity_by_window()` traga el segundo como "ventana corta", y la
        noche habría salido entera en NaN. La noche además comprueba la banda
        antes de recorrer, para que un registro más corto que una época no la
        esconda.
      - Queda anotado lo vecino: una banda que **cruza** Nyquist se mide en la
        parte que entra, sin decirlo, y la potencia de una banda que el
        espectro no alcanza sale en cero (ver la lista de abajo).
  - Test: `tests/test_connectivity.py`, **40 tests en verde**, con los dos
    mensajes, la banda de un solo punto que sí se mide y la noche corta.
  - Test: `tests/test_contratos.py`, **1043 tests en verde**, con tres
    rechazos obligatorios nuevos.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el cartel desde
    los dos menús de conectividad. Con el módulo anterior fallan los seis que
    rechazan.
- [x] **La primera apertura de cada sesión del programa congelaba unos 9 s**, y
      la segunda tardaba 0,6. Eran las importaciones perezosas de MNE:
      `mne.io` carga el módulo de cada formato recién al usarlo, y
      `mne.io.brainvision` arrastra `mne.viz` y `matplotlib`. Medido con
      cProfile: 8,65 de los 9,2 s.
      - **Lo paga ahora el hilo que ya existía**, que pasó a llamarse
        `warm_up_in_background()` porque dejó de ser sólo de análisis. Los
        lectores van primero: abrir un registro es lo primero que hace el
        usuario, y `antropy` no lo tiene esperando a él. Si llega antes que el
        hilo, el lock de importación de Python lo hace esperar lo que falte.
      - **Qué adelantar lo sabe cada formato**, no la ventana: `Reader.warm_up()`
        no hace nada por defecto, como los métodos de evento de `Tool`, y los
        dos lectores importan ahí su módulo de MNE. `warm_up_readers()` los
        recorre.
      - Medido en esta máquina, con procesos limpios: la primera apertura pasó
        de **5058 ms a 256 ms**, y la segunda queda en 53. El hilo tarda 21,6 s
        en total —3,3 los lectores y 14,4 `antropy`—, en segundo plano.
  - Test: `tests/test_readers.py`, **88 tests en verde**, con lo que queda
    importado, el lector que no adelanta nada y que precalentar no lea ningún
    archivo.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el orden de los
    dos precalentamientos y con que la suite no precaliente.
- [x] **Lo que se leía sin avisar o se mostraba sin explicar.** Siete cosas
      chicas, cada una con su test:
  - Un `Scoring.txt` **con BOM** no se importaba: `_leer_lineas()` decodificaba
    con `utf-8` y no con `utf-8-sig`. Lo escribe el Bloc de notas de Windows, y
    con él la cabecera `# AASM` no se reconocía.
  - `Session.center_offsets()` guardaba un desplazamiento NaN si la ventana
    tenía uno, salteando la guarda de `set_offset_uv()`: el canal se dejaba de
    dibujar sin ningún cartel. Ahora se saltean los valores que no son números,
    y un canal que no tiene ninguno se queda donde está. `fit_to_pane()` hacía
    lo contrario —con un solo NaN no ajustaba nada— y sigue la misma regla.
  - El lector de `Scoring.txt` tomaba **cualquier arousal** distinto de cero
    como marcado, y con tres campos una **ventana repetida** pisaba a la
    anterior: el scoring dependía del orden del archivo. Los dos se rechazan.
  - Una banda por encima de lo que el registro alcanza da potencia 0, y un cero
    no se distingue de uno real: **el espectro lo dice** en su descripción, con
    la misma regla semiabierta que usa `band_power()`. El número no cambia.
  - `Informacion.txt` promedia los episodios en ventanas completas y suma las
    fases en duración real: con la última ventana incompleta, un único episodio
    de N2 promedia más que el total de N2. Los dos números son correctos, así
    que **lo que se corrigió es el rótulo**, que ahora dice sobre qué cuenta.
  - Un archivo **que no está** se informaba como dañado, que manda a buscar el
    problema al lugar equivocado.
  - La barra de estado se quedaba en «Calculando…» con el resultado ya en
    pantalla. `_trabajando()` lo borra al salir, y sólo si sigue siendo el suyo.
  - `_export_dialog()` agregaba la extensión **después** de que el diálogo
    confirmó la sobrescritura, así que el archivo que se pisaba no era el que el
    usuario vio: escribía «noche» y se sobrescribía «noche.txt» sin preguntar.
    Ahora se pregunta de nuevo.
  - Test: `tests/test_scoring_reader.py`, **38 tests en verde**;
    `tests/test_session.py`, **156 tests en verde**;
    `tests/test_readers.py`, **88 tests en verde**;
    `tests/test_entrega.py`, **316 tests en verde**. Doce fallan sin la
    corrección.
- [x] **Lo que dicen los documentos y el código no.** Se corrigieron en el
      documento cuando el documento estaba viejo, y en el código cuando el
      equivocado era el código por no hacer lo que el documento prometía:
  - **El documento estaba viejo.** `tools/base.py` y `tools/README.md` decían
    en un lugar que la `x` de `ViewerTool` son segundos de la ventana; son del
    registro desde el [hito 22](#hito-22-refactor-de-la-interfaz), y una
    herramienta escrita con la regla vieja produce tramos corridos sin que nada
    falle. `core/README.md` contaba seis módulos y listaba ocho, y su párrafo
    de unidades no nombraba la página ni los segundos del registro.
    `tests/README.md` y `ui/README.md` decían que `ui/` casi no tiene tests
    —hoy veinte de sus veintidós módulos tienen el suyo—, y `ci.yml`, que la
    suite tarda segundos. `analysis/README.md` daba a
    `band_powers_by_window()` por una de las que alimentan los gráficos de la
    noche: no tiene camino desde la ventana, y le faltaba su fila en la tabla
    de lo que la interfaz no ofrece a propósito. `CLAUDE.md` decía que ningún
    test lee los registros de `data/`; trece los leen, todos detrás de un
    `skipif`.
  - **El equivocado era el código.** `SOLO_BIBLIOTECA` eximía a
    `unidad_de_salida()` diciendo que la consultan los análisis, y no la
    llamaba nadie: ahora la aplica `from_raw()` al reconstruir cada canal, así
    que la regla de la unidad se escribe una sola vez. Y la ventana no llamaba
    nunca a `Session.set_active_tool()`, con lo que `active_tool` era `None`
    pasara lo que pasara; la llama al prender y apagar una herramienta
    exclusiva, y un panel no la desplaza.
  - Una exención que dice que algo se usa y no se usa **es peor que el hueco**:
    lo vuelve invisible y encima parece revisado. Es lo que dice
    «Lo que se verifica solo» de `CLAUDE.md`, y acá pasó.
  - Test: `tests/test_mne_bridge.py`, **15 tests en verde**, con la grafía de
    la unidad que vuelve normalizada; `tests/test_entrega.py`, **240 tests en
    verde**, con la sesión siguiendo a la herramienta del menú. Tres fallan sin
    la corrección.
- [x] **El cartel del scoring no cubría las anotaciones.** Miraba sólo el
      scoring, que es lo único que el menú exporta, así que una noche de
      eventos anotados y ninguna fase puesta se cerraba sin preguntar nada.
      **El usuario decidió que las cuente**, que era lo que este ítem tenía
      pendiente.
      - La regla es de `core/`, como la otra mitad:
        `Session.has_unexported_annotations()`, con la misma comparación
        contra cómo estaban al abrir o al exportarlas. Anotar y borrar no
        cuenta, y sin ninguna anotación no hay nada que perder. **Las clases y
        sus colores quedan afuera**: los exportadores escriben anotaciones y no
        clases, y el color vive en las preferencias, que se guardan solas.
      - El cartel pasó a ser del **trabajo** y no del scoring —de ahí los
        nombres `_puede_descartarse_el_trabajo()` y
        `_preguntar_por_el_trabajo()`—, y **su texto nombra lo que está en
        juego**: decir "el scoring" sobre una sesión que sólo tiene
        anotaciones manda a buscar al lugar equivocado lo que se va a perder.
      - **«Exportar…» abre un diálogo por cada cosa en juego**, el scoring
        primero. Es la parte que no era obvia: `Anotaciones.txt` salió del menú
        en el [hito 23](#hito-23-ajustes-de-la-barra-de-menú) y sin esto el
        cartel sería un callejón —avisar de una pérdida sin ofrecer cómo
        evitarla es peor que no avisar—. Le da a ese archivo su **única** vía
        desde la ventana, y no toca el menú: la decisión del hito 23 sigue en
        pie y sigue sin confirmarse con el cliente.
  - Test: `tests/test_session.py`, **156 tests en verde**, con las seis reglas
    de qué cuenta como anotación sin exportar.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el cartel por la
    ventana: sólo anotaciones, las dos cosas juntas con sus dos diálogos, un
    guardado cancelado a mitad de camino y los tres textos. Diez fallan sin la
    corrección.
- [x] **Un NaN en la señal se aceptaba sin aviso y los filtros lo
      esparcían**: diez muestras terminan en unas treinta mil, la referencia
      promedio lo pasa a todos los canales y la PSD de esa época sale entera en
      NaN. En la pantalla no se ve: la curva se corta y no se distingue de una
      pausa.
      - **Se midió primero**, que es lo que este ítem tenía pendiente. Sobre el
        registro de prueba de 22 h y 445 MB, revisarlo entero cuesta **80 ms
        contra los 2,4 s que tarda abrirlo**: 3 %. Recorrerlo canal por canal
        es más barato que `axis=1` —80 ms contra 175— y deja el temporal de
        booleanos en un canal, 8 MB en vez de 55. Con eso medido, se hace.
      - La regla es de `core/`: `Recording.non_finite_channels()` cuenta las
        muestras sin valor de cada canal, como `flat_channels()` cuenta las
        planas. `isfinite` y no `isnan`, porque un infinito rompe lo mismo.
      - **El aviso lo arma `read_recording()`**, no cada lector: el EDF guarda
        enteros y no puede traer un NaN, pero un BrainVision en
        `IEEE_FLOAT_32` sí, y el formato que se agregue mañana no tiene por qué
        acordarse de mirarlo. Se suma a los que el lector ya haya dejado, así
        que un archivo incompleto **y** con NaN dice las dos cosas.
      - El cartel nombra hasta cinco canales con sus cuentas y resume el resto,
        y dice qué implica: que filtrar las esparce, que la referencia promedio
        las pasa a todos los canales y que la PSD de esa época sale sin valor.
  - Test: `tests/test_recording.py`, **53 tests en verde**, con el NaN, el
    infinito y el orden de los canales.
  - Test: `tests/test_readers.py`, **88 tests en verde**. `escribir_brainvision()`
    aprendió a escribir muestras sin valor, y para eso el archivo en
    `IEEE_FLOAT_32`: es el único de los dos formatos que puede traerlas.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el cartel por la
    ventana. Seis fallan sin la corrección.
- [x] **Un esquema propio inválido descartaba todas las preferencias.** La
      pregunta se cerró sola en el [hito 35](#hito-35-dos-esquemas-y-ninguna-perilla):
      **ya no hay esquemas propios**. Un archivo viejo que traiga uno se lee
      igual —el nombre cae en el de fábrica y `custom_scheme` se ignora— en vez
      de impedir arrancar, que era exactamente lo que el ítem quería evitar.

### Lo que sigue abierto

- [x] **Los registros densos siguen sin entrar en el cuadro**: con 32 canales a
      1000 Hz y página de 5 min, unos 100 ms contra los 40 del reloj. Es el
      pendiente del [hito 27](#hito-27-la-navegación-desde-el-medio), medido de
      nuevo.
      - **Lo resolvió el [hito 49](#hito-49-la-envolvente-se-calcula-una-vez)**: el cuadro era caro por recalcular la
        envolvente entera en cada paso, y ahora se calcula sólo lo que entra.
        Ahora cuesta del orden de las páginas cortas. Cuando pasa de 40 ms es
        pintar, les pasa igual a todas las páginas del registro denso y es el
        ítem abierto del
        [hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar).
- [x] **Lo largo sigue en el hilo de la interfaz**: la conectividad de la noche,
      entre 15 y 18 s sobre ocho horas; la ICA, 9 s; filtrar, 2,5 s. Es la
      decisión del hito 32, ahora con números.
      - **La primera salió en el [hito 42](#hito-42-lo-largo-deja-de-congelar-la-ventana)**,
        con el mecanismo que las otras dos necesitan.
      - ~~Quedan la ICA y el filtrado, que además **cambian la señal**: eso es
        lo que hace que no sean el mismo trabajo que la conectividad.~~
        **Esto último era falso**, y lo mostró medirlo en el
        [hito 47](#hito-47-lo-caro-era-ajustar-y-no-cambia-la-señal): «la ICA»
        son dos operaciones y la cara —ajustar— **no** cambia la señal. Las dos
        que sí la cambian cuestan décimas de segundo.

---

## Hito 34: El rediseño de la pantalla principal

**Cerrado el 20 de septiembre de 2026.** Sale de un canvas de cinco artboards
que el usuario aprobó —la ventana en dos esquemas, el estado trabajando con
análisis, los controles y el sistema visual— y de lo que ese diseño encontró
mirando el programa:

- El esquema de arranque era **blanco puro con tinta negra**, que sobre ocho
  horas de señal es el máximo de deslumbramiento posible.
- **El programa no tenía colores de fase.** El hipnograma se dibujaba en una
  sola tinta, así que reconocer una fase obligaba a leer el eje, y los cinco
  botones de scoring eran grises indistinguibles entre sí.
- La franja de posición decía dónde estoy y no cuánto llevo scoreado, que es
  la otra mitad de la pregunta.

**Las cuatro decisiones del usuario**, tomadas antes de empezar: el alcance es
completo —repinte y las piezas nuevas—, Sereno pasa a ser el esquema de
arranque, la interfaz arranca en IBM Plex Sans, y los botones de fase ganan
tecla.

**No tiene stubs que contar.**

- [x] **El sistema visual**, en `psglab/ui/theme.py`.
      - **`SERENO` y `NOCTURNO`**, dos `ColorScheme` más. Los seis anteriores
        no se tocan y «Claro» sigue devolviendo el aspecto nativo de Qt, que es
        la salida para quien no quiera nada de esto.
      - **`stage_colors`**, el campo que no existía: qué color tiene cada fase.
        La profundidad es la luminosidad —S1/N1 a S4/N3 recorren un mismo azul
        de claro a oscuro— y las dos nomenclaturas comparten la escala, así que
        cambiar de nomenclatura no cambia de colores. Vacío significa «una sola
        tinta», que es como se dibujaba hasta ahora: por eso los seis esquemas
        anteriores siguen viéndose igual.
      - **Los tokens de forma** —radio, altura de control, anillo de foco— van
        en el mismo módulo y no en uno nuevo: su único consumidor es
        `stylesheet()`, y un módulo propio costaría cinco filas de tablas de
        documentación para mover seis números.
      - La hoja de estilo pinta ahora el **título de los paneles**, las
        **solapas** de la pila de análisis, el **foco del teclado** —que era un
        gris que casi no cambiaba— y una regla por fase. La tinta que va encima
        de la fase marcada **se elige midiendo el contraste**, no por esquema:
        el blanco que se lee sobre el azul profundo desaparece sobre el ámbar
        del esquema oscuro.
  - Test: `tests/test_theme.py`, **78 tests en verde**, con la escala de
    fases, las reglas por fase y el contraste de los dos esquemas nuevos, que
    el control de accesibilidad recorre solo porque mira `theme.SCHEMES`.
  - Test: `tests/test_preferences.py`, **68 tests en verde**, y
    `tests/test_settings_dialog.py`, **48 tests en verde**: los dos afirmaban
    «Claro» donde querían decir «el esquema de fábrica».

### Lo que entró después del sistema visual

- [x] **La tipografía por omisión.** `Preferences.font_family` arranca en la
      familia que el programa ya empaqueta, en vez de en la del sistema.
      - `fonts.UI_FONT_FAMILY` la nombra una sola vez, al lado de la lista de
        archivos: si alguna vez se cambian, el nombre se corrige donde está la
        lista y no en tres módulos.
      - **`fonts.available_family()` pregunta antes de pedirla.** Con la
        tipografía del programa como valor de fábrica, en una instalación sin
        los archivos `setFamily()` sustituiría en silencio por lo que Qt
        eligiera, que suele ser peor que la del sistema. Es el mismo criterio
        con que `register_bundled_fonts()` saltea un archivo ilegible.
      - **A quien ya tiene preferencias guardadas no le cambia nada**: el
        archivo siempre escribe `font_family`, y `_con_campos_nuevos()` sólo
        saltea lo que no está. El diseño nuevo lo ve quien instala de cero o
        quien lo elige en Configuración → Tipografía.
  - Test: `tests/test_fonts.py`, **19 tests en verde**, con la familia
    disponible y con una que no existe.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con la tipografía
    aplicada y con la que no está. Los cuatro fallan sin la corrección.
- [x] **Los botones de fase**: 46 px de alto, dos renglones y el color de su
      fase. Es el control que más se aprieta en toda la noche —uno por época—
      y el único al que se le da un alto propio por eso.
      - **La tecla ya existía y no se veía en ningún lado.** `shortcuts.py` la
        deriva del código de la fase desde el principio, así que quien no leía
        la ayuda scoreaba la noche entera a golpe de mouse. El botón la muestra
        ahora, leyéndola de ese módulo con `key_for_stage()`, que pasó a ser
        pública por eso.
      - El color no se escribe en el panel: el botón declara su fase con una
        propiedad dinámica y la hoja de estilo arma la regla. Un esquema sin
        escala deja los botones como estaban.
      - **El mínimo del panel no cambió**: el botón creció de alto y no de
        ancho, así que el reparto con el hipnograma es el mismo. Medido con
        `tests/medir_reparto.py`: el scoring pide 312 px con R&K y 224 con
        AASM, como antes.
  - Test: `tests/test_scoring_panel.py`, **27 tests en verde**, con la tecla,
    la propiedad de la fase y que cambiar de nomenclatura no deje botones
    viejos, que ahora se pintarían con el color de una fase que ya no existe.
- [x] **El hipnograma a color**, con la misma escala.
      - `HistogramTool.runs()` agrupa `bars()` en tramos seguidos de la misma
        fase: sobre ocho horas son unos cientos contra 960 ventanas, y el panel
        se redibuja en cada cambio de época. **Lo no scoreado no es un tramo**:
        es la ausencia de fase, que queda en blanco (V1_P).
      - La ventana los pinta en **un solo ítem de escena**, que es la cuenta
        del hito 25 aplicada a este panel, y **sobre la curva y no en vez de
        ella**: la curva es la que resuelve lo no scoreado con `NaN`.
      - **Medido con la noche entera scoreada**, que es donde cuesta: 2650
        épocas en 123 tramos. Redibujar el hipnograma pasa de 1,8 ms a 3,1,
        con 40 de presupuesto por cuadro. Con la noche sin scorear no hay nada
        que pintar y la diferencia no existe, así que medirlo ahí no habría
        medido nada: es el error que estuvo a punto de quedar escrito acá.
  - Test: `tests/test_histogram.py`, **33 tests en verde**, con los tramos, el
    hueco que los parte y que agrupar no pierda ni agregue ventanas.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el color por la
    ventana y con que un esquema sin escala no pinte nada.
- [x] **La franja de posición con el scoring pintado.** Decía dónde estoy y no
      cuánto llevo hecho, que es la otra mitad de la pregunta que un scorer se
      hace cada vez que vuelve a un registro.
      - Los colores salen de `bars()`, la misma fuente que el hipnograma: una
        fase se ve igual en los dos lugares.
      - **El fondo se cachea en un `QPixmap`** y se rehace sólo cuando cambia
        el scoring, la cantidad de épocas o el ancho. La franja se repinta en
        cada época, o sea veinticinco veces por segundo reproduciendo: pintar
        2650 rectángulos en cada cuadro es lo que el hito 25 sacó de la grilla.
        `set_scoring()` no hace nada si le llega lo mismo, que es lo que
        mantiene vivo el cache en el camino caliente.
      - La franja pasó de 14 a 22 px: con tramos de color, 14 parecía una regla.
  - Test: `tests/test_navigation.py`, **42 tests en verde**, con el cache que
    se reusa, el que se rehace y el que no.
- [x] **La pestaña de la época** sobre la señal, con su número y su fase. La
      banda decía dónde se scorea y no **qué** se scorea: con una página larga
      hay que mirar la barra de abajo para saber en qué época cayó el
      resaltado, y la fase sólo se ve en el panel de scoring, que puede estar
      cerrado. Se crea una vez y después sólo se mueve, como la banda y el
      cursor, y el texto se rearma sólo cuando cambió.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con la franja por la
    ventana.
- [x] **Los atajos de fase ya existían.** `shortcuts.py` los deriva del código
      de la fase desde el principio —W, R, 1 a 4 y M— y se reinstalan al
      cambiar de nomenclatura. Lo que faltaba no era la tecla sino **verla**, y
      eso entró con el botón. El ítem queda como está: no hay nada que agregar.

### Lo que no va a quedar igual al diseño, y se sabe de antemano

- **La columna de etiquetas de canal.** El artboard las pone en un margen
  izquierdo, fuera del área de trazo; hoy son `TextItem` dentro del gráfico.
  Un margen de verdad pide un `AxisItem` propio, que es un hito aparte.
- **Las versalitas del rótulo de panel.** Qt no soporta `letter-spacing` ni
  `text-transform` en su hoja de estilo, y escribir los títulos en mayúscula
  cambiaría `windowTitle()`, que es lo que ocho tests de entrega afirman.
- **El marco de la ventana, los menús desplegados y los diálogos de archivo**
  los dibuja el sistema operativo.

---

## Hito 35: Dos esquemas y ninguna perilla

**Cerrado el 20 de septiembre de 2026.** Sale de probar el hito 34 con un
registro de verdad: el usuario abrió el programa, **no vio ningún cambio** y
avisó. Su archivo de preferencias tenía `"scheme_name": "Claro"` guardado, y
«Claro» era justamente el esquema que no ponía hoja de estilo y dejaba el
aspecto nativo de Qt. El rediseño estaba, y su propia configuración lo tapaba
entero.

Eligió Sereno y Nocturno desde la configuración, le gustaron, y **pidió que
fueran los únicos**: reducir la personalización de colores al mínimo, de manera
que sólo se pueda cambiar entre esos dos.

**El problema de fondo que eso resuelve** es el que el aviso dejó a la vista:
con ocho esquemas y cada color editable, el programa tenía infinitos aspectos
posibles y **ninguno garantizado**. El control de contraste sólo alcanzaba a
los de fábrica, y el que se armaba a mano podía dejar la señal casi invisible
con un cartel al costado. Dos esquemas verificados y ninguna perilla es menos
programa y más garantía: lo que se ve en una máquina del laboratorio es lo que
se ve en todas.

**No tiene stubs que contar.**

- [x] **Quedan dos esquemas.** Se fueron Claro, Oscuro, NK, Azul sobre gris,
      ECG y Papel, y con ellos la paleta que sólo usaba «Azul sobre gris».
      - **La hoja de estilo dejó de tener un caso especial**: «Claro» devolvía
        la cadena vacía para quedar nativo, y los iconos tenían que sacar su
        tinta de la paleta de Qt por eso mismo. Sin ese esquema, las dos
        funciones son lo que dicen ser.
- [x] **Los esquemas no se editan.** Se fue la solapa Colores entera: los doce
      botones de color, la paleta de canales, la línea de base, «un color
      distinto por canal», el aviso de contraste y Guardar…/Cargar….
      - Con ella se fueron `scheme_to_dict()`, `scheme_from_dict()`,
        `save_scheme()`, `load_scheme()` y el campo `custom_scheme`: sin
        esquemas propios no hay nada que serializar, y el archivo de
        preferencias guarda el **nombre**.
      - **Un archivo viejo sigue cargando.** El nombre que ya no existe cae en
        el de fábrica y `custom_scheme` se ignora, como ya se ignoraba
        `window_state` desde el hito 24. Eso cierra además el ítem del hito 33
        sobre el esquema propio ilegible: la pregunta ya no se puede hacer.
      - Lo que queda configurable de color es **el de cada clase de evento**,
        que es otra cosa: no es el aspecto del programa sino el dato de una
        anotación.
- [x] **Elegir esquema pasó al menú «Ver».** Dos entradas excluyentes, al lado
      de los tres fondos de grilla, que es lo otro que cambia cómo se ve la
      señal. La ventana de configuración bajó a cuatro solapas.
      - La tilde se pone también cuando el esquema **no** vino del menú —al
        aplicar el archivo de preferencias al arrancar—, que es el único otro
        camino que queda.
- [x] **Se fue la grilla cuadriculada del esquema ECG.** Era lo único que usaba
      `ecg_grid`, y el pliego no la pide: sus tres fondos —blanco, sólo las
      líneas de 3 s, las dos densidades— son verticales y siguen donde estaban.
  - Test: `tests/test_theme.py`, **78 tests en verde**; `tests/test_grid.py`,
    **19 tests en verde**; `tests/test_settings_dialog.py`, **48 tests en
    verde**; `tests/test_preferences.py`, **68 tests en verde**;
    `tests/test_menus.py`, **44 tests en verde**, con las dos entradas nuevas y
    su exclusividad. Entre los cinco se borraron treinta y seis tests de lo que
    dejó de existir.

### Lo que este hito deja anotado

- **Un esquema nuevo es sumarlo a `SCHEMES`**, y el control de contraste lo
  enrola solo porque recorre ese diccionario. Una perilla de color, en cambio,
  es volver atrás una decisión tomada.
- **El archivo de preferencias no migra.** Quien ya tenía el programa conserva
  lo que había elegido, salvo que ese esquema ya no exista, en cuyo caso ve el
  de fábrica. El usuario dijo explícitamente que las instalaciones viejas no le
  importan.

---

## Hito 36: Las dos barras

**Cerrado el 20 de septiembre de 2026.** El usuario abrió el programa con el
hito 35 ya puesto y avisó: **«las barras inferiores y superiores no se ven para
nada parecidas a las del prototipo»**. Tenía razón, y el motivo es una
distinción que el hito 34 no marcó: una hoja de estilo **repinta** un control,
no lo **reemplaza**. Con QSS se puede cambiar el color y el radio de un botón;
no se le puede poner una etiqueta al lado, ni agregar el identificador del
registro, ni cambiar qué controles hay ni dónde están. Las seis fases del 34
pintaron lo que había, y lo que había en las dos barras no era lo del diseño.

**No tiene stubs que contar.**

- [x] **La barra de menú.**
      - El botón de abrir lleva la palabra «Abrir» al lado del icono. Con la
        carpeta sola, lo único que decía qué hacía era el tooltip, y en la
        esquina de una barra de menú un icono suelto se lee como decoración.
      - **Dejó de ser `autoRaise`**, que es lo que lo tenía sin marco: un botón
        plano no dibuja caja, así que la hoja de estilo no podía darle ni borde
        ni radio por más reglas que tuviera.
      - **Qué registro está abierto, en la otra esquina**: nombre, frecuencia,
        canales y de qué hora a qué hora. No estaba en ningún lado, y con dos
        registros parecidos —la misma noche filtrada y sin filtrar— no había
        forma de saber cuál se miraba.
  - Test: `tests/test_menus.py`, **44 tests en verde**.
- [x] **La barra de navegación.**
      - Los botones pasaron de 26 a 34 px y dejaron de ser planos: con 26 el
        icono quedaba en 14 y la fila entera se leía como una regleta de
        controles diminutos.
      - **Reproducir es la acción primaria** y va relleno con el acento: es la
        única que hace algo por sí sola y no un paso más de lo mismo. La tinta
        de su icono la elige `theme.ink_over()`, midiendo, que es la misma
        función que decide la de una fase marcada.
      - **La franja y lo que dice de ella, en una columna.** Las dos lecturas
        estaban sueltas al final de la fila, así que la proporción que dibuja
        la franja no tenía contra qué leerse. Ahora las horas de los extremos
        van a sus costados y la época, debajo del medio, con su hora: son la
        misma pregunta —dónde estoy— en dos unidades.
      - **La amplitud se ve**, entre los dos botones que la cambian. Hasta acá
        sólo estaba en el eje de cada canal. Con ganancias distintas por canal
        (V5_F) dice «varias» en vez de inventar un número: decir la del primero
        sería que el investigador lea 100 µV mirando un canal a 250.
      - «Velocidad» y «Amplitud» quedaron rotuladas: eran un combo y dos
        flechas sin nada que dijera de qué.
  - Test: `tests/test_navigation.py`, **42 tests en verde**.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con las dos barras
    por la ventana.

- [x] **Una herramienta para mirar**, `tests/capturar_pantalla.py`. Deja PNG de
      la ventana y de cada barra con los dos esquemas, a mano y sin recolectar,
      como los dos bancos de medición.
      - **No corre offscreen**, por el mismo motivo que el banco de reparto: ese
        plugin no trae tipografías ni estilo nativo, y una captura hecha así
        muestra cuadraditos donde van las letras. La primera que se sacó en este
        hito fue exactamente eso, y no servía para nada.
      - **Y no abre ninguna ventana en la pantalla de quien la corre**:
        `WA_DontShowOnScreen` le pide a Qt que maquete el widget completo sin
        mapearlo. Hace falta porque un widget que nunca se mostró no tiene
        layout, y capturarlo da una barra colapsada.

### Los dos errores que encontró la captura

Ninguno lo veía un test, y los dos estaban en lo que este mismo hito acababa de
escribir. Es el argumento de la herramienta, medido:

- **El identificador del registro salía cortado a un tercio.** `QMenuBar` le da
  a su widget de esquina el ancho que pidió cuando se lo colgaron —el de «Sin
  registro»— y no se lo vuelve a preguntar. Ni `adjustSize()` ni
  `updateGeometry()` alcanzan: hay que volver a colgarlo. El mínimo se calcula
  además con las métricas de la fuente puesta y no con `sizeHint()`, que se
  resuelve antes de que la hoja de estilo le dé la tipografía numérica.
- **El icono de reproducir se dibujaba con la tinta de los demás** sobre el
  relleno de acento: **2,87 a 1**, contra los 5,95 de la que corresponde.
  `apply_scheme()` lo corregía, pero sólo corre al cambiar de esquema, así que
  el botón que ve quien abre el programa tenía el icono casi invisible. Ahora
  el botón se pinta al construirse, y hay un test que compara el mapa de bits.

### Lo que este hito deja anotado

- **Lo que la hoja de estilo no puede hacer** conviene tenerlo a mano: poner o
  sacar controles, moverlos, cambiarles el texto, y —en Qt— `letter-spacing` y
  `text-transform`. Todo eso es código, no estilo.
- **Lo que un test puede afirmar de la interfaz es la estructura**: qué
  controles hay, de qué tamaño, con qué texto y qué propiedades. Cómo se ve, no;
  para eso está la captura, y conviene sacarla antes de dar una barra por
  terminada.

---

## Hito 37: El canalón

**Cerrado el 20 de septiembre de 2026.** Lo encontró la herramienta que dejó el
hito 36, en la primera captura de la ventana entera: **la etiqueta de cada
canal se dibujaba encima de su propia señal** y no se leía. Estaba anotado
desde el hito 34 como «diferencia conocida con el artboard, aproximada y no
idéntica», y viéndola no era una diferencia de gusto sino un problema de
legibilidad. El usuario eligió la salida cara de las dos: el canalón de verdad
del diseño, y no correr el rótulo al hueco entre carriles.

**No tiene stubs que contar.**

- [x] **`psglab/ui/channel_axis.py`, el canalón.** El nombre arriba, la clase y
      la escala debajo, a la derecha de una columna propia fuera del gráfico.
      - **Es un `AxisItem` y no un ítem de la escena ni un widget al costado.**
        Mientras el rótulo sea un ítem vive en coordenadas del gráfico y la
        señal se dibuja encima: moverlo no alcanza. El eje es lo único a lo que
        pyqtgraph le descuenta ancho al `ViewBox`, y por eso es lo único que
        reserva píxeles que la señal no puede invadir. Un widget aparte también
        los reservaría, pero tendría que mantener su alineación vertical con
        los carriles a mano y se desalinearía con cada cambio de rango.
      - **No dibuja ninguna marca ni ningún número.** El eje vertical son
        carriles, no una escala: pyqtgraph pondría marcas en 0, −1 y −2, que no
        significan nada para quien mira.
      - **El nombre va en la tinta del texto y el color del canal en una
        muestra**, una barrita al borde. No es estética: la paleta de canales
        está verificada contra `MIN_GRAPHIC_CONTRAST` —3,0— porque son trazos, y
        el color 3 de Sereno da **3,89** sobre el fondo. Escrito con ese color,
        el nombre habría quedado por debajo de los 4,5 que WCAG 2.1 pide para
        texto, que es exactamente lo que hacía el rótulo viejo. La muestra sigue
        siendo un gráfico y conserva la identificación por color.
      - **El ancho es fijo y los nombres largos se recortan.** Un canal llamado
        «EEG Fpz-Cz-A2-referenciado» no puede decidir cuánta pantalla le queda a
        la señal. El nombre entero se sigue viendo en el selector de canales.
  - Test: `tests/test_channel_axis.py`, **12 tests en verde**.
- [x] **El visualizador dejó de dibujar rótulos.** `channel_label()` se fue con
      ellos —era el texto de una sola línea— y en su lugar está
      `channel_detail()`, que arma la segunda: «EEG · 100 µV».
      - **Se cayó un problema entero, no se arregló.** `show_window()`
        arrastraba cada rótulo hasta el borde izquierdo de la página en cada
        dibujo, porque con el eje en segundos absolutos el cero queda fuera de
        la pantalla desde la segunda época. Fuera del gráfico, la página ya no
        los puede dejar afuera.
      - **Y una medida nueva de contraste**: el canalón usa la tinta secundaria
        sobre el fondo de la señal, un par que hasta acá no se medía —
        `overview_text` sólo se miraba contra `overview_background`—. Sereno da
        6,04 y Nocturno 7,18. Como los demás, lo enrola solo cualquier esquema
        que se agregue.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.
  - Test: `tests/test_theme.py`, **78 tests en verde**.

### Medido, porque el canalón toca el camino caliente

El visualizador rearma los rótulos en cada dibujo, o sea veinticinco veces por
segundo mientras se reproduce. **`set_lanes()` no repinta si son los mismos**,
que es lo que evita que el canalón vuelva a costar por cuadro lo que el hito 25
le sacó a la grilla; y el ancho que reserva le saca columnas al área de trazo,
que son curvas más cortas que dibujar. Medido con el banco, intercalado con una
corrida del árbol en `4beafd8` para que las dos vean la misma máquina:

| Un paso de reproducción | Antes | Con el canalón |
|---|---|---|
| 7 canales a 100 Hz, página de 5 s | 9,1 ms | **8,0 ms** |
| 7 canales a 100 Hz, página de 30 s | 10,8 ms | **9,5 ms** |
| 7 canales a 100 Hz, página de 300 s | 12,2 ms | **11,0 ms** |
| 32 canales a 1000 Hz, página de 5 s | 20,1 ms | **17,1 ms** |
| 32 canales a 1000 Hz, página de 30 s | 25,3 ms | **19,0 ms** |
| 32 canales a 1000 Hz, página de 300 s | 66,8 ms | **62,6 ms** |

Ninguna fila empeoró. La última sigue fuera de los 40 ms de presupuesto, que es
el pendiente de registros densos anotado en el hito 33 y no algo que trajo esto.

### El error que encontró la herramienta en sí misma

**`tests/capturar_pantalla.py` nunca había sacado los dos esquemas en una
corrida.** Se colgaba para siempre después del primero, sin consumir CPU y sin
imprimir nada, y los dos PNG que había en el temporal eran de dos corridas
distintas. El motivo: cerrar la ventana principal es cerrar el programa, así
que `closeEvent` pregunta por el trabajo sin exportar —y la herramienta scorea
media noche a propósito, para que la franja y el hipnograma tengan forma—. Ese
cartel es modal, y una ventana con `WA_DontShowOnScreen` no lo muestra en
ninguna parte: nadie podía contestarlo.

Ahora las ventanas **no se cierran**: quedan vivas hasta que termina el
proceso. Es la segunda vez en dos hitos que la herramienta paga su costo, y la
primera que lo paga sobre sí misma.

### Lo que este hito deja anotado

- **El eje horizontal sigue en segundos de la ventana** y el diseño lo tiene en
  hora absoluta de la noche, que es como un scorer nombra un evento. La opción
  existe para el hipnograma (`accion_eje_en_hora`) y no para la señal.
- **El selector de canales sigue siendo un árbol con encabezado «Canal»**, y el
  diseño tiene una lista compacta con el chip de clase de cada uno. Los dos son
  del área central y no de las barras, así que no entraban en el hito 36.

---

## Hito 38: Lo que faltaba del prototipo

**Cerrado el 20 de septiembre de 2026.** El usuario abrió un EDF de verdad con
el hito 37 puesto, sacó una captura y la mandó junto al prototipo: «comparalo y
determiná lo que haya que cambiar para que sea igual». Lo que quedaba no eran
las barras —ésas las cerró el hito 36— sino el área central, y una diferencia
que no era de estructura y se llevaba toda la atención: **los siete canales a la
misma escala**, con el respiratorio barriendo seis carriles.

**No tiene stubs que contar.**

- [x] **Cada clase de canal abre con su escala.** `DEFAULT_SCALE_BY_KIND_UV`,
      en `config.py`: EEG 100 µV, EOG 250, EMG 50, ECG 1000.
      - **Una sola escala para todos no podía servir**, y era lo que había: son
        señales de órdenes de magnitud distintos y el pliego pide soportarlas
        todas sin limitar por tipo (V4_F). Con los 100 µV de un EEG, un canal
        respiratorio se sale de su carril y **tapa seis canales**; un EMG queda
        aplastado contra su eje.
      - **Respiratorio y Otro no están en la tabla y no es un olvido**: un
        termómetro rectal y un flujo oro-nasal no comparten ni unidad ni orden
        de magnitud, así que no hay ninguna escala de uso corriente que darles.
        Se miden sobre la primera época, que es la que se va a ver.
      - **La clave es el valor de `ChannelKind` y no la clase**, porque
        `config.py` es la capa de abajo de todas y no puede importar `core/`.
        Que ninguna clave apunte a una clase que ya no existe lo verifica un
        test: renombrar una clase dejaría su escala sin aplicarse en silencio.
  - Test: `tests/test_session.py`, **156 tests en verde**.
- [x] **El eje de tiempo, en hora de la noche.** `TimeAxis`, en
      `signal_view.py`.
      - Decía «Segundos de la ventana» y numeraba de 1 a 29. Un scorer no
        nombra un evento por el segundo que ocupa dentro de su época, y era el
        único eje del programa en segundos relativos: la barra de navegación, la
        franja y el hipnograma ya hablaban en hora.
      - El formato lo decide cuánto hay entre marcas: con marcas de un minuto
        los segundos son ruido, y con una página de milisegundos —que la escala
        de tiempo libre permite— hace falta la décima o todas dirían lo mismo.
      - **Sin horario de inicio vuelve a los segundos**, con el rótulo: es lo
        que pasa con un EDF anónimo.
  - Test: `tests/test_windows.py`, **65 tests en verde**, con
    `seconds_to_clock_time()`.
- [x] **El selector de canales es una lista con chips.** Una fila por canal con
      su nombre y su clase en una cápsula de color, y un pie con un atajo por
      clase presente en el registro.
      - **Era un árbol agrupado por clase.** Costaba dos renglones por clase y
        una sangría en un panel angosto, y el nombre de la clase aparecía una
        vez por grupo: mirando un canal suelto había que subir la vista hasta
        su encabezado.
      - **El atajo por clase no se perdió**, que es lo que cubre V3_P. Su
        estado se refleja cada vez que cambia una casilla: con medio EEG a la
        vista, un botón que siguiera marcado ocultaría la clase en el próximo
        clic en vez de completarla.
      - **El pie dobla en una grilla de tres.** En una sola fila el mínimo era
        la suma de todos los botones y el panel abría en 327 px en vez de los
        212 del diseño: el ancho lo decidía el pie y no la lista.
      - El color del chip sale de la paleta del esquema por posición en
        `ChannelKind`, y la tinta de `theme.ink_over()`. Una tabla propia sería
        otro juego de colores que mantener en los dos esquemas.
      - **Salió de `SIN_TEST_PROPIO`**: mientras era un árbol lo único suyo era
        reflejar el registro, y el pie tiene estado que se puede desincronizar
        sin que nada falle a la vista.
  - Test: `tests/test_channel_selector.py`, **16 tests en verde**.
  - Test: `tests/test_docks.py`, **39 tests en verde**, con el ancho de apertura.
- [x] **La pestaña de la época, rellena**, y una línea que separa «Abrir» de los
      menús.
      - La tinta de la pestaña la elige `theme.ink_over()` midiendo contra el
        relleno, que es la misma función que decide la del botón de la fase
        marcada y la del icono de reproducir.
  - Test: `tests/test_menus.py`, **44 tests en verde**.
- [x] **El canalón dice sólo la escala.** Llevaba también la clase, y con un
      registro de verdad —«Resp oro-nasal», clase «Respiratorio»— la línea
      salía cortada con puntos suspensivos, que es peor que no decirla. La
      clase se sigue viendo en el selector, que es donde la pone el diseño.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.

### Los tres errores que encontró la captura

Ninguno lo veía un test, y los tres estaban en lo que este mismo hito acababa
de escribir. Es el argumento de la herramienta por tercera vez:

- **La banda de la época le cambiaba el color al fondo entero.** Con el color
  del diseño puesto, y con la página de una época —que es la de arranque— la
  banda y la página son lo mismo: no marcaba ningún tramo, teñía la pantalla.
  Ahora se esconde cuando cubriría todo.
- **La pestaña salía partida en dos.** Estaba en z = −19 y la grilla es un solo
  objeto en −10, así que le dibujaba sus líneas por encima al texto.
- **La amplitud decía «varias» siempre.** Era correcto y no decía nada, desde
  que cada clase abre con la suya. Ahora dice el rango —«50–250 µV»—, y el de
  cada canal está en su carril.

### Lo que este hito deja anotado

- **Los botones de amplitud siguen siendo ▲ y ▼** donde el diseño pone − y +.
  Es a propósito: son las teclas Arriba y Abajo que hacen lo mismo, y el icono
  es lo único que lo dice.
- **Scoring e hipnograma siguen sin abrirse solos**, por decisión del usuario:
  el prototipo dibuja el estado de trabajo y no el de apertura, y el hito 24
  fijó que el programa abre con la señal y los canales.

---

## Hito 39: La carrocería de los paneles

**Cerrado el 21 de septiembre de 2026.** Lo pidió el usuario después de ver el
canvas de los paneles: «implementar el diseño propuesto». Lo primero que hay
que llevar es lo que los seis comparten, porque es lo que hacía que cada uno se
viera distinto sin que ninguno estuviera mal.

**No tiene stubs que contar.**

- [x] **`psglab/ui/panel_header.py`, el encabezado y el cartel de vacío.**
      - **Los tres paneles de curva metían todo en el título del gráfico**, con
        un `_reflejar_titulo()` copiado tres veces: la descripción del
        resultado quedaba centrada sobre el dibujo, sin línea que la separara,
        y el método vivía en un `QLabel` suelto encima. Dos renglones para dos
        datos del mismo cálculo.
      - **El cartel de vacío reemplaza al gráfico, no le escribe encima.** Con
        ejes, grilla y leyenda detrás de la frase, un panel sin resultado se
        leía como un resultado que dio cero. Es una `QStackedWidget`: o el
        contenido o el cartel, nunca los dos.
      - **El rótulo va escrito en mayúsculas en el texto**, no con
        `text-transform`, que la hoja de estilo de Qt no soporta. El espaciado
        entre letras sí se puede pedir, pero por `QFont`. Es la lección del
        hito 36, aplicada antes de tropezarse con ella.
  - Test: `tests/test_panel_header.py`, **33 tests en verde**.
- [x] **`MetricPanel` y `ConnectivityPanel` dejaron de ser `PlotWidget`** y
      pasaron a contenerlo, que es como ya estaba `PsdPanel`. Era la condición
      para que los tres pudieran llevar el encabezado.
  - Test: `tests/test_metric_panel.py`, **29 tests en verde**;
    `tests/test_connectivity_panel.py`, **24 tests en verde**.
- [x] **La tabla de bandas del espectro dice de dónde a dónde va cada una** y
      lleva la muestra del color con que el gráfico la sombrea. El rango había
      que sabérselo de memoria o leerlo del sombreado, y el color no estaba
      escrito en ningún lado.
  - Test: `tests/test_psd_panel.py`, **27 tests en verde**.
- [x] **El esquema trae la tinta de lo que destruye** (`danger`), y la lleva un
      solo control: «Descartar», en el cartel del trabajo sin exportar.
      - **`DestructiveRole` no alcanza**: le dice a Qt dónde ubicar el botón y
        con qué tecla responde, no de qué color pintarlo. En Windows salía
        idéntico a «Cancelar», que es el botón de al lado y el contrario.
      - Entra en el control de contraste con el **mínimo de texto** y no el de
        gráfico, porque es el rótulo de un botón: Sereno da 5,67 y Nocturno
        6,09 sobre la ventana. Un esquema puede no traerla, y entonces el botón
        se ve como cualquier otro.
  - Test: `tests/test_theme.py`, **78 tests en verde**;
    `tests/test_entrega.py`, **316 tests en verde**.
- [x] **Un icono más**, el del cartel de vacío: tres barras y una base. Es el
      único que no vive en un botón, y por eso es la silueta más neutra de
      todas: no sugiere ninguna acción.
  - Test: `tests/test_icons.py`, **33 tests en verde**.

### El tercer error que encontró la herramienta de capturas

**`show_psd_dialog()` y `show_complexity_dialog()` cuelgan la captura**, por el
mismo motivo que la colgaba cerrar la ventana: abren `QInputDialog` para elegir
el canal y la medida, y un cartel modal sobre una ventana con
`WA_DontShowOnScreen` no se muestra en ninguna parte y nadie lo puede
contestar. La herramienta ahora les pone el resultado a los paneles llamando a
sus setters, sin pasar por el menú.

Van tres veces que la herramienta paga su costo, y dos de las tres el error
estaba en ella misma. Conviene tenerlo escrito: **nada de lo que la captura
llama puede abrir un cartel modal.**

### Lo que este hito deja anotado

Del canvas quedan sin llevar, y son todos del mismo tamaño que lo que se hizo:

- **Los chips de estado de la impedancia** (bueno, aceptable, alto) y la
  leyenda de canales del panel de métrica.
- **La escala de color de la conectividad** con sus extremos rotulados, que hoy
  es la barra de pyqtgraph.
- **Los chips de fase y de evento de la Übersicht**, que hoy son rectángulos
  pintados con `QPainter`.
- **El error con la causa técnica plegada** y el cartel de progreso al leer un
  registro.

---

## Hito 40: Lo que cada panel dice de lo suyo

**Cerrado el 21 de septiembre de 2026.** La otra mitad del canvas de paneles:
si el hito 39 llevó lo que los seis comparten, éste lleva lo que cada uno tiene
que decir y no decía.

**No tiene stubs que contar.**

- [x] **El chip pasó a ser una pieza compartida**, en `panel_header.py`. Lo
      dibujan tres lugares —la clase de un canal, el estado de una impedancia,
      la fase de una época— y lo que comparten es el radio, el aire y de qué
      color sale la tinta, que la elige `theme.ink_over()` midiendo contra el
      relleno. Cada uno decide **dónde** va su cápsula, que es lo único que
      cambia entre los tres.
  - Test: `tests/test_panel_header.py`, **33 tests en verde**.
- [x] **La impedancia dice si cada canal pasa el límite**, en una columna
      propia con su chip.
      - **Son dos estados y no tres.** El diseño proponía un semáforo —bueno,
        aceptable, alto— y `analysis/impedance.py` define **un solo umbral**,
        `channels_above_limit()`, inclusive. Un «aceptable» intermedio habría
        sido un criterio clínico que el programa no tiene y que el informe no
        comparte.
      - **Un canal sin medir no lleva cápsula**, se queda como texto: una
        cápsula gris parecería estar afirmando algo sobre una medición que no
        existe, que es lo que el módulo entero evita desde su primera línea.
      - El límite sale de `DEFAULT_LIMIT_KOHM`, el mismo con el que
        `impedance_report()` arma el informe, así que la columna y el informe
        no se pueden contradecir. El encabezado lo dice: sin el límite a la
        vista, «supera» no dice a qué.
  - Test: `tests/test_impedance_panel.py`, **27 tests en verde**.
- [x] **La métrica tiene su leyenda en una franja propia.** pyqtgraph la dibuja
      **adentro** del gráfico, flotando sobre la esquina superior derecha: con
      una noche entera dibujada se apoya justo sobre el tramo de más actividad
      y tapa el dato.
  - Test: `tests/test_metric_panel.py`, **29 tests en verde**.
- [x] **La escala de color de la conectividad dice qué mide.** Decía de 0 a 1 y
      no de qué: un mapa de colores sin la unidad se puede leer de izquierda a
      derecha, pero no se puede comparar con el de otra medida.
      - El nombre escrito sale de `METHOD_LABELS`, al lado de `METHODS`, por lo
        mismo que `psd.describe_method()`: «wpli» es de la API y «wPLI» es de
        quien lo lee, y separarlos en dos módulos garantiza que se agregue un
        método y su rótulo quede en el nombre de la API.
      - **La ventana pide el método explícito** en vez de tomar el de fábrica
        de `compute_connectivity()`: el rótulo sale de ahí, y con el método
        implícito los dos podían separarse sin que nada fallara.
  - Test: `tests/test_connectivity_panel.py`, **24 tests en verde**;
    `tests/test_connectivity.py`, **40 tests en verde**.
- [x] **La Übersicht dice en qué fase está cada ventana**, con el chip pintado
      con la escala del esquema: la misma del hipnograma, la franja de posición
      y el botón de scoring.
      - El panel mostraba tres ventanas y **ninguna decía su fase**. La
        Übersicht existe para ver el contexto de la que se scorea —que hay un
        huso justo antes, que la de al lado ya está puesta— y la fase es la
        mitad de ese contexto.
      - La fase es **dato y no dibujo**, como el resto de `OverviewWindow`: la
        herramienta dice cuál es y la interfaz decide con qué color pintarla.
  - Test: `tests/test_overview.py`, **34 tests en verde**.

### El bug que destapó el chip de la fase

**La Übersicht cachea sus ventanas** y las rearma al cambiar de época, no al
scorear: el chip de la fase recién puesta no aparecía hasta la próxima flecha.
Anotar ya pedía `refresh()` por exactamente este motivo —está escrito en
`main_window.py` desde el hito 28— y scorear no lo hacía porque hasta ahora
nada de lo que la Übersicht mostraba dependía del scoring.

No se veía antes de este hito porque no había nada que mirar. Tiene su test en
`tests/test_entrega.py`, **316 tests en verde**.

### Lo que este hito deja anotado

Del canvas quedan dos, y los dos son carteles y no paneles:

- ~~**El error con la causa técnica plegada.**~~ **Ya estaba hecho y esta nota
  lo decía mal**: `MainWindow._show_error()` usa `setDetailedText()` desde que
  existe, así que el mensaje en español y la causa técnica ya viven separados,
  con la segunda detrás de «Mostrar detalles». Se descubrió al ir a
  implementarlo, en el hito 41.
- **El cartel de progreso al leer un registro.** Hoy hay cursor de espera y un
  mensaje en la barra de estado. Una barra de progreso de verdad necesita que
  el lector informe cuánto lleva leído, y no lo hace.

---

## Hito 41: Los seis paneles, y no cuatro

**Cerrado el 21 de septiembre de 2026.** El hito 39 le puso el encabezado a los
tres paneles de curva y el 40 a la impedancia. Quedaban dos —filtros e ICA— sin
ponerlo, y eso es peor que no habérselo puesto a ninguno: **cambiar de solapa
movía el contenido treinta y cuatro píxeles** para arriba y para abajo.

**No tiene stubs que contar.**

- [x] **El panel de filtros lleva encabezado**: cuántas clases de canal tiene
      el registro y contra qué frecuencia se sugirieron los cortes.
      - **La frecuencia y el tope de Nyquist son dos cosas** y van a dos
        lugares: el encabezado dice de dónde salen los sugeridos, y el rótulo
        de adentro por qué algunos vienen vacíos.
  - Test: `tests/test_filter_panel.py`, **26 tests en verde**.
- [x] **El panel de ICA lleva encabezado y cartel de vacío**, con cuántos
      componentes salieron y sobre cuántos canales.
      - **Acá el cartel reemplaza las dos columnas y no sólo los gráficos.**
        Sin descomposición, la lista de componentes está vacía y el botón de
        aplicar, apagado: media pantalla de controles muertos al lado de una
        frase se lee como un panel roto.
  - Test: `tests/test_ica_panel.py`, **30 tests en verde**.
- [x] **Los seis tienen su test de carrocería**, y no tres: el parámetro del
      test recorre los seis paneles, así que agregar uno sin encabezado hace
      fallar la suite.
  - Test: `tests/test_panel_header.py`, **33 tests en verde**.

### El cuarto error que encontró la captura

**El texto de una fila seleccionada no se leía.** La hoja de estilo pintaba el
fondo de la fila elegida —el realce del esquema— y no su tinta, así que Qt
ponía la suya, que es blanca: sobre el realce de Sereno eso da **1,24 a 1**. El
nombre del componente elegido desaparecía, y con él el del canal seleccionado
en el selector, que usa la misma regla.

**Y dejó a la vista una limitación de `theme.ink_over()`** que conviene tener
escrita: elige entre el blanco y el fondo del esquema, así que sólo da una
respuesta legible cuando el relleno está **lejos de los dos**. Sirve para el
acento, para el color de una fase y para el de una clase de canal; no para un
realce pálido, donde las dos candidatas son casi el mismo color. Ahí la tinta
que corresponde es la del esquema, y la hoja de estilo la pone a mano.

El par entró en el control de contraste, así que cualquier esquema que se
agregue queda medido solo.

### Una nota del hito 40 que estaba mal

**El error con la causa técnica plegada ya estaba hecho.** La nota decía que el
mensaje y su `details` iban al mismo cartel, y `MainWindow._show_error()` usa
`setDetailedText()` desde que existe: la causa técnica ya vive detrás de
«Mostrar detalles». Se descubrió al ir a implementarlo. La nota quedó tachada
en su lugar en vez de borrada, porque el error fue afirmar algo del código sin
mirarlo.

### Lo que queda del canvas

Uno solo, y es el que no depende de la interfaz:

- **El cartel de progreso al leer un registro.** Hoy hay cursor de espera y un
  mensaje en la barra de estado. Una barra de progreso de verdad necesita que
  el lector informe cuánto lleva leído, y `read_recording()` no lo hace: MNE
  lee el archivo entero en una llamada. Es trabajo de `readers/`, no de `ui/`.

---

## Hito 42: Lo largo deja de congelar la ventana

**Cerrado el 21 de septiembre de 2026.** Cerrado el canvas de paneles, el
siguiente paso de interfaz no era otro dibujo: es el ítem que la auditoría del
19 de septiembre dejó abierto en el [hito 33](#hito-33-la-auditoría-del-19-de-septiembre)
con números. La conectividad de la noche tarda **entre 15 y 18 s** sobre ocho
horas, y durante esos quince segundos la ventana no repintaba, no se podía
arrastrar y el sistema la marcaba como «no responde».

**No tiene stubs que contar.**

- [x] **`psglab/ui/background.py`**, correr algo en otro hilo y devolver el
      resultado en el de la interfaz.
      - **`_trabajando()` no podía resolverlo**, y no por estar mal escrito:
        pone el cursor de espera y el mensaje **antes** de bloquear, que es
        todo lo que se puede hacer desde adentro del hilo que se va a bloquear.
      - **No hay cancelar.** Ni MNE ni numpy interrumpen un cálculo empezado:
        un botón así sólo dejaría de mirar el resultado mientras el núcleo
        sigue ocupado hasta el final. Ofrecerlo sería mentir sobre lo que hace.
      - **Un error inesperado se vuelve a elevar** en el hilo de la interfaz.
        Lo que hereda de `PsgLabError` sale por `failed` y llega a
        `_show_error()`, que es el contrato de todo el programa; un
        `AttributeError` es un bug y no un mensaje para el investigador.
        Atraparlo dentro del hilo sería peor todavía: Python lo imprime por
        consola, el hilo muere y la ventana se queda esperando para siempre un
        resultado que no llega.
  - Test: `tests/test_background.py`, **9 tests en verde**.
- [x] **La conectividad de la noche fue la primera en salir del hilo.** Es la
      más cara de las tres y la que no cambia la señal, así que es la que menos
      decisiones nuevas obliga a tomar.
      - **Lo que se lee de la sesión se lee antes de arrancar el hilo**: el
        otro recibe el registro y los nombres ya resueltos y no vuelve a
        preguntarle nada a `Session`.
      - La entrada del menú **se apaga mientras dura**. `BackgroundTask` lo
        rechaza igual, pero un menú que deja pedir algo que va a fallar es peor
        que uno que lo muestra apagado.
  - Test: `tests/test_entrega.py`, **316 tests en verde**.
- [x] **Una barra de espera en la barra de estado, indeterminada.** Ni la
      conectividad ni la ICA informan cuánto llevan hecho, así que un
      porcentaje sería inventado: el cartel de progreso del canvas mostraba un
      62 % que el programa no puede saber. Una barra que se mueve sin decir
      cuánto falta es honesta; una que dice un número, no.
- [x] **Cerrar la ventana espera al cálculo.** Soltar la sesión con otro hilo
      todavía leyendo el registro lo deja trabajando sobre memoria que ya nadie
      tiene.
  - Test: `tests/test_main_window_layout.py`, **8 tests en verde**, que es
    donde se declara qué es público de la ventana.

### Cómo se testea algo con hilos sin que el resultado dependa del reloj

**Ningún `sleep` y ninguna espera con tiempo.** Un test así pasa en una máquina
y falla en la de al lado, y es el mismo motivo por el que los dos bancos de
medición no son tests. Todo se sincroniza con `BackgroundTask.wait()` —que es
lo que ya necesita el cierre de la ventana— y con `threading.Event` para los
dos casos que necesitan ver el trabajo a mitad de camino.

`wait()` además **fuerza la entrega**: `QThread.finished` viaja por la cola de
eventos del hilo de la interfaz, y quien llama a `wait()` la está bloqueando.
Sin eso, el resultado llegaría recién cuando el bucle de eventos volviera a
correr, que al cerrar el programa es nunca.

### Lo que este hito deja anotado

- **La ICA y el filtrado siguen en el hilo de la interfaz**, 9 s y 2,5 s. El
  mecanismo ya está; lo que falta decidir es otra cosa: las dos **cambian la
  señal**, así que hay que definir qué pasa si el usuario navega, scorea o
  anota mientras se calcula sobre el registro que está por reemplazarse.
- **Los registros densos siguen sin entrar en el cuadro** de 40 ms. Es la otra
  mitad del hito 33 y no tiene nada que ver con los hilos.

## Hito 43: Una tipografía, y su hermana de ancho fijo

**Cerrado el 21 de septiembre de 2026.** El encargo era dejar la aplicación en
una tipografía, o dos si están emparentadas. **Estaba medio cumplido y medio
no.** El programa ya empaqueta IBM Plex Sans y IBM Plex Mono, que son la misma
superfamilia dibujada junta; lo que no tenía era **garantía** —Configuración →
Tipografía ofrecía las ciento cuarenta familias de la máquina, así que las dos
empaquetadas eran un valor por omisión— ni **escala**: cada módulo inventaba su
propio salto de tamaño.

**No tiene stubs que contar.**

- [x] **La solapa pierde la lista de familias.** Es el mismo argumento que dejó
      los colores en dos esquemas y sacó la solapa que los editaba en el
      [hito 35](#hito-35-dos-esquemas-y-ninguna-perilla): una lista abierta son
      infinitos aspectos posibles y ninguno garantizado. **El tamaño sí se
      sigue eligiendo**, que es lo que hace falta para ver de lejos.
      - `Preferences.font_family` **se fue entero**, con su validación y su
        línea de serialización. Un archivo viejo que la traiga se lee igual:
        `_con_campos_nuevos()` saltea lo que no reconoce.
      - La solapa muestra **tres muestras** en vez de una: el cuerpo, una
        lectura numérica y un valor ausente. Son los tres estilos de la escala,
        y es la única forma de ver de un vistazo qué hace el tamaño elegido.
  - Test: `tests/test_preferences.py`, **68 tests en verde**;
    `tests/test_settings_dialog.py`, **48 tests en verde**.
- [x] **La escala vive en `psglab/ui/fonts.py` y en ningún otro lado.** Ocho
      roles en `ROLES`, cada uno con su familia, su paso en puntos, su peso, su
      inclinación y su tracking; `font_for()` los arma desde el tamaño que
      eligió el usuario.
      - **Los pasos se cuentan desde ese tamaño**, así que subirlo agranda la
        interfaz entera sin romper ninguna proporción.
      - **`MIN_POINT_SIZE` es el piso.** Con un tamaño base de 6, un paso de
        −2 dejaría el chip en 4, que no se lee. El canalón ya tenía su propio
        piso por su cuenta; ahora es uno solo.
      - **Un rol que no existe eleva `UnknownTypeRoleError`** y el mensaje los
        enumera, como hace `icons.icon()`: el nombre lo escribe quien dibuja y
        un error de tipeo es la causa habitual.
  - Test: `tests/test_fonts.py`, **19 tests en verde**.
- [x] **Los módulos dejaron de inventar su salto.** `channel_axis.py` achicaba
      un punto y `panel_header.py` dos: eran dos respuestas a la misma
      pregunta. Ahora los dos nombran un rol —«cuerpo», «lectura secundaria»,
      «rotulo», «chip»— y no un tamaño. Es el mismo reparto que ya tienen los
      colores: el módulo dice **qué cosa** está dibujando.
  - Test: `tests/test_channel_axis.py`, **12 tests en verde**;
    `tests/test_panel_header.py`, **33 tests en verde**.
- [x] **La itálica entra, y sólo donde significa algo.** Inclinada quiere decir
      **«esto no lo midió ni lo eligió nadie»**: el «sin medir» de la tabla de
      impedancias y el «sin scorear» del pie del panel de scoring.
      - **Hasta acá esa diferencia la cargaba el gris**, que ya quiere decir
        otra cosa —«esto es secundario»— y los dos se pisaban. Un valor ausente
        es lo contrario de secundario: es la advertencia más importante de la
        tabla de impedancias, y ese módulo entero está construido alrededor de
        no confundirlo con un cero.
      - **Se aplica en los dos sentidos.** Al escribir el valor la fila vuelve
        a la redonda y al scorear la ventana el pie también; si todo estuviera
        inclinado, la inclinación no diría nada.
      - **En el pie se inclina la ausencia y no el renglón**, que es lo que
        encontró la captura: «Ventana 1 · *sin scorear*» entero en itálica
        decía que tampoco la ventana la había elegido nadie. El rótulo lleva
        marcas y `status()` contesta el texto pelado, que es lo que el resto
        del programa compara.
  - Test: `tests/test_impedance_panel.py`, **27 tests en verde**;
    `tests/test_scoring_panel.py`, **27 tests en verde**.

### Lo que este hito deja anotado

- ~~**Falta empaquetar `IBMPlexSans-Italic.ttf`.**~~ *(Resuelto en el
  [hito 46](#hito-46-tres-cabos-sueltos).)* El rol `ausente` pedía itálica y
  funcionaba, pero sin el archivo Qt **sintetizaba** la inclinación deformando
  la regular, que se lee peor porque las curvas se estiran en vez de
  redibujarse. El binario no se bajó hasta que el usuario lo decidió.
- **Los roles «titulo» y «secundario» todavía no tienen quien los pida** desde
  un módulo: los escribe la hoja de estilo con sus propios tamaños. Unificarlos
  obliga a decidir qué hace `stylesheet()` cuando no hay `QFont` base, y eso es
  un hito aparte.

---

## Hito 44: Tres cosas que se vieron en la pantalla

**Cerrado el 21 de septiembre de 2026.** Las tres las encontró el usuario
usando el programa, no un test; una de ellas es un bug de verdad y las otras
dos son decisiones de diseño que no sobrevivieron al contacto con la pantalla.

**No tiene stubs que contar.**

- [x] **La barra dejó de decir la amplitud.** La mostraba desde el hito 36,
      entre los dos botones que la cambian.
      - **Lo que mostraba casi siempre era un rango**, «37–1025 µV», y un rango
        no es la amplitud de ningún canal: es el mínimo de uno y el máximo de
        otro. Dejó de ser la excepción en el hito 38, cuando cada clase pasó a
        abrir con su escala; el propio docstring decía que era «lo que se lee
        siempre» y lo daba por bueno.
      - **No se pierde nada**: la escala de cada canal está en su carril del
        canalón desde el hito 37, que es donde se la lee contra la señal que
        describe. Mostrarla dos veces, una de ellas mal, era peor que una.
      - Se fueron `NavigationBar.set_amplitude()`, `ANCHO_DE_LA_AMPLITUD` y
        `MainWindow._amplitud_visible()`.
  - Test: `tests/test_navigation.py`, **42 tests en verde**;
    `tests/test_entrega.py`, **316 tests en verde**.
- [x] **Reproducir se ve como los otros seis.** Iba relleno con el acento por
      ser la única acción de la barra que hace algo por sí sola y no un paso
      más de lo mismo. El usuario lo pidió al revés y el argumento se sostiene
      solo: los siete son transporte, y uno oscuro en el medio se lee como otra
      clase de control. El estado lo dice el icono, que es lo único que cambia.
      - **El icono había que rehacerlo, y eso no estaba a la vista.** Era un
        disco lleno con el triángulo **recortado**, dibujo que funcionaba
        justamente por ir sobre el acento: ahí el disco era la silueta y el
        hueco, el símbolo. Sin ese fondo pasó a ser una mancha oscura con un
        triángulo diminuto adentro —peor que antes—, así que es un anillo con
        el triángulo lleno. Conserva lo que el disco resolvía: en una fila de
        siete, reproducir no puede ser un triángulo más entre las dos flechas
        de época.
      - La regla `QPushButton[primario="true"]` de la hoja de estilo **se fue
        con él**, porque era su único consumidor. Una regla que nadie pide es
        el mismo camino muerto que el hito 9.
  - Test: `tests/test_navigation.py`, **42 tests en verde**;
    `tests/test_icons.py`, **33 tests en verde**, con los tres puntos que
    distinguen un anillo de un disco.
- [x] **La franja de posición se quedaba con los colores del esquema viejo.**
      Éste sí es un bug: al pasar de Nocturno a Sereno la franja seguía oscura.
      - **El cache del fondo no se soltaba al cambiar de esquema.** Existe
        porque la franja se repinta en cada época —veinticinco veces por
        segundo mientras se reproduce— y pintar 2650 rectángulos por cuadro es
        lo que el hito 25 le sacó a la grilla; se tiraba al cambiar el scoring,
        la cantidad de épocas o el ancho, y cambiar de esquema no es ninguna de
        las tres. `apply_scheme()` llamaba a `update()`, que repintaba el mismo
        pixmap de antes.
      - **Ningún test lo veía porque todos comparaban identidad de objeto**, no
        color. El nuevo lee el píxel del medio del pixmap y lo compara contra
        `overview_background` del esquema en uso; sin el arreglo da el color de
        Nocturno.
  - Test: `tests/test_navigation.py`, **42 tests en verde**.

### Lo que este hito deja anotado

- **`utils.units.format_amplitude()` ya no lo llama nadie de `psglab/`.** Era
  su único consumidor `_amplitud_visible()`. Sigue siendo una función de
  biblioteca con su test y su fila de contrato, pero el canalón escribe la
  escala con un `f"{escala:.0f} µV"` propio en vez de pedírsela: son dos
  criterios para escribir lo mismo, y conviene que sea uno.

---

## Hito 45: La banda no se dibujaba y la lupa miraba un solo canal

**Cerrado el 22 de septiembre de 2026.** El usuario reportó dos cosas usando el
programa: que tildar y destildar «Banda de amplitud» no hacía nada aunque
hubiera un canal seleccionado, y que la Lupa no se parecía al prototipo y
ampliaba siempre el primer canal. **Las dos eran ciertas**, y debajo había tres
huecos distintos en `ui/`.

**Es el hito 9 otra vez, del lado del dibujo.** Aquél encontró seis requisitos
hechos en `tools/`, con sus tests en verde, que la ventana no consumía. Éste
encontró dos más de la misma forma y por el mismo motivo de método: los tests de
`tools/` llaman a la herramienta directamente y los de `signal_view` le pasan un
overlay armado a mano, así que **nadie verificaba el camino entre los dos**.

**No tiene stubs que contar.**

- [x] **`_active_viewer_tool` contestaba dos preguntas con un valor**: quién se
      queda con el mouse, y quién tiene algo que dibujar. Se asignaba sólo
      dentro de la rama `exclusive`, y la banda declara `exclusive = False` con
      razón —no compite por el clic—, así que **su `overlays()` no lo llamaba
      nadie**. Ahora son `_mouse_tool` y `_drawing_tools`.
      - **`_activate_panel_tools()` tenía el mismo error de lectura**, y es lo
        que explica el síntoma exacto: usaba `not exclusive` como si dijera «es
        un panel permanente», así que tildaba la banda sola al abrir cada
        registro. El usuario encontraba la opción ya encendida y sin efecto, la
        destildaba y la volvía a tildar, y nada cambiaba. El discriminador
        correcto es tener dock: los no exclusivos son la banda, el histograma y
        la Übersicht, y sólo los dos últimos lo tienen.
      - **Activar un modo del mouse ahora destilda el anterior.** `_toggle_tool()`
        desactivaba a las otras exclusivas pero no tocaba su entrada de menú,
        así que se podían ver dos encendidas con una sola recibiendo eventos.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con el camino
    completo: tildar deja un `BandOverlay` dibujado y destildar lo saca.
- [x] **La `y` en microvoltios se medía siempre contra el primer canal.**
      `microvolts_at_pixel()` acepta un canal desde el hito 9 y **nadie se lo
      pasaba nunca**, así que caía en `self._visible[0]`. Medido sobre tres
      canales, apuntando al centro exacto de cada carril —donde la señal vale
      cero—: 0,0 µV sobre el primero, **−222,2** sobre el segundo y **−444,4**
      sobre el tercero. Números plausibles y equivocados, que es la peor clase.
      - El conversor que faltaba es `SignalView.channel_at_pixel()`, que
        invierte la geometría de `_centro_de_carril()`. Se recorta al carril más
        cercano en vez de contestar None fuera de rango: el mouse sigue estando
        sobre el gráfico.
      - **Les pegaba a las tres herramientas que usan `y`** —lupa, ocupación y
        anotador—, así que se arregló para las tres y no sólo para la que se
        reportó. `ViewerTool` recibe ahora `channel_name` en sus tres métodos de
        mouse, opcional y último, para no romper a quien no lo necesite.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.
- [x] **La lupa no dibujaba ningún círculo y ampliaba un canal fijo.**
      `_dibujar_lupa()` tenía `canal = self._visible[0]` escrito a mano, y
      `CircleOverlay` no tenía campo de canal, así que no había por dónde pasar
      la respuesta: se le agregó, por lo mismo que el hito 7 se lo agregó a
      `BandOverlay`.
      - **Hasta el hito 9 fue un punto de 30 píxeles que no ampliaba nada; del
        9 al 45, una polilínea estirada sin ningún círculo**, pese a que el tipo
        se llama `CircleOverlay`. Hoy es la lente del prototipo: borde, fondo
        propio, el tramo ampliado recortado adentro con el color de su canal, y
        el instante escrito debajo.
      - **El recorte lo hace Qt**, con `ItemClipsChildrenToShape` sobre el
        cristal y la curva como hija. Recortar los datos a mano habría dejado la
        onda cortada en los bordes en vez de la lente.
      - **La lente se dibuja redonda aunque los dos ejes no compartan unidad**
        —`x` son segundos y `y` son carriles—: el radio vertical sale de
        `viewPixelSize()`. Se recalcula en cada movimiento del mouse; con el
        mouse quieto y la ventana redimensionándose queda ovalada hasta el
        próximo movimiento.
- [x] **La banda se dibujaba con el relleno de fábrica de pyqtgraph**, azul a
      alpha 50, o sea invisible sobre el trazo azul del primer canal. Lo
      encontró la captura apenas la banda empezó a dibujarse. Ahora sale del
      esquema, traslúcida y con los dos bordes marcados, que son los que dicen
      dónde terminan los 75 µV.
- [x] **La captura enciende las dos herramientas.** No había ninguna imagen
      donde mirarlas, que es parte de por qué esto duró tanto.

### Dos trampas que costaron encontrar

**`addToGroup()` y no `setParentItem()`.** Sobre un `QGraphicsItemGroup`, lo
segundo deja el ítem sin dueño: el envoltorio de Python es la única referencia
que queda y el recolector se lo lleva al volver de la función, sin avisar y sin
que nada falle. La etiqueta de la hora desaparecía así, y en un banco de prueba
aparte el mismo código andaba.

**Un test se apoyaba en el bug.** El de la ocupación clicaba en el medio del
gráfico y lo daba por «lejos» porque, medido contra el primer canal, el medio
caía a cientos de µV. Con el carril bien resuelto el medio de un carril es cero,
o sea justo encima de la línea. El test afirmaba lo correcto con una premisa que
sólo era cierta por el error; ahora el clic va a 90 µV de verdad, adentro del
mismo carril.

### Lo que este hito deja anotado

- ~~**La ocupación guarda sus líneas sin canal.**~~ *(Resuelto en el
  [hito 46](#hito-46-tres-cabos-sueltos): sí pertenece a un canal, por lo mismo
  que `BandOverlay` en el hito 7 y `CircleOverlay` en éste.)*

---

## Hito 46: Tres cabos sueltos

**Cerrado el 22 de septiembre de 2026.** Los tres estaban anotados al final de
los hitos 43, 44 y 45, y los tres son chicos. Van juntos porque ninguno da para
un hito propio y porque los tres son de la misma clase: cosas que se vieron y
se dejaron escritas en vez de arreglarse en el momento.

**No tiene stubs que contar.**

- [x] **El informe de impedancias mostraba Markdown crudo.** La frase más
      importante del informe —«no quiere decir que estén bien»— iba entre
      asteriscos, y el informe es **texto pelado**: se lee en un
      `QPlainTextEdit` y en el archivo exportado, así que el investigador veía
      los asteriscos. El énfasis lo tiene que cargar la redacción.
      - **El test es por marca y no por frase**, y barre las cuatro situaciones
        del informe: negrita, subrayado, comillas de código, HTML y numeral de
        título. Una frase nueva con marcas lo hace fallar aunque nadie se
        acuerde de esta regla.
      - Un barrido sobre todos los literales de `psglab/` que no son docstrings
        encontró sólo este caso y dos backticks en un `details` de
        `derivation.py`, que quedan: ahí el texto es la causa técnica y el
        backtick rodea el nombre de un argumento.
  - Test: `tests/test_impedance.py`, **54 tests en verde**.
- [x] **Las líneas de ocupación no sabían de qué canal eran.** Lo dejó anotado
      el hito 45 y es el mismo problema que `BandOverlay` tuvo en el hito 7 y
      `CircleOverlay` en el 45: la `y` está en microvoltios medidos contra el
      eje de un canal, y cada uno tiene su ganancia.
      - **Se veía de dos formas.** El visualizador dibujaba todas las líneas
        sobre el primer carril, con la ganancia del primero; y un clic en el
        centro de cualquier carril borraba una línea trazada en otro, porque el
        centro de todos vale 0 µV. La segunda apareció recién cuando el hito 45
        hizo que la `y` se midiera bien: antes estaba tapada por el error.
      - **El canal es el de donde arrancó el trazo**, no el de donde está el
        mouse: una línea que cruza al carril de al lado sigue midiendo sobre el
        canal en el que el usuario empezó, y cambiarla de dueño a mitad del
        arrastre la haría saltar mientras se dibuja.
      - **La tolerancia del clic pasó a seguir al canal del clic.** Decía «el
        primero visible» con un motivo escrito que el hito 45 volvió falso.
  - Test: `tests/test_occupancy.py`, **51 tests en verde**.
- [x] **`IBMPlexSans-Italic.ttf`, empaquetada.** El rol `ausente` la pedía
      desde el hito 43 y Qt la sintetizaba deformando la regular. La de verdad
      tiene `italicAngle` −11° y sus propios dibujos —la «a» pasa de dos pisos
      a uno—, es la misma versión 3.005 y la misma fundición que la regular, y
      entra bajo la misma OFL 1.1. Pesa 203 kB.
      - El párrafo de `docs/ARQUITECTURA.md` que lista los archivos **pide que
        se lo actualice** al agregar uno, porque el control de licencias del CI
        sólo mira los paquetes de pip.
  - Test: `tests/test_fonts.py`, **19 tests en verde**, que ya exigía que todo
    lo declarado en `FONT_FILES` exista.

### Por qué el de Markdown duró tres sesiones

Se encontró mirando una captura del panel de impedancias mientras se trabajaba
en otra cosa, se avisó, y se dejó pasar dos veces por estar fuera del hito en
curso. Es la decisión correcta —no ensanchar el alcance— y el costo es que el
hallazgo vive sólo en una conversación hasta que alguien lo escribe. Ahora
tiene test.

---

## Hito 47: Lo caro era ajustar, y no cambia la señal

**Cerrado el 22 de septiembre de 2026.** Es el segundo y último ítem abierto
del [hito 33](#hito-33-la-auditoría-del-19-de-septiembre): sacar del hilo de la
interfaz lo que quedaba largo. El hito 42 puso el mecanismo y movió la
conectividad de la noche; faltaban «la ICA, 9 s» y «filtrar, 2,5 s».

**El ítem estaba mal planteado, y lo mostró medirlo.** Decía que las dos
**cambian la señal** y que eso era lo que las volvía un trabajo distinto del de
la conectividad. Pero «la ICA» son dos operaciones separadas —ajustar e
inspeccionar por un lado, aplicar por el otro—, y sobre ocho horas de seis
canales a 100 Hz:

| operación | tiempo | ¿cambia la señal? |
|---|---|---|
| `fit_ica()` | **345 s** | no |
| `component_topography()` × 6 | 0,00 s | no |
| `apply_ica()` | 0,26 s | sí |
| `apply_filters()` | 0,44 s | sí |

Los 345 s son ruido blanco, que es el peor caso para que FastICA converja —no
convergió—, así que son una cota superior y no lo típico; los 9 s de la
auditoría, sobre un registro real, son la cifra realista. Lo que no depende del
caso es el orden: **ajustar domina por dos o tres órdenes de magnitud, y no
toca la señal.** Las dos que sí la tocan cuestan décimas de segundo.

Así que la que había que mover era exactamente la que no necesitaba ninguna
decisión nueva: es el mismo trabajo que la conectividad.

**No tiene stubs que contar.**

- [x] **`show_ica_dialog()` corre en otro hilo.** Calca el patrón de
      `show_connectivity_night_dialog()`: lo que se lee de la sesión se lee en
      el hilo de la interfaz, el otro recibe el registro ya resuelto, y
      `_mostrar_la_ica()` guarda la descomposición y abre el panel.
      - **Las topografías se calculan adentro del hilo.** Son parte del costo
        —aunque acá den 0,00 s— y tampoco tocan widgets; dejarlas afuera
        devolvería el trabajo a medio hacer al hilo que se quiso liberar.
  - Test: `tests/test_entrega.py`, **316 tests en verde**.
- [x] **«Montaje» y «Filtrar» se apagan mientras dura un cálculo.** No es
      cosmético: las cuatro operaciones que llevan adentro sustituyen el
      registro, y hacerlo debajo de una ICA que se está ajustando dejaría una
      descomposición de una señal que ya no está. **Eso no falla solo** —MNE
      acepta el pedido y devuelve una señal reconstruida con una matriz ajena—,
      que es lo mismo contra lo que `_olvidar_ica()` existe.
      - Los dos menús quedan en la ventana, como ya quedaba
        `accion_conectividad_de_la_noche` y por el mismo motivo escrito ahí.
- [x] **Navegar, scorear y anotar siguen habilitados.** Es lo que vuelve útil
      sacarlo del hilo: si hubiera que esperar igual para seguir trabajando, no
      se habría ganado nada. La época, el scoring y las anotaciones viven en
      `Session` y no dependen de los valores de las muestras, así que sobreviven
      a que el registro se reemplace.

### Lo que este hito deja anotado

- **Aplicar la ICA y filtrar se quedan en el hilo de la interfaz**, y es una
  decisión y no un olvido: miden 0,26 s y 0,44 s acá, y 2,5 s en el peor caso
  de la auditoría. Moverlas cuesta una decisión nueva —qué pasa con lo que el
  usuario haga mientras se reemplaza la señal— y unas veinticinco esperas
  repartidas por los tests, a cambio de un congelamiento de menos de un
  segundo. Si alguna vez un registro mucho más denso lo vuelve visible, el
  mecanismo ya está y el camino es `_aplicar_analisis()`, que es único.

---

## Hito 48: La auditoría de los tests

**Cerrado el 22 de septiembre de 2026.** Es la primera auditoría de los tests
desde que empezó el proyecto: las cuatro anteriores —la del 4, la del 7, la del
8 y la del 19 de septiembre— miraron el código y la documentación, y los tests
los dieron por buenos porque estaban en verde. El usuario la pidió porque
**nunca se habían auditado y son una parte importante del proyecto**.

Son 1931 funciones de test, 3423 casos y 28 326 líneas. Se revisaron en dos
capas: barridos sobre el árbol de sintaxis para lo mecánico, y **mutación**
—romper el código a propósito y ver si algún test se da cuenta— para lo que de
verdad mide si un test sirve. Lo destructivo corrió en un worktree aparte.

**No tiene stubs que contar.**

### Lo que salió limpio

Conviene decirlo primero, porque es la mayor parte:

- **Cero tests vacíos.** Los nueve sin ningún `assert` son de «no eleva», y
  uno lo comenta.
- **Cero tautológicos.** Los dos que marcó el barrido comparaban dos llamadas
  distintas a la misma fábrica, y uno documenta que **sí fue** tautológico y
  se arregló.
- **Cero nombres de test pisados** dentro de un archivo: ninguno se quedaba
  sin correr por repetir el nombre de otro.
- **Cero referencias muertas** en los docstrings. Las que nombran algo que ya
  no existe lo hacen en pasado, a propósito.
- **Las cuatro ambigüedades cerradas del pliego tienen las dos ramas
  cubiertas**, con tests escritos para sobrevivir a una reversión: leen la
  constante de `config.py` en vez de copiarla.
- **Los tests transversales afirman fuera del bucle**, así que no pueden pasar
  por iterar sobre un conjunto vacío.

### Lo que se arregló

- [x] **`Scoring.change_nomenclature()` aceptaba una nomenclatura inventada.**
      Es un bug y no sólo un hueco de test. No tenía guarda propia: la
      validación vivía dentro de `convert()`, que corre una vez **por ventana
      scoreada**, así que sobre un scoring sin scorear el bucle no iteraba y la
      basura se guardaba. El objeto quedaba con una cadena donde va un enum, y
      el siguiente `export_scoring()` moría con `AttributeError: 'str' object
      has no attribute 'name'` —que es justamente lo que `test_contratos.py`
      existe para impedir, porque atraviesa el `except PsgLabError` de la
      ventana—.
      - **Y el test de contratos lo certificaba como seguro.** Su fila construía
        `Scoring(3, Nomenclature.AASM)`: un scoring recién creado, o sea el
        único camino en el que la guarda no disparaba. Ahora el caso está en
        `RECHAZOS_OBLIGATORIOS`, que es la tabla que **exige** rechazar.
      - No era alcanzable por el usuario —el panel pasa valores de un combo—,
        pero sí desde un script. `check_nomenclature()` pasó a pública porque
        ahora la comparten dos módulos.
  - Test: `tests/test_contratos.py`, **1043 tests en verde**;
    `tests/test_nomenclature.py`, **51 tests en verde**.
- [x] **`tools/occupancy.py` era el módulo peor verificado, y la causa eran las
      fixtures.** Cuatro mutaciones sobrevivían a la suite **entera**:
      - Dos en la conversión entre segundos y fracción: la fixture `sesion`
        dura una época, así que página y época coinciden y la rama correcta y
        la de respaldo daban lo mismo.
      - Una en el acierto del clic: todas las líneas de los tests de borrado
        eran **horizontales**, donde interpolar y tomar el punto medio
        coinciden. Había una vertical y una diagonal, pero sólo en los tests de
        porcentaje.
      - Una en la tolerancia sin sesión. **Esa la dejó el hito 46**, que
        escribió la guarda y probó sólo la mitad.

      Las dos fixtures principales pasaron de uno a dos canales, y hay un test
      por hueco. Se verificó que las cuatro mutaciones mueren.
  - Test: `tests/test_occupancy.py`, **51 tests en verde**.
- [x] **La lupa, lo mismo con los canales.** Su fixture tenía **un solo
      canal**, así que el arreglo del hito 45 —ampliar el canal de abajo del
      cursor— quedó verificado en `test_entrega.py` y `test_signal_view.py`, y
      el archivo propio de la herramienta seguía sin poder verlo. Pasó a tres.
  - Test: `tests/test_magnifier.py`, **30 tests en verde**.
- [x] **V2_F se verificaba por la pieza y no por el camino.** El contador de
      picos sólo se probaba con `herramienta.on_mouse_press(...)`, que es el
      método que el [hito 9](#hito-9-lo-que-la-interfaz-no-consume) señaló como
      la causa de que seis hitos pasaran sin ver que la lupa no llegaba a la
      ventana, y que `psglab/ui/README.md` prohíbe. Ningún test mandaba un clic
      de Qt real. El camino funcionaba: era hueco de test.
  - Test: `tests/test_entrega.py`, **316 tests en verde**.
- [x] **Seis funciones públicas que ningún test nombraba**, y cinco eran de
      `core/windows.py`: `sample_to_seconds_absolute`, `seconds_to_samples`,
      `seconds_to_view_fraction`, `view_fraction_to_seconds` y
      `seconds_to_epoch_offset`. Son justamente las conversiones que
      `tools/base.py` manda a usar para no confundir unidades. `test_windows.py`
      tenía cuarenta y un tests; éstas se verificaban sólo de rebote. La sexta
      era `EpochScore.is_scored`, que decide si hay trabajo sin exportar.
      - **Escribirles el test encontró un error de lectura**: se dio por
        sentado que `epoch_to_seconds()` devolvía el comienzo, y devuelve el
        tramo entero.
  - Test: `tests/test_windows.py`, **65 tests en verde**;
    `tests/test_scoring.py`, **28 tests en verde**.
- [x] **Cuatro más que sólo tenían una fila de contrato**: `is_electrical()`
      —que decide qué canales se escalan a microvoltios y usan ocho lugares—,
      `check_index()`, `check_nomenclature()` y `Viewport.replaced()`, cuyo
      docstring dice que existe «para los tests» y no la usaba ninguno.
  - Test: `tests/test_units.py`, **47 tests en verde**;
    `tests/test_viewport.py`, **51 tests en verde**.
- [x] **`Viewport.containing()` no se probaba con un tramo a medias.** Sus
      cinco tests usaban tramos totalmente adentro o totalmente afuera, nunca
      uno que empezara adentro y terminara afuera, que es el caso normal cuando
      la página es apenas más larga que la época. La suite entera sí atrapaba
      la mutación, por otro lado; ningún test del método lo hacía.

- [x] **`Session.set_active_tool()` valida que el nombre sea texto.** Guardaba
      cualquier cosa. Sigue sin validarlo contra el registro de herramientas
      —importarlo desde `core/` cerraría un ciclo, y el docstring lo explica—,
      pero sí que sea `None` o un texto con algo escrito.
- [x] **`AnnotationSet.add_label(color=...)` exige `#rrggbb`, y validarlo
      encontró un bug.** El visualizador pinta la banda de una anotación con
      `color + "55"`: le **concatena** la transparencia al texto. Eso sólo da
      un color con seis dígitos. Preferencias validaba el color preguntándole
      a pyqtgraph, para el que `red` y `#e6754aff` son colores, así que un
      archivo editado a mano con `red` pasaba, la sesión lo guardaba, y dibujar
      una anotación de esa clase elevaba `ValueError: Unable to convert red55
      to QColor`, crudo.
      - **Una sola gramática, sin romper lo que funcionaba.** `core/` exige
        `#rrggbb` con `es_color_de_clase()`, preferencias valida con la misma
        regla, y al leer el archivo **normaliza** en vez de rechazar: `red`
        llega como `#ff0000` y sigue siendo rojo. Es lo mismo que ya hacía la
        ventana de configuración al elegir un color.
      - Se verificó que el crash era real, desactivando las dos defensas.
  - Test: `tests/test_annotations.py`, `tests/test_session.py` y
    `tests/test_preferences.py`, más el camino entero en `test_entrega.py`.

### La red nueva

- [x] **`test_cada_funcion_de_negocio_la_llama_algun_test`**, en
      `test_consistencia.py`. `COBERTURA_DE_TESTS` dice qué archivo cubre qué
      módulo, y eso es cierto a nivel de archivo y **no dice nada por función**:
      declaraba que `test_units.py` cubría `units.py` mientras `is_electrical()`
      no aparecía en él. La red exige que cada función pública de `core/`,
      `utils/`, `tools/`, `analysis/` y `readers/` la **llame** algún test de
      comportamiento, o que figure en `SIN_TEST_DE_COMPORTAMIENTO` con su
      motivo. Hoy la tabla está vacía.
      - **No cuentan `test_contratos.py` ni `test_consistencia.py`**: el
        primero prueba sólo valores hostiles, el segundo lee el código sin
        correrlo. Tampoco un docstring: nombrar una función al explicar otra no
        la verifica.
      - **Es un piso, no un techo.** Que un test la llame no dice que la
        verifique bien; eso lo mide la mutación, y un chequeo estático no puede.
      - Se comprobó que se pone roja: sacándole los tests a `is_electrical()`,
        la nombra.

### Lo que este hito deja anotado

- **Catorce tests nunca corren en el CI**, los que dependen de `data/`. Está
  documentado en `CLAUDE.md`; conviene tenerlo contado: el CI verifica 3409 de
  3423, y lo que no verifica nunca es la lectura de archivos reales.
- **Nueve filas de `CONTRATOS` aceptaban los seis valores hostiles.** Seis
  son legítimas —predicados y banderas booleanas, que responden en vez de
  rechazar—. Las otras tres pasaron a `RECHAZOS_OBLIGATORIOS`:
  `change_nomenclature`, más `set_active_tool` y `add_label(color=...)`, que
  el usuario decidió que validaran; ver arriba.
- **La mutación de la auditoría no se guardó como herramienta**, y es a
  propósito: tarda del orden de una hora y cambia el código fuente, así que no
  puede ser un test ni correr en el CI. Sólo mutaba comparaciones, `and`/`or` y
  `not` —no constantes ni sentencias—, así que su resultado es un piso.

---

## Hito 49: La envolvente se calcula una vez

**Cerrado el 22 de septiembre de 2026.** Es el ítem que le quedaba al
[hito 33](#hito-33-la-auditoría-del-19-de-septiembre): con 32 canales a
1000 Hz y página de 5 min, un paso de reproducción costaba entre 73 y 152 ms
según la corrida, contra los 40 que pide el reloj. Con él cierra el 33.

**No tiene stubs que contar.**

### Lo que se midió antes de tocar nada

- **No había regresión.** La primera corrida del banco dio el doble de lo que
  anotaba este archivo, también con el registro de prueba. Intercalando el
  banco sobre el cierre del hito 33 y sobre `Add`, los dos dieron lo mismo:
  era la máquina ocupada. La misma medición varió entre 19 y 37 ms de una
  corrida a otra, así que **un número suelto del banco no dice nada**; sólo
  vale intercalado.
- **Lo caro era calcular, no dibujar.** Perfilando treinta pasos con página de
  5 min, dos tercios del cuadro eran `argmin` y `argmax` dentro de la
  envolvente: unos 95 ms. Pintar eran unos 40.
- **La caché no acertaba nunca al reproducir.** Se buscaba por la primera y la
  última muestra de la página, y la reproducción avanza la página en cada
  cuadro. Tampoco se podía aprovechar la parte ya calculada, porque las
  cubetas se contaban desde el borde de la página: al moverse, cada muestra
  caía en otra cubeta.

### Lo que se hizo

- [x] **Las cubetas se cuentan desde el comienzo del registro.**
      `core/decimation.py` recibe ahora el **tamaño** de cubeta y no la
      cantidad —`envelope_by_bucket_size()`, con `bucket_size_for()` para
      sacarlo del ancho—, porque la cantidad depende de dónde empieza el tramo
      y el tamaño no. Reemplazan a `min_max_envelope()`, que ya nadie llamaba.
      Siguen sin perder ningún pico: cada muestra cae en exactamente una
      cubeta.
  - Test: `tests/test_decimation.py`, **41 tests en verde**;
    `tests/test_contratos.py`, **1043 tests en verde**.
- [x] **El visualizador guarda la envolvente por trozos de 64 cubetas**, con
      clave (canal, tamaño de cubeta, número de trozo), y arma cada página con
      los trozos que la cubren. Un paso calcula sólo el trozo que entra, cuando
      entra uno. Las cubetas de los bordes se dibujan enteras aunque empiecen
      antes de la página: la pantalla recorta lo que cae afuera.
      - **De yapa, la traza dejó de titilar.** Con las cubetas contadas desde
        el borde, una espiga caía en cubetas distintas de un cuadro al otro y
        se redibujaba distinta. Con la grilla fija, donde dos páginas se
        superponen se dibujan exactamente los mismos puntos, y hay un test que
        lo exige.
      - Los tests nuevos se probaron contra el cálculo viejo: fallan los seis
        que tocan la caché.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.

### Lo que dio

Intercalado contra `Add`, cinco corridas de cada uno, con 32 canales a
1000 Hz. **Los números absolutos no sirven**: la misma página de 5 s del código
viejo dio 7 ms en una corrida y 67 en otra, según lo que hiciera la máquina.
Lo que se sostiene en las cinco es la proporción:

| Página | Antes | Después |
|---|---|---|
| 5 s | 7–67 ms | 8–48 ms |
| 30 s | 8–54 ms | 13–45 ms |
| **5 min** | **73–152 ms** | **12–69 ms** |
| registro entero, sin moverse | 4–31 ms | 7–47 ms |

- **Antes, la página de 5 min costaba entre 2,2 y 10,5 veces la más cara de
  las otras de la misma corrida.** Después, entre 0,9 y 1,9 veces: en tres de
  las cinco corridas, lo mismo.
- Con la máquina tranquila, sesenta pasos seguidos con página de 5 min dieron
  una mediana de 19 ms y un máximo de 35.

### Lo que este hito deja anotado

- **El registro denso sigue pasando de los 40 ms en algunas corridas, con
  cualquier página**, y lo que falta es pintar: 32 curvas de unos 2200 puntos, más los ejes, que se
  regeneran en cada cuadro porque el rango se mueve. Es el ítem «Un registro
  denso llega justo» del [hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar),
  que sigue abierto con estos números.
- **Redibujar el registro entero sin moverlo arma la página con unos
  diecisiete trozos por canal** en vez de leer una envolvente ya armada. El
  perfil le da unos milisegundos por cuadro y el banco no lo distingue del
  ruido. Es el único caso en que la página no avanza, así que no es el que
  pide el reloj.
- **Cruzar a un trozo nuevo cuesta 1,2 ms**, medido: con página de 5 min pasa
  en uno de cada cuatro pasos, y es calcular 64 cubetas de 32 canales. La
  mediana del banco no lo muestra; por eso se midió aparte.

## Hito 50: Los pendientes, revisados

**Cerrado el 22 de septiembre de 2026.** Con el hito 49 no quedaba ningún
hito abierto, pero dentro de los cerrados había **diecinueve casillas sin
tachar**, y nadie las había vuelto a mirar desde que se escribieron. Se
revisaron una por una contra el código, que es lo único que dice si siguen
siendo ciertas: es la prosa que este archivo sabe que se desincroniza.

**No tiene stubs que contar.**

### Lo que se tachó

- [x] **Cuatro ya no eran ciertas.**
      - «Papel dibuja las señales en negro y Claro las varía» (hito 26): esos
        esquemas y la solapa Colores no existen desde el
        [hito 35](#hito-35-dos-esquemas-y-ninguna-perilla).
      - «La red del hito 20 no mira `tools/`» (hito 28): la cerró el
        [hito 30](#hito-30-las-decisiones-de-la-verificación), y
        `delete_annotation()` tiene camino desde la ventana.
      - «La reproducción corre en el hilo de la interfaz» (hito 24) decía que
        con 32 canales a 1000 Hz no había medición: la hay desde el
        [hito 49](#hito-49-la-envolvente-se-calcula-una-vez), y el pendiente
        es el mismo que «Un registro denso llega justo», del [hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar).
      - El hipnograma y la Übersicht estaban **dos veces**, en los hitos 31 y
        32; queda el del 31.
- [x] **Tres eran decisiones tomadas anotadas como pendientes**, y pasaron a
      llevar la forma que ya usaba el hito 32 —«Decidido en el hito N»—:
      OpenGL y el lector propio, en el hito 25, y el ancho de la pila que
      vuelve al 30 %, que es no guardar la disposición, del hito 24.
- [x] **Una era un bug, y se arregló.** `Recording.get_segment()` no validaba
      el tipo de sus extremos: con `3.5` o `None` la guarda de rango lo dejaba
      pasar y explotaba el índice de numpy, con un `TypeError` crudo que la
      ventana no atrapa. `True` pasaba como la muestra 1. Ahora pide un entero,
      de Python o de numpy, y las dos filas de `CONTRATOS` que faltaban
      existen.
  - Test: `tests/test_recording.py`, **53 tests en verde**;
    `tests/test_contratos.py`, **1043 tests en verde**.
- [x] **Una se actualizó sin tacharse**: el camino muerto de `exporters/` del
      hito 20 decía que ninguna acción llegaba a la rama de anotaciones, y el
      cartel del trabajo sin exportar llega desde el hito 33. La de
      Informacion.txt sigue sin camino.

### Lo que queda abierto, y de quién depende

Son once, y **ninguno es un hito**: cada uno sigue anotado en el suyo.

- **Esperan al cliente.** Qué vía de impedancia usa el laboratorio (hito 0);
  si Anotaciones.txt e Informacion.txt vuelven al menú (hito 23), que decide
  también el camino muerto de `exporters/` (hito 20); y si reproducir tiene
  que arrancar desde lo que se ve y no desde la época (hito 27).
- **Espera al usuario.** Confirmar que el hipnograma y la Übersicht hacen lo
  que tienen que hacer (hito 31).
- **Son trabajo, cuando se decida hacerlo.** La señal entera en memoria, dos
  veces (hito 18), que el [hito 57](#hito-57-cuánta-memoria-cuesta-cada-cosa) midió y dejó en dos decisiones; las solapas Cursores y Calibración, que entran con las
  reglas y los milímetros que configurarían (hito 22); el EDF+ de R&K que
  pregunta la nomenclatura al releerlo (hito 23); pintar el registro denso
  por debajo de 40 ms ([hito 25](#hito-25-rendimiento-al-abrir-y-al-desplazar)); y corregir una anotación sin borrarla (hito 28).

## Hito 51: La Übersicht muestra la señal

**Cerrado el 23 de septiembre de 2026.** El usuario fue a confirmar la
Übersicht —el pendiente del [hito 31](#hito-31-el-recorrido-manual)— y no supo
cómo hacerla dibujar algo. Scoreó tres épocas seguidas y lo único que apareció
fue un chip de fase en cada caja. **Era el comportamiento que el programa
tenía**, y el problema era ése: el panel no mostraba señal.

**No tiene stubs que contar.**

### Lo que faltaba

El prototipo «Herramientas y Übersicht» dibujaba en cada caja **la señal de su
época en miniatura**, con un encabezado —número, fase y eventos con su
nombre— y un clic que llevaba a esa época. Lo implementado desde el hito 9
tenía el número en el medio, el chip de la fase y una franja de color por
evento anotado, **y nada de señal**. El módulo decía que el panel existe para
ver «un huso que arranca en el segundo 29», y sin señal eso sólo se veía si
alguien ya lo había anotado: repetía lo que muestran el hipnograma y la
franja de posición.

Ningún test lo podía ver: verificaban qué ventanas entran, cuál es la actual y
qué eventos caen en cada una, que es todo lo que el panel hacía.

### Lo que se hizo

- [x] **Cada ventana publica su señal.** `OverviewWindow` lleva un
      `OverviewTrace` con las muestras de un canal, reducidas a 400 cubetas
      con la envolvente del hito 49 —que no pierde un pico—, y la escala y el
      desplazamiento del canal en el visualizador. **La misma escala y no una
      por caja**: ajustada a su propio máximo, una ventana tranquila llenaría
      la caja igual que un complejo K.
      - **Un canal**: el seleccionado, o el primero visible, que es la regla
        de la banda de amplitud. En una caja de noventa píxeles no se lee más
        de uno.
  - Test: `tests/test_overview.py`, **34 tests en verde**.
- [x] **Cada caja es un encabezado y una señal**, como en el prototipo: el
      número de la época, el chip de la fase, en la actual el nombre del
      canal, y a la derecha los eventos **con su nombre**, una vez por clase.
      Hasta ahora eran franjas de color sin rótulo. La señal lleva el color de
      su carril en el visualizador.
      - **El nombre del canal va en el encabezado y no sobre la señal**: la
        primera versión lo escribía adentro y la onda lo tapaba —«C3» se leía
        «03»—, que es la regla que llevó los nombres al canalón en el hito 37.
        Lo encontró la captura.
- [x] **Un clic en una caja lleva a esa época**, por el mismo camino que la
      franja de posición.
  - Test: `tests/test_overview_panel.py`, **24 tests en verde**;
    `tests/test_entrega.py`, **316 tests en verde**, con clics de Qt de verdad.
- [x] **La miniatura se rehace cuando cambia lo que dibuja**: el canal
      seleccionado, los visibles, la amplitud, el esquema y la señal misma
      —filtrar, volver a la original—. Ninguna de esas cosas le llegaba antes,
      porque el panel sólo dependía de la época.
- [x] **De paso, el botón de W decía «W» sobre «W»**, y el de R lo mismo: la
      tecla es la inicial de la etiqueta, que ahí es la etiqueta entera. Lo
      vio el usuario en su captura. Ahora se escribe una vez cuando coinciden.
  - Test: `tests/test_scoring_panel.py`, **27 tests en verde**.

Cada test nuevo de la ventana se probó contra el programa sin su pieza —sin el
clic, sin refrescar al seleccionar, sin refrescar al cambiar la amplitud, sin
dibujar la señal—, y falla.

### Lo que este hito deja anotado

- **El usuario todavía no la confirmó**: el pendiente del hito 31 sigue
  abierto, ahora con la versión que sí muestra algo.
- **La miniatura es de un solo canal.** Si el laboratorio quiere ver varios,
  es otra decisión: más canales en una caja de noventa píxeles no se leen, y
  agrandar el panel es V2_F.

## Hito 52: Una anotación se puede corregir

**Cerrado el 23 de septiembre de 2026.** Hasta acá, lo único que se podía
hacer con una anotación hecha era borrarla: equivocarse de clase en la lista o
marcar el tramo un poco corrido obligaba a borrarla y volver a encontrar el
tramo exacto. Estaba anotado en el
[hito 28](#hito-28-un-solo-menú-de-herramientas) «para cuando el laboratorio
lo pida», y el usuario lo eligió como siguiente paso.

**No tiene stubs que contar.**

### Lo que decidió el usuario

- **Se corrigen la clase y los bordes**: los dos errores comunes.
- **La clase se cambia desde el clic derecho**, que pasa de borrar a abrir un
  menú con «Cambiar clase…» y «Borrar».
- **Los bordes se arrastran con «Anotar» activo**: con otra herramienta el
  mouse es de ella.

### Lo que se hizo

- [x] **Corregir es reemplazar.** `Annotation` sigue siendo inmutable —es lo
      que la deja usarse como clave— y `AnnotationSet.replace()` cambia una por
      otra. **Valida la nueva antes de sacar la vieja**: un reemplazo que
      fallara a la mitad le costaría al investigador el evento que corregía.
      La nueva va a su lugar por muestra de inicio, que es la promesa de la que
      depende `remove_at()`.
  - Test: `tests/test_annotations.py`, **60 tests en verde**;
    `tests/test_contratos.py`, **1043 tests en verde**.
- [x] **Los bordes se arrastran.** Con «Anotar» activo, apretar a menos de
      cinco píxeles de un borde lo arrastra en vez de empezar una selección;
      mientras se arrastra, la banda se ve donde va a quedar, y soltar la
      corrige. Sobre un borde el cursor pasa a ↔, que es lo único que avisa
      que se puede. **Los bordes no se cruzan**: llevar el comienzo más allá
      del final lo deja una muestra antes, en vez de invertir la anotación en
      silencio. Tampoco se salen del registro.
      - **La tolerancia es en píxeles y la fija la ventana**: un segundo son
        cientos de píxeles con una página de 5 s y ninguno con la noche
        entera, y `tools/` no conoce la pantalla.
  - Test: `tests/test_annotator.py`, **41 tests en verde**.
- [x] **El clic derecho abre un menú** con «Cambiar clase…» y «Borrar». Cambiar
      la clase usa el mismo diálogo que al anotar —editable, así que una clase
      nueva se puede escribir— y arranca en la que tenía. **Borrar sigue
      preguntando**: el pedido fue agregar el menú, no sacar la confirmación.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con eventos de Qt de
    verdad: el menú, cambiar la clase, arrastrar cada borde, arrastrar lejos
    de un borde y el cursor.

Los tests nuevos se probaron contra el programa roto a propósito —sacar la
vieja antes de validar, no detectar los bordes, dejar que se crucen— y fallan.

**La primera corrida con el menú se colgó**, y es la advertencia de
`CLAUDE.md` sobre los modales: los tests del clic derecho que había abrían el
`QMenu` y nadie lo contestaba. El menú pasa ahora por
`_elegir_en_un_menu()`, que los tests reemplazan.

### Lo que este hito deja anotado

- **No hay deshacer.** Una corrección equivocada se corrige con otra, igual que
  una anotación de más se borra.
- **Mover la anotación entera**, sin cambiar su duración, no está: se hace
  arrastrando los dos bordes.

## Hito 53: Cuatro defectos que encontró el prototipo

**Cerrado el 23 de septiembre de 2026.** Después de que la Übersicht resultara
distinta del prototipo sin que nada lo detectara, el usuario pidió comparar el
programa contra las ocho pantallas del prototipo «Paneles y diálogos de
PsgLab». La comparación no tocó código: listó cuatro defectos, nueve cosas del
prototipo que faltan y las diferencias hechas a propósito. **Este hito arregla
los cuatro defectos**, que no pedían ninguna decisión; los faltantes quedan
anotados abajo.

**No tiene stubs que contar.**

### Lo que se arregló

- [x] **Los botones que arma Qt salían en inglés.** «Yes / No» en la pregunta
      antes de borrar una anotación, «Show Details... / OK» en el cartel de
      error, «OK / Cancel» en el diálogo de la clase: son los botones estándar
      de `QMessageBox` y `QInputDialog`, que el programa no escribe, y se
      traducen con la traducción que Qt tenga cargada. **No había ninguna.**
      `app.install_qt_translations()` carga `qtbase_es.qm`, que viene con
      PySide6. No se cambia el `QLocale`, que también cambiaría cómo se escriben
      los números en los campos. La suite corre con la misma traducción.
  - Test: `tests/test_entrega.py`, **316 tests en verde**.
- [x] **Métrica multiplicaba por mil.** Una entropía de 0,75 se leía «750», con
      «(x0.001)» en el rótulo: pyqtgraph les pone un prefijo por su cuenta a los
      ejes con valores menores que uno. `panel_header.plain_axes()` lo apaga en
      los cuatro gráficos de análisis con eje numérico —Métrica, Espectro y los
      dos de la ICA—; en el Espectro el prefijo habría ido pegado a «µV²/Hz».
  - Test: `tests/test_metric_panel.py`, **29 tests en verde**;
    `tests/test_panel_header.py`, **33 tests en verde**.
- [x] **La banda de una anotación no decía de qué clase era**: sólo tenía
      color, y había que recordar qué color era cada clase. Ahora lleva una
      pestaña con el nombre, como la de la época, una línea más abajo para no
      taparla, con el color de la clase y **encima de su banda**, para que el
      borde de una banda más angosta que el nombre no lo cruce. Se probó al
      revés —la banda detrás de la señal— y con una página larga la envolvente
      es un bloque lleno que la tapaba. Los bordes de la banda llevan también
      el color de la clase, desde que se agarran para corregirla (hito 52).
  - Test: `tests/test_signal_view.py`, **92 tests en verde**.
- [x] **En Sereno, una casilla sin marcar no se veía.** Con el estilo nativo de
      Windows, un elemento sin marcar de una lista no dibujaba ninguna casilla:
      **un canal oculto del selector no tenía nada que tildar**, y lo mismo las
      componentes de la ICA. La casilla del arousal apenas se separaba del
      fondo. La hoja de estilo le da borde a la casilla sin marcar, con la
      tinta secundaria, y el control de contraste la vigila; la marcada se deja
      al estilo nativo, que dibuja la tilde.
  - Test: `tests/test_theme.py`, **78 tests en verde**.

### Lo que apareció en el camino

- [x] **`theme.ink_over()` no podía elegir una tinta oscura en Sereno.** Elegía
      entre el blanco y el fondo del esquema, dando por sentado que el fondo es
      la tinta más oscura disponible, y en Sereno el fondo es casi blanco. El
      rótulo de la banda salía a 2,6 a 1, y **el amarillo de los chips de
      evento de la Übersicht, a 1,75**. Ahora la tinta del esquema es la
      tercera candidata. Cambió la tinta de seis rellenos, todos a mejor; el
      peor color de clase queda en 4,23, debajo de los 4,5 de un texto chico
      —subirlo es cambiar la paleta de clases— y el test afirma el piso de un
      gráfico, 3. El test que fijaba la limitación vieja se invirtió.
- [x] **La herramienta de captura mostraba un informe de impedancias que
      contradecía la tabla**: cargaba los valores a mano sin rehacer el
      informe. La ventana sí lo rehace; la captura ahora también. Y la captura
      lleva dos anotaciones, sin las cuales el rótulo de la banda no tenía
      dónde verse.

Cada test nuevo se probó contra el programa sin su arreglo —sin la traducción,
con el prefijo, sin el rótulo, sin el borde de la casilla, con dos candidatas
de tinta— y falla.

### Lo que la comparación deja anotado

- [x] **Faltan del prototipo** —hechos: los cuatro primeros en el hito 54, el
      resto en el [hito 55](#hito-55-lo-último-del-prototipo)—, de más a menos peso:
      - Métrica: la marca de la época actual sobre la curva, el eje en hora de
        la noche y cuántas ventanas quedaron sin dato.
      - ICA: la varianza que explica cada componente, cuántas va a quitar el
        botón, y la curva temporal en hora y no en segundos.
      - Banda de amplitud: decir sobre qué canal mide y escribir «75 µV» junto
        a la banda.
      - Atajos de teclado: es un cartel de texto plano con columnas
        desalineadas, y el prototipo es una tabla agrupada.
      - Los botones principales —«Aplicar», «Exportar…»— no se distinguen; el
        hito 44 sacó el estilo que los rellenaba.
      - Conectividad: los valores dentro de las celdas y la diagonal «—».
      - Filtros: el chip de la clase y cuántos canales tiene.
      - Espectro: la tabla deja ver tres de las seis bandas.
      - Ocupación: la duración escrita sobre cada línea.
- [ ] **Distintas a propósito**, que no cambian sin una decisión: los pesos de
      la ICA en barras y no en un mapa de la cabeza (no hay coordenadas de
      electrodos); la impedancia con dos estados contra un límite y no tres
      niveles, que es del laboratorio; y la espera al abrir un registro en la
      barra de estado y no en un cartel con el nombre y el tamaño.

## Hito 54: Lo que faltaba del prototipo

**Cerrado el 23 de septiembre de 2026.** Son los cuatro faltantes de peso medio
que listó la comparación con el prototipo del
[hito 53](#hito-53-cuatro-defectos-que-encontró-el-prototipo): los que más se
notan al usar el programa y ninguno pide una decisión de fondo.

**No tiene stubs que contar.**

### Lo que se hizo

- [x] **Métrica dice dónde está parado el usuario.** Una línea del acento marca
      la época actual y se mueve con ella —sólo si cambió, porque la ventana
      lo pide en cada paso de la reproducción—. El eje de abajo lleva **las
      mismas marcas que el hipnograma**, en hora de la noche si el hipnograma
      está en hora: decía «Ventana» siempre, y los dos gráficos de la noche
      hablaban unidades distintas. El encabezado dice cuántas ventanas
      quedaron sin dato, porque un hueco de una ventana entre dos mil no se
      ve.
  - Test: `tests/test_metric_panel.py`, **29 tests en verde**.
- [x] **La banda de amplitud dice cuánto mide y sobre qué canal**: «75 µV ·
      C3», en su borde de arriba, a la derecha de la página. Con una escala
      por canal, 75 µV ocupan distinto en cada carril, y la banda medía contra
      el seleccionado —o el primero visible— sin decir cuál.
      - **`format_amplitude()` escribía con punto decimal**: «37.5 µV» al lado
        del «41,7» del espectro. Lo encontró el test del rótulo; ahora usa
        coma, como todo número que ve el usuario.
  - Test: `tests/test_signal_view.py`, **92 tests en verde**;
    `tests/test_units.py`, **47 tests en verde**.
- [x] **La ICA dice cuánto explica cada componente**, cuántos va a quitar el
      botón, y su curva va en hora.
      - `analysis.ica.explained_variance()` **usa la definición de MNE**
        (`get_explained_variance_ratio`). Se probó sacarla de las normas de la
        matriz de mezcla, sin tocar la señal, y no coincide: 51 % donde MNE da
        62 %. Como MNE reconstruye la señal una vez por componente —casi 2 GB
        cada vez con 32 canales y ocho horas—, se mide sobre hasta 40 ventanas
        repartidas por la noche, y se muestra en porcentaje entero. Corre en
        el mismo hilo que el ajuste.
      - El botón pasó de «Aplicar y quitar los marcados» a decir cuántos.
      - La curva usa el eje del visualizador: decía «Segundos de la ventana» y
        contaba desde cero en cualquier época.
  - Test: `tests/test_ica.py`, **51 tests en verde**;
    `tests/test_ica_panel.py`, **30 tests en verde**;
    `tests/test_contratos.py`, **1043 tests en verde**.
- [x] **Los atajos, en una tabla agrupada**: navegación, scoring,
      visualización y archivo, con la tecla en su columna y en la letra de las
      lecturas. Era un cartel de texto plano con las columnas rellenadas con
      espacios, que en letra proporcional se desalineaban. Los grupos viven en
      `shortcuts.HELP_GROUPS`, y un test exige que cada atajo fijo esté en uno
      solo. La tabla es `ui/shortcuts_dialog.py`, nuevo.
  - Test: `tests/test_shortcuts.py`, **35 tests en verde**;
    `tests/test_shortcuts_dialog.py`, **5 tests en verde**.
  - Test: `tests/test_entrega.py`, **316 tests en verde**,
    con los cuatro por la ventana. Cada uno se probó contra el programa sin
    su conexión —sin mover la marca, sin seguir al hipnograma, con los
    segundos de la ventana, sin la varianza— y falla.

### Lo que este hito deja anotado

- [x] **Los faltantes de peso bajo del hito 53** —hechos en el [hito 55](#hito-55-lo-último-del-prototipo)—: los botones
      principales rellenos, los valores en las celdas de la conectividad, el
      chip de clase en los filtros, la tabla del espectro que muestra tres de
      seis bandas y la duración sobre cada línea de ocupación.
- **La captura no muestra la banda de amplitud**: la herramienta la dibuja
  donde está el mouse, y la captura sólo se lo da a la lupa. El rótulo se miró
  en un visualizador armado aparte.

## Hito 55: Lo último del prototipo

**Cerrado el 23 de septiembre de 2026.** Son los cinco faltantes de peso bajo
que listó la comparación con el prototipo del
[hito 53](#hito-53-cuatro-defectos-que-encontró-el-prototipo). Con este hito y
el [54](#hito-54-lo-que-faltaba-del-prototipo) quedan hechos los nueve.

**No tiene stubs que contar.**

### Lo que se hizo

- [x] **El botón principal va relleno del acento**: «Aplicar» en filtros y en
      la ICA, «Exportar…» en el cartel del trabajo sin exportar. El hito 44
      había sacado la regla, que entonces sólo usaba el botón de reproducir y
      lo volvía un bloque oscuro en la barra; vuelve con `PRIMARIO_PROPERTY`,
      y reproducir no la lleva. **Apagado no parece encendido**: el de la ICA
      sin componentes tenía que dejar de invitar a apretar.
  - Test: `tests/test_theme.py`, **78 tests en verde**;
    `tests/test_entrega.py`, **316 tests en verde**.
- [x] **La conectividad escribe el valor en cada celda**, con la tinta que se
      lee sobre ese color, y **la diagonal va en gris con «—»**: no se calcula,
      y pintada como cero se leía «estos canales no se parecen». Hasta doce
      canales; con más, la celda es más chica que el número.
      - La primera versión dibujaba la diagonal como una mancha: el borde de
        cada celda tenía 1 de grosor **en unidades del gráfico**, una celda
        entera. Lo encontró la captura; el borde es cosmético.
  - Test: `tests/test_connectivity_panel.py`, **24 tests en verde**.
- [x] **Los filtros dicen el color de la clase y cuántos canales tiene**: «EEG
      · 2 canales», con el cuadradito del selector. Un filtro de la fila vale
      para todos sus canales, y «EEG» con dos y con veinte se leían igual. La
      columna se ajusta al texto: la primera versión cortaba «EOG (ocular)…»
      justo antes de la cantidad, y lo mostró la captura.
  - Test: `tests/test_filter_panel.py`, **26 tests en verde**;
    `tests/test_ica_panel.py`, **30 tests en verde**.
- [x] **La tabla del espectro muestra todas sus bandas**: filas compactas y el
      alto de sus filas, que se rehace porque las bandas son configurables.
      Con el alto de fila de fábrica y un tope de 190 px se veían tres de seis.
  - Test: `tests/test_psd_panel.py`, **27 tests en verde**.
- [x] **Cada línea de ocupación dice cuánto dura**, sobre su medio y con el
      fondo del esquema: sin él, el número se perdía sobre una señal densa.
      `SegmentOverlay` gana un `label` que decide la herramienta, que es la que
      sabe qué mide.
  - Test: `tests/test_occupancy.py`, **51 tests en verde**;
    `tests/test_signal_view.py`, **92 tests en verde**.

Cada test nuevo se probó contra el programa sin su cambio —sin la duración,
sin el botón principal, sin la cantidad, sin las celdas, con el tope de la
tabla, sin el rótulo de la línea— y falla. La captura suma el panel de
conectividad, que no tenía, y una línea de ocupación.

## Hito 56: La rueda y el panel táctil sobre la señal

**Cerrado el 23 de septiembre de 2026.** Lo pidió el usuario después de dar
por buenos la Übersicht, el hipnograma, las anotaciones y la métrica: girar la
rueda sobre la señal tiene que acercar y alejar la página, y deslizar de
costado en el panel táctil, o girarla con Mayúsculas, tiene que desplazarla.

**No tiene stubs que contar.**

### Lo que se hizo

- [x] **La rueda sobre la señal acerca y aleja la página**: hacia adelante
      acerca, hacia atrás aleja, y **dos muescas la duplican**. Con una sola,
      cada muesca sería un «×2» del menú y de 30 s a la noche entera habría
      diez saltos sin nada en el medio. Un panel táctil manda pedazos de
      muesca, y la cuenta los suma sin redondear.
  - Test: `tests/test_entrega.py`, **316 tests en verde**, con
    eventos de rueda de Qt de verdad, mandados al viewport.
- [x] **Queda quieto el instante bajo el mouse**, como en un mapa, y ésa es la
      diferencia con Ctrl++, que acerca hacia el centro: para mirar un huso
      de cerca se lo apunta y se gira. Es `Viewport.zoomed_at()`, que ubica el
      comienzo con el ancho que **queda** después de recortar, no con el
      pedido: si no, al llegar a la página mínima la página se corría.
  - Test: `tests/test_viewport.py`, **51 tests en verde**;
    `tests/test_contratos.py`, **1043 tests en verde**.
- [x] **Reproduciendo, el ancla es el cursor** y no el mouse: la página es suya
      y el paso siguiente la vuelve a centrar, así que anclarla en el mouse
      la haría saltar de un cuadro al otro.
- [x] **Deslizar de costado desplaza la página**, un décimo de sí misma por
      muesca: en fracciones y no en segundos, igual que Mayús+→, porque un
      salto fijo no sirve a la vez para 200 ms y para cuatro horas. **Con
      Mayúsculas la rueda vertical también desplaza**; macOS la entrega ya
      convertida en horizontal y Windows no, así que se aceptan las dos.
      Deslizar hacia la derecha trae lo que estaba a la izquierda, como
      arrastrar un papel, y la rueda hacia atrás avanza, como bajar en un
      documento.
      - **Un gesto manda un solo eje**, el que más se movió: un panel táctil
        casi nunca desliza derecho, y sumar los dos haría que cada gesto de
        costado cambiara un poco la escala.
      - Reproduciendo, desplazar mueve el cursor, porque pasa por el mismo
        `_desplazar()` que las teclas: si moviera sólo la página, el paso
        siguiente la devolvería al cursor.
- [x] **Alejar con el registro entero en pantalla no hace nada**, y tampoco
      redibuja.
- [x] **La ayuda de atajos lo dice**, en «Navegación», al lado de Ctrl++:
      la rueda, Mayús+Rueda y deslizar de costado. No
      es un atajo —no pasa por `QShortcut`—, así que va en `MOUSE_HELP` y no
      en `FIXED_SHORTCUTS`.
  - Test: `tests/test_shortcuts.py`, **35 tests en verde**.

Cada test nuevo se probó contra el programa sin su cambio —sin la rueda, con
el centro fijo, anclando en el mouse al reproducir, con el ancho pedido, sin
llevar el ancla al borde de la página, sin Mayúsculas, con Mayúsculas sólo
vertical, sin el desplazamiento horizontal, con el sentido al revés, moviendo
sólo la página al reproducir y sin las filas de la ayuda— y falla.

## Hito 57: Cuánta memoria cuesta cada cosa

**Cerrado el 23 de septiembre de 2026.** Es la medición que pedía el pendiente
del [hito 18](#lo-que-sigue-sin-resolverse), «la señal sigue entera en memoria,
y la ventana principal guarda dos», antes de decidir nada. **La medición
corrige el pendiente**, y encontró que lo caro está en otro lado.

**No tiene stubs que contar.**

### Cómo se midió

Con un banco nuevo, `tests/medir_memoria.py`, que se corre a mano como los
otros dos. Mide **por la ventana** —`open_recording()`, `_aplicar_analisis()`,
`restore_original_recording()`— y no llamando a los módulos sueltos, que es
como midió el hito 18 y lo que no ve cuánto retiene la ventana. Cuenta
**en copias de la señal** —la señal entera como `float64`—, que es la unidad
que no depende del registro, y dice qué línea reservó cada bloque que queda
vivo.

- La primera corrida daba siete copias y media después de abrir un registro
  de 20 MB, y **seis y media eran MNE y scipy importándose** por primera vez.
  El banco hace ahora una pasada sobre un registro de un minuto antes de medir.

### Lo que cuesta

EDF sintético de 32 canales a 256 Hz y una hora: una copia son **236 MB**.
Sobre 8 canales y 20 minutos lo que queda es lo mismo y los picos salen un
poco más altos —abrir 2,7 en vez de 2,1, la ICA 8,3 en vez de 7,0—: lo que
MNE reserva aparte de la señal pesa más cuanto más chica es la señal.

| Operación | Pico | Queda |
|---|---|---|
| Abrir el registro | 2,1 copias | **1,0** |
| Mostrar el registro entero, volver a 30 s | 1,0 | 1,0 |
| Filtrar con los de fábrica | 3,1 | 2,0 |
| Filtrar otra vez, encima | 4,1 | 2,0 |
| Re-referenciar al promedio | 3,0 | 2,0 |
| Volver a la señal original | 2,0 | **1,0** |
| **Ajustar la ICA** y medir su varianza | **7,0** | 1,0 |
| Quitar un componente | 4,0 | 2,0 |
| Abrir otro registro, con la señal procesada | 4,1 | 1,0 |

Llevado a una noche de 8 horas con esos 32 canales, una copia son 1,9 GB:
ajustar la ICA pide **13 GB** de pico.

### Lo que dice

- [x] **La ventana guarda dos copias sólo después de un análisis**, y no
      siempre, como decía el pendiente. Mientras no se filtra nada, el
      original y la señal que se ve son **el mismo objeto**. Volver a la
      original suelta la procesada, y abrir otro registro suelta las dos: no
      hay ninguna fuga.
- [x] **Mirar no cuesta memoria**: la envolvente del registro entero cabe en lo
      que se redondea a la décima.
- [x] **El pico más alto es ajustar la ICA**, 7 copias, más del doble que
      cualquier otra cosa. Seis son de MNE: `ICA.fit()` copia los canales,
      los blanquea en otra copia y la descomposición en componentes principales
      arma una matriz del tamaño de la señal. Pedirle a MNE que use una de
      cada `decim` muestras **no alcanza**: copia la señal entera antes de
      descartar, y el pico queda en 3,2.
- [x] **Abrir otro registro con la señal procesada suma los dos**: el
      anterior sigue vivo mientras se lee el nuevo, a propósito. Si el archivo
      no se puede abrir, lo que se estaba haciendo sigue ahí.

### Lo que queda por decidir

- [x] **Ajustar la ICA sobre una muestra de la noche** —hecho en el
      [hito 58](#hito-58-la-ica-se-ajusta-sobre-una-muestra-de-la-noche)—. Medido sobre 8
      canales y 20 minutos, pasándole a `fit_ica()` una de cada ocho muestras:

      | Muestras | Pico | Tiempo |
      |---|---|---|
      | todas | 6,0 copias | 88 s |
      | una de cada 4 | 1,8 | 14 s |
      | una de cada 8 | **0,9** | **8 s** |

      La ICA no mira el orden de las muestras —separa fuentes mezcladas en el
      mismo instante—, así que saltear muestras no filtra nada: es ajustar con
      menos datos. **Cambia los componentes que salen**, y por eso no se hizo
      sin preguntar. Lo que hay que decidir es cuántas muestras alcanzan: la
      regla de uso habitual es unas veinte veces el cuadrado de los canales, y
      una noche de 32 canales a 256 Hz trae más de trescientas veces eso.
- [ ] **Volver a la original releyendo el archivo** en vez de guardarlo. Baja
      de dos copias a una lo que queda después de un análisis. Lo que cuesta:
      volver deja de ser instantáneo —leer son segundos— y depende de que el
      archivo siga donde estaba y sin cambios.

## Hito 58: La ICA se ajusta sobre una muestra de la noche

**Cerrado el 23 de septiembre de 2026.** Es la primera de las dos decisiones
que dejó el [hito 57](#hito-57-cuánta-memoria-cuesta-cada-cosa), y la tomó el
usuario: ajustar la ICA era lo que más memoria pedía del programa, siete
copias de la señal, y seis eran de MNE.

**No tiene stubs que contar.**

### Lo que se hizo

- [x] **`fit_ica()` le pasa a MNE una muestra repartida a lo largo de la
      noche**: una de cada `paso` muestras, **por lo menos `FIT_SAMPLES`**
      —200 000, trece minutos a 256 Hz— y menos del doble. Un registro más
      corto se ajusta entero, igual que antes. La ICA separa fuentes mezcladas
      **en el mismo instante** y no mira el orden de las muestras, así que
      saltear algunas no filtra nada: ajusta con menos datos, que sobran.
      - **Repartida y no un tramo**: una hora seguida puede ser toda vigilia,
        y el componente de parpadeo de la vigilia no es el de la noche.
      - **Un piso por la cantidad de canales**: treinta veces su cuadrado
        (`FIT_SAMPLES_PER_SQUARED_CHANNEL`), que es la regla de uso habitual.
        Con 32 canales son 30 720 y el tope fijo ya es seis veces eso; manda
        recién pasados los 80 canales.
      - **Sólo se copia lo que se usa**: la vista con el paso se toma antes de
        elegir los canales. Al revés, `data[filas]` copiaba los EEG enteros
        para descartar casi todo, y lo encontró el test de memoria.
      - **A MNE sólo le llegan los EEG.** Antes se le pasaba el registro
        entero y elegía él: una copia de más de cada canal que no se
        descompone.
      - La muestra declara su frecuencia verdadera, `fs / paso`. MNE ajusta
        igual y aplica después sobre la señal a la frecuencia original.
      - **El paso se redondea hacia abajo**: hacia arriba, un registro apenas
        más largo que el tope se ajustaba con la mitad. Lo encontró un test
        antes de que llegara a ningún lado.
  - Test: `tests/test_ica.py`, **51 tests en verde**. Los de antes siguen
    pasando sin tocarlos: su registro dura 60 s y se ajusta entero. Los nuevos
    bajan el tope para que el paso sea de verdad mayor que uno, y afirman
    **que la muestra sigue separando el parpadeo** con los pesos que se
    mezclaron, que lo ajustado sobre ella limpia la señal entera sin
    llevarse el alfa, y que el pico de memoria queda por debajo de una copia.
- [x] **El banco separa el ajuste de la varianza.** Medidos juntos, la
      varianza —que usa cuarenta épocas fijas, un tercio de un registro de
      una hora— tapaba cuánto había bajado el ajuste.

Cada test nuevo se probó contra el programa sin su cambio —con la noche
entera, con un tramo seguido, copiando los EEG enteros antes, con el paso
hacia arriba, sin el piso de los canales y declarando la frecuencia
original— y falla.

### Lo que cuesta ahora

Con `tests/medir_memoria.py`, en copias de la señal, contando la que ya está
abierta:

| Registro | Ajustar la ICA | Su varianza |
|---|---|---|
| 32 canales, 1 hora (hito 57: 7,0 las dos juntas) | 2,5 | 3,4 |
| 8 canales, 8 horas | **1,2** | **1,3** |

En la noche entera, ajustar **pasó de siete copias a poco más de la que ya
estaba**. Con una hora baja menos porque la muestra es un cuarto del registro
y no un treintaiseisavo. El tiempo, medido en el hito 57 sobre 8 canales y
20 minutos: de 88 s a 8 s con un octavo de las muestras.

- [ ] **Ahora el pico más alto es quitar un componente, 4,0 copias**, igual
      que filtrar dos veces seguidas. `apply_ica()` pasa la señal entera por
      MNE, que la copia a la ida y a la vuelta. Es el mismo viaje que el
      filtrado, y no se tocó acá.

---

## Al agregar o cerrar un ítem

Actualizá en el mismo commit: este archivo, la fila de `TRAZABILIDAD.md` y el
`README.md` de la carpeta que tocaste. Los PR van a la branch **`Add`**, nunca
a `Master`, y vienen comentados.
