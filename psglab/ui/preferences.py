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
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

from psglab.ui.theme import (
    DEFAULT_SCHEME_NAME,
    ColorScheme,
    scheme_by_name,
    scheme_from_dict,
    scheme_to_dict,
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


@dataclass(frozen=True)
class Preferences:
    """Las preferencias del usuario.

    Inmutable, igual que `ColorScheme`: cambiar una preferencia es construir
    otra con `replace()`, no escribirle encima a la que está en uso. Así nadie
    puede dejar el objeto a medio actualizar si algo falla en el medio.

    Attributes:
        scheme_name: nombre del esquema de color elegido. Se guarda el nombre y
            no el esquema entero mientras sea uno de fábrica, para que
            mejorarlos en una versión nueva alcance a quien ya los eligió.
        custom_scheme: el esquema completo, cuando el usuario lo modificó y ya
            no es ninguno de fábrica. None mientras use uno de los cinco.
        window_state: la disposición de los paneles acoplables, tal como la
            serializa `QMainWindow.saveState()`, en base64. Se guarda como
            texto opaco **y este módulo no la interpreta**: es un formato de Qt
            y entenderlo sería atarse a su versión.
    """

    scheme_name: str = DEFAULT_SCHEME_NAME
    custom_scheme: ColorScheme | None = None
    window_state: str | None = None

    def with_window_state(self, state: str | None) -> "Preferences":
        """Las mismas preferencias con otra disposición de paneles."""
        return replace(self, window_state=state)

    def scheme(self) -> ColorScheme:
        """El esquema de color que corresponde a estas preferencias.

        **No eleva nunca.** Si el nombre guardado no existe —porque el archivo
        lo escribió otra versión del programa, o alguien lo editó a mano— se
        devuelve el de fábrica. Quedarse sin colores no es motivo para no
        arrancar.
        """
        if self.custom_scheme is not None:
            return self.custom_scheme
        try:
            return scheme_by_name(self.scheme_name)
        except PsgLabError:
            return scheme_by_name(DEFAULT_SCHEME_NAME)

    def with_scheme(self, scheme: ColorScheme) -> "Preferences":
        """Las mismas preferencias con otro esquema elegido.

        Si el esquema es uno de fábrica se guarda sólo su nombre; si no, se
        guarda entero.
        """
        try:
            de_fabrica = scheme_by_name(scheme.name) == scheme
        except PsgLabError:
            de_fabrica = False
        if de_fabrica:
            return replace(self, scheme_name=scheme.name, custom_scheme=None)
        return replace(self, scheme_name=scheme.name, custom_scheme=scheme)


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

    propio = datos.get("custom_scheme")
    esquema = scheme_from_dict(propio) if isinstance(propio, dict) else None

    disposicion = datos.get("window_state")
    if not isinstance(disposicion, str):
        # **No eleva.** Una disposición ilegible se descarta y la ventana abre
        # con la de fábrica: es lo único de este archivo que el usuario puede
        # rehacer con un gesto, así que no vale la pena molestarlo.
        disposicion = None

    return Preferences(
        scheme_name=nombre, custom_scheme=esquema, window_state=disposicion
    )


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
    if preferences.custom_scheme is not None:
        datos["custom_scheme"] = scheme_to_dict(preferences.custom_scheme)
    if preferences.window_state is not None:
        datos["window_state"] = preferences.window_state

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


def load_scheme(path: Path) -> ColorScheme:
    """Lee un esquema de color de un archivo suelto.

    Es lo que hace el botón "Cargar" de la referencia. Un esquema es un archivo
    propio y no una entrada de las preferencias justamente para que el
    laboratorio pueda pasarse uno por correo y que todas las máquinas se vean
    igual.

    Raises:
        InvalidPreferencesError: si el archivo no se puede leer o no es un JSON.
        UnknownColorSchemeError: si es un JSON pero no describe un esquema.
    """
    try:
        datos = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise InvalidPreferencesError(
            "No se pudo abrir el archivo de esquema de color.",
            details=f"No se pudo leer {path}: {error}",
        ) from error
    except json.JSONDecodeError as error:
        raise InvalidPreferencesError(
            "El archivo no es un esquema de color válido.",
            details=f"{path} no es un JSON válido: {error}",
        ) from error
    return scheme_from_dict(datos)


def save_scheme(path: Path, scheme: ColorScheme) -> None:
    """Escribe un esquema de color en un archivo suelto.

    Raises:
        UnknownColorSchemeError: si no es un `ColorScheme`.
        InvalidPreferencesError: si no se pudo escribir.
    """
    datos = scheme_to_dict(scheme)
    try:
        Path(path).write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as error:
        raise InvalidPreferencesError(
            "No se pudo guardar el esquema de color.",
            details=f"No se pudo escribir {path}: {error}",
        ) from error
