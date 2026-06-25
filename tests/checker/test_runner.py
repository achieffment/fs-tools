"""Тесты CLI режима проверки: коды возврата и сообщения (runner)."""
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from fs_tools.checker import FS_LOG, runner


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


def test_missing_fs_rule(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: missing fs rule."""
    code = _run(monkeypatch, str(tmp_path))
    assert code == 1
    assert ".fs-check" in capsys.readouterr().err


def test_no_violations_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: no violations returns zero."""
    root = make_tree(["Activities/Web/Projects/"])
    (root / ".fs-check").write_text("/Activities/Web/Projects\n", encoding="utf-8")
    code = _run(monkeypatch, str(root))
    out = capsys.readouterr().out
    assert code == 0
    assert "Статус: ok. Все требуемые пути на месте." in out


def test_violations_return_two(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: violations return two."""
    root = make_tree(["Activities/Web/"])
    (root / ".fs-check").write_text("/Activities/Web/Projects\n", encoding="utf-8")
    code = _run(monkeypatch, str(root))
    out = capsys.readouterr().out
    assert code == 2
    assert "Отсутствуют пути (1):" in out
    assert "Activities/Web/Projects" in out
    assert "Статус: warn. Найдены отсутствующие пути." in out
    assert "Сводка: проверено правил: 1;" in out
    assert "отсутствует: 1." in out


def test_argument_bypasses_picker(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Проверяет сценарий: argument bypasses picker."""
    root = make_tree(["Activities/Web/Projects/"])
    (root / ".fs-check").write_text("/Activities/Web/Projects\n", encoding="utf-8")

    def _boom(*a: object, **k: object) -> str:
        """Вспомогательная функция для теста."""
        raise AssertionError("pick_directory не должен вызываться при аргументе-каталоге")

    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", _boom)
    monkeypatch.setattr(runner, "send_webhook", lambda text: True)
    code = runner.main([str(root)])
    assert code == 0
    assert "Статус: ok. Все требуемые пути на месте." in capsys.readouterr().out


def test_missing_writes_log_and_sends_webhook(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: missing writes log and sends webhook."""
    root = make_tree(["Activities/Web/"])
    (root / ".fs-check").write_text("/Activities/Web/Projects\n", encoding="utf-8")
    sent: list[str] = []
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(root))
    monkeypatch.setattr(runner, "send_webhook", lambda text: bool(sent.append(text)) or True)
    code = runner.main([])
    assert code == 2
    log = (root / FS_LOG).read_text(encoding="utf-8")
    assert "Activities/Web/Projects" in log
    assert len(sent) == 1
    assert sent[0] == "fs-checker - выполнен с ошибкой."


def test_no_violations_logs_empty_result_no_webhook(
    monkeypatch: pytest.MonkeyPatch,
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: no violations logs empty result no webhook."""
    root = make_tree(["Activities/Web/Projects/"])
    (root / ".fs-check").write_text("/Activities/Web/Projects\n", encoding="utf-8")
    sent: list[str] = []
    monkeypatch.setattr("fs_tools.shared.cli.pick_directory", lambda *a, **k: str(root))
    monkeypatch.setattr(runner, "send_webhook", lambda text: bool(sent.append(text)) or True)
    code = runner.main([])
    assert code == 0
    log = (root / FS_LOG).read_text(encoding="utf-8")
    assert "Инструмент: checker" in log
    assert "Режим: production" in log
    assert "Результат:" in log
    assert "(нарушений нет)" in log
    assert not sent
