#!/usr/bin/env bash
# Кликабельная обёртка для macOS (Finder): откат прогона нормализатора по examples/
# к состоянию из git (восстанавливает файлы и удаляет пустые каталоги-сироты).
set -euo pipefail

here="$(cd -- "$(dirname -- "$0")" && pwd)"   # .../examples
repo="$(cd -- "$here/.." && pwd)"             # корень репозитория
cd "$repo"

pause_exit() {
    echo
    read -n 1 -s -r -p "Нажмите любую клавишу для выхода..." || true
    echo
    exit "$1"
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Это не git-репозиторий — откат через git недоступен." >&2
    pause_exit 1
fi

if ! git restore --staged --worktree -- examples 2>/dev/null; then
    git reset -q -- examples
    git checkout -- examples
fi

# Сами reset-скрипты исключаем, чтобы они не удаляли себя до первого коммита.
git clean -fd examples -e reset.sh -e reset.command -e reset.bat

echo "examples/ возвращён к состоянию из git." >&2
pause_exit 0
