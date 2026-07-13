"""Проверяет выравнивание inline-комментариев в файлах *.toml.

Общая механика флаша (`comment_align.AlignmentGroup`) — та же, что у командных
fenced-блоков Markdown (`test_markdown_comments.py`), но профиль другой:
подблок — строки между пустыми строками, опорная колонка — самая длинная
строка подблока **среди строк с inline-комментарием** (`include_plain=False`;
несвязанные строки кода вроде `default_rule = {...}` не утягивают одиночный
далёкий комментарий) + 2 (`pad=2`, компактнее markdown-профиля), и выравнивание
обязательно уже при одной такой строке (`min_rows=1`) — иначе это просто
минимальный отступ. В отличие от Markdown, `#` внутри TOML-строки
(`text = "# Заметки"`) — литерал, а не начало комментария, поэтому граница
ищется с учётом кавычек, а не регэкспом.
"""
from __future__ import annotations

from pathlib import Path

from tests.shared.comment_align import AlignmentGroup


def _iter_toml_files(root: Path) -> list[Path]:
    files = sorted(root.rglob("*.toml"))
    return [path for path in files if ".venv" not in path.parts and ".scratch" not in path.parts]


def _comment_start(line: str) -> int:
    """Индекс первого `#` вне строкового литерала, либо -1."""
    in_str: str | None = None
    ix = 0
    while ix < len(line):
        ch = line[ix]
        if in_str:
            if ch == "\\" and in_str == '"':
                ix = ix + 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ("\"", "'"):
            in_str = ch
        elif ch == "#":
            return ix
        ix = ix + 1
    return -1


def _file_errors(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    group = AlignmentGroup(pad=2, min_rows=1, include_plain=False)
    errlist: list[str] = []

    def flush_group() -> None:
        for lineno, hash_pos, target, text in group.flush():
            errlist.append(f"{path}:L{lineno}: '#' at {hash_pos}, expected {target}: {text}")

    for ix, text in enumerate(lines, 1):
        bare = text.rstrip()
        if not bare:
            flush_group()
            continue
        if bare.lstrip().startswith("#"):
            continue
        pos = _comment_start(text)
        if pos < 0 or not text[:pos].strip():
            group.add_plain(len(bare))
            continue
        group.add_commented(ix, pos, len(text[:pos].rstrip()), text)
    flush_group()
    return errlist


def test_toml_inline_comment_alignment() -> None:
    """Inline-комментарии в *.toml выровнены в одну колонку внутри локального блока."""
    root = Path(__file__).resolve().parents[2]
    errlist: list[str] = []
    for path in _iter_toml_files(root):
        errlist.extend(_file_errors(path))
    assert not errlist, "\n".join(errlist)
