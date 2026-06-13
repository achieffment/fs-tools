"""Пакет проверки наличия папок и файлов по правилам .fs-rule.

Структуру дерева не меняет; при нарушениях пишет журнал .fs-log и шлёт веб-хук.
Публичное API: импортируйте отсюда, а не из подмодулей напрямую.
"""
from __future__ import annotations

from .cli import main
from .engine import CheckResult, FsChecker
from .log import FS_LOG, write_fs_log
from .notify import load_webhook_config, send_webhook
from .report import format_report
from .rule import FsRule, FsRuleError, Negation, Rule, load_fs_rule

__all__ = [
    "main",
    "FsChecker",
    "CheckResult",
    "format_report",
    "load_fs_rule",
    "FsRule",
    "Rule",
    "Negation",
    "FsRuleError",
    "FS_LOG",
    "write_fs_log",
    "load_webhook_config",
    "send_webhook",
]
