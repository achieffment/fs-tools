"""Тесты разбора .fs-check (rule)."""
from collections.abc import Callable
from pathlib import Path

import pytest

from fs_tools.checker import FsRuleError, Rule, load_fs_rule


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FsRuleError):
        load_fs_rule(tmp_path)


def test_comments_and_blank_lines_ignored(write_rule: Callable[[str], Path]) -> None:
    root = write_rule(
        "# заголовок\n"
        "\n"
        "/Activities\n"
        "   \n"
        "/Activities/Web/Projects\n"
    )
    fs_rule = load_fs_rule(root)
    assert [r.raw for r in fs_rule.rules] == ["/Activities", "/Activities/Web/Projects"]


def test_inline_hash_is_literal(write_rule: Callable[[str], Path]) -> None:
    # Срединный `#` — часть имени (комментарий только ведущий).
    root = write_rule("/C#Notes/Data\n")
    fs_rule = load_fs_rule(root)
    assert fs_rule.rules[0].prefix == ("C#Notes",)
    assert fs_rule.rules[0].mandate == "Data"


def test_positive_split_literal_and_glob(write_rule: Callable[[str], Path]) -> None:
    root = write_rule("/Activities/*/Projects\n/Activities/Web/Projects/**/_Archive/*/Back\n")
    fs_rule = load_fs_rule(root)
    first, second = fs_rule.rules
    assert first.prefix == ("Activities", "*")
    assert first.mandate == "Projects"
    assert second.prefix == ("Activities", "Web", "Projects", "**", "_Archive", "*")
    assert second.mandate == "Back"


def test_single_segment_empty_prefix(write_rule: Callable[[str], Path]) -> None:
    root = write_rule("/Activities\n")
    rule = load_fs_rule(root).rules[0]
    assert rule.prefix == ()
    assert rule.mandate == "Activities"
    assert rule.dir_only is False


def test_trailing_slash_is_dir_only(write_rule: Callable[[str], Path]) -> None:
    # Завершающий `/` распознаётся ДО снятия якорного `/`.
    root = write_rule("/Activities/Web/Projects/Addl/\n/Activities/Web/Projects/Work/*/*/Data/project.md\n")
    dir_rule, file_rule = load_fs_rule(root).rules
    assert dir_rule.dir_only is True
    assert dir_rule.mandate == "Addl"
    assert file_rule.dir_only is False
    assert file_rule.mandate == "project.md"


def test_negatives_go_to_pathspec_not_rules(write_rule: Callable[[str], Path]) -> None:
    root = write_rule("/Activities/*/Projects\n!_Archive\n")
    fs_rule = load_fs_rule(root)
    # Положительное правило — одно; негатив в правила не попал.
    assert [r.raw for r in fs_rule.rules] == ["/Activities/*/Projects"]
    # Негатив прунит имя _Archive, но не обычный проект.
    assert fs_rule.negation.is_pruned("_Archive") is True
    assert fs_rule.negation.is_pruned("crm.example.com") is False


def test_negation_glob_pattern(write_rule: Callable[[str], Path]) -> None:
    root = write_rule("!_Archive*\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned("_Archive_01") is True
    assert negation.is_pruned("_Archive") is True
    assert negation.is_pruned("Archive") is False


def test_no_negatives_prunes_nothing(write_rule: Callable[[str], Path]) -> None:
    root = write_rule("/Activities\n")
    assert load_fs_rule(root).negation.is_pruned("_Archive") is False


def test_utf8_sig_bom_does_not_break_first_line(tmp_path: Path) -> None:
    (tmp_path / ".fs-check").write_text("/Activities\n", encoding="utf-8-sig")
    rule = load_fs_rule(tmp_path).rules[0]
    assert rule.mandate == "Activities"  # BOM не прилип к первому сегменту


def test_escaped_trailing_space_preserved(write_rule: Callable[[str], Path]) -> None:
    # `\ ` сохраняет значимый конечный пробел в имени мандата.
    root = write_rule("/dir/name\\ \n")
    rule = load_fs_rule(root).rules[0]
    assert rule.mandate == "name "


def test_unescaped_trailing_space_trimmed(write_rule: Callable[[str], Path]) -> None:
    root = write_rule("/Activities/Web   \n")
    rule = load_fs_rule(root).rules[0]
    assert rule.mandate == "Web"


def test_rule_from_pattern_without_anchor() -> None:
    # Правило без ведущего `/` тоже якорное (strip снимает оба `/`).
    rule = Rule.from_pattern("Activities/Resources/")
    assert rule.prefix == ("Activities",)
    assert rule.mandate == "Resources"
    assert rule.dir_only is True
