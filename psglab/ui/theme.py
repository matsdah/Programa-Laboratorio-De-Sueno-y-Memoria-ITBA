"""Esquemas de color del programa: qué color tiene cada cosa que se dibuja.

Hasta el refactor de la interfaz no existía ningún concepto de tema. El fondo se
fijaba una sola vez para todo el programa con tres `pg.setConfigOption` en
`psglab/app.py`, y los demás colores vivían como constantes privadas repartidas
en cinco módulos. Cambiar de aspecto era editar código en seis lugares.

**Los colores no salen de `psglab/config.py`, y es a propósito.** Ese archivo
guarda lo que fija el pliego, y el pliego no dice nada de colores: pide tres
fondos de grilla y nada más. Con qué color se distingue un canal de otro es del
programa, no del requisito, y por eso vive acá.

Un esquema es un valor inmutable y **no se puede editar**: se elige uno de los
dos. Hasta el hito 35 eran ocho y cada color se cambiaba uno por uno, así que
el programa tenía infinitos aspectos posibles y ninguno garantizado —el control
de contraste sólo alcanzaba a los de fábrica—. Dos esquemas verificados y
ninguna perilla es menos programa y más garantía.

Cubre del pliego: ningún ID. Es infraestructura de presentación; el único
requisito visual que el pliego fija, los tres fondos de grilla, lo cubre
`psglab/ui/grid.py`.
"""

from dataclasses import dataclass
from typing import Final

import pyqtgraph as pg

from psglab.utils.errors import UnknownColorSchemeError

#: Paleta de la que salen los colores de canal sobre fondo claro. Son las
#: versiones oscurecidas de los seis de `psd_panel.py` y de las clases de
#: anotación: el mismo orden, para que un canal no cambie de color según el
#: panel en el que se lo mire, pero con contraste suficiente sobre blanco.
_PALETA_CLARA: Final[tuple[str, ...]] = (
    "#1b4f9c",
    "#3f7a2e",
    "#9c7a1b",
    "#9c4a1b",
    "#6b1b9c",
    "#1b7a72",
)

#: La misma idea sobre fondo oscuro, donde los colores tienen que ser claros
#: para separarse del fondo. Es el orden de la referencia: amarillo, verde,
#: blanco, rojo, cian, magenta, azul.
_PALETA_OSCURA: Final[tuple[str, ...]] = (
    "#ffff00",
    "#00e000",
    "#e0e0e0",
    "#ff4040",
    "#00e0e0",
    "#ff40ff",
    # **Era `#6060ff`**, y sobre el gris del esquema oscuro daba un contraste
    # de 2,42: el canal azul casi no se distinguía del fondo. Éste da 3,39.
    "#8080ff",
)

#: El color de cada fase sobre fondo claro. **La profundidad es la
#: luminosidad**: el sueño recorre un mismo azul de claro a oscuro —S1/N1 hasta
#: S4/N3— y las dos fases que no son un punto de esa escala salen de ella, la
#: vigilia en ámbar y el REM en morado. Movement Time es gris: no es sueño.
#:
#: Es una tabla y no una paleta por posición como `signal_palette` porque acá
#: el color **significa** algo: una fase tiene que verse igual en el hipnograma,
#: en la franja de posición y en su botón, y las dos nomenclaturas comparten la
#: escala —S2 y N2 son el mismo azul— para que cambiar de nomenclatura no
#: cambie de colores.
_FASES_CLARAS: Final[tuple[tuple[str, str], ...]] = (
    ("W", "#9e5a22"),
    ("REM", "#9c4a78"),
    ("R", "#9c4a78"),
    ("S1", "#55779f"),
    ("N1", "#55779f"),
    ("S2", "#3e6ba3"),
    ("N2", "#3e6ba3"),
    ("S3", "#2b5689"),
    ("S4", "#21497a"),
    ("N3", "#21497a"),
    ("MT", "#5b6169"),
)

#: La misma escala sobre fondo oscuro, donde la profundidad se lee al revés:
#: el sueño liviano es el azul más claro y el profundo el más saturado, porque
#: sobre negro un azul oscuro desaparece. Los contrastes están medidos contra
#: el fondo de `NOCTURNO` y contra su propio texto.
_FASES_OSCURAS: Final[tuple[tuple[str, str], ...]] = (
    ("W", "#e0a264"),
    ("REM", "#d081ac"),
    ("R", "#d081ac"),
    ("S1", "#9fbde4"),
    ("N1", "#9fbde4"),
    ("S2", "#7ba5d8"),
    ("N2", "#7ba5d8"),
    ("S3", "#6494cb"),
    ("S4", "#4f82be"),
    ("N3", "#5b8fc9"),
    ("MT", "#99a1ab"),
)

