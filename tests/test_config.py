"""Тесты config: разбор TOML, дефолты, валидация, разбор remote_root."""
from pathlib import Path

import pytest

from syncher import (
    Config,
    ConfigError,
    is_ssh_remote,
    load_config,
    parse_config,
    split_remote,
)


def _toml(remote: str = "/srv/dst", extra: str = "") -> str:
    return (
        '[[sync]]\n'
        'name = "main"\n'
        'local_root = "."\n'
        f'remote_root = "{remote}"\n'
        f"{extra}"
    )


def test_parse_minimal_sync(tmp_path: Path) -> None:
    config = parse_config(_toml(), tmp_path)
    assert isinstance(config, Config)
    assert len(config.profiles) == 1
    profile = config.profiles[0]
    assert profile.name == "main"
    assert profile.kind == "sync"
    assert profile.local_root == tmp_path.resolve()
    assert profile.delete is True            # дефолт для sync
    assert profile.dry_run is False
    assert profile.delete_threshold == 100
    assert profile.delete_threshold_pct == 25.0
    assert profile.verify is True


def test_backup_delete_default_false(tmp_path: Path) -> None:
    text = (
        '[[backup]]\n'
        'name = "bak"\n'
        'local_root = "."\n'
        'remote_root = "/srv/bak"\n'
    )
    config = parse_config(text, tmp_path)
    profile = config.profiles[0]
    assert profile.kind == "backup"
    assert profile.delete is False           # дефолт для backup
    assert profile.after_push == "nothing"


def test_defaults_section_applied_and_overridden(tmp_path: Path) -> None:
    text = (
        '[defaults]\n'
        'compress = true\n'
        'delete_threshold = 50\n'
        '[[sync]]\n'
        'name = "a"\n'
        'local_root = "."\n'
        'remote_root = "/srv/a"\n'
        '[[sync]]\n'
        'name = "b"\n'
        'local_root = "."\n'
        'remote_root = "/srv/b"\n'
        'delete_threshold = 5\n'
    )
    config = parse_config(text, tmp_path)
    a, b = config.profiles
    assert a.compress is True and a.delete_threshold == 50
    assert b.compress is True and b.delete_threshold == 5   # профиль перекрыл defaults


def test_local_root_relative_to_config(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    text = _toml().replace('local_root = "."', 'local_root = "data"')
    config = parse_config(text, tmp_path)
    assert config.profiles[0].local_root == (tmp_path / "data").resolve()


def test_duplicate_name_rejected(tmp_path: Path) -> None:
    text = _toml() + _toml().replace("[[sync]]", "[[sync]]")
    with pytest.raises(ConfigError, match="не уникально"):
        parse_config(text, tmp_path)


def test_missing_local_root_rejected(tmp_path: Path) -> None:
    text = _toml().replace('local_root = "."', 'local_root = "nope"')
    with pytest.raises(ConfigError, match="не существует"):
        parse_config(text, tmp_path)


def test_empty_remote_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="не задан"):
        parse_config(_toml(remote=""), tmp_path)


def test_root_remote_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="корень"):
        parse_config(_toml(remote="/"), tmp_path)


def test_ssh_root_remote_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="корень"):
        parse_config(_toml(remote="user@host:/"), tmp_path)


def test_bad_after_push_rejected(tmp_path: Path) -> None:
    text = (
        '[[backup]]\n'
        'name = "bak"\n'
        'local_root = "."\n'
        'remote_root = "/srv/bak"\n'
        'after_push = "burn"\n'
    )
    with pytest.raises(ConfigError, match="after_push"):
        parse_config(text, tmp_path)


def test_bad_type_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="delete"):
        parse_config(_toml(extra='delete = "yes"\n'), tmp_path)


def test_no_profiles_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="ни одного профиля"):
        parse_config('[defaults]\ncompress = true\n', tmp_path)


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="нет файла"):
        load_config(tmp_path)


def test_load_config_reads_file(tmp_path: Path) -> None:
    (tmp_path / ".fs-sync.toml").write_text(_toml(), encoding="utf-8")
    config = load_config(tmp_path)
    assert config.profiles[0].name == "main"


def test_invalid_toml_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="разобрать"):
        parse_config("this is = = not toml", tmp_path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("user@host:/path", (True, "user@host", "/path")),
        ("alias:/data/x", (True, "alias", "/data/x")),
        ("/local/abs", (False, None, "/local/abs")),
        ("relative/dir", (False, None, "relative/dir")),
    ],
)
def test_split_remote(value: str, expected: tuple[bool, str | None, str]) -> None:
    assert split_remote(value) == expected


def test_is_ssh_remote() -> None:
    assert is_ssh_remote("user@host:/p") is True
    assert is_ssh_remote("/local/p") is False
