# `ui/` — interfaz gráfica

Construida con **PySide6** y **pyqtgraph**. Esta capa lee el estado de
[`psglab.core`](../core/README.md) y lo dibuja; **no guarda reglas de negocio
propias**.

Si una regla vive acá, está en el lugar equivocado: hay que moverla a `core/`,
donde se puede testear sin abrir una ventana. Mostrar la ventana 0 como
"Ventana 1" es presentación y va acá. Impedir que se scoree la ventana 500 de un
registro de 400 es una regla y va en `core/`.

## Distribución de la ventana

```
+--------------------------------------------------------------+
|  Menú: Archivo | Ver | Herramientas | Análisis | Ayuda        |
+--------------------------------------------------------------+
|  Barra de herramientas (lupa, amplitud, ocupación, anotar)    |
+------------------+-------------------------------------------+
|  Selector de     |                                           |
|  canales         |     Visualizador de la señal (30 s)       |
|                  |                                           |
+------------------+-------------------------------------------+
|  Panel de scoring (W / N1 / N2 / N3 / R ... + Arousal)        |
+--------------------------------------------------------------+
|  Histograma de la noche completa                              |
+--------------------------------------------------------------+
|  Barra de estado: ventana 42 / 960 - 00:21:00                 |
+--------------------------------------------------------------+
```

## Los archivos

| Archivo | De qué se ocupa | Pliego |
|---|---|---|
| `main_window.py` | Arma el layout y **conecta las piezas**; no implementa ninguna funcionalidad. | V4_F de "Archivo de salida" |
| `signal_view.py` | El visualizador de ondas. **El corazón de la interfaz.** | V1_P, V2_P, V4_F, V5_F de "Visualización"; V1_F de "Anotación de la señal" |
| `channel_selector.py` | Elegir cuántos y cuáles canales se ven, y corregir la clase detectada. | V3_P, V4_F de "Visualización" |
| `grid.py` | La grilla de fondo y los tres fondos elegibles. | V1_P, V2_F de "Diseño de la interfaz" |
| `navigation.py` | Botones de ventana anterior y siguiente, y posición actual. | V1_F de "Navegación" |
| `scoring_panel.py` | Elegir la fase de la ventana y marcar arousal. | V1_F, V2_F, V3_F de "Scoring" |
| `shortcuts.py` | **Fuente única de verdad de los atajos de teclado.** | V2_P, V5_F de "Visualización"; V1_F de "Navegación"; V1_F, V2_F de "Scoring" |

## `main_window.py` conecta, no implementa

Es el contenedor que reúne todas las funcionalidades de la Parte 1 **sin
implementar ninguna**: cada una vive en su módulo y acá sólo se las cablea entre
sí. También es donde se enganchan a mano los callbacks de las herramientas, que
no usan señales de Qt (ver [`tools/README.md`](../tools/README.md)).

Si estás agregando lógica acá, probablemente vaya en otro archivo.

## `shortcuts.py`

Todos los atajos se declaran en un solo lugar, por dos motivos: la ayuda muestra
la lista completa sin desactualizarse, y las colisiones se detectan leyendo un
solo archivo.

Los atajos no son un accesorio: **son la principal vía de trabajo de quien
scorea una noche entera.** Son cientos de ventanas, y pasar por el mouse en cada
una es inviable.

| Tecla | Acción |
|---|---|
| ← / → | Ventana anterior / siguiente |
| ↑ / ↓ | Aumentar / reducir la amplitud |
| `A` | Marcar o desmarcar arousal |
| `Ctrl+O` | Abrir un registro |
| `Ctrl+S` | Exportar el scoring |

Los atajos de las fases **no** están en ese diccionario: dependen de la
nomenclatura activa y los arma `stage_shortcuts()` (W, 1, 2, 3, 4, R, M en R&K;
W, 1, 2, 3, R en AASM). Así, agregar o cambiar una fase no obliga a tocar la
tabla a mano.

No se agregan atajos para funciones que el pliego no pide. Un "deshacer", por
ejemplo, no es una tecla sino un subsistema completo (historial de cambios del
scoring y de las anotaciones), y no está pedido.

## `grid.py`

La grilla está separada de `SignalView` porque **cambia por motivos distintos**:
la grilla depende de la preferencia visual del usuario, las curvas dependen de
los datos.

Tres fondos elegibles (`BackgroundStyle`, V2_F): blanco, sólo las líneas de 3
segundos, o las dos densidades juntas (3 s y 0,5 s).

## Por qué PySide6 y por qué pyqtgraph

**PySide6 y no PyQt: es una decisión de licencia, no de gusto.** PyQt5 y PyQt6
se distribuyen bajo GPL o licencia comercial paga; usarlos obligaría a licenciar
todo el proyecto como GPL, lo que contradice el pliego, que pide MIT. PySide6 es
el binding oficial de Qt bajo LGPLv3, que sí permite distribuir el proyecto bajo
MIT mientras el enlace sea dinámico —lo normal en Python—. **No agregar PyQt al
proyecto bajo ninguna circunstancia.**

**pyqtgraph y no matplotlib** para las ondas. matplotlib es excelente para
figuras de publicación y demasiado lento para lo que hace este programa:
redibujar decenas de canales a cientos de hercios cada vez que el usuario aprieta
una flecha. Medio segundo de demora por ventana, multiplicado por las cientos de
ventanas de una noche, vuelve el programa inusable.

## Estado

Pendientes **43 stubs**, en el
[hito 6 del TODO](../../docs/TODO.md#hito-6-interfaz). Es el último hito de
lógica: depende de que `core/session.py` esté terminado (hito 3).

Al cerrarlo, `python main.py` abre algo usable por primera vez.

Esta capa **no lleva tests unitarios**, y por eso se la mantiene delgada: es la
única que no se puede verificar sin levantar una ventana, así que todo lo que
valga la pena verificar debería poder verificarse desde `core/`, `tools/` o
`exporters/`. No es un olvido del TODO, y lo único que la ejercita es
`test_todos_los_modulos_del_paquete_se_pueden_importar`.
