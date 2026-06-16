"""Журнал синхронизации .fs-log: дата + список выполненных операций.

Общий для серии fs-* формат блока: строка-метка времени, затем строки операций с
отступом в 2 пробела и пустая строка-разделитель между блоками прогонов. Несколько
утилит над одним каталогом дополняют один и тот же файл .fs-log.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

FS_LOG = ".fs-log"


def write_fs_log(
    root: Path,
    operations: list[str],
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: заголовок-дата + список операций.

    Создаёт файл, если его нет; иначе дополняет (append). В лог попадают ТОЛЬКО
    фактически выполненные операции (не план dry-run); каждая строка уже содержит
    маркер: `+ <путь>` — отправлено/обновлено, `- <путь>` — удалено на сервере,
    `>> <путь>` — выгружено и удалено/архивировано локально. Пустой список
    фиксируется пометкой «(изменений нет)». Параметр `when` нужен для тестов; по
    умолчанию берётся текущее локальное время. Возвращает путь к журналу.
    """
    stamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    lines = [stamp]
    if operations:
        lines += [f"  {op}" for op in operations]
    else:
        lines.append("  (изменений нет)")
    block = "\n".join(lines) + "\n\n"           # пустая строка отделяет блоки прогонов
    lpath = root / FS_LOG
    with lpath.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return lpath
