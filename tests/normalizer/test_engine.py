"""E2e-тесты обхода и переименования (engine.py, FsNormalizer) на временной папке.

Фикстура дерева `make_tree` — в conftest.py.
"""
import os
from pathlib import Path

import pytest

from fs_tools.normalizer import FsNormalizer, build_normalizer

from .conftest import DEMO_TREE


def test_fs_end_to_end(make_tree):
    """Проверяет сценарий: fs end to end."""
    root = make_tree(DEMO_TREE)
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(root)

    assert (root / "Otchiot_2020-00-00").is_dir()
    assert (root / "Otchiot_2020-00-00" / "2020-05-20_dump").exists()
    assert (root / "01_file.TXT").exists()
    assert (root / "v2-readme.MD").exists()
    # Скрытые не тронуты:
    assert (root / ".git").is_dir()
    assert (root / ".git" / "CONFIG").exists()
    assert (root / ".env").exists()


def test_fs_idempotent_second_run_empty(make_tree):
    """Проверяет сценарий: fs idempotent second run empty."""
    root = make_tree(DEMO_TREE)
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(root)
    renamed, _skipped = fsnm.apply(root)
    assert renamed == 0


def test_fs_conflict_skipped(tmp_path):
    """Проверяет сценарий: fs conflict skipped."""
    (tmp_path / "a b.md").write_text("a")  # -> "a-b.md"
    (tmp_path / "a-b.md").write_text("b")  # уже "a-b.md"
    fsnm = FsNormalizer(build_normalizer())
    renamed, skipped = fsnm.apply(tmp_path)
    # Переименование в уже занятое имя пропускается, оба файла сохраняются.
    assert renamed == 0
    assert skipped >= 1
    # Конфликт — безопасный пропуск: учитывается в conflicts, но НЕ в errlist.
    assert fsnm.conflicts >= 1
    assert not fsnm.errlist
    assert (tmp_path / "a b.md").exists()
    assert (tmp_path / "a-b.md").exists()


def test_fs_oserror_recorded_in_errlist(tmp_path, monkeypatch):
    # Реальный сбой os.rename (OSError, напр. зарезервированное имя/длина пути на
    # Windows) безопасно пропускается: данные сохраняются, но фиксируется в errlist.
    """Проверяет сценарий: fs oserror recorded in errlist."""
    (tmp_path / "Отчёт.txt").write_text("ДАННЫЕ")  # -> "otchiot.txt"

    real_rename = os.rename

    def failing_rename(src, dst, *args, **kwargs):
        """Выполняет шаг: failing rename."""
        if Path(dst).name == "otchiot.txt":
            raise OSError("симулированный сбой переименования")
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr("fs_tools.normalizer.engine.os.rename", failing_rename)
    fsnm = FsNormalizer(build_normalizer())
    renamed, skipped = fsnm.apply(tmp_path)
    assert renamed == 0
    assert skipped >= 1
    assert len(fsnm.errlist) == 1
    src_rel, dest_rel = fsnm.errlist[0]
    assert (src_rel.as_posix(), dest_rel.as_posix()) == ("Отчёт.txt", "otchiot.txt")
    assert fsnm.conflicts == 0
    # Исходный файл уцелел вместе с данными.
    assert (tmp_path / "Отчёт.txt").read_text() == "ДАННЫЕ"


def test_fs_no_relocation_via_separator(tmp_path):
    # Регресс на критический баг: имя с дробью раньше давало '10-1/2.dat' и os.rename
    # МОЛЧА перемещал файл в соседний каталог '10-1'. Теперь имя остаётся одним
    # компонентом пути, файл нормализуется на месте, ничего не теряется.
    """Проверяет сценарий: fs no relocation via separator."""
    secret = tmp_path / "10½.dat"
    secret.write_text("СЕКРЕТ")
    sibling = tmp_path / "10-1"
    sibling.mkdir()
    (sibling / "keep.txt").write_text("сосед")
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(tmp_path)
    # Данные остались прямо в корне (не уехали внутрь соседнего каталога):
    survivors = [p for p in tmp_path.iterdir() if p.is_file() and p.read_text() == "СЕКРЕТ"]
    assert len(survivors) == 1
    assert "/" not in survivors[0].name and "\\" not in survivors[0].name
    assert (tmp_path / "10½.dat").exists() is False  # переименован


def test_fs_guillemets_renamed_no_data_loss(tmp_path):
    # Регресс на WinError 123: имя с кавычками-«ёлочками» давало '<<'/'>>' через
    # unidecode, и одиночный '<' в середине ломал переименование на Windows.
    # Теперь запрещённые символы вырезаются, файл нормализуется на месте.
    """Проверяет сценарий: fs guillemets renamed no data loss."""
    doc = tmp_path / "Заявление ООО «Печоралифтсервис».docx"
    doc.write_text("ДАННЫЕ")
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(tmp_path)
    survivors = [p for p in tmp_path.iterdir() if p.is_file() and p.read_text() == "ДАННЫЕ"]
    assert len(survivors) == 1
    name = survivors[0].name
    assert not any(ch in name for ch in "<>:\"|?*")
    assert name == "zaiavlenie-ooo-pechoraliftservis.docx"
    assert doc.exists() is False  # переименован


def test_fs_case_collision_no_data_loss(tmp_path):
    # Регистрозависимая ФС: "File.md" нормализуется в "file.md", где уже есть
    # другой файл. Это конфликт — переименование должно пропускаться, а не
    # перезатирать существующий файл.
    """Проверяет сценарий: fs case collision no data loss."""
    (tmp_path / "File.md").write_text("upper")
    (tmp_path / "file.md").write_text("lower")
    if len(list(tmp_path.iterdir())) < 2:
        pytest.skip("регистронезависимая ФС: файлы-двойники не сосуществуют")
    fsnm = FsNormalizer(build_normalizer())
    renamed, skipped = fsnm.apply(tmp_path)
    assert renamed == 0
    assert skipped >= 1
    assert (tmp_path / "File.md").read_text() == "upper"
    assert (tmp_path / "file.md").read_text() == "lower"
