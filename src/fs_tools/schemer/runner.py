"""Точка входа режима проверки схемы: main(argv) + run(root)."""
from __future__ import annotations

import sys
from pathlib import Path

from ..shared.cli import ModeMainSpec, run_mode_main
from .config import SchemeConfigError, load_scheme_config
from .engine import FsSchemer
from .log import write_fs_log
from .notify import send_webhook
from .report import format_report, format_violation

_DESCRIPTION = (
    "Проверка структуры и контента базы знаний по декларативным группам fs-schm.toml "
    "(рекурсивно, read-only). Без аргумента каталог выбирается интерактивно (диалог "
    "проводника на Windows и в WSL, диалог macOS, либо ввод пути в терминале на "
    "обычном Linux). Каталог можно задать аргументом — без диалога."
)
_HEADER = "Выберите каталог для проверки схемы"
_PROMPT = "Укажите каталог для проверки схемы."
_MAIN_SPEC = ModeMainSpec(
    description=_DESCRIPTION,
    prog="fs-schemer",
    path_help="Каталог для проверки. Если не задан — выбирается интерактивно.",
    header=_HEADER,
    prompt=_PROMPT,
)


def run(root: Path) -> int:
    """0 — нарушений нет; 1 — нет/невалиден fs-schm.toml; 2 — найдены нарушения.

    Единственная запись на диск — `.fs-log` (проверяемое дерево не мутируется).
    Веб-хук о нарушениях — fire-and-forget, на код возврата не влияет.
    """
    try:
        config = load_scheme_config(root)
    except SchemeConfigError as exc:
        sys.stderr.write(f"Ошибка: {exc}\n")
        return 1
    fssm = FsSchemer(config).check(root)
    print(format_report(root, fssm))
    lines = [format_violation(vio) for vio in fssm.violations]
    # Журнал — вторичный артефакт: проверка уже выполнена, поэтому сбой записи
    # не роняем трейсбеком, а лишь предупреждаем (на код возврата не влияет).
    try:
        lpath = write_fs_log(root, lines, tool="schemer", mode="production")
        print(f"Журнал: {lpath}")
    except OSError as exc:
        sys.stderr.write(f"Не удалось записать журнал .fs-log: {exc}\n")
    if fssm.violations:
        # Уведомление о невалидной структуре: текст лишь сигнализирует о проблеме,
        # детали — в .fs-log. Fire-and-forget, ошибки/таймаут не влияют на прогон.
        send_webhook("fs-schemer - выполнен с ошибкой.")
    return 2 if fssm.violations else 0


def main(argv: list[str] | None = None) -> int:
    """0 — нарушений нет; 1 — ошибка запуска (каталог/конфиг); 2 — найдены нарушения."""
    return run_mode_main(
        argv=argv,
        spec=_MAIN_SPEC,
        run=run,
    )
