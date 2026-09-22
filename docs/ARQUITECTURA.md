# Arquitectura del proyecto

Decisiones de diseño y sus motivos. Si alguna decisión se revisa, actualizar
este archivo con el motivo del cambio: lo que se pierde con el tiempo no son
las decisiones sino las razones.

---

## Las tres reglas del pliego que definen la estructura

El pliego (sección 7) pide tres cosas que, juntas, determinan casi por
completo cómo está organizado el código:

1. `main.py` **lo más simple posible**, llamando funciones que viven en otros
   `.py`.
2. Los `.py` **separados por funcionalidad**, para saber qué hace cada uno y
   **qué archivo se tocó** ante un cambio.
3. Diseño **escalable**: poder agregar funcionalidades.

De ahí salen las capas, el registro de herramientas y la tabla de
trazabilidad.

---

## Capas y dirección de las dependencias

```
                    ┌─────────┐
                    │  utils  │   (no depende de nadie)
                    └────┬────┘
                         │
                    ┌────▼────┐
          ┌─────────►  core   ◄─────────────────────────┐
          │         └────▲────┘         │               │
          │              │              │               │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴──────┐  ┌─────┴────┐
    │  readers  │  │  tools    │  │ exporters  │  │ analysis │
    └───────────┘  └─────▲─────┘  └────────────┘  └──────────┘
                         │
                    ┌────┴────┐
                    │   ui    ├──────────────► core
                    └─────────┘
```

El diagrama muestra de qué **cuelga** cada capa: las cuatro del medio dependen
sólo de `core/` —y de `utils/` y `config`, que no dependen de nadie—, y `ui/`
cuelga de `tools/` además de `core/`.

**Pero `ui/` importa de todas**, medido sobre los imports y no sobre la
intención: `core`, `tools`, `analysis`, `readers`, `exporters`, `utils` y
`config`. Es lo que corresponde a la capa de arriba —abre archivos, exporta,
pide análisis— y no rompe ninguna regla, porque las flechas siguen apuntando en
una sola dirección. Decía que tenía "dos dependencias" y no era cierto; lo que
importa no es cuántas tiene sino que **ninguna apunte hacia arriba**.

Las flechas apuntan en una sola dirección y **`core/` no importa nada de
`ui/`**. No es una preferencia estética: es lo que permite testear el modelo,
el scoring, las estadísticas y los exportadores sin abrir una ventana
gráfica. Sin esa separación, el testeo recurrente que pide el pliego
(sección 7) sería inviable en la práctica, porque cada test necesitaría
levantar la interfaz.

Regla de bolsillo: **si una regla de negocio está en `ui/`, está en el lugar
equivocado.** Que la ventana 0 se muestre como "Ventana 1" es presentación y
va en `ui/`; que no se pueda scorear la ventana 500 de un registro de 400
ventanas es una regla y va en `core/`.

---

## Escalabilidad: los dos puntos de extensión

El pliego pide poder agregar funcionalidades. En este proyecto eso toma dos
formas concretas.

**Herramientas** (`psglab/tools/registry.py`). Agregar una herramienta nueva
es crear un archivo, heredar de `ViewerTool` (si actúa con el mouse sobre la
señal) o de `Tool` (si es un panel), y decorar la clase con
`@register_tool`. El menú Herramientas se arma recorriendo el registro,
así que la herramienta aparece sola. No hay que tocar `main.py`, ni la
ventana principal, ni ninguna herramienta existente.

**Formatos de archivo** (`psglab/readers/base.py`). Mismo mecanismo: heredar
de `Reader`, decorar con `@register_reader`, y el formato aparece solo en el
diálogo de apertura. Esto es lo que hace alcanzable el objetivo del pliego de
importar "cualquier formato de archivo de registro de polisomnografía": los
formatos se suman de a uno sin rediseñar nada.

---

## Decisiones y sus motivos

### PySide6 y no PyQt — es una decisión de licencia, no de gusto

El pliego pide licencia **MIT**. PyQt5 y PyQt6 se distribuyen bajo **GPL** o
licencia comercial paga: usar PyQt obligaría a licenciar todo el proyecto
como GPL, lo que contradice directamente el pliego.

