"""Пакет нормализации имён файлов и папок.

Публичное API: импортируйте отсюда, а не из подмодулей напрямую. Имена, тянущие
`Unidecode` (правила, конвейер, `FsNormalizer`), грузятся лениво — чтобы
импорт пакета и команда `fs-normalizer` не падали без extra `normalizer` до момента работы.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from .ignore import FsIgnore, load_fs_ignore
from .log import FS_LOG, write_fs_log
from .runner import main

if TYPE_CHECKING:
    from .engine import FsNormalizer
    from .name import NameNormalizer, build_normalizer
    from .rules import (
        BracketsRule,
        CaseRule,
        DateRule,
        LeadingZeroRule,
        Rule,
        SpaceToDashRule,
        TransliterationRule,
        TrimEdgeRule,
    )

# Имя -> относительный модуль для ленивой загрузки (тянут `Unidecode`).
_LAZY = {
    "FsNormalizer": ".engine",
    "NameNormalizer": ".name",
    "build_normalizer": ".name",
    "Rule": ".rules",
    "TransliterationRule": ".rules",
    "BracketsRule": ".rules",
    "DateRule": ".rules",
    "LeadingZeroRule": ".rules",
    "CaseRule": ".rules",
    "SpaceToDashRule": ".rules",
    "TrimEdgeRule": ".rules",
}


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    obj = getattr(importlib.import_module(module, __name__), name)
    globals()[name] = obj  # кэшируем — повторный доступ не идёт через __getattr__
    return obj


__all__ = [
    "main",
    "FsNormalizer",
    "FsIgnore",
    "load_fs_ignore",
    "FS_LOG",
    "write_fs_log",
    "NameNormalizer",
    "build_normalizer",
    "Rule",
    "TransliterationRule",
    "BracketsRule",
    "DateRule",
    "LeadingZeroRule",
    "CaseRule",
    "SpaceToDashRule",
    "TrimEdgeRule",
]
