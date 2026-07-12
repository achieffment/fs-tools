"""Разворачивание префиксов правил по ФС и сбор отсутствующих путей.

Модель: префикс правила = множество УЖЕ существующих каталогов-якорей, последний
сегмент = обязательный мандат. Префиксы без `**` (или с несколькими `**`)
разворачивает `Path.glob`; префикс с ровно одним `**` разворачивается собственным
scandir-обходом (`_expand_anchors_recursive`, не разыменовывает symlink) — быстрее
на больших деревьях. Обе стратегии дают одинаковый итоговый набор якорей: скрытые
каталоги `Path.glob` тоже находит, но `_check_group` отбрасывает их через
`_is_hidden` до проверки мандата. Нарушение — отсутствие мандата в найденном
якоре. Если префикс не дал якорей (литерал отсутствует, `*`/`**` ничего не
нашли) — это не нарушение. Но если `**`-обход не смог просканировать каталог
(`OSError`: нет прав, гонка удаления) — это техническая ошибка, а не «нет
совпадений»: фиксируется отдельно в `CheckResult.errlist`, не смешивается с
`missing` и не проглатывается молча.

Негативы (`!`) применяются единым ordered pathspec-каналом к относительным путям
якорей и мандатов (`anchor/require`). В checker это всегда исключение из проверки:
если совпало — кандидат пропускается.
"""
from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .rule import FsRule, Rule


@dataclass
class CheckResult:
    """Итог проверки: отсортированные отсутствующие пути, ошибки чтения и счётчики.

    `errlist` — каталоги, которые не удалось просканировать (`OSError`: нет прав,
    гонка удаления и т.п.) при разворачивании префиксов с `**`. Такой сбой —
    техническая ошибка, а не «якорь не найден» (последнее — штатный, не-нарушающий
    случай по документированной семантике `.fs-chk`), поэтому не смешивается с
    `missing` и не проглатывается молча.
    """

    missing: list[str]
    rules_checked: int
    anchors_found: int
    errlist: list[str]


@dataclass
class _ScanState:
    """Мутируемое состояние одного прогона `check()`: кэш якорей + сырые ошибки сканирования.

    `errlist` хранит пары (абсолютный путь, текст исключения) — релятивизация к `root`
    откладывается до `check()`, чтобы не тащить `root` через весь рекурсивный обход
    только ради форматирования сообщения об ошибке (лишний параметр в горячем пути).
    """

    cache: dict[tuple[str, ...], tuple[Path, ...]]
    errlist: set[tuple[Path, str]]


def _is_hidden(rel: Path) -> bool:
    """Скрытый ли путь: любая компонента начинается с `.` (такие не обходим)."""
    return any(part.startswith(".") for part in rel.parts)