PySide6 es el binding oficial de Qt para Python y se distribuye bajo
**LGPLv3**, que sí permite distribuir el proyecto propio bajo MIT mientras el
enlace sea dinámico, que es lo normal en Python.

**No agregar PyQt al proyecto bajo ninguna circunstancia.**

### pyqtgraph y no matplotlib para las ondas

matplotlib es excelente para figuras de publicación y demasiado lento para lo
que hace este programa: redibujar decenas de canales a cientos de hercios cada
vez que el usuario aprieta una flecha. Alguien que scorea una noche entera
pasa por cientos de ventanas seguidas, y medio segundo de demora por ventana
vuelve el programa inusable.

pyqtgraph está pensado para datos que se actualizan, integra con Qt y es MIT.

### MNE-Python para lectura y análisis

Cubre BrainVision y EDF de fábrica más una veintena de formatos, y ya trae
filtrado, ICA y re-referenciado, que son requisitos de la Parte 2. Escribir
esos parsers y esos algoritmos a mano sería reimplementar, con menos horas de
revisión, algo que la comunidad científica ya validó. Es BSD-3.

### Microvoltios en todo el programa

El pliego escribe "mV", pero su propio ejemplo es "75mv" y el criterio de 75
sobre EEG es el clásico de amplitud de ondas lentas en **microvoltios**. En
milivoltios sería mil veces la amplitud fisiológica real. Confirmado con el
cliente: **µV**.

La conversión se hace una sola vez, al importar, en
`psglab/utils/units.py`. Ninguna otra capa vuelve a preguntarse por la unidad.

### REM es una fase de primera clase

El listado de fases del pliego (V1_F y V3_F de "Scoring") no menciona REM,
pero el histograma sí la incluye. R&K sin REM y AASM sin R no son
nomenclaturas válidas. Confirmado con el cliente: **REM va en las dos**.

`tests/test_nomenclature.py` lo verifica explícitamente, para que la omisión
no vuelva a colarse.

### Las herramientas no heredan de QObject

`Tool` es una clase común y avisa por callbacks, no por señales de Qt. Así se
pueden testear sin levantar una aplicación gráfica. El precio es cablear los
callbacks a mano en la ventana principal, que es un costo chico y acotado a
un solo lugar.

### `Tool` y `ViewerTool`: dos contratos, no uno

El pliego agrupa bajo "herramienta" cosas que se comportan distinto. Cuatro
actúan con el mouse sobre la ventana de la señal (amplitud, ocupación, lupa,
anotador) y dos son paneles con su propia zona de pantalla (Übersicht e
histograma).

La diferencia no es cosmética: **el sistema de coordenadas no es el mismo**.
Un clic en el visualizador cae en el segundo 12 de la ventana actual; un clic
en el histograma cae en la ventana 340 de la noche. Un solo contrato obligaría
a documentar `x` de dos formas contradictorias, y tarde o temprano alguien
interpretaría mal el parámetro.

Por eso `tools/base.py` define dos clases: `Tool` con el ciclo de vida común,
y `ViewerTool` que agrega los eventos de mouse con coordenadas del
visualizador. El histograma declara su propio `on_click(x_fraction)`.

Los métodos de evento **no hacen nada por defecto** en vez de elevar
`NotImplementedError`. Una herramienta sobrescribe sólo los que le interesan:
la banda de amplitud escucha el movimiento del mouse y nada más. Si el método
base fallara, activarla y navegar a otra ventana rompería el programa.

---

## Licencias de las dependencias

Todas compatibles con MIT.

| Paquete | Licencia | Uso |
|---------|----------|-----|
| PySide6 | LGPL-3.0 | Interfaz gráfica |
| pyqtgraph | MIT | Render de las ondas |
| numpy | BSD-3 | Base numérica |
| scipy | BSD-3 | Filtros, PSD, estadística |
| mne | BSD-3 | Lectura de formatos, filtrado, ICA |
| mne-connectivity | BSD-3 | Conectividad |
| antropy | BSD-3 | Complejidad |
| pytest | MIT | Tests |
| pip-licenses | MIT | Verificación de licencias |

