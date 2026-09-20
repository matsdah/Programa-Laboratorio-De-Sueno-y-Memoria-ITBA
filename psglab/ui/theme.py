"""Esquemas de color del programa: qué color tiene cada cosa que se dibuja.

Hasta el refactor de la interfaz no existía ningún concepto de tema. El fondo se
fijaba una sola vez para todo el programa con tres `pg.setConfigOption` en
`psglab/app.py`, y los demás colores vivían como constantes privadas repartidas
en cinco módulos. Cambiar de aspecto era editar código en seis lugares.

**Los colores no salen de `psglab/config.py`, y es a propósito.** Ese archivo
guarda lo que fija el pliego, y el pliego no dice nada de colores: pide tres
fondos de grilla y nada más. Con qué color se distingue un canal de otro es del
programa, no del requisito, y por eso vive acá y lo puede cambiar el usuario.

Un esquema es un valor inmutable. Nadie lo edita: se elige otro. Eso es lo que
permite que guardar un esquema sea escribir un archivo y cargarlo, leerlo, sin
ningún estado a medio camino.

Cubre del pliego: ningún ID. Es infraestructura de presentación; el único
requisito visual que el pliego fija, los tres fondos de grilla, lo cubre
`psglab/ui/grid.py`.
"""

from dataclasses import dataclass, fields
from typing import Final

import pyqtgraph as pg
from PySide6.QtGui import QGuiApplication, QPalette

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

