"""Проверяет выравнивание столбцов GFM-таблиц в Markdown."""
from __future__ import annotations

import re
from pathlib import Path

_SEP_CELL = re.compile(r"^:?-+:?$")


def _iter_markdown_files(root: Path) -> list[Path]:
    files = sorted(root.rglob("*.md")) + sorted(root.rglob("*.mdc"))
    return [path for path in files if ".venv" not in path.parts and ".scratch" not in path.parts]


def _split_cells(line: str) -> list[str]:
    bare = line.strip()
    protected = bare.replace("\\|", "\x00")
    if protected.startswith("|"):
        protected = protected[1:]
    if protected.endswith("|"):
        protected = protected[:-1]
    return [cell.replace("\x00", "\\|").strip() for cell in protected.split("|")]


def _is_row(line: str) -> bool:
    bare = line.strip()
    return bare.startswith("|") and bare.endswith("|") and len(bare) >= 2


def _is_separator_row(line: str) -> bool:
    cells = _split_cells(line)
    return bool(cells) and all(_SEP_CELL.match(cell) for cell in cells)


def _find_tables(lines: list[str]) -> list[tuple[int, int]]:
    tables = []
    ix = 0
    while ix < len(lines) - 1:
        if _is_row(lines[ix]) and _is_separator_row(lines[ix + 1]):
            start = ix
            end = ix + 2
            while end < len(lines) and _is_row(lines[end]):
                end = end + 1
            tables.append((start, end))
            ix = end
        else:
            ix = ix + 1
    return tables


def _table_errors(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    errlist: list[str] = []
    for start, end in _find_tables(lines):
        block = lines[start:end]
        rows = [_split_cells(line) for line in block]
        ncol = len(rows[0])
        if any(len(row) != ncol for row in rows):
            continue
        widths = [0] * ncol
        for r_ix, row in enumerate(rows):
            if r_ix == 1:
                continue
            for c_ix, cell in enumerate(row):
                widths[c_ix] = max(widths[c_ix], len(cell))
        widths = [max(width, 3) for width in widths]

        for r_ix, (line, row) in enumerate(zip(block, rows)):
            if r_ix == 1:
                expected = "|" + "|".join("-" * (width + 2) for width in widths) + "|"
            else:
                cells = [row[c_ix].ljust(widths[c_ix]) for c_ix in range(ncol)]
                expected = "| " + " | ".join(cells) + " |"
            if line != expected:
                errlist.append(f"{path}:L{start + r_ix + 1}: expected {expected!r}, got {line!r}")
    return errlist


def test_markdown_table_alignment() -> None:
    """Столбцы таблиц выровнены по ширине самой длинной ячейки столбца."""
    root = Path(__file__).resolve().parents[2]
    errlist: list[str] = []
    for path in _iter_markdown_files(root):
        errlist.extend(_table_errors(path))
    assert not errlist, "\n".join(errlist)
