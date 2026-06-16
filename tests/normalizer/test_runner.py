"""CLI main(): коды возврата (0 — успех, 1 — ошибка запуска, 2 — сбои os.rename)."""
import os
from pathlib import Path

from fs_tools.normalizer import main


def test_main_clean_run_returns_zero(tmp_path, monkeypatch):
    (tmp_path / "Отчёт.txt").write_text("x")
    monkeypatch.setattr("fs_tools.normalizer.runner.pick_directory", lambda *a, **k: str(tmp_path))
    assert main([]) == 0
    assert (tmp_path / "otchiot.txt").exists()


def test_main_conflict_only_returns_zero(tmp_path, monkeypatch):
    # Конфликт — безопасный пропуск: код возврата остаётся 0.
    (tmp_path / "a b.md").write_text("a")  # -> "a-b.md"
    (tmp_path / "a-b.md").write_text("b")  # уже занято
    monkeypatch.setattr("fs_tools.normalizer.runner.pick_directory", lambda *a, **k: str(tmp_path))
    assert main([]) == 0


def test_main_rename_error_returns_two(tmp_path, monkeypatch):
    (tmp_path / "Отчёт.txt").write_text("ДАННЫЕ")  # -> "otchiot.txt"
    real_rename = os.rename

    def failing_rename(src, dst, *args, **kwargs):
        if Path(dst).name == "otchiot.txt":
            raise OSError("симулированный сбой переименования")
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr("fs_tools.normalizer.filesystem.os.rename", failing_rename)
    monkeypatch.setattr("fs_tools.normalizer.runner.pick_directory", lambda *a, **k: str(tmp_path))
    assert main([]) == 2
    assert (tmp_path / "Отчёт.txt").read_text() == "ДАННЫЕ"  # данные уцелели


def test_main_no_directory_returns_one(monkeypatch):
    monkeypatch.setattr("fs_tools.normalizer.runner.pick_directory", lambda *a, **k: "")
    assert main([]) == 1


def test_main_missing_directory_returns_one(tmp_path, monkeypatch):
    missing = tmp_path / "нет-такого"
    monkeypatch.setattr("fs_tools.normalizer.runner.pick_directory", lambda *a, **k: str(missing))
    assert main([]) == 1


def test_argument_bypasses_picker(tmp_path, monkeypatch):
    # Аргумент-каталог (режим таймера) минует диалог: pick_directory не вызывается.
    (tmp_path / "Отчёт.txt").write_text("x")

    def _boom(*a, **k):
        raise AssertionError("pick_directory не должен вызываться при аргументе-каталоге")

    monkeypatch.setattr("fs_tools.normalizer.runner.pick_directory", _boom)
    assert main([str(tmp_path)]) == 0
    assert (tmp_path / "otchiot.txt").exists()
