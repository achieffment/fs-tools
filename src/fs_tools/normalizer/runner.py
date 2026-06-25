"""Точка входа режима нормализации: main(argv) + run(root).

Верхнеуровневые импорты намеренно лёгкие (без `Unidecode`), чтобы команда `fs-normalizer`
и диспетчер импортировались без extra `normalizer`. Тяжёлые модули (правила тянут
`Unidecode`) импортируются внутри `run`; при отсутствии пакета — понятное сообщение
в `stderr`, а не трассировка.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from ..shared.cli import choose_root, make_parser
from .cli_args import add_normalizer_argument

_DESCRIPTION = (
    "Нормализатор имён файлов и папок (рекурсивно). Без аргумента каталог выбирается "
    "интерактивно (диалог проводника на Windows и в WSL, диалог macOS, либо ввод пути "
    "в терминале на обычном Linux). Каталог можно задать аргументом — без диалога."
)
_HEADER = "Выберите каталог для нормализации"
_PROMPT = "Укажите каталог для нормализации."


def _build_parser() -> argparse.ArgumentParser:
    pars = make_parser(
        _DESCRIPTION,
        prog="fs-normalizer",
        path_help="Каталог для нормализации. Если не задан — выбирается интерактивно.",
    )
    add_normalizer_argument(pars)
    return pars


def run(root: Path, *, dry_run: bool = False) -> int:
    """Нормализует содержимое каталога. 0 — без реальных ошибок (безопасные конфликты
    входят сюда); 2 — часть os.rename упала с OSError. 1 — если режим недоступен
    (нет `Unidecode`): печатается понятное сообщение, а не трассировка.
    """
    try:
        FsNormalizer = importlib.import_module(".engine", __package__).FsNormalizer
        build_normalizer = importlib.import_module(".name", __package__).build_normalizer
        load_fs_ignore = importlib.import_module(".ignore", __package__).load_fs_ignore
        format_report = importlib.import_module(".report", __package__).format_report
        write_fs_log = importlib.import_module(".log", __package__).write_fs_log
    except ImportError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    fsnm = FsNormalizer(build_normalizer(), load_fs_ignore(root))
    renamed, skipped = fsnm.apply(root, dry_run=dry_run)
    print(format_report(root, fsnm, renamed, skipped, dry_run=dry_run))
    mode = "dry-run" if dry_run else "production"
    actions = fsnm.planned if dry_run else fsnm.renames
    # Журнал — вторичный артефакт: план/переименования уже вычислены, поэтому сбой
    # записи не роняем трейсбеком, а лишь предупреждаем. На код возврата это не влияет.
    try:
        lpath = write_fs_log(root, actions, mode=mode)
        print(f"Журнал: {lpath}")
    except OSError as exc:
        sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
    return 2 if fsnm.errlist else 0


def main(argv: list[str] | None = None) -> int:
    """0 — прогон без реальных ошибок; 1 — каталог не выбран/не найден/не каталог
    (или режим недоступен без `Unidecode`); 2 — часть os.rename упала с OSError.
    """
    args = _build_parser().parse_args(argv)
    root = choose_root(args.path, header=_HEADER, prompt=_PROMPT)
    if root is None:
        return 1
    return run(root, dry_run=args.dry_run)
