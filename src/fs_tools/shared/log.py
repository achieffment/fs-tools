"""Общий append-журнал `.fs-log.log`: дата, инструмент, режим и строки.

Формат один на все режимы: метка времени `YYYY-MM-DD HH:MM:SS`, строки
`Инструмент: ...` и `Режим: ...`, строки тела с отступом, пустая строка-разделитель
между прогонами, кодировка `utf-8`. Перед телом ставится заголовок `Результат:`.
Содержимое строк и текст пустого блока —
параметры (`lines` / `empty_marker`), поэтому над одним каталогом любой режим
дополняет один и тот же файл без копий модуля.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

FS_LOG = ".fs-log.log"


def append_log(
    root: Path,
    lines: list[str],
    empty_marker: str,
    meta: tuple[str, str] = ("unknown", "production"),
    when: datetime | None = None,
) -> Path:
    """Дописать в root/.fs-log.log блок прогона: дата, инструмент, режим и строки.

    Создаёт файл, если его нет; иначе дополняет (append). Каждая строка `lines`
    пишется с отступом; пустой список фиксируется пометкой `empty_marker`. Параметр
    `when` нужен для тестов; по умолчанию берётся текущее локальное время. Возвращает
    путь к журналу.
    """
    tool, mode = meta
    date = (when or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    body = [date, f"Инструмент: {tool}", f"Режим: {mode}", "Результат:"]
    if lines:
        body = body + [f"  {line}" for line in lines]
    else:
        body.append(f"  {empty_marker}")
    block = "\n".join(body) + "\n\n"           # пустая строка отделяет блоки прогонов
    lpath = root / FS_LOG
    with lpath.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return lpath
