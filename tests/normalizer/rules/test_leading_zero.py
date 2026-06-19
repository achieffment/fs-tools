"""LeadingZeroRule: ведущий ноль для однозначного числового токена."""
import pytest

from fs_tools.normalizer import LeadingZeroRule


@pytest.mark.parametrize(
    "bare, expected",
    [
        ("1_file", "01_file"),
        ("file_5", "file_05"),
        ("a 7 b", "a 07 b"),
        ("1.5", "1.5"),        # дробь не трогаем
        ("v2", "v2"),          # буквенный префикс
        ("2x", "2x"),          # буквенный суффикс
        ("file10", "file10"),  # двузначное / слитно с буквами
        ("12", "12"),          # уже двузначное
    ],
)
def test_leading_zero(bare, expected):
    """Проверяет сценарий: leading zero."""
    assert LeadingZeroRule().apply(bare, is_dir=False) == expected


@pytest.mark.parametrize(
    "bare, expected",
    [
        ("том 5!", "tom-05"),
        ("report 5!", "report-05"),
        ("5.", "05"),
        ("file 7;", "file-07"),
        ("3,", "03"),
    ],
)
def test_leading_zero_after_trim_edge(nn, bare, expected):
    # LeadingZeroRule идёт ПОСЛЕ TrimEdgeRule: кромочный «мусор» рядом с одиночной
    # цифрой ('5!', '5.') не мешает поставить ведущий ноль за один проход. Иначе
    # на втором прогоне (мусор уже срезан) '5' -> '05' — нарушение идемпотентности.
    """Проверяет сценарий: leading zero after trim edge."""
    once = nn.normalize(bare, is_dir=False)
    assert once == expected
    assert nn.normalize(once, is_dir=False) == once