**Prohibido:** PyQt5, PyQt6 (GPL).

### Las tipografías que el programa trae

Desde el hito 26 el programa distribuye archivos de **IBM Plex** en
`psglab/resources/fonts/`: Sans regular y seminegrita y Mono regular desde
entonces, y **Sans itálica desde el hito 46**. La cuarta entró porque el rol
`ausente` de la escala tipográfica pide inclinada —es como se escribe «sin
medir» y «sin scorear»— y, sin el corte de verdad, Qt sintetizaba la
inclinación deformando la regular: se distinguía de la recta, pero se leía
peor. Es la misma versión 3.005 y la misma fundición que la regular. Van bajo la
**SIL Open Font License 1.1**, que permite empaquetarlas con un programa de
cualquier licencia, el MIT de éste incluido, con dos condiciones: que la
licencia viaje con los archivos —está en `OFL.txt`, al lado— y que una versión
modificada no use el nombre reservado «Plex». No se modifican.

**El control de licencias del CI no las ve**, porque sólo recorre los paquetes
de pip. Por eso quedan anotadas acá, y un archivo que se agregue a esa carpeta
tiene que traer su licencia y sumarse a este párrafo.

Se bajaron del repositorio oficial, `github.com/IBM/plex`, y se verificaron
contra los tamaños que publica su API.

**Desde el hito 34 son las que se ven al arrancar**: Sans en la interfaz, por
el valor de fábrica de `font_family`, y Mono en las lecturas numéricas, por los
dos esquemas nuevos. Hasta entonces sólo las usaba quien elegía el esquema
Papel o las pedía en Tipografía. Lo que no cambió es qué pasa si faltan: el
programa arranca igual, con la del sistema, y `fonts.available_family()` es lo
que impide que Qt sustituya por cualquier otra sin avisar.

Verificar antes de cada release:

```bash
python -m piplicenses --format=markdown --order=license
```

Se invoca por módulo: el comando `pip-licenses` depende de que el directorio
`Scripts/` del entorno esté en el PATH y de que el entorno no haya cambiado de
ruta.

Si aparece una dependencia GPL, hay que reemplazarla: no es un detalle
formal, es la licencia del proyecto entero.

### Verificación del 3 de septiembre de 2026

Corrida sobre el entorno completo (48 paquetes, Python 3.14.7). Resultado:
**la licencia MIT se sostiene.** PyQt5 y PyQt6 están ausentes; el único
paquete cuyo nombre contiene "PyQt" es `pyqtgraph`, que es MIT y no tiene
relación con PyQt.

Dos resultados que conviene explicar, porque parecen alarmas y no lo son:

- **PySide6, PySide6_Essentials, PySide6_Addons y shiboken6** declaran
  `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Es una licencia
  **disyuntiva**: quien la usa elige una. Elegimos **LGPL-3.0**, que permite
  distribuir nuestro código bajo MIT mientras el enlace sea dinámico, que es
  lo que hace pip al instalar el paquete. Es exactamente el escenario para el
  que se eligió PySide6 en lugar de PyQt.
- **certifi** y **tqdm** declaran MPL-2.0. Es copyleft **por archivo**: obliga
  a compartir las modificaciones de los archivos con esa licencia. No los
  modificamos, así que no alcanza a nuestro código.

Ninguna dependencia obliga a relicenciar el proyecto.

### Verificación del 7 de septiembre de 2026

La del hito 8. Corrida sobre el entorno completo, **35 paquetes**, Python
3.12.10:

```bash
python -m piplicenses --format=markdown --order=license
```

| Licencia | Paquetes |
|---|---|
| MIT y variantes (MIT, MIT License, MIT-CMU) | 11 |
| BSD y variantes (BSD License, BSD-3-Clause, BSD-2-Clause) | 13 |
| `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | 4 — los de PySide6 |
| Apache (Apache-2.0, y una disyuntiva con BSD-2-Clause) | 3 |
| MPL-2.0, sola y combinada con MIT | 2 |
| Python Software Foundation License | 1 |
| Combinada permisiva (BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0) | 1 |

