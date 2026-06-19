"""Общий разбор аргументов CLI и валидация выбранного каталога.

Используется всеми `runner.py` и диспетчером `fs_tools.cli`, чтобы разбор
опционального позиционного `path` и приведение пути к корню не дублировались.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .picker import pick_directory

_PATH_HELP = "Каталог для обработки. Если не задан — выбирается интерактивно."


@dataclass(frozen=True)
class ModeMainSpec:
    """Параметры шаблона `run_mode_main` для конкретного CLI-режима."""

    description: str
    prog: str
    path_help: str
    header: str
    prompt: str


def make_parser(
    description: str,
    *,
    prog: str | None = None,
    path_help: str = _PATH_HELP,
) -> argparse.ArgumentParser:
    """Парсер с опциональным `path` и настраиваемыми `prog`/подсказкой пути."""
    pars = argparse.ArgumentParser(prog=prog, description=description)
    add_path_argument(pars, path_help)
    return pars


def add_path_argument(pars: argparse.ArgumentParser, help_text: str = _PATH_HELP) -> None:
    """Добавляет опциональный позиционный `path` (общий и для подпарсеров диспетчера).

    `help_text` переопределяется режимами с отличающейся подсказкой для пользователя
    (например, чтобы явно указать интерактивный выбор каталога).
    """
    pars.add_argument("path", nargs="?", help=help_text)


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


def choose_root(
    path: str | None,
    *,
    header: str,
    prompt: str,
) -> Path | None:
    """Вернуть валидный корень: аргумент-каталог или интерактивный выбор."""
    targ = path if path else pick_directory(header, prompt)
    return resolve_root(targ)


def run_mode_main(
    *,
    argv: list[str] | None,
    spec: ModeMainSpec,
    run: Callable[[Path], int],
) -> int:
    """Общий шаблон main(): парсинг path, выбор корня и запуск режима."""
    pars = make_parser(spec.description, prog=spec.prog, path_help=spec.path_help)
    args = pars.parse_args(argv)
    root = choose_root(args.path, header=spec.header, prompt=spec.prompt)
    if root is None:
        return 1
    return run(root)
