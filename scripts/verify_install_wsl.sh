#!/usr/bin/env bash
# Verifica `install_wsl.sh` escenario por escenario.
#
# Lo corre el job «Instalador de WSL» del CI y se puede correr a mano en
# Ubuntu, dentro de WSL o no:
#
#     bash scripts/verify_install_wsl.sh               # todos los escenarios
#     bash scripts/verify_install_wsl.sh install_once  # uno solo
#
# **Nunca toca una instalación de verdad.** Cada escenario trabaja con su
# propio `XDG_DATA_HOME`, dentro de una carpeta temporal que se borra al
# terminar. Las instalaciones salen del árbol de este repositorio con
# `--source`, así que lo que se prueba es el cambio y no la última release.
#
# Con `VERIFY_SYSTEM_PACKAGES=1` la primera instalación instala también los
# paquetes del sistema con `sudo apt-get`, que es lo que hace el CI; sin esa
# variable todas corren con `--skip-system-packages`, porque `sudo` pediría
# una contraseña.

# shellcheck source-path=SCRIPTDIR

set -uo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALLER="$REPO/scripts/install_wsl.sh"
# **En la carpeta personal y no en `/tmp`.** Cada instalación ocupa más de un
# gigabyte, y en WSL `/tmp` es un disco en memoria de unos pocos: con dos
# instalaciones vivas, `pip` se quedaba sin espacio.
TRABAJO=$(mktemp -d "$HOME/.psglab-verify.XXXXXX")
trap 'rm -rf "$TRABAJO"' EXIT

ESCENARIOS=(
    resolve_latest
    resolve_given
    refuses_root
    old_python
    install_once
    install_twice
    failed_install_keeps_current
    leftovers_removed
    unknown_version
    desktop_entry
    old_version_without_icon
    desktop_entry_spaces
    launcher
    window_offscreen
    platform_libraries
)

# -- Ayudas -------------------------------------------------------------------

# Carga las funciones del instalador sin correr `main`. Hay que llamarla
# dentro de un subshell: el instalador prende `set -e`, y su `die` sale.
load_installer() {
    # shellcheck source=install_wsl.sh
    PSGLAB_INSTALLER_LIBRARY=1 source "$INSTALLER"
}

# Corre el instalador. La primera vez del CI, con los paquetes del sistema.
install() {
    local extra=(--skip-system-packages)
    if [[ "${VERIFY_SYSTEM_PACKAGES:-}" == 1 && ! -e "$TRABAJO/.sistema" ]]; then
        extra=()
        touch "$TRABAJO/.sistema"
    fi
    bash "$INSTALLER" "${extra[@]}" "$@"
}

# Instala y, si falla, falla el escenario con el final de lo que dijo.
install_ok() {
    install "$@" > "$XDG_DATA_HOME/instalacion.log" 2>&1 \
        || fail "la instalación salió con error: $(tail -n 3 "$XDG_DATA_HOME/instalacion.log")"
}

# La carpeta de PSGLab del escenario, y sus carpetas de versión.
raiz() {
    printf '%s/psglab' "$XDG_DATA_HOME"
}

versiones() {
    find "$(raiz)" -mindepth 1 -maxdepth 1 -type d | sort
}

# Copia el repositorio sin lo que no es código, para poder romperlo.
copiar_repo() {
    mkdir -p "$1"
    tar -C "$REPO" --exclude=.git --exclude='.venv*' --exclude=data \
        --exclude=.superpowers --exclude=__pycache__ -cf - . | tar -C "$1" -xf -
}

# Falla el escenario con un motivo. Sale y no vuelve: cada escenario corre en
# su propio subshell, y un chequeo que pase después no puede taparlo.
fail() {
    printf '%s\n' "$*"
    exit 1
}

# -- Escenarios ---------------------------------------------------------------

scenario_resolve_latest() {
    local version
    version=$(bash "$INSTALLER" --resolve-only) || fail "--resolve-only salió con error"
    [[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]] || fail "versión inesperada: «$version»"
}

scenario_resolve_given() {
    local version
    version=$(bash "$INSTALLER" --resolve-only v0.1.0) || fail "--resolve-only v0.1.0 salió con error"
    [[ "$version" == v0.1.0 ]] || fail "imprimió «$version» y no «v0.1.0»"
}

scenario_refuses_root() {
    local error
    if error=$( (load_installer; check_not_root 0) 2>&1 ); then
        fail "check_not_root 0 no se negó"
    fi
    [[ "$error" == *"Corré el comando sin sudo"* ]] || fail "el mensaje no dice cómo correrlo: «$error»"
    ( load_installer; check_not_root 1000 ) || fail "check_not_root 1000 se negó"
}

