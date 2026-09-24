"""Banco de medición de la memoria. **No es un test: no lo corre pytest.**

Se corre a mano, desde la raíz del proyecto:

    python -m tests.medir_memoria
    python -m tests.medir_memoria --minutos 120 --canales 32 --frecuencia 256

Imprime una tabla y no afirma nada, por el mismo motivo que los otros dos
bancos: cuánta memoria hay depende de la máquina, y una cota escrita en un test
se pondría roja en la de al lado.

**Mide en copias, no en megabytes.** Una copia es lo que ocupa la señal entera
como `float64`, y es la unidad en que se razona: «filtrar cuesta 2,3 copias»
vale para cualquier registro, mientras que 1019 MB sólo vale para el que se
midió. Los megabytes van al lado para dimensionar.

Qué mide, siempre **por la ventana** —`open_recording()`, `_aplicar_analisis()`,
`restore_original_recording()`— y no llamando a los módulos sueltos, que es la
forma en que el hito 18 midió y la que no ve lo que la ventana retiene:

- **El pico** de cada operación: lo que tiene que caber para que no salga el
  cartel de memoria.
- **Lo que queda** después, recolectada la basura: lo que la ventana retiene
  mientras el investigador trabaja.
- **Quién retiene lo que queda**, por el lugar del código donde se reservó.

Se mide con `tracemalloc`, que numpy alimenta con cada array que reserva. Lo
que no pasa por el reservador de Python —el de Qt, el de las bibliotecas en C—
no se ve; para la señal no importa, porque vive entera en arrays de numpy.

El registro es un EDF sintético que se escribe en el temporal, igual que en los
tests: `data/` no se versiona y el banco tiene que andar sin él.
"""

import argparse
import gc
import os
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
for ruta in (RAIZ, RAIZ / "tests"):
    if str(ruta) not in sys.path:  # pragma: no cover - para `python tests/medir...`
        sys.path.insert(0, str(ruta))

# La memoria no depende de cómo se pinta, y así no aparece ninguna ventana.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from conftest import escribir_edf  # noqa: E402
from psglab.analysis.filters import DEFAULT_FILTERS, apply_filters, settings_for_kinds  # noqa: E402
from psglab.analysis.ica import apply_ica, explained_variance, fit_ica  # noqa: E402
from psglab.analysis.reference import average_reference  # noqa: E402
from psglab.app import create_application, create_main_window  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402

#: Un bloque que ocupe menos que esta fracción de una copia no se lista como
#: retenedor: hay cientos de reservas chicas y ninguna explica una copia.
FRACCION_PARA_LISTAR = 0.05


class Medidor:
    """Mide operaciones en copias de la señal, y dice quién retiene qué."""

    def __init__(self, bytes_por_copia: int) -> None:
        self.copia = bytes_por_copia
        tracemalloc.start(25)
        #: Lo que reserva el propio `tracemalloc` al formatear las trazas.
        self.filtros = [
            tracemalloc.Filter(False, tracemalloc.__file__),
            tracemalloc.Filter(False, "*linecache*"),
        ]
        gc.collect()
        self.base = tracemalloc.get_traced_memory()[0]

    def medir(self, que: str, operacion: Callable[[], object]) -> None:
        """Corre la operación e imprime su pico y lo que dejó retenido.

        Las dos cifras se cuentan **desde antes de abrir nada**, así que «queda»
        es todo lo que el programa sostiene en ese momento y no la diferencia
        con el paso anterior.

        **Y cuánto suma el paso**, que es el pico menos lo que ya había antes
        de empezar (hito 60). El pico solo engañaba: re-referenciar marcaba
        3,0 copias y sumaba una, la señal nueva que devuelve; las otras dos
        eran el original y la filtrada del paso anterior, y se propuso un hito
        para bajar algo que ya estaba en el mínimo.

        Imprime también cuánto tardó (hito 59): bajar la memoria partiendo el
        trabajo en pedazos puede costar tiempo, y hay que verlo al lado.
        **Con `tracemalloc` encendido**, que enlentece cada reserva: el número
        sirve para comparar dos corridas de este banco, no como el tiempo que
        ve el usuario.
        """
        gc.collect()
        antes = tracemalloc.get_traced_memory()[0] - self.base
        tracemalloc.reset_peak()
        arranque = time.perf_counter()
        operacion()
        QApplication.processEvents()
        segundos = time.perf_counter() - arranque
        pico = tracemalloc.get_traced_memory()[1] - self.base
        gc.collect()
        queda = tracemalloc.get_traced_memory()[0] - self.base
        print(
            f"  {que:<46} pico {pico / self.copia:4.1f} copias ({pico / 1e6:6.0f} MB)"
            f"   suma {(pico - antes) / self.copia:4.1f}"
            f"   queda {queda / self.copia:4.1f} ({queda / 1e6:6.0f} MB)"
            f"   {segundos:6.1f} s"
        )

    def retenedores(self) -> None:
        """Dónde se reservó cada bloque grande que sigue vivo."""
        gc.collect()
        instantanea = tracemalloc.take_snapshot().filter_traces(self.filtros)
        grandes = [
            estadistica
            for estadistica in instantanea.statistics("traceback")
            if estadistica.size >= FRACCION_PARA_LISTAR * self.copia
        ]
        print("    retenido por:")
        if not grandes:
            print("      (nada de más de un vigésimo de copia)")
        for estadistica in grandes:
            print(f"      {estadistica.size / self.copia:4.2f} copias  {_donde(estadistica.traceback)}")


