"""TransliterationRule: не-ASCII -> ASCII + барьеры безопасности имени."""
import pytest

from fs_tools.normalizer import TransliterationRule


# --------------------------------------------------------------------------- #
# Безопасность: транслитерация не должна вносить разделители пути / управляющие
# символы. Иначе os.rename истолковал бы их как путь и переместил/потерял объект.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bare",
    [
        "½", "¼", "¾", "10½", "½ доля", "naïve½", "файл ½",
        "∖обратная", "↘стрелка", "＼fullwidth",  # дают '\' через unidecode
        "пример\u2028строка", "две\u2029строки",  # дают '\n' через unidecode
    ],
)
def test_no_path_separators_introduced(nn, bare):
    for is_dir in (False, True):
        out = nn.normalize(bare if is_dir else bare + ".txt", is_dir=is_dir)
        assert "/" not in out
        assert "\\" not in out
        assert not any(ord(c) < 0x20 for c in out)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("½.txt", "01-02.txt"),
        ("10½.dat", "10-01-02.dat"),
        ("½ доля.txt", "01-02-dolia.txt"),
    ],
)
def test_fraction_pipeline(nn, name, expected):
    assert nn.normalize(name, is_dir=False) == expected


def test_transliteration_rule_strips_separators():
    # Прямой контракт правила: '/' и '\' из unidecode заменяются на '-'.
    assert "/" not in TransliterationRule().apply("½", is_dir=False)
    assert "\\" not in TransliterationRule().apply("∖", is_dir=False)


# --------------------------------------------------------------------------- #
# Мягкий/твёрдый знак: unidecode превращает 'ь'/'ъ' в апостроф — мы его убираем.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, expected",
    [
        ("Письмо", "pismo"),
        ("автомобиль", "avtomobil"),
        ("секретарь", "sekretar"),
        ("подъезд", "podezd"),
        ("Объявление", "obiavlenie"),
    ],
)
def test_soft_hard_sign_removed(nn, name, expected):
    assert nn.normalize(name, is_dir=False) == expected
    # Апостроф не должен появляться в имени:
    assert "'" not in nn.normalize(name, is_dir=False)


def test_ascii_apostrophe_preserved(nn):
    # ASCII-апостроф во ВХОДНОМ имени не трогаем — убираем только 'ь'/'ъ'.
    assert nn.normalize("O'Brien.txt", is_dir=False) == "o'brien.txt"


# --------------------------------------------------------------------------- #
# Запрещённые на Windows символы (< > : " | ? *). Транслитерация порождает их из
# типографики ('«'->'<<', '»'->'>>', '“'/'”'->'"'); их нужно вырезать, иначе
# одиночный '<' в середине имени ломает os.rename на Windows (WinError 123).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "bare",
    [
        "«ёлочки»", "ООО «Печоралифтсервис»", "“кавычки”", "„нижние“",
        "файл «с» кавычками", "‹одинарные›",
    ],
)
def test_no_windows_forbidden_introduced(nn, bare):
    for is_dir in (False, True):
        out = nn.normalize(bare if is_dir else bare + ".txt", is_dir=is_dir)
        assert not any(ch in out for ch in '<>:"|?*')


@pytest.mark.parametrize(
    "name, expected",
    [
        ("«Печоралифтсервис».txt", "pechoraliftservis.txt"),
        ("ООО «Рога и Копыта».doc", "ooo-roga-i-kopyta.doc"),
    ],
)
def test_guillemets_pipeline(nn, name, expected):
    assert nn.normalize(name, is_dir=False) == expected


def test_transliteration_rule_removes_windows_forbidden():
    # Прямой контракт правила: '<<'/'>>' из unidecode('«»') вырезаются.
    out = TransliterationRule().apply("«тест»", is_dir=False)
    assert "<" not in out and ">" not in out


@pytest.mark.parametrize("bare", ["½", "10½", "½ доля", "naïve½"])
def test_fraction_idempotent(nn, bare):
    once = nn.normalize(bare, is_dir=False)
    assert nn.normalize(once, is_dir=False) == once
