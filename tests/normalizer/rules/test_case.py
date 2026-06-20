"""CaseRule: папки — с заглавной, файлы — в нижнем регистре (README сохраняется)."""
import pytest

from fs_tools.normalizer.rules import CaseRule


def test_case_rule():
    """Проверяет сценарий: case rule."""
    assert CaseRule().apply("report", is_dir=True) == "Report"
    assert CaseRule().apply("Report", is_dir=False) == "report"
    # README в верхнем регистре сохраняется как есть:
    assert CaseRule().apply("README", is_dir=False) == "README"
    # Сохраняется только точное совпадение: иной регистр приводится к нижнему.
    assert CaseRule().apply("Readme", is_dir=False) == "readme"
    # У папок ведущий '_' сохраняется, капитализируется первая буква после него:
    assert CaseRule().apply("_private", is_dir=True) == "_Private"
    assert CaseRule().apply("__cache", is_dir=True) == "__Cache"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("README", "README"),
        ("README.md", "README.md"),
        ("README.TXT", "README.TXT"),
    ],
)
def test_readme_preserved(nn, name, expected):
    """Проверяет сценарий: readme preserved."""
    assert nn.normalize(name, is_dir=False) == expected