#: La paleta para fondos grises. **Un gris necesita colores más oscuros que el
#: blanco**: con la paleta clara, el dorado daba 2,41 sobre el esquema «Azul
#: sobre gris». Son los mismos tonos, oscurecidos hasta pasar el mínimo.
_PALETA_SOBRE_GRIS: Final[tuple[str, ...]] = (
    "#123a75",
    "#2c5a20",
    "#6b5412",
    "#7a3a14",
    "#521575",
    "#135a55",
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
        ecg_grid: si la grilla es **cuadriculada**, como el papel de un
            electrocardiograma, en vez de tener sólo líneas verticales. Es la
            opción "Grilla: Normal / ECG" de la referencia. Va en el esquema y
            no aparte porque el esquema ECG la trae prendida, y separarlas
            obligaría a elegir dos cosas para obtener el aspecto que el nombre
            promete.
        chrome: fondo de la ventana —la barra de menú, la de estado, los
            paneles y sus títulos—, cuando es distinto del de las áreas de
            dibujo. **Vacío es «el mismo que `background`»**, que es lo que
            hacen todos los esquemas anteriores al hito 26: la hoja de estilo
            sale idéntica.
        numeric_font: la tipografía de las lecturas numéricas (ver
            `READOUT_PROPERTY`), o vacío para usar la de siempre. Va en el
            esquema por el mismo argumento que `ecg_grid`: el esquema «Papel»
            la trae puesta, y separarlas obligaría a elegir dos cosas para
            obtener el aspecto que el nombre promete.
        stage_colors: qué color tiene cada fase de sueño, como (valor de
            `SleepStage`, color). **Vacío significa «una sola tinta»**, que es
            como se dibujaba el hipnograma hasta que esto existió, y es lo que
            traen los seis esquemas anteriores: inventarles una escala de fases
            a NK o a ECG sería cambiarles el aspecto que su nombre promete. Los
            dos esquemas nuevos sí la traen, y de ahí salen el hipnograma, la
            franja de posición y los botones de fase.

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
    ecg_grid: bool = False
    chrome: str | None = None
    numeric_font: str | None = None
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


CLARO: Final[ColorScheme] = ColorScheme(
    name="Claro",
    background="#ffffff",
    foreground="#000000",
    signals="#1a1a1a",
    vary_signal_colors=True,
    signal_palette=_PALETA_CLARA,
    baseline="#d0d0d0",
    coarse_grid="#a0a0a0",
    fine_grid="#dcdcdc",
    accent="#4a90e6",
    overview_background="#f2f2f2",
    overview_current="#c8d8ec",
    overview_border="#8a8a8a",
    overview_current_border="#2c5a8c",
    overview_text="#333333",
)

OSCURO: Final[ColorScheme] = ColorScheme(
    name="Oscuro",
    background="#3c3c3c",
    foreground="#f0f0f0",
    signals="#ffff00",
    vary_signal_colors=True,
    signal_palette=_PALETA_OSCURA,
    baseline="#6e6e6e",
    coarse_grid="#8c8c8c",
    fine_grid="#565656",
    accent="#63b3ff",
    overview_background="#2e2e2e",
    overview_current="#3f5a76",
    overview_border="#7a7a7a",
    overview_current_border="#9cc4ea",
    overview_text="#e0e0e0",
)

NK: Final[ColorScheme] = ColorScheme(
    name="NK",
    background="#000000",
    foreground="#d0d0d0",
    signals="#ffffff",
    vary_signal_colors=False,
    signal_palette=_PALETA_OSCURA,
    baseline="#404040",
    coarse_grid="#5a5a5a",
    fine_grid="#303030",
    accent="#ffffff",
    overview_background="#101010",
    overview_current="#303030",
    overview_border="#505050",
    overview_current_border="#b0b0b0",
    overview_text="#d0d0d0",
)

AZUL_SOBRE_GRIS: Final[ColorScheme] = ColorScheme(
    name="Azul sobre gris",
    background="#c8c8c8",
    foreground="#1a1a2e",
    signals="#00008b",
    vary_signal_colors=False,
    signal_palette=_PALETA_SOBRE_GRIS,
    baseline="#a8a8a8",
    coarse_grid="#8a8a9a",
    fine_grid="#b8b8c4",
    accent="#00008b",
    overview_background="#bcbcbc",
    overview_current="#9aa8c8",
    overview_border="#8a8a8a",
    overview_current_border="#00008b",
    overview_text="#1a1a2e",
)

ECG: Final[ColorScheme] = ColorScheme(
    name="ECG",
    background="#fff4f4",
    foreground="#5a1a1a",
    signals="#101010",
    vary_signal_colors=False,
    signal_palette=_PALETA_CLARA,
    baseline="#e8b4b4",
    coarse_grid="#e08080",
    fine_grid="#f2c4c4",
    accent="#b02020",
    overview_background="#fbeaea",
    overview_current="#f2c4c4",
    overview_border="#d09090",
    overview_current_border="#b02020",
    overview_text="#5a1a1a",
    ecg_grid=True,
)

#: El aspecto del lienzo de diseño del hito 26: las áreas de dibujo en blanco,
#: como en Claro, y la ventana alrededor en un gris cálido, para que la señal se
#: despegue del resto sin competir con ella. Las cifras van en IBM Plex Mono,
#: que el programa trae consigo (ver `fonts.py`); si no está, Qt usa la de
#: siempre sin avisar, que es lo que corresponde a una preferencia visual.
PAPEL: Final[ColorScheme] = ColorScheme(
    name="Papel",
    background="#ffffff",
    foreground="#1a1a1a",
    signals="#1a1a1a",
    vary_signal_colors=False,
    signal_palette=_PALETA_CLARA,
    baseline="#d0d0d0",
    coarse_grid="#a0a0a0",
    fine_grid="#dcdcdc",
    accent="#2c5a8c",
    overview_background="#f2f2f2",
    overview_current="#c8d8ec",
    overview_border="#8a8a8a",
    overview_current_border="#2c5a8c",
    overview_text="#333333",
    chrome="#ebe8e2",
    numeric_font="IBM Plex Mono",
)

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
    stage_colors=_FASES_OSCURAS,
)

