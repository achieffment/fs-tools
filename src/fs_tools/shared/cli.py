"""Общий разбор аргументов CLI и валидация выбранного каталога.

Используется обоими `runner.py` и диспетчером `fs_tools.cli`, чтобы разбор
опционального позиционного `path` и приведение пути к корню не дублировались.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PATH_HELP = "Каталог для обработки. Если не задан — выбирается интерактивно."


def make_parser(description: str) -> argparse.ArgumentParser:
    """Парсер с единственным опциональным позиционным `path` (`nargs="?"`)."""
    parser = argparse.ArgumentParser(description=description)
    add_path_argument(parser)
    return parser


def add_path_argument(parser: argparse.ArgumentParser) -> None:
    """Добавляет опциональный позиционный `path` (общий и для подпарсеров диспетчера)."""
    parser.add_argument("path", nargs="?", help=_PATH_HELP)


def resolve_root(targ: str | None) -> Path | None:
    """Приводит выбранный путь к существующему каталогу-корню.

    Инкапсулирует `expanduser`, `resolve(strict=True)`, `is_dir()` и печать ошибок в
    `stderr`. Возвращает `Path` либо `None` (тогда вызывающий завершает с кодом 1):
    путь пуст / не найден / не каталог.
    """
    if not targ:
        sys.stderr.write("Каталог не выбран.\n")
        return None
    root = Path(targ).expanduser()
    try:
        root = root.resolve(strict=True)
    except OSError:
        sys.stderr.write(f"Ошибка: каталог не найден: {targ}\n")
        return None
    if not root.is_dir():
        sys.stderr.write(f"Ошибка: каталог не является каталогом: {root}\n")
        return None
    return root
