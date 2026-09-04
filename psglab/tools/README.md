# `tools/` — herramientas enchufables

Cada herramienta del pliego vive en su propio archivo y **se registra sola**.
La ventana principal arma su barra recorriendo el registro, así que agregar una
herramienta es agregar un archivo: no hay que tocar `main.py`, ni la ventana
principal, ni ninguna herramienta existente.

Es la forma concreta que toma en este proyecto el requisito de escalabilidad
del pliego (sección 7). El otro punto de extensión es
[`readers/`](../readers/README.md).

## Los archivos

| Archivo | Herramienta | Base | Pliego |
|---|---|---|---|
| `base.py` | Los dos contratos: `Tool` y `ViewerTool`. | — | Base de las seis |
| `registry.py` | `@register_tool`, `available_tools()`, `load_all_tools()`. | — | — |
| `amplitude_band.py` | Banda de referencia de 75 µV, adaptada a la escala del usuario. | `ViewerTool` | V1_F de "Herramienta de amplitud" |
| `occupancy.py` | Líneas dibujadas con el mouse y su porcentaje de ocupación horizontal. | `ViewerTool` | V1_F–V5_F de "Ocupación de la página" |
| `magnifier.py` | Lupa: zoom circular y contador de picos. | `ViewerTool` | V1_F, V2_F de "Herramienta Lupa" |
| `annotator.py` | Anotación de eventos sobre la señal. | `ViewerTool` | V1_F de "Anotación de la señal" |
| `overview.py` | Übersicht: la ventana actual en su contexto. | `Tool` | V1_F–V3_F de "Herramienta Übersicht" |
| `histogram.py` | Hipnograma de la noche completa. | `Tool` | V1_P–V4_F de "Histograma" |

## Dos contratos, no uno

El pliego agrupa bajo "herramienta" cosas que se comportan distinto, y el código
las separa **porque el sistema de coordenadas no es el mismo**:

- **`ViewerTool`** — actúa con el mouse sobre la ventana de la señal. Sus
  métodos reciben `x` en **segundos desde el inicio de la ventana de 30 s** e
  `y` en **microvoltios**. Son la banda de amplitud, la ocupación, la lupa y el
  anotador.
- **`Tool`** — panel con su propia zona de pantalla y su propio sistema de
  coordenadas. Son la Übersicht y el histograma; un clic en el histograma no
  cae "en el segundo 12 de la ventana", cae **en la ventana 340 de la noche**.
  Por eso `HistogramTool` declara su propio `on_click(x_fraction)`.

Un solo contrato obligaría a documentar `x` de dos formas contradictorias, y
tarde o temprano alguien interpretaría mal el parámetro.

## Cómo agregar una herramienta

```python
# psglab/tools/mi_herramienta.py
from psglab.core.session import Session
from psglab.tools.base import ViewerTool
from psglab.tools.registry import register_tool


@register_tool
class MiHerramienta(ViewerTool):
    """Qué hace.

    Cubre del pliego: VN_F de "Sección tal".
    """

    name = "mi_herramienta"       # identificador interno, único
    label = "Mi herramienta"      # lo que ve el usuario en la barra
    description = "Ayuda que aparece al pasar el mouse."
    exclusive = True              # ver abajo

    def activate(self, session: Session) -> None: ...
    def deactivate(self) -> None: ...

    def on_mouse_move(self, x: float, y: float) -> None:
        ...                       # sobrescribí sólo los eventos que te importen
```

`exclusive = True` significa que activarla desactiva a las demás exclusivas.
Lo son **las que se quedan con el clic del mouse** sobre el visualizador: la
lupa y el anotador. La banda de amplitud no, porque sólo se dibuja; los paneles
tampoco, porque no compiten por el mouse.

`name` tiene que ser único: si se repite, `@register_tool` eleva
`DuplicateToolError` **al importar**, que es cuando conviene enterarse.

## Dos detalles del diseño que conviene no revertir

**Ni `Tool` ni `ViewerTool` heredan de `QObject`.** Son objetos comunes de
Python y avisan por callbacks, no por señales de Qt. Por eso se las puede
testear sin levantar la interfaz. El precio es cablear los callbacks a mano en
la ventana principal: un costo chico y acotado a un solo lugar.

**Los métodos de evento no hacen nada por defecto**, en vez de elevar
`NotImplementedError`. Una herramienta sobrescribe sólo los que le interesan: la
banda de amplitud escucha el movimiento del mouse y nada más. Si el método base
fallara, activarla y navegar a otra ventana rompería el programa.

Por la misma razón, `registry.py` **está implementado y no es un stub**:
`register_tool` es un decorador y se ejecuta al importar cada herramienta. Si
elevara `NotImplementedError`, ningún módulo de `psglab.tools` podría importarse
y el mecanismo enchufable no existiría.

## `on_window_changed`

Lo hereda todo lo que sea `Tool`. No hace nada por defecto; sobrescribilo sólo
si a tu herramienta le importa enterarse de que el usuario navegó. El medidor de
ocupación lo usa para borrar sus líneas (V5_F) y la Übersicht para redibujarse.

## La superposición de la ocupación

Si dos líneas se pisan en horizontal, **la zona compartida se cuenta dos
veces**: se suman los aportes sin descontar, así que el total puede pasar del
100 % y eso es lo buscado. Confirmado con el cliente el 4 de septiembre de 2026
y parametrizado en `config.OCCUPANCY_COUNTS_OVERLAP_ONCE` (hoy `False`). Ver el
[hito 0 del TODO](../../docs/TODO.md#hito-0-desbloquear).

## Estado

Pendientes **47 stubs**, en el
[hito 7 del TODO](../../docs/TODO.md#hito-7-herramientas). Las seis
herramientas son independientes entre sí, así que **se pueden repartir**.

`base.py` y `registry.py` ya están implementados y no tienen stubs.

**Ninguna está bloqueada.** `occupancy.py` (V2_F y V4_F) y `annotator.py` lo
estuvieron hasta que el [hito 0](../../docs/TODO.md#hito-0-desbloquear) fijó el
conteo de la superposición y el índice de los puntos.
