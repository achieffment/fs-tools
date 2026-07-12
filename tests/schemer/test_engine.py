"""Тесты обхода и сбора нарушений (engine): по одному кейсу на F1–F15."""
import os
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from fs_tools.schemer import FsSchemer, parse_scheme_config

_CONFIG = """
[defaults]
exclude_prefix = "_"

[[group]]
name = "_Knowledges"
default_rule = { line = 1, text = "# Заметки" }

  [[group.file]]
  name = "_main.md"
  line = 1
  text = "# Заметки"

  [[group.file]]
  name = "_commands.md"
  optional = true
  line = 1
  text = "# Команды"

  [[group.file]]
  name = "rules.md"
  optional = true
  line = 3
  text = "## Правила"

[[group]]
name = "_Commands"
default_rule = { line = 1, text = "# Команды" }

  [[group.file]]
  name = "_main.md"
  line = 1
  text = "# Команды"

[[group]]
name = "_Blueprints"
default_rule = { line = 1, text = "# Шаблоны" }

  [[group.file]]
  name = "_devs.md"
  optional = true
  line = 1
  text = "# Наработки"

[[group]]
name = "_Resources"
"""


def _kinds(root: Path) -> dict[str, str]:
    """path -> kind для каждого нарушения (удобно для точечных assert)."""
    result = FsSchemer(parse_scheme_config(_CONFIG)).check(root)
    return {vio.path: vio.kind for vio in result.violations}


