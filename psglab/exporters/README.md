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
[`psglab/config.py`](../README.md).

## `Scoring.txt`

Una línea por ventana, en orden, desde la primera hasta la última del registro:

```
2 0     ->  fase 2, sin arousal
2 1     ->  fase 2, con arousal
```

**Ambigüedad abierta.** El pliego describe tres campos por línea (número de
ventana, fase, arousal) pero su ejemplo muestra sólo dos. Mientras no se
confirme, el número de ventana queda implícito en el orden de las líneas, como
en el ejemplo, y el formato está parametrizado en
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

"Puntos" son **muestras del registro, no segundos**. Guardarlo así evita perder
precisión por redondeo y no depende de la frecuencia de muestreo del archivo.

**Ambigüedades abiertas:** si el índice de la primera muestra es 0 o 1, y si
conviene escribir la frecuencia de muestreo en una cabecera para que el archivo
se pueda interpretar sin tener el registro al lado.

## `Informacion.txt`

Resumen legible del registro y de lo que se hizo sobre él: nombre del archivo,
duración total en horas y en puntos, duración en cada fase, métricas de tiempo
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

Pendientes **13 stubs**, en el
[hito 5 del TODO](../../docs/TODO.md#hito-5-exportadores).

`annotations_txt.py` está bloqueado por el
[hito 0](../../docs/TODO.md#hito-0-desbloquear): falta definir si la primera
muestra es la 0 o la 1.

**Cerrado este hito el programa hace su trabajo completo desde un script
—leer, scorear, exportar los tres archivos— sin interfaz gráfica.**
