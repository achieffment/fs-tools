"""Ведущий ноль для однозначного числового токена."""
from __future__ import annotations

from .base import Rule


class LeadingZeroRule(Rule):
    """
    Однозначное число как отдельный токен -> с ведущим нулём.
    Токен ограничен пробелом/подчёркиванием/дефисом или краями строки.
    Дроби (1.5), числа с буквами (v2, 2x) и компоненты дат не затрагиваются.

    Идёт ПОСЛЕ TrimEdgeRule: токен оценивается уже без кромочного «мусора»,
    поэтому '5!'/'том 5,' дополняются нулём за один проход (см. build_normalizer).
    """

    _SE = " _-"

    def apply(self, stem: str, is_dir: bool) -> str:
        score: list[str] = []
        tok = ""
        for ch in stem:
            if ch in self._SE:
                score.append(self._pad(tok))
                score.append(ch)
                tok = ""
            else:
                tok += ch
        score.append(self._pad(tok))
        return "".join(score)

    @staticmethod
    def _pad(tok: str) -> str:
        if len(tok) == 1 and tok in "0123456789":
            return "0" + tok
        return tok
