"""Тесты offload: after_push, verify, частичный успех, dry-run, сбой передачи."""
from pathlib import Path
from typing import Any

import pytest

from syncher import Profile, run_offload
from syncher import offload as offload_mod
from syncher.offload import apply_after_push
from tests.conftest import requires_rsync


def _backup(local_root: Path, **kw: Any) -> Profile:
    base = dict(name="bak", kind="backup", local_root=local_root, remote_root="/srv/bak", delete=False)
    base.update(kw)
    return Profile(**base)


def test_apply_after_push_nothing(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    profile = _backup(tmp_path, after_push="nothing")
    offloaded, errors = apply_after_push(profile, ["a.txt"])
    assert offloaded == [] and errors == []
    assert (tmp_path / "a.txt").exists()


def test_apply_after_push_delete(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("a", encoding="utf-8")
    profile = _backup(tmp_path, after_push="delete")
    offloaded, errors = apply_after_push(profile, ["sub/a.txt"])
    assert offloaded == ["sub/a.txt"] and errors == []
    assert not (tmp_path / "sub" / "a.txt").exists()
    assert not (tmp_path / "sub").exists()       # опустевший каталог удалён
    assert tmp_path.exists()                     # сам корень не трогаем


def test_apply_after_push_archive(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    archive = tmp_path / "_arch"
    profile = _backup(tmp_path, after_push="archive", archive_dir=archive)
    offloaded, errors = apply_after_push(profile, ["a.txt"])
    assert offloaded == ["a.txt"] and errors == []
    assert not (tmp_path / "a.txt").exists()
    assert (archive / "a.txt").read_text(encoding="utf-8") == "a"


def test_run_offload_dry_run_keeps_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    assert result.offloaded == []
    assert (tmp_path / "a.txt").exists()         # dry-run ничего не удаляет


def test_run_offload_failed_push_no_delete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    class _Out:
        ok = False
        returncode = 23
        sent: list[str] = []
        deleted: list[str] = []
        stderr = "rsync error"

    monkeypatch.setattr(offload_mod, "run_rsync", lambda cmd: _Out())
    profile = _backup(tmp_path, after_push="delete")
    result = run_offload(profile, dry_run=False)
    assert result.returncode == 2
    assert (tmp_path / "a.txt").exists()         # сбой передачи — не удаляем


def test_run_offload_verify_partial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    assert result.offloaded == ["ok.txt"]
    assert not (tmp_path / "ok.txt").exists()
    assert (tmp_path / "bad.txt").exists()       # непереданное остаётся


# --- Реальный rsync ---


@requires_rsync
def test_real_offload_delete_after_verified(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    for i in range(3):
        (src / f"f{i}.txt").write_text(str(i), encoding="utf-8")
    profile = _backup(src, remote_root=str(dst), after_push="delete", verify=True)
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert sorted(result.offloaded) == ["f0.txt", "f1.txt", "f2.txt"]
    for i in range(3):
        assert (dst / f"f{i}.txt").exists()      # на сервере есть
        assert not (src / f"f{i}.txt").exists()  # локально удалены


@requires_rsync
def test_real_offload_excluded_file_not_deleted(tmp_path: Path) -> None:
    # Файл, исключённый фильтром, не попадает в область offload и не удаляется,
    # даже если verify (по другим файлам) прошёл успешно.
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "keep.txt").write_text("k", encoding="utf-8")
    (src / "scratch.tmp").write_text("t", encoding="utf-8")
    profile = _backup(src, remote_root=str(dst), exclude=["*.tmp"], after_push="delete", verify=True)
    result = run_offload(profile, dry_run=False)
    assert result.ok
    assert result.offloaded == ["keep.txt"]
    assert not (src / "keep.txt").exists()       # переданное удалено
    assert (src / "scratch.tmp").exists()        # исключённое осталось локально
    assert not (dst / "scratch.tmp").exists()    # и на сервер не ушло
