"""Punto de entrada del programa de scoring de sueño del Laboratorio ITBA.

Este archivo se mantiene deliberadamente mínimo (requisito del pliego,
sección 7): sólo crea la aplicación, abre la ventana principal y cede el
control al bucle de eventos. Toda la lógica vive en los módulos del
paquete `psglab`, separados por funcionalidad.

Uso:
    python main.py

Cubre del pliego: ningún ID de funcionalidad. Cubre el requisito técnico de
"main.py lo más simple posible" (sección 7).
"""

import sys

from psglab.app import create_application, create_main_window


def main() -> int:
    """Arranca la aplicación y devuelve su código de salida al sistema."""
    app = create_application(sys.argv)
    window = create_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
