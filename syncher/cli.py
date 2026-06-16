"""CLI: разбор аргументов, последовательный прогон профилей, коды возврата.

Коды возврата: 0 — успех (включая «изменений нет»); 1 — ошибка запуска (нет каталога/
конфига, ошибка валидации, нет rsync или ssh для SSH-цели); 2 — rsync/offload
завершились ошибкой; 3 — остановлено delete-guard. Итог прогона = наихудший код среди
профилей по шкале 0 < 2 < 3.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config, ConfigError, Profile, is_ssh_remote, load_config
from .log import write_fs_log
from .notify import send_webhook
from .offload import run_offload
from .report import ProfileReport, format_header, format_profile, format_report
from .rsync import (
    build_command,
    delete_preflight,
    rsync_available,
    run_rsync,
    ssh_available,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sync_fs",
        description=(
            "Односторонняя синхронизация локального каталога с сервером (ПК → сервер) "
            "через rsync. Состав задаётся в .fs-sync.toml в корне каталога. Каталог — "
            "позиционный аргумент (для cron/планировщика); без него берётся текущий."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Корень синхронизации с .fs-sync.toml. По умолчанию — текущий каталог.",
    )
    parser.add_argument(
        "--profile",
        action="append",
        metavar="NAME",
        help="Запустить только указанный профиль (флаг повторяемый).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Явно запустить все профили (поведение по умолчанию).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать план без передачи/удаления (приоритетнее dry_run профиля).",
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="Снять защиту от массового удаления (delete-guard).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Печатать подробный вывод rsync.",
    )
    return parser.parse_args(argv)


def _select_profiles(config: Config, names: list[str] | None) -> list[Profile]:
    """Профили к запуску: по --profile или все. Неизвестное имя → ConfigError."""
    if not names:
        return list(config.profiles)
    selected: list[Profile] = []
    for name in names:
        profile = config.by_name(name)
        if profile is None:
            raise ConfigError(f"профиль «{name}» не найден в конфиге")
        selected.append(profile)
    return selected


def _run_sync(profile: Profile, *, dry_run: bool, force: bool, verbose: bool) -> ProfileReport:
    do_delete = profile.delete
    if do_delete and not dry_run and not (force or profile.force_delete):
        plan = delete_preflight(profile)
        if plan.blocked(profile.delete_threshold, profile.delete_threshold_pct):
            return ProfileReport(
                name=profile.name,
                kind=profile.kind,
                code=3,
                deleted=plan.to_delete,
                blocked=True,
            )
    outcome = run_rsync(build_command(profile, dry_run=dry_run, delete=do_delete))
    if verbose and outcome.stdout:
        print(outcome.stdout)
    errors = [outcome.stderr.strip()] if (not outcome.ok and outcome.stderr.strip()) else []
    return ProfileReport(
        name=profile.name,
        kind=profile.kind,
        code=0 if outcome.ok else 2,
        sent=outcome.sent,
        deleted=outcome.deleted,
        errors=errors,
    )


def _run_backup(profile: Profile, *, dry_run: bool) -> ProfileReport:
    result = run_offload(profile, dry_run=dry_run)
    return ProfileReport(
        name=profile.name,
        kind=profile.kind,
        code=result.returncode,
        sent=result.sent,
        offloaded=result.offloaded,
        errors=result.errors,
    )


def _run_profile(profile: Profile, *, dry_run: bool, force: bool, verbose: bool) -> ProfileReport:
    effective_dry = dry_run or profile.dry_run
    if profile.kind == "backup":
        return _run_backup(profile, dry_run=effective_dry)
    return _run_sync(profile, dry_run=effective_dry, force=force, verbose=verbose)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    target = args.path if args.path else "."
    root = Path(target).expanduser()
    try:
        root = root.resolve(strict=True)
    except OSError:
        sys.stderr.write(f"Ошибка: каталог не найден: {target}\n")
        return 1
    if not root.is_dir():
        sys.stderr.write(f"Ошибка: путь не является каталогом: {root}\n")
        return 1

    if not rsync_available():
        sys.stderr.write("Ошибка: не найден rsync (установите rsync и повторите).\n")
        return 1

    try:
        config = load_config(root)
        selected = _select_profiles(config, args.profile)
    except ConfigError as exc:
        sys.stderr.write(f"Ошибка: {exc}\n")
        return 1

    if any(is_ssh_remote(p.remote_root) for p in selected) and not ssh_available():
        sys.stderr.write("Ошибка: для SSH-цели нужен ssh, но он не найден.\n")
        return 1

    print(format_header(root, [p.name for p in selected], args.dry_run))

    reports: list[ProfileReport] = []
    for profile in selected:
        report = _run_profile(
            profile,
            dry_run=args.dry_run,
            force=args.force_delete,
            verbose=args.verbose,
        )
        print(format_profile(report))
        for err in report.errors:
            sys.stderr.write(f"[{report.name}] {err}\n")
        reports.append(report)

    print(format_report(root, reports))

    worst = max((r.code for r in reports), default=0)

    if not args.dry_run:
        operations = [op for report in reports for op in report.operations()]
        try:
            write_fs_log(root, operations)
        except OSError as exc:
            sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
        if worst in (2, 3):
            send_webhook(
                f"fs-syncher: прогон в {root} завершился с кодом {worst}. "
                "Подробности — в .fs-log и выводе."
            )

    return worst