**La licencia MIT se sostiene.** No aparece ninguna GPL pura: las cuatro
disyuntivas son las de PySide6 y se resuelven eligiendo LGPL-3.0, como explica
el bloque anterior. PyQt5 y PyQt6 siguen ausentes; el único paquete cuyo nombre
contiene "PyQt" es `pyqtgraph` 0.14.0, que es MIT.

El número de paquetes bajó de 48 a 35 desde la verificación anterior, y no es
un hallazgo: aquélla se corrió con `requirements-analysis.txt` instalado —que
arrastra numba, llvmlite, xarray, pandas y scikit-learn— y ésta con el entorno
de la Parte 1, que es el que usa el día a día. El CI sigue revisando los tres
requirements juntos en su job de licencias, que es donde importa.

### Verificación del 8 de septiembre de 2026

La del hito 17, que cierra la Parte 2. Corrida sobre el entorno **con los tres
requirements**, que es lo que el producto distribuye: **49 paquetes**, Python
3.12.10.

```bash
python -m piplicenses --format=markdown --order=license
```

| Licencia | Paquetes |
|---|---|
| MIT y variantes (MIT, MIT License, MIT-CMU) | 14 |
| BSD y variantes (BSD License, BSD-3-Clause, BSD-2-Clause, BSD (3-clause)) | 21 |
| `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | 4 — los de PySide6 |
| Apache (Apache-2.0, Apache Software License, y dos disyuntivas con BSD) | 5 |
| MPL-2.0, sola y combinada con MIT | 2 |
| `BSD-2-Clause AND Apache-2.0 WITH LLVM-exception` | 1 — `llvmlite` |
| `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | 1 |
| Python Software Foundation License | 1 |

**La licencia MIT se sostiene.** No aparece ninguna GPL pura: las cuatro
disyuntivas siguen siendo las de PySide6, que se resuelven eligiendo LGPL-3.0.

Los 14 paquetes de diferencia con la verificación anterior son los que arrastra
`requirements-analysis.txt` —numba, llvmlite, xarray, pandas, scikit-learn y sus
dependencias—. **Esta vez se corrió con ellos a propósito**: aquélla se hizo con
el entorno de la Parte 1 porque era el del día a día, y desde el hito 10 dejó de
serlo. `llvmlite` es el único que aporta una licencia nueva a la tabla, y su
excepción LLVM sobre Apache-2.0 es permisiva.

---

### `float64` y no `float32` para la señal — es una decisión medida

La señal vive entera en memoria, así que pasarla a `float32` partiría al medio
lo que ocupa un registro. Se evaluó en el hito 18 y **se descartó**.

El motivo no es la precisión: un conversor de 16 bits entra de sobra en la
mantisa de 24 de un `float32`. Es que **MNE trabaja siempre en `float64`**, y al
pasarle un array `float32` lo convierte, lo que cuesta una copia completa más.

```
RawArray desde float32: pico 224 MB, queda en float64
RawArray desde float64: pico  28 MB, queda en float64   (reusa el array)
```

`float32` **baja lo que está en reposo y sube el pico**, que es justamente donde
ocurre el `MemoryError`. Mueve el problema hacia el peor lado, así que no se
hace. Si algún día se revisa, hay que volver a medir esto primero.

---

### Cuánto tarda dibujar la señal — medido el 15 de septiembre de 2026

La justificación de pyqtgraph decía "medio segundo de demora por ventana vuelve
el programa inusable", y ese umbral se usó durante todo el proyecto **sin que
nadie midiera contra qué**. Se midió al abrir el refactor de la interfaz, porque
la escala de tiempo libre se diseñaba a ciegas sin este número.

`SignalView.show_window()` sobre señal sintética, ventana de 1600 × 900,
promedio de doce redibujos después del primero:

