"""Правила нормализации имён: по одному классу-правилу на модуль.

Публичные имена ре-экспортируются здесь, чтобы внешний код, build_normalizer
(`normalizer/name.py`) и пакет `normalizer` импортировали их из одного места.
Порядок `__all__` отражает логику конвейера/API, а не использование (см.
`.cursor/rules/imports.mdc`); сами import-строки отсортированы по isort.
"""
from __future__ import annotations

from .base import Rule
from .brackets import BracketsRule
from .case import CaseRule
from .date import DateRule
from .leading_zero import LeadingZeroRule
from .space_to_dash import SpaceToDashRule
from .transliteration import TransliterationRule
from .trim_edge import TrimEdgeRule

__all__ = [
    "Rule",
    "TransliterationRule",
    "BracketsRule",
    "DateRule",
    "LeadingZeroRule",
    "CaseRule",
    "SpaceToDashRule",
    "TrimEdgeRule",
]
