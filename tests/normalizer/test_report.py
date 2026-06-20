"""Тесты форматирования отчёта normalizer (report.format_report)."""
from pathlib import Path

from fs_tools.normalizer.report import format_report


class _Result:
    def __init__(self, conflicts: int, errlist_len: int) -> None:
        self.conflicts = conflicts
        self.errlist = [("src", "dst")] * errlist_len


def test_format_report_ok() -> None:
    root = Path("/tmp/demo")
    result = _Result(conflicts=0, errlist_len=0)
    text = format_report(root, result, renamed=3, skipped=1)
    assert "Каталог: /tmp/demo" in text
    assert "Готово. Переименовано: 3, пропущено: 1 (конфликты: 0, ошибки: 0)." in text


def test_format_report_with_errors() -> None:
    root = Path("/tmp/demo")
    result = _Result(conflicts=2, errlist_len=4)
    text = format_report(root, result, renamed=5, skipped=6)
    assert "Каталог: /tmp/demo" in text
    assert "Готово. Переименовано: 5, пропущено: 6 (конфликты: 2, ошибки: 4)." in text
