"""Общий контракт тестов checker/syncher notify."""
from __future__ import annotations

import logging
from types import ModuleType
from typing import Any

import pytest


def assert_notify_contract(
    monkeypatch: pytest.MonkeyPatch,
    mod: ModuleType,
    *,
    url_key: str,
    tok_key: str,
    logger_name: str,
) -> None:
    """Проверить ключи окружения и делегирование в shared.notify."""
    assert mod.URL_KEY == url_key
    assert mod.TOK_KEY == tok_key

    captured: dict[str, Any] = {}

    def _fake_load(url_key: str, tok_key: str) -> tuple[str, str]:
        captured["url_key"] = url_key
        captured["tok_key"] = tok_key
        return ("https://example.com/hook", "tok")

    monkeypatch.setattr(mod.shared_notify, "load_webhook_config", _fake_load)
    assert mod.load_webhook_config() == ("https://example.com/hook", "tok")
    assert captured == {"url_key": mod.URL_KEY, "tok_key": mod.TOK_KEY}

    captured.clear()

    def _fake_send(
        text: str,
        *,
        url_key: str,
        tok_key: str,
        logger: logging.Logger,
        timeout: float,
    ) -> bool:
        captured.update(
            text=text,
            url_key=url_key,
            tok_key=tok_key,
            logger_name=logger.name,
            timeout=timeout,
        )
        return True

    monkeypatch.setattr(mod.shared_notify, "send_webhook", _fake_send)
    assert mod.send_webhook("есть ошибки") is True
    assert captured == {
        "text": "есть ошибки",
        "url_key": mod.URL_KEY,
        "tok_key": mod.TOK_KEY,
        "logger_name": logger_name,
        "timeout": mod.TIMEOUT,
    }
