"""Веб-хук о нарушениях файловой структуры (fire-and-forget).

Конфигурация — из единого `.env` проекта (`FSCHK_WEBHOOK_URL` / `FSCHK_WEBHOOK_TOK`).
Путь к `.env`: `FS_TOOLS_HOME/.env`, при отсутствии переменной — `.env` в текущем
рабочем каталоге (привязка к `__file__` не используется: cron/таймер стартует из
любого cwd, а пакет может быть установлен в произвольное место). Приоритет источников:
переменные окружения процесса важнее значений из `.env`.

Тяжёлые зависимости (`requests`, `python-dotenv`) импортируются лениво — внутри
функций, чтобы команда `fs-chk` импортировалась и работала без extra `checker`.

Запрос отправляется по принципам UDP: минимальный таймаут, ответ не проверяется,
любые сетевые ошибки гасятся — задача лишь известить, не блокируя прогон.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

_URL_KEY = "FSCHK_WEBHOOK_URL"
_TOK_KEY = "FSCHK_WEBHOOK_TOK"

# Минимальный таймаут: «выстрелил и забыл», не ждём ответа сервиса.
_TIMEOUT = 2.0

_log = logging.getLogger(__name__)


def _env_path() -> Path:
    """Путь к единому `.env`: `FS_TOOLS_HOME/.env` либо `.env` в текущем каталоге."""
    home = os.environ.get("FS_TOOLS_HOME")
    return Path(home, ".env") if home else Path.cwd() / ".env"


def _harden_env_permissions(path: Path) -> None:
    """На POSIX привести права `.env` к `600` (секрет не должен читаться другими)."""
    if os.name != "posix":
        return
    try:
        mode = path.stat().st_mode & 0o777
        if mode != 0o600:
            path.chmod(0o600)
    except OSError as exc:                          # права — best-effort, не роняем прогон
        _log.debug("не удалось выставить права .env: %s", exc)


def _file_values() -> dict[str, str | None]:
    """Значения из `.env` (или пустой словарь, если файла/`python-dotenv` нет)."""
    path = _env_path()
    if not path.is_file():
        return {}
    _harden_env_permissions(path)
    try:
        from dotenv import dotenv_values
    except ImportError:                             # без extra checker .env просто игнорируется
        _log.debug("python-dotenv не установлен — .env не читается")
        return {}
    return dotenv_values(path)


def load_webhook_config() -> tuple[str, str] | None:
    """(url, tok); None, если URL не задан.

    Приоритет: переменные окружения процесса важнее значений из `.env`. Токен
    необязателен (заголовок Bearer добавляется лишь при непустом значении) —
    определяющим является адрес: без него уведомления отключены.
    """
    file_vals = _file_values()
    url = (os.environ.get(_URL_KEY) or file_vals.get(_URL_KEY) or "").strip()
    if not url:
        return None
    tok = (os.environ.get(_TOK_KEY) or file_vals.get(_TOK_KEY) or "").strip()
    return url, tok


def send_webhook(text: str) -> bool:
    """Отправить {"text": text} на адрес из конфигурации (Bearer-токен — в заголовке).

    Fire-and-forget: без конфигурации тихо выходит; URL обязан быть `https://` (токен
    не уходит по нешифрованному каналу); минимальный таймаут, ответ не проверяется,
    любые ошибки (сеть, таймаут, недоступность) гасятся. Токен в логи не пишется —
    только факт/причина сбоя на уровне debug. Возвращает True, если попытка отправки
    состоялась, иначе False.
    """
    config = load_webhook_config()
    if config is None:
        return False
    url, tok = config
    if not url.startswith("https://"):              # без TLS токен не отправляем
        _log.debug("веб-хук пропущен: URL не https")
        return False
    try:
        import requests
    except ImportError:                             # без extra checker отправка недоступна
        _log.debug("requests не установлен — веб-хук пропущен")
        return False
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        requests.post(url, json={"text": text}, headers=headers, timeout=_TIMEOUT)
    except Exception as exc:                         # UDP-подобно: не влияет на прогон
        _log.debug("веб-хук не доставлен: %s", exc)
        return False
    return True
