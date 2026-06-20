"""Порядок блоков lazy-import: загрузка через import_module по порядку использования."""
from __future__ import annotations

import ast
from pathlib import Path

from tests.shared.ast_scan import iter_project_trees


def _is_lazy_assign(node: ast.stmt) -> tuple[str, int] | None:
    if not isinstance(node, ast.Assign):
        return None
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return None
    targ = node.targets[0].id
    value = node.value
    if not isinstance(value, ast.Attribute):
        return None
    call = value.value
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr != "import_module":
        return None
    base = func.value
    if not isinstance(base, ast.Name) or base.id != "importlib":
        return None
    return targ, node.lineno


def _first_uses(func: ast.AST) -> dict[str, int]:
    result: dict[str, int] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Name):
            continue
        if not isinstance(node.ctx, ast.Load):
            continue
        prev = result.get(node.id)
        if prev is None or node.lineno < prev:
            result[node.id] = node.lineno
    return result


def _check_stmt_list(stmts: list[ast.stmt], uses: dict[str, int], rel: str, bad: list[str]) -> None:
    ix = 0
    while ix < len(stmts):
        current = _is_lazy_assign(stmts[ix])
        if current is None:
            ix = ix + 1
            continue
        block: list[tuple[str, int]] = [current]
        jx = ix + 1
        while jx < len(stmts):
            nxt = _is_lazy_assign(stmts[jx])
            if nxt is None:
                break
            block.append(nxt)
            jx = jx + 1
        if len(block) > 1:
            for kx in range(len(block) - 1):
                name1, _line1 = block[kx]
                name2, line2 = block[kx + 1]
                use1 = uses.get(name1)
                use2 = uses.get(name2)
                if use1 is None or use2 is None:
                    continue
                if use1 > use2:
                    bad.append(f"{rel}:{line2} ({name2} используется раньше {name1})")
        ix = jx


def _walk_blocks(node: ast.AST, uses: dict[str, int], rel: str, bad: list[str]) -> None:
    for field in (
        "body",
        "orelse",
        "finalbody",
    ):
        part = getattr(node, field, None)
        if isinstance(part, list) and part and all(isinstance(x, ast.stmt) for x in part):
            stmts = [x for x in part if isinstance(x, ast.stmt)]
            _check_stmt_list(stmts, uses, rel, bad)
            for stmt in stmts:
                _walk_blocks(stmt, uses, rel, bad)


def test_lazy_import_order_matches_usage() -> None:
    """Проверяет, что lazy-import в блоках идут по порядку первого использования."""
    root = Path(__file__).resolve().parents[2]
    bad: list[str] = []
    for path, tree in iter_project_trees(root):
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            uses = _first_uses(node)
            _walk_blocks(node, uses, rel, bad)
    assert not bad, "Нарушен порядок lazy-import: " + ", ".join(bad)
