"""Общие CLI-аргументы режима синхронизации.

Единый источник определения sync-флагов для `fs-syncher` и диспетчера `fs-tools`,
чтобы набор аргументов и проброс в runner не расходились.
"""
from __future__ import annotations

import argparse


def add_sync_argument(pars: argparse.ArgumentParser) -> None:
    """Добавить флаги режима синхронизации в переданный pars."""
    pars.add_argument(
        "--profile",
        action="append",
        metavar="NAME",
        help="Запустить только указанный профиль (флаг повторяемый).",
    )
    pars.add_argument(
        "--all",
        action="store_true",
        help="Явно запустить все профили (поведение по умолчанию).",
    )
    pars.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать план без передачи/удаления (приоритетнее dry_run профиля).",
    )
    pars.add_argument(
        "--force-delete",
        action="store_true",
        help="Снять защиту от массового удаления (delete-guard).",
    )
    pars.add_argument(
        "--verbose",
        action="store_true",
        help="Печатать подробный вывод rsync.",
    )


def sync_argv_from_namespace(args: argparse.Namespace) -> list[str]:
    """Восстановить argv режима синхронизации из разобранных диспетчером флагов."""
    argv: list[str] = [args.path] if args.path else []
    for name in args.profile or []:
        argv = argv + ["--profile", name]
    if args.all:
        argv.append("--all")
    if args.dry_run:
        argv.append("--dry-run")
    if args.force_delete:
        argv.append("--force-delete")
    if args.verbose:
        argv.append("--verbose")
    return argv
