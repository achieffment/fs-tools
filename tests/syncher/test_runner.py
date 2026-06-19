"""Тесты runner: коды возврата 0/1/2/3, --profile, --dry-run, журнал, отсутствие rsync.

Также проверяется неинтерактивность режима: без аргумента берётся текущий каталог,
диалог выбора не открывается (picker режимом не используется).
"""
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from fs_tools.syncher import runner
from fs_tools.syncher.runner import main

# Пропуск интеграционных тестов, если в системе нет rsync.
requires_rsync = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync не установлен")


def _sync_config(source: Path, dst: Path, **fields: str) -> str:
    extra = "".join(f"{k} = {v}\n" for k, v in fields.items())
    return (
        '[[sync]]\n'
        'name = "main"\n'
        f'local_root = "{source.as_posix()}"\n'
        f'remote_root = "{dst.as_posix()}"\n'
        f"{extra}"
    )


def test_missing_directory(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["/no/such/dir/xyz"]) == 1
    assert "не найден" in capsys.readouterr().err


def test_missing_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path)]) == 1
    assert "нет файла" in capsys.readouterr().err


def test_no_arg_uses_cwd_no_dialog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Без аргумента берётся CWD; диалог не открывается (нет .fs-sync.toml → код 1).
    monkeypatch.setattr(runner, "rsync_available", lambda: True)
    monkeypatch.chdir(tmp_path)
    assert main([]) == 1
    assert "нет файла" in capsys.readouterr().err


def test_missing_rsync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                       capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / ".fs-sync.toml").write_text(
        _sync_config(tmp_path, tmp_path / "dst"), encoding="utf-8"
    )
    monkeypatch.setattr(runner, "rsync_available", lambda: False)
    assert main([str(tmp_path)]) == 1
    assert "rsync" in capsys.readouterr().err


def test_missing_ssh_for_ssh_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                    capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / ".fs-sync.toml").write_text(
        '[[sync]]\nname = "m"\nlocal_root = "."\nremote_root = "host:/srv"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "rsync_available", lambda: True)
    monkeypatch.setattr(runner, "ssh_available", lambda: False)
    assert main([str(tmp_path)]) == 1
    assert "ssh" in capsys.readouterr().err


def test_unknown_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                         capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / ".fs-sync.toml").write_text(
        _sync_config(tmp_path, tmp_path / "dst"), encoding="utf-8"
    )
    monkeypatch.setattr(runner, "rsync_available", lambda: True)
    assert main([str(tmp_path), "--profile", "nope"]) == 1
    assert "не найден" in capsys.readouterr().err


@requires_rsync
def test_success_and_log(tmp_path: Path, make_tree: Callable[..., Path]) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    make_tree(src, ["a.txt", "sub/b.txt"])
    dst.mkdir()
    (src / ".fs-sync.toml").write_text(_sync_config(src, dst), encoding="utf-8")
    assert main([str(src)]) == 0
    assert (dst / "a.txt").exists()
    log = (src / ".fs-log").read_text(encoding="utf-8")
    assert "+ a.txt" in log


@requires_rsync
def test_dry_run_no_transfer_no_log(tmp_path: Path, make_tree: Callable[..., Path]) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    make_tree(src, ["a.txt"])
    dst.mkdir()
    (src / ".fs-sync.toml").write_text(_sync_config(src, dst), encoding="utf-8")
    assert main([str(src), "--dry-run"]) == 0
    assert not (dst / "a.txt").exists()          # dry-run ничего не передаёт
    assert not (src / ".fs-log").exists()        # и не пишет журнал


@requires_rsync
def test_delete_guard_blocks_returns_3(tmp_path: Path, make_tree: Callable[..., Path]) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    make_tree(src, [f"f{i}.txt" for i in range(6)])
    dst.mkdir()
    (src / ".fs-sync.toml").write_text(
        _sync_config(src, dst, delete="true", delete_threshold="2"), encoding="utf-8"
    )
    assert main([str(src)]) == 0                 # первый прогон — наполнение
    for i in range(6):
        (src / f"f{i}.txt").unlink()
    assert main([str(src)]) == 3                 # массовое удаление заблокировано
    assert len(list(dst.iterdir())) == 6         # на сервере всё на месте
    assert main([str(src), "--force-delete"]) == 0
    assert list(dst.iterdir()) == []             # после подтверждения — удалено


@requires_rsync
def test_profile_selection(tmp_path: Path, make_tree: Callable[..., Path]) -> None:
    src = tmp_path / "src"
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    make_tree(src, ["a.txt"])
    d1.mkdir()
    d2.mkdir()
    text = (
        '[[sync]]\n'
        'name = "one"\n'
        f'local_root = "{src.as_posix()}"\n'
        f'remote_root = "{d1.as_posix()}"\n'
        '[[sync]]\n'
        'name = "two"\n'
        f'local_root = "{src.as_posix()}"\n'
        f'remote_root = "{d2.as_posix()}"\n'
    )
    (src / ".fs-sync.toml").write_text(text, encoding="utf-8")
    assert main([str(src), "--profile", "one"]) == 0
    assert (d1 / "a.txt").exists()
    assert not (d2 / "a.txt").exists()           # второй профиль не запускался
