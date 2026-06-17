from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture()
def write_rule(tmp_path: Path) -> Callable[[str], Path]:
    """Записывает текст в tmp_path/.fs-check и возвращает корень (tmp_path)."""

    def _write(text: str) -> Path:
        (tmp_path / ".fs-check").write_text(text, encoding="utf-8")
        return tmp_path

    return _write
