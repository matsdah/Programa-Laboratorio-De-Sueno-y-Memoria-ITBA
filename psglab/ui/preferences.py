"""Lo que el programa recuerda entre una sesión y la siguiente.

Hasta el refactor de la interfaz no había **ninguna** persistencia: la escala de
cada canal, el eje del histograma y el tamaño del panel de contexto vivían sólo
en memoria y se perdían al cerrar. Para una preferencia que se toca una vez por
sesión eso es tolerable; para el esquema de color no lo es. Un tema oscuro que
hay que volver a elegir en cada arranque no se usa.

**Esto no es `psglab/config.py` y no lo reemplaza.** Aquél guarda lo que fija el
pliego —la ventana de 30 s, la grilla, la banda de 75 µV— y es inmutable en
tiempo de ejecución justamente porque el pliego no se negocia con el usuario.
Acá vive lo contrario: lo que el usuario elige y el programa tiene que recordar.

**Está en `ui/` y no en `core/` porque es presentación**, no regla de negocio:
qué color tiene una curva no cambia ningún resultado. No importa nada de Qt, así
que se testea sin abrir una ventana.

Cubre del pliego: ningún ID. Es infraestructura de presentación.
"""

import json
import math
import os
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Final

import pyqtgraph as pg

from psglab.analysis.psd import DEFAULT_BANDS, METHODS, validate_band
from psglab.config import (
    AMPLITUDE_BAND_UV,
    DEFAULT_VIEW_SECONDS,
    MIN_VIEW_SECONDS,
    OVERVIEW_WINDOWS_AFTER,
    OVERVIEW_WINDOWS_BEFORE,
)
from psglab.core.annotations import es_color_de_clase
from psglab.core.nomenclature import Nomenclature
from psglab.tools.magnifier import RADIO_INICIAL_SEGUNDOS, ZOOM_INICIAL
from psglab.ui.fonts import UI_FONT_FAMILY
from psglab.ui.theme import (
    DEFAULT_SCHEME_NAME,
    ColorScheme,
    is_valid_color,
    scheme_by_name,
)
from psglab.utils.errors import InvalidPreferencesError, PsgLabError

#: Versión del formato del archivo. Se escribe siempre y hoy no se lee para
#: decidir nada: existe para que una versión futura que cambie el formato pueda
#: reconocer los archivos viejos en vez de tener que adivinar.
FORMAT_VERSION: Final[int] = 1

#: Cómo se llama el archivo dentro de la carpeta de configuración del usuario.
FILENAME: Final[str] = "preferencias.json"

#: Nombre de la carpeta propia dentro de la de configuración del sistema.
APP_DIRNAME: Final[str] = "psglab"

#: Tamaños de letra que se aceptan, en puntos. Fuera de este rango la interfaz
#: deja de entrar en la pantalla o deja de leerse.
MIN_FONT_SIZE: Final[int] = 6
MAX_FONT_SIZE: Final[int] = 48

#: Cuántas ventanas vecinas puede mostrar la Übersicht de cada lado. El pliego
#: no pone un tope; éste es el de la pantalla: con cinco de cada lado son once
#: ventanas en un panel que suele tener unos 225 px, y más ya no se distinguen.
MAX_OVERVIEW_WINDOWS: Final[int] = 5

#: Rangos de los ajustes de las herramientas (hito 32). Los valores por omisión
#: son los de siempre —la banda, la del pliego—; los rangos son los de la
#: pantalla: fuera de ellos la banda o la lupa dejan de servir para mirar.
MIN_AMPLITUDE_BAND_UV: Final[float] = 5.0
MAX_AMPLITUDE_BAND_UV: Final[float] = 500.0
MIN_MAGNIFIER_RADIUS_SECONDS: Final[float] = 0.1
MAX_MAGNIFIER_RADIUS_SECONDS: Final[float] = 10.0
MIN_MAGNIFIER_ZOOM: Final[float] = 1.0
MAX_MAGNIFIER_ZOOM: Final[float] = 20.0

#: Lo que puede elevar un campo del archivo cuando trae un valor que no sirve:
#: el rechazo del constructor, o lo que eleva Python al tratar como lista lo
#: que es un número, o como texto lo que es un objeto. **Un campo roto vuelve
#: a su valor de fábrica y el programa arranca igual**; ver `load()`.
_ERRORES_DE_UN_CAMPO: Final[tuple[type[Exception], ...]] = (
    PsgLabError,
    TypeError,
    ValueError,
    IndexError,
    KeyError,
    AttributeError,
)


