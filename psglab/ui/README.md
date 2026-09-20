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
+---------------------------------------------------------------+
| [abrir] Scoring | Escala de tiempo | Amplitud | Ver | Montaje  |
|   Filtrar | Analizar | Herramientas | Configuración | Ayuda     |
+----------+-----------------------------------------+----------+
| Canales  |                                         | Espectro |
|  (dock)  |   Visualizador de la señal (central)    | Métrica  |
|          |                                         | ICA...   |
|          |                                         | (solapas)|
+----------+-----------------------------------------+----------+
|  Übersicht | Scoring | Hipnograma  (docks de abajo, ocultos)   |
+---------------------------------------------------------------+
|  Navegación: ⏮ ◀ ⏯ ▶ ⏭  1×  | amplitud | franja | posición     |
+---------------------------------------------------------------+
|  Barra de estado: ventana 42 / 960 - 00:21:00                  |
+---------------------------------------------------------------+
```

**La señal es el widget central y todo lo demás es un `QDockWidget`**: se mueve,
se apila en solapas, se cierra y se saca a otra pantalla.

**El programa abre siempre con la señal y el panel Canales, y nada más.**
Los otros nueve arrancan ocultos y se abren desde «Herramientas», que desde
el hito 28 junta las herramientas y los paneles; «Herramientas ▸ Restaurar la
disposición» vuelve a esa vista. Desde el hito 24 la
disposición no se recuerda de una apertura a otra.

**La barra de menú empieza con un botón y no con «Archivo».** Abrir un
registro era lo único que le quedaba a ese menú, así que es un icono de
carpeta en la esquina. «Configuración» tampoco despliega nada: abre su
ventana. **No hay barra de herramientas**: las herramientas se activan desde
su menú, que es la única vía desde el hito 23.

**La navegación no es un dock**, y es la única excepción: es la única vía de
navegación con el mouse, así que poder cerrarla dejaría sin salida a quien no
conoce las flechas del teclado.

## Los archivos

| Archivo | De qué se ocupa | Pliego |
|---|---|---|
| `main_window.py` | Arma el layout y **conecta las piezas**; no implementa ninguna funcionalidad. `export()` escribe los tres archivos de salida, pero desde el hito 23 la ventana sólo ofrece el scoring, en cuatro formatos. Antes de cerrar, de abrir otro registro o de importar un scoring encima pregunta por el trabajo sin exportar —Exportar…, Descartar o Cancelar—, scoring y anotaciones, con un diálogo de guardado por cada cosa en juego; la regla de qué cuenta es de `Session`. Después de abrir uno muestra los avisos que dejó el lector, como el de un archivo truncado. | V4_F de "Archivo de salida" |
| `signal_view.py` | El visualizador de ondas. **El corazón de la interfaz.** Marca la época con una banda y, reproduciendo, el cursor con una línea: las dos se crean una vez y se mueven. | V1_P, V2_P, V4_F, V5_F de "Visualización"; V1_F de "Anotación de la señal" |
| `channel_selector.py` | Elegir cuántos y cuáles canales se ven, agrupados por clase. | V3_P, V4_F de "Visualización" |
| `grid.py` | La grilla de fondo, los tres fondos elegibles y las líneas de cero de los canales. **Todas las líneas son un solo objeto de la escena**: como objetos sueltos costaban 0,8 ms por línea y por cuadro. | V1_P, V2_F de "Diseño de la interfaz" |
| `filter_panel.py` | Los filtros de cada clase de canal presente, sugeridos según la frecuencia del registro. La celda vacía desactiva ese filtro. | V1_F de "Filtración" |
| `impedance_panel.py` | Tabla editable de impedancias por canal y el informe. La celda sin valor dice "sin medir", no "0". El nombre del canal no se edita: `FixedColumnDelegate`, que usa también el panel de filtros. | V1_F de "Impedancia" |
| `ica_panel.py` | Inspeccionar los componentes de una ICA y elegir cuáles quitar. La topografía dice **dónde** pesa cada uno y la curva temporal **cuándo** ocurre. Ninguno viene marcado. | V5_F de "Filtración" |
| `metric_panel.py` | Una métrica por ventana a lo largo de la noche, con los NaN como hueco. La usan complejidad y conectividad. | — (Parte 2) |
| `connectivity_panel.py` | Mapa de calor de la matriz de conectividad, con los nombres de canal en los ejes. | — (Parte 2) |
| `psd_panel.py` | Dibuja el espectro que calcula `analysis/psd.py`, con sus bandas sombreadas, el eje de potencia en logarítmico y la tabla de potencia por banda —absoluta y relativa—. Arriba, una línea dice con qué método se estimó. | V1_F de "PSD" |
| `overview_panel.py` | Dibuja el panel de contexto que publica `OverviewTool`: las ventanas vecinas, con la actual marcada. El ancho que se pide es el preferido; se deja angostar hasta 120 px. | V1_F, V2_F, V3_F de "Übersicht" |
| `navigation.py` | La barra inferior: ocho controles —primera, anterior, reproducir/pausar, siguiente, última, velocidad, menos y más amplitud— y una franja que muestra dónde cae la ventana en la noche y deja saltar con un clic. Los botones de página se sacaron en el hito 27; sus atajos siguen. | V1_F de "Navegación" |
| `playback.py` | El reloj de la reproducción: mide el tiempo real y avisa cuánto avanzar el cursor. No conoce la sesión ni mueve nada; la regla del cursor es de `Session.move_playhead()`. | V1_F de "Navegación" |
| `scoring_panel.py` | Elegir la fase de la ventana y marcar arousal. Las fases van en su propia fila, debajo del selector, para que el mínimo del panel sea el de la fila más ancha y no la suma; abajo, un pie con la ventana y su fase, que se sigue viendo si el panel sale a otra pantalla. | V1_F, V2_F, V3_F de "Scoring" |
| `icons.py` | Los iconos de la barra de navegación y el de abrir un registro, dibujados con `QPainterPath`. **No hay ningún archivo de icono en el repositorio**, y es una decisión de licencia. | — |
| `docks.py` | **Dónde va cada panel** alrededor de la señal, que es el widget central. Los seis de análisis se apilan en solapas, arrancan ocultos y al abrirse se llevan `FRACCION_DE_ANALISIS` del ancho: sin eso Qt les daba más lugar que a la señal. **El título de un dock no se cambia**: Qt lo usa como texto de su entrada en «Herramientas». Lo que describe un resultado va en el panel, con `set_caption()`. | — |
| `menus.py` | **La barra de menú**: qué acción vive en qué menú, y el botón de abrir un registro. No implementa ninguna: cada una llama a un método de la ventana. «Herramientas» lleva los modos del mouse y los paneles, sin repetir los que son las dos cosas. | — |
| `theme.py` | **Los esquemas de color del programa.** Qué color tiene cada cosa que se dibuja, y los ocho esquemas de fábrica. Claro no pone hoja de estilo y queda nativo; Papel, el del lienzo de diseño, separa el fondo de la ventana (`chrome`) del de las áreas de dibujo y les da a las lecturas numéricas su propia tipografía. **Sereno y Nocturno**, del hito 34, son los del rediseño: traen además `stage_colors`, la escala que pinta cada fase de sueño, y de acá salen también los tokens de forma —radio, alto de control, anillo de foco— que consume la hoja de estilo. | — |
| `fonts.py` | Registra las tipografías que el programa trae —IBM Plex Sans y Mono, en `psglab/resources/fonts/`, bajo la OFL 1.1—. **Sans es la de la interfaz desde el hito 34** (`UI_FONT_FAMILY`, el valor de fábrica de `font_family`) y Mono, la de las lecturas numéricas de los esquemas que la piden. Si faltan, el programa arranca igual: `available_family()` devuelve None y se usa la del sistema, en vez de dejar que Qt sustituya por cualquier otra. | — |
| `preferences.py` | Lo que el programa recuerda entre una sesión y la siguiente, en un JSON del perfil del usuario. La disposición de paneles ya no es parte de eso. Un campo que trae cualquier cosa vuelve al de fábrica, y `load()` no eleva nada que no sea `PsgLabError`: es lo único que atrapa el arranque. | — |
| `settings_dialog.py` | **La ventana de configuración**: cinco solapas, todas con algo real detrás. Aplica en el momento y avisa por callbacks. En «Otras» se elige cuántas ventanas vecinas muestra la Übersicht, la altura de la banda de amplitud y el radio y el aumento de la lupa. | V3_F de "Herramienta Übersicht" |
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
| `Mayús+←` / `Mayús+→` | Desplazar media página |
| `Ctrl+←` / `Ctrl+→` | Desplazar una página entera |
| `Ctrl+-` / `Ctrl++` | Alejar / acercar: página × 2 / ÷ 2 |
| `Ctrl+0` | Mostrar el registro entero |
| `F6` / `Mayús+F6` | Pasar al panel siguiente / anterior |

Los cinco primeros son requisitos del pliego. **Los demás los agregó el
refactor de la interfaz**: los de desplazamiento y escala acompañan a la escala
de tiempo libre —las flechas solas siguen siendo la época, que es V1_F de
"Navegación"—, y F6 es de accesibilidad: sin él, llegar al selector de canales o
al scoring sin mouse obligaba a atravesar todos los controles con Tab. F6 salta
los paneles cerrados y los que no tienen nada que pueda recibir el foco, como el
de contexto, que se pinta a mano.

**Los menús muestran los atajos pero no los registran.** Leen este módulo con
`key_for()` y escriben la tecla después de un tabulador, que es como Qt dibuja
la columna del atajo. Registrarla también en la acción la volvería ambigua con
el `QShortcut`, y ante un atajo ambiguo Qt no ejecuta ninguno.

Los atajos de las fases **no** están en ese diccionario: dependen de la
nomenclatura activa y los arma `stage_shortcuts()` (W, 1, 2, 3, 4, R, M en R&K;
W, 1, 2, 3, R en AASM). Así, agregar o cambiar una fase no obliga a tocar la
tabla a mano.

Lo que sigue sin tecla es lo que no es una tecla. Un "deshacer", por ejemplo,
es un subsistema completo (historial de cambios del scoring y de las
anotaciones), y no está pedido.

## `grid.py`

La grilla está separada de `SignalView` porque **cambia por motivos distintos**:
la grilla depende de la preferencia visual del usuario, las curvas dependen de
los datos.

Tres fondos elegibles (`BackgroundStyle`, V2_F): sin líneas, sólo las de 3
segundos, o las dos densidades juntas (3 s y 0,5 s). **El primero se llamaba
"fondo blanco"** y dejó de ser cierto cuando el color pasó a depender del
esquema elegido: lo que esa opción hace es no dibujar ninguna línea.

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

**Ese umbral se midió en el refactor de la interfaz**, después de usarse como
supuesto desde el hito 6: el peor caso real —64 canales a 1000 Hz— tarda 92 ms,
cinco veces por debajo. Las tablas están en
[`docs/ARQUITECTURA.md`](../../docs/ARQUITECTURA.md). La conclusión práctica es
que **el dibujo de la ventana de 30 s no hay que optimizarlo**.

## Estado

Pendientes **0 stubs** en 0 módulos: la carpeta está terminada. Era el
[hito 6 del TODO](../../docs/TODO.md#hito-6-interfaz), y con él `python main.py`
abrió algo usable por primera vez.

**Pero sin stubs no era lo mismo que conectada.** El
[hito 9](../../docs/TODO.md#hito-9-lo-que-la-interfaz-no-consume) encontró seis
requisitos del pliego hechos en `tools/`, con sus tests en verde, que esta capa
no consumía: no se podía anotar, no había panel de Übersicht, el porcentaje de
ocupación no se mostraba, la lupa no ampliaba y el eje del histograma no
existía. Además `main_window` le pasaba a las herramientas la coordenada
vertical en unidades del gráfico donde `ViewerTool` documenta microvoltios.

La lección quedó en `tests/test_entrega.py`: **los gestos se mandan como
eventos de Qt al viewport, no llamando a la herramienta.** Llamando a la
herramienta, los mismos tests pasan en verde con el programa roto.

**El dibujo de esta capa no lleva tests**, y por eso se la mantiene delgada: no
se puede verificar sin mirar una pantalla, así que todo lo que valga la pena
verificar debería poder verificarse desde `core/`, `tools/` o `exporters/`.

**Lo que no dibuja sí los lleva, y hoy son casi todos**: veinte de los
veintidós módulos de la carpeta tienen test propio. Los dos que no —
`main_window.py` y `channel_selector.py`— figuran en `SIN_TEST_PROPIO`, y al
primero lo recorre `test_entrega.py` por la ventana. La frase de este párrafo
decía que ninguno llevaba test y se quedó vieja mientras la lista crecía: lo
encontró la auditoría del 19 de septiembre de 2026.

**La regla se acotó en el hito 6, y conviene saber por qué.** Se había fijado con
la carpeta vacía; al escribirla se vio que hay piezas que **no dibujan nada** y
que son justo donde algo se rompe en silencio:

- `shortcuts.py` deriva las teclas de fase de la nomenclatura. Una tabla
  desincronizada se manifiesta como una tecla que no hace nada.
- `grid.py` calcula posiciones. Acumular 0,5 sesenta veces corre la última línea
  del borde.
- Los cuatro conversores de `signal_view.py` son el **único** lugar del programa
  que traduce entre píxeles, segundos, fracción de ventana y muestras.
  Confundirlos produce números plausibles y equivocados.

**Se volvió a acotar con el refactor de la interfaz**, y por el mismo criterio:
`theme.py` y `preferences.py` tampoco dibujan. El primero es un valor inmutable
con una regla de ciclado, y el segundo es leer y escribir un archivo —donde lo
que importa no es el color sino que **un archivo roto no impida arrancar**—.
Los dos se testean sin `QApplication`.

Ésos se testean, con una `QApplication` sin pantalla cuando hace falta. El resto
—el dibujo— sigue sin testear, y esa parte de la regla no cambió.
