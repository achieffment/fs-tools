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
    cfg = load_webhook_config(url_key, tok_key)
    if cfg is None:
        return False
    url, tok = cfg
    if not url.startswith("https://"):              # без TLS токен не отправляем
        logger.debug("веб-хук пропущен: URL не https")
        return False
    try:
        requests = importlib.import_module("requests")
    except ImportError:                             # requests — опциональная зависимость
        logger.debug("requests не установлен — веб-хук пропущен")
        return False
    rexcept = requests.RequestException
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        requests.post(url, json={"text": text}, headers=headers, timeout=timeout)
    except rexcept as exc:                      # fire-and-forget: не влияет на прогон
        logger.debug("веб-хук не доставлен: %s", exc)
        return False
    return True


def make_load_webhook_config(
    url_key: str,
    tok_key: str,
) -> Callable[[], tuple[str, str] | None]:
    """Собрать `load_webhook_config` для конкретных env-ключей режима."""

    def _load_webhook_config() -> tuple[str, str] | None:
        return load_webhook_config(url_key, tok_key)

    return _load_webhook_config


def make_send_webhook(
    *,
    url_key: str,
    tok_key: str,
    logger: logging.Logger,
    timeout: float = _DEFAULT_TIMEOUT,
) -> Callable[[str], bool]:
    """Собрать `send_webhook` для конкретных env-ключей и логгера режима."""

    def _send_webhook(text: str) -> bool:
        return send_webhook(
            text,
            url_key=url_key,
            tok_key=tok_key,
            logger=logger,
            timeout=timeout,
        )

    return _send_webhook


def make_mode_webhook(
    *,
    prefix: str,
    logger: logging.Logger,
    timeout: float = _DEFAULT_TIMEOUT,
) -> tuple[Callable[[], tuple[str, str] | None], Callable[[str], bool]]:
    """Собрать загрузчик конфигурации и отправку веб-хука для префикса режима."""
    url_key = f"{prefix}_WEBHOOK_URL"
    tok_key = f"{prefix}_WEBHOOK_TOK"
    load_cfg = make_load_webhook_config(url_key, tok_key)
    send_hook = make_send_webhook(
        url_key=url_key,
        tok_key=tok_key,
        logger=logger,
        timeout=timeout,
    )
    return load_cfg, send_hook


def make_mode_exports(
    *,
    prefix: str,
    logger: logging.Logger,
    timeout: float = _DEFAULT_TIMEOUT,
) -> tuple[str, str, float, Callable[[], tuple[str, str] | None], Callable[[str], bool]]:
    """Собрать полный набор mode-экспортов (`URL_KEY`, `TOK_KEY`, `TIMEOUT`, callables)."""
    url_key = f"{prefix}_WEBHOOK_URL"
    tok_key = f"{prefix}_WEBHOOK_TOK"
    load_cfg, send_hook = make_mode_webhook(
        prefix=prefix,
        logger=logger,
        timeout=timeout,
    )
    return url_key, tok_key, timeout, load_cfg, send_hook
