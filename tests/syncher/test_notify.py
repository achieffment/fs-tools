"""Тесты syncher.notify."""

import pytest

from fs_tools.syncher import notify


def test_notify_constants() -> None:
    """Проверяет env-ключи и таймаут модуля syncher.notify."""
    assert (notify.URL_KEY, notify.TOK_KEY, notify.TIMEOUT) == (
        "FSSYN_WEBHOOK_URL",
        "FSSYN_WEBHOOK_TOK",
        2.0,
    )


def test_notify_delegates_to_shared(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет, что обёртка вызывает shared.notify с корректными ключами."""
    called: dict[str, object] = {}

    def _fake_load(url_key: str, tok_key: str) -> tuple[str, str]:
        called["load"] = (url_key, tok_key)
        return ("https://example.com/hook", "tok")

    def _fake_send(text: str, **kwargs: object) -> bool:
        called["send"] = (text, kwargs)
        return True

    monkeypatch.setattr(notify.shared_notify, "load_webhook_config", _fake_load)
    monkeypatch.setattr(notify.shared_notify, "send_webhook", _fake_send)

    assert notify.load_webhook_config() == ("https://example.com/hook", "tok")
    assert notify.send_webhook("есть ошибки")
    assert called["load"] == (notify.URL_KEY, notify.TOK_KEY)
    text, kwargs = called["send"]
    assert text == "есть ошибки"
    assert kwargs["url_key"] == notify.URL_KEY
    assert kwargs["tok_key"] == notify.TOK_KEY
