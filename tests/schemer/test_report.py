"""Тесты формата отчёта (report): статус, сводка и строки нарушений."""
from pathlib import Path

from fs_tools.schemer import SchemerResult, Violation, format_report, format_violation


def test_format_violation_missing_group_file() -> None:
    """missing_group_file форматируется без ожидания/факта."""
    text = format_violation(Violation(path="T/_Knowledges/_main.md", kind="missing_group_file"))
    assert text == "отсутствует обязательный файл: T/_Knowledges/_main.md"


def test_format_violation_bad_header() -> None:
    """bad_header включает ожидание и факт."""
    vio = Violation(
        path="T/_Knowledges/_main.md", kind="bad_header", expected="# Заметки", actual="# Х"
    )
    text = format_violation(vio)
    expected = "заголовок не совпадает: T/_Knowledges/_main.md (ожидается «# Заметки», факт «# Х»)"
    assert text == expected


def test_format_violation_missing_line() -> None:
    """missing_line включает только ожидание."""
    vio = Violation(path="a.md", kind="missing_line", expected="## Правила")
    assert "ожидается строка с текстом «## Правила»" in format_violation(vio)


def test_format_violation_read_error() -> None:
    """read_error помечается (ОШИБКА) и включает текст исключения."""
    vio = Violation(path="a.md", kind="read_error", actual="[Errno 13] Permission denied")
    text = format_violation(vio)
    expected = "(ОШИБКА) не удалось прочитать файл: a.md ([Errno 13] Permission denied)"
    assert text == expected


def test_format_report_ok_status(tmp_path: Path) -> None:
    """Без нарушений — статус ok и без блока «Нарушения»."""
    result = SchemerResult(violations=[], groups_checked=1, files_checked=1)
    text = format_report(tmp_path, result)
    assert "Статус: ok. Нарушений нет." in text
    assert "Нарушения" not in text
    assert "Сводка: проверено групп: 1; проверено файлов: 1; нарушений: 0." in text


def test_format_report_error_status_no_item_list(tmp_path: Path) -> None:
    """С нарушениями — только статус error и сводка; список — задача `.fs-log.log`."""
    result = SchemerResult(
        violations=[Violation(path="Topic/_Resources", kind="empty_group")],
        groups_checked=1,
        files_checked=0,
    )
    text = format_report(tmp_path, result)
    assert "Нарушения" not in text
    assert "Topic/_Resources" not in text
    assert "Статус: error. Найдены нарушения структуры/контента." in text
    assert "Сводка: проверено групп: 1; проверено файлов: 0; нарушений: 1." in text
