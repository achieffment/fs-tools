"""Тестовый модуль."""

import pytest

from fs_tools.normalizer import build_normalizer
from fs_tools.normalizer.name import NameNormalizer

DEMO_TREE = [
    "Отчёт 2020/20.05.2020_dump",
    "1_file.TXT",
    "v2 readme.MD",
    ".git/CONFIG",
    ".env",
]


@pytest.fixture()
def nn() -> NameNormalizer:
    """Выполняет шаг: nn."""
    return build_normalizer()
