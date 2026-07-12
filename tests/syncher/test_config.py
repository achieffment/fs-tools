"""Тесты config: разбор TOML, дефолты, валидация, разбор remote_root."""
from pathlib import Path

import pytest

from fs_tools.syncher import (
    Config,
    ConfigError,
    is_ssh_target,
    load_config,
    parse_config,
    split_target,
)


def _toml(target: str = "/srv/dst", extra: str = "") -> str:
    """Вспомогательная функция для теста."""
    return (
        "[[sync]]\n"
        "name = \"main\"\n"
        "local_root = \".\"\n"
        f'remote_root = "{target}"\n'
        f"{extra}"
    )


def test_parse_minimal_sync(tmp_path: Path) -> None:
    """Проверяет сценарий: parse minimal sync."""
    config = parse_config(_toml(), tmp_path)
    assert isinstance(config, Config)
    assert len(config.roll) == 1
    profile = config.roll[0]
    assert profile.name == "main"
    assert profile.kind == "sync"
    assert profile.source_path == tmp_path.resolve()
    assert profile.delete is True            # дефолт для sync
    assert profile.dry_run is False
    assert profile.delete_threshold == 100
    assert profile.delete_threshold_pct == 25.0
    assert profile.verify is True


def test_backup_delete_default_false(tmp_path: Path) -> None:
    """Проверяет сценарий: backup delete default false."""
    text = (
        "[[backup]]\n"
        "name = \"bak\"\n"
        "local_root = \".\"\n"
        "remote_root = \"/srv/bak\"\n"
    )
    config = parse_config(text, tmp_path)
    profile = config.roll[0]
    assert profile.kind == "backup"
    assert profile.delete is False           # дефолт для backup
    assert profile.after_push == "nothing"


def test_defaults_section_applied_and_overridden(tmp_path: Path) -> None:
    """Проверяет сценарий: defaults section applied and overridden."""
    text = (
        "[defaults]\n"
        "compress = true\n"
        "delete_threshold = 50\n"
        "[[sync]]\n"
        "name = \"a\"\n"
        "local_root = \".\"\n"
        "remote_root = \"/srv/a\"\n"
        "[[sync]]\n"
        "name = \"b\"\n"
        "local_root = \".\"\n"
        "remote_root = \"/srv/b\"\n"
        "delete_threshold = 5\n"
    )
    config = parse_config(text, tmp_path)
    a, b = config.roll
    assert a.compress is True and a.delete_threshold == 50
    assert b.compress is True and b.delete_threshold == 5   # профиль перекрыл defaults


def test_local_root_relative_to_config(tmp_path: Path) -> None:
    """Проверяет сценарий: local root relative to config."""
    (tmp_path / "data").mkdir()
    text = _toml().replace("local_root = \".\"", "local_root = \"data\"")
    config = parse_config(text, tmp_path)
    assert config.roll[0].source_path == (tmp_path / "data").resolve()


def test_duplicate_name_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: duplicate name rejected."""
    text = _toml() + _toml().replace("[[sync]]", "[[sync]]")
    with pytest.raises(ConfigError, match="не уникально"):
        parse_config(text, tmp_path)


def test_missing_local_root_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: missing local root rejected."""
    text = _toml().replace("local_root = \".\"", "local_root = \"nope\"")
    with pytest.raises(ConfigError, match="не существует"):
        parse_config(text, tmp_path)


def test_empty_remote_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: empty remote rejected."""
    with pytest.raises(ConfigError, match="не задан"):
        parse_config(_toml(target=""), tmp_path)


def test_root_remote_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: root remote rejected."""
    with pytest.raises(ConfigError, match="корень"):
        parse_config(_toml(target="/"), tmp_path)


def test_ssh_root_remote_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: ssh root remote rejected."""
    with pytest.raises(ConfigError, match="корень"):
        parse_config(_toml(target="user@host:/"), tmp_path)


def test_bad_after_push_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: bad after push rejected."""
    text = (
        "[[backup]]\n"
        "name = \"bak\"\n"
        "local_root = \".\"\n"
        "remote_root = \"/srv/bak\"\n"
        "after_push = \"burn\"\n"
    )
    with pytest.raises(ConfigError, match="after_push"):
        parse_config(text, tmp_path)


def test_after_push_archive_maps_to_internal_backup(tmp_path: Path) -> None:
    """Проверяет сценарий: after push archive maps to internal backup."""
    text = (
        "[[backup]]\n"
        "name = \"bak\"\n"
        "local_root = \".\"\n"
        "remote_root = \"/srv/bak\"\n"
        "after_push = \"archive\"\n"
    )
    config = parse_config(text, tmp_path)
    assert config.roll[0].after_push == "backup"


def test_archive_dir_maps_to_internal_backup_path(tmp_path: Path) -> None:
    """Проверяет сценарий: archive dir maps to internal backup path."""
    text = (
        "[[backup]]\n"
        "name = \"bak\"\n"
        "local_root = \".\"\n"
        "remote_root = \"/srv/bak\"\n"
        "archive_dir = \"store\"\n"
    )
    config = parse_config(text, tmp_path)
    assert config.roll[0].backup_path == (tmp_path / "store")


def test_bad_type_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: bad type rejected."""
    with pytest.raises(ConfigError, match="delete"):
        parse_config(_toml(extra="delete = \"yes\"\n"), tmp_path)


def test_no_profiles_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: no profiles rejected."""
    with pytest.raises(ConfigError, match="ни одного профиля"):
        parse_config("[defaults]\ncompress = true\n", tmp_path)


def test_load_config_missing_file(tmp_path: Path) -> None:
    """Проверяет сценарий: load config missing file."""
    with pytest.raises(ConfigError, match="нет файла"):
        load_config(tmp_path)


def test_load_config_reads_file(tmp_path: Path) -> None:
    """Проверяет сценарий: load config reads file."""
    (tmp_path / ".fs-syn.toml").write_text(_toml(), encoding="utf-8")
    config = load_config(tmp_path)
    assert config.roll[0].name == "main"


def test_invalid_toml_rejected(tmp_path: Path) -> None:
    """Проверяет сценарий: invalid toml rejected."""
    with pytest.raises(ConfigError, match="разобрать"):
        parse_config("this is = = not toml", tmp_path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("user@host:/path", (True, "user@host", "/path")),
        ("alias:/data/x", (True, "alias", "/data/x")),
        ("E:/Home/Access", (False, None, "E:/Home/Access")),
        ("/local/abs", (False, None, "/local/abs")),
        ("relative/dir", (False, None, "relative/dir")),
    ],
)
def test_split_target(value: str, expected: tuple[bool, str | None, str]) -> None:
    """Проверяет сценарий: split target."""
    assert split_target(value) == expected


def test_is_ssh_target() -> None:
    """Проверяет сценарий: is ssh target."""
    assert is_ssh_target("user@host:/p") is True
    assert is_ssh_target("E:/Home/Access") is False
    assert is_ssh_target("/local/p") is False
