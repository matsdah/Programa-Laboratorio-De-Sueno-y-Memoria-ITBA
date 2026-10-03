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
    local respuesta
    respuesta=$(curl -fsSL "https://api.github.com/repos/$REPOSITORIO/releases?per_page=1") \
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
    libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1
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
    sudo apt-get update < /dev/null \
        && sudo apt-get install -y --no-install-recommends "${PAQUETES_DEL_SISTEMA[@]}" < /dev/null \
        || die "No se pudieron instalar los paquetes de Ubuntu. Revisá el mensaje de «apt» de arriba y volvé a correr el comando."
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
switch_to() {
    local nueva=$1 raiz
    raiz=$(dirname "$nueva")
    ln -sfn "$(basename "$nueva")" "$raiz/.actual-nuevo"
    mv -T "$raiz/.actual-nuevo" "$raiz/actual"
    local dir
    for dir in "$raiz"/*/; do
        dir=${dir%/}
        if [[ "$dir" != "$nueva" && ! -L "$dir" ]]; then
            rm -rf "$dir"
        fi
    done
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

    step "Listo: PSGLab $etiqueta quedó instalado en $raiz/actual."
}

[[ -n "${PSGLAB_INSTALLER_LIBRARY:-}" ]] || main "$@"