| Canales | 100 Hz | 256 Hz | 1000 Hz |
|---|---|---|---|
| 4 | 17,6 ms | 20,2 ms | 47,8 ms |
| 8 | 18,8 ms | 40,0 ms | 51,0 ms |
| 16 | 19,7 ms | 47,5 ms | 58,2 ms |
| 32 | 22,8 ms | 56,4 ms | 69,9 ms |
| 64 | 28,3 ms | 56,8 ms | 92,2 ms |

**El dibujo de una ventana no es un cuello de botella.** El peor caso —64
canales a 1000 Hz, más de lo que usa el laboratorio— tarda 92 ms, cinco veces
por debajo del umbral. La decisión de pyqtgraph se sostiene con margen.

**La última frase de este párrafo decía que ninguna optimización del dibujo
estaba justificada, y el hito 25 la revisó.** No porque el número estuviera
mal, sino por lo que no medía: se tomó con `QT_QPA_PLATFORM=offscreen` y sobre
`show_window()`, o sea sin la composición real de la pantalla y sin la grilla
moviéndose. Con la reproducción del hito 24 —veinticinco cuadros por segundo—
eso dejó de ser un detalle:

| Un paso de reproducción, página de 30 s, 1400×800 en pantalla | |
|---|---|
| Registro de prueba, con la grilla fina (72 líneas) | 113 ms |
| El mismo paso con el fondo «sin líneas» | 57 ms |
| 72 líneas sueltas contra 72 en un solo objeto (banco aparte) | 67,5 contra 22,1 ms |

O sea que **cada línea de grilla costaba 0,8 ms por cuadro**, no por dibujarse
sino por ser un objeto de la escena. La lección para quien vuelva a medir es la
de la primera advertencia de abajo, ahora con un caso: un piso medido sin
pantalla no dice nada sobre lo que pasa a veinticinco cuadros por segundo.

Lo que sí es un problema aparece al soltar la escala de tiempo. Con la página
libre, "registro entero" son ocho horas a 1000 Hz, o sea **28,8 millones de
muestras por canal**:

| Puntos por curva | `setData` de una curva |
|---|---|
| 3 000 (una ventana a 100 Hz) | 0,4 ms |
| 300 000 | 0,8 ms |
| 1 000 000 | 3,0 ms |
| 3 000 000 | 10,2 ms |

El tiempo crece linealmente y sería tolerable. **El que no lo es es la
memoria**: una pantalla de 32 canales sin decimar son **6,9 GB** de `float64`,
que no es lento sino imposible. Por eso la decimación no es una optimización
sino un requisito de la escala libre, y por eso es min/max por columna de
píxeles y no un submuestreo: en polisomnografía el pico *es* el dato.

Dos advertencias sobre estos números, para quien los vuelva a medir:

- Se tomaron con `QT_QPA_PLATFORM=offscreen`. El costo de composición real de
  la pantalla no está incluido, así que son **un piso, no un techo**.
- `setData` de pyqtgraph es perezoso: parte del trabajo se difiere al repintado.
  La segunda tabla mide entregar los datos, no verlos.

---

### Contraste de los esquemas de color — WCAG 2.1, verificado por test

Los dos esquemas del programa se comprueban contra los umbrales de **WCAG
2.1**: 4,5 a 1 para el texto (criterio 1.4.3) y 3 a 1 para lo que hay que
distinguir de un vistazo, que en este programa son las curvas, la paleta de
canales y —desde el hito 34— la escala de fases (criterio 1.4.11).
`theme.low_contrast_elements()` hace la cuenta y `tests/test_theme.py` exige
que ningún esquema de fábrica tenga nada en esa lista. Un esquema con fondo de
ventana propio —Papel, desde el hito 26— suma el texto sobre ese fondo a la
cuenta.

**El control se hereda solo**: recorre `theme.SCHEMES`, así que un esquema
nuevo queda enrolado sin que nadie se acuerde de agregarlo. Los dos del hito 34
entraron así.

### Por qué el color de una fase vive en el esquema

Hasta el hito 34 el programa no tenía ninguno: el hipnograma se dibujaba con
una sola tinta. Al agregarlos había tres lugares posibles y uno solo es
correcto.

