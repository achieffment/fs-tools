"""Регрессия песочницы: examples/checker даёт зафиксированный итог из README."""
from pathlib import Path

import pytest

from fs_tools.checker.runner import run

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "checker"


def test_examples_matches_readme(capsys: pytest.CaptureFixture[str]) -> None:
    """Проверяет сценарий: examples matches readme."""
    code = run(EXAMPLES)
    out = capsys.readouterr().out
    assert code == 2
    assert "Отсутствуют пути (4):" in out
    assert "Статус: warn. Найдены отсутствующие пути." in out
    assert (
        "Сводка: проверено правил: 17; найдено каталогов-кандидатов: 22; "
        "отсутствует: 4; ошибок чтения: 0." in out
    )
    assert "Activities/3D/Resources" in out
    assert "Activities/Web/Projects/Addl/safegrid.example/Data" in out
    assert "Activities/Web/Projects/Self/personal.example/Back" in out
    assert "Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/project.md" in out
