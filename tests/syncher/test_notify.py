"""Тесты syncher.notify: ключи окружения и делегирование в shared.notify."""
import logging

import pytest

from fs_tools.syncher import notify


def test_env_keys_constants() -> None:
    assert notify._URL_KEY == "FSSYN_WEBHOOK_URL"
    assert notify._TOK_KEY == "FSSYN_WEBHOOK_TOK"


def test_load_webhook_config_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def _fake(url_key: str, tok_key: str) -> tuple[str, str]:
        captured["url_key"] = url_key
        captured["tok_key"] = tok_key
        return ("https://example.com/hook", "tok")

    monkeypatch.setattr(notify.shared_notify, "load_webhook_config", _fake)
    assert notify.load_webhook_config() == ("https://example.com/hook", "tok")
    assert captured == {"url_key": notify._URL_KEY, "tok_key": notify._TOK_KEY}


def test_send_webhook_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake(
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

    monkeypatch.setattr(notify.shared_notify, "send_webhook", _fake)
    assert notify.send_webhook("есть ошибки") is True
    assert captured == {
        "text": "есть ошибки",
        "url_key": notify._URL_KEY,
        "tok_key": notify._TOK_KEY,
        "logger_name": "fs_tools.syncher.notify",
        "timeout": notify._TIMEOUT,
    }