@dataclass(frozen=True)
class Preferences:
    """Las preferencias del usuario.

    Inmutable, igual que `ColorScheme`: cambiar una preferencia es construir
    otra con `replace()`, no escribirle encima a la que está en uso. Así nadie
    puede dejar el objeto a medio actualizar si algo falla en el medio.

    Attributes:
        scheme_name: nombre del esquema de color elegido, uno de los dos que
            hay. **Se guarda el nombre y no el esquema**, así que mejorar los
            colores en una versión nueva alcanza a quien ya lo eligió.
            **Arranca en la que el programa empaqueta** (hito 34), que es la del
            diseño; si los archivos no estuvieran, la ventana se queda con la
            del sistema en vez de dejar que Qt sustituya por cualquier cosa.
        font_size: su tamaño en puntos, o None para el del sistema.
        psd_method: cómo se estima el espectro; uno de `psd.METHODS`.
        psd_bands: las bandas de frecuencia, como (nombre, desde, hasta), o
            None para las convencionales de `psd.DEFAULT_BANDS`. **Se guarda
            None y no una copia de las convencionales** por el mismo motivo que
            el nombre del esquema: si una versión nueva las corrige, la
            corrección tiene que alcanzar a quien nunca las tocó.
        psd_log_power: si el eje de potencia del espectro es logarítmico.
        annotation_colors: el color elegido para cada clase de evento, como
            (clase, color). Sólo las que el usuario cambió: las demás siguen
            tomando el suyo de la paleta, en orden.
        open_view_seconds: cuánto dura la página al abrir un registro.
        open_nomenclature: con qué nomenclatura arranca un scoring nuevo, por
            el nombre del miembro de `Nomenclature`. **Un scoring importado
            trae la suya** y ésta no la pisa.
        open_clock_axis: si el histograma arranca en hora real. Sólo se aplica
            si el registro informa su hora de inicio.
        overview_before: cuántas ventanas anteriores muestra la Übersicht
            (V3_F). De 0 a `MAX_OVERVIEW_WINDOWS`; cero no muestra ese lado.
        overview_after: cuántas posteriores. Es independiente de la anterior:
            el pliego la pide asimétrica.
        amplitude_band_uv: la altura de la banda de amplitud, en µV. Arranca en
            la del pliego; hay criterios que usan otros umbrales.
        magnifier_radius_seconds: el radio de la lupa, en segundos de señal.
        magnifier_zoom: cuánto amplía la lupa. 1 es sin aumento.

    **Todo valor se comprueba al construir.** Es el criterio de
    `core/recording.py`: rechazar al armar el objeto lo que después no se puede
    arreglar. Así la ventana de configuración no puede fabricar unas
    preferencias inválidas, y `load()` sabe distinguir un campo roto de uno
    sano preguntándole a este mismo constructor.

    Raises:
        InvalidPreferencesError: si algún campo nuevo tiene un valor que el
            programa no puede usar.
    """

    scheme_name: str = DEFAULT_SCHEME_NAME
    font_size: int | None = None
    psd_method: str = METHODS[0]
    psd_bands: tuple[tuple[str, float, float], ...] | None = None
    psd_log_power: bool = True
    annotation_colors: tuple[tuple[str, str], ...] = ()
    open_view_seconds: float = DEFAULT_VIEW_SECONDS
    open_nomenclature: str = Nomenclature.AASM.name
    open_clock_axis: bool = False
    overview_before: int = OVERVIEW_WINDOWS_BEFORE
    overview_after: int = OVERVIEW_WINDOWS_AFTER
    amplitude_band_uv: float = AMPLITUDE_BAND_UV
    magnifier_radius_seconds: float = RADIO_INICIAL_SEGUNDOS
    magnifier_zoom: float = ZOOM_INICIAL

    def __post_init__(self) -> None:
        """Rechaza lo que el programa no podría usar. Ver el docstring de la clase."""
        if self.font_size is not None and not (
            _es_entero(self.font_size)
            and MIN_FONT_SIZE <= self.font_size <= MAX_FONT_SIZE
        ):
            _rechazar(
                f"el tamaño de letra (entre {MIN_FONT_SIZE} y {MAX_FONT_SIZE} puntos)",
                self.font_size,
            )
        if self.psd_method not in METHODS:
            _rechazar("el método del espectro", self.psd_method)
        if self.psd_bands is not None:
            _validar_bandas(self.psd_bands)
        if not isinstance(self.psd_log_power, bool):
            _rechazar("la escala del espectro", self.psd_log_power)
        _validar_colores_de_clase(self.annotation_colors)
        if not (
            _es_numero(self.open_view_seconds)
            and math.isfinite(self.open_view_seconds)
            and self.open_view_seconds >= MIN_VIEW_SECONDS
        ):
            _rechazar("la duración de la página al abrir", self.open_view_seconds)
        if self.open_nomenclature not in Nomenclature.__members__:
            _rechazar("la nomenclatura al abrir", self.open_nomenclature)
        if not isinstance(self.open_clock_axis, bool):
            _rechazar("el eje del histograma al abrir", self.open_clock_axis)
        for que, valor in (
            ("las ventanas anteriores del contexto", self.overview_before),
            ("las ventanas posteriores del contexto", self.overview_after),
        ):
            if not (_es_entero(valor) and 0 <= valor <= MAX_OVERVIEW_WINDOWS):
                _rechazar(f"{que} (entre 0 y {MAX_OVERVIEW_WINDOWS})", valor)
        for que, valor, minimo, maximo in (
            ("la altura de la banda de amplitud", self.amplitude_band_uv,
             MIN_AMPLITUDE_BAND_UV, MAX_AMPLITUDE_BAND_UV),
            ("el radio de la lupa", self.magnifier_radius_seconds,
             MIN_MAGNIFIER_RADIUS_SECONDS, MAX_MAGNIFIER_RADIUS_SECONDS),
            ("el aumento de la lupa", self.magnifier_zoom,
             MIN_MAGNIFIER_ZOOM, MAX_MAGNIFIER_ZOOM),
        ):
            if not (_es_numero(valor) and math.isfinite(valor) and minimo <= valor <= maximo):
                _rechazar(f"{que} (entre {minimo:g} y {maximo:g})", valor)

    def with_changes(self, **changes: object) -> "Preferences":
        """Las mismas preferencias con algunos campos cambiados, ya comprobados.

        Es `dataclasses.replace()` con un nombre que dice lo que hace. El
        constructor comprueba los valores, así que un cambio inválido eleva acá
        y no cuando se lo quiera usar.

        Raises:
            InvalidPreferencesError: si algún valor no se puede usar, o si se
                nombra un campo que no existe.
        """
        conocidos = {campo.name for campo in fields(Preferences)}
        desconocidos = sorted(set(changes) - conocidos)
        if desconocidos:
            raise InvalidPreferencesError(
                "No se pudo cambiar la configuración.",
                details=f"No existen los campos {', '.join(desconocidos)}.",
            )
        return replace(self, **changes)

    def bands(self) -> dict[str, tuple[float, float]]:
        """Las bandas de frecuencia vigentes, como las espera `psd`."""
        if self.psd_bands is None:
            return dict(DEFAULT_BANDS)
        return {nombre: (desde, hasta) for nombre, desde, hasta in self.psd_bands}

    def with_bands(
        self, bands: dict[str, tuple[float, float]] | None
    ) -> "Preferences":
        """Las mismas preferencias con otras bandas, o las convencionales con None.

        Si las que se pasan son exactamente las convencionales, se guarda None:
        así una corrección futura de las de fábrica alcanza a quien las eligió
        sin tocarlas.

        Raises:
            InvalidPreferencesError: si no es un diccionario, o si alguna banda
                no se puede integrar.
        """
        if bands is None or bands == dict(DEFAULT_BANDS):
            return replace(self, psd_bands=None)
        if not isinstance(bands, dict):
            _rechazar("las bandas del espectro", bands)
        filas = []
        for nombre, banda in bands.items():
            try:
                desde, hasta = validate_band(banda)
            except PsgLabError as error:
                raise InvalidPreferencesError(
                    f"La banda «{nombre}» no se puede usar: {error}",
                    details=error.details,
                ) from error
            filas.append((nombre, desde, hasta))
        return replace(self, psd_bands=tuple(filas))

    def nomenclature(self) -> Nomenclature:
        """La nomenclatura con la que arranca un scoring nuevo."""
        return Nomenclature[self.open_nomenclature]

    def annotation_color(self, label: str) -> str | None:
        """El color que el usuario eligió para una clase, o None si no eligió."""
        return dict(self.annotation_colors).get(label)

    def with_annotation_color(self, label: str, color: str) -> "Preferences":
        """Las mismas preferencias con otro color para una clase de evento.

        Raises:
            InvalidPreferencesError: si la clase está vacía o el color no se
                puede dibujar.
        """
        colores = dict(self.annotation_colors)
        colores[label] = color
        return replace(self, annotation_colors=tuple(colores.items()))

    def scheme(self) -> ColorScheme:
        """El esquema de color que corresponde a estas preferencias.

        **No eleva nunca.** Si el nombre guardado no existe —porque el archivo
        lo escribió otra versión del programa, o alguien lo editó a mano— se
        devuelve el de fábrica. Quedarse sin colores no es motivo para no
        arrancar.
        """
        try:
            return scheme_by_name(self.scheme_name)
        except PsgLabError:
            return scheme_by_name(DEFAULT_SCHEME_NAME)

    def with_scheme(self, scheme: ColorScheme) -> "Preferences":
        """Las mismas preferencias con el otro esquema elegido.

        Se guarda el nombre. Un esquema que no sea uno de los dos no se
        rechaza acá: `scheme()` lo resuelve al leer, devolviendo el de fábrica
        si el nombre ya no existe.
        """
        return replace(self, scheme_name=scheme.name)