#: **Los tokens de forma del rediseño**: radio, alturas y espaciado de los
#: controles. Viven acá y no en un módulo aparte porque su único consumidor es
#: `stylesheet()`, que está diez líneas más abajo; un módulo propio costaría
#: fila en la trazabilidad, fila en el README de la carpeta, archivo de test y
#: dos filas más de tablas, a cambio de mover seis números.
#:
#: **No son colores y por eso no están en `ColorScheme`**: no cambian con el
#: esquema. Un botón mide lo mismo de noche que de día.
RADIO_DE_CONTROL: Final[int] = 7
RADIO_DE_TARJETA: Final[int] = 10
ALTO_DE_CONTROL: Final[int] = 30
PADDING_DE_CONTROL: Final[str] = "4px 12px"
#: El ancho del anillo con que se ve qué control tiene el foco del teclado. Es
#: un borde y no un `outline`: Qt no dibuja `outline` en la mayoría de los
#: widgets, así que un anillo escrito con él se perdería sin avisar.
ANILLO_DE_FOCO: Final[int] = 2

#: Contraste mínimo para texto, según WCAG 2.1 (criterio 1.4.3).
MIN_TEXT_CONTRAST: Final[float] = 4.5

#: La propiedad dinámica de Qt que marca una **lectura**: un rótulo que muestra
#: un número que cambia —la ventana actual, la hora de la noche, lo que informa
#: la herramienta activa—. La hoja de estilo la usa para darles a todas la
#: tipografía numérica del esquema, si tiene una, sin que el esquema tenga que
#: conocer los widgets por nombre.
READOUT_PROPERTY: Final[str] = "lectura"

#: La propiedad con que un botón pide la tinta de lo que destruye. La usa
#: «Descartar» en el cartel del trabajo sin exportar: es el único control del
#: programa que pierde trabajo del investigador.
DESTRUCTIVO_PROPERTY: Final[str] = "destructivo"

#: La propiedad dinámica del botón **principal** de un panel o un cartel: el
#: que hace lo que el panel existe para hacer —«Aplicar», «Exportar…»—. Se
#: rellena con el acento, como en el prototipo (hito 55). El hito 44 había
#: sacado la regla, que entonces sólo usaba el botón de reproducir y lo volvía
#: un bloque oscuro en la barra; reproducir no la lleva.
PRIMARIO_PROPERTY: Final[str] = "primario"

#: Contraste mínimo para lo que se dibuja y hay que distinguir —curvas,
#: la paleta de canales—, según WCAG 2.1 (criterio 1.4.11). La grilla y la
#: línea de base quedan afuera a propósito: son referencias que tienen que
#: verse menos que la señal.
MIN_GRAPHIC_CONTRAST: Final[float] = 3.0


