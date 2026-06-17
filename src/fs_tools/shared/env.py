"""Доступ к единому `.env` проекта: путь, права и однократная загрузка в окружение.

Путь к `.env`: `FS_TOOLS_HOME/.env`, при отсутствии переменной — `.env` в текущем
рабочем каталоге (привязка к `__file__` не используется: cron/таймер стартует из
любого cwd, а пакет может быть установлен в произвольное место).

Значения подгружаются штатным `python-dotenv` (`load_dotenv`) прямо в `os.environ`,
после чего консьюмеры читают обычный `os.environ`/`os.getenv`. Приоритет источников
(переменные окружения процесса важнее значений из `.env`) обеспечивает `override=False`.

Зависимость `python-dotenv` импортируется лениво — внутри функции, чтобы модуль
`shared` работал без чужого extra (например, в режиме normalizer, которому `.env` не
нужен; веб-хук читают checker и syncher).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)

_loaded = False


def env_path() -> Path:
    """Путь к единому `.env`: `FS_TOOLS_HOME/.env` либо `.env` в текущем каталоге."""
    home = os.environ.get("FS_TOOLS_HOME")
    return Path(home, ".env") if home else Path.cwd() / ".env"


def harden_permissions(path: Path) -> None:
    """На POSIX привести права `.env` к `600` (секрет не должен читаться другими)."""
    if os.name != "posix":
        return
    try:
        mode = path.stat().st_mode & 0o777
        if mode != 0o600:
            path.chmod(0o600)
    except OSError as exc:                          # права — best-effort, не роняем прогон
        _log.debug("не удалось выставить права .env: %s", exc)


def load_env() -> None:
    """Однократно подгрузить `.env` в окружение процесса (`override=False`: процесс важнее).

    Идемпотентна (повторный вызов — no-op). `dotenv` импортируется лениво; без пакета
    или файла тихо выходит. Привязка к разовому запуску CLI: при смене `FS_TOOLS_HOME`
    в рамках одного процесса повторно не перечитывает.
    """
    global _loaded
    if _loaded:
        return
    _loaded = True
    path = env_path()
    if not path.is_file():
        return
    harden_permissions(path)
    try:
        from dotenv import load_dotenv
    except ImportError:                             # без extra checker/syncher .env игнорируется
        _log.debug("python-dotenv не установлен — .env не читается")
        return
    load_dotenv(path, override=False)
