"""Тесты offload: after_push, verify, частичный успех, dry-run, сбой передачи."""
import shutil
from pathlib import Path
from typing import Any

import pytest

from fs_tools.syncher import Profile, run_offload
from fs_tools.syncher import offload as offload_mod
from fs_tools.syncher.offload import apply_after_push

# Пропуск интеграционных тестов, если в системе нет rsync.
requires_rsync = pytest.mark.skipif(
    shutil.which("rsync") is None,
    reason="rsync не установлен",
)


def _backup(source_path: Path, **kw: Any) -> Profile:
    """Вспомогательная функция для теста."""
    base = {
        "name": "bak",
        "kind": "backup",
        "source_path": source_path,
        "target_path": "/srv/bak",
        "delete": False,
    }
    base.update(kw)
    return Profile(**base)


def test_apply_after_push_nothing(tmp_path: Path) -> None:
    """Проверяет сценарий: apply after push nothing."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    profile = _backup(tmp_path, after_push="nothing")
    offload, errlist = apply_after_push(profile, ["a.txt"])
    assert not offload and not errlist
    assert (tmp_path / "a.txt").exists()


def test_apply_after_push_delete(tmp_path: Path) -> None:
    """Проверяет сценарий: apply after push delete."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("a", encoding="utf-8")
    profile = _backup(tmp_path, after_push="delete")
    offload, errlist = apply_after_push(profile, ["sub/a.txt"])
    assert offload == ["sub/a.txt"] and not errlist
    assert not (tmp_path / "sub" / "a.txt").exists()
    assert not (tmp_path / "sub").exists()       # опустевший каталог удалён
    assert tmp_path.exists()                     # сам корень не трогаем


def test_apply_after_push_delete_keeps_included_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Проверяет сценарий: apply after push delete keeps included dir."""
    (tmp_path / "scope" / "anchor" / "nested").mkdir(parents=True)
    (tmp_path / "scope" / "anchor" / "nested" / "a.txt").write_text("a", encoding="utf-8")
    monkeypatch.setattr(
        offload_mod,
        "source_dirs",
        lambda profile, include_only=False: ["scope", "scope/anchor", "scope/anchor/nested"],
    )
    profile = _backup(
        tmp_path,
        after_push="delete",
        include=["*/", "**/anchor/", "**/anchor/**"],
    )
    offload, errlist = apply_after_push(profile, ["scope/anchor/nested/a.txt"])
    assert offload == ["scope/anchor/nested/a.txt"] and not errlist
    assert (tmp_path / "scope" / "anchor").exists()        # якорный каталог сохранён
    assert not (tmp_path / "scope" / "anchor" / "nested").exists()  # вложенный удалён


def test_apply_after_push_delete_keeps_nested_anchor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Проверяет сценарий: apply after push delete keeps nested anchor."""
    (tmp_path / "scope" / "anchor" / "nested").mkdir(parents=True)
    (tmp_path / "scope" / "anchor" / "nested" / "a.txt").write_text("a", encoding="utf-8")
    monkeypatch.setattr(
        offload_mod,
        "source_dirs",
        lambda profile, include_only=False: ["scope", "scope/anchor", "scope/anchor/nested"],
    )
    profile = _backup(
        tmp_path,
        after_push="delete",
        include=["*/", "**/anchor/", "**/anchor/**", "**/anchor/**/nested/**/"],
    )
    offload, errlist = apply_after_push(profile, ["scope/anchor/nested/a.txt"])
    assert offload == ["scope/anchor/nested/a.txt"] and not errlist
    assert (tmp_path / "scope" / "anchor" / "nested").exists()      # вложенный якорь сохранён


def test_apply_after_push_delete_drops_nested_same_anchor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Проверяет сценарий: apply after push drops nested same anchor."""
    (tmp_path / "scope" / "Back" / "Back").mkdir(parents=True)
    (tmp_path / "scope" / "Back" / "Back" / "a.txt").write_text("a", encoding="utf-8")
    monkeypatch.setattr(
        offload_mod,
        "source_dirs",
        lambda profile, include_only=False: ["scope", "scope/Back", "scope/Back/Back"],
    )
    profile = _backup(
        tmp_path,
        after_push="delete",
        include=["*/", "**/Back/", "**/Back/**"],
        exclude=["*"],
    )
    offload, errlist = apply_after_push(profile, ["scope/Back/Back/a.txt"])
    assert offload == ["scope/Back/Back/a.txt"] and not errlist
    assert (tmp_path / "scope" / "Back").exists()            # внешний якорь сохранён
    assert not (tmp_path / "scope" / "Back" / "Back").exists()  # вложенный одноимённый удалён


def test_apply_after_push_backup(tmp_path: Path) -> None:
    """Проверяет сценарий: apply after push backup."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    backup = tmp_path / "_arch"
    profile = _backup(tmp_path, after_push="backup", backup_path=backup)
    offload, errlist = apply_after_push(profile, ["a.txt"])
    assert offload == ["a.txt"] and not errlist
    assert not (tmp_path / "a.txt").exists()
    assert (backup / "a.txt").read_text(encoding="utf-8") == "a"


def test_run_offload_dry_run_keeps_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Проверяет сценарий: run offload dry run keeps files."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    class _Out:
        ok = True
        sent = ["a.txt"]
        deleted: list[str] = []
        stderr = ""

    monkeypatch.setattr(offload_mod, "run_rsync", lambda cmd: _Out())
    profile = _backup(tmp_path, after_push="delete")
    result = run_offload(profile, dry_run=True)
    assert result.sent == ["a.txt"]
    assert not result.offload
    assert (tmp_path / "a.txt").exists()         # dry-run ничего не удаляет


