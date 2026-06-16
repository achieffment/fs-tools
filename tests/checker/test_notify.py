"""Тесты веб-хука уведомлений (notify): тело, заголовок, приоритеты, гашение.

Тяжёлые зависимости импортируются лениво внутри функций, поэтому на уровне модуля
`notify` атрибутов `requests`/`dotenv_values` нет: значения .env подменяются через
`notify._file_values`, а сеть — через `requests.post` реального модуля.
"""
from typing import Any

import pytest

from fs_tools.checker import notify


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
    """Изоляция от реального .env и переменных окружения процесса."""
    monkeypatch.setattr(notify, "_file_values", lambda: {})
    monkeypatch.delenv(notify._URL_KEY, raising=False)
    monkeypatch.delenv(notify._TOK_KEY, raising=False)


def test_no_url_skips(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("x") is False
    assert rec.calls == []


def test_posts_text_and_bearer(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setattr(notify, "_file_values", lambda: {
        notify._URL_KEY: "https://example.com/hook",
        notify._TOK_KEY: "secret",
    })
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("есть ошибки") is True
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["url"] == "https://example.com/hook"
    assert call["json"] == {"text": "есть ошибки"}
    assert call["headers"]["Authorization"] == "Bearer secret"


def test_process_env_overrides_env_file(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    # Намеренная смена приоритета: переменные окружения процесса важнее .env.
    monkeypatch.setenv(notify._URL_KEY, "https://from-env/hook")
    monkeypatch.setattr(notify, "_file_values", lambda: {notify._URL_KEY: "https://from-file/hook"})
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    notify.send_webhook("x")
    assert rec.calls[0]["url"] == "https://from-env/hook"


def test_no_token_omits_header(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setattr(notify, "_file_values", lambda: {notify._URL_KEY: "https://example.com/hook"})
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    notify.send_webhook("x")
    assert "Authorization" not in rec.calls[0]["headers"]


def test_non_https_url_skips(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    # URL обязан быть https — токен не уходит по нешифрованному каналу.
    monkeypatch.setattr(notify, "_file_values", lambda: {
        notify._URL_KEY: "http://example.com/hook",
        notify._TOK_KEY: "secret",
    })
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("x") is False
    assert rec.calls == []


def test_swallows_exceptions(monkeypatch: pytest.MonkeyPatch, isolated: None) -> None:
    monkeypatch.setattr(notify, "_file_values", lambda: {notify._URL_KEY: "https://example.com/hook"})
    rec = _Recorder()
    rec.raise_exc = RuntimeError("network down")
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("x") is False
