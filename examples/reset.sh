#!/usr/bin/env bash
# Откат прогона нормализатора по examples/: возвращает дерево к состоянию из git
# (восстанавливает отслеживаемые файлы и удаляет пустые каталоги-сироты).
set -euo pipefail

here="$(cd -- "$(dirname -- "$0")" && pwd)"   # .../examples
repo="$(cd -- "$here/.." && pwd)"             # корень репозитория
cd "$repo"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Это не git-репозиторий — откат через git недоступен." >&2
    exit 1
fi

# Восстанавливаем отслеживаемые файлы (индекс + рабочее дерево).
if ! git restore --staged --worktree -- examples 2>/dev/null; then
    # Откат для старого git (< 2.23), где нет команды restore.
    git reset -q -- examples
    git checkout -- examples
fi

# Удаляем неотслеживаемое, включая опустевшие нормализованные каталоги
# (git не хранит пустые каталоги, поэтому одного checkout недостаточно).
# Сами reset-скрипты исключаем, чтобы они не удаляли себя до первого коммита.
git clean -fd examples -e reset.sh -e reset.command -e reset.bat

echo "examples/ возвращён к состоянию из git." >&2
