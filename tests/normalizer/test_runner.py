"""CLI main(): коды возврата (0 — успех, 1 — ошибка запуска, 2 — сбои os.rename)."""
import os
from pathlib import Path

import pytest

from fs_tools.normalizer import main


def test_main_clean_run_returns_zero(tmp_path, monkeypatch, capsys):
    """Проверяет сценарий: main clean run returns zero."""
    (tmp_path / "Отчёт.txt").write_text("x")
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(tmp_path))
    assert main([]) == 0
    out = capsys.readouterr().out
    assert f"Каталог: {tmp_path}" in out
    assert "Режим: production" in out
    assert "Статус: ok. Нормализация завершена успешно." in out
    assert "Сводка: переименовано: 1; пропущено: 0; конфликты: 0; ошибки: 0." in out
    assert (tmp_path / "otchiot.txt").exists()
    log = (tmp_path / ".fs-log").read_text(encoding="utf-8")
    assert "Инструмент: normalizer" in log
    assert "Режим: production" in log
    assert "Результат:" in log


def test_main_conflict_only_returns_zero(tmp_path, monkeypatch, capsys):
    # Конфликт — безопасный пропуск: код возврата остаётся 0.
    """Проверяет сценарий: main conflict only returns zero."""
    (tmp_path / "a b.md").write_text("a")  # -> "a-b.md"
    (tmp_path / "a-b.md").write_text("b")  # уже занято
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(tmp_path))
    assert main([]) == 0
    captured = capsys.readouterr()
    out = captured.out
    err = captured.err
    assert f"Каталог: {tmp_path}" in out
    assert "Режим: production" in out
    assert "Статус: warn. Нормализация завершена с конфликтами." in out
    assert "Сводка: переименовано: 0; пропущено: 1; конфликты: 1; ошибки: 0." in out
    assert err == ""


def test_main_rename_error_returns_two(tmp_path, monkeypatch, capsys):
    """Проверяет сценарий: main rename error returns two."""
    (tmp_path / "Отчёт.txt").write_text("ДАННЫЕ")  # -> "otchiot.txt"
    class _RenameProxy:
        """Прокси `os.rename` с управляемым сбоем для целевого имени."""

        def __call__(self, src, dst, *args, **kwargs):
            if Path(dst).name == "otchiot.txt":
                raise OSError("симулированный сбой переименования")
            return os.rename(src, dst, *args, **kwargs)

    monkeypatch.setattr("fs_tools.normalizer.engine.os.rename", _RenameProxy())
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(tmp_path))
    assert main([]) == 2
    assert capsys.readouterr().err == ""
    assert (tmp_path / "Отчёт.txt").read_text() == "ДАННЫЕ"  # данные уцелели


def test_main_no_directory_returns_one(monkeypatch):
    """Проверяет сценарий: main no directory returns one."""
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: "")
    assert main([]) == 1


def test_main_missing_directory_returns_one(tmp_path, monkeypatch):
    """Проверяет сценарий: main missing directory returns one."""
    missing = tmp_path / "нет-такого"
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(missing))
    assert main([]) == 1


@pytest.mark.skipif(os.name != "posix", reason="права файла проверяются только на POSIX")
def test_main_unreadable_fs_nrm_returns_one(tmp_path, monkeypatch, capsys):
    # .fs-nrm ЕСТЬ, но не удалось прочитать -> код 1, а не молчаливое отключение
    # фильтра и переименование того, что должно было остаться нетронутым.
    """Проверяет сценарий: main unreadable fs nrm returns one."""
    (tmp_path / "Отчёт.txt").write_text("x")
    ignore_file = tmp_path / ".fs-nrm"
    ignore_file.write_text("Отчёт*\n")
    ignore_file.chmod(0o000)
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(tmp_path))
    try:
        code = main([])
    finally:
        ignore_file.chmod(0o644)  # иначе tmp_path не сможет удалить дерево при уборке
    assert code == 1
    assert "Ошибка" in capsys.readouterr().err
    assert (tmp_path / "Отчёт.txt").exists()  # прогон остановлен ДО переименований


def test_argument_bypasses_picker(tmp_path, monkeypatch):
    # Аргумент-каталог минует диалог: pick_directory не вызывается.
    """Проверяет сценарий: argument bypasses picker."""
    (tmp_path / "Отчёт.txt").write_text("x")

    def _boom(*a, **k):
        """Вспомогательная функция для теста."""
        raise AssertionError("pick_directory не должен вызываться при аргументе-каталоге")

    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", _boom)
    assert main([str(tmp_path)]) == 0
    assert (tmp_path / "otchiot.txt").exists()


def test_main_dry_run_returns_zero_without_changes(tmp_path, monkeypatch, capsys):
    """Проверяет сценарий: main dry run returns zero without changes."""
    (tmp_path / "Отчёт.txt").write_text("x")
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(tmp_path))
    assert main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"Каталог: {tmp_path}" in out
    assert "Режим: dry-run" in out
    assert "Статус: ok. Нормализация завершена успешно." in out
    assert "Сводка: переименовано: 1; пропущено: 0; конфликты: 0; ошибки: 0." in out
    assert "Журнал:" in out
    assert (tmp_path / "Отчёт.txt").exists()
    assert (tmp_path / "otchiot.txt").exists() is False
    text = (tmp_path / ".fs-log").read_text(encoding="utf-8")
    assert "Инструмент: normalizer" in text
    assert "Режим: dry-run" in text
    assert "Результат:" in text
    assert "Отчёт.txt -> otchiot.txt" in text


def test_argument_with_dry_run_bypasses_picker(tmp_path, monkeypatch):
    """Проверяет сценарий: argument with dry run bypasses picker."""
    (tmp_path / "Отчёт.txt").write_text("x")

    def _boom(*a, **k):
        """Вспомогательная функция для теста."""
        raise AssertionError("pick_directory не должен вызываться при аргументе-каталоге")

    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", _boom)
    assert main([str(tmp_path), "--dry-run"]) == 0
    assert (tmp_path / "Отчёт.txt").exists()
    assert (tmp_path / "otchiot.txt").exists() is False
