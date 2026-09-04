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
| `SCORING_INCLUDES_WINDOW_NUMBER` | `False` | `Scoring.txt` lleva dos campos, como el ejemplo del pliego. |
| `ANNOTATION_SAMPLE_BASE` | `0` | Base de las muestras en `Anotaciones.txt`. |
| `OCCUPANCY_COUNTS_OVERLAP_ONCE` | `False` | La superposición de líneas se cuenta dos veces. |
| `SCORING_INCLUDES_NOMENCLATURE_HEADER` | `True` | `Scoring.txt` declara su nomenclatura en una cabecera. |
| `SCORING_HEADER_PREFIX` | `#` | Prefijo de esa cabecera. |

Las cinco últimas resuelven puntos que el pliego dejaba ambiguos y que se
cerraron con el cliente. Siguen siendo constantes, y no valores escritos a mano
en el módulo que los usa, por dos motivos: revertir una decisión es cambiar una
línea, y el valor queda junto al motivo por el que se eligió.

**No hardcodear ninguna de estas variantes** en ningún módulo. El detalle de
cada decisión está en el
[hito 0 del TODO](../docs/TODO.md#hito-0-desbloquear).

## Convenciones

- Identificadores y nombres de archivo en **inglés**; comentarios, docstrings y
  todo texto que ve el usuario, en **español**.
- **Cada módulo abre con un docstring** que dice de qué se ocupa y qué IDs del
  pliego cubre. Esa línea es la que alimenta [`docs/TRAZABILIDAD.md`](../docs/TRAZABILIDAD.md).
- Type hints en todas las firmas.
- Los errores que ve el usuario heredan de `PsgLabError`.
- **Todo el programa trabaja en microvoltios.**

## Estado

Esqueleto: los 42 módulos del paquete importan —50 archivos `.py` contando los
ocho `__init__.py`— pero la lógica todavía no está implementada y los métodos
elevan `NotImplementedError`.

Pendientes **170 stubs** en 29 módulos de la Parte 1, ordenados por
dependencias en el [TODO](../docs/TODO.md). `app.py` es el último de la fila
(hito 6): hasta que se implemente, `python main.py` termina en
`NotImplementedError`, que es lo esperado.

Estas piezas **sí** están implementadas, a propósito, y no deben volver a ser
stubs:

- Los decoradores `@register_tool` y `@register_reader`, y el resto de
  `tools/registry.py` (`available_tools`, `get_tool`, `load_all_tools`).
- `Reader.can_read` y el despacho de `read_recording()`.
- `PsgLabError.__init__`.
- Los métodos de evento de `Tool` y `ViewerTool`, que no hacen nada por defecto
  en vez de elevar: si el método base fallara, activar una herramienta y navegar
  rompería el programa.
- `config.py` entero: sus constantes ya están fijadas.
- `core/windows.py` entero, único módulo de la Parte 1 terminado.

Las primeras corren en tiempo de importación; si elevaran `NotImplementedError`,
ningún módulo del paquete podría cargarse y los mecanismos enchufables no
existirían.
