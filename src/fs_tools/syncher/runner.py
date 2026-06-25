"""Точка входа режима синхронизации: main(argv) + run(root, args).

Коды возврата: 0 — успех (включая «изменений нет»); 1 — ошибка запуска (нет каталога/
конфига, ошибка валидации, нет rsync или ssh для SSH-цели); 2 — rsync/offload
завершились ошибкой; 3 — остановлено delete-guard. Итог прогона = наихудший код среди
профилей по шкале 0 < 2 < 3. Без аргумента каталог выбирается интерактивно (диалог
проводника на Windows и в WSL, диалог macOS, либо ввод пути в терминале на Linux).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..shared.cli import make_parser, resolve_root
from ..shared.picker import pick_directory
from .cli_args import add_sync_argument
from .config import Config, ConfigError, Profile, is_ssh_target, load_config
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

_DESCRIPTION = (
    "Односторонняя синхронизация локального каталога с сервером (ПК → сервер) через "
    "rsync. Состав задаётся в .fs-sync.toml в корне каталога. Без аргумента каталог "
    "выбирается интерактивно (диалог проводника на Windows и в WSL, диалог macOS, "
    "либо ввод пути в терминале на Linux). Каталог можно задать аргументом — без диалога."
)
_HEADER = "Выберите каталог для синхронизации"
_PROMPT = "Укажите каталог для синхронизации."


def _build_parser() -> argparse.ArgumentParser:
    pars = make_parser(
        _DESCRIPTION,
        prog="fs-syncher",
        path_help="Каталог для синхронизации. Если не задан — выбирается интерактивно.",
    )
    add_sync_argument(pars)
    return pars


def _select_roll(config: Config, names: list[str] | None) -> list[Profile]:
    """Профили к запуску: по --profile или все. Неизвестное имя → ConfigError."""
    if not names:
        return list(config.roll)
    selected: list[Profile] = []
    for name in names:
        profile = config.by_name(name)
        if profile is None:
            raise ConfigError(f"профиль «{name}» не найден в конфиге")
        selected.append(profile)
    return selected


def _run_sync(profile: Profile, *, dry_run: bool, force: bool) -> ProfileReport:
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
    errlist = [outcome.stderr.strip()] if (not outcome.ok and outcome.stderr.strip()) else []
    return ProfileReport(
        name=profile.name,
        kind=profile.kind,
        code=0 if outcome.ok else 2,
        sent=outcome.sent,
        deleted=outcome.deleted,
        errlist=errlist,
    )


def _run_backup(profile: Profile, *, dry_run: bool) -> ProfileReport:
    result = run_offload(profile, dry_run=dry_run)
    return ProfileReport(
        name=profile.name,
        kind=profile.kind,
        code=result.rc,
        sent=result.sent,
        offload=result.offload,
        errlist=result.errlist,
    )


def _run_profile(profile: Profile, *, dry_run: bool, force: bool) -> ProfileReport:
    effective_dry = dry_run or profile.dry_run
    if profile.kind == "backup":
        report = _run_backup(profile, dry_run=effective_dry)
    else:
        report = _run_sync(profile, dry_run=effective_dry, force=force)
    report.dry_run = effective_dry
    return report


def run(root: Path, args: argparse.Namespace) -> int:
    """Прогнать профили в каталоге root; вернуть наихудший код (0 < 2 < 3).

    Загружает .fs-sync.toml, отбирает профили, проверяет наличие ssh для SSH-целей
    (ошибки запуска → 1), прогоняет профили последовательно, печатает отчёт, дописывает
    .fs-log и в production-прогоне шлёт веб-хук при наихудшем коде 2/3.
    """
    try:
        cfg = load_config(root)
        selected = _select_roll(cfg, args.profile)
    except ConfigError as exc:
        sys.stderr.write(f"Ошибка: {exc}\n")
        return 1

    if any(is_ssh_target(p.target_path) for p in selected) and not ssh_available():
        sys.stderr.write("Ошибка: для SSH-цели нужен ssh, но он не найден.\n")
        return 1

    any_dry = args.dry_run or any(p.dry_run for p in selected)
    print(format_header(root, [p.name for p in selected], any_dry))

    result: list[ProfileReport] = []
    actions: list[str] = []
    for profile in selected:
        report = _run_profile(
            profile,
            dry_run=args.dry_run,
            force=args.force_delete,
        )
        print(format_profile(report))
        actions = actions + report.actions()
        if report.blocked:
            actions.append(
                f"(КОНФЛИКТ) [{report.name}] остановлено delete-guard "
                f"(к удалению {len(report.deleted)})."
            )
        for err in report.errlist:
            actions.append(f"(ОШИБКА) [{report.name}] {err}")
        result.append(report)

    print(format_report(root, result))

    worst = max((r.code for r in result), default=0)

    is_dry = all(report.dry_run for report in result)
    mode = "dry-run" if is_dry else "production"
    try:
        write_fs_log(root, actions, tool="syncher", mode=mode)
    except OSError as exc:
        sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
    if (not is_dry) and worst in (2, 3):
        send_webhook("fs-syncher - выполнен с ошибкой.")

    return worst


def main(argv: list[str] | None = None) -> int:
    """0 — успех; 1 — ошибка запуска; 2 — ошибка rsync/offload; 3 — delete-guard."""
    args = _build_parser().parse_args(argv)

    # Аргумент-каталог минует диалог; иначе — интерактивный выбор.
    targ = args.path if args.path else pick_directory(_HEADER, _PROMPT)
    root = resolve_root(targ)
    if root is None:
        return 1

    if not rsync_available():
        sys.stderr.write("Ошибка: не найден rsync (установите rsync и повторите).\n")
        return 1

    return run(root, args)