@dataclass(frozen=True)
class ColorScheme:
    """Qué color tiene cada elemento del programa.

    Inmutable por el mismo motivo que `Overlay` y `OccupancyLine`: se reparte
    entre seis widgets, y si alguno pudiera escribirle encima el resto quedaría
    dibujando con un esquema que ya no es el elegido, sin que nada avise.

    Attributes:
        name: cómo se llama el esquema para el usuario.
        background: fondo de todas las áreas de dibujo.
        foreground: ejes, ticks y texto de los gráficos.
        signals: color de las curvas de señal cuando **no** se varía por canal.
        vary_signal_colors: si cada canal toma un color distinto de la paleta.
        signal_palette: de dónde salen esos colores, en orden de canal.
        baseline: color de la línea de cero de cada canal, o None para no
            dibujarla. En la referencia se prende y apaga además de elegirse.
        coarse_grid: la línea de la grilla que el pliego llama "visible".
        fine_grid: la que el pliego llama "discreta". Más tenue a propósito:
            una grilla que compite con la señal estorba el scoring.
        accent: curva única, para los paneles que dibujan una sola serie.
        overview_background: fondo del panel de contexto.
        overview_current: relleno de la ventana actual en ese panel.
        overview_border: borde de las ventanas vecinas.
        overview_current_border: borde de la ventana actual.
        overview_text: número de ventana.
        chrome: fondo de la ventana —la barra de menú, la de estado, los
            paneles y sus títulos—, cuando es distinto del de las áreas de
            dibujo. **Vacío es «el mismo que `background`»**, y la hoja de
            estilo sale igual que si se lo hubiera escrito.
        numeric_font: la tipografía de las lecturas numéricas (ver
            `READOUT_PROPERTY`), o vacío para usar la de siempre. Va en el
            esquema y no aparte porque es parte del aspecto que el nombre del
            esquema promete, como los colores.
        control_border: el borde de lo que se toca —campos, botones, listas,
            tablas—, o vacío para usar `coarse_grid`. **Existe por WCAG 1.4.11**
            (hito 62): en un campo de texto el borde es lo único que dice dónde
            se escribe, y tiene que llegar a 3:1 contra el fondo del control y
            contra el de la ventana. El de la grilla no puede: la grilla tiene
            que ser tenue para no competir con la señal, y los dos compartían
            color, a 1,42 en Sereno y 1,53 en Nocturno.
        stage_colors: qué color tiene cada fase de sueño, como (valor de
            `SleepStage`, color). De acá salen el hipnograma, la franja de
            posición y los botones de fase. **Vacío significa «una sola
            tinta»**, que es como se dibujaba el hipnograma hasta el hito 34:
            los dos esquemas de hoy la traen, y el campo sigue admitiendo el
            vacío porque un esquema puede querer no distinguirlas —imprimir en
            blanco y negro, por ejemplo—.

    **No tiene los colores de las reglas ni del rectángulo del mouse**, que la
    referencia sí trae: todavía no hay nada que los dibuje. Entran con la
    herramienta de reglas, no antes. Un campo de configuración que no se
    consume es una promesa que el programa no cumple.
    """

    name: str
    background: str
    foreground: str
    signals: str
    vary_signal_colors: bool
    signal_palette: tuple[str, ...]
    baseline: str | None
    coarse_grid: str
    fine_grid: str
    accent: str
    overview_background: str
    overview_current: str
    overview_border: str
    overview_current_border: str
    overview_text: str
    chrome: str | None = None
    numeric_font: str | None = None
    danger: str | None = None
    control_border: str | None = None
    stage_colors: tuple[tuple[str, str], ...] = ()

    def color_for_channel(self, position: int) -> str:
        """El color que le toca al canal dibujado en esa posición vertical.

        Cicla la paleta, igual que `AnnotationSet.color_of()` con las clases:
        con más canales que colores dos van a repetir, y repetir es mejor que
        quedarse sin color.

        Args:
            position: índice del canal dentro de los visibles, desde 0.
        """
        if not self.vary_signal_colors or not self.signal_palette:
            return self.signals
        return self.signal_palette[position % len(self.signal_palette)]

    def color_for_stage(self, stage_value: str) -> str | None:
        """El color de una fase de sueño, o None si el esquema no tiene escala.

        **None no es un error**: es el esquema diciendo que las fases se
        dibujan con una sola tinta, como antes de que la escala existiera.
        Quien llama decide con qué —el hipnograma con su curva, el botón con
        el color de los demás botones—.

        Se pide por el **valor** de `SleepStage` y no por el miembro para que
        este módulo no tenga que importar `core.nomenclature`: la fase es del
        modelo y el color es de la presentación, y sólo se cruzan acá.

        Args:
            stage_value: el `.value` de la fase, "N2" o "REM".
        """
        for nombre, color in self.stage_colors:
            if nombre == stage_value:
                return color
        return None


#: **Los dos esquemas del rediseño de la pantalla principal.** Salen de medir
#: lo que tenía el programa: «Claro» es blanco puro con tinta negra, que sobre
#: ocho horas de señal es el máximo de deslumbramiento posible, y ninguno de
#: los seis distinguía una fase de otra.
#:
#: Lo que cambia respecto de los anteriores:
#:
#: - El lienzo es un blanco **cálido** y la ventana alrededor un papel más
#:   oscuro, así que la señal se despega del resto sin competir con ella.
#: - Traen `stage_colors`, que es lo que pinta el hipnograma, la franja de
#:   posición y los botones de fase con la misma escala.
#: - Las cifras van en IBM Plex Mono, como «Papel»: un número que cambia no
#:   puede saltar de ancho mientras se navega.
#:
#: **La paleta de canales se reusa tal cual.** Está verificada contra WCAG y
#: cambiarla cambiaría lo que el investigador ve en el dato, que no es lo que
#: un rediseño tiene que tocar.
SERENO: Final[ColorScheme] = ColorScheme(
    name="Sereno",
    background="#fcfbf7",
    foreground="#1a1c20",
    signals="#1a1c20",
    vary_signal_colors=True,
    signal_palette=_PALETA_CLARA,
    baseline="#e4e0d6",
    coarse_grid="#d9d5ca",
    fine_grid="#ece8dc",
    accent="#1e6f68",
    overview_background="#f6f4ef",
    overview_current="#dceae7",
    overview_border="#c9c4b6",
    overview_current_border="#1e6f68",
    overview_text="#5b6169",
    chrome="#edebe4",
    numeric_font="IBM Plex Mono",
    danger="#9e3b22",
    control_border="#838688",
    stage_colors=_FASES_CLARAS,
)

