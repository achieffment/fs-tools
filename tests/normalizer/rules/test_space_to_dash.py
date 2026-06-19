"""SpaceToDashRule: пробелы -> дефис со схлопыванием цепочек вокруг пробела."""
import pytest

from fs_tools.normalizer import SpaceToDashRule


@pytest.mark.parametrize(
    "bare, expected",
    [
        # Прогон с пробелом -> одно тире:
        ("a b", "a-b"),
        ("a - b", "a-b"),
        ("a -- b", "a-b"),
        ("a   b", "a-b"),
        # Дефисы без пробелов сохраняются (даты не множатся, идемпотентно):
        ("a---b", "a---b"),
        ("file--improved", "file--improved"),
        ("2020-05-20", "2020-05-20"),
    ],
)
def test_space_to_dash(bare, expected):
    assert SpaceToDashRule().apply(bare, is_dir=False) == expected
