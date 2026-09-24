"""Banco de medición del reparto de los paneles de abajo. **No es un test.**

Se corre a mano, desde la raíz del proyecto:

    python -m tests.medir_reparto

Imprime una tabla y no afirma nada, por el mismo motivo que
`medir_rendimiento.py`: **los mínimos de los paneles salen de métricas de
fuente**, así que dependen del escalado de pantalla, del tema y de la tipografía
del sistema. Un número de acá vale para la máquina que lo sacó. Fijarlo como
cota en un test lo pondría rojo en la de al lado sin que nadie sepa cuál de las
dos está mal.

**Y no corre offscreen a propósito.** El plugin "offscreen" no usa el estilo
nativo, que es justamente lo que decide cuánto mide un botón de fase: medir con
él daría otros mínimos y otro reparto. Por eso abre una ventana de verdad, al
revés que la suite, que fija `QT_QPA_PLATFORM=offscreen` en `conftest.py`.

Qué mide, para cada ancho de ventana y cada nomenclatura:

- **Cuánto recibe cada panel de abajo** después de `repartir_abajo()`, con su
  posición, para ver dónde arranca la fila y si alguno quedó fuera.
- **El mínimo de cada uno**, que es lo que Qt atiende antes que la proporción
  de `ANCHOS_DE_ABAJO` y lo que explica el reparto que sale.
- **El ancho del panel de canales y el de la señal**, que son lo que queda.
- **La pila de análisis de la derecha**: cuánto recibe al abrir uno de sus
  paneles, el mínimo de cada uno de los seis y cuánto le queda a la señal.

Con el registro de `data/` si está —el árbol de canales cambia de ancho con los
nombres que trae—, y con uno sintético si no, que no se versiona.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover - para `python tests/medir...`
    sys.path.insert(0, str(RAIZ))

from psglab.app import create_application, create_main_window  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.ui.docks import ANCHOS_DE_ABAJO, ORDEN_DE_ANALISIS, repartir_abajo  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from tests.medir_rendimiento import registro_sintetico, sesion_de  # noqa: E402

#: El registro real de prueba, el mismo que usa el otro banco.
REGISTRO = RAIZ / "data" / "SC4001E0-PSG.edf"

#: Los anchos que se miden. 1400 es la ventana con la que se midió el hito 25;
#: 1280 es la pantalla chica que todavía se usa; los otros dos están alrededor
#: del punto en que el scoring pasa a ser más ancho que el hipnograma.
ANCHOS: tuple[int, ...] = (1400, 1280, 1170, 1050)

#: El alto no cambia nada del reparto, que es horizontal. Se fija para que la
#: tabla no dependa de con qué tamaño quedó abierta la ventana.
ALTO: int = 800

#: Los tres paneles del borde inferior, con el nombre que ve el usuario.
ABAJO: tuple[str, ...] = ("overview", "scoring", "histogram")
ROTULOS: dict[str, str] = {
    "overview": "Contexto",
    "scoring": "Scoring",
    "histogram": "Hipnograma",
}


def asentar(veces: int = 3) -> None:
    """Deja que Qt termine de acomodar la ventana antes de medirla.

    Un solo `processEvents()` no alcanza: el reparto se pide después del
    `resize()` y cada uno genera sus propios eventos de layout.
    """
    for _ in range(veces):
        QApplication.processEvents()


def medir(ventana: MainWindow, ancho: int, nomenclatura: Nomenclature) -> None:
    """Imprime el reparto con ese ancho de ventana y esa nomenclatura."""
    ventana.scoring_panel.set_nomenclature(nomenclatura)
    ventana.resize(ancho, ALTO)
    asentar()
    repartir_abajo(ventana)
    asentar()

    print(f"\n== Ventana de {ventana.width()} px · {nomenclatura.value} ==")
    canales = ventana.docks["channels"]
    print(f"  {'Canales (izquierda)':<21} x={canales.geometry().x():4d}  {canales.width():4d} px")
    total = 0
    for clave in ABAJO:
        dock = ventana.docks[clave]
        total += dock.width()
        print(
            f"  {ROTULOS[clave]:<21} x={dock.geometry().x():4d}  {dock.width():4d} px"
            f"   (mínimo {dock.minimumSizeHint().width():3d},"
            f" pedido {ANCHOS_DE_ABAJO[clave]})"
        )
    desde = ventana.docks[ABAJO[0]].geometry().x()
    print(f"  {'Suma de los tres':<21} x={desde:4d}  {total:4d} px")
    central = ventana.centralWidget().geometry()
    print(f"  {'Señal':<21} x={central.x():4d}  {central.width():4d} px")


def medir_analisis(ventana: MainWindow, ancho: int) -> None:
    """Imprime cuánto recibe la pila de análisis con ese ancho de ventana.

    Se abre el espectro, que es el primero que pide el investigador; los seis
    están apilados en solapas, así que el ancho de uno es el de la pila.
    """
    ventana.resize(ancho, ALTO)
    asentar()
    pila = ventana.docks["psd"]
    pila.show()
    asentar()
    central = ventana.centralWidget().geometry()
    print(f"\n== Análisis con una ventana de {ventana.width()} px ==")
    print(f"  {'Pila (derecha)':<28} x={pila.geometry().x():4d}  {pila.width():4d} px")
    print(f"  {'Señal':<28} x={central.x():4d}  {central.width():4d} px")
    for clave, titulo in ORDEN_DE_ANALISIS:
        minimo = ventana.docks[clave].minimumSizeHint().width()
        print(f"  {titulo:<28} mínimo {minimo:4d} px")
    pila.hide()
    asentar()


def preparar(ventana: MainWindow) -> None:
    """Carga un registro y deja los tres paneles de abajo a la vista.

    Sin registro los paneles existen igual, pero el árbol de canales queda
    vacío y su ancho no es el que ve el investigador.
    """
    if REGISTRO.exists():
        print(f"Registro: {REGISTRO.relative_to(RAIZ)}")
        ventana.open_recording(REGISTRO)
    else:
        print(f"(no está {REGISTRO.relative_to(RAIZ)}: se mide con uno sintético)")
        registro = registro_sintetico(7, 100.0, 10)
        sesion = sesion_de(registro)
        ventana.signal_view.set_session(sesion)
        ventana._session = sesion
    asentar()
    for clave in ABAJO:
        ventana.docks[clave].show()
    asentar()
    repartir_abajo(ventana)
    asentar()


def main() -> int:
    """Mide el reparto con cada ancho y cada nomenclatura."""
    aplicacion = create_application(sys.argv)
    ventana = create_main_window()
    ventana.resize(ANCHOS[0], ALTO)
    ventana.show()
    asentar()
    preparar(ventana)

    for nomenclatura in (Nomenclature.RK, Nomenclature.AASM):
        for ancho in ANCHOS:
            medir(ventana, ancho, nomenclatura)
    for ancho in ANCHOS[:2]:
        medir_analisis(ventana, ancho)

    ventana.close()
    del aplicacion
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
