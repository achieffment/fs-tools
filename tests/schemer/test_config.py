"""Тесты разбора/валидации fs-schm.toml (config)."""
from collections.abc import Callable
from pathlib import Path

import pytest

from fs_tools.schemer import SchemeConfigError, load_scheme_config, parse_scheme_config


def test_missing_file_raises(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии fs-schm.toml."""
    with pytest.raises(SchemeConfigError):
        load_scheme_config(tmp_path)


def test_minimal_group_without_files(write_scheme_toml: Callable[[str], Path]) -> None:
    """Группа без [[group.file]] и без default_rule — валидна (как _Resources)."""
    root = write_scheme_toml('[[group]]\nname = "_Resources"\n')
    config = load_scheme_config(root)
    assert config.exclude_prefix == "_"
    group = config.group_by_name("_Resources")
    assert group is not None
    assert group.default_rule is None
    assert group.files == ()


def test_default_exclude_prefix(write_scheme_toml: Callable[[str], Path]) -> None:
    """Дефолт exclude_prefix — '_', если [defaults] не задан."""
    root = write_scheme_toml('[[group]]\nname = "G"\n')
    assert load_scheme_config(root).exclude_prefix == "_"


def test_custom_exclude_prefix(write_scheme_toml: Callable[[str], Path]) -> None:
    """[defaults].exclude_prefix переопределяет дефолт."""
    root = write_scheme_toml('[defaults]\nexclude_prefix = "."\n\n[[group]]\nname = "G"\n')
    assert load_scheme_config(root).exclude_prefix == "."


def test_group_file_required_and_optional(write_scheme_toml: Callable[[str], Path]) -> None:
    """Обязательность выражается одним механизмом group.file (optional по умолчанию false)."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "_Knowledges"\n\n'
        '  [[group.file]]\n'
        '  name = "_main.md"\n'
        '  line = 1\n'
        '  text = "# Заметки"\n\n'
        '  [[group.file]]\n'
        '  name = "_commands.md"\n'
        '  optional = true\n'
        '  line = 1\n'
        '  text = "# Команды"\n'
    )
    group = load_scheme_config(root).group_by_name("_Knowledges")
    assert group is not None
    main_file = group.file_by_name("_main.md")
    optional_file = group.file_by_name("_commands.md")
    assert main_file is not None and main_file.optional is False
    assert main_file.rule.line == 1 and main_file.rule.text == "# Заметки"
    assert optional_file is not None and optional_file.optional is True


def test_default_rule_parsed(write_scheme_toml: Callable[[str], Path]) -> None:
    """default_rule группы разбирается в ContentRule."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "_Knowledges"\n'
        'default_rule = { line = 1, text = "# Заметки" }\n'
    )
    group = load_scheme_config(root).group_by_name("_Knowledges")
    assert group is not None
    assert group.default_rule is not None
    assert (group.default_rule.line, group.default_rule.text) == (1, "# Заметки")


def test_group_name_not_unique_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """Дублирующееся имя группы — ошибка."""
    root = write_scheme_toml('[[group]]\nname = "G"\n\n[[group]]\nname = "G"\n')
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_group_name_with_slash_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """name с «/» — ошибка (basename, не путь)."""
    root = write_scheme_toml('[[group]]\nname = "A/B"\n')
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_group_file_name_not_unique_in_group_raises(
    write_scheme_toml: Callable[[str], Path],
) -> None:
    """Дублирующееся имя файла внутри одной группы — ошибка."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "G"\n\n'
        '  [[group.file]]\n'
        '  name = "a.md"\n'
        '  line = 1\n'
        '  text = "x"\n\n'
        '  [[group.file]]\n'
        '  name = "a.md"\n'
        '  line = 1\n'
        '  text = "y"\n'
    )
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_group_file_missing_line_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """line обязателен в [[group.file]]."""
    root = write_scheme_toml(
        '[[group]]\nname = "G"\n\n  [[group.file]]\n  name = "a.md"\n  text = "x"\n'
    )
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_group_file_empty_text_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """text не может быть пустым."""
    root = write_scheme_toml(
        '[[group]]\nname = "G"\n\n  [[group.file]]\n  name = "a.md"\n  line = 1\n  text = ""\n'
    )
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_group_file_line_below_one_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """line должен быть ≥ 1."""
    root = write_scheme_toml(
        '[[group]]\nname = "G"\n\n  [[group.file]]\n  name = "a.md"\n  line = 0\n  text = "x"\n'
    )
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_no_groups_at_all_is_valid(write_scheme_toml: Callable[[str], Path]) -> None:
    """Конфиг без единой [[group]] — валиден (пустой список групп)."""
    root = write_scheme_toml("[defaults]\nexclude_prefix = \"_\"\n")
    assert not load_scheme_config(root).groups


def test_invalid_toml_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """Некорректный синтаксис TOML — ошибка."""
    root = write_scheme_toml("not = [valid\n")
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_parse_scheme_config_without_reading_file() -> None:
    """parse_scheme_config работает над текстом напрямую (без чтения файла)."""
    config = parse_scheme_config('[[group]]\nname = "G"\n')
    assert [group.name for group in config.groups] == ["G"]
