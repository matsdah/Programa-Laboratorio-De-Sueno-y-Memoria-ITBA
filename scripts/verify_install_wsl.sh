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

# **Las instalaciones de los escenarios no saben que están en WSL.** Si lo
# supieran, cada corrida dejaría un `PSGLab.lnk` de verdad en el escritorio de
# Windows. El acceso del escritorio se prueba con sus funciones sueltas.
unset WSL_DISTRO_NAME

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
    windows_shortcut_quoting
    windows_shortcut_fallback
    start_menu_entry
    start_menu_entry_without_sudo
    switch_releases_build_before_cleanup
    switch_refuses_outside_root
    rejects_path_in_version
    resolve_uses_token
    windows_text_round_trip
    launcher_follows_windows_scale
)

# -- Ayudas -------------------------------------------------------------------

# Carga las funciones del instalador sin correr `main`. Hay que llamarla
# dentro de un subshell: el instalador prende `set -e`, y su `die` sale.
load_installer() {
    # shellcheck source=install_wsl.sh
    PSGLAB_INSTALLER_LIBRARY=1 source "$INSTALLER"
}

# Corre el instalador. La primera vez del CI, con los paquetes del sistema.
run_installer() {
    local extra=(--skip-system-packages)
    if [[ "${VERIFY_SYSTEM_PACKAGES:-}" == 1 && ! -e "$TRABAJO/.sistema" ]]; then
        extra=()
        touch "$TRABAJO/.sistema"
    fi
    bash "$INSTALLER" "${extra[@]}" "$@"
}

