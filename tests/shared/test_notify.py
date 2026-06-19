"""Тесты общей отправки веб-хука (shared.notify): конфиг, https, заголовок, гашение."""
import logging
from typing import Any

import pytest
import requests

from fs_tools.shared import env, notify

_URL_KEY = "FS_TOOLS_TEST_WEBHOOK_URL"
_TOK_KEY = "FS_TOOLS_TEST_WEBHOOK_TOK"
_LOG = logging.getLogger(__name__)


class _Recorder:
    """Заглушка requests.post: пишет вызовы и опционально бросает исключение."""

    def __init__(self) -> None:
        """Вспомогательная функция для теста."""
        self.calls: list[dict[str, Any]] = []
        self.raise_exc: Exception | None = None

    def __call__(self, url: str, **kwargs: Any) -> None:
        """Вспомогательная функция для теста."""
        self.calls.append({"url": url, **kwargs})
        if self.raise_exc is not None:
            raise self.raise_exc


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Изоляция от реального .env и переменных окружения процесса."""
    monkeypatch.setattr(env, "load_env", lambda: None)
    monkeypatch.delenv(_URL_KEY, raising=False)
    monkeypatch.delenv(_TOK_KEY, raising=False)


def test_no_url_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет пропуск отправки без URL."""
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("x", url_key=_URL_KEY, tok_key=_TOK_KEY, logger=_LOG) is False
    assert not rec.calls


def test_posts_text_and_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет отправку текста и Bearer-заголовка."""
    monkeypatch.setenv(_URL_KEY, "https://example.com/hook")
    monkeypatch.setenv(_TOK_KEY, "secret")
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    assert (
        notify.send_webhook("есть ошибки", url_key=_URL_KEY, tok_key=_TOK_KEY, logger=_LOG)
        is True
    )
    assert len(rec.calls) == 1
    call = rec.calls[0]
    assert call["url"] == "https://example.com/hook"
    assert call["json"] == {"text": "есть ошибки"}
    assert call["headers"]["Authorization"] == "Bearer secret"


def test_no_token_omits_header(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет отправку без Authorization при пустом токене."""
    monkeypatch.setenv(_URL_KEY, "https://example.com/hook")
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    notify.send_webhook("x", url_key=_URL_KEY, tok_key=_TOK_KEY, logger=_LOG)
    assert "Authorization" not in rec.calls[0]["headers"]


def test_non_https_url_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет блокировку не-https веб-хука."""
    monkeypatch.setenv(_URL_KEY, "http://example.com/hook")
    monkeypatch.setenv(_TOK_KEY, "secret")
    rec = _Recorder()
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("x", url_key=_URL_KEY, tok_key=_TOK_KEY, logger=_LOG) is False
    assert not rec.calls


def test_swallows_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет гашение исключений транспорта."""
    monkeypatch.setenv(_URL_KEY, "https://example.com/hook")
    rec = _Recorder()
    rec.raise_exc = requests.RequestException("network down")
    monkeypatch.setattr("requests.post", rec)
    assert notify.send_webhook("x", url_key=_URL_KEY, tok_key=_TOK_KEY, logger=_LOG) is False


def test_load_webhook_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет чтение URL/токена из окружения."""
    monkeypatch.setenv(_URL_KEY, "https://example.com/hook")
    monkeypatch.setenv(_TOK_KEY, "secret")
    assert notify.load_webhook_config(_URL_KEY, _TOK_KEY) == (
        "https://example.com/hook",
        "secret",
    )