def _rechazar(que: str, valor: object) -> None:
    """Eleva el error de un campo que el programa no puede usar."""
    raise InvalidPreferencesError(
        f"La configuración tiene un valor que no se puede usar en {que}.",
        details=f"Se recibió {valor!r}.",
    )


def _es_entero(valor: object) -> bool:
    """Un entero de verdad: `True` es un `int` para Python y no se acepta."""
    return isinstance(valor, int) and not isinstance(valor, bool)


def _es_numero(valor: object) -> bool:
    """Un número real, sin booleanos."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _validar_bandas(bandas: object) -> None:
    """Comprueba la tupla de bandas que guarda `Preferences`.

    La regla de qué banda se puede integrar **no se escribe acá**: es
    `psd.validate_band()`, la misma que usa el análisis. Acá sólo se comprueba
    la forma y que los nombres no se repitan, que es lo que la tabla necesita.
    """
    if not isinstance(bandas, tuple) or not bandas:
        _rechazar("las bandas del espectro", bandas)
    vistos: set[str] = set()
    for fila in bandas:
        if not isinstance(fila, tuple) or len(fila) != 3:
            _rechazar("las bandas del espectro", fila)
        nombre, desde, hasta = fila
        if not isinstance(nombre, str) or not nombre.strip():
            _rechazar("el nombre de una banda", nombre)
        if nombre in vistos:
            _rechazar("las bandas del espectro (nombre repetido)", nombre)
        vistos.add(nombre)
        if not (_es_numero(desde) and _es_numero(hasta)):
            _rechazar(f"la banda «{nombre}»", (desde, hasta))
        try:
            validate_band((desde, hasta))
        except PsgLabError as error:
            raise InvalidPreferencesError(
                f"La banda «{nombre}» no se puede usar: {error}",
                details=error.details,
            ) from error


def _validar_colores_de_clase(colores: object) -> None:
    """Comprueba la tupla de colores por clase de evento."""
    if not isinstance(colores, tuple):
        _rechazar("los colores de las anotaciones", colores)
    vistas: set[str] = set()
    for fila in colores:
        if not isinstance(fila, tuple) or len(fila) != 2:
            _rechazar("los colores de las anotaciones", fila)
        clase, color = fila
        if not isinstance(clase, str) or not clase.strip():
            _rechazar("el nombre de una clase de evento", clase)
        if clase in vistas:
            _rechazar("los colores de las anotaciones (clase repetida)", clase)
        vistas.add(clase)
        # **Con la regla de `core/` y no con la de pyqtgraph** (hito 48): la
        # sesión rechaza lo que no sea `#rrggbb`, y validar acá con otra
        # gramática dejaba pasar `red` hasta el dibujo. Lo que viene del
        # archivo ya llega normalizado por `_normalizar_color()`.
        if not es_color_de_clase(color):
            _rechazar(f"el color de la clase «{clase}»", color)


def config_dir() -> Path:
    """La carpeta donde el sistema espera que el programa guarde su configuración.

    En Windows es `%APPDATA%`, y en el resto `$XDG_CONFIG_HOME` o `~/.config`,
    que es la convención de freedesktop que siguen macOS y Linux en la práctica.
    Se resuelve a mano y no con `QStandardPaths` para que este módulo no dependa
    de Qt y se pueda testear sin levantar una aplicación gráfica.
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIRNAME
        return Path.home() / "AppData" / "Roaming" / APP_DIRNAME
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_DIRNAME
    return Path.home() / ".config" / APP_DIRNAME


