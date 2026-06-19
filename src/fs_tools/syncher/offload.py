"""Профиль [[backup]]: выгрузка на сервер с подтверждённым локальным удалением/архивом.

Поток: передать каталог (по умолчанию без серверного удаления — накопительный архив),
при `verify=true` сверить передачу повторным `rsync --dry-run --checksum` и применить
`after_push` (`delete` | `backup` | `nothing`) ТОЛЬКО к локальным файлам, чья передача
подтверждена. Частичный успех не трогает непереданное — это ключевой инвариант
безопасности данных.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import Profile
from .rsync import RsyncOutcome, build_command, run_rsync, source_files


@dataclass
class OffloadResult:
    """Итог offload-профиля: переданное, выгруженное (удалено/архивировано) и ошибки."""

    rc: int
    sent: list[str] = field(default_factory=list)
    offload: list[str] = field(default_factory=list)
    errlist: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.rc == 0 and not self.errlist


def verify_pending(profile: Profile) -> set[str]:
    """Файлы, которые повторный сухой прогон (с checksum) всё ещё считает к передаче.

    Пустое множество означает: всё переданное идентично на сервере. Передача каждого
    файла из этого множества НЕ подтверждена.
    """
    cmd = build_command(profile, dry_run=True, delete=False)
    if "--checksum" not in cmd:
        cmd.insert(1, "--checksum")
    return set(run_rsync(cmd).sent)


def _default_backup_dir(profile: Profile) -> Path:
    """`<source_root>/../_fs-backup/<profile>/<YYYY-MM-DD>/` по умолчанию."""
    date = datetime.now().strftime("%Y-%m-%d")
    return profile.source_path.parent / "_fs-backup" / profile.name / date


def _prune_empty_dirs(root: Path, start: Path) -> None:
    """Удалить опустевшие каталоги вверх до root (сам root не трогаем)."""
    curr = start
    while curr != root and curr.is_dir():
        try:
            next(curr.iterdir())
            return
        except StopIteration:
            parent = curr.parent
            curr.rmdir()
            curr = parent


def apply_after_push(
    profile: Profile,
    confirm: list[str],
) -> tuple[list[str], list[str]]:
    """Применить after_push к подтверждённым файлам. Возвращает (выгружено, ошибки)."""
    offload: list[str] = []
    errlist: list[str] = []
    if profile.after_push == "nothing" or not confirm:
        return offload, errlist

    root = profile.source_path
    backup_path = profile.backup_path or _default_backup_dir(profile)
    for rel in confirm:
        src = root / rel
        if not src.exists():
            continue
        try:
            if profile.after_push == "delete":
                src.unlink()
                _prune_empty_dirs(root, src.parent)
            elif profile.after_push == "backup":
                dst = backup_path / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                src.replace(dst)
                _prune_empty_dirs(root, src.parent)
            offload.append(rel)
        except OSError as exc:
            errlist.append(f"{rel}: {exc}")
    return offload, errlist


def run_offload(profile: Profile, *, dry_run: bool) -> OffloadResult:
    """Выгрузить профиль и (при подтверждении) применить after_push.

    В dry-run только показывается план передачи; локальные файлы не трогаются.
    """
    push: RsyncOutcome = run_rsync(
        build_command(profile, dry_run=dry_run, delete=profile.delete)
    )
    rc = 0 if push.ok else 2
    result = OffloadResult(rc=rc, sent=push.sent)
    if dry_run or not push.ok:
        if not push.ok and push.stderr:
            result.errlist.append(push.stderr.strip())
        return result

    scope = source_files(profile)
    pending = verify_pending(profile) if profile.verify else set()
    confirm = [rel for rel in scope if rel not in pending]
    offload, errlist = apply_after_push(profile, confirm)
    result.offload = offload
    result.errlist += errlist
    if errlist:
        result.rc = 2
    return result
