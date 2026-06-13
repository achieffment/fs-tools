"""Веб-хук о нарушениях файловой структуры (fire-and-forget).

Конфигурация — из .env рядом со скриптом (FSCHK_WEBHOOK_URL / FSCHK_WEBHOOK_TOK)
с откатом на переменные окружения процесса. Запрос отправляется по принципам UDP:
минимальный таймаут, ответ не проверяется, любые сетевые ошибки гасятся — задача
лишь известить, не блокируя прогон.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import dotenv_values

# .env лежит рядом со скриптом (корень проекта = родитель пакета checker/), а не в
# проверяемом каталоге: путь фиксирован, т.к. cron/таймер стартует из любого cwd.
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

_URL_KEY = "FSCHK_WEBHOOK_URL"
_TOK_KEY = "FSCHK_WEBHOOK_TOK"

# Минимальный таймаут: «выстрелил и забыл», не ждём ответа сервиса.
_TIMEOUT = 2.0


def load_webhook_config() -> tuple[str, str] | None:
    """(url, tok) из .env рядом со скриптом или из окружения; None, если URL не задан.

    Значения .env приоритетнее переменных окружения процесса. Токен необязателен
    (заголовок Bearer добавляется лишь при непустом значении) — определяющим является
    адрес: без него уведомления отключены.
    """
    env = dotenv_values(_ENV_PATH)
    url = (env.get(_URL_KEY) or os.environ.get(_URL_KEY) or "").strip()
    if not url:
        return None
    tok = (env.get(_TOK_KEY) or os.environ.get(_TOK_KEY) or "").strip()
    return url, tok


def send_webhook(text: str) -> bool:
    """Отправить {"text": text} на адрес из .env (Bearer-токен — в заголовке).

    Fire-and-forget: без конфигурации тихо выходит; минимальный таймаут, ответ не
    проверяется, любые ошибки (сеть, таймаут, недоступность сервиса) гасятся.
    Возвращает True, если попытка отправки состоялась, иначе False.
    """
    config = load_webhook_config()
    if config is None:
        return False
    url, tok = config
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    try:
        requests.post(url, json={"text": text}, headers=headers, timeout=_TIMEOUT)
    except Exception:           # UDP-подобно: уведомление не должно влиять на прогон
        return False
    return True
