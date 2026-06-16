"""Формирование текста отчёта и итоговой сводки."""
from __future__ import annotations

from pathlib import Path

from .engine import CheckResult


def format_report(root: Path, result: CheckResult) -> str:
    """Заголовок с каталогом, список отсутствующих путей (или «всё на месте») и сводка.

    Термин «пути», т.к. мандатом может быть и папка, и файл. Список уже отсортирован
    и дедуплицирован движком.
    """
    lines = [f"Каталог: {root}"]
    if result.missing:
        lines.append(f"Отсутствуют пути ({len(result.missing)}):")
        lines += [f"  {path}" for path in result.missing]
    else:
        lines.append("Все требуемые пути на месте.")
    lines.append(
        f"Проверено правил: {result.rules_checked}. "
        f"Найдено каталогов-кандидатов: {result.anchors_found}. "
        f"Отсутствует: {len(result.missing)}."
    )
    return "\n".join(lines)
