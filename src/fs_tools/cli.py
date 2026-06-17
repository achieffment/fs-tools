"""Диспетчер `fs-tools <normalize|check|sync> [КАТАЛОГ] [ФЛАГИ]`.

Подкоманды соответствуют трём режимам. Runner выбранного режима импортируется
лениво — внутри обработчика подкоманды, чтобы `fs-tools --help` и доступный режим
работали даже без extra другого режима (например, без `Unidecode` для нормализации
или без `requests`/`python-dotenv` для синхронизации).
"""
from __future__ import annotations

import argparse

from .shared.cli import add_path_argument


def _add_sync_flags(parser: argparse.ArgumentParser) -> None:
    """Флаги режима синхронизации в подпарсере (диспетчер обязан их пробросить)."""
    parser.add_argument("--profile", action="append", metavar="NAME")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-delete", action="store_true")
    parser.add_argument("--verbose", action="store_true")


def _sync_argv(args: argparse.Namespace) -> list[str]:
    """Восстановить argv режима синхронизации из разобранных диспетчером флагов."""
    argv: list[str] = [args.path] if args.path else []
    for name in args.profile or []:
        argv += ["--profile", name]
    if args.all:
        argv.append("--all")
    if args.dry_run:
        argv.append("--dry-run")
    if args.force_delete:
        argv.append("--force-delete")
    if args.verbose:
        argv.append("--verbose")
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fs-tools",
        description=(
            "Кросс-платформенные операции с файловой системой: нормализация имён "
            "(normalize), проверка наличия путей по правилам (check) и односторонняя "
            "синхронизация каталога с сервером через rsync (sync)."
        ),
    )
    sub = parser.add_subparsers(
        dest="mode", required=True, metavar="<normalize|check|sync>"
    )

    p_fsnm = sub.add_parser("normalize", help="нормализовать имена файлов и папок")
    add_path_argument(p_fsnm)
    p_fsch = sub.add_parser("check", help="проверить наличие путей по .fs-check")
    add_path_argument(p_fsch)
    p_fssy = sub.add_parser("sync", help="синхронизировать каталог с сервером (rsync)")
    add_path_argument(p_fssy, "Каталог для синхронизации. Если не задан — текущий рабочий каталог.")
    _add_sync_flags(p_fssy)

    args = parser.parse_args(argv)

    # Ленивый импорт режима: тянем только то, что нужно выбранной подкоманде.
    if args.mode == "normalize":
        from .normalizer.runner import main as run_mode

        return run_mode([args.path] if args.path else [])
    if args.mode == "check":
        from .checker.runner import main as run_mode

        return run_mode([args.path] if args.path else [])
    from .syncher.runner import main as run_sync

    return run_sync(_sync_argv(args))
