"""Разворачивание префиксов правил по ФС и сбор отсутствующих путей.

Модель: префикс правила = множество УЖЕ существующих каталогов-якорей
(`Path.glob` разворачивает `*`/`**`/литералы), последний сегмент = обязательный
мандат. Нарушение — отсутствие мандата в найденном якоре. Если префикс не дал
якорей (литерал отсутствует, `*`/`**` ничего не нашли) — это не нарушение.

Негативы (`!`) прунят якори по ИМЕНИ каждой `*`/`**`-выбранной компоненты
(`_selected_names` + `Negation`), а не только по листу: так `_Archive` отсекается и
на промежуточных `*`-позициях. Литералы шаблона (в т.ч. записанный буквально
`_Archive` в `**/_Archive/*`) под прунинг НЕ попадают.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .rule import FsRule, Rule

# Метасимволы glob: сегмент с ними — подстановка (его компонента проверяется негативом).
_GLOB_META = ("*", "?", "[")


@dataclass
class CheckResult:
    """Итог проверки: отсортированные отсутствующие пути и счётчики для сводки."""

    missing: list[str]
    rules_checked: int
    anchors_found: int


def _is_hidden(rel: Path) -> bool:
    """Скрытый ли путь: любая компонента начинается с `.` (такие не обходим)."""
    return any(part.startswith(".") for part in rel.parts)


def _has_glob(segment: str) -> bool:
    return any(meta in segment for meta in _GLOB_META)


def _selected_names(prefix: tuple[str, ...], parts: tuple[str, ...]) -> list[str]:
    """Имена компонент якоря, выбранных подстановкой `*`/`**` — только их прунит негатив.

    Литералы (включая `_Archive`, записанный буквально) сюда НЕ попадают. Поддержан
    один `**` на правило: его захват выравнивается на «середину» компонент пути, а
    `*`-сегменты слева/справа — позиционно.
    """
    if "**" not in prefix:  # 1:1 выравнивание сегмент <-> компонента
        names = []
        for seg, part in zip(prefix, parts):
            if _has_glob(seg):
                names.append(part)
        return names
    ix = prefix.index("**")
    lf, rt = prefix[:ix], prefix[ix + 1:]
    if rt:
        md = parts[len(lf):len(parts) - len(rt)]
    else:
        md = parts[len(lf):]
    names = list(md)  # всё, что поймал `**`, — это подстановка
    names_left = []
    for seg, part in zip(lf, parts):
        if _has_glob(seg):
            names_left.append(part)
    names = names + names_left
    if rt:
        rtail = parts[len(parts) - len(rt):]
        names_right = []
        for seg, part in zip(rt, rtail):
            if _has_glob(seg):
                names_right.append(part)
        names = names + names_right
    return names


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
            if any(
                self._negation.is_pruned(name)
                for name in _selected_names(rule.anchors, rel.parts)
            ):
                continue
            anccnt = anccnt + 1
            target = adir / rule.require
            result = target.is_dir() if rule.dirflag else target.exists()
            if not result:
                missing.add((rel / rule.require).as_posix())
        return anccnt
