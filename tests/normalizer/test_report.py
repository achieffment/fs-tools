"""Тесты форматирования отчёта normalizer (report.format_report)."""
from pathlib import Path

from fs_tools.normalizer.report import format_report


class _Result:
    """Минимальный объект результата для проверки форматирования отчёта."""

    def __init__(self, conflicts: int, errlist_len: int) -> None:
        """Сохраняет количество конфликтов и имитирует список ошибок."""
        self.conflicts = conflicts
        self.errlist = [("src", "dst")] * errlist_len


def test_format_report_ok() -> None:
    """Проверяет формат отчёта без конфликтов и ошибок."""
    root = Path("/tmp/demo")
    result = _Result(conflicts=0, errlist_len=0)
    text = format_report(root, result, renamed=3, skipped=1)
    assert "Каталог: /tmp/demo" in text
    assert "Режим: боевой" in text
    assert "Готово. Переименовано: 3, пропущено: 1 (конфликты: 0, ошибки: 0)." in text


def test_format_report_with_errors() -> None:
    """Проверяет формат отчёта с конфликтами и ошибками."""
    root = Path("/tmp/demo")
    result = _Result(conflicts=2, errlist_len=4)
    text = format_report(root, result, renamed=5, skipped=6)
    assert "Каталог: /tmp/demo" in text
    assert "Режим: боевой" in text
    assert "Готово. Переименовано: 5, пропущено: 6 (конфликты: 2, ошибки: 4)." in text


def test_format_report_dry_run() -> None:
    """Проверяет формат отчёта в dry-run."""
    root = Path("/tmp/demo")
    result = _Result(conflicts=1, errlist_len=0)
    text = format_report(root, result, renamed=2, skipped=1, dry_run=True)
    assert "Каталог: /tmp/demo" in text
    assert "Режим: dry-run (без изменений)" in text
    assert "Готово. Переименовано: 2, пропущено: 1 (конфликты: 1, ошибки: 0)." in text
