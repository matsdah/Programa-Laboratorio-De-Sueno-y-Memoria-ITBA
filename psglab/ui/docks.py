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

**Sólo la señal y el selector de canales.** Hasta el hito 24 arrancaban
abiertos también el scoring, el hipnograma y la Übersicht, y entre los tres le
quitaban a la señal un cuarto de la pantalla; se abren desde «Paneles». Scorear
no los necesita: las fases y el arousal tienen su tecla.

Los seis de análisis arrancan ocultos y los abre la acción del menú que los
calcula: un panel de conectividad vacío ocupando media pantalla desde el
arranque es ruido, no información.

Cubre del pliego: ningún ID. Es la disposición de la ventana; cada panel cubre
lo suyo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QWidget

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from psglab.ui.main_window import MainWindow

#: Cuánto mide de alto el hipnograma. Es la altura que tenía en la columna
#: rígida y se conserva: la curva escalonada de una noche no necesita más, y
#: dejarla crecer le come lugar a la señal.
ALTO_DEL_HIPNOGRAMA: Final[int] = 140

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
    nombre, que es lo que usa el menú «Paneles» para poder mostrarlos y
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

    window.overview_dock = nuevo_dock(window, "Übersicht", window.overview_panel, abajo)
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

    # Se ocultan después de acomodarlos, para que al mostrarlos desde «Paneles»
    # vuelvan al borde de abajo y lado a lado.
    for clave in ANCHOS_DE_ABAJO:
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

    **Es una proporción, no una garantía.** Qt respeta el mínimo de cada
    panel —el del scoring es el mayor: unos 380 px con AASM y 460 con
    Rechtschaffen y Kales— y reparte el resto. Hasta el hito 24 esos mínimos
    eran de 480 y 690 px, y en una pantalla de 1400 el hipnograma recibía
    unos 230.
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
        # **El nombre del atributo conserva el sufijo `_dialog`.** Ver la
        # explicación de arriba: cambiarlo costaría ocho tests y no ganaría
        # nada.
        setattr(window, f"{clave}_dialog", dock)
        window.docks[clave] = dock
        anterior = dock
