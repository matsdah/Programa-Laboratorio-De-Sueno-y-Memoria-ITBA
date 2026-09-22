"""Las tipografías que el programa trae consigo.

Son dos familias de IBM Plex y **ninguna se elige**: **Sans** para todo lo que
se lee y **Mono** para todo lo que se mide. Son la misma superfamilia, dibujadas
juntas, así que una lectura numérica al lado de su etiqueta no cambia de voz.

## Por qué no hay lista de familias

Hasta el hito 43 Configuración → Tipografía ofrecía **todas las familias
instaladas en la máquina**, más una casilla para usar la del sistema. El
programa empaquetaba dos y no garantizaba ninguna: eran un valor por omisión.
Es el mismo argumento que dejó los colores en dos esquemas —una lista abierta
son infinitos aspectos posibles y ninguno garantizado— y la misma respuesta.
**El tamaño sí se elige**, que es lo que hace falta para ver de lejos.

## La escala

Ocho roles, en `ROLES`. Cada uno dice de qué familia es, cuántos puntos se
aparta del tamaño base, con qué peso y si va inclinado. **Los pasos se cuentan
desde el tamaño que el usuario elige**, así que subirlo agranda la interfaz
entera sin romper ninguna proporción.

Están acá y no en cada módulo porque hasta el hito 43 cada uno inventaba el
suyo: el canalón achicaba un punto y el chip dos, que son dos respuestas a la
misma pregunta. Es el mismo reparto que ya tienen los colores: el módulo dice
**qué cosa** está dibujando y no de qué tamaño.

## La itálica significa algo

Inclinada es **lo que nadie midió ni eligió**: «sin medir», «sin scorear», un
valor que el programa dedujo. Hasta acá eso lo cargaba el gris, que ya quiere
decir otra cosa —«esto es secundario»— y los dos se pisaban. Un valor ausente
no es secundario: es la advertencia más importante de la tabla de impedancias,
y ese módulo entero está construido alrededor de no confundirlo con un cero.

Falta empaquetar la itálica de verdad; ver `FONT_FILES`.

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

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PySide6.QtGui import QFont, QFontDatabase

from psglab.utils.errors import UnknownTypeRoleError

#: Dónde están los archivos.
FONTS_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "resources" / "fonts"

#: La familia de todo lo que se lee. Está acá y no en `preferences.py` porque
#: es el nombre que Qt le da a **estos archivos**: si alguna vez se cambian, el
#: nombre se corrige en el mismo lugar que la lista.
#:
#: **Ya no es una preferencia** (hito 43). Si los archivos no estuvieran,
#: `available_family()` devuelve None y la interfaz se queda con la del
#: sistema, que es degradar a lo conocido.
UI_FONT_FAMILY: Final[str] = "IBM Plex Sans"

#: La familia de todo lo que se mide: la hora, la ventana, los microvoltios.
#: **Es la hermana de ancho fijo de la otra**, no una familia distinta.
NUMERIC_FONT_FAMILY: Final[str] = "IBM Plex Mono"

#: Los archivos que se registran. La negrita de Sans está porque los rótulos de
#: la interfaz la usan; de Mono alcanza la regular, que es la de las lecturas.
#:
#: **Falta `IBMPlexSans-Italic.ttf`**, y es lo único que le queda al hito 43.
#: El rol `ausente` ya pide itálica y funciona: sin el archivo, Qt **sintetiza**
#: la inclinación deformando la regular, que se lee peor —las curvas se
#: estiran— pero se distingue igual de la recta. Agregarlo es soltarlo en
#: `psglab/resources/fonts/` y sumarlo a esta lista; entra bajo la misma OFL
#: 1.1 que los otros tres y pesa unos 80 kB.
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


def available_family(family: str = UI_FONT_FAMILY) -> str | None:
    """La familia pedida si Qt la tiene, o None si no.

    **Existe porque una tipografía que falta no puede empeorar el programa.**
    `QFont.setFamily()` con un nombre que no existe no avisa: Qt sustituye por
    la que le parece, que en Linux suele ser una serif genérica, y la ventana
    queda peor que con la del sistema. Preguntar antes es la diferencia entre
    degradar a lo conocido y degradar a cualquier cosa.

    Es el mismo criterio con que `register_bundled_fonts()` saltea un archivo
    que no puede leer: la tipografía es una preferencia visual, no un motivo
    para no arrancar.

    Args:
        family: el nombre a buscar. Por omisión, la de la interfaz.
    """
    return family if family in QFontDatabase.families() else None


@dataclass(frozen=True)
class TypeRole:
    """Qué tipografía le toca a una clase de texto.

    Attributes:
        family: `UI_FONT_FAMILY` o `NUMERIC_FONT_FAMILY`. **Son las dos
            únicas**: cualquier otra rompe la promesa del módulo.
        step: cuántos puntos se aparta del tamaño base que eligió el usuario.
            Negativo achica.
        bold: si va en semi-negrita.
        italic: si va inclinado. Ver el docstring del módulo: quiere decir
            «esto no lo midió ni lo eligió nadie», no «esto es importante».
        tracking: cuánto espacio extra entre letras, en píxeles. Sólo lo usa el
            rótulo de panel, que va en mayúsculas y sin aire se apelmaza.
    """

    family: str
    step: int = 0
    bold: bool = False
    italic: bool = False
    tracking: float = 0.0


#: Hasta dónde se achica un paso. Por debajo de esto no se lee, y un tamaño
#: base chico con un paso de −2 llegaría ahí.
MIN_POINT_SIZE: Final[int] = 6

#: Los ocho roles. **Tres tamaños y tres estilos**, sobre dos familias.
ROLES: Final[dict[str, TypeRole]] = {
    # Lo que se lee.
    "titulo": TypeRole(UI_FONT_FAMILY, step=2, bold=True),
    "cuerpo": TypeRole(UI_FONT_FAMILY),
    "secundario": TypeRole(UI_FONT_FAMILY, step=-1),
    "ausente": TypeRole(UI_FONT_FAMILY, step=-1, italic=True),
    "rotulo": TypeRole(UI_FONT_FAMILY, step=-2, bold=True, tracking=1.4),
    # Lo que se mide.
    "lectura": TypeRole(NUMERIC_FONT_FAMILY),
    "lectura_secundaria": TypeRole(NUMERIC_FONT_FAMILY, step=-1),
    "chip": TypeRole(NUMERIC_FONT_FAMILY, step=-2),
}


def font_for(role: str, base: QFont) -> QFont:
    """La tipografía de un rol, a partir del tamaño base de la interfaz.

    Args:
        role: una clave de `ROLES`.
        base: la tipografía de la aplicación, de la que sale el tamaño.

    Returns:
        Una `QFont` nueva; la de entrada no se toca.

    Raises:
        UnknownTypeRoleError: si el rol no existe. El nombre lo escribe quien
            dibuja, y un error de tipeo es la causa habitual; el mensaje los
            enumera, como hace `icons.icon()`.

    **La familia se pide sólo si Qt la tiene.** `QFont.setFamily()` con un
    nombre que no existe no avisa: sustituye por lo que le parece, que suele
    ser peor que la del sistema. Es el mismo criterio que `available_family()`.
    """
    if not isinstance(role, str) or role not in ROLES:
        raise UnknownTypeRoleError(
            f"No hay ningún rol tipográfico llamado «{role}».",
            details=f"Los disponibles son: {', '.join(ROLES)}.",
        )
    definicion = ROLES[role]
    fuente = QFont(base)
    familia = available_family(definicion.family)
    if familia is not None:
        fuente.setFamily(familia)
    # Un tamaño en píxeles —que Qt usa cuando `pointSize()` da −1— no se puede
    # desplazar en puntos sin cambiar de unidad. Ahí el rol se queda con el
    # tamaño de la base, que es lo que el usuario pidió.
    if base.pointSize() > 0:
        fuente.setPointSize(max(MIN_POINT_SIZE, base.pointSize() + definicion.step))
    fuente.setBold(definicion.bold)
    fuente.setItalic(definicion.italic)
    if definicion.tracking:
        fuente.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing, definicion.tracking
        )
    return fuente
