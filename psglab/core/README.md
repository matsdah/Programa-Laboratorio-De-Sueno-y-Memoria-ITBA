# `core/` — modelo de datos y reglas de negocio

El corazón del programa. Acá vive **qué es un registro, qué es un scoring y qué
está permitido hacer con ellos**; nada de cómo se dibujan.

## La restricción que define esta capa

**`core/` no importa nada de `psglab.ui`.** Sólo depende de la biblioteca
estándar, de numpy y de `psglab.utils` y `psglab.config`.

No es preferencia estética. Es lo que permite testear el modelo, el scoring, la
navegación y las estadísticas **sin abrir una ventana gráfica**. Sin esa
separación, cada test tendría que levantar Qt y el testeo recurrente que pide el
pliego (sección 7) sería inviable en la práctica.

Si estás por escribir `from PySide6...` en un archivo de esta carpeta, algo se
ubicó mal.

## Los archivos

| Archivo | De qué se ocupa | Pliego |
|---|---|---|
| `recording.py` | El registro cargado en memoria: `Recording`, `Channel`, `ChannelKind`. `flat_channels()` dice qué canales no varían en un tramo, para que los análisis lo expliquen, y `non_finite_channels()`, cuántas muestras sin valor tiene cada uno, para avisarlo al importar. `content_limit_hz()` dice hasta qué frecuencia tiene contenido de verdad un canal grabado más lento que el registro (hito 72). | Soporte de V1_F–V3_F de "Importación", V4_F de "Visualización" |
| `session.py` | Estado de trabajo del usuario. **Es el objeto central.** | V1_F de "Navegación"; V2_P, V3_P, V5_F de "Visualización"; V4_F del histograma |
| `scoring.py` | Fase y arousal de cada ventana: `Scoring`, `EpochScore`. | V1_F, V2_F, V3_F de "Scoring" |
| `nomenclature.py` | Rechtschaffen y Kales frente a AASM: `Nomenclature`, `SleepStage`, conversión entre ambas. `check_nomenclature()` es pública desde el hito 48 porque `Scoring` la necesita para no guardar una nomenclatura inventada. | V1_F, V3_F de "Scoring"; V3_F del histograma |
| `annotations.py` | Eventos anotados sobre la señal: `Annotation`, `AnnotationSet`. Una anotación es inmutable; corregirla es reemplazarla con `replace()`, que valida la nueva antes de sacar la vieja (hito 52). `marks_to_annotations()` convierte las marcas que trae el archivo en anotaciones, en muestras (hito 73). | V1_F de "Anotación de la señal" |
| `windows.py` | Conversión entre ventanas, muestras y hora de la noche. | V1_P de "Visualización", V1_F de "Navegación", V2_F del histograma |
| `viewport.py` | **La página visible**, separada de la época de scoring. Inmutable: cambiarla es construir otra. `zoomed_at()` cambia la escala dejando quieto un instante, que es lo que hace la rueda (hito 56). | — |
| `decimation.py` | **La envolvente mínimo/máximo** que hace dibujable el registro entero sin perder un solo pico. Las cubetas se cuentan desde el comienzo del registro y no desde el borde de la página (hito 49), para que el visualizador pueda guardarlas y calcular sólo las que entran. | — |

## `Session`: el objeto que todos consultan

`Session` reúne todo lo que el usuario tiene abierto y configurado en un
momento dado: qué registro, qué scoring, qué anotaciones, en qué ventana está
parado, qué canales ve y con qué amplitud.

La interfaz **lo consulta para dibujarse** y **lo modifica** cuando el usuario
hace algo. Mantenerlo fuera de `ui/` es lo que hace testeables la navegación y
el manejo de amplitudes sin abrir una ventana.

Cuando agregues estado de trabajo nuevo, va acá, no en un widget.

**Cada clase de canal abre con su propia escala vertical**
(`DEFAULT_SCALE_BY_KIND_UV`, en `config.py`), y las que no tienen una de uso
corriente —Respiratorio, Otro— se miden sobre la primera época, **después de
centrarlas en su media** (hito 70): una temperatura de 37 °C se medía contra
el cero y se dibujaba pegada al borde de su carril. Una sola escala
para todos no puede servir: con los 100 µV de un EEG, un canal respiratorio se
sale de su carril y tapa seis canales.

**Se sustituye adentro, no se arma otra.** `set_scoring()` existe porque
importar un scoring (V3_F) no es abrir otro registro: el usuario sigue parado
en su ventana, con sus canales y sus amplitudes. Una `Session` nueva los
perdería, y además dejaría a las herramientas ya activadas apuntando a la
vieja —guardan la que recibieron en `activate()`—, así que el histograma
dibujaría el scoring anterior sin que nada fallara.

