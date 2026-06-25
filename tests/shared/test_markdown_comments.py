"""Проверяет выравнивание inline-комментариев в fenced-блоках Markdown."""
from __future__ import annotations

import re
from pathlib import Path

_INLINE = re.compile(r"^(?P<base>.*\S)(?P<spaces>\s+)#\s.*$")
_LANGS = {"bash", "sh", "shell", "powershell", "pwsh", "bat", "cmd"}


def _iter_markdown_files(root: Path) -> list[Path]:
    files = sorted(root.rglob("*.md"))
    return [path for path in files if ".venv" not in path.parts and ".scratch" not in path.parts]


def _block_errors(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_fence = False
    is_cmd_fence = False
    block: list[str] = []
    start = 0
    errlist: list[str] = []

    def check_block(block_lines: list[str], start_line: int) -> None:
        rows: list[tuple[int, int, int, str]] = []
        base_len: list[int] = []

        def flush_group() -> None:
            if len(rows) < 2:
                rows.clear()
                base_len.clear()
                return
            target = max(base_len) + 4
            for ix, _base_size, hash_pos, text in rows:
                if hash_pos != target:
                    errlist.append(
                        f"{path}:L{ix}: '#' at {hash_pos}, expected {target}: {text}"
                    )
            rows.clear()
            base_len.clear()

        for ix, text in enumerate(block_lines, start_line):
            bare = text.rstrip()
            if not bare:
                flush_group()
                continue
            if bare.lstrip().startswith("#"):
                continue

            match = _INLINE.match(text)
            if match is None:
                base_len.append(len(bare))
                continue
            curr_len = len(match.group("base"))
            base_len.append(curr_len)
            rows.append((ix, curr_len, text.index("#"), text))
        flush_group()

    for ix, text in enumerate(lines, 1):
        if text.strip().startswith("```"):
            if in_fence:
                if is_cmd_fence:
                    check_block(block, start)
                in_fence = False
                is_cmd_fence = False
                block = []
            else:
                in_fence = True
                fence = text.strip()[3:].strip().lower()
                is_cmd_fence = fence in _LANGS
                start = ix + 1
                block = []
            continue
        if in_fence:
            block.append(text)
    return errlist


def test_markdown_inline_comment_alignment() -> None:
    """Inline-комментарии в fenced-блоках выровнены в одну колонку."""
    root = Path(__file__).resolve().parents[2]
    errlist: list[str] = []
    for path in _iter_markdown_files(root):
        errlist.extend(_block_errors(path))
    assert not errlist, "\n".join(errlist)
