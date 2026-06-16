import shutil
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

# Делаем sync_fs.py и пакет syncher импортируемыми из тестов.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Пропуск интеграционных тестов, если в системе нет rsync.
requires_rsync = pytest.mark.skipif(
    shutil.which("rsync") is None,
    reason="rsync не установлен",
)


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
