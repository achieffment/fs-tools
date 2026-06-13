"""CLI: разбор аргументов и сценарий запуска."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .filesystem import FilesystemNormalizer
from .ignore import load_fs_ignore
from .log import write_fs_log
from .name import build_normalizer
from .picker import pick_directory


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Нормализатор имён файлов и папок (рекурсивно). Без аргумента каталог выбирается интерактивно (диалог проводника на Windows и в WSL, диалог macOS, либо ввод пути в терминале на обычном Linux). Каталог можно задать аргументом — для запуска по таймеру (cron/планировщик) без диалога.")
    parser.add_argument(
        "path",
        nargs="?",
        help="Каталог для нормализации. Если не задан — выбирается интерактивно.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """0 — прогон завершён без реальных ошибок (безопасные пропуски-конфликты входят
    сюда); 1 — ошибка запуска (каталог не выбран/не найден/не каталог); 2 — прогон
    завершён, но часть os.rename упала с OSError.
    """
    args = _parse_args(argv)
    # Аргумент-каталог минует диалог (режим таймера); иначе — интерактивный выбор.
    targ = args.path if args.path else pick_directory()
    if not targ:
        sys.stderr.write("Каталог не выбран.\n")
        return 1
    root = Path(targ).expanduser()
    try:
        root = root.resolve(strict=True)
    except OSError:
        sys.stderr.write(f"Ошибка: каталог не найден: {targ}\n")
        return 1
    if not root.is_dir():
        sys.stderr.write(f"Ошибка: каталог не является каталогом: {root}\n")
        return 1
    fsnm = FilesystemNormalizer(build_normalizer(), load_fs_ignore(root))
    print(f"Каталог: {root}")
    renamed, skipped = fsnm.apply(root)
    print(
        f"Готово. Переименовано: {renamed}, пропущено: {skipped} "
        f"(конфликты: {fsnm.conflicts}, ошибки: {len(fsnm.errors)})."
    )
    # Журнал — вторичный артефакт: переименования уже выполнены, поэтому сбой записи
    # не роняем трейсбеком, а лишь предупреждаем (в духе остальной обработки ошибок).
    # На код возврата сбой журнала не влияет.
    try:
        lpath = write_fs_log(root, fsnm.renames)
        print(f"Журнал: {lpath}")
    except OSError as exc:
        sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
    # Код возврата: 2 — прогон завершён, но часть os.rename упала с OSError (реальный
    # сбой). Безопасные пропуски-конфликты на код не влияют (остаются 0).
    return 2 if fsnm.errors else 0
