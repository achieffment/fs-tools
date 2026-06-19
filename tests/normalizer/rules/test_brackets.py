"""BracketsRule: скобки с числом/датой убираются, с текстом сохраняются."""
import pytest

from fs_tools.normalizer import BracketsRule


@pytest.mark.parametrize(
    "bare, expected",
    [
        # Число/дата (без букв) -> скобки убираются (круглые и квадратные):
        ("file (1)", "file 1"),
        ("file (12)", "file 12"),
        ("(2021.03.10)", "2021.03.10"),
        ("file [1]", "file 1"),
        ("[2021.03.10]", "2021.03.10"),
        # Текст (буквы) -> скобки сохраняются:
        ("inn (kopiia)", "inn (kopiia)"),
        ("a (b1c)", "a (b1c)"),
        ("inn [chernovik]", "inn [chernovik]"),
        # Пустые скобки убираются, без скобок — без изменений:
        ("x ()", "x "),
        ("x []", "x "),
        ("plain", "plain"),
        # Непарные/несовпадающие скобки вырезаются (валидность контента не важна):
        ("file (1", "file 1"),
        ("file 1)", "file 1"),
        ("file (1]", "file 1"),
        ("file [1)", "file 1"),
        ("inn (kopiia", "inn kopiia"),
        ("inn kopiia)", "inn kopiia"),
        ("a (1) b (2", "a 1 b 2"),
        ("((1))", "1"),  # вложенные пары схлопываются
    ],
)
def test_brackets_rule(bare, expected):
    assert BracketsRule().apply(bare, is_dir=False) == expected


def test_brackets_rule_exported():
    # Публичное API не должно разойтись: новое правило экспортируется из пакета.
    import fs_tools.normalizer as normalizer

    assert "BracketsRule" in normalizer.__all__
    assert normalizer.BracketsRule is BracketsRule
