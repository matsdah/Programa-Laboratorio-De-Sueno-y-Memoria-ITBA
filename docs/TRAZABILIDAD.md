# Trazabilidad: requisito del pliego → archivo responsable

Esta tabla responde dos preguntas: **dónde se implementa cada requisito** y,
al revés, **qué requisitos rompe un cambio en un archivo**. Es lo que hace
verificable el pedido del pliego (sección 7) de "en caso de cambio saber cuál
archivo fue cambiado".

Los identificadores se repiten entre secciones del pliego (hay varios `V1_F`),
así que siempre se los nombra junto a su sección.

**Convención de sufijos**, confirmada con el cliente:
`_F` = versión **final**. `_P` = versión **parcial**, que va cambiando a lo
largo del proyecto. Un `_P` y su `_F` son el mismo módulo en dos momentos
distintos, no dos archivos: `signal_view.py` recorre V1_P → V5_F sin
duplicarse.

Cuando se agregue una funcionalidad, **agregar acá su fila** en el mismo
commit.

---

## Parte 1 — Scorer de polisomnografía

### Importación de archivos

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Importar BrainVision (VHDR/VMRK/EEG) | `psglab/readers/brainvision.py`, `psglab/readers/base.py` (despacho), `psglab/core/recording.py` (modelo) |
| V2_F | Importar `.edf` | `psglab/readers/edf.py`, `psglab/readers/base.py` (despacho), `psglab/core/recording.py` (modelo) |
| V3_F | Importar señal ya escorada y ver la fase de cada ventana | `psglab/readers/scoring_reader.py`, `psglab/core/scoring.py`, `psglab/core/recording.py` (cantidad de ventanas) |

### Visualización de la señal

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_P | Ventana de 30 s con ojos, C3, C4 y EMG; nº de ventana y total; nombres; escala en µV | `psglab/ui/signal_view.py`, `psglab/ui/navigation.py` (nº de ventana), `psglab/core/windows.py` (cuenta de ventanas), `psglab/utils/units.py` (µV) |
| V2_P | Aumentar la amplitud con flechas y con botón; escala adaptada | `psglab/ui/signal_view.py`, `psglab/core/session.py`, `psglab/ui/shortcuts.py` (flechas) |
| V3_P | Elegir cuántos y cuáles canales visualizar | `psglab/ui/channel_selector.py` (elección), `psglab/ui/signal_view.py` (dibujo), `psglab/core/session.py` (estado) |
| V4_F | Cualquier canal sin límite de tipo, con detección automática de clase | `psglab/readers/channel_types.py`, `psglab/ui/signal_view.py`, `psglab/ui/channel_selector.py`, `psglab/core/recording.py` (`ChannelKind`) |
| V5_F | Amplitud de todos los canales, o sólo de los seleccionados | `psglab/core/session.py`, `psglab/ui/signal_view.py`, `psglab/ui/channel_selector.py` (selección), `psglab/ui/shortcuts.py` (flechas) |

### Navegación en la señal

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Avanzar y retroceder con flechas ←→ y con botones | `psglab/ui/navigation.py`, `psglab/ui/shortcuts.py`, `psglab/core/session.py`, `psglab/core/windows.py` |

### Diseño de la interfaz de visualización

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_P | Línea discreta cada 0,5 s y línea visible cada 3 s | `psglab/ui/grid.py` |
| V2_F | Elegir entre los tres fondos | `psglab/ui/grid.py` |

### Scoring de la señal

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Elegir la fase de la ventana de 30 s | `psglab/core/scoring.py`, `psglab/ui/scoring_panel.py`, `psglab/core/nomenclature.py` (vocabulario), `psglab/ui/shortcuts.py` (teclas) |
| V2_F | Indicar la presencia de un arousal | `psglab/core/scoring.py`, `psglab/ui/scoring_panel.py`, `psglab/ui/shortcuts.py` (tecla A) |
| V3_F | Elegir entre Rechtschaffen y Kales y AASM | `psglab/core/nomenclature.py`, `psglab/ui/scoring_panel.py`, `psglab/core/scoring.py` (`change_nomenclature`) |

### Herramienta de amplitud

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Banda de 75 µV adaptada a la escala del usuario | `psglab/tools/amplitude_band.py`, `psglab/utils/units.py` (µV) |

### Herramienta de ocupación de la página

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Dibujar una línea con el mouse | `psglab/tools/occupancy.py` |
| V2_F | Calcular el porcentaje de ocupación horizontal | `psglab/tools/occupancy.py` |
| V3_F | Mostrar el porcentaje | `psglab/tools/occupancy.py` |
| V4_F | Sumar la distancia horizontal de varias líneas | `psglab/tools/occupancy.py` |
| V5_F | Borrar una línea con clic o al cambiar de ventana | `psglab/tools/occupancy.py` |

### Histograma

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_P | Histograma de la noche completa, con lo no anotado en blanco | `psglab/tools/histogram.py` |
| V2_F | Eje horizontal en hora real o de 1 a VENMAX | `psglab/tools/histogram.py`, `psglab/core/windows.py` |
| V3_F | Adaptar el histograma a la nomenclatura elegida | `psglab/tools/histogram.py`, `psglab/core/nomenclature.py` |
| V4_F | Clic en el histograma para ir a esa ventana | `psglab/tools/histogram.py`, `psglab/core/session.py` |

