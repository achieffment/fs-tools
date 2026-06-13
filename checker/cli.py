"""CLI: разбор аргументов и сценарий запуска."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import FsChecker
from .log import write_fs_log
from .notify import send_webhook
from .picker import pick_directory
from .report import format_report
from .rule import FsRuleError, load_fs_rule


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Проверка наличия папок и файлов по правилам .fs-rule (рекурсивно). Без аргумента каталог выбирается интерактивно (диалог проводника на Windows и в WSL, диалог macOS, либо ввод пути в терминале на обычном Linux). Каталог можно задать аргументом — для запуска по таймеру (cron/планировщик) без диалога.")
    parser.add_argument(
        "path",
        nargs="?",
        help="Каталог для проверки. Если не задан — выбирается интерактивно.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """0 — нарушений нет; 1 — ошибка запуска; 2 — найдены отсутствующие пути."""
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
        # Уведомление о невалидной структуре: текст только сигнализирует о проблеме,
        # детали — в .fs-log. Fire-and-forget, ошибки/таймаут не влияют на прогон.
        send_webhook(
            f"fs-checker: в каталоге {root} отсутствуют пути ({len(result.missing)}). "
            "Подробности — в .fs-log."
        )
    return 2 if result.missing else 0