#: El mismo diseño para el turno noche. **No es gris plano como «Oscuro»**: el
#: fondo tira a azul y la ventana es más oscura que el lienzo, al revés que en
#: Sereno, porque sobre negro lo que se hunde es el marco y no la señal.
NOCTURNO: Final[ColorScheme] = ColorScheme(
    name="Nocturno",
    background="#0f1217",
    foreground="#e7e9ec",
    signals="#e7e9ec",
    vary_signal_colors=True,
    signal_palette=_PALETA_OSCURA,
    baseline="#232a32",
    coarse_grid="#2e3640",
    fine_grid="#1a1f26",
    accent="#58b7af",
    overview_background="#1b1f25",
    overview_current="#1c3a38",
    overview_border="#333a43",
    overview_current_border="#58b7af",
    overview_text="#99a1ab",
    chrome="#14171b",
    numeric_font="IBM Plex Mono",
    danger="#e07a5f",
    control_border="#5e6670",
    stage_colors=_FASES_OSCURAS,
)

#: Los esquemas del programa, por nombre. El orden es el que ve el usuario en
#: el menú «Ver».
#:
#: **Son dos y no se pueden editar**, por decisión del usuario en el hito 35.
#: Antes eran ocho y cada color se podía cambiar uno por uno, con lo que el
#: programa tenía infinitos aspectos posibles y ninguno garantizado: el control
#: de contraste sólo alcanzaba a los de fábrica, y el que se armaba a mano
#: podía dejar la señal invisible con un aviso al costado. Dos esquemas
#: verificados y ninguna perilla es menos programa y más garantía.
SCHEMES: Final[dict[str, ColorScheme]] = {
    esquema.name: esquema
    for esquema in (SERENO, NOCTURNO)
}

#: Con cuál arranca el programa la primera vez. **Es Sereno desde el rediseño
#: de la pantalla principal**, y sigue siendo el claro y no el oscuro por el
#: mismo motivo que antes: quien abre el programa de noche elige Nocturno, y
#: quien no, no tiene por qué encontrarse la pantalla apagada.
#:
#: A quien ya venía usando el programa no le cambia nada: su archivo de
#: preferencias trae el esquema que eligió, y esto sólo decide con cuál arranca
#: una instalación nueva. «Claro» sigue estando, y sigue devolviendo el aspecto
#: nativo de Qt.
DEFAULT_SCHEME_NAME: Final[str] = SERENO.name

_actual: ColorScheme = SERENO


def current() -> ColorScheme:
    """El esquema que está en uso.

    Es estado de módulo y no de la ventana porque lo consultan widgets que no
    se conocen entre sí —el visualizador, la grilla, los cinco paneles— y
    pasárselo por el constructor a cada uno obligaría a cablear el esquema por
    seis lugares cada vez que cambia.
    """
    return _actual


def set_current(scheme: ColorScheme) -> None:
    """Fija el esquema en uso y lo deja listo para los widgets que se creen.

    **No repinta lo que ya está dibujado.** `pg.setConfigOption` sólo alcanza a
    los `PlotWidget` que se construyan después, así que la ventana principal
    tiene que pedirle a cada widget que se vuelva a dibujar. Está separado a
    propósito: este módulo no conoce la ventana ni sabe qué hay abierto.

    Raises:
        UnknownColorSchemeError: si lo que se pasa no es un `ColorScheme`.
    """
    if not isinstance(scheme, ColorScheme):
        raise UnknownColorSchemeError(
            "No se pudo aplicar el esquema de color porque no es un esquema válido.",
            details=f"Se recibió un objeto de tipo {type(scheme).__name__}.",
        )
    global _actual
    _actual = scheme
    pg.setConfigOption("background", scheme.background)
    pg.setConfigOption("foreground", scheme.foreground)