### Herramienta Lupa

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Círculo de zoom que sigue al mouse | `psglab/tools/magnifier.py` |
| V2_F | Contador de clics para contar picos | `psglab/tools/magnifier.py` |

### Herramienta Übersicht

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Ventana anterior, actual y siguiente, con la actual más oscura | `psglab/tools/overview.py` |
| V2_F | Agrandar el panel con el mouse | `psglab/tools/overview.py` |
| V3_F | Cantidad configurable y asimétrica de ventanas vecinas | `psglab/tools/overview.py` |

### Anotación de la señal

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | Seleccionar un evento, asignarle o crear una clase, marcarlo con una banda | `psglab/tools/annotator.py`, `psglab/core/annotations.py`, `psglab/ui/signal_view.py` (`sample_at`) |

### Archivo de salida

| ID | Requisito | Archivo |
|----|-----------|---------|
| V1_F | `Scoring.txt` | `psglab/exporters/scoring_txt.py`, `psglab/core/nomenclature.py` (`STAGE_CODES`) |
| V2_F | `Anotaciones.txt` | `psglab/exporters/annotations_txt.py`, `psglab/core/annotations.py` |
| V3_F | `Informacion.txt` | `psglab/exporters/information_txt.py`, `psglab/exporters/statistics.py` |
| V4_F | Elegir cuál de los tres exportar | `psglab/ui/main_window.py` |

---

## Parte 2 — Módulo de análisis

| Sección | ID | Requisito | Archivo |
|---------|----|-----------|---------|
| Filtración | V1_F | Importar señal cruda y filtrar por tipo de canal | `psglab/analysis/filters.py` |
| Filtración | V5_F | Análisis de componentes independientes | `psglab/analysis/ica.py` |
| Impedancia | V1_F | Límite por canal y alerta al superarlo | `psglab/analysis/impedance.py` |
| Rereferenciar | — | Re-referenciar la señal | `psglab/analysis/reference.py` |
| Derivar | — | Derivar la señal | `psglab/analysis/derivation.py` |
| PSD | V1_F | PSD por banda de frecuencia elegida | `psglab/analysis/psd.py` |
| Complejidad | — | Complejidad de la señal | `psglab/analysis/complexity.py` |
| Conectividad | — | Conectividad de la señal | `psglab/analysis/connectivity.py` |

---

## Módulos de infraestructura

No implementan ninguna funcionalidad numerada, así que no tienen fila arriba.
Se listan igual porque la tabla también sirve para la pregunta inversa: **qué se
rompe si se toca este archivo**. Estos cinco se rompen hacia todos lados.

| Archivo | De qué se ocupa | Qué se ve afectado si cambia |
|---|---|---|
| `psglab/config.py` | Constantes del pliego (30 s, grilla, 75 µV, nombres de salida) | Todo lo que dependa de esos valores |
| `psglab/core/recording.py` | Modelo del registro en memoria | Toda la Parte 1 y toda la Parte 2 |
| `psglab/utils/units.py` | Conversión a microvoltios | Cualquier requisito que hable de amplitud |
| `psglab/utils/errors.py` | Excepciones con mensaje para el investigador | Todo mensaje de error que ve el usuario |
| `psglab/tools/base.py` | Los contratos `Tool` y `ViewerTool`, y el sistema de coordenadas | Las seis herramientas |
| `psglab/tools/registry.py` | Registro enchufable de herramientas | La barra de herramientas entera |
| `psglab/app.py` | Construcción de la aplicación y la ventana | El arranque del programa |

---

## Requisitos técnicos (sección 7 del pliego)

| Requisito | Dónde se cumple |
|-----------|-----------------|
| Python con interfaz visual | Todo el proyecto; interfaz en `psglab/ui/` |
| `main.py` lo más simple posible | `main.py` (9 sentencias: crea la app, abre la ventana y sale) |
| Archivos `.py` separados por funcionalidad | Estructura de `psglab/`, documentada en esta tabla |
| Código completamente comentado | Docstring de responsabilidad en cada módulo y función |
| Archivo de texto explicativo de soporte | `docs/EXPLICACION.txt` |
| Escalabilidad | `psglab/tools/registry.py` y `psglab/tools/base.py`; `psglab/readers/base.py` |
| Multiplataforma | PySide6 y MNE funcionan en Windows, macOS y Linux |
| Licencia MIT | `LICENSE`; ver la nota sobre PyQt en `docs/ARQUITECTURA.md` |
| Branch `Add`, PRs comentadas | `README.md`, sección "Cómo contribuir" |
| Testeos recurrentes por componente | `tests/` |

---

## Funcionalidades futuras

Confirmadas con el cliente como fuera del alcance actual. Todavía no tienen
archivo; cuando se retomen, entran como módulos nuevos en `psglab/analysis/`.

- Detección de potencial evocado
- Acoplamiento de husos de sueño

---

## Puntos del pliego pendientes de definición

La lista vive en **[`TODO.md`](TODO.md#hito-0-desbloquear)**, hito 0, con el
detalle de qué trabajo frena cada una. Acá no se repite: el estado y las
preguntas abiertas los posee el TODO, y duplicarlos garantizaba —y de hecho
produjo— que las copias se desincronizaran.

Las que ya afectan a un archivo concreto están anotadas además en el docstring
de ese archivo, con la marca `PENDIENTE DE CONFIRMACIÓN`:

```bash
grep -rn "PENDIENTE DE" psglab --include=*.py
```
