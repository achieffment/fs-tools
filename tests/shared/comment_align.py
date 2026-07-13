"""Общая проверка выравнивания inline-комментариев по локальным подблокам.

Подблок — строки между пустыми строками (см. `.claude/rules/comments-style.md`).
Два независимых профиля используют одну и ту же механику флаша, но разные
параметры:

- Markdown (командные fenced-блоки, `test_markdown_comments.py`): опора —
  самая длинная строка подблока **среди всех строк** (в т.ч. без комментария,
  например соседняя команда) + 4; выравнивание требуется только при ≥2 строках
  с inline-комментарием — блок должен визуально читаться как таблица.
- TOML (`test_toml_comments.py`): опора — самая длинная строка подблока
  **среди строк с inline-комментарием** (не связанные строки кода вроде
  `default_rule = {...}` не должны утягивать далёкий одиночный комментарий) + 2;
  выравнивание требуется уже при одной строке (это и есть минимальный отступ).
"""
from __future__ import annotations


class AlignmentGroup:
    """Копит строки одного подблока и проверяет их по флашу."""

    def __init__(self, *, pad: int = 4, min_rows: int = 2, include_plain: bool = True) -> None:
        self._pad = pad
        self._min_rows = min_rows
        self._include_plain = include_plain
        self._rows: list[tuple[int, int, str]] = []
        self._base_len: list[int] = []

    def add_plain(self, base_len: int) -> None:
        """Строка без inline-комментария — участвует в опорной длине, если профиль это учитывает."""
        if self._include_plain:
            self._base_len.append(base_len)

    def add_commented(self, lineno: int, hash_pos: int, base_len: int, text: str) -> None:
        """Строка с inline-комментарием — всегда участвует и в опоре, и в проверке."""
        self._base_len.append(base_len)
        self._rows.append((lineno, hash_pos, text))

    def flush(self) -> list[tuple[int, int, int, str]]:
        """Вернуть несовпадения `(строка, факт, ожидание, текст)` и сбросить подблок."""
        misaligned: list[tuple[int, int, int, str]] = []
        if len(self._rows) >= self._min_rows:
            target = max(self._base_len) + self._pad
            for lineno, hash_pos, text in self._rows:
                if hash_pos != target:
                    misaligned.append((lineno, hash_pos, target, text))
        self._rows.clear()
        self._base_len.clear()
        return misaligned
