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
          ┌─────────►  core   ◄─────────┐
          │         └────▲────┘         │
          │              │              │
    ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴──────┐
    │  readers  │  │  tools    │  │ exporters  │
    └───────────┘  └─────▲─────┘  └────────────┘
                         │
                    ┌────┴────┐        ┌──────────┐
                    │   ui    │        │ analysis ├──► core
                    └─────────┘        └──────────┘
```

Las flechas apuntan en una sola dirección y **`core/` no importa nada de
`ui/`**. No es una preferencia estética: es lo que permite testear el modelo,
el scoring, las estadísticas y los exportadores sin abrir una ventana
gráfica. Sin esa separación, el testeo recurrente que pide el pliego
(sección 11) sería inviable en la práctica, porque cada test necesitaría
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
`@register_tool`. La barra de herramientas se arma recorriendo el registro,
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

**Prohibido:** PyQt5, PyQt6 (GPL).

Verificar antes de cada release:

```bash
pip-licenses --format=markdown --order=license
```

Si aparece una dependencia GPL, hay que reemplazarla: no es un detalle
formal, es la licencia del proyecto entero.

### Verificación del 3 de septiembre de 2026

Corrida sobre el entorno completo (48 paquetes, Python 3.14.7). Resultado:
**la licencia MIT se sostiene.** PyQt5 y PyQt6 están ausentes; el único
paquete cuyo nombre contiene "PyQt" es `pyqtgraph`, que es MIT y no tiene
relación con PyQt.

Tres resultados que conviene explicar, porque parecen alarmas y no lo son:

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

---

## Convenciones de código

- **Identificadores y nombres de archivo en inglés**; comentarios, docstrings,
  documentación y **todo lo que ve el usuario, en español**. Es la convención
  de open source: no cierra la puerta a contribuidores externos y mantiene el
  código legible para el equipo del laboratorio.
- **Cada módulo abre con un docstring** que dice de qué se ocupa y **qué IDs
  del pliego cubre**. Esa línea es la que alimenta `docs/TRAZABILIDAD.md`.
- **Los errores que ve el usuario heredan de `PsgLabError`** y llevan mensaje
  en español. Los usuarios son investigadores, no necesariamente
  programadores: una traza de Python no le sirve a nadie.
- **Type hints en todas las firmas.** Documentan el contrato mejor que un
  comentario y no se desactualizan en silencio.
