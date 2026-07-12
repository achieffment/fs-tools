"""Точка входа режима проверки: main(argv) + run(root)."""
from __future__ import annotations

import sys
from pathlib import Path

from ..shared.cli import ModeMainSpec, run_mode_main
from .engine import FsChecker
from .log import write_fs_log
from .notify import send_webhook
from .report import format_report
from .rule import FsRuleError, load_fs_rule

_DESCRIPTION = (
    "Проверка наличия папок и файлов по правилам .fs-chk (рекурсивно). Без аргумента "
    "каталог выбирается интерактивно (диалог проводника на Windows и в WSL, диалог "
    "macOS, либо ввод пути в терминале на обычном Linux). Каталог можно задать "
    "аргументом — без диалога."
)
_HEADER = "Выберите каталог для проверки"
_PROMPT = "Укажите каталог для проверки."
_MAIN_SPEC = ModeMainSpec(
    description=_DESCRIPTION,
    prog="fs-checker",
    path_help="Каталог для проверки. Если не задан — выбирается интерактивно.",
    header=_HEADER,
    prompt=_PROMPT,
)


def run(root: Path) -> int:
    """0 — нарушений нет; 1 — нет/нечитаем .fs-chk; 2 — найдены отсутствующие пути.

    Единственная запись на диск — `.fs-log` (структура проверяемого каталога не
    меняется). Веб-хук о нарушениях — fire-and-forget, на код возврата не влияет.
    """
    try:
        fs_rule = load_fs_rule(root)
    except FsRuleError as exc:
        sys.stderr.write(f"Ошибка: {exc}\n")
        return 1
    fsch = FsChecker(fs_rule).check(root)
    print(format_report(root, fsch))
    # Журнал — вторичный артефакт: проверка уже выполнена, поэтому сбой записи
    # не роняем трейсбеком, а лишь предупреждаем (на код возврата не влияет).
    try:
        lpath = write_fs_log(root, fsch.missing, tool="checker", mode="production")
        print(f"Журнал: {lpath}")
    except OSError as exc:
        sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
    if fsch.missing:
        # Уведомление о невалидной структуре: текст лишь сигнализирует о проблеме,
        # детали — в .fs-log. Fire-and-forget, ошибки/таймаут не влияют на прогон.
        send_webhook("fs-checker - выполнен с ошибкой.")
    return 2 if fsch.missing else 0


def main(argv: list[str] | None = None) -> int:
    """0 — нарушений нет; 1 — ошибка запуска (каталог/файл правил); 2 — отсутствующие пути."""
    return run_mode_main(
        argv=argv,
        spec=_MAIN_SPEC,
        run=run,
    )
