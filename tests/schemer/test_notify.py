"""Тесты schemer.notify."""

import pytest

from fs_tools.schemer import notify


def test_env_keys_and_timeout_constants() -> None:
    """Проверяет имена env-ключей и таймаут schemer."""
    assert (notify.URL_KEY, notify.TOK_KEY, notify.TIMEOUT) == (
        "FSSCH_WEBHOOK_URL",
        "FSSCH_WEBHOOK_TOK",
        2.0,
    )


def test_load_webhook_config_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет делегирование загрузки конфигурации в shared.notify."""
    called: dict[str, object] = {}

    def _fake_load(url_key: str, tok_key: str) -> tuple[str, str]:
        called["load"] = (url_key, tok_key)
        return ("https://example.com/hook", "tok")

    monkeypatch.setattr(notify.shared_notify, "load_webhook_config", _fake_load)
    assert notify.load_webhook_config() == ("https://example.com/hook", "tok")
    assert called["load"] == (notify.URL_KEY, notify.TOK_KEY)


def test_send_webhook_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет делегирование отправки в shared.notify с корректными ключами."""
    called: dict[str, object] = {}

    def _fake_send(text: str, **kwargs: object) -> bool:
        called["send"] = (text, kwargs)
        return True

    monkeypatch.setattr(notify.shared_notify, "send_webhook", _fake_send)
    assert notify.send_webhook("есть ошибки") is True
    text, kwargs = called["send"]
    assert text == "есть ошибки"
    assert kwargs["url_key"] == notify.URL_KEY
    assert kwargs["tok_key"] == notify.TOK_KEY
    assert kwargs["logger"].name == "fs_tools.schemer.notify"
    assert kwargs["timeout"] == notify.TIMEOUT
