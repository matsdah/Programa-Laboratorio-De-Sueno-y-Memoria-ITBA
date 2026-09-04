# `psglab/` — el paquete del programa

Todo el código vive acá. `main.py`, en la raíz del repositorio, sólo crea la
aplicación y abre la ventana: no contiene lógica.

## Las capas y hacia dónde apuntan

```
utils  ←  no depende de nadie
  ↑
core   ←  modelo y reglas de negocio
  ↑
  ├── readers     importar archivos
  ├── tools       herramientas del visualizador
  ├── exporters   archivos de salida
  ├── analysis    Parte 2: procesamiento y métricas
  └── ui          interfaz gráfica (además depende de tools)
```

**`core/` no importa nada de `ui/`.** Es la restricción que sostiene todo lo
demás: gracias a ella el modelo, el scoring, las estadísticas y los
exportadores se pueden testear sin abrir una ventana, que es el testeo
recurrente que pide el pliego (sección 11).

Regla de bolsillo para ubicar código nuevo: **si es una regla de negocio y
quedó en `ui/`, está mal ubicada.** Mostrar la ventana 0 como "Ventana 1" es
presentación y va en `ui/`. Impedir que se scoree la ventana 500 de un registro
de 400 ventanas es una regla y va en `core/`.

## Mapa de carpetas

| Carpeta | Responsabilidad | Documentación |
|---|---|---|
| [`core/`](core/README.md) | Modelo de datos y reglas de negocio. Sin GUI. | [core/README.md](core/README.md) |
| [`readers/`](readers/README.md) | Importar BrainVision, EDF y scoring existente. | [readers/README.md](readers/README.md) |
| [`ui/`](ui/README.md) | Visualizador, navegación, panel de scoring, ventana principal. | [ui/README.md](ui/README.md) |
| [`tools/`](tools/README.md) | Herramientas enchufables: lupa, amplitud, ocupación, anotador, Übersicht, histograma. | [tools/README.md](tools/README.md) |
| [`exporters/`](exporters/README.md) | Los tres archivos de salida y las estadísticas que los alimentan. | [exporters/README.md](exporters/README.md) |
| [`analysis/`](analysis/README.md) | Parte 2: filtrado, ICA, impedancia, PSD, complejidad, conectividad. | [analysis/README.md](analysis/README.md) |
| [`utils/`](utils/README.md) | Unidades (µV) y errores propios. | [utils/README.md](utils/README.md) |

## Los dos archivos sueltos del paquete

### `app.py`

Lo único que `main.py` conoce. Arma los objetos de Qt y los devuelve cableados:
`create_application(argv)` y `create_main_window()`. Mantener la construcción
acá es lo que permite que el punto de entrada se quede en veinte líneas
(requisito del pliego, sección 7).

### `config.py`

**Punto único de verdad de las constantes del pliego.** Ningún otro módulo
debería escribir estos números a mano; si mañana el laboratorio quiere ventanas
de 20 segundos, se cambia acá y en ningún otro lado.

| Constante | Valor | De dónde sale |
|---|---|---|
| `WINDOW_SECONDS` | 30,0 | Duración de la ventana de scoring. |
| `COARSE_GRID_SECONDS` / `FINE_GRID_SECONDS` | 3,0 / 0,5 | Grilla de fondo del visualizador. |
| `AMPLITUDE_BAND_UV` | 75,0 | Banda de referencia de la herramienta de amplitud. |
| `DEFAULT_SCALE_UV`, `MIN_SCALE_UV`, `MAX_SCALE_UV` | 100 / 1 / 10 000 | Escala vertical y sus topes. |
| `AMPLITUDE_STEP_FACTOR` | 1,25 | Cuánto cambia la amplitud por pulsación de flecha. |
| `SCORING_FILENAME` y compañía | `Scoring.txt`, … | Nombres de los archivos de salida. |
| `SCORING_INCLUDES_WINDOW_NUMBER` | `False` | **Ambigüedad abierta del pliego**, ver abajo. |

`SCORING_INCLUDES_WINDOW_NUMBER` existe porque el pliego describe tres campos
por línea en `Scoring.txt` pero su ejemplo muestra dos. Mientras el cliente no
confirme, las dos variantes tienen que seguir siendo alcanzables cambiando esa
sola constante: **no hardcodear ninguna de las dos.**

## Estado actual

Esqueleto: la estructura está completa y los 49 módulos importan, pero la
lógica todavía no está implementada y los métodos elevan `NotImplementedError`.

Cuatro piezas **sí** están implementadas, a propósito, y no deben volver a ser
stubs: los decoradores `@register_tool` y `@register_reader`, `Reader.can_read`,
`read_recording()` y `PsgLabError.__init__`. Todas corren en tiempo de
importación; si elevaran `NotImplementedError`, ningún módulo del paquete podría
cargarse y los mecanismos enchufables no existirían.

## Convenciones

- Identificadores y nombres de archivo en **inglés**; comentarios, docstrings y
  todo texto que ve el usuario, en **español**.
- **Cada módulo abre con un docstring** que dice de qué se ocupa y qué IDs del
  pliego cubre. Esa línea es la que alimenta [`docs/TRAZABILIDAD.md`](../docs/TRAZABILIDAD.md).
- Type hints en todas las firmas.
- Los errores que ve el usuario heredan de `PsgLabError`.
- **Todo el programa trabaja en microvoltios.**

## Estado

Pendientes **173 stubs** en 30 módulos de la Parte 1, ordenados por
dependencias en el [TODO](../docs/TODO.md). `app.py` es el último de la fila
(hito 6): hasta que se implemente, `python main.py` termina en
`NotImplementedError`, que es lo esperado.

`config.py` no tiene stubs: sus constantes ya están fijadas.
