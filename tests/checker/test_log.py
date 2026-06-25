"""Мод-специфичные строки журнала проверки: пути и пометка «(нарушений нет)»."""
from datetime import datetime
from pathlib import Path

from fs_tools.checker import FS_LOG, write_fs_log


def test_write_fs_log_lists_missing_paths(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log lists missing paths."""
    when = datetime(2026, 6, 14, 9, 0, 0)
    lpath = write_fs_log(tmp_path, ["Activities/Web/Projects"], when=when)
    assert lpath == tmp_path / FS_LOG
    text = lpath.read_text(encoding="utf-8")
    assert "Режим: production" in text
    assert "  Activities/Web/Projects" in text


def test_write_fs_log_empty_marks_no_violations(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log empty marks no violations."""
    text = write_fs_log(tmp_path, [], when=datetime(2026, 6, 14, 9, 5, 0)).read_text(
        encoding="utf-8"
    )
    assert "Режим: production" in text
    assert "(нарушений нет)" in text