def preferences_path() -> Path:
    """El archivo de preferencias del usuario."""
    return config_dir() / FILENAME


def load(path: Path | None = None) -> Preferences:
    """Lee las preferencias guardadas.

    Args:
        path: de dónde leer. Por omisión, el archivo del usuario.

    Returns:
        Lo guardado, o los valores por omisión si el archivo **no existe**, que
        es lo normal la primera vez que alguien abre el programa.

    Raises:
        InvalidPreferencesError: si el archivo existe pero no se puede leer o no
            tiene el formato esperado. **Se distingue del caso anterior a
            propósito**: que no haya archivo es normal, que lo haya y esté roto
            es algo que el usuario merece saber, aunque el programa siga.
    """
    destino = preferences_path() if path is None else path
    if not destino.exists():
        return Preferences()

    try:
        datos = json.loads(destino.read_text(encoding="utf-8"))
    except OSError as error:
        raise InvalidPreferencesError(
            "No se pudieron leer las preferencias guardadas. El programa abre "
            "con la configuración de fábrica.",
            details=f"No se pudo leer {destino}: {error}",
        ) from error
    except json.JSONDecodeError as error:
        raise InvalidPreferencesError(
            "El archivo de preferencias está dañado. El programa abre con la "
            "configuración de fábrica.",
            details=f"{destino} no es un JSON válido: {error}",
        ) from error

    if not isinstance(datos, dict):
        raise InvalidPreferencesError(
            "El archivo de preferencias no tiene el formato esperado. El "
            "programa abre con la configuración de fábrica.",
            details=f"{destino} tiene {type(datos).__name__} en vez de un objeto.",
        )

    nombre = datos.get("scheme_name", DEFAULT_SCHEME_NAME)
    if not isinstance(nombre, str):
        nombre = DEFAULT_SCHEME_NAME

    # **Las claves que ya no existen se ignoran**, sin error: `window_state`,
    # la disposición de paneles que se guardaba hasta el hito 24, y
    # `custom_scheme`, el esquema editado a mano que se quitó en el 35. Un
    # archivo viejo las sigue trayendo y eso no puede impedir arrancar.
    base = Preferences(scheme_name=nombre)
    return _con_campos_nuevos(base, datos)


