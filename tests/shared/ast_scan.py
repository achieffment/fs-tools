"""Общие обходы AST для проверок по проекту."""
from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path


def iter_project_trees(root: Path) -> Iterator[tuple[Path, ast.AST]]:
    """Итерирует python-файлы `src` и `tests` и отдаёт пары (path, tree)."""
    for base in (root / "src", root / "tests"):
        for path in sorted(base.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=path.as_posix())
            yield path, tree
