"""Регрессия песочницы: examples/schemer даёт зафиксированный итог из README."""
from pathlib import Path

import pytest

from fs_tools.schemer import FS_LOG
from fs_tools.schemer.runner import run

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "schemer" / "Warehouse"


def test_examples_matches_readme(capsys: pytest.CaptureFixture[str]) -> None:
    """Проверяет сценарий: examples matches readme (терминал — сводка, детали — .fs-log)."""
    code = run(EXAMPLES)
    out = capsys.readouterr().out
    assert code == 2
    assert "Нарушения" not in out
    assert "Статус: error. Найдены нарушения структуры/контента." in out
    assert "Сводка: проверено групп: 4; проверено файлов: 6; нарушений: 4." in out

    log = (EXAMPLES / FS_LOG).read_text(encoding="utf-8")
    assert "заголовок не совпадает: Code/_Blueprints/_devs.md" in log
    assert "отсутствует обязательный файл: Code/_Commands/_main.md" in log
    assert "пустая группа: Code/_Resources" in log
    assert "файл вне групповой папки: Code/loose.md" in log
