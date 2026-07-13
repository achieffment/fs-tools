"""Тесты rsync: сборка команды, разбор итемизированного итога, delete-guard."""
import shutil
from pathlib import Path
from typing import Any

import pytest

from fs_tools.syncher import (
    DeletePlan,
    Profile,
    build_command,
    build_listing,
    delete_preflight,
    parse_itemized,
    parse_listing,
    source_files,
)
from fs_tools.syncher import rsync as rsync_mod

# Пропуск интеграционных тестов, если в системе нет rsync.
requires_rsync = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync не установлен")


def _profile(tmp_path: Path, **kw: Any) -> Profile:
    """Вспомогательная функция для теста."""
    base = {"name": "p", "kind": "sync", "source_path": tmp_path, "target_path": "/srv/dst"}
    base.update(kw)
    return Profile(**base)


def test_build_command_basics(tmp_path: Path) -> None:
    """Проверяет сценарий: build command basics."""
    cmd = build_command(_profile(tmp_path), dry_run=False, delete=True)
    assert cmd[0] == "rsync"
    assert "-a" in cmd and "--itemize-changes" in cmd and "--stats" in cmd
    assert "--delete" in cmd
    assert cmd[-2].endswith("/")               # источник с завершающим /
    assert cmd[-1] == "/srv/dst/"


def test_build_command_dry_run_and_options(tmp_path: Path) -> None:
    """Проверяет сценарий: build command dry run and options."""
    profile = _profile(tmp_path, checksum=True, compress=True, partial_progress=True, bwlimit="500")
    cmd = build_command(profile, dry_run=True, delete=False)
    assert "--dry-run" in cmd
    assert "--checksum" in cmd
    assert "-z" in cmd
    assert "--partial" in cmd and "--progress" in cmd
    assert "--bwlimit=500" in cmd
    assert "--delete" not in cmd


def test_build_command_ssh_opts_only_for_ssh(tmp_path: Path) -> None:
    """Проверяет сценарий: build command ssh opts only for ssh."""
    ssh = _profile(tmp_path, target_path="host:/p", ssh_opts=["-p", "2222"])
    cmd1 = build_command(ssh, dry_run=False, delete=False)
    assert "-e" in cmd1
    assert "ssh -p 2222" in cmd1
    assert cmd1[-1] == "host:/p/"

    source = _profile(tmp_path, ssh_opts=["-p", "2222"])
    cmd2 = build_command(source, dry_run=False, delete=False)
    assert "-e" not in cmd2                     # локальная цель — ssh не нужен


def test_build_command_windows_source_with_ssh_dest() -> None:
    """Проверяет сценарий: build command windows source with ssh dest."""
    profile = Profile(
        name="p",
        kind="sync",
        source_path=Path("E:/Home/Access"),
        target_path="user@host:/mnt/disk/Home/Access",
    )
    cmd = build_command(profile, dry_run=True, delete=False)
    assert cmd[-2] == "/cygdrive/e/Home/Access/"
    assert cmd[-1] == "user@host:/mnt/disk/Home/Access/"


def test_build_command_windows_local_dest_is_not_remote() -> None:
    """Проверяет сценарий: build command windows local dest is not remote."""
    profile = Profile(
        name="p",
        kind="sync",
        source_path=Path("E:/Home/Access"),
        target_path="D:/Backup/Access",
    )
    cmd = build_command(profile, dry_run=False, delete=False)
    assert cmd[-2] == "/cygdrive/e/Home/Access/"
    assert cmd[-1] == "/cygdrive/d/Backup/Access/"


def test_parse_itemized_sent_and_deleted() -> None:
    """Проверяет сценарий: parse itemized sent and deleted."""
    out = (
        ">f+++++++++ a.txt\n"
        "<f.st...... b.txt\n"
        "cd+++++++++ newdir/\n"
        ".f          unchanged.txt\n"
        "*deleting   old.txt\n"
        "*deleting   gone/\n"
    )
    sent, deleted = parse_itemized(out)
    assert sent == ["a.txt", "b.txt"]           # каталог newdir и unchanged пропущены
    assert deleted == ["old.txt", "gone"]


def test_parse_itemized_empty_idempotent() -> None:
    """Проверяет сценарий: parse itemized empty idempotent."""
    sent, deleted = parse_itemized("\nNumber of files: 5\n")
    assert not sent and not deleted


def test_build_listing_single_endpoint() -> None:
    """Проверяет сценарий: build listing single endpoint."""
    cmd = build_listing("/srv/dst/", ["--filter=- *.tmp"])
    assert cmd == ["rsync", "-a", "--list-only", "--filter=- *.tmp", "/srv/dst/"]


def test_parse_listing_files_and_dirs() -> None:
    """Проверяет сценарий: parse listing files and dirs."""
    out = (
        "drwxr-xr-x          4,096 2026/06/16 12:00:00 .\n"
        "-rw-r--r--              2 2026/06/16 12:00:00 a.txt\n"
        "drwxr-xr-x          4,096 2026/06/16 12:00:00 sub\n"
        "-rw-r--r--              5 2026/06/16 12:00:00 sub/two words.txt\n"
    )
    items = parse_listing(out)
    assert items == [
        ("a.txt", False),
        ("sub", True),
        ("sub/two words.txt", False),       # пробелы в имени сохранены, "." пропущена
    ]