def test_run_offload_failed_push_no_delete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Проверяет сценарий: run offload failed push no delete."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    class _Out:
        ok = False
        rc = 23
        sent: list[str] = []
        deleted: list[str] = []
        stderr = "rsync error"

    monkeypatch.setattr(offload_mod, "run_rsync", lambda cmd: _Out())
    profile = _backup(tmp_path, after_push="delete")
    result = run_offload(profile, dry_run=False)
    assert result.rc == 2
    assert (tmp_path / "a.txt").exists()         # сбой передачи — не удаляем


def test_run_offload_verify_partial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Проверяет сценарий: run offload verify partial."""
    (tmp_path / "ok.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "bad.txt").write_text("bad", encoding="utf-8")

    class _Out:
        ok = True
        sent = ["ok.txt", "bad.txt"]
        deleted: list[str] = []
        stderr = ""

    monkeypatch.setattr(offload_mod, "run_rsync", lambda cmd: _Out())
    # область offload — то, что rsync считает к отправке (единый источник истины)
    monkeypatch.setattr(offload_mod, "source_files", lambda profile: ["ok.txt", "bad.txt"])
    # verify сообщает, что bad.txt ещё требует передачи → не подтверждён
    monkeypatch.setattr(offload_mod, "verify_pending", lambda profile: {"bad.txt"})
    profile = _backup(tmp_path, after_push="delete", verify=True)
    result = run_offload(profile, dry_run=False)
    assert result.offload == ["ok.txt"]
    assert not (tmp_path / "ok.txt").exists()
    assert (tmp_path / "bad.txt").exists()       # непереданное остаётся


# --- Реальный rsync ---


@requires_rsync
def test_real_offload_delete_after_verified(tmp_path: Path) -> None:
    """Проверяет сценарий: real offload delete after verified."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    for i in range(3):
        (src / f"f{i}.txt").write_text(str(i), encoding="utf-8")
    profile = _backup(src, target_path=str(dst), after_push="delete", verify=True)
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert sorted(result.offload) == ["f0.txt", "f1.txt", "f2.txt"]
    for i in range(3):
        assert (dst / f"f{i}.txt").exists()      # на сервере есть
        assert not (src / f"f{i}.txt").exists()  # локально удалены


@requires_rsync
def test_real_offload_excluded_file_not_deleted(tmp_path: Path) -> None:
    # Файл, исключённый фильтром, не попадает в область offload и не удаляется,
    # даже если verify (по другим файлам) прошёл успешно.
    """Проверяет сценарий: real offload excluded file not deleted."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "keep.txt").write_text("k", encoding="utf-8")
    (src / "scratch.tmp").write_text("t", encoding="utf-8")
    profile = _backup(
        src,
        target_path=str(dst),
        exclude=["*.tmp"],
        after_push="delete",
        verify=True,
    )
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert result.offload == ["keep.txt"]
    assert not (src / "keep.txt").exists()       # переданное удалено
    assert (src / "scratch.tmp").exists()        # исключённое осталось локально
    assert not (dst / "scratch.tmp").exists()    # и на сервер не ушло


@requires_rsync
def test_real_offload_keeps_matched_include_dirs(tmp_path: Path) -> None:
    """Проверяет сценарий: real offload keeps matched include dirs."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    anchor = src / "scope" / "anchor"
    nested = anchor / "nested"
    nested.mkdir(parents=True)
    (nested / "dump.sql").write_text("sql", encoding="utf-8")
    dst.mkdir()
    profile = _backup(
        src,
        target_path=str(dst),
        include=["*/", "**/anchor/", "**/anchor/**"],
        exclude=["*"],
        after_push="delete",
        verify=True,
    )
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert result.offload == ["scope/anchor/nested/dump.sql"]
    assert anchor.exists()                         # якорный каталог сохранён
    assert not nested.exists()                     # вложенный каталог удалён
    assert (dst / "scope" / "anchor" / "nested" / "dump.sql").exists()


@requires_rsync
def test_real_offload_keeps_explicit_nested_anchor(tmp_path: Path) -> None:
    """Проверяет сценарий: real offload keeps explicit nested anchor."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    anchor = src / "scope" / "anchor"
    nested = anchor / "nested"
    nested.mkdir(parents=True)
    (nested / "dump.sql").write_text("sql", encoding="utf-8")
    dst.mkdir()
    profile = _backup(
        src,
        target_path=str(dst),
        include=["*/", "**/anchor/", "**/anchor/**", "**/anchor/**/nested/**/"],
        exclude=["*"],
        after_push="delete",
        verify=True,
    )
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert result.offload == ["scope/anchor/nested/dump.sql"]
    assert anchor.exists()
    assert nested.exists()                         # вложенный якорь явно сохранён
    assert (dst / "scope" / "anchor" / "nested" / "dump.sql").exists()


@requires_rsync
def test_real_offload_drops_nested_same_anchor(tmp_path: Path) -> None:
    """Проверяет сценарий: real offload drops nested same anchor."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    nested = src / "scope" / "Back" / "Back"
    nested.mkdir(parents=True)
    (nested / "dump.sql").write_text("sql", encoding="utf-8")
    dst.mkdir()
    profile = _backup(
        src,
        target_path=str(dst),
        include=["*/", "**/Back/", "**/Back/**"],
        exclude=["*"],
        after_push="delete",
        verify=True,
    )
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert result.offload == ["scope/Back/Back/dump.sql"]
    assert (src / "scope" / "Back").exists()         # внешний якорь сохранён
    assert not (src / "scope" / "Back" / "Back").exists()  # вложенный одноимённый удалён
    assert (dst / "scope" / "Back" / "Back" / "dump.sql").exists()
