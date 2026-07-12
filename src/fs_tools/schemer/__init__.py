"""Пакет проверки структуры и контента базы знаний по fs-schm.toml (read-only).

Публичное API: импортируйте отсюда, а не из подмодулей напрямую.
"""
from __future__ import annotations

from .config import (
    CONFIG_NAME,
    ContentRule,
    Group,
    GroupFile,
    SchemeConfig,
    SchemeConfigError,
    load_scheme_config,
    parse_scheme_config,
)
from .engine import FsSchemer, SchemerResult, Violation
from .log import FS_LOG, write_fs_log
from .notify import load_webhook_config, send_webhook
from .report import format_report, format_violation
from .runner import main

__all__ = [
    "main",
    "FsSchemer",
    "SchemerResult",
    "Violation",
    "format_report",
    "format_violation",
    "load_scheme_config",
    "parse_scheme_config",
    "SchemeConfig",
    "SchemeConfigError",
    "Group",
    "GroupFile",
    "ContentRule",
    "CONFIG_NAME",
    "FS_LOG",
    "write_fs_log",
    "load_webhook_config",
    "send_webhook",
]
