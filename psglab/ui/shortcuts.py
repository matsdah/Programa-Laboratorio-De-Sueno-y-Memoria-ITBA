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

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QWidget

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
#: Los primeros siete corresponden a requisitos del pliego. **Los demás los
#: agregó el refactor de la interfaz**, y cada uno dice por qué: el
#: desplazamiento y la escala de tiempo libre, y el recorrido de paneles, que
#: es de accesibilidad. Lo que sigue sin tecla es lo que no es una tecla: un
#: "deshacer" es un subsistema completo (historial de cambios del scoring y de
#: las anotaciones), y no está pedido.
#:
#: **Los menús muestran estas teclas pero no las registran**: leen este
#: diccionario con `key_for()`. Este módulo sigue siendo el único que dice qué
#: tecla hace qué.
FIXED_SHORTCUTS: Final[dict[str, str]] = {
    "Right": "Ventana siguiente",           # V1_F de "Navegación"
    "Left": "Ventana anterior",             # V1_F de "Navegación"
    "Up": "Aumentar la amplitud",           # V2_P y V5_F de "Visualización"
    "Down": "Reducir la amplitud",          # V2_P y V5_F de "Visualización"
    "A": "Marcar o desmarcar arousal",      # V2_F de "Scoring"
    "Ctrl+O": "Abrir un registro",          # "Importación de archivos"
    "Ctrl+S": "Exportar el scoring",        # V1_F de "Archivo de salida"
    # La escala de tiempo libre, que el pliego no pide y el refactor agrega.
    # **Las flechas solas siguen siendo la época**: son V1_F de "Navegación" y
    # memoria muscular de quien scorea una noche entera. Reasignarlas a
    # desplazar la vista rompería un requisito del pliego para ganar comodidad.
    "Shift+Left": "Desplazar media página hacia atrás",
    "Shift+Right": "Desplazar media página hacia adelante",
    "Ctrl+Left": "Desplazar una página hacia atrás",
    "Ctrl+Right": "Desplazar una página hacia adelante",
    "Ctrl+-": "Alejar: página × 2",
    "Ctrl++": "Acercar: página ÷ 2",
    "Ctrl+0": "Mostrar el registro entero",
    # La reproducción, del hito 24. **Sólo con el foco en la señal**: en el
    # resto de la ventana Espacio ya tiene dueño —tilda una casilla de
    # Canales, aprieta el botón enfocado— y robárselo rompería el uso con
    # teclado de esos paneles.
    "Space": "Reproducir o pausar (con el foco en la señal)",
    # Accesibilidad. F6 es la tecla con que la mayoría de los programas pasan
    # el foco de un panel al siguiente; sin ella, llegar al selector de canales
    # o al scoring sin mouse obligaba a atravesar todos los controles con Tab.
    "F6": "Pasar al panel siguiente",
    "Shift+F6": "Volver al panel anterior",
}

#: Qué método de la ventana principal ejecuta cada atajo fijo. Está separado de
#: `FIXED_SHORTCUTS` porque aquél es lo que **lee el usuario** en la ayuda y
#: éste es el cableado: cambiar un texto de ayuda no puede desconectar una
#: tecla.
#: Marca con la que este módulo firma los `QShortcut` que crea, para poder
#: reconocerlos y desinstalarlos al reinstalar. Ver `_quitar_atajos_anteriores`.
_NOMBRE_DE_ATAJO: Final[str] = "psglab-shortcut"

ACTIONS: Final[dict[str, str]] = {
    "Right": "go_to_next_window",
    "Left": "go_to_previous_window",
    "Up": "increase_amplitude",
    "Down": "decrease_amplitude",
    "A": "toggle_arousal",
    "Ctrl+O": "open_recording_dialog",
    "Ctrl+S": "export_scoring_dialog",
    "Shift+Left": "pan_view_left",
    "Shift+Right": "pan_view_right",
    "Ctrl+Left": "pan_view_page_left",
    "Ctrl+Right": "pan_view_page_right",
    "Ctrl+-": "double_timescale",
    "Ctrl++": "halve_timescale",
    "Ctrl+0": "show_whole_recording",
    "F6": "focus_next_pane",
    "Shift+F6": "focus_previous_pane",
}

