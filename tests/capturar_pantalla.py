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

import numpy as np

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

#: Con qué tamaño se captura un panel de análisis. Es el del artboard, para
#: poder compararlos uno al lado del otro.
ANCHO_DEL_PANEL: int = 720
ALTO_DEL_PANEL: int = 520

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
    llenar_los_paneles(ventana)
    QApplication.processEvents()
    return ventana


def llenar_los_paneles(ventana) -> None:
    """Les pone un resultado a los paneles de análisis, sin pasar por el menú.

    **A mano y no con `show_psd_dialog()`**, que es lo que haría el usuario:
    esas acciones abren `QInputDialog` para elegir el canal y la medida, y un
    cartel modal sobre una ventana con `WA_DontShowOnScreen` no se muestra en
    ninguna parte y nadie lo puede contestar. Es la misma trampa que el cartel
    del trabajo sin exportar, y por eso acá tampoco se cierra ninguna ventana.

    Lo que hay que mirar es la carrocería —el encabezado con su descripción y
    su método, la tabla de bandas— y para eso alcanza con datos plausibles.
    """
    frecuencias = np.linspace(0.5, 45.0, 180)
    potencias = 40.0 / frecuencias**1.35 + 4.5 * np.exp(-(((frecuencias - 10.2) / 1.5) ** 2))
    ventana.psd_panel.set_spectrum(frecuencias, potencias[None, :], ["C3"])
    ventana.psd_panel.set_method_description("Welch · segmento 4 s · Hann · solape 50 %")
    ventana.psd_panel.set_band_powers(
        {
            nombre: (valor, fraccion)
            for nombre, valor, fraccion in (
                ("Delta", 128.4, 0.612),
                ("Theta", 41.7, 0.199),
                ("Alpha", 18.9, 0.090),
                ("Sigma", 11.2, 0.053),
                ("Beta", 6.3, 0.030),
                ("Gamma", 1.8, 0.009),
            )
        }
    )
    ventana.psd_panel.set_caption("Ventana 1 · C3 (EEG)")

    epocas = np.arange(ventana.session.n_windows, dtype=float)
    ventana.metric_panel.set_metric(
        "Entropía espectral",
        {"C3": 0.62 + 0.13 * np.sin(epocas / 3.0), "EOG-izq": 0.7 + 0.08 * np.cos(epocas / 4.0)},
    )
    ventana.metric_panel.set_caption("Entropía espectral · 2 canales")

    ventana.impedance_panel.set_channels(
        ventana.session.visible_channels,
        {nombre: 3.2 + 4.0 * posicion for posicion, nombre in enumerate(ventana.session.visible_channels[:2])},
    )
    # **`refresh()` antes de leer**: la Übersicht cachea sus ventanas y las
    # rearma al cambiar de época. Acá se scorea sin navegar, igual que al
    # anotar, así que sin esto el chip de la fase saldría vacío.
    contexto = ventana._tools["overview"]
    contexto.refresh()
    ventana.overview_panel.set_windows(contexto.windows(), {})

    # El panel de ICA con una descomposición de mentira: lo que hay que mirar
    # es el encabezado y las dos columnas, no de dónde salen los pesos.
    ventana.ica_panel.set_components(
        [
            {nombre: 0.8 - 0.3 * posicion for posicion, nombre in enumerate(ventana.session.visible_channels)},
            {nombre: -0.2 + 0.5 * posicion for posicion, nombre in enumerate(ventana.session.visible_channels)},
        ]
    )

    # **Se les pide un mínimo y no un `resize()`.** Un panel adentro de un dock
    # recibe el tamaño que el dock le da, así que redimensionarlo a mano no
    # hace nada: la captura salía del alto del dock —unos 180 px— y los
    # rótulos aparecían cortados por una compresión que en la ventana de
    # verdad no ocurre. Con el mínimo puesto, el layout se lo concede.
    for clave in ("psd", "metric", "impedance", "overview", "filter", "ica"):
        ventana.docks[clave].show()
        ventana.docks[clave].widget().setMinimumSize(ANCHO_DEL_PANEL, ALTO_DEL_PANEL)


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
        f"{nombre}-espectro": ventana.psd_panel,
        f"{nombre}-metrica": ventana.metric_panel,
        f"{nombre}-impedancia": ventana.impedance_panel,
        f"{nombre}-contexto": ventana.overview_panel,
        f"{nombre}-filtros": ventana.filter_panel,
        f"{nombre}-ica": ventana.ica_panel,
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
