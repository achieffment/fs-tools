"""Тесты журнала .fs-log.log нормализатора (write_fs_log + сбор renames в FsNormalizer).

Общие механики журнала — в tests/shared/test_log.py. Фикстура `make_tree` — в conftest.py.
"""
import os
from datetime import datetime
from pathlib import Path

from fs_tools.normalizer import FS_LOG, FsNormalizer, build_normalizer, write_fs_log

from .conftest import DEMO_TREE


def test_write_fs_log_creates_file(tmp_path):
    """Проверяет сценарий: write fs log creates file."""
    when = datetime(2026, 6, 11, 13, 39, 0)
    renames = [(Path("Отчёт за март"), Path("Otchiot-za-mart"))]
    lpath = write_fs_log(tmp_path, renames, when=when)
    assert lpath == tmp_path / FS_LOG
    text = lpath.read_text(encoding="utf-8")
    assert "2026-06-11 13:39:00" in text
    assert "Инструмент: normalizer" in text
    assert "Режим: production" in text
    assert "Результат:" in text
    assert "  Отчёт за март -> Otchiot-za-mart" in text


def test_write_fs_log_empty_marks_no_changes(tmp_path):
    """Проверяет сценарий: write fs log empty marks no changes."""
    when = datetime(2026, 6, 11, 14, 2, 11)
    lpath = write_fs_log(tmp_path, [], when=when)
    text = lpath.read_text(encoding="utf-8")
    assert "2026-06-11 14:02:11" in text
    assert "Инструмент: normalizer" in text
    assert "Режим: production" in text
    assert "Результат:" in text
    assert "(изменений нет)" in text


def test_write_fs_log_appends(tmp_path):
    """Проверяет сценарий: write fs log appends."""
    write_fs_log(tmp_path, [(Path("a"), Path("b"))], when=datetime(2026, 6, 11, 13, 0, 0))
    lpath = write_fs_log(tmp_path, [], when=datetime(2026, 6, 11, 14, 0, 0))
    text = lpath.read_text(encoding="utf-8")
    # Оба блока сохранены (дополнение, а не перезапись):
    assert "2026-06-11 13:00:00" in text
    assert "  a -> b" in text
    assert "2026-06-11 14:00:00" in text
    assert "(изменений нет)" in text


def test_write_fs_log_dry_run_mode(tmp_path):
    """Проверяет сценарий: write fs log dry run mode."""
    lpath = write_fs_log(
        tmp_path,
        [(Path("x"), Path("y"))],
        mode="dry-run",
        when=datetime(2026, 6, 11, 15, 0, 0),
    )
    text = lpath.read_text(encoding="utf-8")
    assert "Инструмент: normalizer" in text
    assert "Режим: dry-run" in text
    assert "Результат:" in text


def test_fs_renames_collected(make_tree):
    """Проверяет сценарий: fs renames collected."""
    root = make_tree(DEMO_TREE)
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(root)
    pairs = {(src.as_posix(), dest.as_posix()) for src, dest in fsnm.renames}
    assert ("1_file.TXT", "01_file.TXT") in pairs
    assert ("v2 readme.MD", "v2-readme.MD") in pairs
    # Дочерний объект записан раньше родителя (deepest-first), путь — относительный.
    assert ("Отчёт 2020/20.05.2020_dump", "Отчёт 2020/2020-05-20_dump") in pairs
    # Скрытые в журнал не попадают:
    assert all(".git" not in src.as_posix() for src, _ in fsnm.renames)
    assert all(not src.as_posix().startswith(".env") for src, _ in fsnm.renames)


def test_fs_renames_reset_on_second_run(make_tree):
    """Проверяет сценарий: fs renames reset on second run."""
    root = make_tree(DEMO_TREE)
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(root)
    assert fsnm.renames  # первый прогон что-то переименовал
    fsnm.apply(root)
    # На нормализованном дереве переименований нет — список сброшен.
    assert not fsnm.renames

def test_fs_conflict_is_logged(tmp_path):
    """Проверяет сценарий: fs conflict is logged."""
    (tmp_path / "a b.md").write_text("a")  # -> "a-b.md"
    (tmp_path / "a-b.md").write_text("b")  # уже занято
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(tmp_path)
    assert fsnm.actions == ["(КОНФЛИКТ) a b.md -> a-b.md"]
    assert not fsnm.renames


def test_fs_log_keeps_success_conflict_error_order(tmp_path, monkeypatch):
    """Проверяет сценарий: fs log keeps success conflict error order."""
    (tmp_path / "Отчёт.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "a b.md").write_text("conflict", encoding="utf-8")
    (tmp_path / "a-b.md").write_text("taken", encoding="utf-8")
    (tmp_path / "Плохой.doc").write_text("err", encoding="utf-8")
    fsnm = FsNormalizer(build_normalizer())
    ordered = [
        tmp_path / "Отчёт.txt",
        tmp_path / "a b.md",
        tmp_path / "Плохой.doc",
    ]
    monkeypatch.setattr(FsNormalizer, "_collect", lambda _self, _root: ordered)
    base_rename = os.rename

    def rename_with_error(src: Path, dst: Path) -> None:
        if src.name == "Плохой.doc":
            raise OSError("rename failed")
        base_rename(src, dst)

    monkeypatch.setattr(os, "rename", rename_with_error)
    fsnm.apply(tmp_path)
    lpath = write_fs_log(
        tmp_path,
        fsnm.actions,
        mode="production",
        when=datetime(2026, 6, 11, 16, 0, 0),
    )
    text = lpath.read_text(encoding="utf-8")
    s_ix = text.index("  Отчёт.txt -> otchiot.txt")
    c_ix = text.index("  (КОНФЛИКТ) a b.md -> a-b.md")
    e_ix = text.index("  (ОШИБКА) Плохой.doc -> plokhoi.doc: rename failed")
    assert s_ix < c_ix < e_ix


def test_fs_log_file_itself_not_normalized(tmp_path):
    # .fs-log.log скрыт (на '.') — обходом пропускается, не переименовывается.
    """Проверяет сценарий: fs log file itself not normalized."""
    (tmp_path / FS_LOG).write_text("2026-06-11 13:00:00\n  (изменений нет)\n\n")
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(tmp_path)
    assert (tmp_path / FS_LOG).is_file()
    assert all(FS_LOG not in src.as_posix() for src, _ in fsnm.renames)