#: Los atajos que sólo andan **con el foco en la señal**, y el método que
#: ejecutan. Van aparte de `ACTIONS` porque no se cuelgan de la ventana sino
#: del visualizador, con `WidgetWithChildrenShortcut`: así la tecla no le llega
#: a la ventana cuando el foco está en otro panel.
SIGNAL_ACTIONS: Final[dict[str, str]] = {
    "Space": "toggle_playback",
}

#: Cómo se le escribe cada tecla al usuario. Las flechas se dibujan, y
#: «Shift» es «Mayús», que es lo que dice un teclado en español.
_NOMBRES_DE_TECLA: Final[dict[str, str]] = {
    "Left": "←",
    "Right": "→",
    "Up": "↑",
    "Down": "↓",
    "Shift": "Mayús",
    "Space": "Espacio",
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
        key_for_stage(fase): f"Marcar la ventana como {stage_label(fase)}"
        for fase in stages_of(nomenclature)
    }


def readable_key(key: str) -> str:
    """Una tecla escrita como la lee el usuario: «Mayús+←» y no «Shift+Left».

    La que termina en «++» es la tecla «+» con modificadores: partirla por
    «+» a secas la perdería.
    """
    if key.endswith("++"):
        partes = key[:-2].split("+") + ["+"]
    else:
        partes = key.split("+")
    return "+".join(_NOMBRES_DE_TECLA.get(parte, parte) for parte in partes)