def ink_over(scheme: ColorScheme, fill: str) -> str:
    """La tinta que se lee sobre un relleno de ese color.

    **Se elige midiendo y no por esquema**: la misma escala de fases se usa
    sobre papel y sobre negro, y el blanco que se lee sobre el azul profundo
    desaparece sobre el ámbar claro del esquema oscuro.

    **Las candidatas son tres**: el blanco, el fondo y la tinta del esquema.
    Hasta el hito 53 eran las dos primeras, con la idea de que el fondo era la
    tinta más oscura disponible, y eso sólo vale en Nocturno: en Sereno el
    fondo es casi blanco, así que no podía devolver ninguna tinta oscura. Sobre
    los colores de las clases de anotación daba entre 1,75 y 3 a 1 —el amarillo
    no se leía en los chips de evento de la Übersicht— y la tinta del esquema
    da entre 5,2 y 9,8. Lo encontró el rótulo de la banda de anotación.

    La usan las reglas de las fases, el botón de reproducir, los chips y los
    rótulos de las bandas.
    """
    return max(
        ("#ffffff", scheme.background, scheme.foreground),
        key=lambda tinta: contrast_ratio(tinta, fill),
    )


#: **Hasta el hito 53 `ink_over()` no servía sobre un relleno pálido**: elegía
#: entre el blanco y el fondo del esquema, y sobre el realce de una selección
#: en Sereno devolvía blanco, a 1,24 a 1. Desde que la tinta del esquema es la
#: tercera candidata ya sirve, pero la hoja de estilo le sigue poniendo la
#: tinta a mano a la fila seleccionada, que es una regla que no depende de
#: esta función.


def _reglas_de_las_fases(scheme: ColorScheme) -> str:
    """Una regla de hoja de estilo por fase, con el color que le toca.

    El botón de fase lleva la propiedad dinámica `fase` con el valor de su
    `SleepStage`, así que el color no se escribe en el panel de scoring: sale
    de acá, del esquema, como el de todo lo demás. Un esquema sin
    `stage_colors` no genera ninguna regla y sus botones se ven como cualquier
    otro, que es como se veían antes.

    **La tinta de encima la elige `ink_over()`**, midiendo.
    """
    reglas: list[str] = []
    for fase, color in scheme.stage_colors:
        tinta = ink_over(scheme, color)
        reglas.append(
            f'QPushButton[fase="{fase}"] {{ color: {color}; border-color: {color}; }}'
            f'QPushButton[fase="{fase}"]:checked {{'
            f" background-color: {color}; color: {tinta}; border-color: {color}; }}"
        )
    return "\n        ".join(reglas)


