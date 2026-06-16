"""Чтение и валидация .fs-sync.toml: модель профилей [[sync]] и [[backup]].

TOML разбирается стандартным `tomllib` (Python 3.11+) или `tomli` (3.10). Значения
из секции [defaults] применяются к каждому профилю, поля профиля их переопределяют.
Любое нарушение формата/валидации поднимает `ConfigError` — CLI транслирует его в
код возврата 1 с указанием профиля и поля.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:                                           # pragma: no cover
    import tomli as tomllib

CONFIG_NAME = ".fs-sync.toml"

_AFTER_PUSH = ("delete", "archive", "nothing")

_DEFAULT_DELETE_THRESHOLD = 100
_DEFAULT_DELETE_THRESHOLD_PCT = 25.0


class ConfigError(Exception):
    """Ошибка чтения или валидации .fs-sync.toml (код возврата 1)."""


@dataclass
class Profile:
    """Один профиль синхронизации (sync) или выгрузки (backup).

    `local_root` уже приведён к абсолютному пути относительно каталога с конфигом.
    `remote_root` сохранён как в конфиге (SSH-форма `user@host:/path`, alias из
    ~/.ssh/config либо локальный путь). `kind` — 'sync' или 'backup'.
    """

    name: str
    kind: str
    local_root: Path
    remote_root: str
    exclude: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    delete: bool = True
    dry_run: bool = False
    delete_threshold: int = _DEFAULT_DELETE_THRESHOLD
    delete_threshold_pct: float = _DEFAULT_DELETE_THRESHOLD_PCT
    force_delete: bool = False
    checksum: bool = False
    compress: bool = False
    partial_progress: bool = False
    bwlimit: str | None = None
    ssh_opts: list[str] = field(default_factory=list)
    after_push: str = "nothing"
    verify: bool = True
    archive_dir: Path | None = None


@dataclass
class Config:
    """Разобранный .fs-sync.toml: каталог-корень и упорядоченный список профилей."""

    root: Path
    profiles: list[Profile]

    def by_name(self, name: str) -> Profile | None:
        for profile in self.profiles:
            if profile.name == name:
                return profile
        return None


def _as_bool(value: Any, profile: str, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"профиль «{profile}»: поле «{field_name}» должно быть true/false")
    return value


def _as_str(value: Any, profile: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"профиль «{profile}»: поле «{field_name}» должно быть строкой")
    return value


def _as_str_list(value: Any, profile: str, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"профиль «{profile}»: поле «{field_name}» должно быть списком строк")
    return list(value)


def _as_int(value: Any, profile: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"профиль «{profile}»: поле «{field_name}» должно быть целым числом")
    return value


def _as_float(value: Any, profile: str, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"профиль «{profile}»: поле «{field_name}» должно быть числом")
    return float(value)


def _validate_remote_root(remote_root: str, profile: str) -> None:
    """remote_root: непустой и безопасный (не корень `/`, непустой путь после `:`)."""
    if not remote_root.strip():
        raise ConfigError(f"профиль «{profile}»: «remote_root» не задан")
    is_ssh, _, path = split_remote(remote_root)
    if not path:
        raise ConfigError(f"профиль «{profile}»: «remote_root» — пустой путь")
    if path == "/":
        raise ConfigError(
            f"профиль «{profile}»: «remote_root» указывает на корень `/` — "
            "запрещено (риск массового удаления)"
        )


def split_remote(remote_root: str) -> tuple[bool, str | None, str]:
    """Разобрать remote_root на (is_ssh, host, path).

    SSH-форма — `host:path` (двоеточие до первого `/`): host непустой. Иначе значение
    считается локальным путём (host=None). Чисто rsync-конвенция переноса каталогов.
    """
    sep = remote_root.find(":")
    slash = remote_root.find("/")
    if sep > 0 and (slash == -1 or sep < slash):
        host = remote_root[:sep]
        path = remote_root[sep + 1:]
        return True, host, path
    return False, None, remote_root


def is_ssh_remote(remote_root: str) -> bool:
    """True, если remote_root указывает на SSH-цель (требует наличия `ssh`)."""
    return split_remote(remote_root)[0]


def _build_profile(
    kind: str,
    raw: dict[str, Any],
    defaults: dict[str, Any],
    root: Path,
) -> Profile:
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ConfigError(f"профиль [[{kind}]]: обязательное поле «name» отсутствует или пустое")

    def pick(key: str) -> Any:
        return raw[key] if key in raw else defaults.get(key)

    local_raw = pick("local_root")
    if not isinstance(local_raw, str) or not local_raw.strip():
        raise ConfigError(f"профиль «{name}»: обязательное поле «local_root» отсутствует")
    local_root = Path(local_raw).expanduser()
    if not local_root.is_absolute():
        local_root = root / local_root
    local_root = local_root.resolve()
    if not local_root.is_dir():
        raise ConfigError(f"профиль «{name}»: «local_root» не существует: {local_root}")

    remote_raw = pick("remote_root")
    if not isinstance(remote_raw, str):
        raise ConfigError(f"профиль «{name}»: обязательное поле «remote_root» отсутствует")
    _validate_remote_root(remote_raw, name)
    # Локальный remote_root отсчитывается от каталога конфига (как local_root), а не
    # от cwd процесса; SSH-цель остаётся как есть. Приёмник может не существовать —
    # resolve(strict) не применяем, rsync создаст его при передаче.
    if not is_ssh_remote(remote_raw):
        remote_path = Path(remote_raw).expanduser()
        if not remote_path.is_absolute():
            remote_path = root / remote_path
        remote_value = remote_path.as_posix()
    else:
        remote_value = remote_raw

    profile = Profile(name=name, kind=kind, local_root=local_root, remote_root=remote_value)
    profile.delete = True if kind == "sync" else False

    if (val := pick("exclude")) is not None:
        profile.exclude = _as_str_list(val, name, "exclude")
    if (val := pick("include")) is not None:
        profile.include = _as_str_list(val, name, "include")
    if (val := pick("delete")) is not None:
        profile.delete = _as_bool(val, name, "delete")
    if (val := pick("dry_run")) is not None:
        profile.dry_run = _as_bool(val, name, "dry_run")
    if (val := pick("delete_threshold")) is not None:
        profile.delete_threshold = _as_int(val, name, "delete_threshold")
    if (val := pick("delete_threshold_pct")) is not None:
        profile.delete_threshold_pct = _as_float(val, name, "delete_threshold_pct")
    if (val := pick("force_delete")) is not None:
        profile.force_delete = _as_bool(val, name, "force_delete")
    if (val := pick("checksum")) is not None:
        profile.checksum = _as_bool(val, name, "checksum")
    if (val := pick("compress")) is not None:
        profile.compress = _as_bool(val, name, "compress")
    if (val := pick("partial_progress")) is not None:
        profile.partial_progress = _as_bool(val, name, "partial_progress")
    if (val := pick("bwlimit")) is not None:
        profile.bwlimit = _as_str(str(val) if isinstance(val, int) else val, name, "bwlimit")
    if (val := pick("ssh_opts")) is not None:
        profile.ssh_opts = _as_str_list(val, name, "ssh_opts")

    if kind == "backup":
        if (val := pick("after_push")) is not None:
            after = _as_str(val, name, "after_push")
            if after not in _AFTER_PUSH:
                raise ConfigError(
                    f"профиль «{name}»: «after_push» = «{after}», допустимо: "
                    f"{', '.join(_AFTER_PUSH)}"
                )
            profile.after_push = after
        if (val := pick("verify")) is not None:
            profile.verify = _as_bool(val, name, "verify")
        if (val := pick("archive_dir")) is not None:
            archive_raw = _as_str(val, name, "archive_dir")
            archive_dir = Path(archive_raw).expanduser()
            if not archive_dir.is_absolute():
                archive_dir = root / archive_dir
            profile.archive_dir = archive_dir
    return profile


def parse_config(text: str, root: Path) -> Config:
    """Разобрать содержимое .fs-sync.toml в модель профилей (без чтения файла)."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"не удалось разобрать {CONFIG_NAME}: {exc}") from exc

    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ConfigError("секция [defaults] должна быть таблицей")

    profiles: list[Profile] = []
    for kind in ("sync", "backup"):
        entries = data.get(kind, [])
        if not isinstance(entries, list):
            raise ConfigError(f"секция [[{kind}]] должна быть массивом таблиц")
        for raw in entries:
            if not isinstance(raw, dict):
                raise ConfigError(f"секция [[{kind}]] должна быть массивом таблиц")
            profiles.append(_build_profile(kind, raw, defaults, root))

    if not profiles:
        raise ConfigError(f"{CONFIG_NAME}: не найдено ни одного профиля [[sync]]/[[backup]]")

    seen: set[str] = set()
    for profile in profiles:
        if profile.name in seen:
            raise ConfigError(f"имя профиля «{profile.name}» не уникально")
        seen.add(profile.name)

    return Config(root=root, profiles=profiles)


def load_config(root: Path) -> Config:
    """Прочитать root/.fs-sync.toml и разобрать его. Нет файла → ConfigError."""
    path = root / CONFIG_NAME
    if not path.is_file():
        raise ConfigError(f"в каталоге {root} нет файла {CONFIG_NAME}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"не удалось прочитать {path}: {exc}") from exc
    return parse_config(text, root)
