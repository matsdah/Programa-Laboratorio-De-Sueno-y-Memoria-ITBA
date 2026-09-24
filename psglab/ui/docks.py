"""Los paneles acoplables de la ventana principal.

Antes del refactor la ventana era una columna rígida: el selector de canales y
la señal arriba, y debajo el panel de contexto, el de scoring, la navegación y
el hipnograma, cada uno con su altura fija. El investigador no podía agrandar la
señal a costa del hipnograma, ni cerrar el selector de canales, ni sacar el
scoring a otra pantalla. Y los seis paneles de análisis eran ventanas sueltas
que tapaban la señal justo cuando había que mirarla.

Ahora **la señal es el widget central y todo lo demás es un `QDockWidget`**: se
mueve, se apila en solapas, se cierra y se saca a otra pantalla.

**La disposición no se recuerda entre aperturas**, por decisión del hito 24:
el programa abre siempre con la vista de abajo, y lo que el usuario arme vale
hasta que lo cierre. Hasta ese hito se guardaba al cerrar.

## El nombre del atributo no cambió

Los seis paneles de análisis siguen colgando de la ventana como `psd_dialog`,
`metric_dialog` y compañía, aunque ya no sean `QDialog`. **No es pereza**:
`QDockWidget` responde a `windowTitle()`, `show()`, `hide()` e `isVisible()`
igual que un diálogo, así que los ocho tests de entrega que preguntan por el
título de esas ventanas siguieron pasando sin tocarse. Renombrarlos habría
cambiado ocho tests para no ganar nada; el sufijo dejó de ser literal y pasó a
significar "el contenedor del panel", que es lo que siempre quiso decir.

## Qué arranca visible

**La señal, el selector de canales y el hipnograma.** Hasta el hito 24
arrancaban abiertos también el scoring y el contexto, y entre los tres le
quitaban a la señal un cuarto de la pantalla; se abren desde «Herramientas».
Scorear no los necesita: las fases y el arousal tienen su tecla.

**El hipnograma volvió en el hito 64**, solo, como una tira de
`ALTO_DEL_HIPNOGRAMA` a todo el ancho de abajo. En los programas de scoring es
lo único que está siempre a la vista: ubica la noche de un vistazo y muestra
lo que se va puntuando, que la franja de posición hace a medias porque no
tiene los niveles de las fases.

Los seis de análisis arrancan ocultos y los abre la acción del menú que los
calcula: un panel de conectividad vacío ocupando media pantalla desde el
arranque es ruido, no información.

Cubre del pliego: ningún ID. Es la disposición de la ventana; cada panel cubre
lo suyo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDockWidget, QWidget

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from psglab.ui.main_window import MainWindow

#: Cuánto mide de alto el hipnograma. Es la altura que tenía en la columna
#: rígida y se conserva: la curva escalonada de una noche no necesita más, y
#: dejarla crecer le come lugar a la señal.
ALTO_DEL_HIPNOGRAMA: Final[int] = 140

#: Con cuánto ancho abre el panel de canales, en píxeles. Es el del diseño, y
#: alcanza para un nombre de canal con su chip de clase al lado.
ANCHO_DE_CANALES: Final[int] = 212

#: Cómo se reparten el ancho los tres paneles de abajo, en proporción:
#: Übersicht, scoring e hipnograma. **El hipnograma se lleva la mayor parte**:
#: dibuja las 2650 ventanas de la noche entera, y en un tercio de la pantalla
#: las fases se amontonan hasta ser ilegibles. La Übersicht muestra tres
#: ventanas y no gana nada con más lugar.
ANCHOS_DE_ABAJO: Final[dict[str, int]] = {
    "overview": 250,
    "scoring": 400,
    "histogram": 900,
}

#: Los paneles de análisis, en el orden en que se apilan en solapas a la
#: derecha. El orden es el del flujo de trabajo, no el alfabético: primero el
#: control de calidad, después lo que mide, al final lo que modifica la señal.
ORDEN_DE_ANALISIS: Final[tuple[tuple[str, str], ...]] = (
    ("impedance", "Impedancia de los electrodos"),
    ("psd", "Espectro"),
    ("metric", "Métrica por ventana"),
    ("connectivity", "Conectividad"),
    ("filter", "Filtrar la señal"),
    ("ica", "Componentes independientes"),
)

#: Qué parte del ancho de la ventana se lleva la pila de análisis al abrirse.
#: **Hasta el hito 26 no había ninguna, y lo decidía Qt**: con el espectro
#: abierto la pila se quedaba con 640 px de una ventana de 1400, y a la señal
#: le quedaban 478 —358 con 1280—. El panel explicaba una señal que ya casi no
#: se veía. Con un 30 % la señal conserva unos 700 px con 1400 y 620 con 1280,
#: medido con `tests/medir_reparto.py`. El mínimo del panel manda si es mayor:
#: el de Impedancia, el más ancho de los seis, es de 380.
FRACCION_DE_ANALISIS: Final[float] = 0.30


def nuevo_dock(
    window: "MainWindow",
    titulo: str,
    contenido: QWidget,
    areas: Qt.DockWidgetArea,
) -> QDockWidget:
    """Envuelve un widget en un panel acoplable y se lo cuelga a la ventana.

    Args:
        titulo: lo que se lee en la barra del panel, y lo que devuelve
            `windowTitle()`.
        contenido: el widget que va adentro.
        areas: en qué bordes de la ventana se lo puede soltar. Se restringe a
            propósito: dejar caer el hipnograma en el borde izquierdo lo deja
            de 200 píxeles de ancho y una curva de 960 ventanas ahí no se lee.
    """
    dock = QDockWidget(titulo, window)
    # Sin nombre de objeto, `saveState()` no puede identificarlo y la
    # disposición no se restaura: Qt lo avisa por consola y sigue, que es la
    # peor combinación posible.
    dock.setObjectName(f"dock-{titulo}")
    dock.setAllowedAreas(areas)
    dock.setWidget(contenido)
    # **El nombre que lee un lector de pantalla.** Sin él, un lector anuncia
    # "grupo" o nada al llegar al panel. El título ya dice lo que es.
    if not contenido.accessibleName():
        contenido.setAccessibleName(titulo)
    return dock


def build_docks(window: "MainWindow") -> None:
    """Ubica todos los paneles alrededor de la señal.

    Deja en la ventana un atributo por dock, y `docks` con todos ellos por
    nombre, que es lo que usa el menú «Herramientas» para poder mostrarlos y
    ocultarlos sin conocerlos uno por uno.
    """
    window.setCentralWidget(window.signal_view)
    window.docks = {}

    _trabajo(window)
    _analisis(window)


def _trabajo(window: "MainWindow") -> None:
    """Los cuatro que se usan al scorear. Sólo el de canales arranca visible."""
    izquierda = Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
    abajo = Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea

    window.channels_dock = nuevo_dock(window, "Canales", window.channel_selector, izquierda)
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window.channels_dock)
    # **Se le pide un ancho y no se le fija un máximo**: el usuario lo puede
    # agrandar. Sin pedirlo, Qt le da lo que salga del `sizeHint` de la lista,
    # que con los nombres de canal de un registro real se lleva un cuarto de la
    # pantalla para una columna de casillas.
    window.resizeDocks(
        [window.channels_dock], [ANCHO_DE_CANALES], Qt.Orientation.Horizontal
    )

    # **«Contexto» y no «Übersicht»** (hito 64): era el único rótulo en alemán
    # de un programa en español, y su propio tooltip ya lo llamaba contexto.
    # El menú conserva el nombre del pliego entre paréntesis, para que quien lo
    # busque por ese nombre lo encuentre.
    window.overview_dock = nuevo_dock(window, "Contexto", window.overview_panel, abajo)
    window.overview_dock.toggleViewAction().setText("Contexto (Übersicht)")
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window.overview_dock)

    window.scoring_dock = nuevo_dock(window, "Scoring", window.scoring_panel, abajo)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window.scoring_dock)

    window.histogram_view.setMaximumHeight(ALTO_DEL_HIPNOGRAMA)
    window.histogram_dock = nuevo_dock(window, "Hipnograma", window.histogram_view, abajo)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window.histogram_dock)

    for nombre, dock in (
        ("channels", window.channels_dock),
        ("overview", window.overview_dock),
        ("scoring", window.scoring_dock),
        ("histogram", window.histogram_dock),
    ):
        window.docks[nombre] = dock

    # Se ocultan después de acomodarlos, para que al mostrarlos desde «Herramientas»
    # vuelvan al borde de abajo y lado a lado. **El hipnograma no** (hito 64):
    # ver «Qué arranca visible».
    for clave in ANCHOS_DE_ABAJO:
        if clave != "histogram":
            window.docks[clave].hide()
        # **Cada vez que uno aparece se vuelve a repartir el ancho.** Qt no
        # recuerda un reparto pedido mientras estaban ocultos: los mostraba
        # con lo que le sobrara a cada uno, y el hipnograma quedaba el más
        # angosto de los tres.
        window.docks[clave].toggleViewAction().toggled.connect(
            lambda visible: visible and repartir_abajo(window)
        )


def repartir_abajo(window: "MainWindow") -> None:
    """Reparte el ancho entre los paneles de abajo que estén a la vista.

    Según `ANCHOS_DE_ABAJO`, y sólo entre los que están acoplados: uno suelto
    en otra pantalla no comparte el borde con nadie.

    **Es una proporción, no una garantía.** Qt atiende primero el mínimo de cada
    panel —el del scoring es el mayor— y reparte el resto entre los demás.
    Medido con el registro de prueba: con 1400 px, 225, 360 y 811 px, y con
    1280, 206, 329 y 741, con cualquiera de las dos nomenclaturas. Ahí manda la
    proporción entera, porque ningún panel toca su mínimo.

    **El mínimo del scoring recién aparece debajo de unos 1210 px**: es de
    312 px con Rechtschaffen y Kales y 224 con AASM, que es lo que mide su fila
    de fases desde que las fases van en su propia fila (hito 26). Con 1170 px
    el reparto ya es 186, 312 y 668. Por la misma cuenta, sin medir, el
    hipnograma sigue siendo el más ancho hasta unos 715 px de ventana.

    Así se llegó acá: hasta el hito 24 los mínimos del scoring y de la
    Übersicht eran de 690 y 480 px, y el hipnograma recibía unos 230; hasta el
    26 el scoring iba en una sola fila con un mínimo de 464 px, más de lo que
    la proporción le pedía, y el hipnograma se quedaba en 729 con 1400 px y en
    635 con 1280.

    Esos números **dependen de la máquina**: los mínimos salen de métricas de
    fuente, y con otro escalado de pantalla son otros. Para volver a sacarlos
    está `tests/medir_reparto.py`, que no es un test por ese mismo motivo.
    """
    visibles = [
        (window.docks[clave], ancho)
        for clave, ancho in ANCHOS_DE_ABAJO.items()
        if not window.docks[clave].isHidden() and not window.docks[clave].isFloating()
    ]
    if len(visibles) < 2:
        return
    window.resizeDocks(
        [dock for dock, _ in visibles],
        [ancho for _, ancho in visibles],
        Qt.Orientation.Horizontal,
    )


def repartir_derecha(window: "MainWindow") -> None:
    """Le da a la pila de análisis su parte del ancho de la ventana.

    La parte es `FRACCION_DE_ANALISIS`, y sólo si la pila está acoplada: suelta
    en otra pantalla no le quita lugar a la señal. Los seis paneles están
    apilados en solapas, así que pedirle el ancho a uno es pedírselo a la pila.

    Se vuelve a pedir cada vez que se abre un panel de análisis, aunque la pila
    ya estuviera a la vista: es la misma regla que abajo, y por el mismo motivo.
    Un ancho que el usuario haya arrastrado a mano se respeta hasta ese momento.
    """
    acoplados = [
        window.docks[clave]
        for clave, _ in ORDEN_DE_ANALISIS
        if not window.docks[clave].isHidden() and not window.docks[clave].isFloating()
    ]
    if not acoplados:
        return
    ancho = round(window.width() * FRACCION_DE_ANALISIS)
    window.resizeDocks([acoplados[0]], [ancho], Qt.Orientation.Horizontal)


def _analisis(window: "MainWindow") -> None:
    """Los seis de la Parte 2, apilados en solapas a la derecha y ocultos.

    **Se apilan y no se reparten**: los seis abiertos a la vez no entran en
    ninguna pantalla, y son alternativas entre sí —nadie mira el espectro y la
    conectividad al mismo tiempo— así que las solapas son la forma correcta.
    """
    derecha = Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea

    anterior: QDockWidget | None = None
    for clave, titulo in ORDEN_DE_ANALISIS:
        panel = getattr(window, f"{clave}_panel")
        dock = nuevo_dock(window, titulo, panel, derecha)
        window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        if anterior is not None:
            window.tabifyDockWidget(anterior, dock)
        dock.hide()
        # Como los de abajo: el ancho se pide cada vez que uno aparece, porque
        # Qt no recuerda lo pedido mientras la pila estaba oculta. **Pero en la
        # vuelta siguiente del ciclo de eventos, no en el momento.** La primera
        # vez que la pila aparece, Qt todavía no la ubicó cuando llega el aviso,
        # y su primer acomodo pisa lo pedido: la pila quedaba en los 600 px que
        # pide el gráfico. Abajo no pasa porque, cuando aparece el segundo
        # panel, el primero ya está ubicado.
        dock.toggleViewAction().toggled.connect(
            lambda visible: visible and QTimer.singleShot(0, lambda: repartir_derecha(window))
        )
        # **El nombre del atributo conserva el sufijo `_dialog`.** Ver la
        # explicación de arriba: cambiarlo costaría ocho tests y no ganaría
        # nada.
        setattr(window, f"{clave}_dialog", dock)
        window.docks[clave] = dock
        anterior = dock
