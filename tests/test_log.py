"""Тесты журнала .fs-log: создание, дополнение, формат, пометка «изменений нет»."""
from datetime import datetime
from pathlib import Path

from syncher import FS_LOG, write_fs_log


def test_write_creates_file(tmp_path: Path) -> None:
    when = datetime(2026, 6, 16, 9, 0, 0)
    lpath = write_fs_log(tmp_path, ["+ a.txt", "- old.txt"], when=when)
    assert lpath == tmp_path / FS_LOG
    text = lpath.read_text(encoding="utf-8")
    assert "2026-06-16 09:00:00" in text
    assert "  + a.txt" in text
    assert "  - old.txt" in text


def test_write_empty_marks_no_changes(tmp_path: Path) -> None:
    when = datetime(2026, 6, 16, 9, 5, 0)
    lpath = write_fs_log(tmp_path, [], when=when)
    text = lpath.read_text(encoding="utf-8")
    assert "(изменений нет)" in text


def test_write_appends(tmp_path: Path) -> None:
    write_fs_log(tmp_path, ["+ a"], when=datetime(2026, 6, 16, 9, 0, 0))
    lpath = write_fs_log(tmp_path, [">> b"], when=datetime(2026, 6, 16, 10, 0, 0))
    text = lpath.read_text(encoding="utf-8")
    assert "2026-06-16 09:00:00" in text and "2026-06-16 10:00:00" in text
    assert "  + a" in text and "  >> b" in text
    assert text.endswith("\n\n")                 # блоки разделены пустой строкой
