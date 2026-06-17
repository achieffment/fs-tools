"""Веб-хук о нарушениях файловой структуры (fire-and-forget).

Конфигурация — из единого `.env` проекта (`FSCHK_WEBHOOK_URL` / `FSCHK_WEBHOOK_TOK`).
Загрузку `.env` в окружение и приоритет источников (переменные окружения процесса
важнее значений из `.env`) берёт на себя общий модуль `shared.env`; здесь конфиг
читается из `os.environ`.

Тяжёлая зависимость `requests` импортируется лениво — внутри функции, чтобы команда
`fs-checker` импортировалась и работала без extra `checker`.

Запрос отправляется по принципам UDP: минимальный таймаут, ответ не проверяется,
любые сетевые ошибки гасятся — задача лишь известить, не блокируя прогон.
"""
from __future__ import annotations

import logging
import os

from ..shared import env

_URL_KEY = "FSCHK_WEBHOOK_URL"
_TOK_KEY = "FSCHK_WEBHOOK_TOK"

# Минимальный таймаут: «выстрелил и забыл», не ждём ответа сервиса.
_TIMEOUT = 2.0

_log = logging.getLogger(__name__)


def load_webhook_config() -> tuple[str, str] | None:
    """(url, tok); None, если URL не задан.

    Приоритет: переменные окружения процесса важнее значений из `.env`. Токен
    необязателен (заголовок Bearer добавляется лишь при непустом значении) —
    определяющим является адрес: без него уведомления отключены.
    """
    env.load_env()
    url = (os.environ.get(_URL_KEY) or "").strip()
    if not url:
        return None
    tok = (os.environ.get(_TOK_KEY) or "").strip()
    return url, tok


def send_webhook(text: str) -> bool:
    """Отправить {"text": text} на адрес из конфигурации (Bearer-токен — в заголовке).

    Fire-and-forget: без конфигурации тихо выходит; URL обязан быть `https://` (токен
    не уходит по нешифрованному каналу); минимальный таймаут, ответ не проверяется,
    любые ошибки (сеть, таймаут, недоступность) гасятся. Токен в логи не пишется —
    только факт/причина сбоя на уровне debug. Возвращает True, если попытка отправки
    состоялась, иначе False.
    """
    config = load_webhook_config()
    if config is None:
        return False
    url, tok = config
    if not url.startswith("https://"):              # без TLS токен не отправляем
        _log.debug("веб-хук пропущен: URL не https")
        return False
    try:
        import requests
    except ImportError:                             # без extra checker отправка недоступна
        _log.debug("requests не установлен — веб-хук пропущен")
        return False
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        requests.post(url, json={"text": text}, headers=headers, timeout=_TIMEOUT)
    except Exception as exc:                        # UDP-подобно: не влияет на прогон
        _log.debug("веб-хук не доставлен: %s", exc)
        return False
    return True
