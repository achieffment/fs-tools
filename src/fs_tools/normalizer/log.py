"""Журнал переименований .fs-log: дата + список выполненных переименований.

Формат — общий `shared.log`; различие лишь в содержимом строк (пары `old -> new`)
и тексте пустого блока (`(изменений нет)`). В dry-run запись журнала отключает runner.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    renames: list[tuple[Path, Path]],
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: заголовок-дата + список переименований.

    В лог попадают ТОЛЬКО выполненные переименования — ошибки и конфликты сюда не
    пишутся. Пустой список фиксируется пометкой «(изменений нет)». Параметр `when`
    нужен для тестов; по умолчанию берётся текущее локальное время.
    """
    lines = [f"{src.as_posix()} -> {dest.as_posix()}" for src, dest in renames]
    return append_log(root, lines, "(изменений нет)", when=when)
