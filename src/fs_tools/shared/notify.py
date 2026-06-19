"""Общая отправка веб-хука: чтение конфигурации из env и fire-and-forget POST.

Логика единая для режимов checker/syncher: URL+токен читаются по переданным ключам,
URL обязан быть `https://`, зависимость `requests` импортируется лениво.
"""
from __future__ import annotations

import logging
import os

from . import env

_DEFAULT_TIMEOUT = 2.0


def load_webhook_config(url_key: str, tok_key: str) -> tuple[str, str] | None:
    """(url, tok); None, если URL по `url_key` не задан."""
    env.load_env()
    url = (os.environ.get(url_key) or "").strip()
    if not url:
        return None
    tok = (os.environ.get(tok_key) or "").strip()
    return url, tok


def send_webhook(
    text: str,
    *,
    url_key: str,
    tok_key: str,
    logger: logging.Logger,
    timeout: float = _DEFAULT_TIMEOUT,
) -> bool:
    """Отправить `{\"text\": text}` по ключам конфигурации; ошибки не роняют прогон."""
    config = load_webhook_config(url_key, tok_key)
    if config is None:
        return False
    url, tok = config
    if not url.startswith("https://"):              # без TLS токен не отправляем
        logger.debug("веб-хук пропущен: URL не https")
        return False
    try:
        import requests
    except ImportError:                             # requests — опциональная зависимость
        logger.debug("requests не установлен — веб-хук пропущен")
        return False
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        requests.post(url, json={"text": text}, headers=headers, timeout=timeout)
    except Exception as exc:                        # fire-and-forget: не влияет на прогон
        logger.debug("веб-хук не доставлен: %s", exc)
        return False
    return True
