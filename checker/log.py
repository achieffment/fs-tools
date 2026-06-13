"""Журнал проверки .fs-log: дата + список отсутствующих путей.

Формат блока совпадает с журналом fs-normalizer (метка времени + строки с
отступом + пустая строка-разделитель), чтобы при запуске из одного каталога обе
утилиты дописывали один и тот же файл как единая система.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

FS_LOG = ".fs-log"


def write_fs_log(
    root: Path,
    missing: list[str],
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log запись прогона: заголовок-дата + список отсутствующих путей.

    Создаёт файл, если его нет; иначе дополняет (append). Пустой список фиксируется
    пометкой «(нарушений нет)» (CLI вызывает только при наличии нарушений; пометка —
    для прямого использования API). Параметр `when` нужен для тестов; по умолчанию
    берётся текущее локальное время. Возвращает путь к журналу.
    """
    stamp = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    lines = [stamp]
    if missing:
        lines += [f"  {path}" for path in missing]
    else:
        lines.append("  (нарушений нет)")
    block = "\n".join(lines) + "\n\n"           # пустая строка отделяет блоки прогонов
    lpath = root / FS_LOG
    with lpath.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return lpath
