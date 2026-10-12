#!/usr/bin/env python3
"""Mide cambios en el recuento de referencias de ``None`` al llamar Qt.

Ejecute un modo por proceso descartable. El script informa las mediciones y no
afirma un resultado esperado. En CPython 3.12 o posterior, ``None`` es
inmortal y su recuento no sirve para diagnosticar este problema.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import time
from collections.abc import Sequence


MODES = (
    "translate",
    "translator",
    "translator-owner",
    "plotitem",
    "colorbar",
    "settext",
    "tooltip",
    "spinbox",
    "objectname",
)


def positive_int(value: str) -> int:
    """Convierte un entero positivo para las opciones de la línea de comandos."""
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("debe ser un entero") from error
    if number < 1:
        raise argparse.ArgumentTypeError("debe ser mayor que cero")
    return number


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Lee y valida las opciones de la medición."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=MODES,
        default="objectname",
        help="operación Qt que se repite; se ejecuta una sola por proceso",
    )
    parser.add_argument(
        "--translation",
        choices=("none", "empty", "native-es"),
        default="none",
        help="traductor de la aplicación para el modo translate",
    )
    parser.add_argument(
        "--iterations",
        type=positive_int,
        default=1000,
        help="cantidad de llamadas después del calentamiento",
    )
    parser.add_argument(
        "--sample-every",
        type=positive_int,
        default=100,
        help="intervalo entre mediciones del recuento",
    )
    parser.add_argument(
        "--floor",
        type=positive_int,
        default=None,
        help="piso positivo; por omisión usa 2048 para Qt o 10000 para gráficos",
    )
    parser.add_argument(
        "--drop-translator-wrapper",
        action="store_true",
        help="descarta el envoltorio Python del traductor con padre, antes de las llamadas",
    )
    args = parser.parse_args(argv)
    if args.translation != "none" and args.mode != "translate":
        parser.error("--translation sólo se usa con --mode translate")
    if args.drop_translator_wrapper and args.mode != "translator-owner":
        parser.error("--drop-translator-wrapper requiere --mode translator-owner")
    if args.floor is None:
        args.floor = 10000 if args.mode in {"plotitem", "colorbar"} else 2048
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta una medición aislada y escribe sus resultados como JSON."""
    args = parse_args(argv)
    implementation = platform.python_implementation()
    if implementation != "CPython" or not hasattr(sys, "getrefcount"):
        print(
            "Error: la medición requiere CPython y sys.getrefcount().",
            file=sys.stderr,
            flush=True,
        )
        return 2
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import PySide6
    import shiboken6
    from PySide6 import QtCore, QtWidgets

    pg = None
    if args.mode in {"plotitem", "colorbar"}:
        import pyqtgraph as pg

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(
        ["qt-refcount-probe"]
    )

    def refcount() -> int:
        return sys.getrefcount(None)

    gc.collect()
    initial_refcount = refcount()
    measurement_meaningful = (
        sys.version_info < (3, 12)
        and initial_refcount < 2**31
    )
    environment = {
        "python": sys.version.split()[0],
        "implementation": implementation,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pyside6": PySide6.__version__,
        "shiboken6": shiboken6.__version__,
        "qt": QtCore.qVersion(),
        "pyqtgraph": pg.__version__ if pg is not None else None,
        "pyqtgraph_imported": pg is not None,
        "mode": args.mode,
        "iterations": args.iterations,
        "sample_every": args.sample_every,
        "floor": args.floor,
        "translation": args.translation,
        "drop_translator_wrapper": args.drop_translator_wrapper,
        "initial_none_refcount": initial_refcount,
        "none_refcount_mortal": measurement_meaningful,
        "diagnostic": measurement_meaningful,
    }
    print(json.dumps({"environment": environment}, sort_keys=True), flush=True)
    if not measurement_meaningful:
        print(
            "Aviso: este intérprete no permite diagnosticar cambios con el "
            "recuento de None; las mediciones siguientes no son concluyentes.",
            file=sys.stderr,
            flush=True,
        )

    translator = None
    owner_translator = None
    if args.mode == "translator" or (
        args.mode == "translate" and args.translation != "none"
    ):
        translator = QtCore.QTranslator()
        if args.mode == "translate" and args.translation == "native-es":
            translations = QtCore.QLibraryInfo.path(
                QtCore.QLibraryInfo.LibraryPath.TranslationsPath
            )
            loaded = translator.load("qtbase_es", translations)
        else:
            loaded = True
        installed = app.installTranslator(translator) if loaded else False
        details = {
            "modo": args.mode,
            "traductor": args.translation if args.mode == "translate" else "empty",
            "cargado": loaded,
            "instalado": installed,
        }
        if args.mode == "translate":
            details["acierto"] = QtCore.QCoreApplication.translate(
                "QDialogButtonBox", "OK"
            )
            details["falta"] = QtCore.QCoreApplication.translate("Form", "Peak")
        print(json.dumps(details), flush=True)

    if args.mode == "translator-owner":
        # Reproduce el traductor nativo con la aplicación como padre QObject.
        owner_translator = QtCore.QTranslator(app)
        translations = QtCore.QLibraryInfo.path(
            QtCore.QLibraryInfo.LibraryPath.TranslationsPath
        )
        loaded = owner_translator.load("qtbase_es", translations)
        installed = app.installTranslator(owner_translator) if loaded else False
        print(
            json.dumps(
                {
                    "modo": args.mode,
                    "traductor_cargado": loaded,
                    "instalado": installed,
                    "antes_de_descartar": refcount(),
                    "acierto": QtCore.QCoreApplication.translate(
                        "QDialogButtonBox", "OK"
                    ),
                    "falta": QtCore.QCoreApplication.translate("Form", "Peak"),
                }
            ),
            flush=True,
        )
        if args.drop_translator_wrapper:
            del owner_translator
            owner_translator = None
            gc.collect()
            print(
                json.dumps(
                    {"modo": args.mode, "envoltorio_descartado": True, "despues": refcount()}
                ),
                flush=True,
            )

    widget = None
    if args.mode == "settext":
        widget = QtWidgets.QLabel()
    elif args.mode == "tooltip":
        widget = QtWidgets.QWidget()
    elif args.mode == "spinbox":
        widget = QtWidgets.QSpinBox()
    elif args.mode == "objectname":
        widget = QtCore.QObject()

    def operation() -> None:
        if args.mode == "translate":
            # Compara los overloads de dos argumentos y de None explícito.
            QtCore.QCoreApplication.translate("Probe", "miss")
            QtCore.QCoreApplication.translate("Probe", "miss", None)
            QtCore.QCoreApplication.translate("Probe", "hit", None, 1)
        elif args.mode == "translator":
            translator.translate("Probe", "miss", None)
            translator.translate("Probe", "hit", None, 1)
        elif args.mode == "translator-owner":
            QtCore.QCoreApplication.translate("QPlatformTheme", "OK")
            QtCore.QCoreApplication.translate("QPlatformTheme", "Cancel", None)
        elif args.mode == "plotitem":
            item = pg.PlotItem()
            del item
        elif args.mode == "colorbar":
            item = pg.ColorBarItem(values=(0, 1))
            del item
        elif args.mode == "settext":
            widget.setText("probe")
        elif args.mode == "tooltip":
            widget.setToolTip("probe")
        elif args.mode == "spinbox":
            widget.setValue(1)
        elif args.mode == "objectname":
            widget.setObjectName("probe")

    # Descarta asignaciones de inicialización sin cruzar el piso de seguridad.
    warmup_count = 0
    warmup_stopped = False
    if measurement_meaningful and initial_refcount <= args.floor:
        warmup_stopped = True
    for _ in range(min(10, args.iterations)):
        if warmup_stopped:
            break
        if measurement_meaningful and refcount() <= args.floor:
            warmup_stopped = True
            break
        operation()
        warmup_count += 1
    gc.collect()
    start = refcount()
    if measurement_meaningful and start <= args.floor:
        warmup_stopped = True
    if warmup_stopped:
        print(
            json.dumps(
                {
                    "modo": args.mode,
                    "inicio": start,
                    "llamadas_calentamiento": warmup_count,
                    "detencion": "piso de seguridad durante el calentamiento",
                    "diagnostic": True,
                }
            ),
            flush=True,
        )
        if translator is not None:
            app.removeTranslator(translator)
        if owner_translator is not None:
            app.removeTranslator(owner_translator)
        return 0
    samples = []
    started = time.monotonic()
    stopped = False
    for iteration in range(args.iterations):
        if measurement_meaningful and refcount() <= args.floor:
            print(
                json.dumps(
                    {
                        "modo": args.mode,
                        "inicio": start,
                        "muestras": samples,
                        "detencion": "piso antes de la llamada",
                        "iteracion": iteration,
                        "diagnostic": True,
                    }
                ),
                flush=True,
            )
            stopped = True
            break
        operation()
        if (iteration + 1) % args.sample_every == 0 or iteration + 1 == args.iterations:
            gc.collect()
            current = refcount()
            samples.append(
                {
                    "iteracion": iteration + 1,
                    "recuento_none": current,
                    "cambio": current - start,
                }
            )
            if measurement_meaningful and current <= args.floor:
                print(
                    json.dumps(
                        {
                            "modo": args.mode,
                            "inicio": start,
                            "muestras": samples,
                            "detencion": "piso de seguridad",
                            "diagnostic": True,
                        }
                    ),
                    flush=True,
                )
                stopped = True
                break
    if not stopped:
        print(
            json.dumps(
                {
                    "modo": args.mode,
                    "inicio": start,
                    "muestras": samples,
                    "segundos": round(time.monotonic() - started, 3),
                    "diagnostic": measurement_meaningful,
                }
            ),
            flush=True,
        )

    if translator is not None:
        app.removeTranslator(translator)
    if owner_translator is not None:
        app.removeTranslator(owner_translator)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