def stylesheet(scheme: ColorScheme) -> str:
    """La hoja de estilo de Qt que hace juego con un esquema.

    **Los `PlotWidget` no alcanzan.** Un esquema oscuro que pinte sólo el área
    de señal deja el selector de canales, el panel de scoring y la barra de
    estado en claro: la ventana queda a dos colores y el resultado se ve peor
    que no haber cambiado nada.

    Se usa una hoja de estilo y no `QPalette` porque la paleta no alcanza a los
    bordes ni a los encabezados de las tablas, que son justamente los que
    quedaban brillando sobre un fondo oscuro.

    **El esquema claro devuelve la cadena vacía**, que le devuelve a Qt su
    apariencia nativa. Es lo que hace que elegir "Claro" deje el programa
    exactamente como era antes de que existiera este módulo, en vez de como una
    imitación nuestra de un tema claro.

    Raises:
        UnknownColorSchemeError: si lo que se pasa no es un `ColorScheme`.
    """
    if not isinstance(scheme, ColorScheme):
        raise UnknownColorSchemeError(
            "No se pudo armar la hoja de estilo porque no es un esquema válido.",
            details=f"Se recibió un objeto de tipo {type(scheme).__name__}.",
        )
    fondo = scheme.background
    texto = scheme.foreground
    borde = scheme.coarse_grid
    borde_de_control = scheme.control_border or scheme.coarse_grid
    realce = scheme.overview_current
    # **La ventana y el contenido**: lo que rodea —barras, paneles, títulos,
    # encabezados— va con `chrome`, y lo que se lee adentro —campos, listas,
    # tablas— con el fondo. Sin `chrome` los dos son el mismo color, y la hoja
    # sale idéntica a la de antes del hito 26.
    ventana = scheme.chrome if scheme.chrome is not None else fondo
    # **El borde de la casilla sin marcar** (hito 53). Con el estilo nativo de
    # Windows, en Sereno un elemento sin marcar de una lista no dibujaba
    # ninguna casilla —el selector de canales y la lista de la ICA mostraban
    # el nombre suelto, sin nada que tildar— y la casilla del arousal apenas
    # se separaba del fondo. Es la tinta secundaria, la de los rótulos, que ya
    # pasa el contraste contra el fondo. La marcada se deja al estilo nativo,
    # que dibuja la tilde: una regla para ese estado obligaría a traer una
    # imagen propia de la tilde.
    casilla = scheme.overview_text
    lecturas = (
        f'QLabel[{READOUT_PROPERTY}="true"] {{ font-family: "{scheme.numeric_font}"; }}'
        if scheme.numeric_font is not None
        else ""
    )
    fases = _reglas_de_las_fases(scheme)
    # **La tinta de lo que destruye.** Un esquema puede no traerla, y entonces
    # el botón se ve como cualquier otro, que es como se veía antes de que
    # existiera: el cartel que lo rodea sigue diciendo qué se pierde.
    principal = f"""
        QPushButton[{PRIMARIO_PROPERTY}="true"] {{
            background-color: {scheme.accent};
            border: 1px solid {scheme.accent};
            color: {ink_over(scheme, scheme.accent)};
        }}
        QPushButton[{PRIMARIO_PROPERTY}="true"]:disabled {{
            background-color: {ventana};
            border: 1px solid {borde};
            color: {scheme.overview_text};
        }}
    """
    peligro = (
        f'QPushButton[{DESTRUCTIVO_PROPERTY}="true"] {{ color: {scheme.danger}; }}'
        if scheme.danger is not None
        else ""
    )
    return f"""
        QWidget {{ background-color: {ventana}; color: {texto}; }}
        QDockWidget {{ titlebar-close-icon: none; titlebar-normal-icon: none; }}
        QDockWidget::title {{
            background-color: {ventana};
            color: {texto};
            border-bottom: 1px solid {borde};
            padding: 5px 10px;
            text-align: left;
        }}
        QTabBar::tab {{
            background-color: {ventana};
            color: {texto};
            border: 1px solid transparent;
            border-bottom: 0;
            border-top-left-radius: {RADIO_DE_CONTROL}px;
            border-top-right-radius: {RADIO_DE_CONTROL}px;
            padding: 4px 10px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {fondo};
            border-color: {borde};
        }}
        QMenuBar, QMenu, QToolBar, QStatusBar {{
            background-color: {ventana}; color: {texto};
        }}
        QMenuBar {{ padding: 4px 6px; }}
        QMenuBar::item {{ padding: 6px 10px; border-radius: 6px; }}
        QMenuBar::item:selected, QMenu::item:selected {{
            background-color: {realce};
        }}
        QMenu {{ border: 1px solid {borde}; }}
        /* El botón de abrir: es un botón y no una entrada de menú, así que se
           ve como los demás botones —caja, borde y radio— y no como texto. */
        QMenuBar QToolButton {{
            background-color: {fondo};
            border: 1px solid {borde};
            border-radius: {RADIO_DE_CONTROL}px;
            padding: 4px 10px;
            margin: 0 8px 0 2px;
        }}
        QMenuBar QToolButton:hover, QMenuBar QToolButton:pressed {{
            background-color: {realce};
            border-color: {scheme.accent};
        }}
        QToolBar {{ border-bottom: 1px solid {borde}; }}
        QPushButton, QComboBox, QLineEdit, QAbstractSpinBox {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde_de_control};
            border-radius: {RADIO_DE_CONTROL}px;
            padding: {PADDING_DE_CONTROL};
            min-height: {ALTO_DE_CONTROL - 10}px;
        }}
        QPushButton:hover, QComboBox:hover {{ border-color: {scheme.accent}; }}
        QPushButton:focus, QComboBox:focus, QLineEdit:focus, QAbstractSpinBox:focus {{
            border: {ANILLO_DE_FOCO}px solid {scheme.accent};
        }}
        PlotWidget {{ border: {ANILLO_DE_FOCO}px solid transparent; }}
        PlotWidget:focus {{ border: {ANILLO_DE_FOCO}px solid {scheme.accent}; }}
        QCheckBox {{
            border: {ANILLO_DE_FOCO}px solid transparent;
            border-radius: {RADIO_DE_CONTROL}px;
            padding: 1px 3px;
        }}
        QCheckBox:focus {{ border-color: {scheme.accent}; }}
        QTabBar::tab:focus {{ border: {ANILLO_DE_FOCO}px solid {scheme.accent}; border-bottom: 0; }}
        QPushButton:checked, QPushButton:pressed {{ background-color: {realce}; }}
        QPushButton:disabled {{ color: {borde}; }}
        {principal}
        {peligro}
        PanelHeader {{
            background-color: {ventana};
            border-bottom: 1px solid {borde};
        }}
        EmptyState {{ background-color: {fondo}; }}
        QLabel[rotulo="true"] {{ color: {scheme.overview_text}; }}
        QLabel[secundario="true"] {{ color: {scheme.overview_text}; }}
        {fases}
        QTreeWidget, QTableWidget, QListWidget, QTextEdit, QPlainTextEdit {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde_de_control};
        }}
        QHeaderView::section {{
            background-color: {ventana};
            color: {texto};
            border: 1px solid {borde};
        }}
        QTreeWidget:focus, QTableWidget:focus, QListWidget:focus,
        QTextEdit:focus, QPlainTextEdit:focus {{
            border: {ANILLO_DE_FOCO}px solid {scheme.accent};
        }}
        QTreeWidget::item:selected, QTableWidget::item:selected,
        QListWidget::item:selected {{
            background-color: {realce};
            color: {texto};
        }}
        QListWidget::indicator:unchecked, QTreeWidget::indicator:unchecked,
        QCheckBox::indicator:unchecked {{
            border: 1px solid {casilla};
            border-radius: 3px;
            background-color: {fondo};
            width: 13px;
            height: 13px;
        }}
        QSplitter::handle {{ background-color: {borde}; }}
        QScrollBar {{ background-color: {ventana}; }}
        QScrollBar::handle {{ background-color: {borde}; }}
        QToolTip {{
            background-color: {fondo}; color: {texto};
            border: 1px solid {borde};
        }}
        {lecturas}
    """


