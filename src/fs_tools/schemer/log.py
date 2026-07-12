"""Журнал проверки .fs-log: дата, режим + список нарушений.

Формат — общий `shared.log`; различие лишь в содержимом строк (нарушения) и тексте
пустого блока (`(нарушений нет)`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    violations: list[str],
    tool: str = "schemer",
    mode: str = "production",
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: дата, режим + список нарушений.

    Пустой список фиксируется пометкой «(нарушений нет)». Параметр `when` нужен для
    тестов; по умолчанию берётся текущее локальное время.
    """
    return append_log(root, violations, "(нарушений нет)", meta=(tool, mode), when=when)
