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

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow

from psglab.core.nomenclature import (
    Nomenclature,
    SleepStage,
    stage_code,
    stage_label,
    stages_of,
)
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

#: Qué método de la ventana principal ejecuta cada atajo fijo. Está separado de
#: `FIXED_SHORTCUTS` porque aquél es lo que **lee el usuario** en la ayuda y
#: éste es el cableado: cambiar un texto de ayuda no puede desconectar una
#: tecla.
ACTIONS: Final[dict[str, str]] = {
    "Right": "go_to_next_window",
    "Left": "go_to_previous_window",
    "Up": "increase_amplitude",
    "Down": "decrease_amplitude",
    "A": "toggle_arousal",
    "Ctrl+O": "open_recording_dialog",
    "Ctrl+S": "export_scoring_dialog",
}


def stage_shortcuts(nomenclature: Nomenclature) -> dict[str, str]:
    """Atajos de las fases de sueño según la nomenclatura activa.

    En Rechtschaffen y Kales las teclas naturales son W, 1, 2, 3, 4, R y M;
    en AASM, W, 1, 2, 3 y R. Se generan a partir de la nomenclatura para que
    agregar o cambiar una fase no obligue a tocar este diccionario a mano.

    **La tecla sale del código de la fase**, no de una tabla paralela: 1 a 4 son
    su propio número, y W, R y M son la inicial de su etiqueta. Así una fase
    nueva trae su tecla sola, que es justamente lo que este módulo promete.
    """
    return {
        _tecla_de_fase(fase): f"Marcar la ventana como {stage_label(fase)}"
        for fase in stages_of(nomenclature)
    }


def install_shortcuts(window: QMainWindow, session: Session | None) -> None:
    """Instala todos los atajos sobre la ventana principal.

    `session` admite `None` porque los atajos se instalan al construir la
    ventana, y en ese momento **todavía no hay ningún registro abierto**: la
    ventana arranca vacía y `MainWindow.session` es `Session | None`. Los atajos
    que necesitan una sesión no hacen nada mientras no la haya.

    Los atajos se cuelgan de la ventana y se conectan a **sus** métodos, que es
    lo que mantiene a este módulo sin lógica propia: acá se declara qué tecla
    hace qué, y la acción vive en `main_window.py`. Los nombres que espera están
    en `ACTIONS`.

    Las fases se instalan aparte porque dependen de la nomenclatura, que cambia
    en tiempo de ejecución (V3_F de "Scoring"): se vuelven a instalar cuando el
    usuario la cambia.
    """
    for tecla, metodo in ACTIONS.items():
        _conectar(window, tecla, metodo)

    if session is None:
        return
    for tecla, fase in _fases_por_tecla(session.scoring.nomenclature).items():
        _conectar_fase(window, tecla, fase)


def _tecla_de_fase(stage: SleepStage) -> str:
    """La tecla natural de una fase, derivada de su código.

    Los códigos 1 a 4 son las fases numeradas y su tecla es su propio número.
    Los otros tres son letras: W de vigilia, R de REM y M de movimiento.
    """
    codigo = stage_code(stage)
    if 1 <= codigo <= 4:
        return str(codigo)
    return {0: "W", 5: "R", 6: "M"}[codigo]


def _fases_por_tecla(nomenclature: Nomenclature) -> dict[str, SleepStage]:
    """La inversa de `stage_shortcuts()`: qué fase asigna cada tecla."""
    return {_tecla_de_fase(fase): fase for fase in stages_of(nomenclature)}


def _conectar(window: QMainWindow, tecla: str, metodo: str) -> None:
    """Cuelga un atajo de la ventana y lo conecta a uno de sus métodos.

    Si la ventana no tiene ese método, el atajo **no se instala**. No es un
    descuido: `install_shortcuts()` se llama con la ventana a medio construir en
    los tests y en el arranque, y hacer fallar el programa entero por un atajo
    sería peor que quedarse sin él.
    """
    accion = getattr(window, metodo, None)
    if accion is None:
        return
    QShortcut(QKeySequence(tecla), window).activated.connect(accion)


def _conectar_fase(window: QMainWindow, tecla: str, stage: SleepStage) -> None:
    """Igual que `_conectar`, para las teclas que asignan una fase."""
    accion = getattr(window, "score_current_window", None)
    if accion is None:
        return
    QShortcut(QKeySequence(tecla), window).activated.connect(
        lambda fase=stage: accion(fase)
    )


def shortcuts_help_text(nomenclature: Nomenclature) -> str:
    """Texto de ayuda con todos los atajos disponibles.

    Se muestra en el menú Ayuda. Se arma desde los diccionarios de este
    módulo, así que nunca queda desactualizado.

    Las fases van al final y aparte, porque son las que cambian con la
    nomenclatura: el usuario que cambia de R&K a AASM tiene que ver la lista
    nueva sin que nadie edite nada.
    """
    lineas = ["Atajos de teclado", ""]
    lineas += [f"  {tecla:8}  {texto}" for tecla, texto in FIXED_SHORTCUTS.items()]
    lineas += ["", f"Fases ({nomenclature.value})", ""]
    lineas += [
        f"  {tecla:8}  {texto}"
        for tecla, texto in stage_shortcuts(nomenclature).items()
    ]
    return "\n".join(lineas)
