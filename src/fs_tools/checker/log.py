"""Журнал проверки .fs-log: дата, режим + список отсутствующих путей.

Формат — общий `shared.log`; различие лишь в содержимом строк (отсутствующие пути)
и тексте пустого блока (`(нарушений нет)`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    missing: list[str],
    tool: str = "checker",
    mode: str = "production",
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: дата, режим + список отсутствующих путей.

    Пустой список фиксируется пометкой «(нарушений нет)» (runner вызывает только при
    наличии нарушений; пометка — для прямого использования API). Параметр `when` нужен
    для тестов; по умолчанию берётся текущее локальное время.
    """
    return append_log(root, missing, "(нарушений нет)", meta=(tool, mode), when=when)
