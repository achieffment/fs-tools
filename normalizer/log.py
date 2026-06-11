"""Журнал переименований .fs-log: дата + список выполненных переименований."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

FS_LOG = ".fs-log"


def write_fs_log(
    root: Path,
    renames: list[tuple[Path, Path]],
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: заголовок-дата + список переименований.

    Создаёт файл, если его нет; иначе дополняет (append). В лог попадают ТОЛЬКО
    выполненные переименования — ошибки и конфликты сюда не пишутся. Пустой список
    фиксируется пометкой «(изменений нет)». Параметр `when` нужен для тестов;
    по умолчанию берётся текущее локальное время. Возвращает путь к журналу.
    """
    stamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    lines = [stamp]
    if renames:
        lines += [f"  {src.as_posix()} -> {dest.as_posix()}" for src, dest in renames]
    else:
        lines.append("  (изменений нет)")
    block = "\n".join(lines) + "\n\n"           # пустая строка отделяет блоки прогонов
    lpath = root / FS_LOG
    with lpath.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return lpath
