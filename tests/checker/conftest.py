from collections.abc import Callable, Iterable
from pathlib import Path

import pytest


@pytest.fixture()
def make_tree(tmp_path: Path) -> Callable[[Iterable[str]], Path]:
    """Фабрика дерева: создаёт каталоги/файлы из списка путей в tmp_path.

    Путь, оканчивающийся на '/', — каталог; иначе файл (вместе с родителями).
    Возвращает корень созданного дерева (tmp_path).
    """

    def _make(paths: Iterable[str]) -> Path:
        for rel in paths:
            target = tmp_path / rel
            if rel.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("", encoding="utf-8")
        return tmp_path

    return _make


@pytest.fixture()
def write_rule(tmp_path: Path) -> Callable[[str], Path]:
    """Записывает текст в tmp_path/.fs-check и возвращает корень (tmp_path)."""

    def _write(text: str) -> Path:
        (tmp_path / ".fs-check").write_text(text, encoding="utf-8")
        return tmp_path

    return _write
