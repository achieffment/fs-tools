"""Общие CLI-аргументы режима нормализации.

Единый источник определения normalizer-флагов для `fs-normalizer` и диспетчера
`fs-tools`, чтобы набор аргументов и проброс в runner не расходились.
"""
from __future__ import annotations

import argparse


def add_normalizer_argument(pars: argparse.ArgumentParser) -> None:
    """Добавить флаги режима нормализации в переданный pars."""
    pars.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать план нормализации без переименования объектов.",
    )


def normalizer_argv_from_namespace(args: argparse.Namespace) -> list[str]:
    """Восстановить argv режима нормализации из флагов диспетчера."""
    argv: list[str] = [args.path] if args.path else []
    if args.dry_run:
        argv.append("--dry-run")
    return argv
