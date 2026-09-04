# `docs/` — documentación del proyecto

| Archivo | Para qué sirve | Cuándo se toca |
|---|---|---|
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | **Decisiones de diseño y sus motivos.** Capas, puntos de extensión, licencias, convenciones de código. | Cada vez que se revisa una decisión: hay que anotar el motivo del cambio. |
| [`TRAZABILIDAD.md`](TRAZABILIDAD.md) | **Requisito del pliego → archivo responsable.** | Cada vez que se agrega una funcionalidad, **en el mismo commit**. |
| [`EXPLICACION.txt`](EXPLICACION.txt) | Explicación general del programa en texto plano, para quien no lee código. Su sección 8 lista lo que falta definir. | Cuando el cliente cierra una ambigüedad. |
| `mockups/` | Bocetos de la interfaz. | — |

## Por qué existe `ARQUITECTURA.md`

Guarda **los motivos**, no sólo las decisiones. Lo que se pierde con el tiempo
no es qué se decidió sino por qué, y sin el porqué cualquier decisión parece
arbitraria y se revierte sin querer. Ahí está explicado, por ejemplo, por qué no
se puede agregar PyQt, por qué las herramientas no heredan de `QObject` y por
qué la unidad es µV y no mV.

## Por qué existe `TRAZABILIDAD.md`

Responde dos preguntas: **dónde se implementa cada requisito** y, al revés,
**qué requisitos rompe un cambio en un archivo**. Es lo que hace verificable el
pedido del pliego (sección 7) de saber, ante un cambio, cuál archivo fue
cambiado.

Los identificadores se repiten entre secciones del pliego (hay varios `V1_F`),
así que **siempre se los nombra junto a su sección**.

Convención de sufijos, confirmada con el cliente:

- `_F` = versión **final**.
- `_P` = versión **parcial**, que va cambiando a lo largo del proyecto.

Un `_P` y su `_F` son **el mismo módulo en dos momentos distintos**, no dos
archivos: `signal_view.py` recorre V1_P → V5_F sin duplicarse.

La tabla se alimenta de la línea "Cubre del pliego:" del docstring de cada
módulo. Al agregar una funcionalidad, **agregá su fila acá en el mismo commit**.

## Ambigüedades abiertas

Están en `EXPLICACION.txt`, sección 8. Son los puntos del pliego que quedaron
sin cerrar y hay que confirmar con el cliente antes de programarlos:

1. `Scoring.txt`: ¿dos campos o tres? (Ya parametrizado en
   `config.SCORING_INCLUDES_WINDOW_NUMBER`.)
2. "Puntos": ¿la primera muestra es la 0 o la 1?
3. Impedancias: ¿de dónde salen, si el archivo no las trae?
4. Ocupación: si dos líneas se pisan, ¿la zona compartida se cuenta una o dos veces?
5. Titular del copyright para `LICENSE`, y nombre del repositorio.
6. Un registro de prueba en BrainVision y en EDF.

Cuando se cierre una, **actualizar `EXPLICACION.txt` y el módulo que la
esperaba** (los que dicen "PENDIENTE DE CONFIRMACIÓN" en su docstring).

## Documentación por carpeta

Cada paquete del código tiene su propio README con el mapa de archivos y las
reglas que lo gobiernan:

[`psglab/`](../psglab/README.md) ·
[`core/`](../psglab/core/README.md) ·
[`readers/`](../psglab/readers/README.md) ·
[`ui/`](../psglab/ui/README.md) ·
[`tools/`](../psglab/tools/README.md) ·
[`exporters/`](../psglab/exporters/README.md) ·
[`analysis/`](../psglab/analysis/README.md) ·
[`utils/`](../psglab/utils/README.md) ·
[`tests/`](../tests/README.md)
