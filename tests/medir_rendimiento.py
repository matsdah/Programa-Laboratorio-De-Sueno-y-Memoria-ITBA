"""Banco de medición del visualizador. **No es un test: no lo corre pytest.**

Se corre a mano, desde la raíz del proyecto:

    python -m tests.medir_rendimiento

Imprime una tabla y no afirma nada. Los tiempos dependen de la máquina, del
tamaño de la ventana y de lo que haya abierto al lado, así que un número de acá
sólo sirve **comparado contra otro de la misma corrida** o contra una corrida
anterior en la misma máquina. Por eso no es un test: una cota en segundos se
pone roja en la máquina de otro y nadie sabe si empeoró el programa o el día.

Qué mide:

- **Abrir un registro**, por partes, con el archivo real de `data/` si está.
  Ése no se versiona y el banco funciona igual sin él: la parte del dibujo usa
  un registro sintético.
- **Un paso de reproducción**, que es lo que el reloj pide veinticinco veces
  por segundo, con páginas de 5 s, 30 s, 5 min y el registro entero.
- Lo mismo sobre un registro **denso** —32 canales a 1000 Hz—, que es el caso
  que el registro de prueba no cubre: tiene cuarenta y cinco veces más muestras
  por página.
- **Un movimiento del mouse con la lupa**, sobre una página de 5 min con
  cientos de anotaciones: cada movimiento vuelve a pedir lo que dibujan las
  herramientas, y las bandas de anotación van incluidas.
- **Una flecha** sobre una noche de ocho horas con la mitad scoreada: lo que
  cuesta cambiar de época, con el hipnograma y la franja de posición.
- **Las anotaciones de una noche**, sin ventana: agregar miles, que es lo que
  hacen importar las marcas de un archivo, deshacer y la recuperación, y
  buscar las de un tramo de cinco minutos, que se pide en cada repintado.

**Se informa la mediana y no el promedio.** Una corrida cualquiera trae algún
cuadro que tardó el triple porque el sistema operativo hizo otra cosa, y el
promedio se lo lleva puesto.
"""

import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # pragma: no cover - para `python tests/medir...`
    sys.path.insert(0, str(RAIZ))

from psglab.app import create_application, create_main_window  # noqa: E402
from psglab.core.annotations import AnnotationSet  # noqa: E402
from psglab.core.nomenclature import Nomenclature  # noqa: E402
from psglab.core.recording import Channel, ChannelKind, Recording  # noqa: E402
from psglab.core.scoring import Scoring  # noqa: E402
from psglab.core.session import Session  # noqa: E402
from psglab.core.windows import count_windows  # noqa: E402
from psglab.readers.base import read_recording  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402

#: El registro real de prueba. No está versionado; si no está, se saltea.
REGISTRO = RAIZ / "data" / "SC4001E0-PSG.edf"

#: Tamaño de la ventana con que se mide. Fijo a propósito: el costo de un
#: cuadro crece con los píxeles que hay que pintar.
ANCHO, ALTO = 1400, 800

#: Cuántos cuadros se miden y cuántos se descartan antes. Los primeros pagan
#: la caché de envolventes y el primer dibujo de cada curva.
CUADROS = 40
CALENTAMIENTO = 5


def mediana_ms(funcion, veces: int = CUADROS) -> float:
    """La mediana de `veces` corridas, en milisegundos."""
    for _ in range(CALENTAMIENTO):
        funcion()
    tiempos = []
    for _ in range(veces):
        arranque = time.perf_counter()
        funcion()
        tiempos.append((time.perf_counter() - arranque) * 1000)
    return statistics.median(tiempos)


def fila(que: str, ms: float, extra: str = "") -> None:
    """Una línea de la tabla, con los cuadros por segundo que dan esos ms."""
    print(f"  {que:<44} {ms:8.1f} ms   {1000 / ms:5.1f} cuadros/s  {extra}")


def registro_sintetico(canales: int, frecuencia: float, minutos: float) -> Recording:
    """Un registro en memoria, para medir sin depender de `data/`.

    Ruido y una onda de 10 Hz, que es lo que dibuja una señal de verdad: una
    constante se decima a dos puntos por columna y mediría otra cosa.
    """
    muestras = int(frecuencia * minutos * 60)
    tiempo = np.arange(muestras) / frecuencia
    generador = np.random.default_rng(0)
    datos = np.empty((canales, muestras), dtype=float)
    for fila_canal in range(canales):
        datos[fila_canal] = 20 * np.sin(2 * np.pi * 10 * tiempo) + generador.normal(
            scale=5.0, size=muestras
        )
    return Recording(
        file_path=Path(f"sintetico-{canales}x{frecuencia:g}.vhdr"),
        channels=[
            Channel(name=f"EEG {i + 1}", kind=ChannelKind.EEG, unit="µV", index=i)
            for i in range(canales)
        ],
        data=datos,
        sampling_rate=frecuencia,
    )


