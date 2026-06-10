import sys
from pathlib import Path

import pytest

# Делаем normalize_fs.py импортируемым из тестов.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def nn():
    # Импорт отложен: путь к проекту добавляется в sys.path выше.
    from normalizer import build_normalizer

    return build_normalizer()