class FsChecker:
    """Проверка структуры по правилам `.fs-chk` (read-only)."""

    def __init__(self, fs_rule: FsRule):
        self._rules = fs_rule.rules
        self._negation = fs_rule.negation

    def check(self, root: Path) -> CheckResult:
        """Разворачивает все правила от `root`, собирает отсутствующие пути (дедуп+сорт)."""
        missing: set[str] = set()
        state = _ScanState(cache={}, errlist=set())
        anchors = 0
        groups = self._group_rules_by_anchors()
        for anchor_key, rules in groups.items():
            anchors = anchors + self._check_group(root, anchor_key, rules, missing, state)
        errlist = sorted(
            f"{path.relative_to(root).as_posix()}: {msg}" for path, msg in state.errlist
        )
        return CheckResult(
            missing=sorted(missing),
            rules_checked=len(self._rules),
            anchors_found=anchors,
            errlist=errlist,
        )

    def _group_rules_by_anchors(self) -> dict[tuple[str, ...], tuple[Rule, ...]]:
        """Группирует правила по префиксу якорей, чтобы не разворачивать его повторно."""
        grouped: dict[tuple[str, ...], list[Rule]] = {}
        for rule in self._rules:
            key = rule.anchors
            rules = grouped.get(key)
            if rules is None:
                grouped[key] = [rule]
                continue
            rules.append(rule)
        return {key: tuple(rules) for key, rules in grouped.items()}

    def _expand_anchors(
        self,
        root: Path,
        anchor_key: tuple[str, ...],
        state: _ScanState,
    ) -> tuple[Path, ...]:
        """Разворачивает каталог-якоря один раз на группу правил (с кэшем по префиксу)."""
        cached = state.cache.get(anchor_key)
        if cached is not None:
            return cached
        # Пустой префикс (правило из одного сегмента) => единственный якорь — сам root.
        # root.glob(".") НЕДОПУСТИМ (ValueError на Python 3.13+/3.14), поэтому особый случай.
        anchrs: Iterable[Path]
        if not anchor_key:
            anchrs = [root]
        elif "**" in anchor_key and anchor_key.count("**") == 1:
            anchrs = self._expand_anchors_recursive(root, anchor_key, state.errlist)
        else:
            anchrs = root.glob("/".join(anchor_key))
        expnd = tuple(anchrs)
        state.cache[anchor_key] = expnd
        return expnd

    def _expand_anchors_recursive(
        self,
        root: Path,
        anchor_key: tuple[str, ...],
        errlist: set[tuple[Path, str]],
    ) -> tuple[Path, ...]:
        """Разворачивает префикс с `**` через scandir (быстрее на больших деревьях)."""
        found: list[Path] = []
        self._walk_recursive(root, anchor_key, 0, found, errlist)
        return tuple(found)

    def _walk_recursive(
        self,
        curr: Path,
        anchor_key: tuple[str, ...],
        ix: int,
        found: list[Path],
        errlist: set[tuple[Path, str]],
    ) -> None:
        """Рекурсивно сопоставляет сегменты anchors с каталогами на диске."""
        if ix >= len(anchor_key):
            found.append(curr)
            return
        seg = anchor_key[ix]
        if seg == "**":
            self._walk_recursive(curr, anchor_key, ix + 1, found, errlist)
            for child in self._iter_child_dirs(curr, errlist):
                self._walk_recursive(child, anchor_key, ix, found, errlist)
            return
        for child in self._iter_child_dirs(curr, errlist):
            if fnmatch.fnmatch(child.name, seg):
                self._walk_recursive(child, anchor_key, ix + 1, found, errlist)

    def _iter_child_dirs(self, curr: Path, errlist: set[tuple[Path, str]]) -> tuple[Path, ...]:
        """Дочерние каталоги (без скрытых, без разыменования symlink).

        `OSError` (нет прав, гонка удаления) — не «нет совпадений», а сбой сканирования:
        фиксируется в `errlist` (абсолютный путь + текст исключения), а не проглатывается
        вместе со штатным пустым случаем.
        """
        dirs: list[Path] = []
        try:
            with os.scandir(curr) as ents:
                for ent in ents:
                    name = ent.name
                    if name.startswith("."):
                        continue
                    if not ent.is_dir(follow_symlinks=False):
                        continue
                    dirs.append(Path(ent.path))
        except OSError as exc:
            errlist.add((curr, str(exc)))
            return ()
        return tuple(dirs)

    def _check_group(
        self,
        root: Path,
        anchor_key: tuple[str, ...],
        rules: tuple[Rule, ...],
        missing: set[str],
        state: _ScanState,
    ) -> int:
        """Проверяет группу правил с одинаковым префиксом. Возвращает число якорей-кандидатов."""
        anchrs = self._expand_anchors(root, anchor_key, state)
        anccnt = 0
        for adir in anchrs:
            if not adir.is_dir():
                continue
            rel = adir.relative_to(root)
            if rel.parts and _is_hidden(rel):
                continue
            if self._negation.is_pruned_path(rel, is_dir=True):
                continue
            for rule in rules:
                target_rel = rel / rule.require
                if self._negation.is_pruned_path(target_rel, is_dir=False):
                    continue
                if self._negation.is_pruned_path(target_rel, is_dir=True):
                    continue
                anccnt = anccnt + 1
                target = adir / rule.require
                result = target.is_dir() if rule.dirflag else target.exists()
                if not result:
                    missing.add(target_rel.as_posix())
        return anccnt
