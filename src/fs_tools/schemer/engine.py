"""Read-only обход дерева и сбор нарушений структуры/контента базы знаний.

Классификация узла: каталог — «групповой», если его basename совпадает с именем
одной из групп конфига (регистрозависимо, на любой глубине); иначе — «тематический».
Групповые узлы проверяются по F1/F4 (обязательный файл), F7/F9–F13 (опциональный
файл с контент-правилом), F2/F3/F5/F6/F8 (контент — литеральное совпадение
`line`/`text`) и F14 (не должна существовать пустой — рекурсивно, в т.ч. вложенные
подпапки). Тематические узлы проверяются по F15 (файлы напрямую в узле запрещены;
сам `.fs-sch.toml` под неё не попадает — он скрытый и отсеян общим фильтром).
`group.file`/`default_rule` применяются только к файлам, лежащим НЕПОСРЕДСТВЕННО в
групповой папке (не рекурсивно) — рекурсивный обход зарезервирован только для F14.
По умолчанию (`strict=False`) обход не спускается в подпапки группы вовсе: их
содержимое не классифицируется ни группой, ни тематическим узлом, F15 на них не
срабатывает — вложенность внутри группы разрешена. `strict=True` включает прежнее
поведение: подпапки группы заново классифицируются наравне с остальным деревом.
`default_rule.extensions`/`exclude_extensions` (см. `config.py`) сужают круг файлов,
которые вообще читаются под `default_rule` — не подошедшие под фильтр не читаются
и не попадают в `files_checked` (не нарушение).

Обход — `os.walk` от корня без `followlinks` (симлинки не разыменовываются); скрытые
(на `.`) каталоги и файлы пропускаются — как у normalizer/checker.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .config import ContentRule, Group, SchemeConfig


@dataclass(frozen=True)
class Violation:
    """Одно нарушение: тип, относительный путь и (для контентных) ожидание/факт."""

    path: str
    kind: str
    expected: str = ""
    actual: str = ""


@dataclass
class SchemerResult:
    """Итог проверки: отсортированные нарушения и счётчики для сводки."""

    violations: list[Violation]
    groups_checked: int
    files_checked: int


def _is_hidden(name: str) -> bool:
    return name.startswith(".")


def _visible_dirnames(dirnames: list[str]) -> list[str]:
    return sorted(name for name in dirnames if not _is_hidden(name))


def _visible_filenames(filenames: list[str]) -> list[str]:
    return sorted(name for name in filenames if not _is_hidden(name))


def _has_any_visible_file(curr: Path) -> bool:
    """Рекурсивно: есть ли под `curr` хотя бы один видимый файл (скрытые не обходим)."""
    for _dirpath, dirnames, filenames in os.walk(curr, followlinks=False):
        dirnames[:] = _visible_dirnames(dirnames)
        if _visible_filenames(filenames):
            return True
    return False


def _matches_extension_filter(name: str, rule: ContentRule) -> bool:
    """default_rule: подходит ли `name` под её extensions/exclude_extensions.

    Оба условия независимы и комбинируются через «И»: не заданный `extensions`
    не сужает набор (стартуем со «всех файлов»), не заданный `exclude_extensions`
    ничего из набора не убирает. Оба не заданы -> подходит любой файл (прежнее
    поведение). Расширение сравнивается регистронезависимо (`Path.suffix.lower()`).
    """
    suffix = Path(name).suffix.lower()
    if rule.extensions is not None and suffix not in rule.extensions:
        return False
    if rule.exclude_extensions is not None and suffix in rule.exclude_extensions:
        return False
    return True


def _check_content(target: Path, rel: str, rule: ContentRule) -> Violation | None:
    """Проверить `line`/`text` файла: `missing_line` короче, `bad_header` не совпал.

    Файл не удалось прочитать (нет прав, гонка удаления, не-UTF-8 содержимое) —
    отдельная категория `read_error`, а не `missing_line`: это техническая ошибка
    чтения, а не содержательное несовпадение, и текст исключения важен для диагностики.
    """
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return Violation(path=rel, kind="read_error", actual=str(exc))
    lines = text.splitlines()
    if len(lines) < rule.line:
        return Violation(path=rel, kind="missing_line", expected=rule.text)
    actual = lines[rule.line - 1]
    if actual != rule.text:
        return Violation(path=rel, kind="bad_header", expected=rule.text, actual=actual)
    return None


class FsSchemer:
    """Проверка структуры/контента базы знаний по декларативным группам (read-only)."""

    def __init__(self, config: SchemeConfig):
        self._config = config
        self._groups_by_name = {group.name: group for group in config.groups}

    def check(self, root: Path) -> SchemerResult:
        """Обходит `root`, собирает нарушения (дедуп+сорт) и счётчики групп/файлов."""
        violations: set[Violation] = set()
        groups_checked = 0
        files_checked = 0
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            curr = Path(dirpath)
            dirnames[:] = _visible_dirnames(dirnames)
            visible_files = _visible_filenames(filenames)
            group = self._groups_by_name.get(curr.name)
            if group is not None:
                groups_checked = groups_checked + 1
                found = self._check_group(root, curr, group, visible_files, violations)
                files_checked = files_checked + found
                if not group.strict:
                    dirnames[:] = []
            else:
                self._check_loose(root, curr, visible_files, violations)
        return SchemerResult(
            violations=sorted(violations, key=lambda vio: (vio.path, vio.kind)),
            groups_checked=groups_checked,
            files_checked=files_checked,
        )

    def _check_loose(
        self,
        root: Path,
        curr: Path,
        visible_files: list[str],
        violations: set[Violation],
    ) -> None:
        """F15: файлы напрямую в тематическом узле запрещены."""
        for name in visible_files:
            rel = (curr.relative_to(root) / name).as_posix()
            violations.add(Violation(path=rel, kind="loose_file"))

    def _check_group(
        self,
        root: Path,
        curr: Path,
        group: Group,
        visible_files: list[str],
        violations: set[Violation],
    ) -> int:
        """Обязательность/контент/пустота (F1–F14) для одной групповой папки.

        Возвращает число файлов, для которых выполнена контент-проверка.
        """
        rel_dir = curr.relative_to(root)
        by_name = set(visible_files)
        files_checked = 0
        handled: set[str] = set()
        for gfile in group.files:
            handled.add(gfile.name)
            rel = (rel_dir / gfile.name).as_posix()
            if gfile.name not in by_name:
                if not gfile.optional:
                    violations.add(Violation(path=rel, kind="missing_group_file"))
                continue
            files_checked = files_checked + 1
            content = _check_content(curr / gfile.name, rel, gfile.rule)
            if content is not None:
                violations.add(content)

        if group.default_rule is not None:
            rule = group.default_rule
            for name in visible_files:
                if name in handled or name.startswith(self._config.exclude_prefix):
                    continue
                if not _matches_extension_filter(name, rule):
                    continue
                files_checked = files_checked + 1
                rel = (rel_dir / name).as_posix()
                content = _check_content(curr / name, rel, rule)
                if content is not None:
                    violations.add(content)

        if not _has_any_visible_file(curr):
            violations.add(Violation(path=rel_dir.as_posix(), kind="empty_group"))

        return files_checked
