# `exporters/` — archivos de salida

Tres archivos de texto, uno por módulo, más las estadísticas que alimentan al
tercero. El usuario elige cuál exportar (V4_F).

**Los formatos son texto plano y fáciles de leer con cualquier herramienta, y
eso es deliberado:** los archivos de salida son la vía por la que el scoring
entra a los análisis estadísticos del laboratorio, y no deberían necesitar este
programa para poder leerse.

## Los archivos

| Archivo | Genera | Pliego |
|---|---|---|
| `scoring_txt.py` | `Scoring.txt` | V1_F de "Archivo de salida" |
| `annotations_txt.py` | `Anotaciones.txt` | V2_F de "Archivo de salida" |
| `information_txt.py` | `Informacion.txt` | V3_F de "Archivo de salida" |
| `statistics.py` | Los números que usa `Informacion.txt`. No escribe archivos. | Alimenta V3_F |

Los nombres propuestos en el diálogo de guardado salen de `DEFAULT_FILENAMES`,
en el `__init__.py` del paquete, que a su vez los toma de
[`psglab/config.py`](../config.py).

## `Scoring.txt`

Una cabecera con la nomenclatura y después una línea por ventana, en orden:

```
# AASM  ->  nomenclatura con la que se scoreó
2 0     ->  fase 2, sin arousal
2 1     ->  fase 2, con arousal
-1 0    ->  ventana todavía sin scorear
```

La cabecera existe porque **el archivo no es interpretable sin ella**: "2" es S2
en Rechtschaffen y Kales y N2 en AASM. Registrar la nomenclatura sólo en
`Informacion.txt` no alcanzaba, porque V4_F deja exportar **uno solo** de los
tres archivos.

**Dos campos, no tres.** El pliego describe tres por línea (número de ventana,
fase, arousal) pero su ejemplo muestra sólo dos, y el cliente confirmó el 4 de
septiembre de 2026 que **vale el ejemplo**: el número de ventana queda implícito
en el orden de las líneas. El formato sigue parametrizado en
`config.SCORING_INCLUDES_WINDOW_NUMBER` (hoy `False`).

**Cambiar esa sola constante tiene que alcanzar para pasar a la otra variante:
no hardcodear ninguna de las dos.**

## `Anotaciones.txt`

Una línea por anotación, tres campos separados por barra vertical:

```
Label_Annotation | Puntos_Emp | Duracion_Puntos
```

Las anotaciones se escriben **ordenadas por muestra de inicio**, no por orden de
creación.

"Puntos" son **muestras del registro, no segundos**, y la primera es la **0**
(`config.ANNOTATION_SAMPLE_BASE`). Guardarlo así evita perder precisión por
redondeo.

**El archivo no se interpreta solo**, y se aceptó a propósito: para convertir
esas muestras a tiempo hace falta la frecuencia de muestreo, que vive en
`Informacion.txt`. Se decidió no repetirla en una cabecera acá porque **falla
distinto** que el caso de la nomenclatura: una fase mal interpretada pasa
desapercibida, mientras que una posición sin frecuencia directamente no se puede
convertir y el problema salta enseguida. Ver el
[hito 0 del TODO](../../docs/TODO.md#hito-0-desbloquear).

## `Informacion.txt`

Resumen legible del registro y de lo que se hizo sobre él: nombre del archivo,
duración del registro en horas y en puntos, tiempo scoreado, duración en cada
fase, métricas de tiempo
por fase (promedio, desvío estándar y mediana) y lista de anotaciones con
cantidad y tiempo promedio.

**Las secciones que no correspondan se omiten con una explicación en vez de
mostrar ceros.** Un archivo que dice "el registro no está scoreado" es más útil
que uno lleno de "0,00 s", que se puede confundir con un registro scoreado sin
ninguna ventana en esa fase.

## `statistics.py` no escribe archivos

Calcula: cantidad de ventanas y duración por fase, episodios de cada fase y sus
métricas, resumen de anotaciones y tiempo total de registro. Separarlo del
exportador es lo que permite **testear los números sin escribir en disco** y
reutilizarlos si mañana hacen falta en pantalla o en un análisis.

## Testeo

Esta capa corre sin interfaz gráfica, así que se testea de punta a punta:

```bash
python -m pytest tests/test_exporters.py
```

## Estado

Pendientes **14 stubs**, en el
[hito 5 del TODO](../../docs/TODO.md#hito-5-exportadores).

**Ninguno está bloqueado.** `annotations_txt.py` lo estuvo hasta que el
[hito 0](../../docs/TODO.md#hito-0-desbloquear) fijó el índice de la primera
muestra en 0.

**Cerrado este hito el programa hace su trabajo completo desde un script
—leer, scorear, exportar los tres archivos— sin interfaz gráfica.**
