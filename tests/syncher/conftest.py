"""Мод-специфичные фикстуры режима синхронизации.

`make_tree` здесь переопределяет общую фикстуру: режиму нужны деревья источника и
приёмника под разными базами (а не одно дерево в `tmp_path`). `write_config` — фабрика
`.fs-sync.toml`. Маркер `requires_rsync` (пропуск интеграционных тестов без бинаря
rsync) определяется локально в нуждающихся тест-файлах.
"""
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest


@pytest.fixture()
def make_tree() -> Callable[[Path, Iterable[str]], Path]:
    """Фабрика дерева: создаёт каталоги/файлы из списка путей внутри base.

    Путь, оканчивающийся на '/', — каталог; иначе файл (с родителями). Файлам
    записывается их относительный путь как содержимое — детерминированно для тестов.
    """

    def _make(base: Path, paths: Iterable[str]) -> Path:
        for rel in paths:
            target = base / rel
            if rel.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(rel, encoding="utf-8")
        return base

    return _make


@pytest.fixture()
def write_config() -> Callable[[Path, str], Path]:
    """Записать текст в base/.fs-sync.toml и вернуть base."""

    def _write(base: Path, text: str) -> Path:
        (base / ".fs-sync.toml").write_text(text, encoding="utf-8")
        return base

    return _write
