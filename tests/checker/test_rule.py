"""Тесты разбора .fs-check (rule)."""
from collections.abc import Callable
from pathlib import Path

import pytest

from fs_tools.checker import FsRuleError, Rule, load_fs_rule


def test_missing_file_raises(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии `.fs-check`."""
    with pytest.raises(FsRuleError):
        load_fs_rule(tmp_path)


def test_comments_and_blank_lines_ignored(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: comments and blank lines ignored."""
    root = write_rule(
        "# заголовок\n"
        "\n"
        "/Activities\n"
        "   \n"
        "/Activities/Web/Projects\n"
    )
    fs_rule = load_fs_rule(root)
    assert [r.pattern for r in fs_rule.rules] == ["/Activities", "/Activities/Web/Projects"]


def test_inline_hash_is_literal(write_rule: Callable[[str], Path]) -> None:
    # Срединный `#` — часть имени (комментарий только ведущий).
    """Проверяет сценарий: inline hash is literal."""
    root = write_rule("/C#Notes/Data\n")
    fs_rule = load_fs_rule(root)
    assert fs_rule.rules[0].anchors == ("C#Notes",)
    assert fs_rule.rules[0].require == "Data"


def test_positive_split_literal_and_glob(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: positive split literal and glob."""
    root = write_rule("/Activities/*/Projects\n/Activities/Web/Projects/**/_Archive/*/Back\n")
    fs_rule = load_fs_rule(root)
    first, second = fs_rule.rules
    assert first.anchors == ("Activities", "*")
    assert first.require == "Projects"
    assert second.anchors == ("Activities", "Web", "Projects", "**", "_Archive", "*")
    assert second.require == "Back"


def test_single_segment_empty_prefix(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: single segment empty prefix."""
    root = write_rule("/Activities\n")
    rule = load_fs_rule(root).rules[0]
    assert rule.anchors == ()
    assert rule.require == "Activities"
    assert rule.dirflag is False


def test_trailing_slash_is_dir_only(write_rule: Callable[[str], Path]) -> None:
    # Завершающий `/` распознаётся ДО снятия якорного `/`.
    """Проверяет сценарий: trailing slash is dir only."""
    root = write_rule(
        "/Activities/Web/Projects/Addl/\n"
        "/Activities/Web/Projects/Work/*/*/Data/project.md\n"
    )
    dir_rule, file_rule = load_fs_rule(root).rules
    assert dir_rule.dirflag is True
    assert dir_rule.require == "Addl"
    assert file_rule.dirflag is False
    assert file_rule.require == "project.md"


def test_negatives_go_to_pathspec_not_rules(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negatives go to pathspec not rules."""
    root = write_rule("/Activities/*/Projects\n!_Archive\n")
    fs_rule = load_fs_rule(root)
    # Положительное правило — одно; негатив в правила не попал.
    assert [r.pattern for r in fs_rule.rules] == ["/Activities/*/Projects"]
    # Негатив прунит имя _Archive, но не обычный проект.
    assert fs_rule.negation.is_pruned("_Archive") is True
    assert fs_rule.negation.is_pruned("crm.example.com") is False


def test_negation_glob_pattern(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation glob pattern."""
    root = write_rule("!_Archive*\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned("_Archive_01") is True
    assert negation.is_pruned("_Archive") is True
    assert negation.is_pruned("Archive") is False


def test_no_negatives_prunes_nothing(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: no negatives prunes nothing."""
    root = write_rule("/Activities\n")
    assert load_fs_rule(root).negation.is_pruned("_Archive") is False


def test_utf8_sig_bom_does_not_break_first_line(tmp_path: Path) -> None:
    """Проверяет сценарий: utf8 sig bom does not break first line."""
    (tmp_path / ".fs-check").write_text("/Activities\n", encoding="utf-8-sig")
    rule = load_fs_rule(tmp_path).rules[0]
    assert rule.require == "Activities"  # BOM не прилип к первому сегменту


def test_escaped_trailing_space_preserved(write_rule: Callable[[str], Path]) -> None:
    # `\ ` сохраняет значимый конечный пробел в имени мандата.
    """Проверяет сценарий: escaped trailing space preserved."""
    root = write_rule("/dir/name\\ \n")
    rule = load_fs_rule(root).rules[0]
    assert rule.require == "name "


def test_unescaped_trailing_space_trimmed(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: unescaped trailing space trimmed."""
    root = write_rule("/Activities/Web   \n")
    rule = load_fs_rule(root).rules[0]
    assert rule.require == "Web"


def test_rule_from_pattern_without_anchor() -> None:
    """Проверяет разбор правила без ведущего якоря `/`."""
    # Правило без ведущего `/` тоже якорное (strip снимает оба `/`).
    rule = Rule.from_pattern("Activities/Resources/")
    assert rule.anchors == ("Activities",)
    assert rule.require == "Resources"
    assert rule.dirflag is True
