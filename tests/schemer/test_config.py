"""Тесты разбора/валидации .fs-sch.toml (config)."""
from collections.abc import Callable
from pathlib import Path

import pytest

from fs_tools.schemer import SchemeConfigError, load_scheme_config, parse_scheme_config


def test_missing_file_raises(tmp_path: Path) -> None:
    """Проверяет ошибку при отсутствии .fs-sch.toml."""
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
    assert group.strict is False


def test_strict_defaults_false(write_scheme_toml: Callable[[str], Path]) -> None:
    """strict не задан -> False (вложенность внутри группы разрешена по умолчанию)."""
    root = write_scheme_toml('[[group]]\nname = "G"\n')
    group = load_scheme_config(root).group_by_name("G")
    assert group is not None
    assert group.strict is False


def test_strict_true_parsed(write_scheme_toml: Callable[[str], Path]) -> None:
    """strict = true разбирается в Group.strict."""
    root = write_scheme_toml('[[group]]\nname = "_Commands"\nstrict = true\n')
    group = load_scheme_config(root).group_by_name("_Commands")
    assert group is not None
    assert group.strict is True


def test_strict_non_bool_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """strict не bool -> SchemeConfigError."""
    root = write_scheme_toml('[[group]]\nname = "G"\nstrict = "yes"\n')
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


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
    (main_file,) = group.files_by_name("_main.md")
    (optional_file,) = group.files_by_name("_commands.md")
    assert main_file.optional is False
    assert main_file.rule.line == 1 and main_file.rule.text == "# Заметки"
    assert optional_file.optional is True


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


def test_default_rule_extensions_parsed(write_scheme_toml: Callable[[str], Path]) -> None:
    """default_rule.extensions разбирается в frozenset (нормализация в нижний регистр)."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "_Blueprints"\n'
        'default_rule = { line = 1, text = "# Шаблоны", extensions = [".MD", ".txt"] }\n'
    )
    group = load_scheme_config(root).group_by_name("_Blueprints")
    assert group is not None
    assert group.default_rule is not None
    assert group.default_rule.extensions == frozenset({".md", ".txt"})
    assert group.default_rule.exclude_extensions is None


def test_default_rule_exclude_extensions_parsed(write_scheme_toml: Callable[[str], Path]) -> None:
    """default_rule.exclude_extensions разбирается в frozenset."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "G"\n'
        'default_rule = { line = 1, text = "x", exclude_extensions = [".bin"] }\n'
    )
    group = load_scheme_config(root).group_by_name("G")
    assert group is not None
    assert group.default_rule is not None
    assert group.default_rule.exclude_extensions == frozenset({".bin"})
    assert group.default_rule.extensions is None


def test_default_rule_extensions_and_exclude_together_parsed(
    write_scheme_toml: Callable[[str], Path],
) -> None:
    """extensions и exclude_extensions можно задать одновременно (комбинируются)."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "G"\n'
        'default_rule = { line = 1, text = "x", extensions = [".md", ".txt"], '
        'exclude_extensions = [".txt"] }\n'
    )
    group = load_scheme_config(root).group_by_name("G")
    assert group is not None
    assert group.default_rule is not None
    assert group.default_rule.extensions == frozenset({".md", ".txt"})
    assert group.default_rule.exclude_extensions == frozenset({".txt"})


def test_default_rule_extensions_empty_list_raises(
    write_scheme_toml: Callable[[str], Path],
) -> None:
    """extensions — пустой список -> ошибка (список без значений бессмысленен)."""
    root = write_scheme_toml(
        '[[group]]\nname = "G"\ndefault_rule = { line = 1, text = "x", extensions = [] }\n'
    )
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_default_rule_extensions_without_dot_raises(
    write_scheme_toml: Callable[[str], Path],
) -> None:
    """Элемент extensions без ведущей точки -> ошибка."""
    root = write_scheme_toml(
        '[[group]]\nname = "G"\ndefault_rule = { line = 1, text = "x", extensions = ["md"] }\n'
    )
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


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


def test_group_file_duplicate_name_parsed(
    write_scheme_toml: Callable[[str], Path],
) -> None:
    """Несколько [[group.file]] с одинаковым name — валидно, обе записи сохраняются."""
    root = write_scheme_toml(
        '[[group]]\n'
        'name = "G"\n\n'
        '  [[group.file]]\n'
        '  name = "a.md"\n'
        '  line = 1\n'
        '  text = "x"\n\n'
        '  [[group.file]]\n'
        '  name = "a.md"\n'
        '  line = 2\n'
        '  text = "y"\n'
    )
    group = load_scheme_config(root).group_by_name("G")
    assert group is not None
    first, second = group.files_by_name("a.md")
    assert (first.rule.line, first.rule.text) == (1, "x")
    assert (second.rule.line, second.rule.text) == (2, "y")


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


def test_apply_root_default_none(write_scheme_toml: Callable[[str], Path]) -> None:
    """apply_root не задан -> None (каталог проверки = каталог конфига)."""
    root = write_scheme_toml('[[group]]\nname = "G"\n')
    assert load_scheme_config(root).apply_root is None


def test_apply_root_parsed(write_scheme_toml: Callable[[str], Path]) -> None:
    """[defaults].apply_root разбирается как сырая строка (без резолвинга пути)."""
    root = write_scheme_toml(
        '[defaults]\napply_root = "../Warehouse"\n\n[[group]]\nname = "G"\n'
    )
    assert load_scheme_config(root).apply_root == "../Warehouse"


def test_apply_root_empty_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """Пустая строка apply_root -> SchemeConfigError."""
    root = write_scheme_toml('[defaults]\napply_root = ""\n\n[[group]]\nname = "G"\n')
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)


def test_apply_root_non_str_raises(write_scheme_toml: Callable[[str], Path]) -> None:
    """apply_root не строка -> SchemeConfigError."""
    root = write_scheme_toml('[defaults]\napply_root = 1\n\n[[group]]\nname = "G"\n')
    with pytest.raises(SchemeConfigError):
        load_scheme_config(root)