def key_for(method: str) -> str | None:
    """La tecla que ejecuta un método de la ventana, o None si no tiene.

    Es la inversa de `ACTIONS` y de `SIGNAL_ACTIONS`, y la usa el menú para
    mostrar el atajo al lado de cada acción **sin declararlo otra vez**: este
    módulo sigue siendo el único lugar que dice qué tecla hace qué.
    """
    for tecla, metodo in {**ACTIONS, **SIGNAL_ACTIONS}.items():
        if metodo == method:
            return tecla
    return None


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

    **Lo primero que hace es desinstalar los anteriores.** No es una precaución
    teórica: se la llama tres veces —al construir la ventana, al abrir un
    registro y al cambiar de nomenclatura— y sin esto cada llamada dejaba vivos
    los `QShortcut` de la anterior. Dos atajos con la misma tecla colgados de la
    misma ventana hacen que Qt no dispare ninguno de los dos y escriba
    "Ambiguous shortcut overload" por consola, así que la tecla `2` dejaba de
    scorear justo después de cambiar de nomenclatura, que es cuando el usuario
    más la necesita.
    """
    _quitar_atajos_anteriores(window)

    for tecla, metodo in ACTIONS.items():
        _conectar(window, tecla, metodo)

    senal = getattr(window, "signal_view", None)
    if isinstance(senal, QWidget):
        for tecla, metodo in SIGNAL_ACTIONS.items():
            _conectar(window, tecla, metodo, sobre=senal)

    if session is None:
        return
    for tecla, fase in _fases_por_tecla(session.scoring.nomenclature).items():
        _conectar_fase(window, tecla, fase)


def key_for_stage(stage: SleepStage) -> str:
    """La tecla natural de una fase, derivada de su código.

    Los códigos 1 a 4 son las fases numeradas y su tecla es su propio número.
    Los otros tres son letras: W de vigilia, R de REM y M de movimiento.

    **Es pública desde el hito 34**, que la muestra en el botón de la fase. Es
    el mismo trato que `key_for()` le da a los menús: la tecla se lee de este
    módulo en vez de escribirse al lado del control, que es como se
    desincronizan.
    """
    codigo = stage_code(stage)
    if 1 <= codigo <= 4:
        return str(codigo)
    return {0: "W", 5: "R", 6: "M"}[codigo]


def _fases_por_tecla(nomenclature: Nomenclature) -> dict[str, SleepStage]:
    """La inversa de `stage_shortcuts()`: qué fase asigna cada tecla."""
    return {key_for_stage(fase): fase for fase in stages_of(nomenclature)}


def _quitar_atajos_anteriores(window: QMainWindow) -> None:
    """Desinstala los atajos que puso una llamada anterior.

    Se reconocen por su `objectName`, y no se borran todos los `QShortcut` de la
    ventana. `findChildren()` busca en toda la descendencia, así que también
    encuentra los que cuelgan de la señal: este módulo es la fuente única de los atajos del programa, pero
    nada impide que Qt o un widget de terceros cuelgue el suyo, y llevárselo
    puesto sería un efecto secundario invisible.

    `setParent(None)` antes de `deleteLater()` es lo que hace que el atajo deje
    de existir **ahora** y no cuando el ciclo de eventos pase por su cola: sin
    eso, reinstalar y usar la tecla en el mismo gesto seguiría encontrando al
    viejo, que es justo el caso de cambiar de nomenclatura.
    """
    for atajo in window.findChildren(QShortcut):
        if atajo.objectName() != _NOMBRE_DE_ATAJO:
            continue
        atajo.setEnabled(False)
        atajo.setParent(None)
        atajo.deleteLater()


def _nuevo_atajo(dueno: QWidget, tecla: str) -> QShortcut:
    """Crea un atajo marcado como nuestro, para poder desinstalarlo después."""
    atajo = QShortcut(QKeySequence(tecla), dueno)
    atajo.setObjectName(_NOMBRE_DE_ATAJO)
    return atajo


def _conectar(
    window: QMainWindow, tecla: str, metodo: str, sobre: QWidget | None = None
) -> None:
    """Cuelga un atajo y lo conecta a uno de los métodos de la ventana.

    Con `sobre`, el atajo cuelga de ese widget y sólo anda con el foco adentro
    de él; sin `sobre`, cuelga de la ventana y anda siempre.

    Si la ventana no tiene ese método, el atajo **no se instala**. No es un
    descuido: `install_shortcuts()` se llama con la ventana a medio construir en
    los tests y en el arranque, y hacer fallar el programa entero por un atajo
    sería peor que quedarse sin él.
    """
    accion = getattr(window, metodo, None)
    if accion is None:
        return
    atajo = _nuevo_atajo(window if sobre is None else sobre, tecla)
    if sobre is not None:
        atajo.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    atajo.activated.connect(accion)


def _conectar_fase(window: QMainWindow, tecla: str, stage: SleepStage) -> None:
    """Igual que `_conectar`, para las teclas que asignan una fase."""
    accion = getattr(window, "score_current_window", None)
    if accion is None:
        return
    _nuevo_atajo(window, tecla).activated.connect(lambda fase=stage: accion(fase))


def shortcuts_help_text(nomenclature: Nomenclature) -> str:
    """Texto de ayuda con todos los atajos disponibles.

    Se muestra en el menú Ayuda. Se arma desde los diccionarios de este
    módulo, así que nunca queda desactualizado.

    Las fases van al final y aparte, porque son las que cambian con la
    nomenclatura: el usuario que cambia de R&K a AASM tiene que ver la lista
    nueva sin que nadie edite nada.
    """
    lineas = ["Atajos de teclado", ""]
    lineas += [
        f"  {readable_key(tecla):10}  {texto}" for tecla, texto in FIXED_SHORTCUTS.items()
    ]
    lineas += ["", f"Fases ({nomenclature.value})", ""]
    lineas += [
        f"  {tecla:8}  {texto}"
        for tecla, texto in stage_shortcuts(nomenclature).items()
    ]
    return "\n".join(lineas)
