"""Точка входа режима нормализации: main(argv) + run(root).

Верхнеуровневые импорты намеренно лёгкие (без `Unidecode`), чтобы команда `fs-normalizer`
и диспетчер импортировались без extra `normalizer`. Тяжёлые модули (правила тянут
`Unidecode`) импортируются внутри `run`; при отсутствии пакета — понятное сообщение
в `stderr`, а не трассировка.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ..shared.cli import make_parser, resolve_root
from ..shared.picker import pick_directory

_DESCRIPTION = (
    "Нормализатор имён файлов и папок (рекурсивно). Без аргумента каталог выбирается "
    "интерактивно (диалог проводника на Windows и в WSL, диалог macOS, либо ввод пути "
    "в терминале на обычном Linux). Каталог можно задать аргументом — для запуска по "
    "таймеру (cron/планировщик) без диалога."
)
_HEADER = "Выберите каталог для нормализации"
_PROMPT = "Укажите каталог для нормализации."


def run(root: Path) -> int:
    """Нормализует содержимое каталога. 0 — без реальных ошибок (безопасные конфликты
    входят сюда); 2 — часть os.rename упала с OSError. 1 — если режим недоступен
    (нет `Unidecode`): печатается понятное сообщение, а не трассировка.
    """
    try:
        from .engine import FsNormalizer
        from .ignore import load_fs_ignore
        from .log import write_fs_log
        from .name import build_normalizer
    except ImportError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    fsnm = FsNormalizer(build_normalizer(), load_fs_ignore(root))
    print(f"Каталог: {root}")
    renamed, skipped = fsnm.apply(root)
    print(
        f"Готово. Переименовано: {renamed}, пропущено: {skipped} "
        f"(конфликты: {fsnm.conflicts}, ошибки: {len(fsnm.errors)})."
    )
    # Журнал — вторичный артефакт: переименования уже выполнены, поэтому сбой записи
    # не роняем трейсбеком, а лишь предупреждаем. На код возврата это не влияет.
    try:
        lpath = write_fs_log(root, fsnm.renames)
        print(f"Журнал: {lpath}")
    except OSError as exc:
        sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
    return 2 if fsnm.errors else 0


def main(argv: list[str] | None = None) -> int:
    """0 — прогон без реальных ошибок; 1 — каталог не выбран/не найден/не каталог
    (или режим недоступен без `Unidecode`); 2 — часть os.rename упала с OSError.
    """
    parser = make_parser(_DESCRIPTION)
    args = parser.parse_args(argv)
    # Аргумент-каталог минует диалог (режим таймера); иначе — интерактивный выбор.
    targ = args.path if args.path else pick_directory(_HEADER, _PROMPT)
    root = resolve_root(targ)
    if root is None:
        return 1
    return run(root)
