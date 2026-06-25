"""Журнал normalizer .fs-log: дата, режим + список результатов.

Формат — общий `shared.log`; различие лишь в содержимом строк (пары `old -> new`
и диагностические строки `(КОНФЛИКТ)`/`(ОШИБКА)`) и тексте пустого блока
(`(изменений нет)`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    result: list[str] | list[tuple[Path, Path]],
    tool: str = "normalizer",
    mode: str = "production",
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: дата, режим + список результатов.

    `result` принимает либо готовые строковые события, либо legacy-пары
    переименований `(src, dst)`, которые переводятся в строку `src -> dst`.
    Пустой список фиксируется пометкой «(изменений нет)». Параметр `when` нужен для
    тестов; по умолчанию берётся текущее локальное время.
    """
    lines: list[str] = []
    for item in result:
        if isinstance(item, tuple):
            src, dest = item
            lines.append(f"{src.as_posix()} -> {dest.as_posix()}")
        else:
            lines.append(item)
    return append_log(root, lines, "(изменений нет)", meta=(tool, mode), when=when)