def icon_ink(scheme: ColorScheme) -> str:
    """El color con que se dibujan los iconos bajo este esquema.

    Es el texto del esquema, y desde el hito 35 nada más que eso. Hasta
    entonces había un esquema —«Claro»— que no aplicaba hoja de estilo y dejaba
    el aspecto nativo del sistema, y ahí la tinta tenía que salir de la paleta
    de Qt: con Windows en modo oscuro, el negro de ese esquema dejaba los
    iconos negros sobre una barra negra. Sin ese caso, la función es el campo.

    Raises:
        UnknownColorSchemeError: si lo que se pasa no es un `ColorScheme`.
    """
    if not isinstance(scheme, ColorScheme):
        raise UnknownColorSchemeError(
            "No se pudo elegir el color de los iconos porque no es un esquema válido.",
            details=f"Se recibió un objeto de tipo {type(scheme).__name__}.",
        )
    return scheme.foreground


def scheme_by_name(name: str) -> ColorScheme:
    """Busca un esquema de fábrica por su nombre.

    Raises:
        UnknownColorSchemeError: si no existe ninguno con ese nombre. El mensaje
            enumera los que sí, porque el nombre suele venir de un archivo de
            preferencias escrito por otra versión del programa.
    """
    if not isinstance(name, str) or name not in SCHEMES:
        raise UnknownColorSchemeError(
            f"No existe ningún esquema de color llamado «{name}».",
            details=f"Los disponibles son: {', '.join(SCHEMES)}.",
        )
    return SCHEMES[name]


def is_valid_color(value: object) -> bool:
    """Si un valor se puede usar como color para dibujar.

    **Se pregunta al mismo que va a dibujar**, `pyqtgraph.mkColor()`, en vez de
    reimplementar su gramática. Comprobar sólo que fuera texto dejaba pasar
    "gris oscuro" desde un esquema escrito a mano, y el error salía recién al
    aplicarlo, como `ValueError` crudo y en la cara del investigador.

    No eleva: devuelve falso para cualquier cosa que no sirva, incluido lo que
    ni siquiera es texto.
    """
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        pg.mkColor(value)
    except (ValueError, TypeError, IndexError, KeyError):
        return False
    return True


def contrast_ratio(first: str, second: str) -> float:
    """El contraste entre dos colores, como lo define WCAG 2.1: de 1 a 21.

    Raises:
        UnknownColorSchemeError: si alguno no es un color que se pueda dibujar.
    """
    for color in (first, second):
        if not is_valid_color(color):
            raise UnknownColorSchemeError(
                "No se pudo medir el contraste porque uno de los colores no es válido.",
                details=f"Se recibió {color!r}.",
            )
    claro, oscuro = sorted(
        (_luminancia(first), _luminancia(second)), reverse=True
    )
    return (claro + 0.05) / (oscuro + 0.05)


