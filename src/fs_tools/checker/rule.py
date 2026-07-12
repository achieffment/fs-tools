"""Чтение и классификация правил из файла .fs-chk.

`.fs-chk` оформляется в стиле .gitignore, но с инвертированным смыслом: строки
описывают пути, которые ОБЯЗАНЫ существовать. Файл делится на два класса строк:

- положительные правила -> разбираются на префикс (якори) и последний сегмент
  (мандат); префикс разворачивает движок — `pathlib.Path.glob` или, для одного
  `**` в префиксе, собственный scandir-обход (см. engine.py);
- негативные правила (`!...`) -> собираются в единый ordered `pathspec.PathSpec`
  и применяются к относительным путям якорей/мандатов (с учётом порядка строк).
  В checker `!` всегда означает исключение из проверки; ведущие `!` схлопываются
  (`!!/a` эквивалентно `!/a`).

Свой код тут — только тривиальная оркестрация (пропуск комментариев/пустых строк,
снятие `!` и якорного `/`, разбиение на сегменты); gitignore-семантику самих
`!`-шаблонов целиком обеспечивает pathspec.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pathspec

from ..shared.pathspec_match import build_spec, path_text


class FsRuleError(Exception):
    """Файл .fs-chk отсутствует или не читается (некорректный запуск)."""


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


def _normalize_negation(line: str) -> str:
    """Нормализует негатив: схлопывает ведущие `!` до одного отрицания.

    Возвращает паттерн БЕЗ ведущих `!` для передачи в pathspec. Таким образом
    `!!/a` и `!!!/a` трактуются как `!/a` (без re-include семантики).
    """
    return line.lstrip("!")


@dataclass(frozen=True)
class Rule:
    """Положительное правило: префикс (якори) + последний сегмент (мандат).

    `anchors` — сегменты, разворачиваемые `Path.glob` в существующие каталоги-якори;
    `require` — обязательный последний сегмент (проверяется литерально);
    `dirflag` — завершающий `/` в исходной строке: мандат проверяется как `is_dir()`,
    иначе как `exists()` (файл ИЛИ папка).
    """

    anchors: tuple[str, ...]
    require: str
    dirflag: bool
    pattern: str

    @classmethod
    def from_pattern(cls, pattern: str) -> Rule:
        """Разбирает строку правила. Завершающий `/` распознаётся ДО снятия якоря.

        Якорный и завершающий `/` снимаются для `glob`; `\\ ` разэкранируется в
        значимый пробел (нужно для литерального сравнения мандата без поддержки
        gitignore-экранирования у `Path.glob`).
        """
        dirflag = pattern.endswith("/")
        cleaned = pattern.strip("/").replace("\\ ", " ")
        seglist = cleaned.split("/")
        *anchors, require = seglist
        return cls(
            anchors=tuple(anchors),
            require=require,
            dirflag=dirflag,
            pattern=pattern,
        )


class Negation:
    """Негативы `.fs-chk`: единый ordered pathspec-канал.

    Шаблоны из строк `!...` (без ведущих `!`) компилируются в `pathspec.PathSpec`.
    Матч идёт по относительным путям якорей/мандатов. Порядок строк учитывается
    pathspec (`last-match-wins`), но в checker это влияет только на исключения:
    re-include через `!!...` не поддерживается (ведущие `!` схлопываются).
    """

    def __init__(self, spec: pathspec.PathSpec[Any]):
        self._spec = spec

    def is_pruned_path(self, rel_path: Path, is_dir: bool) -> bool:
        """Совпадает ли относительный путь якоря/мандата с негативом."""
        return self._spec.match_file(path_text(rel_path, is_dir))


@dataclass(frozen=True)
class FsRule:
    """Результат разбора .fs-chk: положительные правила + спека негативов."""

    rules: tuple[Rule, ...]
    negation: Negation


def load_fs_rule(root: Path) -> FsRule:
    """Читает .fs-chk из корня проверки (`utf-8-sig` — BOM проглатывается).

    Нет файла -> FsRuleError (некорректный запуск). Пропуск
    комментариев (ведущий `#`) и пустых строк делает сам этот разбор для ВСЕГО файла
    (до классификации) — в pathspec уходят `!`-шаблоны без ведущих `!`.
    """
    path = root / ".fs-chk"
    if not path.is_file():
        raise FsRuleError(f"в выбранном каталоге нет файла .fs-chk: {path}")
    try:
        bare = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise FsRuleError(f"не удалось прочитать .fs-chk: {exc}") from exc

    rules: list[Rule] = []
    negatives: list[str] = []
    for line in bare.splitlines():
        cont = _rstrip_rule(line)
        if not cont or cont.startswith("#"):
            continue  # пустая строка или комментарий (только ведущий `#`)
        if cont.startswith("!"):
            neg = _normalize_negation(cont)
            if neg:
                negatives.append(neg)
            continue
        rule = Rule.from_pattern(cont)
        if rule.require:  # отбрасываем вырожденные строки вроде "/" без сегментов
            rules.append(rule)

    spec = build_spec(negatives)
    return FsRule(rules=tuple(rules), negation=Negation(spec))