scenario_old_python() {
    local falso="$TRABAJO/python-viejo" error
    printf '#!/bin/sh\nexit 1\n' > "$falso"
    chmod +x "$falso"
    if error=$( (load_installer; check_python "$falso") 2>&1 ); then
        fail "check_python aceptó un Python viejo"
    fi
    [[ "$error" == *3.11* ]] || fail "el mensaje no nombra la versión que hace falta: «$error»"
}

scenario_install_once() {
    install_ok --source "$REPO"
    local destino
    destino=$(readlink "$(raiz)/actual") || fail "no quedó el enlace «actual»"
    [[ "$destino" == source.* ]] || fail "«actual» apunta a «$destino»"
    (cd "$(raiz)/actual/app" && "$(raiz)/actual/venv/bin/python" -c 'import psglab') \
        || fail "el venv instalado no importa psglab"
    [[ $(versiones | wc -l) -eq 1 ]] || fail "quedaron $(versiones | wc -l) carpetas de versión"
}

scenario_install_twice() {
    install_ok --source "$REPO"
    local primera segunda
    primera=$(readlink "$(raiz)/actual")
    install_ok --source "$REPO"
    segunda=$(readlink "$(raiz)/actual")
    [[ "$segunda" != "$primera" ]] || fail "la segunda instalación no reemplazó a la primera"
    [[ $(versiones | wc -l) -eq 1 ]] || fail "quedaron $(versiones | wc -l) carpetas de versión"
}

scenario_failed_install_keeps_current() {
    install_ok --source "$REPO"
    local antes copia="$TRABAJO/copia-rota"
    antes=$(readlink "$(raiz)/actual")
    copiar_repo "$copia"
    printf '\npsglab-paquete-que-no-existe==0.0.0\n' >> "$copia/requirements-analysis.txt"
    if install --source "$copia" > "$XDG_DATA_HOME/rota.log" 2>&1; then
        fail "instaló una copia con una dependencia que no existe"
    fi
    [[ "$(readlink "$(raiz)/actual")" == "$antes" ]] || fail "«actual» cambió después de una instalación fallida"
    [[ $(versiones | wc -l) -eq 1 ]] || fail "la instalación fallida dejó su carpeta"
}

scenario_leftovers_removed() {
    mkdir -p "$(raiz)/v0.0.0.abcdef"
    install_ok --source "$REPO"
    [[ ! -e "$(raiz)/v0.0.0.abcdef" ]] || fail "quedó la carpeta de una instalación interrumpida"
}

scenario_unknown_version() {
    install_ok --source "$REPO"
    local antes error
    antes=$(readlink "$(raiz)/actual")
    if error=$(install v0.0.0-no-existe 2>&1 > /dev/null); then
        fail "instaló una versión que no existe"
    fi
    [[ "$(head -n 1 <<< "$error")" == PSGLab:* ]] || fail "el error no empieza con «PSGLab:»: «$error»"
    [[ "$error" == *v0.0.0-no-existe* ]] || fail "el error no nombra la versión: «$error»"
    [[ "$(readlink "$(raiz)/actual")" == "$antes" ]] || fail "«actual» cambió"
}

acceso_directo() {
    printf '%s/applications/psglab.desktop' "$XDG_DATA_HOME"
}

scenario_desktop_entry() {
    install_ok --source "$REPO"
    desktop-file-validate "$(acceso_directo)" || fail "el acceso directo no valida"
    grep -q '^Exec=.*/psglab/launch' "$(acceso_directo)" || fail "«Exec» no llama al lanzador"
    local icono
    icono=$(sed -n 's/^Icon=//p' "$(acceso_directo)")
    [[ -n "$icono" && -f "$icono" ]] || fail "«Icon» no apunta a un PNG que exista: «$icono»"
}

scenario_old_version_without_icon() {
    local copia="$TRABAJO/copia-rota" error
    copiar_repo "$copia"
    sed -i 's/^def app_icon_image(/def _sin_icono_de_aplicacion(/' "$copia/psglab/ui/icons.py"
    install --source "$copia" > "$XDG_DATA_HOME/instalacion.log" 2> "$XDG_DATA_HOME/errores.log" \
        || fail "una versión sin icono no se instaló: $(tail -n 3 "$XDG_DATA_HOME/errores.log")"
    error=$(cat "$XDG_DATA_HOME/errores.log")
    [[ "$error" == *"sin icono"* ]] || fail "no avisó que queda sin icono: «$error»"
    desktop-file-validate "$(acceso_directo)" || fail "el acceso directo no valida"
    if grep -q '^Icon=' "$(acceso_directo)"; then
        fail "el acceso directo nombra un icono que no hay"
    fi
}

