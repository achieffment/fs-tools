"""Журнал синхронизации .fs-log: дата + список выполненных операций.

Формат — общий `shared.log`; различие лишь в содержимом строк (маркеры `+`/`-`/`>>`
из `report.ProfileReport.operations()`) и тексте пустого блока (`(изменений нет)`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    operations: list[str],
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: заголовок-дата + список операций.

    В лог попадают ТОЛЬКО фактически выполненные операции (не план dry-run); каждая
    строка уже содержит маркер: `+ <путь>` — отправлено/обновлено, `- <путь>` —
    удалено на сервере, `>> <путь>` — выгружено и удалено/архивировано локально.
    Пустой список фиксируется пометкой «(изменений нет)». Параметр `when` нужен для
    тестов; по умолчанию берётся текущее локальное время.
    """
    return append_log(root, operations, "(изменений нет)", when=when)
