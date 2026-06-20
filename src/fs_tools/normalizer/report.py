"""Формирование текста отчёта и итоговой сводки нормализатора."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import FsNormalizer


def format_report(root: Path, result: FsNormalizer, renamed: int, skipped: int) -> str:
    """Заголовок с каталогом и итог прогона нормализации."""
    lines = [f"Каталог: {root}"]
    lines.append(
        f"Готово. Переименовано: {renamed}, пропущено: {skipped} "
        f"(конфликты: {result.conflicts}, ошибки: {len(result.errlist)})."
    )
    return "\n".join(lines)
