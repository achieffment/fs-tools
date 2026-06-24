"""Разворачивание префиксов правил по ФС и сбор отсутствующих путей.

Модель: префикс правила = множество УЖЕ существующих каталогов-якорей
(`Path.glob` разворачивает `*`/`**`/литералы), последний сегмент = обязательный
мандат. Нарушение — отсутствие мандата в найденном якоре. Если префикс не дал
якорей (литерал отсутствует, `*`/`**` ничего не нашли) — это не нарушение.

Негативы (`!`) применяются единым ordered pathspec-каналом к относительным путям
якорей и мандатов (`anchor/require`). В checker это всегда исключение из проверки:
если совпало — кандидат пропускается.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .rule import FsRule, Rule


@dataclass
class CheckResult:
    """Итог проверки: отсортированные отсутствующие пути и счётчики для сводки."""

    missing: list[str]
    rules_checked: int
    anchors_found: int


def _is_hidden(rel: Path) -> bool:
    """Скрытый ли путь: любая компонента начинается с `.` (такие не обходим)."""
    return any(part.startswith(".") for part in rel.parts)


class FsChecker:
    """Проверка структуры по правилам `.fs-check` (read-only)."""

    def __init__(self, fs_rule: FsRule):
        self._rules = fs_rule.rules
        self._negation = fs_rule.negation

    def check(self, root: Path) -> CheckResult:
        """Разворачивает все правила от `root`, собирает отсутствующие пути (дедуп+сорт)."""
        missing: set[str] = set()
        anchors = 0
        for rule in self._rules:
            anchors = anchors + self._check_rule(root, rule, missing)
        return CheckResult(
            missing=sorted(missing),
            rules_checked=len(self._rules),
            anchors_found=anchors,
        )

    def _check_rule(self, root: Path, rule: Rule, missing: set[str]) -> int:
        """Разворачивает один префикс и проверяет мандат. Возвращает число якорей-кандидатов."""
        # Пустой префикс (правило из одного сегмента) => единственный якорь — сам root.
        # root.glob(".") НЕДОПУСТИМ (ValueError на Python 3.13+/3.14), поэтому особый случай.
        anchors: Iterable[Path] = [root] if not rule.anchors else root.glob("/".join(rule.anchors))
        anccnt = 0
        for adir in anchors:
            if not adir.is_dir():
                continue
            rel = adir.relative_to(root)
            if rel.parts and _is_hidden(rel):
                continue
            if self._negation.is_pruned_path(rel, is_dir=True):
                continue
            target_rel = rel / rule.require
            if self._negation.is_pruned_path(target_rel, is_dir=False):
                continue
            if self._negation.is_pruned_path(target_rel, is_dir=True):
                continue
            anccnt = anccnt + 1
            target = adir / rule.require
            result = target.is_dir() if rule.dirflag else target.exists()
            if not result:
                missing.add((rel / rule.require).as_posix())
        return anccnt
