#!/usr/bin/env bash
# Instala PSGLab dentro de Ubuntu, en WSL o en un Linux cualquiera.
#
# **Por qué existe.** En Windows 11, el Control inteligente de aplicaciones
# bloquea las DLL sin firma que instala `pip` —pandas, numba, scipy—, y no
# admite excepciones. Dentro de WSL corre la versión Linux del programa, que
# ese control no revisa. La decisión y lo que se descartó están en
# `docs/ARQUITECTURA.md`, «En Windows se instala por WSL y no con un ejecutable
# firmado».
#
# **Cómo se usa**, desde la terminal de Ubuntu y sin `sudo`:
#
#     curl -fsSL https://raw.githubusercontent.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/Master/scripts/install_wsl.sh | bash
#     ... | bash -s -- v0.1.0        # una versión puntual
#
# Opciones: `--source DIR` instala desde un árbol local en vez de bajar una
# release; `--skip-system-packages` no corre `apt`; `--resolve-only` dice qué
# versión instalaría y termina.
#
# **Qué hace.** Instala cada versión en su propia carpeta, con su venv, y
# recién cuando la prueba de humo pasa apunta `actual` a la nueva: una
# instalación que falla a mitad de camino no pisa la que andaba. Correrlo de
# nuevo actualiza.
#
# **Qué no hace.** No fija versiones de las dependencias: cada instalación
# resuelve las del día, como `pip`. No desinstala: cómo hacerlo está en
# `scripts/README.md`.
#
# **Todo vive en funciones y la última línea llama a `main`.** Con
# `curl | bash`, bash lee el script de la entrada estándar mientras lo
# ejecuta, y un comando que leyera esa entrada se comería el resto. Así bash
# tiene que leerlo entero antes de empezar. Con `PSGLAB_INSTALLER_LIBRARY`
# definida, `main` no corre: lo usa `verify_install_wsl.sh` para probar las
# funciones sueltas.

set -euo pipefail

REPOSITORIO="matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA"

SOURCE=""
SKIP_SYSTEM_PACKAGES=0
RESOLVE_ONLY=0
VERSION=""

# -- Mensajes -----------------------------------------------------------------

die() {
    printf 'PSGLab: %s\n' "$*" >&2
    exit 1
}

warn() {
    printf 'PSGLab: %s\n' "$*" >&2
}

step() {
    printf '\n==> %s\n' "$*"
}

# -- Comprobaciones -----------------------------------------------------------

# Con `sudo`, todo quedaría en la carpeta de root, lejos del menú Inicio de
# quien lo instaló.
check_not_root() {
    if [[ "$1" == 0 ]]; then
        die "No hace falta ser administrador. Corré el comando sin sudo: el script pide la contraseña sólo para instalar con «apt» lo que le falta a Ubuntu."
    fi
}

check_python() {
    if ! "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
        die "Hace falta Python 3.11 o más nuevo, y «$1» es más viejo o no está. Ubuntu 24.04 y las siguientes ya lo traen."
    fi
}

# -- Versión ------------------------------------------------------------------

# La versión pedida, o la más nueva publicada **contando las pre-releases**:
# el pedido de «la última release» de la API de GitHub las saltea.
resolve_version() {
    if [[ -n "${1:-}" ]]; then
        printf '%s\n' "$1"
        return
    fi
    # Con un token, la API no aplica el límite de pedidos por dirección, que
    # los runners del CI comparten. Quien instala no lo necesita.
    local respuesta autorizacion=()
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        autorizacion=(--header "Authorization: Bearer $GITHUB_TOKEN")
    fi
    respuesta=$(curl -fsSL "${autorizacion[@]}" "https://api.github.com/repos/$REPOSITORIO/releases?per_page=1") \
        || die "No se pudo consultar qué versiones hay publicadas. Revisá la conexión a internet y volvé a correr el comando."
    printf '%s' "$respuesta" | python3 -c '
import json, sys
releases = json.load(sys.stdin)
if not releases:
    sys.exit(1)
print(releases[0]["tag_name"])
' || die "No hay ninguna versión publicada en GitHub."
}

# -- Instalación --------------------------------------------------------------

#: Lo que el programa necesita de Ubuntu. Las primeras son para instalarlo;
#: las del medio, las mismas que instala el job de Linux del CI; las últimas,
#: las que Qt pide para mostrar la ventana con X o con Wayland, que es lo que
#: usa WSLg.
PAQUETES_DEL_SISTEMA=(
    python3-venv curl
    libegl1 libgl1 libxkbcommon0 libdbus-1-3 libglib2.0-0 libfontconfig1 libfreetype6
    libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 libxcb-util1
    libwayland-client0 libwayland-cursor0 libwayland-egl1
)

