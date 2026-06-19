"""Общие для всех режимов фикстуры.

Мод-специфичные фикстуры (фабрика нормализатора `nn`, запись `.fs-check` `write_rule`)
держатся в conftest.py соответствующих подпапок. При src-layout + editable пакет
доступен по импорту напрямую — хак вставки корня в sys.path не нужен.
"""
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest


@pytest.fixture()
def make_tree(tmp_path: Path) -> Callable[[Iterable[str]], Path]:
    """Фабрика дерева: создаёт каталоги/файлы из списка путей в tmp_path.

    Путь, оканчивающийся на '/', — каталог; иначе файл (вместе с родителями).
    Возвращает корень созданного дерева (tmp_path). Используется обоими режимами.
    """

    def _make(paths: Iterable[str]) -> Path:
        """Вспомогательная функция для теста."""
        for rel in paths:
            target = tmp_path / rel
            if rel.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("", encoding="utf-8")
        return tmp_path

    return _make