def sesion_de(registro: Recording) -> Session:
    ventanas = count_windows(registro.n_samples, registro.sampling_rate)
    return Session(registro, Scoring(ventanas, Nomenclature.AASM), AnnotationSet())


def medir_apertura(ventana: MainWindow) -> None:
    """Abrir el registro real, entero y por partes."""
    print("\n== Abrir el registro real ==")
    if not REGISTRO.exists():
        print(f"  (no está {REGISTRO.relative_to(RAIZ)}: se saltea)")
        return

    # Una lectura previa, para que lo que se mida no sea el disco.
    read_recording(REGISTRO)

    arranque = time.perf_counter()
    registro = read_recording(REGISTRO)
    lectura = (time.perf_counter() - arranque) * 1000
    print(
        f"  {len(registro.channels)} canales, {registro.sampling_rate:g} Hz, "
        f"{registro.duration_seconds / 3600:.1f} h, "
        f"{registro.data.nbytes / 1e6:.0f} MB en memoria"
    )
    fila("read_recording()", lectura)

    arranque = time.perf_counter()
    ventana.open_recording(REGISTRO)
    QApplication.processEvents()
    fila("open_recording() por la ventana", (time.perf_counter() - arranque) * 1000)


def medir_dibujo(ventana: MainWindow, registro: Recording, titulo: str) -> None:
    """Un paso de reproducción con cada escala de tiempo."""
    print(f"\n== Un paso de reproducción: {titulo} ==")
    sesion = sesion_de(registro)
    ventana.signal_view.set_session(sesion)
    ventana._session = sesion
    QApplication.processEvents()

    for pagina in (5.0, 30.0, 300.0, registro.duration_seconds):
        if pagina > registro.duration_seconds:
            continue
        ventana.set_timescale(pagina)
        ventana._cambiar_pagina(sesion.viewport.with_start(0.0))
        # **Desde el hito 27 el paso mueve un cursor**, que arranca en el medio
        # de la página y la arrastra. Sin olvidarlo acá, cada escala seguiría
        # desde donde la dejó la anterior hasta el final del registro, donde la
        # página ya no se mueve y el paso no dibuja nada: medía 0,0 ms.
        ventana.playback_controller.stop()
        QApplication.processEvents()

        # Un quincuagésimo de página por paso: los cuarenta y cinco pasos de la
        # medición recorren menos de media página y el cursor no llega al borde
        # del registro, donde la página se queda quieta. Hasta el hito 27 era
        # un veinticincoavo desde un tercio del registro, y con la página de
        # 300 s la medición terminaba redibujando una página que no se movía.
        def paso() -> None:
            ventana.playback_controller.step(pagina / 50)
            QApplication.processEvents()

        entera = pagina >= registro.duration_seconds
        nombre = "registro entero" if entera else f"página de {pagina:g} s"
        # Con el registro entero la página no se puede mover: se mide redibujar.
        if entera:

            def paso() -> None:  # noqa: F811 - el caso en que no hay hacia dónde ir
                ventana.signal_view.draw_viewport()
                QApplication.processEvents()

        fila(nombre, mediana_ms(paso, veces=15 if entera else CUADROS))


