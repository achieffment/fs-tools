#!/usr/bin/env bash
# Общий bootstrap для обёрток Linux/macOS: готовит .venv в корне проекта и делает
# editable-установку со всеми тремя extra. Подключается обёртками через `source`; сам
# по себе ничего не запускает. После вызова `_fs_tools_bootstrap "<корень>"` задаёт:
#   FS_TOOLS_HOME — корень проекта (нужен для поиска единого .env);
#   FS_TOOLS_VBIN — каталог bin виртуального окружения (fs-normalizer/fs-checker/fs-syncher).
# Возвращает ненулевой код при сбое подготовки окружения.

_fs_tools_bootstrap() {
    local root="$1"
    export FS_TOOLS_HOME="$root"
    local venv="$root/.venv"
    FS_TOOLS_VBIN="$venv/bin"
    local pyex="$FS_TOOLS_VBIN/python"

    # Переустановка только если окружения нет или в нём не хватает зависимостей.
    if [ ! -x "$pyex" ] || ! "$pyex" -c "import fs_tools, pathspec, unidecode, requests, dotenv" >/dev/null 2>&1; then
        echo "Подготовка окружения (.venv)..." >&2
        rm -rf "$venv"
        if ! python3 -m venv "$venv"; then
            echo "Не удалось создать .venv (возможно, временный сбой сети). Повторите запуск." >&2
            rm -rf "$venv"
            return 1
        fi
        if ! "$pyex" -m pip install -e "${root}[normalizer,checker,syncher]"; then
            echo "Не удалось установить зависимости (возможно, временный сбой сети). Повторите запуск." >&2
            rm -rf "$venv"
            return 1
        fi
    fi
    return 0
}
