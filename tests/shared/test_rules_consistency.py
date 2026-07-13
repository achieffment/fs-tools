"""Проверяет, что набор и порядок правил синхронны во всех листингах."""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_NAME_RX = r"[a-z][a-z0-9-]*"


def _rule_names(directory: Path, suffix: str) -> set[str]:
    return {path.stem for path in directory.glob(f"*{suffix}")}


def _claude_md_order(text: str) -> list[str]:
    return re.findall(rf"^- \[`\.claude/rules/({_NAME_RX})\.md`\]", text, re.MULTILINE)


def _agents_md_order(text: str) -> list[str]:
    rx = rf"^\| \[{_NAME_RX}\.mdc\]\(\.cursor/rules/({_NAME_RX})\.mdc\)"
    return re.findall(rx, text, re.MULTILINE)


def _rules_sync_order(text: str) -> list[str]:
    return re.findall(rf"^\| `({_NAME_RX})\.mdc`", text, re.MULTILINE)


def test_claude_and_cursor_rule_pairs_symmetric() -> None:
    """Каждому `.claude/rules/*.md` соответствует `.cursor/rules/*.mdc` и наоборот."""
    claude_names = _rule_names(_ROOT / ".claude/rules", ".md")
    cursor_names = _rule_names(_ROOT / ".cursor/rules", ".mdc")
    assert claude_names == cursor_names, (
        f"Несимметричные пары правил: только Claude {claude_names - cursor_names}, "
        f"только Cursor {cursor_names - claude_names}"
    )


def test_rule_listings_share_identical_order() -> None:
    """`CLAUDE.md`, `AGENTS.md` и `rules-sync.md` перечисляют правила в одном порядке."""
    claude_names = _rule_names(_ROOT / ".claude/rules", ".md")
    expected = sorted(claude_names)

    sync_path = _ROOT / ".claude/rules/rules-sync.md"
    claude_order = _claude_md_order((_ROOT / "CLAUDE.md").read_text(encoding="utf-8"))
    agents_order = _agents_md_order((_ROOT / "AGENTS.md").read_text(encoding="utf-8"))
    sync_order = _rules_sync_order(sync_path.read_text(encoding="utf-8"))

    assert sorted(claude_order) == expected, "CLAUDE.md: список правил неполон или устарел"
    assert sorted(agents_order) == expected, "AGENTS.md: таблица правил неполна или устарела"
    assert sorted(sync_order) == expected, "rules-sync.md: карта соответствия неполна или устарела"

    assert claude_order == expected, "CLAUDE.md: порядок правил не алфавитный/не синхронный"
    assert agents_order == expected, "AGENTS.md: порядок правил не алфавитный/не синхронный"
    assert sync_order == expected, "rules-sync.md: порядок правил не алфавитный/не синхронный"


def test_claude_rule_files_reference_cursor_pair() -> None:
    """Каждый `.claude/rules/*.md` (кроме `rules-sync.md`) ссылается на свой `.mdc`."""
    for path in sorted((_ROOT / ".claude/rules").glob("*.md")):
        if path.stem == "rules-sync":
            continue
        text = path.read_text(encoding="utf-8")
        link = f"../../.cursor/rules/{path.stem}.mdc"
        expected = f"> Claude-эквивалент [`.cursor/rules/{path.stem}.mdc`]({link})."
        assert expected in text, f"{path.name}: нет blockquote-ссылки на парный .mdc"


def test_cursor_rule_files_have_frontmatter() -> None:
    """Каждый `.cursor/rules/*.mdc` содержит YAML frontmatter с `description`."""
    for path in sorted((_ROOT / ".cursor/rules").glob("*.mdc")):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{path.name}: нет frontmatter в начале файла"
        frontmatter = text.split("---", 2)[1]
        assert "description:" in frontmatter, f"{path.name}: нет поля description"
        assert "alwaysApply:" in frontmatter or "globs:" in frontmatter, (
            f"{path.name}: нет alwaysApply/globs"
        )
