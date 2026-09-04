# TODO — Parte 1 (scorer de polisomnografía)

La cola de trabajo del proyecto. **Este archivo es el único lugar que dice qué
está hecho y qué falta**; `TRAZABILIDAD.md` dice *dónde* va cada requisito y no
lleva estado, para que no haya dos fuentes que se desincronicen.

Quedan **168 stubs** (`raise NotImplementedError`) en 29 módulos de la Parte 1.
Los 26 stubs de `psglab/analysis/` son de la Parte 2 y no entran acá.

## Cómo se usa

Los hitos están **ordenados por dependencias reales**, sacadas del grafo de
importaciones del paquete. No es el orden de `TRAZABILIDAD.md`, que sigue las
secciones del pliego: quien lo lea de arriba abajo arrancaría por
`readers/brainvision.py`, que necesita `core/recording.py` terminado para poder
devolver algo.

**No empieces un módulo si el hito anterior no está cerrado.** Vas a escribir
contra firmas que todavía elevan `NotImplementedError` y no vas a poder testear
nada.

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

| Hito | Módulos | Stubs | Estado |
|---|---|---|---|
| [0. Desbloquear](#hito-0-desbloquear) | — | 0 | ⬜ |
| [1. Cimientos](#hito-1-cimientos) | 4 | 16 | 🟡 1 de 4 |
| [2. Scoring y anotaciones](#hito-2-scoring-y-anotaciones) | 2 | 20 | ⬜ |
| [3. Sesión](#hito-3-sesión) | 1 | 19 | ⬜ |
| [4. Importación](#hito-4-importación) | 5 | 8 | ⬜ |
| [5. Exportadores](#hito-5-exportadores) | 4 | 13 | ⬜ |
| [6. Interfaz](#hito-6-interfaz) | 8 | 45 | ⬜ |
| [7. Herramientas](#hito-7-herramientas) | 6 | 47 | ⬜ |
| [8. Cierre](#hito-8-cierre-de-la-parte-1) | — | 0 | ⬜ |
| | **29** | **168** | |

### Los tres cortes que importan

- **Al cerrar el hito 3** toda la capa de negocio funciona y se puede testear
  sin abrir una ventana.
- **Al cerrar el hito 5** el programa hace su trabajo completo desde un script
  —leer un EDF, scorear, exportar los tres archivos— **todavía sin interfaz
  gráfica**. Es el pago concreto de que `core/` no importe `ui/`.
- **Al cerrar el hito 6** `python main.py` abre algo usable por primera vez.

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
| ¿Cómo se sabe con qué nomenclatura se generó un `Scoring.txt`? | **Se registra en `Informacion.txt`.** No se agrega cabecera a `Scoring.txt`, para no apartarse del pliego. | `exporters/information_txt.py` |
| ¿El scoring automático entra en el alcance? | **No.** Queda como funcionalidad futura, junto al potencial evocado y el acoplamiento de husos. | `TRAZABILIDAD.md` |
| Titular del copyright | **Confirmado** tal como está: Laboratorio de Sueño y Memoria, ITBA. | `LICENSE` |

La decisión de la nomenclatura tiene una consecuencia que conviene no perder de
vista: **los tres archivos de salida sólo son interpretables juntos.**
`Scoring.txt` escribe la fase como un número que significa cosas distintas según
la nomenclatura, y `Anotaciones.txt` guarda posiciones en muestras que no se
pasan a segundos sin la frecuencia. Los dos datos viven en `Informacion.txt`.

### Material de prueba

- [x] **EDF** — [Sleep-EDF Database Expanded](https://physionet.org/content/sleep-edfx/1.0.0/)
  de PhysioNet, bajo [ODC-By v1.0](https://www.physionet.org/content/sleep-edfx/view-license/1.0.0/).
  Registro real de noche completa: 7 canales, 100 Hz, 22 h, con hipnograma
  scoreado en Rechtschaffen y Kales.
- [x] **BrainVision** — los archivos de prueba de
  [MNE-Python](https://github.com/mne-tools/mne-python/tree/main/mne/io/brainvision/tests/data)
  (BSD-3): tripleta `.vhdr` + `.vmrk` + `.eeg`, 32 canales con nombres 10-20,
  1000 Hz. **Son 7,9 segundos, no una noche**: sirven para verificar que el
  lector entiende el formato, no para probar el programa de punta a punta.
  Conseguir un registro real del laboratorio sigue siendo deseable.

Los dos viven en `data/`, que **el `.gitignore` excluye**: no van al
repositorio.

### Sigue abierta

- [ ] **Origen de las impedancias** (cabecera del archivo, archivo aparte o
  carga manual). Es de la **Parte 2**, así que no frena nada de este TODO.
  Ver `analysis/impedance.py`.

---

## Hito 1: Cimientos

Los cuatro módulos que **no importan nada interno**. Se pueden hacer en
cualquier orden, incluso en paralelo.

- [ ] **`psglab/utils/units.py`** · 4 stubs · sostiene la escala en µV de V1_P
      "Visualización" y la banda de V1_F "Herramienta de amplitud"
  - Test: **crear** `tests/test_units.py`. Casos mínimos: `V`→µV es ×10⁶,
    `mV`→µV es ×10³, y una unidad desconocida eleva `UnknownUnitError` en vez
    de asumir un factor.
- [x] **`psglab/core/windows.py`** · ~~5 stubs~~ · sostiene V1_P "Visualización"
      (nº de ventana y total), V1_F "Navegación", V2_F "Histograma"
  - Test: `tests/test_windows.py`, **15 tests en verde**.
  - Los bordes se calculan desde el índice de la ventana, nunca acumulando un
    paso redondeado: con una frecuencia no redonda (256,125 Hz en EDF) acumular
    corre la ventana 960 casi tres segundos. Hay tres tests que lo fijan.
- [ ] **`psglab/core/nomenclature.py`** · 5 stubs · V3_F "Scoring",
      V3_F "Histograma"
  - Test: `tests/test_nomenclature.py` → **borrar el `pytestmark`**.
  - REM va en las dos nomenclaturas. El test ya lo verifica: no lo toques.
- [ ] **`psglab/core/recording.py`** · 7 stubs · soporte de V1_F/V2_F/V3_F
      "Importación" y V4_F "Visualización"
  - Test: **crear** `tests/test_recording.py`, con la fixture
    `synthetic_signal` de `conftest.py`.

---

## Hito 2: Scoring y anotaciones

- [ ] **`psglab/core/scoring.py`** · 10 stubs · V1_F, V2_F, V3_F "Scoring"
  - Test: `tests/test_scoring.py` → **borrar el `pytestmark`**.
  - Un scoring nuevo arranca entero en `UNSCORED`: el histograma tiene el
    tamaño de la noche desde el principio.
- [ ] **`psglab/core/annotations.py`** · 10 stubs · V1_F "Anotación de la señal"
  - Test: **crear** `tests/test_annotations.py`.
  - Las anotaciones se guardan en muestras, no en segundos.

---

## Hito 3: Sesión

- [ ] **`psglab/core/session.py`** · 19 stubs · V1_F "Navegación";
      V2_P, V3_P, V4_F "Histograma", V5_F "Visualización"
  - Test: **crear** `tests/test_session.py`. Navegación y amplitud son
    testeables sin GUI: ese es el motivo de que `Session` viva en `core/`.
  - Va a necesitar importar `core/windows.py` para `n_windows` (VENMAX); hoy
    todavía no lo importa.
  - Los topes de amplitud salen de `config`, no se escriben a mano.
  - Las tres propiedades `recording`, `scoring` y `annotations` son el único
    camino por el que las herramientas y la interfaz llegan a lo que hay
    abierto: no agregar accesos por atributo suelto.

> **Cerrado el hito 3, toda la capa de negocio funciona sin abrir una ventana.**

---

## Hito 4: Importación

- [ ] **`psglab/readers/channel_types.py`** · 3 stubs · V4_F "Visualización"
  - Test: **crear** `tests/test_channel_types.py`. Los nombres de
    `conftest.py` ya sirven: `C3` debe dar EEG por 10-20 y `EMG-menton` por
    prefijo.
- [ ] **`psglab/readers/base.py`** · 1 stub (`file_dialog_filter`) · base de
      V1_F/V2_F/V3_F "Importación"
  - El resto del módulo ya está implementado a propósito: `can_read`,
    `register_reader` y `read_recording` corren al importar. **No convertirlos
    en stubs.**
- [ ] **`psglab/readers/edf.py`** · 1 stub · V2_F "Importación"
- [ ] **`psglab/readers/brainvision.py`** · 1 stub · V1_F "Importación"
  - Test de los dos: **crear** `tests/test_readers.py`. Necesita el registro de
    prueba del hito 0.
  - `read()` devuelve la señal **ya en µV** y con la clase de canal detectada.
    Ninguna capa posterior lo vuelve a verificar.
- [ ] **`psglab/readers/scoring_reader.py`** · 2 stubs · V3_F "Importación"

---

## Hito 5: Exportadores

- [ ] **`psglab/exporters/statistics.py`** · 6 stubs · alimenta V3_F
      "Archivo de salida"
  - No escribe archivos: por eso se puede testear sin tocar el disco.
- [ ] **`psglab/exporters/scoring_txt.py`** · 2 stubs · V1_F "Archivo de salida"
  - **Las dos variantes de formato tienen que seguir siendo alcanzables**
    cambiando sólo `config.SCORING_INCLUDES_WINDOW_NUMBER`.
- [ ] **`psglab/exporters/annotations_txt.py`** · 2 stubs · V2_F "Archivo de
      salida" — **depende del hito 0** (índice de los puntos)
- [ ] **`psglab/exporters/information_txt.py`** · 3 stubs · V3_F "Archivo de
      salida"
  - Las secciones que no correspondan se omiten con una explicación, no con
    ceros.
- [ ] Test de los cuatro: `tests/test_exporters.py` → **borrar el
      `pytestmark`** y extenderlo a `statistics`.

> **Cerrado el hito 5, el programa hace su trabajo entero desde un script, sin
> interfaz.** Vale la pena escribir ese script y guardarlo como verificación.

---

## Hito 6: Interfaz

Primera vez que el programa se puede abrir. `ui/` **no lleva tests unitarios**:
por eso la capa se mantiene delgada y toda la regla vive en `core/`. No es un
olvido.

- [ ] **`psglab/ui/grid.py`** · 4 stubs · V1_P, V2_F "Diseño de la interfaz"
- [ ] **`psglab/ui/signal_view.py`** · 12 stubs · V1_P, V2_P, V4_F, V5_F
      "Visualización" (+ el dibujo de V3_P)
  - Incluye `seconds_at`, `window_fraction_at` y `sample_at`: es el **único**
    lugar que traduce entre píxeles, segundos, fracción de ventana y muestras.
    Ver el contrato en `psglab/tools/base.py`.
- [ ] **`psglab/ui/navigation.py`** · 5 stubs · V1_F "Navegación"
- [ ] **`psglab/ui/channel_selector.py`** · 6 stubs · V3_P, V4_F "Visualización"
- [ ] **`psglab/ui/scoring_panel.py`** · 3 stubs · V1_F, V2_F, V3_F "Scoring"
- [ ] **`psglab/ui/shortcuts.py`** · 3 stubs · flechas y teclas de fase
  - Los atajos se declaran **sólo acá**. Los de fase salen de la nomenclatura,
    no de un diccionario a mano.
- [ ] **`psglab/ui/main_window.py`** · 10 stubs · V4_F "Archivo de salida"
  - Conecta, no implementa. Acá se cablean a mano los callbacks de las
    herramientas, que no usan señales de Qt.
- [ ] **`psglab/app.py`** · 2 stubs · infraestructura
  - Con esto `python main.py` deja de terminar en `NotImplementedError`.

---

## Hito 7: Herramientas

Las seis son independientes entre sí: **se pueden repartir**. Todas se pueden
testear sin GUI, porque `Tool` y `ViewerTool` no heredan de `QObject`.

Antes de escribir una, leé [`tools/README.md`](../psglab/tools/README.md): el
sistema de coordenadas de `ViewerTool` (segundos y µV) no es el de `Tool`
(coordenadas propias del panel).

- [ ] **`psglab/tools/amplitude_band.py`** · 5 stubs · V1_F "Herramienta de
      amplitud" · `ViewerTool`
  - Test: **crear** `tests/test_amplitude_band.py`. Los 75 µV salen de
    `config.AMPLITUDE_BAND_UV`.
- [ ] **`psglab/tools/occupancy.py`** · 12 stubs · V1_F–V5_F "Ocupación" ·
      `ViewerTool` — **V2_F y V4_F dependen del hito 0**
  - Test: `tests/test_occupancy.py` → **borrar el `pytestmark`**.
- [ ] **`psglab/tools/magnifier.py`** · 8 stubs · V1_F, V2_F "Lupa" ·
      `ViewerTool`
  - Test: **crear** `tests/test_magnifier.py` (el contador de picos es
    testeable sin dibujar nada).
- [ ] **`psglab/tools/overview.py`** · 6 stubs · V1_F, V2_F, V3_F "Übersicht" ·
      `Tool`
  - Test: **crear** `tests/test_overview.py`. La cantidad de vecinas es
    configurable y asimétrica.
- [ ] **`psglab/tools/histogram.py`** · 7 stubs · V1_P, V2_F, V3_F, V4_F
      "Histograma" · `Tool`
  - Test: **crear** `tests/test_histogram.py`.
  - Su `on_click(x_fraction)` es propio: un clic cae en una ventana de la
    noche, no en un segundo de la ventana actual.
- [ ] **`psglab/tools/annotator.py`** · 9 stubs · V1_F "Anotación" ·
      `ViewerTool` — **depende del hito 0** (índice de los puntos)
  - Test: **crear** `tests/test_annotator.py`.

`tools/base.py` y `tools/registry.py` **ya están implementados** y no tienen
stubs. No hay nada que hacer en ellos.

---

## Hito 8: Cierre de la Parte 1

- [ ] **Ningún test salteado.** `python -m pytest` no debe informar ningún
      `skipped`:
      ```bash
      python -m pytest -rs
      ```
- [ ] **Ningún stub de Parte 1.** Tiene que dar 0:
      ```bash
      grep -r "raise NotImplementedError" psglab --include=*.py | grep -v "/analysis/" | wc -l
      ```
- [ ] **Los 34 IDs de la Parte 1 de [`TRAZABILIDAD.md`](TRAZABILIDAD.md) están
      cerrados**, y cada fila apunta al archivo correcto.
- [ ] **Las ambigüedades resueltas quedaron documentadas** en
      `EXPLICACION.txt` sección 8, y los módulos que decían "PENDIENTE DE
      CONFIRMACIÓN" ya no lo dicen.
- [ ] **Licencias verificadas**, sin ninguna GPL:
      ```bash
      pip-licenses --format=markdown --order=license
      ```
- [ ] **El programa se abre, scorea una noche y exporta los tres archivos.**

---

## Al agregar o cerrar un ítem

Actualizá en el mismo commit: este archivo, la fila de `TRAZABILIDAD.md` y el
`README.md` de la carpeta que tocaste. Los PR van a la branch **`Add`**, nunca
a `Master`, y vienen comentados.
