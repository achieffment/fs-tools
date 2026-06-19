"""Тесты checker.notify."""

import logging

import pytest

from fs_tools.checker import notify


def test_env_keys_constants() -> None:
    """Проверяет имена env-ключей checker."""
    assert notify.URL_KEY == "FSCHK_WEBHOOK_URL"
    assert notify.TOK_KEY == "FSCHK_WEBHOOK_TOK"


def test_load_webhook_config_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет делегирование загрузки конфигурации."""
    captured: dict[str, str] = {}

    def _fake_load(url_key: str, tok_key: str) -> tuple[str, str]:
        captured["url_key"] = url_key
        captured["tok_key"] = tok_key
        return ("https://example.com/hook", "tok")

    monkeypatch.setattr(notify.shared_notify, "load_webhook_config", _fake_load)
    assert notify.load_webhook_config() == ("https://example.com/hook", "tok")
    assert captured == {"url_key": notify.URL_KEY, "tok_key": notify.TOK_KEY}


def test_send_webhook_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет делегирование отправки веб-хука."""
    captured: dict[str, object] = {}

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

    monkeypatch.setattr(notify.shared_notify, "send_webhook", _fake_send)
    assert notify.send_webhook("есть ошибки") is True
    assert captured["url_key"] == notify.URL_KEY
    assert captured["tok_key"] == notify.TOK_KEY
    assert captured["logger_name"] == "fs_tools.checker.notify"
    assert captured["timeout"] == notify.TIMEOUT
