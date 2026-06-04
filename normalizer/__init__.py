"""Пакет нормализации имён файлов и папок.

Публичное API: импортируйте отсюда, а не из подмодулей напрямую.
"""
from __future__ import annotations

from .cli import main
from .filesystem import FilesystemNormalizer
from .name import NameNormalizer, build_normalizer
from .rules import (
    CaseRule,
    DateRule,
    LeadingZeroRule,
    Rule,
    SpaceToDashRule,
    TransliterationRule,
    TrimEdgeRule,
)

__all__ = [
    "main",
    "FilesystemNormalizer",
    "NameNormalizer",
    "build_normalizer",
    "Rule",
    "TransliterationRule",
    "DateRule",
    "LeadingZeroRule",
    "CaseRule",
    "SpaceToDashRule",
    "TrimEdgeRule",
]
