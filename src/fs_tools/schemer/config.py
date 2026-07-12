"""Чтение и валидация .fs-sch.toml: декларативные группы и контент-правила.

TOML разбирается стандартным `tomllib`. Модель — типизированные `dataclass`
(`SchemeConfig`/`Group`/`GroupFile`/`ContentRule`); любое нарушение формата/валидации
поднимает `SchemeConfigError` — runner транслирует его в код возврата 1.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_NAME = ".fs-sch.toml"

_DEFAULT_EXCLUDE_PREFIX = "_"


class SchemeConfigError(Exception):
    """Файл .fs-sch.toml отсутствует или не проходит валидацию (код возврата 1)."""


@dataclass(frozen=True)
class ContentRule:
    """Контент-правило: 1-based номер строки и её точный ожидаемый текст."""

    line: int
    text: str


@dataclass(frozen=True)
class GroupFile:
    """Единственный механизм для конкретного имени файла в группе.

    `optional=False` — файл обязателен (F1/F4); `optional=True` — отсутствие не
    нарушение, но при наличии контент-проверка обязательна (F7/F9–F13).
    """

    name: str
    optional: bool
    rule: ContentRule


@dataclass(frozen=True)
class Group:
    """Групповая папка: имя (basename, матчится на любой глубине) и её правила.

    По умолчанию поддерево группы непрозрачно для движка: `group.file`/
    `default_rule` по-прежнему проверяются для прямых детей папки, но обход не
    спускается в подпапки (F15 `loose_file` на них не срабатывает) — вложенность
    внутри группы (сторонние библиотеки, произвольная организация) — норма, а не
    нарушение. `strict=True` включает прежнее строгое поведение: подпапки группы
    заново классифицируются и подпадают под F15, как обычные тематические узлы.
    """

    name: str
    default_rule: ContentRule | None
    files: tuple[GroupFile, ...]
    strict: bool = False

    def file_by_name(self, name: str) -> GroupFile | None:
        """Найти запись `[[group.file]]` по имени или вернуть None."""
        for gfile in self.files:
            if gfile.name == name:
                return gfile
        return None


@dataclass(frozen=True)
class SchemeConfig:
    """Разобранный .fs-sch.toml: префикс служебных файлов и упорядоченные группы."""

    exclude_prefix: str
    groups: tuple[Group, ...]

    def group_by_name(self, name: str) -> Group | None:
        """Найти группу по имени (регистрозависимо) или вернуть None."""
        for group in self.groups:
            if group.name == name:
                return group
        return None


def _as_str(value: Any, where: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise SchemeConfigError(f"{where}: поле «{field_name}» должно быть строкой")
    return value


def _as_bool(value: Any, where: str, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise SchemeConfigError(f"{where}: поле «{field_name}» должно быть true/false")
    return value


def _as_int(value: Any, where: str, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemeConfigError(f"{where}: поле «{field_name}» должно быть целым числом")
    return value


def _build_content_rule(bare: dict[str, Any], where: str) -> ContentRule:
    line = _as_int(bare.get("line"), where, "line")
    if line < 1:
        raise SchemeConfigError(f"{where}: поле «line» должно быть ≥ 1")
    text = _as_str(bare.get("text"), where, "text")
    if not text:
        raise SchemeConfigError(f"{where}: поле «text» не может быть пустым")
    return ContentRule(line=line, text=text)


def _build_group_file(bare: dict[str, Any], group_name: str) -> GroupFile:
    where = f"группа «{group_name}»"
    name = bare.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SchemeConfigError(f"{where}: поле «name» отсутствует или пустое")
    optional = False
    if (val := bare.get("optional")) is not None:
        optional = _as_bool(val, where, "optional")
    rule = _build_content_rule(bare, f"{where}, файл «{name}»")
    return GroupFile(name=name, optional=optional, rule=rule)


def _build_group(bare: dict[str, Any]) -> Group:
    name = bare.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SchemeConfigError("секция [[group]]: поле «name» отсутствует или пустое")
    if "/" in name:
        raise SchemeConfigError(f"группа «{name}»: «name» не может содержать «/»")

    strict = False
    if (val := bare.get("strict")) is not None:
        strict = _as_bool(val, f"группа «{name}»", "strict")

    default_rule: ContentRule | None = None
    if (val := bare.get("default_rule")) is not None:
        if not isinstance(val, dict):
            raise SchemeConfigError(f"группа «{name}»: «default_rule» должен быть таблицей")
        default_rule = _build_content_rule(val, f"группа «{name}», default_rule")

    files_bare = bare.get("file", [])
    where = f"группа «{name}»: секция [[group.file]] должна быть массивом таблиц"
    if not isinstance(files_bare, list):
        raise SchemeConfigError(where)
    files: list[GroupFile] = []
    seen: set[str] = set()
    for file_bare in files_bare:
        if not isinstance(file_bare, dict):
            raise SchemeConfigError(where)
        gfile = _build_group_file(file_bare, name)
        if gfile.name in seen:
            raise SchemeConfigError(f"группа «{name}»: имя файла «{gfile.name}» не уникально")
        seen.add(gfile.name)
        files.append(gfile)

    return Group(name=name, default_rule=default_rule, files=tuple(files), strict=strict)


def parse_scheme_config(text: str) -> SchemeConfig:
    """Разобрать содержимое .fs-sch.toml в модель групп (без чтения файла)."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SchemeConfigError(f"не удалось разобрать {CONFIG_NAME}: {exc}") from exc

    defaults = data.get("defaults", {})
    if not isinstance(defaults, dict):
        raise SchemeConfigError("секция [defaults] должна быть таблицей")
    exclude_prefix = _DEFAULT_EXCLUDE_PREFIX
    if (val := defaults.get("exclude_prefix")) is not None:
        exclude_prefix = _as_str(val, "[defaults]", "exclude_prefix")

    groups_bare = data.get("group", [])
    if not isinstance(groups_bare, list):
        raise SchemeConfigError("секция [[group]] должна быть массивом таблиц")
    groups: list[Group] = []
    seen: set[str] = set()
    for group_bare in groups_bare:
        if not isinstance(group_bare, dict):
            raise SchemeConfigError("секция [[group]] должна быть массивом таблиц")
        group = _build_group(group_bare)
        if group.name in seen:
            raise SchemeConfigError(f"имя группы «{group.name}» не уникально")
        seen.add(group.name)
        groups.append(group)

    return SchemeConfig(exclude_prefix=exclude_prefix, groups=tuple(groups))


def load_scheme_config(root: Path) -> SchemeConfig:
    """Прочитать root/.fs-sch.toml и разобрать его. Нет файла → SchemeConfigError."""
    path = root / CONFIG_NAME
    if not path.is_file():
        raise SchemeConfigError(f"в каталоге {root} нет файла {CONFIG_NAME}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SchemeConfigError(f"не удалось прочитать {path}: {exc}") from exc
    return parse_scheme_config(text)
