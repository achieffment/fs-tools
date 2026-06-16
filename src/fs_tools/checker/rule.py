"""Чтение и классификация правил из файла .fs-check.

`.fs-check` оформляется в стиле .gitignore, но с инвертированным смыслом: строки
описывают пути, которые ОБЯЗАНЫ существовать. Файл делится на два класса строк:

- положительные правила -> разбираются на префикс (якори) и последний сегмент
  (мандат); их разворачивает движок через `pathlib.Path.glob` (см. engine.py);
- негативные правила (`!...`) -> собираются в `pathspec.PathSpec` и работают как
  прунинг подстановок `*`/`**` по имени одной компоненты (gitignore-семантика).

Свой код тут — только тривиальная оркестрация (пропуск комментариев/пустых строк,
снятие `!` и якорного `/`, разбиение на сегменты); gitignore-семантику самих
`!`-шаблонов целиком обеспечивает pathspec.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pathspec

from ..shared.pathspec_compat import _FACTORY


class FsRuleError(Exception):
    """Файл .fs-check отсутствует или не читается (некорректный запуск)."""


def _rstrip_rule(line: str) -> str:
    """Обрезает конечные пробелы, не экранированные обратным слэшем.

    Как в gitignore: значимый конечный пробел экранируется `\\ ` (нечётное число
    предшествующих `\\`); такой пробел сохраняется.
    """
    stripped = line
    while stripped.endswith(" "):
        head = stripped[:-1]
        trailing_backslashes = len(head) - len(head.rstrip("\\"))
        if trailing_backslashes % 2 == 1:
            break  # экранированный пробел — значимый
        stripped = head
    return stripped


@dataclass(frozen=True)
class Rule:
    """Положительное правило: префикс (якори) + последний сегмент (мандат).

    `prefix` — сегменты, разворачиваемые `Path.glob` в существующие каталоги-якори;
    `mandate` — обязательный последний сегмент (проверяется литерально);
    `dir_only` — завершающий `/` в исходной строке: мандат проверяется как `is_dir()`,
    иначе как `exists()` (файл ИЛИ папка).
    """

    prefix: tuple[str, ...]
    mandate: str
    dir_only: bool
    raw: str

    @classmethod
    def from_pattern(cls, pattern: str) -> Rule:
        """Разбирает строку правила. Завершающий `/` распознаётся ДО снятия якоря.

        Якорный и завершающий `/` снимаются для `glob`; `\\ ` разэкранируется в
        значимый пробел (нужно для литерального сравнения мандата без поддержки
        gitignore-экранирования у `Path.glob`).
        """
        dir_only = pattern.endswith("/")
        core = pattern.strip("/").replace("\\ ", " ")
        segments = core.split("/")
        *prefix, mandate = segments
        return cls(prefix=tuple(prefix), mandate=mandate, dir_only=dir_only, raw=pattern)


class Negation:
    """Прунинг подстановок `*`/`**` по имени одной компоненты якоря.

    Шаблоны из строк `!...` (без ведущего `!`) компилируются в `pathspec.PathSpec`.
    Матч идёт по ИМЕНИ одного сегмента (`match_file(name + "/")`), а не по полному
    пути: иначе gitignore-семантика «совпал каталог → совпало поддерево» исключила
    бы и содержимое (например, архивные проекты под `_Archive`).
    """

    def __init__(self, spec: pathspec.PathSpec[Any]):
        self._spec = spec

    def is_pruned(self, name: str) -> bool:
        """Совпадает ли имя одной компоненты с негативом (тогда якорь отбрасывается)."""
        return self._spec.match_file(name + "/")


@dataclass(frozen=True)
class FsRule:
    """Результат разбора .fs-check: положительные правила + спека негативов."""

    rules: tuple[Rule, ...]
    negation: Negation


def load_fs_rule(root: Path) -> FsRule:
    """Читает .fs-check из корня проверки (`utf-8-sig` — BOM проглатывается).

    Нет файла -> FsRuleError (некорректный запуск). Пропуск
    комментариев (ведущий `#`) и пустых строк делает сам этот разбор для ВСЕГО файла
    (до классификации) — в pathspec уходят только `!`-шаблоны без ведущего `!`.
    """
    path = root / ".fs-check"
    if not path.is_file():
        raise FsRuleError(f"в выбранном каталоге нет файла .fs-check: {path}")
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise FsRuleError(f"не удалось прочитать .fs-check: {exc}") from exc

    rules: list[Rule] = []
    negatives: list[str] = []
    for line in raw.splitlines():
        content = _rstrip_rule(line)
        if not content or content.startswith("#"):
            continue  # пустая строка или комментарий (только ведущий `#`)
        if content.startswith("!"):
            negatives.append(content[1:])  # `!`-шаблон отдаём pathspec без ведущего `!`
            continue
        rule = Rule.from_pattern(content)
        if rule.mandate:  # отбрасываем вырожденные строки вроде "/" без сегментов
            rules.append(rule)

    spec: pathspec.PathSpec[Any] = pathspec.PathSpec.from_lines(_FACTORY, negatives)
    return FsRule(rules=tuple(rules), negation=Negation(spec))
