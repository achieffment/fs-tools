"""Тестовый модуль."""

from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture()
def write_scheme_toml(tmp_path: Path) -> Callable[[str], Path]:
    """Записывает текст в tmp_path/.fs-sch.toml и возвращает корень (tmp_path)."""

    def _write(text: str) -> Path:
        """Вспомогательная функция для теста."""
        (tmp_path / ".fs-sch.toml").write_text(text, encoding="utf-8")
        return tmp_path

    return _write
