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
| `recording.py` | El registro cargado en memoria: `Recording`, `Channel`, `ChannelKind`. | Soporte de V1_F–V3_F de "Importación", V4_F de "Visualización" |
| `session.py` | Estado de trabajo del usuario. **Es el objeto central.** | V1_F de "Navegación"; V2_P, V3_P, V5_F de "Visualización"; V4_F del histograma |
| `scoring.py` | Fase y arousal de cada ventana: `Scoring`, `EpochScore`. | V1_F, V2_F, V3_F de "Scoring" |
| `nomenclature.py` | Rechtschaffen y Kales frente a AASM: `Nomenclature`, `SleepStage`, conversión entre ambas. | V1_F, V3_F de "Scoring"; V3_F del histograma |
| `annotations.py` | Eventos anotados sobre la señal: `Annotation`, `AnnotationSet`. | V1_F de "Anotación de la señal" |
| `windows.py` | Conversión entre ventanas, muestras y hora de la noche. | V1_P de "Visualización", V1_F de "Navegación", V2_F del histograma |

## `Session`: el objeto que todos consultan

`Session` reúne todo lo que el usuario tiene abierto y configurado en un
momento dado: qué registro, qué scoring, qué anotaciones, en qué ventana está
parado, qué canales ve y con qué amplitud.

La interfaz **lo consulta para dibujarse** y **lo modifica** cuando el usuario
hace algo. Mantenerlo fuera de `ui/` es lo que hace testeables la navegación y
el manejo de amplitudes sin abrir una ventana.

Cuando agregues estado de trabajo nuevo, va acá, no en un widget.

## `windows.py`: el único lugar donde se convierten unidades de tiempo

El programa habla en varias unidades a la vez: el usuario piensa en **ventanas
de 30 segundos**, el archivo guarda **muestras** (los "puntos" del pliego), las
herramientas reciben **segundos** desde el inicio de la ventana, el medidor de
ocupación trabaja en **fracción de ventana** y el histograma muestra la **hora
de la noche**.

Todas esas conversiones viven acá, para que no aparezcan cuentas de
`* 30 * fs` repartidas por el código. Si necesitás pasar de una unidad a otra,
llamá a este módulo en vez de escribir la cuenta.

**El reparto con `ui/signal_view.py` es exacto:** unidad ↔ unidad se hace acá;
píxel ↔ unidad se hace en el visualizador, que es lo único que conoce el ancho
de la pantalla. Por eso todo esto se testea sin abrir una ventana.

**Con una frecuencia de muestreo que no sea positiva, las cinco funciones que
la reciben elevan `ZeroDivisionError`.** No validan índices —quien llama ya lo
hizo— pero una frecuencia corrupta sí se detiene acá: devolver una ventana
vacía en silencio esconde el archivo roto hasta mucho después.

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

Pendientes **19 stubs**, todos en `session.py`, el hito 3 del
[TODO](../../docs/TODO.md):

| Hito | Módulos |
|---|---|
| [1. Cimientos](../../docs/TODO.md#hito-1-cimientos) | ~~`windows`~~ ✅, ~~`nomenclature`~~ ✅, ~~`recording`~~ ✅ |
| [2. Scoring y anotaciones](../../docs/TODO.md#hito-2-scoring-y-anotaciones) | ~~`scoring`~~ ✅, ~~`annotations`~~ ✅ |
| [3. Sesión](../../docs/TODO.md#hito-3-sesión) | `session` |

**Cerrado el hito 3, toda esta capa funciona y se puede testear sin abrir una
ventana.** Es el primer punto en que el proyecto tiene valor real.
