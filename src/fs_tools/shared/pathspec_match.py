"""Общие утилиты для pathspec-мэтчинга путей.

Один и тот же формат входа нужен в normalizer и checker:
- путь всегда относительный и в posix-виде;
- для каталогов добавляется завершающий `/` (dir-only паттерны).
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pathspec

from .pathspec_compat import _FACTORY


def build_spec(lines: Iterable[str]) -> pathspec.PathSpec[Any]:
    """Собирает `PathSpec` с совместимой фабрикой gitignore-паттернов."""
    return pathspec.PathSpec.from_lines(_FACTORY, lines)


def path_text(rel: Path, is_dir: bool) -> str:
    """Преобразует относительный путь в формат для `PathSpec.match_file`."""
    text = rel.as_posix()
    if is_dir:
        text = text + "/"
    return text