psglab_root() {
    printf '%s/psglab' "${XDG_DATA_HOME:-$HOME/.local/share}"
}

# Todo lo que lee la entrada estándar lee `/dev/null`: con `curl | bash`, la
# entrada estándar es el resto de este script.
system_packages() {
    if ((SKIP_SYSTEM_PACKAGES)); then
        return 0
    fi
    step "Instalando lo que le falta a Ubuntu. Te va a pedir tu contraseña de Ubuntu."
    if ! sudo apt-get update < /dev/null \
        || ! sudo apt-get install -y --no-install-recommends "${PAQUETES_DEL_SISTEMA[@]}" < /dev/null; then
        die "No se pudieron instalar los paquetes de Ubuntu. Revisá el mensaje de «apt» de arriba y volvé a correr el comando."
    fi
}

# Deja el código en `<destino>`: el de `--source`, o el de la release `<tag>`.
# De un árbol local no se copian el repositorio de git, los entornos ni
# `data/`, donde puede haber registros de participantes.
fetch_source() {
    local tag=$1 destino=$2
    mkdir -p "$destino"
    if [[ -n "$SOURCE" ]]; then
        tar -C "$SOURCE" --exclude=.git --exclude='.venv*' --exclude=data \
            --exclude=.superpowers --exclude=__pycache__ --exclude=.pytest_cache \
            -cf - . | tar -C "$destino" -xf - \
            || die "No se pudo copiar el código de «$SOURCE»."
        return
    fi
    local archivo
    archivo="$(dirname "$destino")/codigo.tar.gz"
    curl --fail --silent --location --output "$archivo" \
        "https://github.com/$REPOSITORIO/archive/refs/tags/$tag.tar.gz" \
        || die "No se pudo bajar la versión «$tag». Revisá que exista en https://github.com/$REPOSITORIO/releases y la conexión a internet."
    tar -xzf "$archivo" -C "$destino" --strip-components=1 \
        || die "El código de la versión «$tag» llegó dañado. Volvé a correr el comando."
    rm -f "$archivo"
}

create_venv() {
    local dir=$1
    python3 -m venv "$dir/venv" \
        || die "No se pudo crear el entorno de Python. En Ubuntu se arregla con «sudo apt install python3-venv»."
    (cd "$dir/app" && "$dir/venv/bin/python" -m pip install --disable-pip-version-check \
        -r requirements.txt -r requirements-analysis.txt < /dev/null) \
        || die "No se pudieron instalar las dependencias. Revisá el mensaje de «pip» de arriba y la conexión a internet."
}