def _con_campos_nuevos(base: Preferences, datos: dict[str, object]) -> Preferences:
    """Agrega los campos de la ventana de configuración, uno por uno.

    **Un campo roto vuelve a su valor de fábrica y no invalida el resto.** Es el
    mismo criterio que la disposición de paneles: todo esto se rehace con un
    gesto desde la ventana de configuración, y perder la tipografía porque una
    banda quedó mal escrita sería desproporcionado.

    La comprobación no se reescribe acá: se le pregunta al constructor de
    `Preferences`, que es donde vive.

    **Atrapa todo lo que un valor de JSON puede provocar** (hito 33): el archivo
    se edita a mano y un campo puede traer cualquier cosa. Hasta ahí atrapaba
    sólo `TypeError` y `ValueError`, y una banda de dos números elevaba
    `IndexError`, que atravesaba `load()` y **el programa no arrancaba**.
    """
    for nombre, convertir in _LECTORES.items():
        if nombre not in datos:
            continue
        try:
            base = base.with_changes(**{nombre: convertir(datos[nombre])})
        except _ERRORES_DE_UN_CAMPO:
            continue
    return base


def _leer_bandas(valor: object) -> tuple[tuple[str, float, float], ...] | None:
    """Del JSON —una lista de [nombre, desde, hasta]— a lo que guarda la clase.

    Comprueba la forma antes de desarmar cada fila; que los valores sirvan lo
    decide el constructor de `Preferences`.
    """
    if valor is None:
        return None
    if not isinstance(valor, list):
        raise TypeError("se esperaba una lista de bandas")
    filas = []
    for fila in valor:
        if not isinstance(fila, list) or len(fila) != 3:
            raise ValueError("cada banda es [nombre, desde, hasta]")
        filas.append((fila[0], fila[1], fila[2]))
    return tuple(filas)


