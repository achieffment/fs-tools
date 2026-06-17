#!/usr/bin/env bash
# Обёртка для Linux/macOS (терминал): готовит .venv при первом запуске и вызывает
# fs-checker. Аргументы пробрасываются как есть ("$@").
set -euo pipefail

here="$(cd -- "$(dirname -- "$0")" && pwd)"
root="$(cd -- "$here/.." && pwd)"
# shellcheck source=/dev/null
source "$here/_bootstrap.sh"
_fs_tools_bootstrap "$root"
exec "$FS_TOOLS_VBIN/fs-checker" "$@"