# Instala y, si falla, falla el escenario con el final de lo que dijo.
install_ok() {
    run_installer "$@" > "$XDG_DATA_HOME/instalacion.log" 2>&1 \
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
    if run_installer --source "$copia" > "$XDG_DATA_HOME/rota.log" 2>&1; then
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
    if error=$(run_installer v0.0.0-no-existe 2>&1 > /dev/null); then
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
    run_installer --source "$copia" > "$XDG_DATA_HOME/instalacion.log" 2> "$XDG_DATA_HOME/errores.log" \
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

scenario_windows_shortcut_quoting() {
    local guion
    # shellcheck disable=SC1003  # Son barras de rutas de Windows, no escapes.
    guion=$( (load_installer
              windows_shortcut_script 'C:\Users\O'"'"'Brien\OneDrive\Escritorio\PSGLab.lnk' \
                  'C:\Program Files\WSL\wslg.exe' Ubuntu /home/o/.local/share/psglab/launch \
                  'C:\Users\O'"'"'Brien\AppData\Local\PSGLab\psglab.ico') 2>&1 ) \
        || fail "windows_shortcut_script salió con error: $guion"
    [[ "$guion" == *"'C:\Users\O''Brien\OneDrive\Escritorio\PSGLab.lnk'"* ]] \
        || fail "la ruta del .lnk no quedó bien citada: «$guion»"
    [[ "$guion" == *"'-d Ubuntu -- \"/home/o/.local/share/psglab/launch\"'"* ]] \
        || fail "los argumentos de wslg no quedaron bien: «$guion»"
    # Dentro de WSL, que PowerShell lo pueda leer. `Create` sólo lo analiza:
    # no lo corre, así que no crea ningún acceso.
    if command -v powershell.exe > /dev/null; then
        printf '%s' "$guion" | (cd /mnt/c && powershell.exe -NoProfile -NonInteractive \
            -Command '[scriptblock]::Create([Console]::In.ReadToEnd()) | Out-Null') \
            || fail "PowerShell no puede leer el código: «$guion»"
    fi
}

scenario_windows_shortcut_fallback() {
    local error
    error=$( (load_installer
              PATH=/usr/bin:/bin WSL_DISTRO_NAME=Prueba \
                  create_windows_shortcut "$XDG_DATA_HOME/psglab") 2>&1 ) \
        || fail "sin PowerShell la instalación falló: «$error»"
    [[ "$error" == *"menú Inicio"* ]] || fail "no explicó cómo hacerlo a mano: «$error»"
}

# Un `sudo` de mentira que corre el comando sin privilegios, o que falla.
sudo_de_mentira() {
    mkdir -p "$TRABAJO/bin"
    if [[ "$1" == anda ]]; then
        printf '#!/bin/sh\nexec "$@"\n' > "$TRABAJO/bin/sudo"
    else
        printf '#!/bin/sh\nexit 1\n' > "$TRABAJO/bin/sudo"
    fi
    chmod +x "$TRABAJO/bin/sudo"
}

scenario_start_menu_entry() {
    local origen="$XDG_DATA_HOME/psglab.desktop" sistema="$XDG_DATA_HOME/sistema"
    mkdir -p "$sistema"
    printf '[Desktop Entry]\nName=PSGLab\n' > "$origen"
    sudo_de_mentira anda
    ( load_installer; PATH="$TRABAJO/bin:$PATH" publish_start_menu_entry "$origen" "$sistema" ) \
        || fail "publish_start_menu_entry salió con error"
    cmp -s "$origen" "$sistema/psglab.desktop" || fail "no copió el acceso a la carpeta del sistema"
}

scenario_start_menu_entry_without_sudo() {
    local origen="$XDG_DATA_HOME/psglab.desktop" sistema="$XDG_DATA_HOME/sistema" error
    mkdir -p "$sistema"
    printf '[Desktop Entry]\nName=PSGLab\n' > "$origen"
    sudo_de_mentira falla
    error=$( (load_installer; PATH="$TRABAJO/bin:$PATH" publish_start_menu_entry "$origen" "$sistema") 2>&1 ) \
        || fail "sin sudo la instalación falló: «$error»"
    [[ "$error" == *"sudo cp"* ]] || fail "no dijo cómo hacerlo a mano: «$error»"
}

# Un Ctrl+C mientras se borran las versiones viejas corre la trampa de
# salida, que borra la versión en construcción: para entonces ya tiene que
# haber dejado de serlo, porque `actual` apunta a ella.
scenario_switch_releases_build_before_cleanup() {
    local raiz
    raiz=$(raiz)
    mkdir -p "$raiz/vieja.abcdef" "$raiz/nueva.abcdef"
    ( load_installer
      CONSTRUCCION="$raiz/nueva.abcdef"
      rm() {
          [[ -z "$CONSTRUCCION" ]] || { echo "borraba con la construcción todavía pendiente"; exit 1; }
          command rm "$@"
      }
      switch_to "$raiz/nueva.abcdef" ) || fail "la construcción seguía pendiente durante el borrado"
    [[ "$(readlink "$raiz/actual")" == nueva.abcdef ]] || fail "«actual» no apunta a la nueva"
}

scenario_switch_refuses_outside_root() {
    local afuera="$TRABAJO/afuera" error
    mkdir -p "$afuera/nueva.abcdef" "$afuera/ajena"
    if error=$( (load_installer; switch_to "$afuera/nueva.abcdef") 2>&1 ); then
        fail "cambió de versión fuera de la carpeta de PSGLab"
    fi
    [[ -d "$afuera/ajena" ]] || fail "borró una carpeta que no era de PSGLab"
    [[ "$error" == PSGLab:* ]] || fail "el error no empieza con «PSGLab:»: «$error»"
}

scenario_rejects_path_in_version() {
    local error
    if error=$(run_installer ../../v0.1.0 2>&1 > /dev/null); then
        fail "aceptó una versión con «..»"
    fi
    [[ "$error" == PSGLab:*"../../v0.1.0"* ]] || fail "el error no nombra la versión: «$error»"
    if compgen -G "$XDG_DATA_HOME/../v0.1.0.*" > /dev/null; then
        fail "creó algo fuera de la carpeta de PSGLab"
    fi
}

# Con `GITHUB_TOKEN` definido, la consulta lo manda: uno inválido tiene que
# hacerla fallar. Sin token, desde los runners del CI se choca con el límite
# de pedidos por hora.
scenario_resolve_uses_token() {
    if GITHUB_TOKEN=token-que-no-existe bash "$INSTALLER" --resolve-only > /dev/null 2>&1; then
        fail "la consulta no mandó el token"
    fi
}

# Dentro de WSL, un texto con acentos tiene que ir y volver de Windows
# intacto: `cmd.exe` y `powershell.exe` escriben en la página de códigos de la
# consola, y «Pérez» llegaba como «P\x82rez». Fuera de WSL no hay Windows.
scenario_windows_text_round_trip() {
    command -v powershell.exe > /dev/null || return 0
    local texto
    texto=$( (load_installer; windows_eval "'P' + [char]0x00E9 + 'rez ' + [char]0x0141") 2>&1 ) \
        || fail "windows_eval salió con error: «$texto»"
    [[ "$texto" == "Pérez Ł" ]] || fail "volvió «$texto» y no «Pérez Ł»"
}

# WSLg le pasa al programa escala 1 aunque Windows esté en 125 %: el
# lanzador lee la escala de Windows y se la da a Qt. Con un `reg.exe` de
# mentira que contesta 120 DPI, el programa tiene que arrancar con 1.25; sin
# `reg.exe` —fuera de WSL—, sin escala; y una puesta a mano se respeta.
scenario_launcher_follows_windows_scale() {
    local raiz bin="$TRABAJO/bin-escala" salida
    raiz=$(raiz)
    mkdir -p "$bin" "$raiz/falsa/venv/bin" "$raiz/falsa/app"
    # shellcheck disable=SC2016  # `$QT_SCALE_FACTOR` lo expande el Python de mentira.
    printf '#!/bin/sh\nprintf "escala=%%s\\n" "$QT_SCALE_FACTOR"\n' > "$raiz/falsa/venv/bin/python"
    printf '#!/bin/sh\nprintf "\\r\\nHKEY_CURRENT_USER\\\\Control Panel\\\\Desktop\\\\WindowMetrics\\r\\n    AppliedDPI    REG_DWORD    0x78\\r\\n\\r\\n"\n' > "$bin/reg.exe"
    chmod +x "$raiz/falsa/venv/bin/python" "$bin/reg.exe"
    ln -s falsa "$raiz/actual"
    ( load_installer; write_launcher "$raiz" "$TRABAJO" ) || fail "write_launcher salió con error"
    salida=$(PATH="$bin:/usr/bin:/bin" "$raiz/launch") || fail "el lanzador salió con error"
    [[ "$salida" == "escala=1.25" ]] || fail "con 120 DPI arrancó con «$salida»"
    salida=$(PATH="/usr/bin:/bin" "$raiz/launch")
    [[ "$salida" == "escala=" ]] || fail "sin reg.exe puso una escala: «$salida»"
    salida=$(PATH="$bin:/usr/bin:/bin" QT_SCALE_FACTOR=2 "$raiz/launch")
    [[ "$salida" == "escala=2" ]] || fail "no respetó la escala puesta a mano: «$salida»"
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
