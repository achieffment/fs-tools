"""Чтение и валидация .fs-sync.toml: модель профилей [[sync]] и [[backup]].

TOML разбирается стандартным `tomllib` (есть в stdlib на Python 3.11+). Значения из
секции [defaults] применяются к каждому профилю, поля профиля их переопределяют. Любое
нарушение формата/валидации поднимает `ConfigError` — runner транслирует его в код
возврата 1 с указанием профиля и поля.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_NAME = ".fs-sync.toml"

_AFTER_PUSH = ("delete", "archive", "nothing")

_DEFAULT_DELETE_THRESHOLD = 100
_DEFAULT_DELETE_THRESHOLD_PCT = 25.0


class ConfigError(Exception):
    """Ошибка чтения или валидации .fs-sync.toml (код возврата 1)."""


@dataclass
class Profile:
    """Один профиль синхронизации (sync) или выгрузки (backup).

    Внешний TOML-контракт использует legacy-ключи `local_root`, `remote_root`,
    `archive_dir`, `after_push = "archive"`. Внутри модели эти значения хранятся в
    унифицированных полях `source_path`/`target_path`/`backup_path`; `kind` — 'sync'
    или 'backup'.
    """

    name: str
    kind: str
    source_path: Path
    target_path: str
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
    backup_path: Path | None = None


@dataclass
class Config:
    """Разобранный .fs-sync.toml: каталог-корень и упорядоченный список профилей."""

    root: Path
    roll: list[Profile]

    def by_name(self, name: str) -> Profile | None:
        for profile in self.roll:
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
    is_ssh, _, path = split_target(remote_root)
    if not path:
        raise ConfigError(f"профиль «{profile}»: «remote_root» — пустой путь")
    if path == "/":
        raise ConfigError(
            f"профиль «{profile}»: «remote_root» указывает на корень `/` — "
            "запрещено (риск массового удаления)"
        )


def split_target(target_root: str) -> tuple[bool, str | None, str]:
    """Разобрать target_root на (is_ssh, host, path).

    SSH-форма — `host:path` (двоеточие до первого `/`): host непустой. Иначе значение
    считается локальным путём (host=None). Чисто rsync-конвенция переноса каталогов.
    """
    sep = target_root.find(":")
    slh = target_root.find("/")
    if sep > 0 and (slh == -1 or sep < slh):
        host = target_root[:sep]
        path = target_root[sep + 1:]
        return True, host, path
    return False, None, target_root


def is_ssh_target(target_root: str) -> bool:
    """True, если target_root указывает на SSH-цель (требует наличия `ssh`)."""
    return split_target(target_root)[0]


def _build_profile(
    kind: str,
    bare: dict[str, Any],
    defaults: dict[str, Any],
    root: Path,
) -> Profile:
    name = bare.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ConfigError(f"профиль [[{kind}]]: обязательное поле «name» отсутствует или пустое")

    def pick(key: str) -> Any:
        return bare[key] if key in bare else defaults.get(key)

    source_bare = pick("local_root")
    if not isinstance(source_bare, str) or not source_bare.strip():
        raise ConfigError(f"профиль «{name}»: обязательное поле «local_root» отсутствует")
    source_path = Path(source_bare).expanduser()
    if not source_path.is_absolute():
        source_path = root / source_path
    source_path = source_path.resolve()
    if not source_path.is_dir():
        raise ConfigError(f"профиль «{name}»: «local_root» не существует: {source_path}")

    target_bare = pick("remote_root")
    if not isinstance(target_bare, str):
        raise ConfigError(f"профиль «{name}»: обязательное поле «remote_root» отсутствует")
    _validate_remote_root(target_bare, name)
    # Локальный remote_root отсчитывается от каталога конфига (как local_root), а не
    # от cwd процесса; SSH-цель остаётся как есть. Приёмник может не существовать —
    # resolve(strict) не применяем, rsync создаст его при передаче.
    if not is_ssh_target(target_bare):
        target_resolved = Path(target_bare).expanduser()
        if not target_resolved.is_absolute():
            target_resolved = root / target_resolved
        target_path = target_resolved.as_posix()
    else:
        target_path = target_bare

    profile = Profile(name=name, kind=kind, source_path=source_path, target_path=target_path)
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
            profile.after_push = "backup" if after == "archive" else after
        if (val := pick("verify")) is not None:
            profile.verify = _as_bool(val, name, "verify")
        if (val := pick("archive_dir")) is not None:
            backup_bare = _as_str(val, name, "archive_dir")
            backup_path = Path(backup_bare).expanduser()
            if not backup_path.is_absolute():
                backup_path = root / backup_path
            profile.backup_path = backup_path
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

    roll: list[Profile] = []
    for kind in ("sync", "backup"):
        entries = data.get(kind, [])
        if not isinstance(entries, list):
            raise ConfigError(f"секция [[{kind}]] должна быть массивом таблиц")
        for bare in entries:
            if not isinstance(bare, dict):
                raise ConfigError(f"секция [[{kind}]] должна быть массивом таблиц")
            roll.append(_build_profile(kind, bare, defaults, root))

    if not roll:
        raise ConfigError(f"{CONFIG_NAME}: не найдено ни одного профиля [[sync]]/[[backup]]")

    seen: set[str] = set()
    for profile in roll:
        if profile.name in seen:
            raise ConfigError(f"имя профиля «{profile.name}» не уникально")
        seen.add(profile.name)

    return Config(root=root, roll=roll)


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
