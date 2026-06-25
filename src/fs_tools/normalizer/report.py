"""Формирование текста отчёта и итоговой сводки нормализатора."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import FsNormalizer


def format_report(
    root: Path, result: FsNormalizer, renamed: int, skipped: int, *, dry_run: bool = False
) -> str:
    """Заголовок с каталогом и итог прогона нормализации."""
    lines = [f"Каталог: {root}"]
    mode = "dry-run" if dry_run else "production"
    lines.append(f"Режим: {mode}")
    errcnt = len(result.errlist)
    if errcnt:
        status = "error. Нормализация завершена с ошибками."
    elif result.conflicts:
        status = "warn. Нормализация завершена с конфликтами."
    else:
        status = "ok. Нормализация завершена успешно."
    lines.append(f"Статус: {status}")
    lines.append(
        f"Сводка: переименовано: {renamed}; пропущено: {skipped}; "
        f"конфликты: {result.conflicts}; ошибки: {errcnt}."
    )
    return "\n".join(lines)
