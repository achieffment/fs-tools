"""Диспетчер `fs-tools <normalize|check|sync|scheme> [КАТАЛОГ] [ФЛАГИ]`.

Подкоманды соответствуют четырём режимам. Runner выбранного режима импортируется
лениво — внутри обработчика подкоманды, чтобы `fs-tools --help` и доступный режим
работали даже без extra другого режима (например, без `Unidecode` для нормализации
или без `requests`/`python-dotenv` для синхронизации/проверки схемы).
"""
from __future__ import annotations

import argparse
import importlib
from typing import Callable, cast

from .shared.cli import add_path_argument


def main(argv: list[str] | None = None) -> int:
    """Разобрать `fs-tools` CLI и вызвать runner выбранного режима."""
    # Normalizer-флаги объявляются через общий модуль, чтобы не дублировать контракт CLI.
    map_norm_argument = importlib.import_module(".normalizer.cli_args", __package__)
    add_norm_argument = map_norm_argument.add_normalizer_argument
    norm_argv_from_namespace = map_norm_argument.normalizer_argv_from_namespace

    # Sync-флаги объявляются через общий модуль, чтобы не дублировать контракт CLI.
    map_sych_argument = importlib.import_module(".syncher.cli_args", __package__)
    add_sync_argument = map_sych_argument.add_sync_argument
    sync_argv_from_namespace = map_sych_argument.sync_argv_from_namespace

    pars = argparse.ArgumentParser(
        prog="fs-tools",
        description=(
            "Кросс-платформенные операции с файловой системой: нормализация имён "
            "(normalize), проверка наличия путей по правилам (check), односторонняя "
            "синхронизация каталога с сервером через rsync (sync) и проверка "
            "структуры/контента базы знаний по .fs-sch.toml (scheme)."
        ),
    )
    sub = pars.add_subparsers(
        dest="mode", required=True, metavar="<normalize|check|sync|scheme>"
    )

    p_fsnm = sub.add_parser("normalize", help="нормализовать имена файлов и папок")
    add_path_argument(p_fsnm)
    add_norm_argument(p_fsnm)

    p_fsch = sub.add_parser("check", help="проверить наличие путей по .fs-chk")
    add_path_argument(p_fsch)

    p_fssy = sub.add_parser("sync", help="синхронизировать каталог с сервером (rsync)")
    add_path_argument(p_fssy)
    add_sync_argument(p_fssy)

    p_fssm = sub.add_parser("scheme", help="проверить структуру/контент по .fs-sch.toml")
    add_path_argument(p_fssm)

    # Ленивый импорт режима: тянем только то, что нужно выбранной подкоманде.
    args = pars.parse_args(argv)
    if args.mode == "normalize":
        run_mode = cast(
            Callable[[list[str] | None], int],
            importlib.import_module(".normalizer.runner", __package__).main,
        )
        return run_mode(norm_argv_from_namespace(args))
    if args.mode == "check":
        run_mode = cast(
            Callable[[list[str] | None], int],
            importlib.import_module(".checker.runner", __package__).main,
        )
        return run_mode([args.path] if args.path else [])
    if args.mode == "sync":
        run_mode = cast(
            Callable[[list[str] | None], int],
            importlib.import_module(".syncher.runner", __package__).main,
        )
        return run_mode(sync_argv_from_namespace(args))
    if args.mode == "scheme":
        run_mode = cast(
            Callable[[list[str] | None], int],
            importlib.import_module(".schemer.runner", __package__).main,
        )
        return run_mode([args.path] if args.path else [])
    return 1