**No en `config.py`**, que guarda lo que fija el pliego: el pliego no dice nada
de colores, igual que con la paleta de canales. **No en `core/nomenclature.py`**,
donde vive `SleepStage`: el modelo no puede saber de presentación, y la regla
de que `core/` no conoce `ui/` es lo que permite testear el scoring sin abrir
una ventana. **Sí en `ColorScheme`**, porque el color de una fase depende del
fondo sobre el que se dibuja —el azul profundo que se lee sobre papel
desaparece sobre negro— y porque la misma escala tiene que pintar el
hipnograma, la franja de posición y el botón: si viviera en cada uno, se
separarían.

El campo se pide por el **valor** de la fase (`"N2"`) y no por el miembro del
enum, que es lo que evita que `ui/theme.py` importe `core/`.

**Se eligió un estándar y no un criterio propio** porque un umbral inventado se
discute cada vez que alguien no ve bien un color; uno publicado, no.

**Al escribir el test fallaron dos esquemas.** El azul de la paleta oscura daba
2,42 sobre el gris de fondo —un canal que casi no se distinguía— y el dorado
daba 2,41 sobre «Azul sobre gris». El primero se aclaró; el segundo esquema ganó una paleta propia, porque
**un fondo gris necesita colores más oscuros que uno blanco** y oscurecer la
paleta compartida habría cambiado el esquema claro sin motivo.

**La grilla y la línea de base quedan afuera a propósito.** Son referencias, y
tienen que verse menos que la señal: exigirles 3 a 1 las volvería tan
llamativas como lo que están ayudando a medir.

### Por qué son dos esquemas y no se editan

Hasta el hito 35 eran ocho, cada color se cambiaba uno por uno y un esquema
propio con poco contraste se permitía con un aviso al costado. El resultado era
que **el programa tenía infinitos aspectos posibles y ninguno garantizado**: el
control de arriba sólo alcanzaba a los de fábrica, y el que se armaba a mano
podía dejar la señal casi invisible con un cartel que nadie lee dos veces.

El usuario decidió quedarse con los dos del rediseño y ninguna perilla. Lo que
se gana no es sólo código de menos: **lo que se ve en una máquina del
laboratorio es lo que se ve en todas**, y las dos combinaciones posibles están
medidas. Lo que se pierde —un esquema para imprimir en blanco y negro, o uno
armado para una pantalla concreta— no lo pidió nadie en doce hitos de
interfaz. Si alguna vez hace falta, vuelve como un esquema más en la lista,
verificado como los dos que hay, y no como una perilla por color.

Con eso se fueron también el archivo suelto de esquema —`save_scheme` y
`load_scheme`, la vía para pasarse uno por correo—, el campo `custom_scheme`
de las preferencias y la grilla cuadriculada del esquema ECG, que era lo único
que la usaba. Un archivo de preferencias viejo que traiga cualquiera de esas
claves **sigue cargando**: el nombre que ya no existe cae en el de fábrica y lo
demás se ignora.

## Convenciones de código

- **La API pública y los nombres de archivo, en inglés**; comentarios,
  docstrings, documentación y **todo lo que ve el usuario, en español**. Lo
  que cruza el borde de un módulo se nombra en inglés —`read_recording`,
  `scale_uv`, `on_window_changed`— y el interior se escribe en español, que es
  el idioma en que se razona el problema: `_linea_debajo()`,
  `TOLERANCIA_DE_CLIC_EN_ESCALAS`. Así no se cierra la puerta a contribuidores
  externos y el código se lee igual para el equipo del laboratorio.
- **Cada módulo abre con un docstring** que dice de qué se ocupa y **qué IDs
  del pliego cubre**. Esa línea es la que alimenta `docs/TRAZABILIDAD.md`.
- **Los errores que ve el usuario heredan de `PsgLabError`** y llevan mensaje
  en español. Los usuarios son investigadores, no necesariamente
  programadores: una traza de Python no le sirve a nadie.
- **Type hints en todas las firmas.** Documentan el contrato mejor que un
  comentario y no se desactualizan en silencio.
