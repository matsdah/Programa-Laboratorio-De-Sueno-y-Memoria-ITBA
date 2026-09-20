"""Capturas de la ventana, para mirar el aspecto en vez de suponerlo.

**No es un test y pytest no lo recolecta**, como los dos bancos de medición: se
corre a mano y deja archivos PNG. Lo que un test puede afirmar de la interfaz
es la estructura —qué controles hay, de qué tamaño, con qué texto—; **cómo se
ve** no se puede afirmar, y por eso hasta acá se revisaba abriendo el programa.

    python -m tests.capturar_pantalla

**Y no corre offscreen, a propósito**, igual que `medir_reparto.py`: el plugin
"offscreen" no trae tipografías ni el estilo nativo, así que una captura hecha
así muestra cuadraditos donde van las letras y no sirve para juzgar nada.

**No abre ninguna ventana en la pantalla de quien lo corre.**
`WA_DontShowOnScreen` le pide a Qt que maquete el widget completo sin mapearlo:
hace falta porque un widget que nunca se mostró no tiene layout, y capturarlo
da una barra colapsada. Es la diferencia entre una captura fiel y una inútil.

**Qué encontró la primera vez que se usó** (hito 36), y que ningún test veía:
el identificador del registro salía cortado a un tercio, porque `QMenuBar` le
da a su widget de esquina un ancho que cachea; y el icono del botón de
reproducir se dibujaba con la tinta de los demás sobre el relleno de acento,
2,87 a 1 de contraste, porque lo corregía `apply_scheme()` y eso sólo corre al
cambiar de esquema. En el hito 37 encontró la etiqueta de cada canal dibujada
encima de su propia señal, que es de donde salió `psglab/ui/channel_axis.py`.

**Las ventanas no se cierran, y no es un descuido.** Cerrar la ventana
principal es cerrar el programa, así que `closeEvent` pregunta por el trabajo
sin exportar —y acá siempre hay: se scorea media noche para que la franja y el
hipnograma tengan forma—. Ese cartel es modal, y una ventana con
`WA_DontShowOnScreen` no lo muestra en ninguna parte: el proceso se quedaba
colgado para siempre después del primer esquema, sin consumir CPU y sin decir
nada. Quedan vivas hasta que termina el proceso, que es lo que hace `VENTANAS`.
"""

import os
import pathlib
import sys
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

from conftest import escribir_brainvision  # noqa: E402

# **Importar `conftest` deja fijado `QT_QPA_PLATFORM=offscreen`**, que es lo que
# la suite necesita y lo único que esta herramienta no puede usar. Se lo quita
# antes de que exista una `QApplication`, que es cuando Qt lo lee. Se importa
# igual porque de ahí sale el escritor de BrainVision sintético, y duplicarlo
# acá sería un segundo formato que mantener.
os.environ.pop("QT_QPA_PLATFORM", None)

from psglab.app import create_main_window  # noqa: E402
from psglab.core.nomenclature import Nomenclature, stages_of  # noqa: E402
from psglab.ui import theme  # noqa: E402

#: Dónde quedan los PNG. En el temporal del sistema y no en el repositorio:
#: son para mirar una vez, no para versionar.
SALIDA: pathlib.Path = pathlib.Path(tempfile.gettempdir()) / "psglab-capturas"

#: Cuánto dura el registro sintético. Veinte épocas alcanzan para que la franja
#: tenga tramos y el hipnograma, forma.
SEGUNDOS: int = 30 * 20

#: El tamaño con que se captura. Es el de los artboards del diseño, para poder
#: compararlos uno al lado del otro.
ANCHO: int = 1440
ALTO: int = 760

#: Las ventanas que se armaron, para que no las recoja el recolector de basura
#: mientras se arma la siguiente. Ver el docstring del módulo: **no se
#: cierran**.
VENTANAS: list[object] = []


def armar_ventana(esquema: theme.ColorScheme):
    """Una ventana con un registro sintético y media noche scoreada."""
    ventana = create_main_window()
    ventana.set_color_scheme(esquema, remember=False)
    ventana.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    ventana.resize(ANCHO, ALTO)
    ventana.show()
    QApplication.processEvents()

    carpeta = pathlib.Path(tempfile.mkdtemp())
    ventana.open_recording(escribir_brainvision(carpeta, segundos=SEGUNDOS))
    fases = list(stages_of(Nomenclature.AASM))
    for posicion in range(ventana.session.n_windows // 2):
        ventana.session.scoring.set_stage(posicion, fases[posicion % len(fases)])
    ventana._reload_histogram()
    QApplication.processEvents()
    return ventana


def capturar(esquema: theme.ColorScheme) -> None:
    """Guarda la ventana entera y sus dos barras, con ese esquema."""
    ventana = armar_ventana(esquema)
    VENTANAS.append(ventana)
    nombre = esquema.name.lower()
    piezas = {
        f"{nombre}-ventana": ventana,
        f"{nombre}-menu": ventana.menuBar(),
        f"{nombre}-navegacion": ventana.navigation_bar,
        f"{nombre}-scoring": ventana.scoring_panel,
    }
    for archivo, widget in piezas.items():
        destino = SALIDA / f"{archivo}.png"
        widget.grab().save(str(destino))
        print(f"  {destino}")


def main() -> None:
    """Captura las dos barras y la ventana, con los dos esquemas."""
    QApplication.instance() or QApplication([])
    SALIDA.mkdir(parents=True, exist_ok=True)
    for esquema in theme.SCHEMES.values():
        print(f"== {esquema.name} ==")
        capturar(esquema)


if __name__ == "__main__":
    main()
