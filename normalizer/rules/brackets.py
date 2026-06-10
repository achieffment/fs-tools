"""Обработка круглых и квадратных скобок в имени."""
from __future__ import annotations

import re

from .base import Rule


class BracketsRule(Rule):
    """Круглые и квадратные скобки: с числом/датой убираем, с текстом сохраняем.

    Дубли файловых менеджеров ('Файл (1)', 'Файл [1]') -> 'file-01': скобки
    вокруг числа/даты снимаем, дальше DateRule/LeadingZero дополнят. Скобки с
    буквами ('(копия)', '[черновик]') оставляем как часть имени. Идёт после
    транслитерации (содержимое уже ASCII, проверка '[A-Za-z]' однозначна).
    Пустые и непарные/несовпадающие скобки ('Файл (1', 'инн (текст]') убираются:
    обрабатываем сбалансированные пары до стабилизации, остаток (непарные '()[]')
    вырезаем.
    """

    _RE = re.compile(r"\(([^()\[\]]*)\)|\[([^()\[\]]*)\]")
    _HAS_LETTER = re.compile(r"[A-Za-z]")
    _OP = {"(": ")", "[": "]"}
    _CL = {")": "(", "]": "["}

    def apply(self, stem: str, is_dir: bool) -> str:
        prev = ""
        while prev != stem:  # вложенные пары: '((1))' -> '(1)' -> '1'
            prev = stem
            stem = self._RE.sub(self._rep, stem)
        return self._strip_unpa(stem)

    @classmethod
    def _rep(cls, m: "re.Match[str]") -> str:
        content = m.group(1) if m.group(1) is not None else m.group(2)
        if cls._HAS_LETTER.search(content):
            return m.group(0)  # текст — скобки сохраняем
        return content  # число/дата/пусто — скобки убираем

    @classmethod
    def _strip_unpa(cls, stem: str) -> str:
        # Стек сопоставляет открывающие с закрывающими; индексы найденных пар —
        # в pairs, всё остальное из '()[]' (непарное/несовпадающее) вырезаем.
        pairs: set[int] = set()
        stack: list[tuple[str, int]] = []
        for i, ch in enumerate(stem):
            if ch in cls._OP:
                stack.append((ch, i))
            elif ch in cls._CL and stack and stack[-1][0] == cls._CL[ch]:
                pairs.add(i)
                pairs.add(stack.pop()[1])
        return "".join(ch for i, ch in enumerate(stem) if i in pairs or (ch not in cls._OP and ch not in cls._CL))