def test_delete_plan_thresholds() -> None:
    """Проверяет сценарий: delete plan thresholds."""
    plan = DeletePlan(to_delete=["a", "b", "c"], remote_total=4)
    assert plan.count == 3
    assert plan.pct() == pytest.approx(75.0)
    assert plan.blocked(threshold=100, threshold_pct=25) is True    # по доле
    assert plan.blocked(threshold=2, threshold_pct=100) is True     # по количеству
    assert plan.blocked(threshold=100, threshold_pct=100) is False


def test_delete_plan_zero_remote_no_pct() -> None:
    """Проверяет сценарий: delete plan zero remote no pct."""
    plan = DeletePlan(to_delete=[], remote_total=0)
    assert plan.pct() == 0.0
    assert plan.blocked(threshold=100, threshold_pct=25) is False


def test_delete_preflight_uses_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Проверяет сценарий: delete preflight uses mock."""
    calls: list[list[str]] = []

    class _Proc:
        def __init__(self, stdout: str) -> None:
            """Вспомогательная функция для теста."""
            self.stdout = stdout
            self.stderr = ""
            self.returncode = 0

    def fake_run(cmd: list[str], **_kw: Any) -> _Proc:
        """Выполняет шаг: fake run."""
        calls.append(cmd)
        if "--list-only" in cmd:
            return _Proc(
                "drwxr-xr-x 0 2024/01/01 00:00:00 .\n"
                "-rw-r--r-- 1 2024/01/01 00:00:00 keep\n"
                "-rw-r--r-- 1 2024/01/01 00:00:00 x\n"
            )
        return _Proc("*deleting   x\n*deleting   y\n")

    monkeypatch.setattr(rsync_mod.subprocess, "run", fake_run)
    plan = delete_preflight(_profile(tmp_path))
    assert plan.to_delete == ["x", "y"]
    assert plan.remote_total == 2               # корневая "." не считается
    assert any("--delete" in c for c in calls)
    assert any("--list-only" in c for c in calls)


# --- Реальный rsync (локальный каталог→каталог, без сети) ---


@requires_rsync
def test_real_sync_transfers_and_idempotent(tmp_path: Path) -> None:
    """Проверяет сценарий: real sync transfers and idempotent."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "sub").mkdir(parents=True)
    dst.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "sub" / "b.txt").write_text("b", encoding="utf-8")
    profile = _profile(src, target_path=str(dst), delete=True)

    first = rsync_mod.run_rsync(build_command(profile, dry_run=False, delete=True))
    assert first.ok
    assert sorted(first.sent) == ["a.txt", "sub/b.txt"]
    assert (dst / "a.txt").is_file()

    again = rsync_mod.run_rsync(build_command(profile, dry_run=False, delete=True))
    assert not again.sent and not again.deleted    # идемпотентность


@requires_rsync
def test_real_delete_mirrors(tmp_path: Path) -> None:
    """Проверяет сценарий: real delete mirrors."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    profile = _profile(src, target_path=str(dst), delete=True)
    rsync_mod.run_rsync(build_command(profile, dry_run=False, delete=True))
    (src / "a.txt").unlink()
    out = rsync_mod.run_rsync(build_command(profile, dry_run=False, delete=True))
    assert out.deleted == ["a.txt"]
    assert not (dst / "a.txt").exists()


@requires_rsync
def test_real_artifacts_excluded(tmp_path: Path) -> None:
    """Проверяет сценарий: real artifacts excluded."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / ".fs-syn.toml").write_text("x", encoding="utf-8")
    (src / ".fs-log.log").write_text("x", encoding="utf-8")
    (src / ".env").write_text("secret", encoding="utf-8")
    profile = _profile(src, target_path=str(dst), delete=True)
    rsync_mod.run_rsync(build_command(profile, dry_run=False, delete=True))
    assert (dst / "a.txt").exists()
    assert not (dst / ".fs-syn.toml").exists()
    assert not (dst / ".fs-log.log").exists()
    assert not (dst / ".env").exists()


@requires_rsync
def test_real_source_files_respects_filters(tmp_path: Path) -> None:
    """Проверяет сценарий: real source files respects filters."""
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "sub" / "b.bin").write_text("b", encoding="utf-8")
    (src / "skip.tmp").write_text("t", encoding="utf-8")
    (src / ".fs-syn.toml").write_text("x", encoding="utf-8")   # артефакт исключается
    profile = _profile(src, target_path=str(tmp_path / "dst"), exclude=["*.tmp"])
    assert source_files(profile) == ["a.txt", "sub/b.bin"]


@requires_rsync
def test_real_remote_object_count(tmp_path: Path) -> None:
    """Проверяет сценарий: real remote object count."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (dst / "x.txt").write_text("x", encoding="utf-8")
    (dst / "sub").mkdir()
    (dst / "sub" / "y.txt").write_text("y", encoding="utf-8")
    profile = _profile(src, target_path=str(dst))
    # считаются объекты приёмника (файлы и каталоги), не источника
    assert rsync_mod.remote_object_count(profile) == 3
