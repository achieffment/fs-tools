"""TrimEdgeRule: обрезка не буквенно-цифровых символов по краям имени."""
import pytest

from fs_tools.normalizer.rules import TrimEdgeRule


@pytest.mark.parametrize(
    "bare, expected",
    [
        ("-file-", "file"),
        ("__name__", "__name"),  # ведущие '_' у файлов сохраняются
        ("_private", "_private"),
        ("--_file", "file"),  # '_' не в самом начале -> обрезается вместе с мусором
        ("2020-05-00", "2020-05-00"),  # цифры плейсхолдера сохраняются
        ("2020-00-00", "2020-00-00"),
        # Парная скобка на краю сохраняется (круглая и квадратная):
        ("inn-(novogo-net)", "inn-(novogo-net)"),
        ("(kopiia)-fail", "(kopiia)-fail"),
        ("inn-[novogo-net]", "inn-[novogo-net]"),
        ("[kopiia]-fail", "[kopiia]-fail"),
        # Непарная скобка по-прежнему срезается как мусор:
        ("abc)", "abc"),
        ("(abc", "abc"),
        ("abc]", "abc"),
        ("[abc", "abc"),
        # '+' и '#' — символы имени, сохраняются по обоим краям:
        ("C#", "C#"),
        ("C++", "C++"),
        ("F#", "F#"),
        ("notepad++", "notepad++"),
        ("#tag", "#tag"),
        ("+note", "+note"),
        # Прочий мусор всё ещё срезается, в т.ч. за хвостовым '+'/'#':
        ("C#!", "C#"),
        ("C++ ", "C++"),
        ("file!", "file"),
    ],
)
def test_trim_edge(bare, expected):
    """Проверяет сценарий: trim edge."""
    assert TrimEdgeRule().apply(bare, is_dir=False) == expected


def test_trim_edge_dir_keeps_leading_underscore():
    # Ведущий '_' сохраняется и у папок (как у файлов); хвостовой мусор обрезается.
    """Проверяет сценарий: trim edge dir keeps leading underscore."""
    assert TrimEdgeRule().apply("__name__", is_dir=True) == "__name"
