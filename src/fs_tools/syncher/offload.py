"""Профиль [[backup]]: выгрузка на сервер с подтверждённым локальным удалением/архивом.

Поток: передать каталог (по умолчанию без серверного удаления — накопительный архив),
при `verify=true` сверить передачу повторным `rsync --dry-run --checksum` и применить
`after_push` (`delete` | `backup` | `nothing`) ТОЛЬКО к локальным файлам, чья передача
подтверждена. Частичный успех не трогает непереданное — это ключевой инвариант
безопасности данных.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .config import Profile
from .rsync import RsyncOutcome, build_command, run_rsync, source_dirs, source_files


@dataclass
class OffloadResult:
    """Итог offload-профиля: переданное, выгруженное (удалено/архивировано) и ошибки."""

    rc: int
    sent: list[str] = field(default_factory=list)
    offload: list[str] = field(default_factory=list)
    errlist: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True, когда профиль завершился без ошибок передачи и offload."""
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


def _anchor_includes(include: list[str]) -> list[str]:
    """Якорные include-паттерны каталогов (универсально, без привязки к именам)."""
    anchors: list[str] = []
    seen: set[str] = set()
    for pat in include:
        curr = pat.strip()
        if not curr:
            continue
        anchor: str | None = None
        if curr.endswith("/**/"):
            anchor = curr[:-4] + "/"
        elif curr.endswith("/"):
            anchor = curr
        if anchor is None:
            continue
        bare = anchor.rstrip("/")
        tail = bare.rsplit("/", 1)[-1]
        if tail in {"*", "**"}:
            continue
        if any(ch in tail for ch in "*?[]"):
            continue
        if anchor not in seen:
            seen.add(anchor)
            anchors.append(anchor)
    return anchors


def _matches_anchor(rel: str, anchor: str) -> bool:
    """Совпадает ли относительный каталог с якорным include-паттерном."""
    clean = anchor.strip("/")
    if not clean:
        return False
    rel_parts = tuple(part for part in rel.split("/") if part)
    anchor_parts = tuple(part for part in clean.split("/") if part)

    @lru_cache(maxsize=None)
    def match(ix: int, jx: int) -> bool:
        if jx == len(anchor_parts):
            return ix == len(rel_parts)
        part = anchor_parts[jx]
        if part == "**":
            if match(ix, jx + 1):
                return True
            if ix < len(rel_parts) and match(ix + 1, jx):
                return True
            return False
        if ix >= len(rel_parts):
            return False
        if not fnmatch.fnmatchcase(rel_parts[ix], part):
            return False
        return match(ix + 1, jx + 1)

    return match(0, 0)


def _is_descendant(path: str, parent: str) -> bool:
    """True, если относительный каталог path лежит внутри parent."""
    return path == parent or path.startswith(parent + "/")


def _protected_dirs(profile: Profile) -> set[Path]:
    """Каталоги якорной include-области, которые нельзя удалять после offload."""
    if not profile.include:
        return set()
    anchors = _anchor_includes(profile.include)
    if not anchors:
        return set()
    root = profile.source_path
    rel_dirs = source_dirs(profile, include_only=True)
    protected: set[Path] = set()
    for anchor in anchors:
        matched = [rel for rel in rel_dirs if _matches_anchor(rel, anchor)]
        matched = sorted(matched, key=lambda rel: (rel.count("/"), rel))
        selected: list[str] = []
        for rel in matched:
            if any(_is_descendant(rel, parent) for parent in selected):
                continue
            selected.append(rel)
        protected = protected.union({root / rel for rel in selected})
    return protected


def _prune_empty_dirs(root: Path, start: Path, *, protected: set[Path]) -> None:
    """Удалить опустевшие каталоги вверх до root, кроме защищённых каталогов."""
    curr = start
    while curr != root and curr.is_dir():
        if curr in protected:
            return
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
    protected = _protected_dirs(profile)
    for rel in confirm:
        src = root / rel
        if not src.exists():
            continue
        try:
            if profile.after_push == "delete":
                src.unlink()
                _prune_empty_dirs(root, src.parent, protected=protected)
            elif profile.after_push == "backup":
                dst = backup_path / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                src.replace(dst)
                _prune_empty_dirs(root, src.parent, protected=protected)
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
    result.errlist = result.errlist + errlist
    if errlist:
        result.rc = 2
    return result
