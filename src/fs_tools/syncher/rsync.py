"""Сборка и запуск команды rsync, разбор итемизированного итога, delete-guard.

Базовый набор опций: `-a` (архив) + `--itemize-changes` (для отчёта/журнала) +
`--stats`. Зеркалирование удалений (`--delete`), сжатие (`-z`), `--checksum`,
`--partial --progress`, `--bwlimit`, кастомный транспорт `-e ssh ...` — по параметрам
профиля. Источник всегда формируется с завершающим `/` (содержимое каталога), чтобы
поведение не зависело от слешей в конфиге.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import Profile, split_target
from .ignore import filter_args

RSYNC = "rsync"


@dataclass
class RsyncOutcome:
    """Итог одного запуска rsync: переданные/удалённые объекты и код возврата."""

    rc: int
    sent: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.rc == 0


@dataclass
class DeletePlan:
    """Результат preflight-расчёта удалений для delete-guard."""

    to_delete: list[str]
    remote_total: int

    @property
    def count(self) -> int:
        return len(self.to_delete)

    def pct(self) -> float:
        if self.remote_total <= 0:
            return 0.0
        return self.count / self.remote_total * 100.0

    def blocked(self, threshold: int, threshold_pct: float) -> bool:
        """Превышен ли любой из порогов (по количеству или по доле)."""
        return self.count > threshold or self.pct() > threshold_pct


def rsync_available() -> bool:
    """Доступен ли бинарь rsync в PATH."""
    return shutil.which(RSYNC) is not None


def ssh_available() -> bool:
    """Доступен ли бинарь ssh в PATH (нужен только для SSH-целей)."""
    return shutil.which("ssh") is not None


def _source(source_path: Path) -> str:
    """Путь-источник для rsync: posix + завершающий `/` (содержимое каталога)."""
    return source_path.as_posix().rstrip("/") + "/"


def _dest(target_path: str) -> str:
    """Путь-приёмник: завершающий `/`, чтобы синхронизировать содержимое в каталог."""
    is_ssh, host, path = split_target(target_path)
    norm = path.rstrip("/") + "/"
    if is_ssh and host is not None:
        return f"{host}:{norm}"
    return norm


def transfer_args(profile: Profile) -> list[str]:
    """Опции передачи, зависящие от профиля (без --delete и --dry-run)."""
    args: list[str] = []
    if profile.checksum:
        args.append("--checksum")
    if profile.compress:
        args.append("-z")
    if profile.partial_progress:
        args += ["--partial", "--progress"]
    if profile.bwlimit:
        args.append(f"--bwlimit={profile.bwlimit}")
    if profile.ssh_opts and split_target(profile.target_path)[0]:
        args += ["-e", "ssh " + " ".join(profile.ssh_opts)]
    return args


def build_command(
    profile: Profile,
    *,
    dry_run: bool,
    delete: bool,
) -> list[str]:
    """Собрать аргументы запуска rsync (передача source/ → dest/) для профиля."""
    cmd = [RSYNC, "-a", "--itemize-changes", "--stats"]
    if delete:
        cmd.append("--delete")
    if dry_run:
        cmd.append("--dry-run")
    cmd += transfer_args(profile)
    cmd += filter_args(profile.exclude, profile.include)
    cmd.append(_source(profile.source_path))
    cmd.append(_dest(profile.target_path))
    return cmd


def build_listing(endpoint: str, filters: list[str]) -> list[str]:
    """Команда `rsync --list-only` одной точки (источника ИЛИ приёмника).

    Перечисляет содержимое endpoint с учётом filters. Важно: `--list-only` с двумя
    путями (src dst) листает ИСТОЧНИК, поэтому для подсчётов всегда передаём ровно
    одну точку — ту, что хотим перечислить.
    """
    return [RSYNC, "-a", "--list-only", *filters, endpoint]


def parse_listing(stdout: str) -> list[tuple[str, bool]]:
    """Разобрать вывод `--list-only` в список (путь, is_dir); корневую `.` пропустить.

    Формат строки: `<права> <размер> <дата> <время> <путь>` (путь может содержать
    пробелы — он идёт после четвёртого разделителя). Каталог распознаётся по `d` в
    правах.
    """
    items: list[tuple[str, bool]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        perms, path = parts[0], parts[4]
        if path == ".":
            continue
        items.append((path.rstrip("/"), perms.startswith("d")))
    return items


def parse_itemized(stdout: str) -> tuple[list[str], list[str]]:
    """Разобрать вывод `--itemize-changes`: (переданные пути, удалённые пути).

    Переданными считаем файлы/симлинки с реальным изменением (первый символ кода —
    `<`, `>`, `c` или `h`; создание каталогов `cd...` пропускаем как структурное).
    Удаления — строки `*deleting <путь>`. Строки без изменений (код на `.`) не
    попадают никуда — это и обеспечивает идемпотентность отчёта.
    """
    sent: list[str] = []
    deleted: list[str] = []
    for line in stdout.splitlines():
        if not line:
            continue
        if line.startswith("*deleting"):
            path = line[len("*deleting"):].strip()
            if path:
                deleted.append(path.rstrip("/"))
            continue
        code, sep, path = line.partition(" ")
        if not sep or len(code) < 2:
            continue
        if code[0] in "<>ch":
            if code[1] == "d":                  # создание/изменение каталога — структурное
                continue
            cleaned = path.strip()
            if cleaned:
                sent.append(cleaned)
    return sent, deleted


def run_rsync(cmd: list[str]) -> RsyncOutcome:
    """Запустить rsync и разобрать итог. Сетевые/прочие ошибки → ненулевой код."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sent, deleted = parse_itemized(proc.stdout)
    return RsyncOutcome(
        rc=proc.returncode,
        sent=sent,
        deleted=deleted,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def _run_listing(endpoint: str, filters: list[str]) -> list[tuple[str, bool]] | None:
    """Запустить `--list-only` и разобрать вывод; None при ошибке запуска/листинга."""
    try:
        proc = subprocess.run(build_listing(endpoint, filters), capture_output=True, text=True)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return parse_listing(proc.stdout)


def remote_object_count(profile: Profile) -> int:
    """Число объектов в приёмнике (знаменатель доли delete-guard).

    Листинг ровно приёмника (`--list-only DEST/`, без фильтров — считаем всё на
    сервере). Недоступность/ошибка листинга → 0: тогда срабатывает только порог по
    количеству (безопасный откат, доля не учитывается).
    """
    items = _run_listing(_dest(profile.target_path), [])
    return 0 if items is None else len(items)


def source_files(profile: Profile) -> list[str]:
    """Файлы источника в области передачи (с учётом фильтров и авто-исключений).

    Единый с передачей источник истины: то, что rsync реально считает к отправке
    (а не отдельный матчер). Используется offload для определения области удаления.
    Каталоги не включаются. Ошибка листинга → пустой список.
    """
    items = _run_listing(_source(profile.source_path), filter_args(profile.exclude, profile.include))
    if items is None:
        return []
    return sorted(path for path, is_dir in items if not is_dir)


def delete_preflight(profile: Profile) -> DeletePlan:
    """Сухой прогон с `--delete` для подсчёта удаляемых на сервере объектов."""
    outcome = run_rsync(build_command(profile, dry_run=True, delete=True))
    return DeletePlan(to_delete=outcome.deleted, remote_total=remote_object_count(profile))
