# `docs/` — documentación del proyecto

| Archivo | Para qué sirve | Cuándo se toca |
|---|---|---|
| [`TODO.md`](TODO.md) | **La cola de trabajo.** Lo abierto, las preguntas al cliente, cómo se trabaja y la tabla de progreso de todos los hitos, ordenados por dependencias. Es el único lugar que lleva estado, y el único que dice cuántos hitos hay. | Al empezar y al cerrar cada módulo. |
| [`HISTORIAL.md`](HISTORIAL.md) | **Los hitos cerrados**, cada uno con lo que se hizo, lo que se decidió y lo que se midió. No lleva estado: sus cuentas de tests son las de cuando se cerró cada hito. Se separó del TODO en el hito 79. | Al cerrar un hito, que se muda acá entero. |
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | **Decisiones de diseño y sus motivos.** Capas, puntos de extensión, licencias, convenciones de código. | Cada vez que se revisa una decisión: hay que anotar el motivo del cambio. |
| [`TRAZABILIDAD.md`](TRAZABILIDAD.md) | **Requisito del pliego → archivo responsable.** | Cada vez que se agrega una funcionalidad, **en el mismo commit**. |
| [`EXPLICACION.txt`](EXPLICACION.txt) | Explicación general del programa en texto plano, para quien no lee código. Su sección 8 lista lo que falta definir. | Cuando el cliente cierra una ambigüedad. |
| `mockups/` | Bocetos de la interfaz. | — |

**Las auditorías no tienen archivo acá.** Las dos primeras —la del 4 de
septiembre de 2026 y la del cierre de la Parte 1, el 7— fueron fotos fechadas
en esta carpeta hasta que el usuario las borró el 19 de septiembre, dándolas
por resueltas; siguen en el historial de git. Las del 8 y el 19 de septiembre
nunca lo tuvieron: sus hallazgos viven en los hitos del TODO que los atienden,
del 19 al 21 y el 33.

## Por qué existe `ARQUITECTURA.md`

Guarda **los motivos**, no sólo las decisiones. Lo que se pierde con el tiempo
no es qué se decidió sino por qué, y sin el porqué cualquier decisión parece
arbitraria y se revierte sin querer. Ahí está explicado, por ejemplo, por qué no
se puede agregar PyQt, por qué las herramientas no heredan de `QObject` y por
qué la unidad es µV y no mV.

## Por qué el estado vive sólo en `TODO.md`

`TRAZABILIDAD.md` dice **dónde** va cada requisito; `TODO.md` dice **qué falta
y en qué orden**. Son preguntas distintas y la segunda cambia todas las
semanas.

Por eso `TRAZABILIDAD.md` **no lleva columna de estado**: si el avance se
anotara en los dos lugares, se desincronizarían, y no habría forma de saber
cuál miente.

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

## Ambigüedades del pliego

**Las que estaban abiertas se cerraron el 4 de septiembre de 2026**, con el
cliente. La lista de qué se preguntó, qué se respondió y en qué constante vive
cada respuesta está en el [hito 0 del TODO](HISTORIAL.md#hito-0-desbloquear); el
resumen para el lector no técnico, en `EXPLICACION.txt`, sección 8.

**No se listan acá.** Una copia más de esa lista es una copia más para
desincronizar, y ya pasó: al cerrarse el hito 0, siete README de carpeta
siguieron pidiendo confirmar lo que el cliente ya había confirmado. Lo encontró
la primera auditoría, y volvió a pasar al cerrarse la Parte 1: lo encontró la
segunda.

Queda **una sola** genuinamente abierta, y es de la Parte 2: de dónde salen las
impedancias de los electrodos, si el archivo no las trae. El módulo que la
espera la declara en su docstring con la marca `PENDIENTE DE DEFINICIÓN CON EL
CLIENTE`, que se encuentra así:

```bash
grep -rn "PENDIENTE DE" psglab --include=*.py
```

Cuando se cierre, **actualizar `EXPLICACION.txt` y borrar la marca del módulo**.

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

El estado de cada una está en su bloque "Estado", que remite al hito
correspondiente del [TODO](TODO.md).