#: Los esquemas de fábrica, por nombre. El orden es el que ve el usuario en el
#: menú, y arranca por el que reproduce el aspecto histórico del programa.
SCHEMES: Final[dict[str, ColorScheme]] = {
    esquema.name: esquema
    for esquema in (SERENO, NOCTURNO, CLARO, OSCURO, NK, AZUL_SOBRE_GRIS, ECG, PAPEL)
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


def _reglas_de_las_fases(scheme: ColorScheme) -> str:
    """Una regla de hoja de estilo por fase, con el color que le toca.

    El botón de fase lleva la propiedad dinámica `fase` con el valor de su
    `SleepStage`, así que el color no se escribe en el panel de scoring: sale
    de acá, del esquema, como el de todo lo demás. Un esquema sin
    `stage_colors` no genera ninguna regla y sus botones se ven como cualquier
    otro, que es como se veían antes.

    **La tinta de encima se elige midiendo**, no por esquema: la misma escala
    de fases se usa sobre papel y sobre negro, y el blanco que se lee sobre el
    azul profundo desaparece sobre el ámbar claro del esquema oscuro.
    """
    reglas: list[str] = []
    for fase, color in scheme.stage_colors:
        tinta = (
            "#ffffff"
            if contrast_ratio("#ffffff", color) >= contrast_ratio(scheme.background, color)
            else scheme.background
        )
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
    if scheme is CLARO:
        return ""

    fondo = scheme.background
    texto = scheme.foreground
    borde = scheme.coarse_grid
    realce = scheme.overview_current
    # **La ventana y el contenido**: lo que rodea —barras, paneles, títulos,
    # encabezados— va con `chrome`, y lo que se lee adentro —campos, listas,
    # tablas— con el fondo. Sin `chrome` los dos son el mismo color, y la hoja
    # sale idéntica a la de antes del hito 26.
    ventana = scheme.chrome if scheme.chrome is not None else fondo
    lecturas = (
        f'QLabel[{READOUT_PROPERTY}="true"] {{ font-family: "{scheme.numeric_font}"; }}'
        if scheme.numeric_font is not None
        else ""
    )
    fases = _reglas_de_las_fases(scheme)
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
        QMenuBar::item:selected, QMenu::item:selected {{
            background-color: {realce};
        }}
        QMenu {{ border: 1px solid {borde}; }}
        QMenuBar QToolButton {{
            border: none; border-radius: 3px; padding: 2px 6px;
        }}
        QMenuBar QToolButton:hover, QMenuBar QToolButton:pressed {{
            background-color: {realce};
        }}
        QToolBar {{ border-bottom: 1px solid {borde}; }}
        QPushButton, QComboBox, QLineEdit, QSpinBox {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde};
            border-radius: {RADIO_DE_CONTROL}px;
            padding: {PADDING_DE_CONTROL};
            min-height: {ALTO_DE_CONTROL - 10}px;
        }}
        QPushButton:hover, QComboBox:hover {{ border-color: {scheme.accent}; }}
        QPushButton:focus, QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{
            border: {ANILLO_DE_FOCO}px solid {scheme.accent};
        }}
        QPushButton:checked, QPushButton:pressed {{ background-color: {realce}; }}
        QPushButton:disabled {{ color: {borde}; }}
        {fases}
        QTreeWidget, QTableWidget, QListWidget, QTextEdit, QPlainTextEdit {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde};
        }}
        QHeaderView::section {{
            background-color: {ventana};
            color: {texto};
            border: 1px solid {borde};
        }}
        QTreeWidget::item:selected, QTableWidget::item:selected,
        QListWidget::item:selected {{ background-color: {realce}; }}
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

    Es el texto del esquema, **salvo en Claro**. Ése no aplica hoja de estilo
    y deja el aspecto nativo, que sigue el modo claro u oscuro del sistema: con
    Windows en modo oscuro, el negro de Claro dejaba los iconos negros sobre
    una barra negra. Ahí la tinta es la del texto de la aplicación, que Qt ya
    eligió para ese fondo.

    Raises:
        UnknownColorSchemeError: si lo que se pasa no es un `ColorScheme`.
    """
    if not isinstance(scheme, ColorScheme):
        raise UnknownColorSchemeError(
            "No se pudo elegir el color de los iconos porque no es un esquema válido.",
            details=f"Se recibió un objeto de tipo {type(scheme).__name__}.",
        )
    if scheme is CLARO and QGuiApplication.instance() is not None:
        return QGuiApplication.palette().color(QPalette.ColorRole.WindowText).name()
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


def scheme_to_dict(scheme: ColorScheme) -> dict[str, object]:
    """Pasa un esquema a algo que se pueda escribir en un archivo.

    Raises:
        UnknownColorSchemeError: si lo que se pasa no es un `ColorScheme`.
    """
    if not isinstance(scheme, ColorScheme):
        raise UnknownColorSchemeError(
            "No se pudo guardar el esquema de color porque no es un esquema válido.",
            details=f"Se recibió un objeto de tipo {type(scheme).__name__}.",
        )
    datos: dict[str, object] = {}
    for campo in fields(ColorScheme):
        valor = getattr(scheme, campo.name)
        datos[campo.name] = list(valor) if isinstance(valor, tuple) else valor
    return datos


def scheme_from_dict(data: dict[str, object]) -> ColorScheme:
    """Reconstruye un esquema desde lo que se leyó de un archivo.

    **Lo que falte se toma del esquema claro y lo que sobre se ignora.** Un
    archivo guardado por una versión anterior, que no tenía algún campo, sigue
    cargando en vez de rechazarse entero: el esquema es una preferencia visual,
    y perderla porque el programa creció es peor que dibujar un color por
    omisión.

    Raises:
        UnknownColorSchemeError: si no es un diccionario, o si algún campo
            presente tiene un tipo con el que no se puede dibujar.
    """
    if not isinstance(data, dict):
        raise UnknownColorSchemeError(
            "El esquema de color no se pudo leer porque no tiene el formato esperado.",
            details=f"Se esperaba un diccionario y se recibió {type(data).__name__}.",
        )

    valores: dict[str, object] = {}
    for campo in fields(ColorScheme):
        if campo.name not in data:
            valores[campo.name] = getattr(CLARO, campo.name)
            continue
        valores[campo.name] = _valor_validado(campo.name, data[campo.name])
    return ColorScheme(**valores)  # type: ignore[arg-type]


def _valor_validado(nombre: str, valor: object) -> object:
    """Comprueba que un campo leído de un archivo se pueda usar para dibujar.

    Raises:
        UnknownColorSchemeError: si el tipo no es el que ese campo necesita.
    """
    if nombre == "signal_palette":
        if not isinstance(valor, (list, tuple)) or not all(
            is_valid_color(color) for color in valor
        ):
            raise UnknownColorSchemeError(
                "El esquema de color tiene una paleta que no se puede usar.",
                details="«signal_palette» tiene que ser una lista de colores.",
            )
        return tuple(valor)
    if nombre == "stage_colors":
        if not isinstance(valor, (list, tuple)) or not all(
            isinstance(fila, (list, tuple))
            and len(fila) == 2
            and isinstance(fila[0], str)
            and is_valid_color(fila[1])
            for fila in valor
        ):
            raise UnknownColorSchemeError(
                "El esquema de color tiene una escala de fases que no se puede usar.",
                details="«stage_colors» tiene que ser una lista de (fase, color).",
            )
        return tuple((str(fila[0]), str(fila[1])) for fila in valor)
    if nombre == "vary_signal_colors":
        if not isinstance(valor, bool):
            raise UnknownColorSchemeError(
                "El esquema de color tiene un valor que no se puede usar.",
                details="«vary_signal_colors» tiene que ser verdadero o falso.",
            )
        return valor
    if nombre == "name":
        # Es el único campo de texto que **no** es un color: es lo que ve el
        # usuario en el menú, así que basta con que haya algo escrito.
        if not isinstance(valor, str) or not valor.strip():
            raise UnknownColorSchemeError(
                "El esquema de color no tiene nombre.",
                details=f"«name» tiene que ser un texto no vacío; es {valor!r}.",
            )
        return valor
    if nombre == "ecg_grid":
        if not isinstance(valor, bool):
            raise UnknownColorSchemeError(
                "El esquema de color tiene un valor que no se puede usar.",
                details="«ecg_grid» tiene que ser verdadero o falso.",
            )
        return valor
    if nombre == "numeric_font":
        if valor is not None and (not isinstance(valor, str) or not valor.strip()):
            raise UnknownColorSchemeError(
                "El esquema de color tiene una tipografía que no se puede usar.",
                details=f"«numeric_font» tiene que ser un nombre, o estar vacío; es {valor!r}.",
            )
        return valor
    if nombre == "chrome":
        if valor is not None and not is_valid_color(valor):
            raise UnknownColorSchemeError(
                "El esquema de color tiene un fondo de ventana que no se puede usar.",
                details=f"«chrome» tiene que ser un color, o estar vacío; es {valor!r}.",
            )
        return valor
    if nombre == "baseline":
        if valor is not None and not is_valid_color(valor):
            raise UnknownColorSchemeError(
                "El esquema de color tiene una línea de base que no se puede usar.",
                details=f"«baseline» tiene que ser un color, o estar vacío; es {valor!r}.",
            )
        return valor
    if not is_valid_color(valor):
        raise UnknownColorSchemeError(
            f"El esquema de color tiene un color que no se puede usar en «{nombre}».",
            details=f"Se esperaba un color y se recibió {valor!r}.",
        )
    return valor


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
        ("las señales", scheme.signals, scheme.background, MIN_GRAPHIC_CONTRAST),
        ("la curva de los paneles", scheme.accent, scheme.background, MIN_GRAPHIC_CONTRAST),
    ]
    if scheme.chrome is not None:
        medidas.append(
            ("el texto de la ventana", scheme.foreground, scheme.chrome, MIN_TEXT_CONTRAST)
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
