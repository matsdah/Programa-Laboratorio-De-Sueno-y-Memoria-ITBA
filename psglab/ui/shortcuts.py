"""Atajos de teclado: fuente única de verdad.

Todos los atajos del programa se declaran acá y en ningún otro lado. Dos
motivos: se puede mostrar la lista completa en la ayuda sin que se
desactualice, y se detectan las colisiones al leer un solo archivo.

Los atajos son la principal vía de trabajo de quien scorea una noche entera:
son cientos de ventanas, y pasar por el mouse en cada una es inviable.

Cubre del pliego: V2_P y V5_F de "Visualización" (flechas Arriba/Abajo),
V1_F de "Navegación" (flechas Izquierda/Derecha) y V1_F/V2_F de "Scoring".
"""

from typing import Final

from PySide6.QtWidgets import QMainWindow

from psglab.core.session import Session

#: Atajos fijos del programa: tecla -> descripción para la ayuda.
#: Los atajos de las fases de sueño no están acá porque dependen de la
#: nomenclatura activa; los arma `stage_shortcuts()`.
#:
#: Cada atajo corresponde a un requisito del pliego. No se agregan atajos
#: para funciones que el pliego no pide: un "deshacer", por ejemplo, no es
#: una tecla sino un subsistema completo (historial de cambios del scoring y
#: de las anotaciones), y no está pedido.
FIXED_SHORTCUTS: Final[dict[str, str]] = {
    "Right": "Ventana siguiente",           # V1_F de "Navegación"
    "Left": "Ventana anterior",             # V1_F de "Navegación"
    "Up": "Aumentar la amplitud",           # V2_P y V5_F de "Visualización"
    "Down": "Reducir la amplitud",          # V2_P y V5_F de "Visualización"
    "A": "Marcar o desmarcar arousal",      # V2_F de "Scoring"
    "Ctrl+O": "Abrir un registro",          # "Importación de archivos"
    "Ctrl+S": "Exportar el scoring",        # V1_F de "Archivo de salida"
}


def stage_shortcuts(nomenclature) -> dict[str, str]:
    """Atajos de las fases de sueño según la nomenclatura activa.

    En Rechtschaffen y Kales las teclas naturales son W, 1, 2, 3, 4, R y M;
    en AASM, W, 1, 2, 3 y R. Se generan a partir de la nomenclatura para que
    agregar o cambiar una fase no obligue a tocar este diccionario a mano.
    """
    raise NotImplementedError("Pendiente: generar los atajos desde la nomenclatura.")


def install_shortcuts(window: QMainWindow, session: Session) -> None:
    """Instala todos los atajos sobre la ventana principal."""
    raise NotImplementedError("Pendiente: crear los QShortcut y conectarlos.")


def shortcuts_help_text(nomenclature) -> str:
    """Texto de ayuda con todos los atajos disponibles.

    Se muestra en el menú Ayuda. Se arma desde los diccionarios de este
    módulo, así que nunca queda desactualizado.
    """
    raise NotImplementedError("Pendiente: componer el texto de ayuda.")
