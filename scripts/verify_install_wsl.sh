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

set -uo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INSTALLER="$REPO/scripts/install_wsl.sh"
TRABAJO=$(mktemp -d)
trap 'rm -rf "$TRABAJO"' EXIT

ESCENARIOS=(
    resolve_latest
    resolve_given
    refuses_root
    old_python
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