def _leer_colores(valor: object) -> tuple[tuple[str, str], ...]:
    """Del JSON —un objeto {clase: color}— a lo que guarda la clase.

    Se escribe como objeto y no como lista porque es lo que alguien editaría a
    mano, y un objeto no puede repetir una clase.
    """
    if not isinstance(valor, dict):
        raise TypeError("se esperaba un objeto")
    return tuple((clase, _normalizar_color(color)) for clase, color in valor.items())


def _normalizar_color(color: object) -> object:
    """Lleva un color que se puede dibujar a la forma `#rrggbb`.

    **Es por donde entra texto arbitrario** —un archivo editado a mano— y la
    forma que `AnnotationSet.add_label()` acepta es una sola, porque el
    visualizador le concatena la transparencia al texto. Normalizar acá en vez
    de rechazar conserva lo que funcionaba: `red` sigue siendo rojo, como
    `#ff0000`. Es lo mismo que ya hace la ventana de configuración al elegir.

    Lo que no se puede dibujar pasa tal cual, para que el constructor lo
    rechace con su mensaje.
    """
    if not is_valid_color(color):
        return color
    return pg.mkColor(color).name()


def _identidad(valor: object) -> object:
    return valor


#: Cómo se lee cada campo nuevo desde el JSON. Los que no necesitan conversión
#: pasan tal cual y los comprueba el constructor.
_LECTORES: Final[dict[str, object]] = {
    "font_size": _identidad,
    "psd_method": _identidad,
    "psd_bands": _leer_bandas,
    "psd_log_power": _identidad,
    "annotation_colors": _leer_colores,
    "open_view_seconds": _identidad,
    "open_nomenclature": _identidad,
    "open_clock_axis": _identidad,
    "overview_before": _identidad,
    "overview_after": _identidad,
    "amplitude_band_uv": _identidad,
    "magnifier_radius_seconds": _identidad,
    "magnifier_zoom": _identidad,
}


def save(preferences: Preferences, path: Path | None = None) -> None:
    """Guarda las preferencias.

    Escribe primero en un archivo temporal al lado del definitivo y después lo
    reemplaza. **Sin eso, cerrar el programa en el momento justo deja un JSON
    truncado**, y el arranque siguiente se encuentra con un archivo roto en vez
    de con el anterior.

    Raises:
        InvalidPreferencesError: si no es un `Preferences`, o si no se pudo
            escribir.
    """
    if not isinstance(preferences, Preferences):
        raise InvalidPreferencesError(
            "No se pudieron guardar las preferencias.",
            details=f"Se recibió un objeto de tipo {type(preferences).__name__}.",
        )

    destino = preferences_path() if path is None else path
    datos: dict[str, object] = {
        "version": FORMAT_VERSION,
        "scheme_name": preferences.scheme_name,
    }
    # Los campos de la ventana de configuración. **Se escriben siempre**, aunque
    # tengan el valor de fábrica: el archivo es también lo que alguien abre
    # para ver qué puede cambiar. Una versión anterior del programa los ignora,
    # así que no hizo falta cambiar `FORMAT_VERSION`.
    datos["font_size"] = preferences.font_size
    datos["psd_method"] = preferences.psd_method
    datos["psd_bands"] = (
        None
        if preferences.psd_bands is None
        else [list(fila) for fila in preferences.psd_bands]
    )
    datos["psd_log_power"] = preferences.psd_log_power
    datos["annotation_colors"] = dict(preferences.annotation_colors)
    datos["open_view_seconds"] = preferences.open_view_seconds
    datos["open_nomenclature"] = preferences.open_nomenclature
    datos["open_clock_axis"] = preferences.open_clock_axis
    datos["overview_before"] = preferences.overview_before
    datos["overview_after"] = preferences.overview_after
    datos["amplitude_band_uv"] = preferences.amplitude_band_uv
    datos["magnifier_radius_seconds"] = preferences.magnifier_radius_seconds
    datos["magnifier_zoom"] = preferences.magnifier_zoom

    temporal = destino.with_name(destino.name + ".tmp")
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporal.replace(destino)
    except OSError as error:
        raise InvalidPreferencesError(
            "No se pudieron guardar las preferencias.",
            details=f"No se pudo escribir {destino}: {error}",
        ) from error


