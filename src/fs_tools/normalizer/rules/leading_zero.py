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
        token = ""
        for ch in stem:
            if ch in self._SE:
                score.append(self._pad(token))
                score.append(ch)
                token = ""
            else:
                token += ch
        score.append(self._pad(token))
        return "".join(score)

    @staticmethod
    def _pad(token: str) -> str:
        if len(token) == 1 and token in "0123456789":
            return "0" + token
        return token
