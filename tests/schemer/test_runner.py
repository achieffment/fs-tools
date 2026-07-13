"""Тесты CLI режима проверки схемы: коды возврата и сообщения (runner)."""
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from fs_tools.schemer import FS_LOG, runner

_CONFIG = '[[group]]\nname = "_Resources"\n'


def _run(monkeypatch: pytest.MonkeyPatch, target: str) -> int:
    """Вспомогательная функция для теста."""
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: target)
    # По умолчанию глушим веб-хук, чтобы тесты не уходили в сеть.
    monkeypatch.setattr(runner, "send_webhook", lambda text: True)
    return runner.main([])


def test_no_directory_selected(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: no directory selected."""
    code = _run(monkeypatch, "")
    assert code == 1
    assert "Каталог не выбран" in capsys.readouterr().err


def test_directory_not_found(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: directory not found."""
    code = _run(monkeypatch, str(tmp_path / "missing"))
    assert code == 1
    assert "каталог не найден" in capsys.readouterr().err


def test_not_a_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: not a directory."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    code = _run(monkeypatch, str(file_path))
    assert code == 1
    assert "не является каталогом" in capsys.readouterr().err


def test_missing_scheme_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: missing scheme config."""
    code = _run(monkeypatch, str(tmp_path))
    assert code == 1
    assert ".fs-sch.toml" in capsys.readouterr().err


def test_no_violations_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: no violations returns zero."""
    root = make_tree(["Topic/_Resources/note.md"])
    (root / ".fs-sch.toml").write_text(_CONFIG, encoding="utf-8")
    code = _run(monkeypatch, str(root))
    out = capsys.readouterr().out
    assert code == 0
    assert "Статус: ok. Нарушений нет." in out


def test_violations_return_two(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: violations return two."""
    root = make_tree(["Topic/_Resources/"])
    (root / ".fs-sch.toml").write_text(_CONFIG, encoding="utf-8")
    code = _run(monkeypatch, str(root))
    out = capsys.readouterr().out
    assert code == 2
    assert "Нарушения" not in out
    assert "Topic/_Resources" not in out
    assert "Статус: error. Найдены нарушения структуры/контента." in out
    assert "Сводка: проверено групп: 1;" in out
    log = (root / FS_LOG).read_text(encoding="utf-8")
    assert "Topic/_Resources" in log


def test_argument_bypasses_picker(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: argument bypasses picker."""
    root = make_tree(["Topic/_Resources/note.md"])
    (root / ".fs-sch.toml").write_text(_CONFIG, encoding="utf-8")

    def _boom(*a: object, **k: object) -> str:
        """Вспомогательная функция для теста."""
        raise AssertionError("pick_directory не должен вызываться при аргументе-каталоге")

    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", _boom)
    monkeypatch.setattr(runner, "send_webhook", lambda text: True)
    code = runner.main([str(root)])
    assert code == 0
    assert "Статус: ok. Нарушений нет." in capsys.readouterr().out


def test_violations_writes_log_and_sends_webhook(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: violations writes log and sends webhook."""
    root = make_tree(["Topic/_Resources/"])
    (root / ".fs-sch.toml").write_text(_CONFIG, encoding="utf-8")
    sent: list[str] = []
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(root))
    monkeypatch.setattr(runner, "send_webhook", lambda text: bool(sent.append(text)) or True)
    code = runner.main([])
    assert code == 2
    log = (root / FS_LOG).read_text(encoding="utf-8")
    assert "Topic/_Resources" in log
    assert len(sent) == 1
    assert sent[0] == "fs-schemer - выполнен с ошибкой."


def test_apply_root_checks_separate_directory_logs_next_to_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """apply_root перенаправляет обход/отчёт в другой каталог; .fs-log — рядом с конфигом."""
    cfg_root = tmp_path / "Config"
    cfg_root.mkdir()
    target = tmp_path / "Warehouse"
    (target / "Topic" / "_Resources").mkdir(parents=True)
    (target / "Topic" / "_Resources" / "note.md").write_text("x", encoding="utf-8")
    (cfg_root / ".fs-sch.toml").write_text(
        f'[defaults]\napply_root = "{target.as_posix()}"\n\n{_CONFIG}',
        encoding="utf-8",
    )
    code = _run(monkeypatch, str(cfg_root))
    out = capsys.readouterr().out
    assert code == 0
    assert f"Каталог: {target}" in out
    assert (cfg_root / FS_LOG).is_file()
    assert not (target / FS_LOG).exists()


def test_apply_root_relative_resolved_against_config_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Относительный apply_root резолвится от каталога конфига, не от CWD."""
    cfg_root = tmp_path / "Config"
    cfg_root.mkdir()
    target = tmp_path / "Warehouse"
    target.mkdir()
    (target / "Topic" / "_Resources").mkdir(parents=True)
    (target / "Topic" / "_Resources" / "note.md").write_text("x", encoding="utf-8")
    (cfg_root / ".fs-sch.toml").write_text(
        f'[defaults]\napply_root = "../Warehouse"\n\n{_CONFIG}',
        encoding="utf-8",
    )
    code = _run(monkeypatch, str(cfg_root))
    assert code == 0
    assert (cfg_root / FS_LOG).is_file()


def test_apply_root_missing_directory_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """apply_root указывает на несуществующий каталог -> код 1."""
    cfg_root = tmp_path / "Config"
    cfg_root.mkdir()
    (cfg_root / ".fs-sch.toml").write_text(
        '[defaults]\napply_root = "missing"\n\n' + _CONFIG,
        encoding="utf-8",
    )
    code = _run(monkeypatch, str(cfg_root))
    assert code == 1
    assert "каталог не найден" in capsys.readouterr().err


def test_no_violations_logs_empty_result_no_webhook(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: no violations logs empty result no webhook."""
    root = make_tree(["Topic/_Resources/note.md"])
    (root / ".fs-sch.toml").write_text(_CONFIG, encoding="utf-8")
    sent: list[str] = []
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(root))
    monkeypatch.setattr(runner, "send_webhook", lambda text: bool(sent.append(text)) or True)
    code = runner.main([])
    assert code == 0
    log = (root / FS_LOG).read_text(encoding="utf-8")
    assert "Инструмент: schemer" in log
    assert "Режим: production" in log
    assert "Результат:" in log
    assert "(нарушений нет)" in log
    assert not sent
