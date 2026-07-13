"""Регрессия песочницы: examples/schemer даёт зафиксированный итог из README."""
from pathlib import Path

import pytest

from fs_tools.schemer import FS_LOG
from fs_tools.schemer.runner import run

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "schemer"
WAREHOUSE = EXAMPLES / "Warehouse"


def test_examples_matches_readme(capsys: pytest.CaptureFixture[str]) -> None:
    """Проверяет сценарий: examples matches readme (терминал — сводка, детали — .fs-log.log).

    Конфиг лежит в `examples/schemer` (`EXAMPLES`), а `apply_root = "Warehouse"`
    перенаправляет обход на `WAREHOUSE` — демонстрация разнесения конфига и
    проверяемого дерева; `.fs-log.log` при этом пишется рядом с конфигом (`EXAMPLES`).
    """
    code = run(EXAMPLES)
    out = capsys.readouterr().out
    assert code == 2
    assert "Нарушения" not in out
    assert f"Каталог: {WAREHOUSE}" in out
    assert "Статус: error. Найдены нарушения структуры/контента." in out
    assert "Сводка: проверено групп: 5; проверено файлов: 6; нарушений: 5." in out

    assert not (WAREHOUSE / FS_LOG).exists()
    log = (EXAMPLES / FS_LOG).read_text(encoding="utf-8")
    assert "заголовок не совпадает: Code/_Blueprints/_devs.md" in log
    assert "отсутствует обязательный файл: Code/_Commands/_main.md" in log
    assert "пустая группа: Code/_Archive" in log
    assert "файл вне групповой папки: Code/loose.md" in log
    # strict=true у _Commands: вложенный Old/legacy.md заново классифицируется -> loose_file.
    assert "файл вне групповой папки: Code/_Commands/Old/legacy.md" in log
    # strict не задан (false) у _Resources: вложенный Library/Sub/asset.bin не даёт loose_file.
    assert "Library" not in log
    # _Blueprints.default_rule.extensions=[".md"]: asset.bin не читается -> нет read_error.
    assert "asset.bin" not in log
