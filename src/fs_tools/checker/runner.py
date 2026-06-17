"""Точка входа режима проверки: main(argv) + run(root)."""
from __future__ import annotations

import sys
from pathlib import Path

from ..shared.cli import make_parser, resolve_root
from ..shared.picker import pick_directory
from .engine import FsChecker
from .log import write_fs_log
from .notify import send_webhook
from .report import format_report
from .rule import FsRuleError, load_fs_rule

_DESCRIPTION = (
    "Проверка наличия папок и файлов по правилам .fs-check (рекурсивно). Без аргумента "
    "каталог выбирается интерактивно (диалог проводника на Windows и в WSL, диалог "
    "macOS, либо ввод пути в терминале на обычном Linux). Каталог можно задать "
    "аргументом — для запуска по таймеру (cron/планировщик) без диалога."
)
_TITLE = "Выберите каталог для проверки"
_PROMPT = "Укажите каталог для проверки."


def run(root: Path) -> int:
    """0 — нарушений нет; 1 — нет/нечитаем .fs-check; 2 — найдены отсутствующие пути.

    Единственная запись на диск — `.fs-log` (структура проверяемого каталога не
    меняется). Веб-хук о нарушениях — fire-and-forget, на код возврата не влияет.
    """
    try:
        fs_rule = load_fs_rule(root)
    except FsRuleError as exc:
        sys.stderr.write(f"Ошибка: {exc}\n")
        return 1
    result = FsChecker(fs_rule).check(root)
    print(format_report(root, result))
    if result.missing:
        # Журнал — вторичный артефакт: проверка уже выполнена, поэтому сбой записи
        # не роняем трейсбеком, а лишь предупреждаем (на код возврата не влияет).
        try:
            lpath = write_fs_log(root, result.missing)
            print(f"Журнал: {lpath}")
        except OSError as exc:
            sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
        # Уведомление о невалидной структуре: текст лишь сигнализирует о проблеме,
        # детали — в .fs-log. Fire-and-forget, ошибки/таймаут не влияют на прогон.
        send_webhook(
            f"fs-checker: в каталоге {root} отсутствуют пути ({len(result.missing)}). "
            "Подробности — в .fs-log."
        )
    return 2 if result.missing else 0


def main(argv: list[str] | None = None) -> int:
    """0 — нарушений нет; 1 — ошибка запуска (каталог/файл правил); 2 — отсутствующие пути."""
    parser = make_parser(_DESCRIPTION)
    args = parser.parse_args(argv)
    # Аргумент-каталог минует диалог (режим таймера); иначе — интерактивный выбор.
    targ = args.path if args.path else pick_directory(_TITLE, _PROMPT)
    root = resolve_root(targ)
    if root is None:
        return 1
    return run(root)
