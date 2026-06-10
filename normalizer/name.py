"""Сборка нового имени из набора правил (без обращения к ФС)."""
from __future__ import annotations

import re

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
from .safety import enforce_safe_component


class NameNormalizer:
    """Применяет правила по порядку к stem; расширение файла не трогает."""

    # Расширение — последний сегмент из букв/цифр (1-8), не состоящий целиком из цифр.
    # Это защищает даты с точками (20.05.2020) от ложного разбиения на «расширение».
    _EXT_RE = re.compile(r"\.([A-Za-z0-9]{1,8})$")

    def __init__(self, rules: list[Rule]):
        self.rules = rules

    @classmethod
    def _split_ext(cls, name: str) -> tuple[str, str]:
        m = cls._EXT_RE.search(name)
        if m and not m.group(1).isdigit():
            return name[: m.start()], name[m.start():]
        return name, ""

    def normalize(self, name: str, is_dir: bool) -> str:
        if is_dir:
            stem, ext = name, ""
        else:
            stem, ext = self._split_ext(name)
        new_stem = stem
        for rule in self.rules:
            new_stem = rule.apply(new_stem, is_dir)
        # Защитный барьер: имя не должно содержать разделителей пути/управляющих
        # символов и запрещённых на Windows символов. В норме TransliterationRule
        # их уже убрал — здесь страховка.
        new_stem = enforce_safe_component(new_stem)
        if not new_stem:
            return name  # защита от пустого имени (например, имя из одних emoji)
        return new_stem + ext


def build_normalizer() -> NameNormalizer:
    """Фабрика: собирает конвейер правил в каноническом порядке.

    LeadingZeroRule идёт ПОСЛЕ TrimEdgeRule (и SpaceToDashRule): ведущий ноль
    добавляется к уже очищенному от кромочного «мусора» токену. Иначе одиночная
    цифра рядом с символом, который потом срежет TrimEdge ('5!', '5.', 'том 5,'),
    на первом проходе не распозналась бы как отдельный токен и осталась без нуля,
    а на втором (мусор уже срезан) — получила бы его: '5' -> '05' (нарушение
    идемпотентности).

    CaseRule идёт ПОСЛЕДНИМ — после схлопывания пробелов и обрезки кромок,
    чтобы заглавная буква папки применялась к финальному первому символу.
    Иначе ведущие пробелы/дефисы «съедали» бы капитализацию, и она проявлялась
    бы только при повторном прогоне (нарушение идемпотентности).
    """
    return NameNormalizer(
        [
            TransliterationRule(),
            BracketsRule(),
            DateRule(),
            SpaceToDashRule(),
            TrimEdgeRule(),
            LeadingZeroRule(),
            CaseRule(),
        ]
    )
