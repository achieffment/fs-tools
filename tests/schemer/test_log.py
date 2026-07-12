"""Мод-специфичные строки журнала проверки схемы: нарушения и «(нарушений нет)»."""
from datetime import datetime
from pathlib import Path

from fs_tools.schemer import FS_LOG, write_fs_log


def test_write_fs_log_lists_violations(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log lists violations."""
    when = datetime(2026, 6, 14, 9, 0, 0)
    lpath = write_fs_log(tmp_path, ["пустая группа: Topic/_Resources"], when=when)
    assert lpath == tmp_path / FS_LOG
    text = lpath.read_text(encoding="utf-8")
    assert "Инструмент: schemer" in text
    assert "Режим: production" in text
    assert "Результат:" in text
    assert "  пустая группа: Topic/_Resources" in text


def test_write_fs_log_empty_marks_no_violations(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log empty marks no violations."""
    text = write_fs_log(tmp_path, [], when=datetime(2026, 6, 14, 9, 5, 0)).read_text(
        encoding="utf-8"
    )
    assert "Инструмент: schemer" in text
    assert "Режим: production" in text
    assert "Результат:" in text
    assert "(нарушений нет)" in text