def _write(tree_root: Path, rel: str, content: str) -> None:
    target = tree_root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def test_f1_f2_main_missing_and_present(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F1: _main.md обязателен в _Knowledges; F2: контент строки 1 проверяется."""
    root = make_tree(["Topic/_Knowledges/"])
    kinds = _kinds(root)
    assert kinds["Topic/_Knowledges/_main.md"] == "missing_group_file"

    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    assert "Topic/_Knowledges/_main.md" not in _kinds(root)


def test_f2_bad_header_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F2: неверный заголовок _main.md -> bad_header."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Другое\n")
    assert _kinds(root)["Topic/_Knowledges/_main.md"] == "bad_header"


def test_f3_default_rule_applies_to_plain_file(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F3: обычный файл (не начинающийся с _) сверяется с default_rule группы."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    _write(root, "Topic/_Knowledges/note.md", "# Другое\n")
    assert _kinds(root)["Topic/_Knowledges/note.md"] == "bad_header"


def test_f4_f5_commands_main_required(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F4/F5: _main.md обязателен в _Commands, строка 1 == '# Команды'."""
    root = make_tree(["Topic/_Commands/"])
    assert _kinds(root)["Topic/_Commands/_main.md"] == "missing_group_file"
    _write(root, "Topic/_Commands/_main.md", "# Команды\n")
    assert "Topic/_Commands/_main.md" not in _kinds(root)


def test_f6_default_rule_commands(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F6: обычный файл в _Commands сверяется с '# Команды'."""
    root = make_tree(["Topic/_Commands/"])
    _write(root, "Topic/_Commands/_main.md", "# Команды\n")
    _write(root, "Topic/_Commands/cmd.md", "# Команды\n")
    assert "Topic/_Commands/cmd.md" not in _kinds(root)


def test_f7_devs_optional_content_checked_when_present(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """F7: _devs.md опционален; отсутствие не нарушение, наличие с плохим текстом — да."""
    root = make_tree(["Topic/_Blueprints/blueprint.md"])
    _write(root, "Topic/_Blueprints/blueprint.md", "# Шаблоны\n")
    assert "Topic/_Blueprints/_devs.md" not in _kinds(root)  # отсутствие — не нарушение

    _write(root, "Topic/_Blueprints/_devs.md", "# Плохо\n")
    assert _kinds(root)["Topic/_Blueprints/_devs.md"] == "bad_header"


def test_f8_default_rule_blueprints(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F8: обычный файл в _Blueprints сверяется с '# Шаблоны'."""
    root = make_tree(["Topic/_Blueprints/"])
    _write(root, "Topic/_Blueprints/tpl.md", "# Шаблоны\n")
    assert "Topic/_Blueprints/tpl.md" not in _kinds(root)


def test_f9_commands_md_optional_in_knowledges(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F9: _commands.md в _Knowledges опционален, при наличии проверяется."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    _write(root, "Topic/_Knowledges/_commands.md", "# Не то\n")
    assert _kinds(root)["Topic/_Knowledges/_commands.md"] == "bad_header"


def test_f10_rules_md_line_three(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F10: rules.md опционален, строка 3 == '## Правила'."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    _write(root, "Topic/_Knowledges/rules.md", "line1\nline2\n## Правила\n")
    assert "Topic/_Knowledges/rules.md" not in _kinds(root)


def test_missing_line_shorter_than_required(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Файл короче нужного числа строк -> missing_line."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    _write(root, "Topic/_Knowledges/rules.md", "line1\n")
    assert _kinds(root)["Topic/_Knowledges/rules.md"] == "missing_line"


def test_non_utf8_content_reports_read_error(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Файл без валидного UTF-8 не роняет обход -> read_error (не missing_line)."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    (root / "Topic/_Knowledges/rules.md").write_bytes(b"\xb2\xff\x00")
    assert _kinds(root)["Topic/_Knowledges/rules.md"] == "read_error"


@pytest.mark.skipif(os.name != "posix", reason="права файла проверяются только на POSIX")
def test_unreadable_file_reports_read_error(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """OSError при чтении (нет прав) -> read_error, а не missing_line."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    target = root / "Topic/_Knowledges/rules.md"
    _write(root, "Topic/_Knowledges/rules.md", "line1\nline2\n## Правила\n")
    target.chmod(0o000)
    try:
        result = FsSchemer(parse_scheme_config(_CONFIG)).check(root)
    finally:
        target.chmod(0o644)  # иначе tmp_path не сможет удалить дерево при уборке
    matches = [vio for vio in result.violations if vio.path == "Topic/_Knowledges/rules.md"]
    assert len(matches) == 1
    assert matches[0].kind == "read_error"
    assert matches[0].actual


def test_f14_empty_group_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F14: полностью пустая группа (без файлов, даже вложенных) -> empty_group."""
    root = make_tree(["Topic/_Resources/"])
    assert _kinds(root)["Topic/_Resources"] == "empty_group"


def test_f14_nested_visible_file_not_empty(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F14: видимый файл во вложенной подпапке группы тоже снимает 'пусто'."""
    root = make_tree(["Topic/_Resources/Sub/"])
    _write(root, "Topic/_Resources/Sub/file.txt", "x")
    assert "Topic/_Resources" not in _kinds(root)


def test_f15_loose_file_in_theme_node_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """F15: файл напрямую в тематическом узле (не в групповой папке) — нарушение."""
    root = make_tree(["Topic/"])
    _write(root, "Topic/note.md", "text")
    assert _kinds(root)["Topic/note.md"] == "loose_file"


def test_f15_file_inside_group_not_loose(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Файлы внутри групповой папки не считаются loose_file."""
    root = make_tree(["Topic/_Resources/"])
    _write(root, "Topic/_Resources/x.pdf", "x")
    assert "Topic/_Resources/x.pdf" not in _kinds(root)


def test_default_group_exempts_nested_subfolders_from_f15(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """strict по умолчанию false: файл во вложенной подпапке группы не даёт loose_file."""
    config = parse_scheme_config('[[group]]\nname = "_Resources"\n')
    root = make_tree(["Topic/_Resources/Lib/Sub/"])
    _write(root, "Topic/_Resources/Lib/Sub/asset.bin", "x")
    result = FsSchemer(config).check(root)
    assert not result.violations


def test_strict_group_still_reports_f15_in_subfolders(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """strict=true: подпапки группы заново классифицируются, F15 в них работает."""
    config = parse_scheme_config('[[group]]\nname = "_Resources"\nstrict = true\n')
    root = make_tree(["Topic/_Resources/Lib/Sub/"])
    _write(root, "Topic/_Resources/Lib/Sub/asset.bin", "x")
    result = FsSchemer(config).check(root)
    assert {vio.path: vio.kind for vio in result.violations} == {
        "Topic/_Resources/Lib/Sub/asset.bin": "loose_file",
    }


def test_non_strict_group_direct_children_still_checked(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """strict по умолчанию false: group.file для прямых детей группы проверяется как обычно."""
    config = parse_scheme_config(
        '[[group]]\n'
        'name = "_Resources"\n\n'
        '  [[group.file]]\n'
        '  name = "_main.md"\n'
        '  line = 1\n'
        '  text = "# Ресурсы"\n'
    )
    root = make_tree(["Topic/_Resources/Lib/"])
    _write(root, "Topic/_Resources/Lib/asset.bin", "x")
    result = FsSchemer(config).check(root)
    assert {vio.path: vio.kind for vio in result.violations} == {
        "Topic/_Resources/_main.md": "missing_group_file",
    }


def test_fs_sch_toml_in_root_excluded_from_f15(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """.fs-sch.toml в корне не даёт ложный loose_file — он скрытый (ведущая точка)."""
    root = make_tree(["_Resources/"])
    (root / ".fs-sch.toml").write_text('[[group]]\nname = "_Resources"\n', encoding="utf-8")
    result = FsSchemer(parse_scheme_config(_CONFIG)).check(root)
    assert ".fs-sch.toml" not in {vio.path for vio in result.violations}


def test_hidden_group_not_visited(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Скрытые каталоги не обходим: группа под '.' не проверяется."""
    root = make_tree(["Topic/.hidden/_Resources/"])
    assert not FsSchemer(parse_scheme_config(_CONFIG)).check(root).violations


def test_counters_groups_and_files_checked(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Счётчики groups_checked/files_checked отражают фактический охват."""
    root = make_tree(["Topic/_Knowledges/"])
    _write(root, "Topic/_Knowledges/_main.md", "# Заметки\n")
    result = FsSchemer(parse_scheme_config(_CONFIG)).check(root)
    assert result.groups_checked == 1
    assert result.files_checked == 1  # только _main.md — единственный видимый файл
    assert not result.violations
