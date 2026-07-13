"""Журнал проверки .fs-log.log: дата, режим + строки тела прогона.

Формат — общий `shared.log`; различие лишь в содержимом строк (отсутствующие пути,
с `(ОШИБКА)`-пометкой для сбоев сканирования — см. `runner.py`) и тексте пустого
блока (`(нарушений нет)`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..shared.log import FS_LOG, append_log

__all__ = ["FS_LOG", "write_fs_log"]


def write_fs_log(
    root: Path,
    lines: list[str],
    tool: str = "checker",
    mode: str = "production",
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log.log запись прогона: дата, режим + строки тела.

    Пустой список фиксируется пометкой «(нарушений нет)» (runner вызывает только при
    наличии нарушений/ошибок; пометка — для прямого использования API). Параметр
    `when` нужен для тестов; по умолчанию берётся текущее локальное время.
    """
    return append_log(root, lines, "(нарушений нет)", meta=(tool, mode), when=when)
