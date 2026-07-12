"""Тесты разбора .fs-chk (rule)."""
from collections.abc import Callable
from pathlib import Path

import pytest

from fs_tools.checker import FsRuleError, Rule, load_fs_rule


def test_missing_file_raises(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии `.fs-chk`."""
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
    # Единый pathspec-канал: _Archive отсекается как basename-паттерн.
    assert fs_rule.negation.is_pruned_path(Path("Activities/Web/_Archive"), is_dir=True) is True
    assert fs_rule.negation.is_pruned_path(Path("Activities/Web/Projects"), is_dir=True) is False


def test_negation_glob_pattern(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation glob pattern."""
    root = write_rule("!_Archive*\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Activities/_Archive_01"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Activities/_Archive"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Activities/Archive"), is_dir=True) is False


def test_no_negatives_prunes_nothing(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: no negatives prunes nothing."""
    root = write_rule("/Activities\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Activities/Web"), is_dir=True) is False


def test_negation_path_anchored_match(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation path anchored match."""
    root = write_rule("/Workspace/*/Projects\n!/Workspace/Code/Projects\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Workspace/Code/Projects"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Workspace/Database/Projects"), is_dir=True) is False


def test_negation_path_basename_anywhere(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation path basename anywhere."""
    root = write_rule("/Workspace/*/Projects\n!**/Code\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Workspace/Code"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Workspace/Web"), is_dir=True) is False


def test_negation_path_mask_double_star(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation path mask double star."""
    root = write_rule("/Code/*/Projects\n!/Code/PHP/**\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Code/PHP"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Code/PHP/Legacy/Projects"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Code/Python"), is_dir=True) is False


def test_negation_path_mask_single_char_and_star(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation path mask single char and star."""
    root = write_rule("/Code/*/Projects\n!/Code/*/v?ndor\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Code/PHP/vendor"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Code/PHP/vxndor"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Code/PHP/vndor"), is_dir=True) is False


def test_negation_order_last_match_wins(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation order last match wins."""
    root = write_rule("/Code/*/Projects\n!/Code/**\n!!/Code/PHP/**\n")
    negation = load_fs_rule(root).negation
    assert negation.is_pruned_path(Path("Code/Python/Projects"), is_dir=True) is True
    assert negation.is_pruned_path(Path("Code/PHP/Projects"), is_dir=True) is True


def test_negation_double_bang_equals_single_bang(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation double bang equals single bang."""
    root1 = write_rule("!/Code/PHP/**\n")
    root2 = write_rule("!!/Code/PHP/**\n")
    neg1 = load_fs_rule(root1).negation
    neg2 = load_fs_rule(root2).negation
    probe = Path("Code/PHP/Projects")
    assert neg1.is_pruned_path(probe, is_dir=True) is True
    assert neg2.is_pruned_path(probe, is_dir=True) is True


def test_negation_triple_bang_equals_single_bang(write_rule: Callable[[str], Path]) -> None:
    """Проверяет сценарий: negation triple bang equals single bang."""
    root1 = write_rule("!_Archive\n")
    root2 = write_rule("!!!_Archive\n")
    neg1 = load_fs_rule(root1).negation
    neg2 = load_fs_rule(root2).negation
    probe = Path("Activities/Web/_Archive")
    assert neg1.is_pruned_path(probe, is_dir=True) is True
    assert neg2.is_pruned_path(probe, is_dir=True) is True


def test_utf8_sig_bom_does_not_break_first_line(tmp_path: Path) -> None:
    """Проверяет сценарий: utf8 sig bom does not break first line."""
    (tmp_path / ".fs-chk").write_text("/Activities\n", encoding="utf-8-sig")
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
