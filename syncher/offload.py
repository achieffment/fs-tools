"""Профиль [[backup]]: выгрузка на сервер с подтверждённым локальным удалением/архивом.

Поток: передать каталог (по умолчанию без серверного удаления — накопительный архив),
при `verify=true` сверить передачу повторным `rsync --dry-run --checksum` и применить
`after_push` (`delete` | `archive` | `nothing`) ТОЛЬКО к локальным файлам, чья передача
подтверждена. Частичный успех не трогает непереданное — это ключевой инвариант
безопасности данных.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .config import Profile
from .rsync import RsyncOutcome, build_command, run_rsync, source_files


@dataclass
class OffloadResult:
    """Итог offload-профиля: переданное, выгруженное (удалено/архивировано) и ошибки."""

    returncode: int
    sent: list[str] = field(default_factory=list)
    offloaded: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.errors


def verify_pending(profile: Profile) -> set[str]:
    """Файлы, которые повторный сухой прогон (с checksum) всё ещё считает к передаче.

    Пустое множество означает: всё переданное идентично на сервере. Передача каждого
    файла из этого множества НЕ подтверждена.
    """
    cmd = build_command(profile, dry_run=True, delete=False)
    if "--checksum" not in cmd:
        cmd.insert(1, "--checksum")
    return set(run_rsync(cmd).sent)


def _default_archive_dir(profile: Profile) -> Path:
    """`<local_root>/../_fs-archive/<profile>/<YYYY-MM-DD>/` по умолчанию."""
    stamp = date.today().strftime("%Y-%m-%d")
    return profile.local_root.parent / "_fs-archive" / profile.name / stamp


def _prune_empty_dirs(root: Path, start: Path) -> None:
    """Удалить опустевшие каталоги вверх до root (сам root не трогаем)."""
    current = start
    while current != root and current.is_dir():
        try:
            next(current.iterdir())
            return
        except StopIteration:
            parent = current.parent
            current.rmdir()
            current = parent


def apply_after_push(
    profile: Profile,
    confirmed: list[str],
) -> tuple[list[str], list[str]]:
    """Применить after_push к подтверждённым файлам. Возвращает (выгружено, ошибки)."""
    offloaded: list[str] = []
    errors: list[str] = []
    if profile.after_push == "nothing" or not confirmed:
        return offloaded, errors

    root = profile.local_root
    archive_dir = profile.archive_dir or _default_archive_dir(profile)
    for rel in confirmed:
        src = root / rel
        if not src.exists():
            continue
        try:
            if profile.after_push == "delete":
                src.unlink()
                _prune_empty_dirs(root, src.parent)
            elif profile.after_push == "archive":
                dest = archive_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                src.replace(dest)
                _prune_empty_dirs(root, src.parent)
            offloaded.append(rel)
        except OSError as exc:
            errors.append(f"{rel}: {exc}")
    return offloaded, errors


def run_offload(profile: Profile, *, dry_run: bool) -> OffloadResult:
    """Выгрузить профиль и (при подтверждении) применить after_push.

    В dry-run только показывается план передачи; локальные файлы не трогаются.
    """
    push: RsyncOutcome = run_rsync(
        build_command(profile, dry_run=dry_run, delete=profile.delete)
    )
    code = 0 if push.ok else 2
    result = OffloadResult(returncode=code, sent=push.sent)
    if dry_run or not push.ok:
        if not push.ok and push.stderr:
            result.errors.append(push.stderr.strip())
        return result

    scope = source_files(profile)
    pending = verify_pending(profile) if profile.verify else set()
    confirmed = [rel for rel in scope if rel not in pending]
    offloaded, errors = apply_after_push(profile, confirmed)
    result.offloaded = offloaded
    result.errors += errors
    if errors:
        result.returncode = 2
    return result
