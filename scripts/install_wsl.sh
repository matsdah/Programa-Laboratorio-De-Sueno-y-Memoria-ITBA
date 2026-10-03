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
}

[[ -n "${PSGLAB_INSTALLER_LIBRARY:-}" ]] || main "$@"