def medir_overlays(ventana: MainWindow) -> None:
    """Un movimiento del mouse con la lupa, con muchas anotaciones en la página.

    Pasa por el camino entero —la herramienta avisa, el controlador junta lo
    que hay que dibujar y el visualizador lo dibuja—, que es el que la lupa y
    el anotador recorren con cada movimiento.
    """
    import tempfile

    from psglab.core.annotations import Annotation
    from tests.conftest import escribir_brainvision

    print("\n== Un movimiento del mouse con la lupa, página de 5 min ==")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = escribir_brainvision(Path(carpeta), segundos=600.0)
        ventana.open_recording(ruta)
    sesion = ventana.session
    frecuencia = sesion.recording.sampling_rate
    ventana.set_timescale(300.0)
    ventana._cambiar_pagina(sesion.viewport.with_start(0.0))
    canal = sesion.visible_channels[0]
    ventana.tool_controller.toggle("magnifier", True)
    lupa = ventana.tool_controller.tools["magnifier"]

    for cuantas in (0, 100, 400):
        for anotacion in list(sesion.annotations.all()):
            sesion.annotations.remove(anotacion)
        for numero in range(cuantas):
            inicio = int((numero * 290.0 / max(cuantas, 1) + 1.0) * frecuencia)
            sesion.annotations.add(
                Annotation("Spindle", onset_sample=inicio, duration_samples=int(frecuencia))
            )
        ventana.tool_controller.redraw_overlays()
        QApplication.processEvents()
        posicion = [10.0]

        def mover() -> None:
            posicion[0] = 10.0 + (posicion[0] + 0.7) % 250.0
            lupa.on_mouse_move(posicion[0], 0.0, canal)
            QApplication.processEvents()

        fila(f"{cuantas} anotaciones en la página", mediana_ms(mover))


def medir_flecha(ventana: MainWindow) -> None:
    """Una flecha, ida y vuelta, sobre una noche de ocho horas.

    **La mitad scoreada, con la fase cambiando cada pocas ventanas**, para que
    el hipnograma tenga cientos de tramos: es lo que tiene una noche real a
    medio scorear, y lo que el hipnograma rearmaba entero en cada flecha.
    """
    import tempfile

    from psglab.core.nomenclature import SleepStage
    from tests.conftest import escribir_brainvision

    print("\n== Una flecha, noche de 8 h (960 ventanas), la mitad scoreada ==")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = escribir_brainvision(Path(carpeta), segundos=8 * 3600.0, frecuencia=100.0)
        ventana.open_recording(ruta)
    sesion = ventana.session
    fases = (SleepStage.N1, SleepStage.N2, SleepStage.N3, SleepStage.R, SleepStage.WAKE)
    for indice in range(0, sesion.n_windows, 2):
        sesion.scoring.set_stage(indice, fases[(indice // 6) % len(fases)])
    ventana._reload_histogram()
    sesion.go_to_window(sesion.n_windows // 2)
    ventana.refresh()
    QApplication.processEvents()

    adelante = [True]

    def flecha() -> None:
        if adelante[0]:
            ventana.go_to_next_window()
        else:
            ventana.go_to_previous_window()
        adelante[0] = not adelante[0]
        QApplication.processEvents()

    fila("flecha a la derecha o a la izquierda", mediana_ms(flecha))


def medir_anotaciones() -> None:
    """Agregar miles de anotaciones y buscar las de un tramo, sin ventana."""
    import random

    from psglab.core.annotations import Annotation, AnnotationSet

    print("\n== Las anotaciones de una noche de 8 h a 100 Hz ==")
    azar = random.Random(0)
    for cuantas in (1_000, 5_000, 20_000):
        anotaciones = [
            Annotation("Spindle", azar.randrange(0, 8 * 3600 * 100), azar.randrange(50, 300))
            for _ in range(cuantas)
        ]
        conjunto = AnnotationSet()
        inicio = time.perf_counter()
        for anotacion in anotaciones:
            conjunto.add(anotacion)
        fila(f"agregar {cuantas} anotaciones", (time.perf_counter() - inicio) * 1000)

        def buscar() -> None:
            desde = azar.randrange(0, 8 * 3600 * 100)
            conjunto.in_range(desde, desde + 30_000)

        fila(f"las de 5 min, entre {cuantas}", mediana_ms(buscar))


def main() -> int:
    """Corre las mediciones sobre una ventana de tamaño fijo."""
    aplicacion = create_application(sys.argv)
    ventana = create_main_window()
    ventana.resize(ANCHO, ALTO)
    ventana.show()
    QApplication.processEvents()
    print(f"Ventana de {ANCHO}x{ALTO}. Mediana de {CUADROS} cuadros.")

    medir_apertura(ventana)
    medir_dibujo(ventana, registro_sintetico(7, 100.0, 10), "7 canales a 100 Hz")
    medir_dibujo(ventana, registro_sintetico(32, 1000.0, 10), "32 canales a 1000 Hz")
    medir_overlays(ventana)
    medir_flecha(ventana)
    medir_anotaciones()

    # **Sin esto el banco no termina.** Las mediciones anotan y scorean, y
    # cerrar con trabajo sin exportar abre un cartel modal que nadie contesta.
    if ventana.session is not None:
        ventana.session.mark_scoring_exported()
        ventana.session.mark_annotations_exported()
    ventana.close()
    del aplicacion
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
