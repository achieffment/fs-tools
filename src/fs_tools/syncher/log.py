"""Журнал синхронизации .fs-log: дата, режим + список результатов.

Формат — общий `shared.log`; различие лишь в содержимом строк (операции и
диагностические строки `(КОНФЛИКТ)`/`(ОШИБКА)`) и тексте пустого блока
(`(изменений нет)`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    actions: list[str],
    tool: str = "syncher",
    mode: str = "production",
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: дата, режим + список результатов.

    В лог попадают строки операций (`+`/`-`/`>>`) и диагностические строки
    `(КОНФЛИКТ)`/`(ОШИБКА)` в уже подготовленном порядке.
    Пустой список фиксируется пометкой «(изменений нет)». Параметр `when` нужен для
    тестов; по умолчанию берётся текущее локальное время.
    """
    return append_log(root, actions, "(изменений нет)", meta=(tool, mode), when=when)
