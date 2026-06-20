"""Тесты checker.notify."""

import pytest

from fs_tools.checker import notify

from .notify_contract import assert_notify_contract


def test_env_keys_constants() -> None:
    """Проверяет имена env-ключей checker."""
    assert notify.URL_KEY == "FSCHK_WEBHOOK_URL"
    assert notify.TOK_KEY == "FSCHK_WEBHOOK_TOK"


def test_load_webhook_config_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет делегирование загрузки/отправки через общий контракт."""
    assert_notify_contract(
        monkeypatch,
        notify,
        url_key="FSCHK_WEBHOOK_URL",
        tok_key="FSCHK_WEBHOOK_TOK",
        logger_name="fs_tools.checker.notify",
    )


def test_send_webhook_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Проверяет делегирование отправки через общий контракт."""
    assert_notify_contract(
        monkeypatch,
        notify,
        url_key="FSCHK_WEBHOOK_URL",
        tok_key="FSCHK_WEBHOOK_TOK",
        logger_name="fs_tools.checker.notify",
    )
