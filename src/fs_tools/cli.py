"""Диспетчер `fs-tools <normalize|check> [КАТАЛОГ]`.

Подкоманды соответствуют двум режимам. Runner выбранного режима импортируется
лениво — внутри обработчика подкоманды, чтобы `fs-tools --help` и доступный режим
работали даже без extra другого режима (например, без `Unidecode` для нормализации).
"""
from __future__ import annotations

import argparse

from .shared.cli import add_path_argument


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fs-tools",
        description=(
            "Кросс-платформенные операции с файловой системой: нормализация имён "
            "(normalize) и проверка наличия путей по правилам (check)."
        ),
    )
    sub = parser.add_subparsers(dest="mode", required=True, metavar="<normalize|check>")

    p_norm = sub.add_parser("normalize", help="нормализовать имена файлов и папок")
    add_path_argument(p_norm)
    p_check = sub.add_parser("check", help="проверить наличие путей по .fs-check")
    add_path_argument(p_check)

    args = parser.parse_args(argv)

    # Ленивый импорт режима: тянем только то, что нужно выбранной подкоманде.
    mode_argv = [args.path] if args.path else []
    if args.mode == "normalize":
        from .normalizer.runner import main as run_mode
    else:
        from .checker.runner import main as run_mode
    return run_mode(mode_argv)
