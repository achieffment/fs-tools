"""Запрет на `AugAssign` с `Add` (`a = a + b` вместо инкрементального сложения)."""
from __future__ import annotations

import ast
from pathlib import Path

from tests.shared.ast_scan import iter_project_trees


def test_no_add_augassign_in_project() -> None:
    """Проверяет сценарий: no add augassign in project."""
    root = Path(__file__).resolve().parents[2]
    bad: list[str] = []
    for path, tree in iter_project_trees(root):
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                rel = path.relative_to(root).as_posix()
                bad.append(f"{rel}:{node.lineno}")
    assert not bad, "Найдены запрещённые AugAssign/Add: " + ", ".join(bad)