def _donde(traza: tracemalloc.Traceback) -> str:
    """El marco más profundo del programa en la traza de una reserva.

    El más profundo de todos suele ser numpy o MNE, que no dice nada; el que
    importa es la línea de `psglab/` que la pidió.
    """
    propios = [marco for marco in traza if f"{os.sep}psglab{os.sep}" in marco.filename]
    marco = propios[-1] if propios else traza[-1]
    ruta = Path(marco.filename)
    try:
        ruta = ruta.relative_to(RAIZ)
    except ValueError:
        pass
    return f"{ruta.as_posix()}:{marco.lineno}"


def _filtrar(ventana: MainWindow) -> None:
    """Lo mismo que «Aplicar» en el panel de filtros con los de fábrica."""
    ventana._aplicar_analisis(
        "Se filtró la señal",
        lambda registro: apply_filters(registro, settings_for_kinds(registro, DEFAULT_FILTERS)),
    )


def _recorrer(ventana: MainWindow, ruta: Path, ica: bool) -> None:
    """Todas las operaciones que se miden, sin medir: el calentamiento."""
    ventana.open_recording(ruta)
    ventana.show_whole_recording()
    _filtrar(ventana)
    ventana._aplicar_analisis("Se re-referenció", average_reference)
    ventana.restore_original_recording()
    if ica:
        registro = ventana.session.recording
        descomposicion = fit_ica(registro)
        explained_variance(descomposicion, registro)
        ventana._aplicar_analisis("Se quitó", lambda r: apply_ica(r, descomposicion, [0]))
    ventana.restore_original_recording()
    QApplication.processEvents()


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--canales", type=int, default=32)
    argumentos.add_argument("--frecuencia", type=int, default=256)
    argumentos.add_argument("--minutos", type=int, default=60)
    argumentos.add_argument(
        "--sin-ica", action="store_true", help="saltea la ICA, que es lo más lento"
    )
    opciones = argumentos.parse_args()

    carpeta = Path(tempfile.mkdtemp(prefix="psglab-memoria-"))
    canales = [(f"EEG {i + 1}", "uV", opciones.frecuencia) for i in range(opciones.canales)]
    segundos = opciones.minutos * 60
    print(f"Escribiendo un EDF de {opciones.canales} canales a {opciones.frecuencia} Hz, "
          f"{opciones.minutos} min…")
    primero = escribir_edf(carpeta / "uno", segundos, canales)
    segundo = escribir_edf(carpeta / "dos", segundos, canales)

    aplicacion = create_application([sys.argv[0]])
    ventana = create_main_window()
    # Un cartel modal colgaría el banco sin decir nada: se imprime.
    ventana._show_error = lambda error: print(f"  !! cartel: {error}")  # type: ignore[method-assign]
    ventana._puede_descartarse_el_trabajo = lambda _que: True  # type: ignore[method-assign]
    ventana.resize(1400, 800)

    # **Una pasada entera sobre un registro chico antes de medir.** La primera
    # vez que se lee, se filtra o se ajusta una ICA se importan MNE, scipy y
    # scikit-learn, y eso son decenas de megabytes que no son de la señal: en
    # la primera corrida de este banco eran seis de las siete copias y media que
    # «quedaban» al abrir un registro de 20 MB.
    print("Calentando: una pasada sobre un registro de un minuto…")
    chico = escribir_edf(carpeta / "chico", 60, canales)
    _recorrer(ventana, chico, ica=not opciones.sin_ica)

    copia = opciones.canales * opciones.frecuencia * segundos * 8
    print(f"Una copia de la señal: {copia / 1e6:.0f} MB.\n")
    medidor = Medidor(copia)

    print("== Abrir y mirar ==")
    medidor.medir("abrir el registro", lambda: ventana.open_recording(primero))
    medidor.retenedores()
    medidor.medir("mostrar el registro entero", ventana.show_whole_recording)
    medidor.medir("volver a una página de 30 s", lambda: ventana.set_timescale(30.0))

    print("\n== Analizar y volver ==")
    medidor.medir("filtrar con los de fábrica", lambda: _filtrar(ventana))
    medidor.retenedores()
    medidor.medir("filtrar otra vez, encima", lambda: _filtrar(ventana))
    medidor.medir(
        "re-referenciar al promedio",
        lambda: ventana._aplicar_analisis("Se re-referenció", average_reference),
    )
    medidor.medir("volver a la señal original", ventana.restore_original_recording)
    medidor.retenedores()

    if not opciones.sin_ica:
        print("\n== ICA ==")
        ajuste: list = []

        # Lo mismo que el hilo de fondo de la ventana, en dos pasos: medidos
        # juntos, la varianza —que usa una cantidad fija de épocas— tapaba
        # cuánto bajó el ajuste en el hito 58 sobre un registro de una hora.
        medidor.medir(
            "ajustar la ICA", lambda: ajuste.append(fit_ica(ventana.session.recording))
        )
        medidor.medir(
            "medir la varianza de cada componente",
            lambda: explained_variance(ajuste[0], ventana.session.recording),
        )
        medidor.medir(
            "quitar un componente",
            lambda: ventana._aplicar_analisis(
                "Se quitó un componente", lambda r: apply_ica(r, ajuste[0], [0])
            ),
        )
        ajuste.clear()
        medidor.retenedores()

    print("\n== Otro registro ==")
    medidor.medir("abrir otro, con la señal procesada", lambda: ventana.open_recording(segundo))
    medidor.retenedores()

    ventana.close()
    del aplicacion
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
