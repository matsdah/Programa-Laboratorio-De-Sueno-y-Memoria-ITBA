"""La barra de menú: qué acción vive en qué menú.

Se separó de `main_window.py` en el refactor de la interfaz, por el mismo motivo
por el que `grid.py` está separado de `signal_view.py`: **cambia por razones
distintas**. El menú cambia cuando se reorganiza la interfaz; la ventana, cuando
cambia lo que el programa hace.

## Por qué nueve menús y no cinco

Había cinco —Archivo, Ver, Herramientas, Análisis, Ayuda— y `Análisis` se había
convertido en el cajón de todo lo de la Parte 2: filtrar, derivar,
re-referenciar, el espectro, la complejidad, la conectividad, la ICA, la
impedancia y "volver a la señal original", separados apenas por tres líneas.
Nueve entradas heterogéneas en un solo menú obligan a leerlo entero cada vez.

La división es **por dominio, no por sección del pliego**: `Montaje` reúne las
tres operaciones que cambian de qué canal viene cada fila, `Filtrar` las que
cambian la forma de la señal, `Analizar` las que no la modifican y sólo miden.
Esa distinción no es estética: las dos primeras sustituyen el `Recording` de la
sesión y por eso habilitan "volver a la señal original", y las terceras no.

## Lo que este módulo no hace

**No implementa ninguna acción.** Cada entrada llama a un método de la ventana
principal, y ahí es donde vive lo que hace. Si estás por escribir lógica acá,
va en otro archivo.

**Tampoco arma el menú de herramientas.** Ése se puebla recorriendo el registro
—`available_tools()`— desde `main_window._build_toolbar()`, y es el punto de
extensión que pide el pliego: una herramienta nueva aparece sola. Acá sólo se
crea el menú vacío que aquél después llena.

Cubre del pliego: ningún ID. Es el cableado de la barra de menú; cada acción la
implementa el método de `main_window.py` al que llama.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from psglab.config import AMPLITUDE_PRESETS_UV, VIEW_TIMESCALE_PRESETS
from psglab.exporters import DEFAULT_FILENAMES
from psglab.ui import theme
from psglab.ui.grid import BackgroundStyle

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from psglab.ui.main_window import MainWindow


def build_menus(window: "MainWindow") -> None:
    """Arma la barra de menú entera sobre la ventana principal.

    Deja en la ventana los dos `QAction` que el resto del programa necesita
    tocar después —`accion_eje_en_hora` y `accion_señal_original`— y el menú
    vacío de herramientas, `tools_menu`, que `_build_toolbar()` puebla desde el
    registro.
    """
    _archivo(window)
    _sesion(window)
    _escala_de_tiempo(window)
    _amplitud(window)
    _ver(window)
    _montaje(window)
    _filtrar(window)
    _analizar(window)
    window.tools_menu = window.menuBar().addMenu("&Herramientas")
    _configuracion(window)
    _ayuda(window)


def _archivo(window: "MainWindow") -> None:
    """Abrir un registro y salir. Nada más: lo demás se mudó a «Sesión»."""
    archivo = window.menuBar().addMenu("&Archivo")
    archivo.addAction("&Abrir registro…", window.open_recording_dialog)
    archivo.addSeparator()
    archivo.addAction("&Salir", window.close)


def _sesion(window: "MainWindow") -> None:
    """El scoring y las anotaciones: lo que el investigador produce.

    **Se separó de «Archivo» a propósito.** Abrir un registro es abrir el dato
    de entrada; importar y exportar un scoring es manejar el trabajo propio, y
    son las dos cosas que más veces por sesión se hacen. Mezclarlas obligaba a
    buscar "Exportar Scoring.txt" entre las acciones de apertura.
    """
    sesion = window.menuBar().addMenu("&Sesión")
    sesion.addAction("&Importar scoring…", window.open_scoring_dialog)
    sesion.addSeparator()
    # V4_F pide poder exportar **uno solo** de los tres, así que son tres
    # acciones y no un único "Exportar todo".
    for kind, nombre in DEFAULT_FILENAMES.items():
        sesion.addAction(
            f"Exportar {nombre}…", lambda _=False, k=kind: window._export_dialog(k)
        )


def _escala_de_tiempo(window: "MainWindow") -> None:
    """Cuánto registro entra en la pantalla.

    **Es lo único del refactor que separa dos cosas que el programa tenía
    pegadas**: la época de scoring, que el pliego fija en 30 s y no cambia, y la
    página visible, que ahora va de diez milisegundos al registro entero.

    Las escalas ofrecidas están acotadas a polisomnografía y no son las
    veintiocho de un visor universal: veinte de aquéllas no tienen sentido en un
    registro de sueño, y un menú donde la mayoría no sirve obliga a buscar la
    que sí. La época aparece en la lista como una más, que es lo que es.
    """
    escala = window.menuBar().addMenu("&Escala de tiempo")
    for segundos in VIEW_TIMESCALE_PRESETS:
        escala.addAction(
            _pagina(segundos),
            lambda _=False, s=segundos: window.set_timescale(s),
        )
    escala.addSeparator()
    escala.addAction("&Registro entero", window.show_whole_recording)
    escala.addAction("Definida por el &usuario…", window.ask_timescale)
    escala.addSeparator()
    escala.addAction("&Acercar (página ÷ 2)", window.halve_timescale)
    escala.addAction("A&lejar (página × 2)", window.double_timescale)


def _pagina(segundos: float) -> str:
    """Cómo se lee una duración de página en el menú."""
    if segundos < 60.0:
        return f"{segundos:g} s por página".replace(".", ",")
    if segundos < 3600.0:
        return f"{segundos / 60:g} min por página".replace(".", ",")
    return f"{segundos / 3600:g} h por página".replace(".", ",")


def _amplitud(window: "MainWindow") -> None:
    """Todo lo que cambia el tamaño vertical de la señal.

    **Las entradas hablan de microvoltios por carril y no de "amplitud".** Es
    deliberado: el número que el programa guarda es cuántos µV representa la
    altura del carril, así que subirlo **achica** la onda. Un menú que dijera
    "Amplitud 100" y escribiera 100 haría lo contrario de lo que el usuario
    espera la mitad de las veces.

    El alcance de todas es el mismo que el de las flechas del teclado: los
    canales seleccionados, o todos los visibles si no hay ninguno seleccionado.
    Lo resuelve `Session`, no este menú.
    """
    amplitud = window.menuBar().addMenu("A&mplitud")
    amplitud.addAction("&Ajustar al panel", window.fit_amplitude_to_pane)
    amplitud.addAction("Ajustar el &desplazamiento", window.center_amplitude_offsets)
    amplitud.addAction("Desplazamiento a &cero", window.reset_amplitude_offsets)
    amplitud.addSeparator()
    for microvoltios in AMPLITUDE_PRESETS_UV:
        etiqueta = f"{microvoltios:g} µV por carril"
        amplitud.addAction(
            etiqueta, lambda _=False, uv=microvoltios: window.set_amplitude_scale(uv)
        )
    amplitud.addSeparator()
    amplitud.addAction("Definida por el &usuario…", window.ask_amplitude_scale)
    amplitud.addSeparator()
    # Las mismas dos operaciones que las flechas Arriba y Abajo. Están en el
    # menú **además** de en el teclado porque el pliego pide las dos vías
    # (V2_P), y porque un menú es donde se descubre que el atajo existe.
    amplitud.addAction("Aumentar la amplitud", window.increase_amplitude)
    amplitud.addAction("Reducir la amplitud", window.decrease_amplitude)


def _ver(window: "MainWindow") -> None:
    """Lo que cambia cómo se ve la señal sin tocar el dato."""
    ver = window.menuBar().addMenu("&Ver")
    for estilo in BackgroundStyle:
        ver.addAction(
            estilo.value,
            lambda _=False, e=estilo: window.signal_view.grid.set_style(e),
        )

    ver.addSeparator()
    # **El submenú se arma recorriendo los docks**, no con una lista escrita a
    # mano: un panel nuevo aparece solo. `toggleViewAction()` es la acción que
    # Qt ya mantiene sincronizada con el estado del panel, así que la tilde
    # queda bien aunque el usuario lo cierre con la cruz.
    paneles = ver.addMenu("&Paneles")
    for dock in window.docks.values():
        paneles.addAction(dock.toggleViewAction())
    ver.addAction("&Restaurar la disposición", window.restore_default_layout)

    ver.addSeparator()
    # V2_F del histograma: el pliego pide poder elegir el eje.
    window.accion_eje_en_hora = ver.addAction("Histograma en hora real de la noche")
    window.accion_eje_en_hora.setCheckable(True)
    window.accion_eje_en_hora.toggled.connect(window.set_histogram_time_axis)


def _montaje(window: "MainWindow") -> None:
    """Las tres operaciones que cambian de qué canal viene cada fila.

    Van juntas y separadas de «Filtrar» porque responden a una pregunta
    distinta: no cómo se ve la señal sino **de dónde sale**. Las tres sustituyen
    el registro de la sesión, así que las tres habilitan "volver a la señal
    original", que por eso vive acá y no en «Analizar».
    """
    montaje = window.menuBar().addMenu("&Montaje")
    montaje.addAction("&Derivar canales…", window.derive_dialog)
    montaje.addAction("&Re-referenciar…", window.rereference_dialog)
    montaje.addAction("Referencia &promedio (EEG)", window.apply_average_reference)
    montaje.addSeparator()
    window.accion_señal_original = montaje.addAction(
        "&Volver a la señal original", window.restore_original_recording
    )
    window.accion_señal_original.setEnabled(False)


def _filtrar(window: "MainWindow") -> None:
    """Lo que cambia la forma de la señal.

    La ICA está acá y no en «Analizar» aunque parezca un análisis: ajustar la
    descomposición no cambia nada, pero aplicarla **sustituye la señal**, y es
    la operación menos reversible del programa. Agruparla con el filtrado es
    decirle al usuario a qué familia pertenece antes de que la use.
    """
    filtrar = window.menuBar().addMenu("&Filtrar")
    filtrar.addAction("&Filtros por clase de canal…", window.show_filter_dialog)
    filtrar.addSeparator()
    filtrar.addAction("Componentes &independientes (ICA)…", window.show_ica_dialog)


def _analizar(window: "MainWindow") -> None:
    """Lo que mide sin modificar nada.

    La impedancia va arriba de todo y en su propio grupo: no es un análisis de
    la señal sino el control de calidad **previo** a confiar en cualquiera de
    los otros. Analizar la señal de un electrodo suelto da un resultado prolijo
    y falso, que es peor que uno feo.
    """
    analizar = window.menuBar().addMenu("&Analizar")
    analizar.addAction("&Impedancia de los electrodos…", window.show_impedance_dialog)
    analizar.addSeparator()
    analizar.addAction("&Espectro de la ventana…", window.show_psd_dialog)
    analizar.addAction("&Complejidad de la noche…", window.show_complexity_dialog)
    analizar.addAction("Conectividad de la &ventana…", window.show_connectivity_dialog)


def _configuracion(window: "MainWindow") -> None:
    """Las preferencias del usuario.

    El submenú se arma recorriendo `theme.SCHEMES`, así que agregar un esquema
    no obliga a tocar este archivo: es el mismo criterio que hace que una
    herramienta o un formato de archivo nuevos aparezcan solos.
    """
    configuracion = window.menuBar().addMenu("&Configuración")
    esquemas = configuracion.addMenu("Esquema de &color")
    for nombre, esquema in theme.SCHEMES.items():
        esquemas.addAction(nombre, lambda _=False, e=esquema: window.set_color_scheme(e))


def _ayuda(window: "MainWindow") -> None:
    ayuda = window.menuBar().addMenu("A&yuda")
    ayuda.addAction("&Atajos de teclado", window._show_shortcuts)
