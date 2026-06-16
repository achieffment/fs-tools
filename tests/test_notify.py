"""Тесты веб-хука уведомлений (syncher.notify): тело, заголовок, приоритеты, гашение."""
from typing import Any

import pytest

from syncher import notify


class _Recorder:
    """Заглушка requests.post: пишет вызовы и опционально бросает исключение."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.raise_exc: Exception | None = None

    def __call__(self, url: str, **kwargs: Any) -> None:
        self.calls.append({"url": url, **kwargs})
        if self.raise_exc is not None:
            raise self.raise_exc


@pytest.fixture()
def isolated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notify, "dotenv_values", lambda *_: {})
    monkeypatch.delenv(notify._URL_KEY, raising=False)
    monkeypatch.delenv(notify._TOK_KEY, raising=False)


def test_no_url_skips(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    rec = _Recorder()
    monkeypatch.setattr(notify.requests, "post", rec)
    assert notify.send_webhook("x") is False
    assert rec.calls == []


def test_posts_text_and_bearer(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setattr(notify, "dotenv_values", lambda *_: {
        notify._URL_KEY: "https://example.com/hook",
        notify._TOK_KEY: "secret",
    })
    rec = _Recorder()
    monkeypatch.setattr(notify.requests, "post", rec)
    assert notify.send_webhook("есть ошибки") is True
    call = rec.calls[0]
    assert call["url"] == "https://example.com/hook"
    assert call["json"] == {"text": "есть ошибки"}
    assert call["headers"]["Authorization"] == "Bearer secret"


def test_env_file_overrides_process_env(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setenv(notify._URL_KEY, "https://from-env/hook")
    monkeypatch.setattr(notify, "dotenv_values", lambda *_: {notify._URL_KEY: "https://from-file/hook"})
    rec = _Recorder()
    monkeypatch.setattr(notify.requests, "post", rec)
    notify.send_webhook("x")
    assert rec.calls[0]["url"] == "https://from-file/hook"


def test_no_token_omits_header(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setattr(notify, "dotenv_values", lambda *_: {notify._URL_KEY: "https://example.com/hook"})
    rec = _Recorder()
    monkeypatch.setattr(notify.requests, "post", rec)
    notify.send_webhook("x")
    assert "Authorization" not in rec.calls[0]["headers"]


def test_swallows_exceptions(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setattr(notify, "dotenv_values", lambda *_: {notify._URL_KEY: "https://example.com/hook"})
    rec = _Recorder()
    rec.raise_exc = RuntimeError("network down")
    monkeypatch.setattr(notify.requests, "post", rec)
    assert notify.send_webhook("x") is False
