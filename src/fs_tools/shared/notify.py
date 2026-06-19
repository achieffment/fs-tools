"""Общая отправка веб-хука: чтение конфигурации из env и fire-and-forget POST.

Логика единая для режимов checker/syncher: URL+токен читаются по переданным ключам,
URL обязан быть `https://`, зависимость `requests` импортируется лениво.
"""
from __future__ import annotations

import importlib
import logging
import os
from collections.abc import Callable

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
        requests = importlib.import_module("requests")
    except ImportError:                             # requests — опциональная зависимость
        logger.debug("requests не установлен — веб-хук пропущен")
        return False
    request_exc = requests.RequestException
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        requests.post(url, json={"text": text}, headers=headers, timeout=timeout)
    except request_exc as exc:                      # fire-and-forget: не влияет на прогон
        logger.debug("веб-хук не доставлен: %s", exc)
        return False
    return True


def make_mode_notifier(
    *,
    url_key: str,
    tok_key: str,
    logger: logging.Logger,
    timeout: float = _DEFAULT_TIMEOUT,
) -> tuple[Callable[[], tuple[str, str] | None], Callable[[str], bool]]:
    """Собрать функции `load_webhook_config`/`send_webhook` для конкретного режима."""

    def _load_webhook_config() -> tuple[str, str] | None:
        return load_webhook_config(url_key, tok_key)

    def _send_webhook(text: str) -> bool:
        return send_webhook(
            text,
            url_key=url_key,
            tok_key=tok_key,
            logger=logger,
            timeout=timeout,
        )

    return _load_webhook_config, _send_webhook


def make_mode_exports(
    *,
    url_key: str,
    tok_key: str,
    logger_name: str,
    timeout: float = _DEFAULT_TIMEOUT,
) -> tuple[str, str, float, Callable[[], tuple[str, str] | None], Callable[[str], bool]]:
    """Собрать публичные константы и функции webhook-режима."""
    logger = logging.getLogger(logger_name)
    load_cfg, send = make_mode_notifier(
        url_key=url_key,
        tok_key=tok_key,
        logger=logger,
        timeout=timeout,
    )
    return url_key, tok_key, timeout, load_cfg, send