def _luminancia(color: str) -> float:
    """La luminancia relativa de WCAG 2.1, de 0 (negro) a 1 (blanco)."""
    qcolor = pg.mkColor(color)

    def canal(valor: int) -> float:
        c = valor / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * canal(qcolor.red())
        + 0.7152 * canal(qcolor.green())
        + 0.0722 * canal(qcolor.blue())
    )


def low_contrast_elements(scheme: ColorScheme) -> list[tuple[str, float]]:
    """Lo que en un esquema no alcanza el contraste mínimo, con su contraste.

    Lo usan dos: el test que garantiza que **ningún esquema de fábrica** tenga
    nada en esta lista, y la ventana de configuración, que avisa cuando el
    usuario elige un color que no se va a distinguir del fondo.

    Returns:
        (qué cosa, contraste), vacía si todo alcanza.
    """
    medidas: list[tuple[str, str, str, float]] = [
        ("el texto de los gráficos", scheme.foreground, scheme.background, MIN_TEXT_CONTRAST),
        ("el texto del contexto", scheme.overview_text, scheme.overview_background, MIN_TEXT_CONTRAST),
        # **El canalón usa la tinta secundaria sobre el fondo de la señal**, que
        # es un par que hasta el hito 37 no se medía: `overview_text` sólo se
        # miraba contra `overview_background`. La clase y la escala de cada
        # canal se leen ahí.
        ("el detalle del canalón", scheme.overview_text, scheme.background, MIN_TEXT_CONTRAST),
        # **La fila seleccionada de una lista o una tabla.** Sin esta medida,
        # Qt le ponía su tinta de selección —blanco— sobre el realce del
        # esquema, y en Sereno eso da 1,24 a 1: el nombre del canal elegido
        # desaparecía. Lo mostró una captura del panel de ICA.
        (
            "el texto de una fila seleccionada",
            scheme.foreground,
            scheme.overview_current,
            MIN_TEXT_CONTRAST,
        ),
        ("las señales", scheme.signals, scheme.background, MIN_GRAPHIC_CONTRAST),
        ("la curva de los paneles", scheme.accent, scheme.background, MIN_GRAPHIC_CONTRAST),
        # Hito 62: en un campo de texto el borde es lo único que dice dónde se
        # escribe (WCAG 1.4.11). Contra el fondo del control y contra el de la
        # ventana, que son los dos que tiene a cada lado.
        (
            "el borde de los controles",
            scheme.control_border or scheme.coarse_grid,
            scheme.background,
            MIN_GRAPHIC_CONTRAST,
        ),
        (
            "el borde de los controles sobre la ventana",
            scheme.control_border or scheme.coarse_grid,
            scheme.chrome or scheme.background,
            MIN_GRAPHIC_CONTRAST,
        ),
        # Hito 53: el borde de la casilla sin marcar es lo único que dice que
        # un canal oculto se puede volver a tildar.
        (
            "el borde de la casilla sin marcar",
            scheme.overview_text,
            scheme.background,
            MIN_GRAPHIC_CONTRAST,
        ),
    ]
    if scheme.chrome is not None:
        medidas.append(
            ("el texto de la ventana", scheme.foreground, scheme.chrome, MIN_TEXT_CONTRAST)
        )
    if scheme.danger is not None:
        # Es texto —el rótulo de un botón— y no un gráfico, así que le toca el
        # mínimo de texto. Se mide contra la ventana porque ahí vive el botón.
        medidas.append(
            (
                "la tinta de lo que destruye",
                scheme.danger,
                scheme.chrome if scheme.chrome is not None else scheme.background,
                MIN_TEXT_CONTRAST,
            )
        )
    medidas += [
        (f"el color {posicion + 1} de los canales", color, scheme.background, MIN_GRAPHIC_CONTRAST)
        for posicion, color in enumerate(scheme.signal_palette)
    ]
    # **Las fases entran con el mismo criterio que los canales**: son algo que
    # se dibuja y hay que distinguir del fondo, no texto. Un esquema sin escala
    # no aporta ninguna medida, y por eso los seis anteriores no cambian.
    medidas += [
        (f"el color de la fase {fase}", color, scheme.background, MIN_GRAPHIC_CONTRAST)
        for fase, color in scheme.stage_colors
    ]
    return [
        (que, round(contrast_ratio(color, fondo), 2))
        for que, color, fondo, minimo in medidas
        if contrast_ratio(color, fondo) < minimo
    ]
