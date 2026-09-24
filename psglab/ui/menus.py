"""La barra de menú: qué acción vive en qué menú.

Se separó de `main_window.py` en el refactor de la interfaz, por el mismo motivo
por el que `grid.py` está separado de `signal_view.py`: **cambia por razones
distintas**. El menú cambia cuando se reorganiza la interfaz; la ventana, cuando
cambia lo que el programa hace.

## Qué hay en la barra

Un botón con el icono de una carpeta, que abre un registro, y después Scoring,
Escala de tiempo, Amplitud, Ver, Montaje, Filtrar, Analizar, Herramientas,
Configuración y Ayuda.

**«Archivo» dejó de ser un menú** porque sólo le quedaba una acción: un menú
de una entrada obliga a dos clics para lo que un botón hace en uno. Por el
mismo motivo **«Configuración» abre su ventana directamente**: el submenú de
esquemas repetía la solapa Colores de esa ventana.

**«Herramientas» lleva también los paneles** desde el hito 28. Hasta entonces
había un menú «Paneles» aparte, y los dos se pisaban: la Übersicht estaba en
los dos, y el hipnograma también, con dos nombres —«Histograma» en uno,
«Hipnograma» en el otro—. Además decían cosas distintas: la herramienta se
prende sola al abrir un registro y su panel arranca oculto, así que un menú la
mostraba tildada y el otro no. Ahora es un solo menú plano, en cuatro bloques
separados: los modos del mouse, los paneles de trabajo, los de análisis y
«Restaurar la disposición». Sigue a un clic, que es por lo que «Paneles» había
salido de «Ver» en el hito 23.

## Por qué los menús van por dominio

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

**Tampoco arma los modos del mouse del menú de herramientas.** Ésos se pueblan
recorriendo el registro —`available_tools()`— desde
`main_window._build_tools_menu()`, que es el punto de extensión que pide el
pliego: una herramienta nueva aparece sola. Acá se ponen los paneles, que
salen de `window.docks`, y aquél inserta los modos arriba de todo. **Es la
única vía para activar una herramienta**: la barra horizontal que repetía ese
menú debajo de la barra de menú se quitó por confusa.

Cubre del pliego: ningún ID. Es el cableado de la barra de menú; cada acción la
implementa el método de `main_window.py` al que llama.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QWidget

from psglab.config import AMPLITUDE_PRESETS_UV, VIEW_TIMESCALE_PRESETS
from psglab.exporters.scoring_formats import SCORING_FORMATS
from psglab.ui import theme
from psglab.ui.docks import ORDEN_DE_ANALISIS
from psglab.ui.grid import BackgroundStyle
from psglab.ui.icons import icon
from psglab.ui.shortcuts import key_for, readable_key

if TYPE_CHECKING:  # pragma: no cover - sólo para las anotaciones
    from collections.abc import Callable

    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QMenu, QMenuBar

    from psglab.ui.main_window import MainWindow

#: Lado del icono de abrir, en píxeles. El de Qt por omisión, 16, deja la
#: carpeta más chica que el texto de los menús de al lado.
TAMANO_DEL_ICONO = 20

#: La línea que separa «Abrir» de los menús: cuánto mide de alto y cuánto
#: aire le queda a cada lado.
ALTO_DEL_SEPARADOR = 20
ESPACIO_DEL_SEPARADOR = 8


def build_menus(window: "MainWindow") -> None:
    """Arma la barra de menú entera sobre la ventana principal.

    Deja en la ventana los dos `QAction` que el resto del programa necesita
    tocar después —`accion_eje_en_hora` y `accion_señal_original`—, el botón
    de abrir un registro, `open_button`, y el menú de herramientas,
    `tools_menu`, con los paneles ya puestos: `_build_tools_menu()` le inserta
    arriba los modos del mouse que salen del registro.

    **La barra de menú no es la nativa del sistema.** En macOS la nativa es la
    de arriba de la pantalla, que no muestra el botón de abrir ni deja una
    entrada sin submenú como «Configuración»: la barra quedaría distinta, y
    sin la vía principal para abrir un registro.
    """
    window.menuBar().setNativeMenuBar(False)
    _abrir(window)
    _identificador(window)
    _scoring(window)
    _escala_de_tiempo(window)
    _amplitud(window)
    _ver(window)
    _montaje(window)
    _filtrar(window)
    _analizar(window)
    _herramientas(window)
    _configuracion(window)
    _ayuda(window)
    _mostrar_atajos(window)


def _agregar(
    menu: "QMenu | QMenuBar", texto: str, slot: "Callable[[], object]"
) -> "QAction":
    """Agrega una acción y anota qué método de la ventana ejecuta.

    El nombre queda en `QAction.data()`, que es donde `_mostrar_atajos()` lo
    busca: Qt no deja preguntarle a una acción a qué está conectada.
    """
    accion = menu.addAction(texto, slot)
    accion.setData(getattr(slot, "__name__", None))
    return accion


def menu_path(window: "MainWindow", method_name: str) -> str | None:
    """La ruta de menú que ejecuta un método de la ventana, como la lee el usuario.

    Por ejemplo «Analizar › Espectro de la ventana». La usan los paneles vacíos
    para decir desde dónde se piden, y **se lee del menú armado y no se escribe
    a mano**: renombrar una entrada no puede dejar a un panel mandando al
    usuario a buscar algo que ya no existe.

    Returns:
        La ruta, o None si ninguna acción de la barra ejecuta ese método.
    """
    for de_la_barra in window.menuBar().actions():
        menu = de_la_barra.menu()
        if menu is None:
            continue
        for accion in menu.actions():
            if accion.data() == method_name:
                return f"{_legible(menu.title())} › {_legible(accion.text())}"
    return None


def _legible(texto: str) -> str:
    """El texto de un menú sin el atajo, sin el `&` del acelerador y sin «…»."""
    return texto.split("\t")[0].replace("&", "").rstrip("…").strip()


def _mostrar_atajos(window: "MainWindow") -> None:
    """Escribe al lado de cada acción el atajo que la ejecuta, si tiene uno.

    **Hasta la fase 9 los menús no mostraban ningún atajo**, y es lo primero
    que mira quien aprende un programa: la única forma de saber que Ctrl+O
    abría un registro era la ayuda.

    **El atajo no se registra en la acción, sólo se muestra.** Las teclas ya
    las instala `shortcuts.py` como `QShortcut`, y declararlas también en la
    acción las volvería ambiguas: ante un atajo ambiguo, Qt no ejecuta
    ninguno. Se usa el mismo mecanismo con que Qt dibuja los menús: lo que
    sigue a un tabulador en el texto va en la columna del atajo.
    """
    for accion_de_menu in window.menuBar().actions():
        _atajos_en(accion_de_menu.menu())


def _atajos_en(menu: "QMenu | None") -> None:
    if menu is None:
        return
    for accion in menu.actions():
        if accion.menu() is not None:
            _atajos_en(accion.menu())
            continue
        metodo = accion.data()
        tecla = key_for(metodo) if isinstance(metodo, str) else None
        if tecla is not None and "\t" not in accion.text():
            accion.setText(f"{accion.text()}\t{readable_key(tecla)}")


def _abrir(window: "MainWindow") -> None:
    """El botón con que se abre un registro, en la esquina izquierda de la barra.

    Ocupa el lugar de «Archivo», que ya no tenía otra acción: «Salir» se quitó
    porque lo hace la cruz de la ventana. `setAutoRaise()` es lo que le da el
    realce al pasar el mouse, y la hoja de estilo de `theme.py` lo repite con
    los colores del esquema.

    **El atajo va en el tooltip** y no como texto al lado, que es donde lo
    ponen los menús: un botón con icono no tiene columna de atajo.

    **Lleva la palabra «Abrir» desde el hito 36.** Con el icono solo, lo único
    que decía qué hacía era el tooltip, y en la esquina de una barra de menú
    una carpeta suelta se lee como decoración. Es además el primer control que
    usa quien abre el programa.
    """
    boton = QToolButton(window.menuBar())
    boton.setIcon(icon("abrir", theme.icon_ink(theme.current())))
    boton.setIconSize(QSize(TAMANO_DEL_ICONO, TAMANO_DEL_ICONO))
    boton.setText("Abrir")
    boton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    boton.setCursor(Qt.CursorShape.PointingHandCursor)
    boton.setAccessibleName("Abrir registro")
    tecla = key_for("open_recording_dialog")
    boton.setToolTip(
        "Abrir registro" + (f" ({readable_key(tecla)})" if tecla is not None else "")
    )
    boton.clicked.connect(window.open_recording_dialog)

    # **El botón y una línea vertical, no el botón solo.** «Abrir» no es un
    # menú más y sin la línea se leía como el primero de la fila. Va en un
    # contenedor porque la esquina de `QMenuBar` acepta un widget, uno solo.
    contenedor = QWidget(window.menuBar())
    fila = QHBoxLayout(contenedor)
    fila.setContentsMargins(0, 0, 0, 0)
    fila.setSpacing(ESPACIO_DEL_SEPARADOR)
    fila.addWidget(boton)
    separador = QFrame(contenedor)
    separador.setFrameShape(QFrame.Shape.VLine)
    separador.setFixedWidth(1)
    separador.setFixedHeight(ALTO_DEL_SEPARADOR)
    fila.addWidget(separador)
    window.menuBar().setCornerWidget(contenedor, Qt.Corner.TopLeftCorner)
    window.open_button = boton


def _identificador(window: "MainWindow") -> None:
    """Qué registro está abierto, en la otra esquina de la barra de menú.

    **No estaba en ningún lado** hasta el hito 36: el nombre del archivo, su
    frecuencia y cuántos canales tiene sólo se conseguían abriendo un panel de
    análisis o mirando el título de la ventana, que el sistema puede recortar.
    Con dos registros parecidos —la misma noche filtrada y sin filtrar— no
    había forma de saber cuál se estaba mirando.

    Es una lectura: el esquema le da la tipografía numérica, que es la que
    hace que la frecuencia y las horas no bailen.
    """
    etiqueta = QLabel("Sin registro")
    etiqueta.setProperty(theme.READOUT_PROPERTY, True)
    etiqueta.setAccessibleName("Registro abierto")
    etiqueta.setContentsMargins(0, 0, 10, 0)
    window.menuBar().setCornerWidget(etiqueta, Qt.Corner.TopRightCorner)
    window.recording_summary = etiqueta


def _scoring(window: "MainWindow") -> None:
    """El scoring: lo que el investigador produce, en los cuatro formatos.

    **Se separó de «Archivo» a propósito.** Abrir un registro es abrir el dato
    de entrada; importar y exportar un scoring es manejar el trabajo propio, y
    son las dos cosas que más veces por sesión se hacen.

    Las exportaciones se arman recorriendo `SCORING_FORMATS`, así que un
    formato nuevo aparece solo. **Anotaciones.txt e Informacion.txt ya no se
    ofrecen desde acá**, por decisión del 16 de septiembre de 2026:
    `MainWindow.export()` los sigue escribiendo, pero del menú no se piden.
    Anotaciones.txt tiene una salida de emergencia desde el hito 33 —el cartel
    del trabajo sin exportar ofrece guardarlas antes de perderlas—, que no es
    lo mismo que poder pedirlas cuando uno quiere.
    """
    scoring = window.menuBar().addMenu("&Scoring")
    _agregar(scoring, "&Importar scoring…", window.open_scoring_dialog)
    scoring.addSeparator()
    for extension in SCORING_FORMATS:
        accion = scoring.addAction(
            f"Exportar .{extension}…",
            lambda _=False, e=extension: window.export_scoring_dialog(e),
        )
        # El `.txt` es lo que exporta Ctrl+S: el mismo método, sin argumento.
        if extension == "txt":
            accion.setData("export_scoring_dialog")


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
    _agregar(escala, "&Registro entero", window.show_whole_recording)
    _agregar(escala, "&Personalizado…", window.ask_timescale)
    # Acercar y alejar a la mitad y al doble no están en el menú: agregaban
    # poco frente a la lista de escalas, y siguen en Ctrl++ y Ctrl+-.


def duration_text(seconds: float) -> str:
    """Una duración escrita como la leería un investigador: 200 ms, 30 s, 5 min, 1 h.

    **Es el único formateador de duraciones de la interfaz.** Hubo dos —uno acá
    para el menú y otro en la ventana principal para la barra de estado— y no
    coincidían: la misma página de 0,2 s era "0,2 s por página" en el menú y
    "Página: 200 ms" abajo. La ventana de configuración iba a ser el tercero.

    El separador decimal es la coma, como en todo el texto que ve el usuario.
    """
    if seconds < 1.0:
        return f"{seconds * 1000:g} ms".replace(".", ",")
    if seconds < 60.0:
        return f"{seconds:g} s".replace(".", ",")
    if seconds < 3600.0:
        return f"{seconds / 60:g} min".replace(".", ",")
    return f"{seconds / 3600:g} h".replace(".", ",")


def _pagina(segundos: float) -> str:
    """Cómo se lee una duración de página en el menú."""
    return f"{duration_text(segundos)} por página"


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
    _agregar(amplitud, "&Ajustar al panel", window.fit_amplitude_to_pane)
    _agregar(amplitud, "Ajustar el &desplazamiento", window.center_amplitude_offsets)
    _agregar(amplitud, "Desplazamiento a &cero", window.reset_amplitude_offsets)
    amplitud.addSeparator()
    for microvoltios in AMPLITUDE_PRESETS_UV:
        etiqueta = f"{microvoltios:g} µV por carril"
        amplitud.addAction(
            etiqueta, lambda _=False, uv=microvoltios: window.set_amplitude_scale(uv)
        )
    amplitud.addSeparator()
    _agregar(amplitud, "&Personalizado…", window.ask_amplitude_scale)
    amplitud.addSeparator()
    # Las mismas dos operaciones que las flechas Arriba y Abajo. Están en el
    # menú **además** de en el teclado porque el pliego pide las dos vías
    # (V2_P), y porque un menú es donde se descubre que el atajo existe.
    _agregar(amplitud, "Aumentar la amplitud", window.increase_amplitude)
    _agregar(amplitud, "Reducir la amplitud", window.decrease_amplitude)


def _ver(window: "MainWindow") -> None:
    """Lo que cambia cómo se ve la señal sin tocar el dato."""
    ver = window.menuBar().addMenu("&Ver")
    for estilo in BackgroundStyle:
        ver.addAction(
            estilo.value,
            lambda _=False, e=estilo: window.signal_view.grid.set_style(e),
        )

    ver.addSeparator()
    # **Los dos esquemas** (hito 35). Estaban en la solapa Colores de la ventana
    # de configuración, junto con la edición de cada color; al quedar sólo la
    # elección entre dos, una solapa entera para dos botones era más camino que
    # el que ahorraba. Acá quedan al lado de los tres fondos de grilla, que es
    # lo otro que cambia cómo se ve la señal.
    #
    # Son un grupo exclusivo, como los fondos: elegir uno destilda el otro sin
    # que nadie lo maneje a mano.
    grupo = QActionGroup(window)
    grupo.setExclusive(True)
    window.acciones_de_esquema = {}
    for nombre in theme.SCHEMES:
        accion = ver.addAction(nombre)
        accion.setCheckable(True)
        accion.setActionGroup(grupo)
        accion.triggered.connect(
            lambda _=False, n=nombre: window.set_color_scheme(theme.scheme_by_name(n))
        )
        window.acciones_de_esquema[nombre] = accion
    window.acciones_de_esquema[theme.current().name].setChecked(True)

    ver.addSeparator()
    # V2_F del histograma: el pliego pide poder elegir el eje.
    window.accion_eje_en_hora = ver.addAction("Histograma en hora real de la noche")
    window.accion_eje_en_hora.setCheckable(True)
    window.accion_eje_en_hora.toggled.connect(window.set_histogram_time_axis)


def _herramientas(window: "MainWindow") -> None:
    """Los paneles del menú de herramientas, y cómo volver a la disposición.

    El menú queda en cuatro bloques. **El primero, los modos del mouse, lo
    inserta después `_build_tools_menu()`** antes del separador con que arranca
    éste: salen del registro y acá no se conocen. Si no hubiera ninguno, `QMenu`
    no dibuja el separador que quedaría suelto arriba.

    **Se arma recorriendo los docks**, no con una lista escrita a mano: un panel
    nuevo aparece solo. `toggleViewAction()` es la acción que Qt ya mantiene
    sincronizada con el estado del panel, así que la tilde queda bien aunque el
    usuario lo cierre con la cruz. Los de análisis van aparte, en el orden de
    `docks.ORDEN_DE_ANALISIS`, que es el del flujo de trabajo.

    Una herramienta que tiene panel —la Übersicht, el hipnograma— **está acá
    una sola vez, como su panel**: ver `main_window._build_tools_menu()`.
    """
    menu = window.menuBar().addMenu("&Herramientas")
    window.tools_menu = menu
    de_analisis = {clave for clave, _ in ORDEN_DE_ANALISIS}

    menu.addSeparator()
    for clave, dock in window.docks.items():
        if clave not in de_analisis:
            menu.addAction(dock.toggleViewAction())
    menu.addSeparator()
    for clave, _ in ORDEN_DE_ANALISIS:
        menu.addAction(window.docks[clave].toggleViewAction())
    menu.addSeparator()
    _agregar(menu, "&Restaurar la disposición", window.restore_default_layout)
    # **Junto a restaurar, y no con los modos del mouse**: no es un modo sino
    # algo que vuelve a su estado inicial, como la disposición (hito 32).
    _agregar(menu, "Poner en &cero el contador de la lupa", window.reset_magnifier_count)


def _montaje(window: "MainWindow") -> None:
    """Las tres operaciones que cambian de qué canal viene cada fila.

    Van juntas y separadas de «Filtrar» porque responden a una pregunta
    distinta: no cómo se ve la señal sino **de dónde sale**. Las tres sustituyen
    el registro de la sesión, así que las tres habilitan "volver a la señal
    original", que por eso vive acá y no en «Analizar».
    """
    montaje = window.menuBar().addMenu("&Montaje")
    # **Queda en la ventana** para poder apagarlo entero mientras corre un
    # cálculo: las tres operaciones sustituyen el registro, y hacerlo debajo de
    # una ICA que se está ajustando dejaría una descomposición de una señal que
    # ya no está. Ver `MainWindow._reflejar_lo_que_se_puede_pedir()`.
    window.menu_montaje = montaje
    _agregar(montaje, "&Derivar canales…", window.derive_dialog)
    _agregar(montaje, "&Re-referenciar…", window.rereference_dialog)
    _agregar(montaje, "Referencia &promedio (EEG)", window.apply_average_reference)
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
    # Por lo mismo que «Montaje», y además porque ajustar la ICA es la otra
    # operación que corre en otro hilo: con una en curso no se puede pedir otra.
    window.menu_filtrar = filtrar
    _agregar(filtrar, "&Filtros por clase de canal…", window.show_filter_dialog)
    filtrar.addSeparator()
    _agregar(filtrar, "Componentes &independientes (ICA)…", window.show_ica_dialog)


def _analizar(window: "MainWindow") -> None:
    """Lo que mide sin modificar nada.

    La impedancia va arriba de todo y en su propio grupo: no es un análisis de
    la señal sino el control de calidad **previo** a confiar en cualquiera de
    los otros. Analizar la señal de un electrodo suelto da un resultado prolijo
    y falso, que es peor que uno feo.
    """
    analizar = window.menuBar().addMenu("&Analizar")
    _agregar(analizar, "&Impedancia de los electrodos…", window.show_impedance_dialog)
    analizar.addSeparator()
    _agregar(analizar, "&Espectro de la ventana…", window.show_psd_dialog)
    _agregar(analizar, "&Complejidad de la noche…", window.show_complexity_dialog)
    _agregar(analizar, "Conectividad de la &ventana…", window.show_connectivity_dialog)
    # **Queda en la ventana** porque hay que poder apagarla: es la única que
    # arranca un cálculo en otro hilo, y con uno en curso no se puede pedir
    # otro. Ver `MainWindow._reflejar_lo_que_se_puede_pedir()`.
    window.accion_conectividad_de_la_noche = _agregar(
        analizar, "Conectividad de la &noche…", window.show_connectivity_night_dialog
    )


def _configuracion(window: "MainWindow") -> None:
    """Las preferencias del usuario: un clic abre su ventana.

    Es una entrada de la barra sin submenú. Tenía uno con «Configuración…» y
    los esquemas de color, que repetían la solapa Colores de esa misma ventana,
    donde además se ve el esquema antes de elegirlo.
    """
    _agregar(window.menuBar(), "&Configuración", window.show_settings_dialog)


def _ayuda(window: "MainWindow") -> None:
    ayuda = window.menuBar().addMenu("A&yuda")
    _agregar(ayuda, "&Atajos de teclado", window._show_shortcuts)