# Lo mínimo para saber que el programa va a abrir: el paquete, los lectores y
# las herramientas —que se descubren al arrancar, así que un archivo que no
# llegó no avisaría hasta usarlo— y lo que importa la Parte 2.
smoke_test() {
    local dir=$1
    (cd "$dir/app" && "$dir/venv/bin/python" -c '
from psglab.readers.base import available_readers, load_all_readers
from psglab.tools.registry import available_tools, load_all_tools

load_all_readers()
load_all_tools()
assert available_readers(), "no hay ningún lector"
assert available_tools(), "no hay ninguna herramienta"

import antropy, mne_connectivity, yasa
import psglab.ui.main_window
' < /dev/null) || die "La instalación nueva no pasó la prueba. La que ya estaba, si había una, sigue andando."
}

# Apunta `actual` a la versión nueva y borra las demás. El enlace se cambia de
# una vez: se arma al lado y se renombra encima del viejo.
#
# **Sólo dentro de la carpeta de PSGLab**: lo que sigue borra con `rm -rf`
# toda carpeta vecina de la nueva, así que si la nueva no está ahí, se niega.
# **La construcción deja de serlo apenas cambia el enlace**: un Ctrl+C
# mientras se borran las viejas corre la trampa de salida, que si no borraría
# la versión a la que ya apunta `actual`.
switch_to() {
    local nueva=$1 raiz
    raiz=$(dirname "$nueva")
    if [[ "$(realpath -m -- "$raiz")" != "$(realpath -m -- "$(psglab_root)")" ]]; then
        die "No se cambia de versión fuera de $(psglab_root): «$nueva»."
    fi
    ln -sfn "$(basename "$nueva")" "$raiz/.actual-nuevo"
    mv -T "$raiz/.actual-nuevo" "$raiz/actual"
    CONSTRUCCION=""
    local dir
    for dir in "$raiz"/*/; do
        dir=${dir%/}
        if [[ "$dir" != "$nueva" && ! -L "$dir" ]]; then
            rm -rf "$dir"
        fi
    done
}

# -- Accesos directos ---------------------------------------------------------

# WSL define `WSL_DISTRO_NAME` en cada sesión. Es lo único que se mira: así
# `verify_install_wsl.sh` la puede borrar para que sus instalaciones no dejen
# accesos de verdad en el escritorio de Windows.
in_wsl() {
    [[ -n "${WSL_DISTRO_NAME:-}" ]]
}

# Corre código de PowerShell en Windows y devuelve lo que imprime, en UTF-8.
# **Ni la entrada ni la salida pasan por la página de códigos de la consola**:
# `powershell.exe` y `cmd.exe` escriben al pipe en la OEM —850 en un Windows en
# español— y «Pérez» llegaba como «P\x82rez», así que una carpeta de usuario
# con acentos no se encontraba. El código va en UTF-16 con `-EncodedCommand`,
# y lo primero que hace es pasar la salida a UTF-8.
windows_eval() {
    local codigo codificado
    codigo="[Console]::OutputEncoding = [Text.Encoding]::UTF8
$1"
    codificado=$(printf '%s' "$codigo" | iconv -f UTF-8 -t UTF-16LE | base64 -w 0) || return 1
    (cd /mnt/c && powershell.exe -NoProfile -NonInteractive -EncodedCommand "$codificado") \
        < /dev/null 2> /dev/null | tr -d '\r'
}

# Desde dónde se abre el programa: la carpeta de usuario de Windows, así el
# diálogo de apertura arranca en las carpetas de siempre y no en un `/home`
# vacío. Fuera de WSL, o si Windows no contesta, la carpeta personal.
launch_dir() {
    if in_wsl && command -v powershell.exe > /dev/null && command -v wslpath > /dev/null; then
        local windows linux
        windows=$(windows_eval "[Environment]::GetFolderPath('UserProfile')") || windows=""
        if [[ -n "$windows" ]] \
            && linux=$(wslpath -u "$windows" 2> /dev/null) && [[ -d "$linux" ]]; then
            printf '%s\n' "$linux"
            return
        fi
    fi
    printf '%s\n' "$HOME"
}

# **El lanzador entra en la carpeta, y no la línea `Path=` del acceso
# directo:** WSLg arma su `.lnk` con `wslg.exe --cd "~"` y esa línea no
# llega.
#
# **La escala de la pantalla también la pone el lanzador.** WSLg le pasa al
# programa escala 1 aunque Windows esté en 125 %, porque por omisión sólo
# maneja escalas enteras, y el texto salía un quinto más chico que en el
# resto de Windows. Se lee en cada arranque —`reg.exe` tarda 0,1 s—, así que
# acompaña un cambio de escala o de monitor. Fuera de WSL no hay `reg.exe` y
# no se toca nada; una `QT_SCALE_FACTOR` puesta a mano se respeta.
write_launcher() {
    local raiz=$1 carpeta=$2
    {
        printf '#!/usr/bin/env bash\n'
        printf '# Abre PSGLab. Lo escribe scripts/install_wsl.sh.\n'
        printf 'cd -- %q 2> /dev/null || cd ~\n' "$carpeta"
        cat <<'ESCALA'
if [[ -z "${QT_SCALE_FACTOR:-}" ]] && command -v reg.exe > /dev/null; then
    dpi=$(reg.exe query 'HKCU\Control Panel\Desktop\WindowMetrics' /v AppliedDPI 2> /dev/null \
        | tr -d '\r' | awk '$1 == "AppliedDPI" { print $3 }')
    if [[ "$dpi" =~ ^0x[0-9a-fA-F]+$ ]] && (( dpi > 96 )); then
        QT_SCALE_FACTOR=$(awk -v dpi=$((dpi)) 'BEGIN { printf "%.2f", dpi / 96 }')
        export QT_SCALE_FACTOR
    fi
fi
ESCALA
        printf 'exec %q %q "$@"\n' "$raiz/actual/venv/bin/python" "$raiz/actual/app/main.py"
    } > "$raiz/launch"
    chmod +x "$raiz/launch"
}

# Guarda el icono como `<raíz>/psglab.png` y, si se pide, como ICO para
# Windows. Lo dibuja el programa instalado, así que una versión publicada
# antes de que existiera el icono no lo trae: avisa y sigue sin él.
export_icon() {
    local raiz=$1 ico=${2:-}
    rm -f "$raiz/psglab.png"
    if (cd "$raiz/actual/app" && QT_QPA_PLATFORM=offscreen "$raiz/actual/venv/bin/python" - \
        "$raiz/psglab.png" "$ico" <<'PYTHON'
import sys

from PySide6.QtGui import QGuiApplication

aplicacion = QGuiApplication(sys.argv[:1])
try:
    from psglab.ui.icons import app_icon_image
except ImportError:
    sys.exit(3)
imagen = app_icon_image(256)
if not imagen.save(sys.argv[1], "PNG"):
    sys.exit(1)
if sys.argv[2] and not imagen.save(sys.argv[2], "ICO"):
    sys.exit(1)
PYTHON
    ) > /dev/null 2>&1; then
        return 0
    fi
    rm -f "$raiz/psglab.png"
    warn "Esta versión no pudo dibujar el icono del programa, así que los accesos directos quedan sin icono. El programa funciona igual."
    return 1
}

write_desktop_entry() {
    local raiz=$1 carpeta=$2 dir
    dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$dir"
    {
        printf '[Desktop Entry]\n'
        printf 'Type=Application\n'
        printf 'Name=PSGLab\n'
        printf 'Comment=Scoring de sueño y análisis de polisomnografía\n'
        printf 'Exec="%s"\n' "$raiz/launch"
        if [[ -f "$raiz/psglab.png" ]]; then
            printf 'Icon=%s\n' "$raiz/psglab.png"
        fi
        printf 'Path=%s\n' "$carpeta"
        printf 'Terminal=false\n'
        printf 'Categories=Science;MedicalSoftware;\n'
    } > "$dir/psglab.desktop"
}

# **WSLg publica en el menú Inicio sólo lo de la carpeta del sistema**,
# `/usr/share/applications`: el acceso de `~/.local/share/applications` no
# apareció, y el mismo archivo copiado ahí sí. Se copia con el `sudo` que ya
# se usó para `apt`; si no anda, avisa el comando y sigue.
publish_start_menu_entry() {
    local origen=$1 sistema=$2
    if sudo install -m 644 "$origen" "$sistema/psglab.desktop" < /dev/null; then
        return 0
    fi
    warn "No se pudo publicar PSGLab en el menú Inicio. Se hace a mano, desde Ubuntu: sudo cp $origen $sistema/"
    return 0
}

# Un texto entre comillas simples de PowerShell, que se escapan duplicándolas.
ps_quote() {
    printf "'%s'" "${1//\'/\'\'}"
}

# El código de PowerShell que crea el `.lnk` del escritorio: abre el
# lanzador con `wslg.exe`, que es lo mismo que hacen los accesos que WSLg
# publica en el menú Inicio.
# shellcheck disable=SC2016  # `$acceso` es de PowerShell: bash no lo tiene que expandir.
windows_shortcut_script() {
    local lnk=$1 wslg=$2 distro=$3 lanzador=$4 ico=${5:-}
    printf '$acceso = (New-Object -ComObject WScript.Shell).CreateShortcut(%s)\n' "$(ps_quote "$lnk")"
    printf '$acceso.TargetPath = %s\n' "$(ps_quote "$wslg")"
    printf '$acceso.Arguments = %s\n' "$(ps_quote "-d $distro -- \"$lanzador\"")"
    printf '$acceso.Description = %s\n' "$(ps_quote 'PSGLab')"
    if [[ -n "$ico" ]]; then
        printf '$acceso.IconLocation = %s\n' "$(ps_quote "$ico")"
    fi
    printf '$acceso.Save()\n'
}

# Sólo dentro de WSL: «PSGLab» en el escritorio de Windows. La ruta del
# escritorio se le pide a Windows, porque puede estar en OneDrive. **Si algo
# falla, la instalación no falla**: avisa cómo hacerlo a mano. Pasa, por
# ejemplo, en un equipo administrado donde PowerShell está restringido.
create_windows_shortcut() {
    local raiz=$1
    in_wsl || return 0
    local a_mano="Para tenerlo en el escritorio, buscá «PSGLab (Ubuntu)» en el menú Inicio y arrastralo al escritorio."
    if ! command -v powershell.exe > /dev/null || ! command -v wslpath > /dev/null; then
        warn "No se pudo crear el acceso del escritorio, porque no se encontró PowerShell. $a_mano"
        return 0
    fi

    # `wslg.exe` no suele estar en el PATH de Windows: vive en la carpeta de
    # WSL, que es de donde lo lanzan los accesos que WSLg publica.
    local datos escritorio datos_locales wslg
    datos=$(windows_eval "
        [Environment]::GetFolderPath('Desktop')
        \$env:LOCALAPPDATA
        \$encontrado = Get-Command wslg.exe -ErrorAction SilentlyContinue
        if (\$encontrado) { \$encontrado.Source }
        else { Join-Path \$env:ProgramFiles 'WSL\wslg.exe' | Where-Object { Test-Path \$_ } }") \
        || datos=""
    escritorio=$(sed -n 1p <<< "$datos")
    datos_locales=$(sed -n 2p <<< "$datos")
    wslg=$(sed -n 3p <<< "$datos")
    if [[ -z "$escritorio" || -z "$datos_locales" || -z "$wslg" ]]; then
        warn "No se pudo crear el acceso del escritorio, porque Windows no dijo dónde está el escritorio. $a_mano"
        return 0
    fi

    local ico=""
    if [[ -f "$raiz/psglab.png" ]]; then
        local carpeta_ico
        carpeta_ico=$(wslpath -u "$datos_locales\\PSGLab" 2> /dev/null) || carpeta_ico=""
        if [[ -n "$carpeta_ico" ]] && mkdir -p "$carpeta_ico" 2> /dev/null \
            && export_icon "$raiz" "$carpeta_ico/psglab.ico"; then
            ico="$datos_locales\\PSGLab\\psglab.ico"
        fi
    fi

    if ! windows_eval "$(windows_shortcut_script "$escritorio\\PSGLab.lnk" "$wslg" \
        "$WSL_DISTRO_NAME" "$raiz/launch" "$ico")" > /dev/null; then
        warn "No se pudo crear el acceso del escritorio, porque PowerShell no lo permitió. $a_mano"
        return 0
    fi
    printf 'El acceso «PSGLab» quedó en el escritorio.\n'
}

#: La versión que se está armando. Si el script termina antes de cambiar
#: `actual`, por un error o un Ctrl+C, se borra.
CONSTRUCCION=""

discard_build() {
    if [[ -n "$CONSTRUCCION" ]]; then
        rm -rf "$CONSTRUCCION"
    fi
}

# -- Línea de comandos --------------------------------------------------------

parse_args() {
    while (($#)); do
        case "$1" in
            --source)
                (($# >= 2)) || die "A «--source» le falta la carpeta."
                SOURCE=$2
                shift 2
                ;;
            --skip-system-packages)
                SKIP_SYSTEM_PACKAGES=1
                shift
                ;;
            --resolve-only)
                RESOLVE_ONLY=1
                shift
                ;;
            -*)
                die "No conozco la opción «$1»."
                ;;
            *)
                [[ -z "$VERSION" ]] || die "Se pidieron dos versiones: «$VERSION» y «$1»."
                # La versión termina en una ruta, así que no puede traer
                # barras ni empezar con un punto.
                [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] \
                    || die "«$1» no es una versión. Se escribe como en GitHub, por ejemplo «v0.1.0»."
                VERSION=$1
                shift
                ;;
        esac
    done
}

main() {
    parse_args "$@"
    check_not_root "$EUID"
    check_python python3
    if ((RESOLVE_ONLY)); then
        resolve_version "$VERSION"
        return
    fi

    system_packages

    local raiz etiqueta
    raiz=$(psglab_root)
    mkdir -p "$raiz"
    if [[ -n "$SOURCE" ]]; then
        [[ -d "$SOURCE" ]] || die "No existe la carpeta «$SOURCE»."
        etiqueta=source
    else
        etiqueta=$(resolve_version "$VERSION")
    fi

    trap discard_build EXIT
    CONSTRUCCION=$(mktemp -d "$raiz/$etiqueta.XXXXXX")

    step "Bajando PSGLab $etiqueta."
    fetch_source "$etiqueta" "$CONSTRUCCION/app"
    step "Instalando las dependencias. Tarda unos minutos."
    create_venv "$CONSTRUCCION"
    step "Probando la instalación."
    smoke_test "$CONSTRUCCION"
    switch_to "$CONSTRUCCION"
    CONSTRUCCION=""

    step "Creando el acceso directo."
    local carpeta
    carpeta=$(launch_dir)
    write_launcher "$raiz" "$carpeta"
    export_icon "$raiz" "" || true
    write_desktop_entry "$raiz" "$carpeta"
    if in_wsl; then
        publish_start_menu_entry "${XDG_DATA_HOME:-$HOME/.local/share}/applications/psglab.desktop" \
            /usr/share/applications
    fi
    create_windows_shortcut "$raiz"

    step "Listo: PSGLab $etiqueta quedó instalado en $raiz/actual."
}

[[ -n "${PSGLAB_INSTALLER_LIBRARY:-}" ]] || main "$@"
