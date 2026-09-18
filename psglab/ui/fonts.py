"""Las tipografías que el programa trae consigo.

Son dos familias de IBM Plex: **Sans**, que queda disponible en Configuración →
Tipografía junto a las del sistema, y **Mono**, la que el esquema «Papel» les da
a las lecturas numéricas (ver `theme.READOUT_PROPERTY`). Registrarlas no cambia
nada por sí solo: el programa sigue arrancando con la tipografía del sistema y
el esquema Claro, y las usa quien las elige.

**Los archivos no viven en esta carpeta** sino en `psglab/resources/fonts/`.
`psglab/ui/` no lleva subcarpetas, porque los chequeos de `test_consistencia.py`
la recorren sin entrar en ellas, y una carpeta `fonts/` al lado de este módulo
compartiría además su nombre.

**Se distribuyen bajo la SIL Open Font License 1.1**, que permite empaquetarlas
con un programa de cualquier licencia, el MIT de éste incluido, siempre que la
licencia viaje con los archivos: por eso `OFL.txt` está en la misma carpeta. El
control de licencias del CI sólo mira los paquetes de pip, así que esto está
documentado a mano en `docs/ARQUITECTURA.md`.

Cubre del pliego: ningún ID. Es infraestructura de presentación, como
`theme.py`.
"""

from pathlib import Path
from typing import Final

from PySide6.QtGui import QFontDatabase

#: Dónde están los archivos.
FONTS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "resources" / "fonts"

#: Los archivos que se registran. La negrita de Sans está porque los rótulos de
#: la interfaz la usan; de Mono alcanza la regular, que es la de las lecturas.
FONT_FILES: Final[tuple[str, ...]] = (
    "IBMPlexSans-Regular.ttf",
    "IBMPlexSans-SemiBold.ttf",
    "IBMPlexMono-Regular.ttf",
)

#: Qué familias dejó cada archivo ya registrado. Qt no deduplica: registrar dos
#: veces el mismo archivo lo carga dos veces.
_registradas: dict[Path, list[str]] = {}


def register_bundled_fonts(directory: Path = FONTS_DIR) -> list[str]:
    """Registra las tipografías del programa y devuelve sus familias, sin repetir.

    Se puede llamar más de una vez: lo ya registrado no se vuelve a cargar.

    **Un archivo que falta, o que Qt no puede leer, se saltea sin avisar.** Una
    tipografía es una preferencia visual: si no está, las lecturas y la
    configuración usan la del sistema, y eso es mejor que un programa que no
    arranca. Es el mismo criterio que con un archivo de preferencias roto.

    Necesita una `QGuiApplication` ya creada: la llama `create_application()`.

    Args:
        directory: la carpeta de donde se leen. Los tests la cambian para
            probar qué pasa cuando falta o está rota.
    """
    familias: list[str] = []
    for nombre in FONT_FILES:
        ruta = directory / nombre
        if ruta not in _registradas:
            if not ruta.is_file():
                continue
            identificador = QFontDatabase.addApplicationFont(str(ruta))
            if identificador < 0:
                continue
            _registradas[ruta] = QFontDatabase.applicationFontFamilies(identificador)
        for familia in _registradas[ruta]:
            if familia not in familias:
                familias.append(familia)
    return familias
