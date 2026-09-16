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
    "#6060ff",
)


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
    signal_palette=_PALETA_CLARA,
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

#: Los esquemas de fábrica, por nombre. El orden es el que ve el usuario en el
#: menú, y arranca por el que reproduce el aspecto histórico del programa.
SCHEMES: Final[dict[str, ColorScheme]] = {
    esquema.name: esquema for esquema in (CLARO, OSCURO, NK, AZUL_SOBRE_GRIS, ECG)
}

#: Con cuál arranca el programa la primera vez. **Es el claro y no el oscuro**,
#: aunque la referencia sea oscura: quien ya venía usando el programa no tiene
#: por qué encontrárselo cambiado sin haberlo pedido. Se elige otro desde el
#: menú y queda guardado.
DEFAULT_SCHEME_NAME: Final[str] = CLARO.name

_actual: ColorScheme = CLARO


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
    return f"""
        QWidget {{ background-color: {fondo}; color: {texto}; }}
        QMenuBar, QMenu, QToolBar, QStatusBar {{
            background-color: {fondo}; color: {texto};
        }}
        QMenuBar::item:selected, QMenu::item:selected {{
            background-color: {realce};
        }}
        QMenu {{ border: 1px solid {borde}; }}
        QToolBar {{ border-bottom: 1px solid {borde}; }}
        QPushButton, QComboBox, QLineEdit, QSpinBox {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde};
            padding: 2px 6px;
        }}
        QPushButton:checked, QPushButton:pressed {{ background-color: {realce}; }}
        QPushButton:disabled {{ color: {borde}; }}
        QTreeWidget, QTableWidget, QListWidget, QTextEdit, QPlainTextEdit {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde};
        }}
        QHeaderView::section {{
            background-color: {fondo};
            color: {texto};
            border: 1px solid {borde};
        }}
        QTreeWidget::item:selected, QTableWidget::item:selected,
        QListWidget::item:selected {{ background-color: {realce}; }}
        QSplitter::handle {{ background-color: {borde}; }}
        QScrollBar {{ background-color: {fondo}; }}
        QScrollBar::handle {{ background-color: {borde}; }}
        QToolTip {{
            background-color: {fondo}; color: {texto};
            border: 1px solid {borde};
        }}
    """


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