**`Session` sabe si hay trabajo sin exportar**, con
`has_unexported_scoring()` y `has_unexported_annotations()`: compara cada mitad
contra cómo estaba la última vez que quedó en un archivo —al abrir el registro,
al importar un scoring o al exportarlo, que es cuando la ventana llama a
`mark_scoring_exported()` o a `mark_annotations_exported()`—. Es lo que la
ventana pregunta antes de cerrar, de abrir otro registro o de importar un
scoring encima, y vive acá
porque decidir qué cuenta como trabajo es una regla: deshacer un cambio no
cuenta, y ni un scoring sin ninguna fase ni arousal ni un registro sin ninguna
anotación tienen algo que perder.

Las **anotaciones entraron al cerrarse el hito 33**, con las mismas reglas:
definir una clase de evento no es trabajo que se pierda —los exportadores
escriben anotaciones y no clases— y anotar algo y borrarlo tampoco.

**`Session` avisa sola cuando cambia de ventana**, por `add_window_listener()`.
Son callbacks y no señales de Qt, por el mismo motivo que en `tools/base.py`.
Quien navega no tiene que acordarse de avisarle a nadie: son tres las
herramientas que dependen de enterarse, y el olvido no fallaba de forma
visible.

## `windows.py`: el único lugar donde se convierten unidades de tiempo

El programa habla en varias unidades a la vez: el usuario piensa en **ventanas
de 30 segundos**, el archivo guarda **muestras** (los "puntos" del pliego), las
herramientas reciben **segundos desde el inicio del registro**, el medidor de
ocupación trabaja en **fracción de la página** y el histograma muestra la
**hora de la noche**.

Todas esas conversiones viven acá, para que no aparezcan cuentas de
`* 30 * fs` repartidas por el código. Si necesitás pasar de una unidad a otra,
llamá a este módulo en vez de escribir la cuenta.

**El reparto con `ui/signal_view.py` es exacto:** unidad ↔ unidad se hace acá;
píxel ↔ unidad se hace en el visualizador, que es lo único que conoce el ancho
de la pantalla. Por eso todo esto se testea sin abrir una ventana.

**Con una frecuencia de muestreo que no sea finita y positiva, las seis
funciones públicas que la reciben elevan `ZeroDivisionError`.** No validan
índices —quien llama ya lo hizo— pero una frecuencia corrupta sí se detiene
acá: devolver una ventana vacía en silencio esconde el archivo roto hasta mucho
después.

**Convención de índices:** las ventanas se numeran **desde 0 internamente** y
desde 1 al mostrarlas y al exportarlas. La conversión se hace al mostrar, no
en `core/`.

## Decisiones cerradas

**REM es fase de primera clase en las dos nomenclaturas.** El listado del
pliego no la menciona, pero el histograma sí la incluye, y R&K sin REM o AASM
sin R no son nomenclaturas válidas. Confirmado con el cliente: REM en
Rechtschaffen y Kales, R en AASM. `tests/test_nomenclature.py` lo verifica
explícitamente para que la omisión no se vuelva a colar.

**Un scoring nuevo arranca entero, con todas sus ventanas en `UNSCORED`.** Eso
es lo que permite que el histograma tenga el tamaño de la noche completa desde
el arranque y que se pueda scorear una parte alejada del registro sin pasar por
las anteriores.

**La última ventana incompleta se cuenta igual.** Si el registro no termina en
un múltiplo exacto de 30 segundos, el usuario tiene que poder scorearla o ver
que está incompleta.

## El índice de los "puntos"

Los "puntos" del pliego son muestras del registro, y **la primera es la 0**:
confirmado con el cliente el 4 de septiembre de 2026, por ser la base del
programa, de numpy y de MNE. Vive en `config.ANNOTATION_SAMPLE_BASE`, no en el
código de `windows.py` ni en el de los exportadores, para que revertirla sea
cambiar una línea. Ver el [hito 0 del TODO](../../docs/TODO.md#hito-0-desbloquear).

## Estado

Pendientes **0 stubs**: la carpeta está **terminada**, con los hitos 1, 2 y 3
del [TODO](../../docs/TODO.md) cerrados. Sus **ocho** módulos tienen su test
corriendo: los seis de aquellos hitos más `viewport.py` y `decimation.py`, que
llegaron con el refactor de la interfaz y que este párrafo no contaba.

**Toda esta capa funciona y se puede testear sin abrir una ventana**, que es el
pago concreto de que `core/` no importe `ui/`. Es el primer punto en que el
proyecto tiene valor real: desde acá, los hitos 4 y 5 pueden ir en paralelo con
el 6.
