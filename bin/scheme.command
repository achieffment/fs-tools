#!/usr/bin/env bash
# Кликабельная обёртка для macOS (Finder): готовит .venv при первом запуске,
# вызывает fs-schemer и ждёт клавишу перед выходом. Аргументы пробрасываются ("$@").
set -euo pipefail

here="$(cd -- "$(dirname -- "$0")" && pwd)"
root="$(cd -- "$here/.." && pwd)"

pause_exit() {
    echo
    read -n 1 -s -r -p "Нажмите любую клавишу для выхода..." || true
    echo
    exit "$1"
}

# shellcheck source=/dev/null
source "$here/_bootstrap.sh"
if ! _fs_tools_bootstrap "$root"; then
    pause_exit 1
fi

stat=0
"$FS_TOOLS_VBIN/fs-schemer" "$@" || stat=$?
pause_exit "$stat"