scenario_desktop_entry_spaces() {
    ( load_installer; write_desktop_entry "$XDG_DATA_HOME/psglab" "/mnt/c/Users/Juan Pérez" ) \
        || fail "write_desktop_entry salió con error"
    desktop-file-validate "$(acceso_directo)" || fail "el acceso directo no valida"
    grep -qx 'Path=/mnt/c/Users/Juan Pérez' "$(acceso_directo)" || fail "la línea «Path» no quedó intacta"
}

scenario_launcher() {
    local raiz carpeta="$TRABAJO/Juan Pérez" salida
    raiz=$(raiz)
    mkdir -p "$carpeta" "$raiz/falsa/venv/bin" "$raiz/falsa/app"
    # shellcheck disable=SC2016  # `$PWD` y `$*` los expande el Python de mentira, no este script.
    printf '#!/bin/sh\nprintf "%%s\\n" "$PWD" "$*"\n' > "$raiz/falsa/venv/bin/python"
    chmod +x "$raiz/falsa/venv/bin/python"
    ln -s falsa "$raiz/actual"
    ( load_installer; write_launcher "$raiz" "$carpeta" ) || fail "write_launcher salió con error"
    [[ -x "$raiz/launch" ]] || fail "el lanzador no es ejecutable"
    salida=$("$raiz/launch" uno dos) || fail "el lanzador salió con error"
    [[ "$(head -n 1 <<< "$salida")" == "$carpeta" ]] || fail "no entró en «$carpeta»: «$salida»"
    [[ "$(tail -n 1 <<< "$salida")" == *"/app/main.py uno dos" ]] || fail "no pasó los argumentos: «$salida»"
}

scenario_window_offscreen() {
    install_ok --source "$REPO"
    local salida
    # La configuración de quien corre esto no tiene que cambiar el resultado.
    salida=$(cd "$(raiz)/actual/app" && XDG_CONFIG_HOME="$XDG_DATA_HOME/config" \
        QT_QPA_PLATFORM=offscreen "$(raiz)/actual/venv/bin/python" -c '
import os, sys
from psglab.app import create_application, create_main_window
aplicacion = create_application(sys.argv)
ventana = create_main_window()
ventana.show()
aplicacion.processEvents()
assert not aplicacion.windowIcon().isNull(), "la aplicación no tiene icono"
ventana.close()
aplicacion.processEvents()
print("ventana: ok", flush=True)
os._exit(0)
' 2>&1) || fail "la ventana no abrió: $(tail -n 3 <<< "$salida")"
    [[ "$salida" == *"ventana: ok"* ]] || fail "no llegó a cerrar la ventana: «$salida»"
}

scenario_platform_libraries() {
    install_ok --source "$REPO"
    local carpetas faltan so
    carpetas=("$(raiz)"/actual/venv/lib/python3*/site-packages/PySide6/Qt/plugins/platforms)
    [[ -f "${carpetas[0]}/libqxcb.so" ]] || fail "no está el plugin de X de Qt"
    faltan=$(for so in "${carpetas[0]}"/libqxcb.so "${carpetas[0]}"/libqwayland*.so \
                 "${carpetas[0]}"/libqoffscreen.so; do
                 [[ -e "$so" ]] && ldd "$so" | grep 'not found'
             done | sort -u)
    [[ -z "$faltan" ]] || fail "le faltan librerías del sistema a Qt: $faltan"
}

# -- Corrida ------------------------------------------------------------------

FALLAS=0

run_scenario() {
    local nombre=$1 motivo
    export XDG_DATA_HOME="$TRABAJO/$nombre"
    mkdir -p "$XDG_DATA_HOME"
    if motivo=$("scenario_$nombre" 2>&1); then
        printf 'ok %s\n' "$nombre"
    else
        printf 'FALLÓ %s: %s\n' "$nombre" "$(tail -n 5 <<< "$motivo")"
        FALLAS=$((FALLAS + 1))
    fi
    rm -rf "$XDG_DATA_HOME" "$TRABAJO/copia-rota"
}

if (($#)); then
    for nombre in "$@"; do
        run_scenario "$nombre"
    done
else
    for nombre in "${ESCENARIOS[@]}"; do
        run_scenario "$nombre"
    done
fi

((FALLAS == 0))
