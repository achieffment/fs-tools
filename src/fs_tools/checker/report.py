"""Формирование текста отчёта и итоговой сводки."""
from __future__ import annotations

from pathlib import Path

from .engine import CheckResult


def format_report(root: Path, result: CheckResult) -> str:
    """Заголовок с каталогом, список отсутствующих путей/ошибок чтения и сводка.

    Термин «пути», т.к. мандатом может быть и папка, и файл. Списки уже отсортированы
    и дедуплицированы движком. `errlist` — сбои сканирования каталогов (`OSError`),
    отдельная категория от отсутствующих путей; помечается `(ОШИБКА)`, как у
    `normalizer`/`syncher`, и приоритетнее `missing` в статусе, т.к. означает
    потенциально неполный обход.
    """
    lines = [f"Каталог: {root}"]
    if result.errlist:
        lines.append(f"Ошибки чтения ({len(result.errlist)}):")
        lines = lines + [f"  (ОШИБКА) {entry}" for entry in result.errlist]
    if result.missing:
        lines.append(f"Отсутствуют пути ({len(result.missing)}):")
        lines = lines + [f"  {path}" for path in result.missing]
    if result.errlist:
        status = "error. Не удалось просканировать часть каталогов."
    elif result.missing:
        status = "warn. Найдены отсутствующие пути."
    else:
        status = "ok. Все требуемые пути на месте."
    lines.append(f"Статус: {status}")
    lines.append(
        f"Сводка: проверено правил: {result.rules_checked}; "
        f"найдено каталогов-кандидатов: {result.anchors_found}; "
        f"отсутствует: {len(result.missing)}; "
        f"ошибок чтения: {len(result.errlist)}."
    )
    return "\n".join(lines)
