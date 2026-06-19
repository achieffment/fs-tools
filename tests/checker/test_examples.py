"""Регрессия песочницы: examples/checker даёт зафиксированный итог из README."""
from pathlib import Path

import pytest

from fs_tools.checker.runner import run

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "checker"


def test_examples_matches_readme(capsys: pytest.CaptureFixture[str]) -> None:
    code = run(EXAMPLES)
    out = capsys.readouterr().out
    assert code == 2
    assert "Отсутствуют пути (7):" in out
    assert "Проверено правил: 17. Найдено каталогов-кандидатов: 26. Отсутствует: 7." in out
    assert "Activities/3D/Resources" in out
    assert "Activities/Web/Projects/Addl/_Archive/aero.example/Data" in out
    assert "Activities/Web/Projects/Self/personal.example/Back" in out
    assert "Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/project.md" in out
