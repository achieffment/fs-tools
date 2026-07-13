"""Формирование текста отчёта, строк журнала и итоговой сводки."""
from __future__ import annotations

from pathlib import Path

from .engine import SchemerResult, Violation

_KIND_TEXT = {
    "missing_group_file": "отсутствует обязательный файл",
    "empty_group": "пустая группа",
    "loose_file": "файл вне групповой папки",
    "missing_line": "файл короче ожидаемой строки",
    "bad_header": "заголовок не совпадает",
    "read_error": "не удалось прочитать файл",
}


def format_violation(vio: Violation) -> str:
    """Одна строка нарушения: тип, путь и (для контентных/технических) детали.

    `read_error` помечается префиксом `(ОШИБКА)` — симметрично `normalizer`/`syncher`,
    где та же пометка отделяет реальный сбой от штатного результата проверки.
    """
    text = f"{_KIND_TEXT[vio.kind]}: {vio.path}"
    if vio.kind == "missing_line":
        text = f"{text} (ожидается строка с текстом «{vio.expected}»)"
    elif vio.kind == "bad_header":
        text = f"{text} (ожидается «{vio.expected}», факт «{vio.actual}»)"
    elif vio.kind == "read_error":
        text = f"(ОШИБКА) {text} ({vio.actual})"
    return text


def format_report(root: Path, result: SchemerResult) -> str:
    """Заголовок с каталогом, статус и сводка. Список нарушений — только в `.fs-log.log`."""
    status = (
        "error. Найдены нарушения структуры/контента."
        if result.violations
        else "ok. Нарушений нет."
    )
    return "\n".join(
        [
            f"Каталог: {root}",
            f"Статус: {status}",
            f"Сводка: проверено групп: {result.groups_checked}; "
            f"проверено файлов: {result.files_checked}; "
            f"нарушений: {len(result.violations)}.",
        ]
    )
