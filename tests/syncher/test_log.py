"""Мод-специфичные строки журнала синхронизации: маркеры `+`/`-`/`>>` и «(изменений нет)».

Общие механики формата (метка времени, отступ, append, utf-8) проверяются в
`tests/shared/test_log.py`; здесь — только специфика режима.
"""
from datetime import datetime
from pathlib import Path

from fs_tools.syncher import FS_LOG, write_fs_log


def test_write_fs_log_marks_actions(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log marks actions."""
    when = datetime(2026, 6, 16, 9, 0, 0)
    lpath = write_fs_log(tmp_path, ["+ a.txt", "- old.txt", ">> x.bin"], when=when)
    assert lpath == tmp_path / FS_LOG
    text = lpath.read_text(encoding="utf-8")
    assert "Режим: production" in text
    assert "  + a.txt" in text
    assert "  - old.txt" in text
    assert "  >> x.bin" in text


def test_write_fs_log_empty_marks_no_changes(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log empty marks no changes."""
    text = write_fs_log(tmp_path, [], when=datetime(2026, 6, 16, 9, 5, 0)).read_text(
        encoding="utf-8"
    )
    assert "Режим: production" in text
    assert "(изменений нет)" in text


def test_write_fs_log_dry_run_mode(tmp_path: Path) -> None:
    """Проверяет сценарий: write fs log dry run mode."""
    text = write_fs_log(
        tmp_path,
        ["+ planned.txt"],
        mode="dry-run",
        when=datetime(2026, 6, 16, 9, 10, 0),
    ).read_text(encoding="utf-8")
    assert "Режим: dry-run" in text
