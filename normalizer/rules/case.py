"""Единый регистр: папки — с заглавной, файлы — в нижнем."""
from __future__ import annotations

from .base import Rule


class CaseRule(Rule):
    """Папки — с заглавной буквы, файлы — в нижнем регистре.

    У папок ведущие '_' сохраняются (их оставляет TrimEdgeRule), поэтому
    капитализируется первая буква уже ПОСЛЕ них ('_private' -> '_Private').

    Исключение: общепринятые имена-маркеры (README и т.п.) сохраняют
    свой регистр — их stem не приводится к нижнему. Чтобы защитить новое
    имя, достаточно добавить его в PRESERVED_STEMS.
    """

    # Имена (stem без расширения), регистр которых не меняем: README, README.md ...
    PRESERVED_STEMS = frozenset({"README"})

    def apply(self, stem: str, is_dir: bool) -> str:
        if is_dir:
            i = len(stem) - len(stem.lstrip("_"))  # позиция первой буквы после '_'
            return stem[:i] + stem[i:i + 1].upper() + stem[i + 1:]
        if stem in self.PRESERVED_STEMS:
            return stem
        return stem.lower()
