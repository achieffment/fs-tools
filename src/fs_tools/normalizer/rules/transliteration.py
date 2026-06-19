"""Транслитерация не-ASCII символов в ASCII с барьером безопасности имени."""
from __future__ import annotations

try:
    from unidecode import unidecode
except ImportError as exc:
    raise ImportError(
        "Не найден пакет 'Unidecode' (требуется режиму нормализации). "
        'Установите зависимость: pip install "fs-tools[normalizer]"'
    ) from exc

from ..safety import enforce_safe_component
from .base import Rule


class TransliterationRule(Rule):
    """Любой не-ASCII символ -> ASCII (кириллица, умляуты, emoji и т.п.).

    Транслитерация может породить разделители пути и управляющие символы:
    например '½' -> '1/2', '½'(дробь)/'∖'/стрелки -> '\\', а U+2028/U+2029 -> '\\n'.
    Если оставить их в stem, os.rename истолкует '/'/'\\' как разделитель пути и
    МОЛЧА переместит объект в соседний каталог (или потеряет его). Поэтому сразу
    после транслитерации такие символы заменяются на '-': имя гарантированно
    остаётся ОДНИМ компонентом пути на любой ОС. Делается это до остальных правил,
    чтобы LeadingZero/Trim видели одинаковую структуру токенов и сохранялась
    идемпотентность.

    Дополнительно чистятся два класса «мусора», который вносит unidecode:
    - мягкий и твёрдый знаки ('ь'/'ъ' -> апостроф) удаляются ДО транслитерации,
      чтобы апостроф не появлялся вовсе (ASCII-апостроф во входном имени, как в
      O'Brien, при этом не затрагивается);
    - запрещённые на Windows символы ('< > : " | ? *', в которые превращается
      типографика вроде '«»') удаляются ПОСЛЕ транслитерации.
    """

    # Кириллические знаки, дающие через unidecode апостроф, вырезаем.
    _DROP = str.maketrans("", "", "ьЬъЪ")

    def apply(self, stem: str, is_dir: bool) -> str:
        ascii_stem = stem.translate(self._DROP)
        ascii_stem = unidecode(ascii_stem)
        return enforce_safe_component(ascii_stem)
