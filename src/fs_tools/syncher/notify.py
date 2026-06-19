"""Веб-хук syncher: тонкая обёртка над общей логикой `shared.notify`."""
from __future__ import annotations

import logging

from ..shared import notify as shared_notify

_URL_KEY = "FSSYN_WEBHOOK_URL"
_TOK_KEY = "FSSYN_WEBHOOK_TOK"

# Минимальный таймаут: «выстрелил и забыл», не ждём ответа сервиса.
_TIMEOUT = 2.0

_log = logging.getLogger(__name__)


def load_webhook_config() -> tuple[str, str] | None:
    """(url, tok); None, если URL не задан."""
    return shared_notify.load_webhook_config(_URL_KEY, _TOK_KEY)


def send_webhook(text: str) -> bool:
    """Отправить уведомление syncher и вернуть результат попытки отправки."""
    return shared_notify.send_webhook(
        text,
        url_key=_URL_KEY,
        tok_key=_TOK_KEY,
        logger=_log,
        timeout=_TIMEOUT,
    )
