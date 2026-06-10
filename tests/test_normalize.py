from pathlib import PurePosixPath

import pathspec
import pytest

from normalizer import (
    BracketsRule,
    CaseRule,
    DateRule,
    FilesystemNormalizer,
    FsIgnore,
    LeadingZeroRule,
    SpaceToDashRule,
    TransliterationRule,
    TrimEdgeRule,
    build_normalizer,
    load_fs_ignore,
)
from normalizer.ignore import _FACTORY


@pytest.fixture()
def nn():
    return build_normalizer()


# --------------------------------------------------------------------------- #
# Конвейер целиком (файлы)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, expected",
    [
        ("Отчёт.TXT", "otchiot.TXT"),
        ("1_file.TXT", "01_file.TXT"),
        ("v2 readme.MD", "v2-readme.MD"),
        ("20.05.2020_dump", "2020-05-20_dump"),
        ("dump_20.05.2020", "dump_2020-05-20"),
        ("05.2020_report", "2020-05-00_report"),
        ("2020.05", "2020-05-00"),
        ("2020", "2020-00-00"),
        ("-file_01-.png", "file_01.png"),
        ("файл 1.JPG", "fail-01.JPG"),
        ("2020-05-05-file.txt", "2020-05-05_file.txt"),
        ("dump-2020-05-05.txt", "dump_2020-05-05.txt"),
        # Дубли файлового менеджера ('(1)' и '[1]') -> скобки убираются, ведущий ноль:
        ("Файл (1).docx", "fail-01.docx"),
        ("Файл (12).docx", "fail-12.docx"),
        ("Файл [1].docx", "fail-01.docx"),
        # Текст в скобках -> скобки сохраняются (концевая скобка не срезается):
        ("инн (Нового договора нет).txt", "inn-(novogo-dogovora-net).txt"),
        ("инн [Нового договора нет].txt", "inn-[novogo-dogovora-net].txt"),
        # Пробел-дефис-пробел схлопывается в одно тире:
        ("Резюме - подготовка.txt", "reziume-podgotovka.txt"),
        # Намеренное двойное тире (без пробелов) сохраняется:
        ("file--improved.txt", "file--improved.txt"),
        # Незакрытые/несовпадающие скобки вырезаются (как невалидный мусор):
        ("Файл (1.docx", "fail-01.docx"),
        ("Файл (1].docx", "fail-01.docx"),
        ("инн (Нового договора нет.txt", "inn-novogo-dogovora-net.txt"),
        # Мягкий знак удаляется (не превращается в апостроф):
        ("Письмо.txt", "pismo.txt"),
        # Кавычки-«ёлочки» (unidecode -> '<<'/'>>') запрещены на Windows: вырезаются:
        (
            "Заявление директору ООО «Печоралифтсервис».docx",
            "zaiavlenie-direktoru-ooo-pechoraliftservis.docx",
        ),
    ],
)
def test_file_pipeline(nn, name, expected):
    assert nn.normalize(name, is_dir=False) == expected


def test_brackets_rule_exported():
    # Публичное API не должно разойтись: новое правило экспортируется из пакета.
    import normalizer

    assert "BracketsRule" in normalizer.__all__
    assert normalizer.BracketsRule is BracketsRule


# --------------------------------------------------------------------------- #
# Конвейер целиком (папки)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, expected",
    [
        ("отчёт за март", "Otchiot-za-mart"),
        ("Отчёт 2020", "Otchiot_2020-00-00"),
        ("my docs", "My-docs"),
        # Ведущие пробелы/дефисы не должны мешать капитализации с первого прогона:
        ("  отчёт", "Otchiot"),
        ("   фывфыв   фывфыв ---", "Fyvfyv-fyvfyv"),
        ("--- папка", "Papka"),
        ("-файл с пробелом", "Fail-s-probelom"),
        # Ведущий '_' сохраняется и у папок; первая буква после него — заглавная:
        ("_private", "_Private"),
        ("__cache__", "__Cache"),
    ],
)
def test_dir_pipeline(nn, name, expected):
    assert nn.normalize(name, is_dir=True) == expected


# --------------------------------------------------------------------------- #
# Идемпотентность
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "name, is_dir",
    [
        ("20.05.2020_dump", False),
        ("05.2020", False),
        ("2020", False),
        ("Отчёт 2020", True),
        ("v2 readme.MD", False),
        ("2020-05-05-file.txt", False),
        ("dump-2020-05-05.txt", False),
        # Скобки (круглые и квадратные) и схлопывание дефисов:
        ("Файл (1)", False),
        ("инн (Нового договора нет)", False),
        ("Файл [1]", False),
        ("инн [Нового договора нет]", False),
        ("Резюме - подготовка", False),
        ("file--improved", False),
        # Незакрытые скобки вырезаются за один прогон, дальше стабильно:
        ("Файл (1", False),
        ("инн (Нового договора нет", False),
        # Папки с ведущим мусором — капитализация за один прогон:
        ("  отчёт", True),
        ("   фывфыв   фывфыв ---", True),
        ("--- папка", True),
        # Папки с ведущим '_' — стабильны после первого прогона:
        ("_private", True),
        ("__cache__", True),
    ],
)
def test_idempotent(nn, name, is_dir):
    once = nn.normalize(name, is_dir)
    twice = nn.normalize(once, is_dir)
    assert once == twice


# --------------------------------------------------------------------------- #
# DateRule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("20.05.2020", "2020-05-20"),
        ("2020.05.20", "2020-05-20"),
        ("2020/05/20", "2020-05-20"),
        ("1.2.2020", "2020-02-01"),
        # Соседние разделители вокруг даты -> '_':
        ("2020-05-05-file", "2020-05-05_file"),
        ("dump-2020-05-05", "dump_2020-05-05"),
        ("2020-05-05.file", "2020-05-05_file"),
        ("dump 20.05.2020", "dump_2020-05-20"),
        ("dump_2020-05-05", "dump_2020-05-05"),
        ("2020-05-00-file", "2020-05-00_file"),
        ("year-2020-end", "year_2020-00-00_end"),
        ("05.2020", "2020-05-00"),
        ("2020.05", "2020-05-00"),
        ("1.2020", "2020-01-00"),
        ("2020", "2020-00-00"),
        # Невалидные/нерелевантные — без изменений:
        ("31.02.2020", "31.02.2020"),
        ("13.2020", "13.2020"),
        ("1080", "1080"),
        ("12345", "12345"),
        # Цифры, склеенные с буквами, — НЕ дата (отдельный токен обязателен):
        ("model2020", "model2020"),
        ("version2021", "version2021"),
        ("abc1999x", "abc1999x"),
        ("build2024release", "build2024release"),
        ("2020s", "2020s"),
        # Разделители-токены (_) сохраняют распознавание года:
        ("file_2020", "file_2020-00-00"),
        # Уже нормализованные — без изменений:
        ("2020-05-20", "2020-05-20"),
        ("2020-05-00", "2020-05-00"),
        ("2020-00-00", "2020-00-00"),
    ],
)
def test_date_rule(raw, expected):
    assert DateRule().apply(raw, is_dir=False) == expected


# --------------------------------------------------------------------------- #
# LeadingZeroRule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw, expected",
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
def test_leading_zero(raw, expected):
    assert LeadingZeroRule().apply(raw, is_dir=False) == expected


# --------------------------------------------------------------------------- #
# BracketsRule
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw, expected",
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
def test_brackets_rule(raw, expected):
    assert BracketsRule().apply(raw, is_dir=False) == expected


# --------------------------------------------------------------------------- #
# SpaceToDashRule — схлопывание пробелов и дефисов
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw, expected",
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
def test_space_to_dash(raw, expected):
    assert SpaceToDashRule().apply(raw, is_dir=False) == expected


# --------------------------------------------------------------------------- #
# CaseRule / TrimEdgeRule
# --------------------------------------------------------------------------- #
def test_case_rule():
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
    assert nn.normalize(name, is_dir=False) == expected


@pytest.mark.parametrize(
    "raw, expected",
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
    ],
)
def test_trim_edge(raw, expected):
    assert TrimEdgeRule().apply(raw, is_dir=False) == expected


def test_trim_edge_dir_keeps_leading_underscore():
    # Ведущий '_' сохраняется и у папок (как у файлов); хвостовой мусор обрезается.
    assert TrimEdgeRule().apply("__name__", is_dir=True) == "__name"


def test_empty_stem_guard(nn):
    # Имя из символов, которые после транслитерации/чистки исчезают -> без изменений.
    assert nn.normalize("@@@.png", is_dir=False) == "@@@.png"


# --------------------------------------------------------------------------- #
# Безопасность: транслитерация не должна вносить разделители пути / управляющие
# символы. Иначе os.rename истолковал бы их как путь и переместил/потерял объект.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw",
    [
        "½", "¼", "¾", "10½", "½ доля", "naïve½", "файл ½",
        "∖обратная", "↘стрелка", "＼fullwidth",  # дают '\' через unidecode
        "пример\u2028строка", "две\u2029строки",  # дают '\n' через unidecode
    ],
)
def test_no_path_separators_introduced(nn, raw):
    for is_dir in (False, True):
        out = nn.normalize(raw if is_dir else raw + ".txt", is_dir=is_dir)
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
    "raw",
    [
        "«ёлочки»", "ООО «Печоралифтсервис»", "“кавычки”", "„нижние“",
        "файл «с» кавычками", "‹одинарные›",
    ],
)
def test_no_windows_forbidden_introduced(nn, raw):
    for is_dir in (False, True):
        out = nn.normalize(raw if is_dir else raw + ".txt", is_dir=is_dir)
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


@pytest.mark.parametrize("raw", ["½", "10½", "½ доля", "naïve½"])
def test_fraction_idempotent(nn, raw):
    once = nn.normalize(raw, is_dir=False)
    assert nn.normalize(once, is_dir=False) == once


# --------------------------------------------------------------------------- #
# FilesystemNormalizer (e2e на временной папке)
# --------------------------------------------------------------------------- #
def _make_tree(root):
    (root / "Отчёт 2020").mkdir()
    (root / "Отчёт 2020" / "20.05.2020_dump").write_text("x")
    (root / "1_file.TXT").write_text("x")
    (root / "v2 readme.MD").write_text("x")
    hidden = root / ".git"
    hidden.mkdir()
    (hidden / "CONFIG").write_text("x")
    (root / ".env").write_text("x")


def test_fs_end_to_end(tmp_path):
    _make_tree(tmp_path)
    fs = FilesystemNormalizer(build_normalizer())
    fs.apply(tmp_path)

    assert (tmp_path / "Otchiot_2020-00-00").is_dir()
    assert (tmp_path / "Otchiot_2020-00-00" / "2020-05-20_dump").exists()
    assert (tmp_path / "01_file.TXT").exists()
    assert (tmp_path / "v2-readme.MD").exists()
    # Скрытые не тронуты:
    assert (tmp_path / ".git").is_dir()
    assert (tmp_path / ".git" / "CONFIG").exists()
    assert (tmp_path / ".env").exists()


def test_fs_idempotent_second_run_empty(tmp_path):
    _make_tree(tmp_path)
    fs = FilesystemNormalizer(build_normalizer())
    fs.apply(tmp_path)
    renamed, skipped = fs.apply(tmp_path)
    assert renamed == 0


def test_fs_conflict_skipped(tmp_path):
    (tmp_path / "a b.md").write_text("a")  # -> "a-b.md"
    (tmp_path / "a-b.md").write_text("b")  # уже "a-b.md"
    fs = FilesystemNormalizer(build_normalizer())
    renamed, skipped = fs.apply(tmp_path)
    # Переименование в уже занятое имя пропускается, оба файла сохраняются.
    assert renamed == 0
    assert skipped >= 1
    assert (tmp_path / "a b.md").exists()
    assert (tmp_path / "a-b.md").exists()


def test_fs_no_relocation_via_separator(tmp_path):
    # Регресс на критический баг: имя с дробью раньше давало '10-1/2.dat' и os.rename
    # МОЛЧА перемещал файл в соседний каталог '10-1'. Теперь имя остаётся одним
    # компонентом пути, файл нормализуется на месте, ничего не теряется.
    secret = tmp_path / "10½.dat"
    secret.write_text("СЕКРЕТ")
    sibling = tmp_path / "10-1"
    sibling.mkdir()
    (sibling / "keep.txt").write_text("сосед")
    fs = FilesystemNormalizer(build_normalizer())
    fs.apply(tmp_path)
    # Данные остались прямо в корне (не уехали внутрь соседнего каталога):
    survivors = [p for p in tmp_path.iterdir() if p.is_file() and p.read_text() == "СЕКРЕТ"]
    assert len(survivors) == 1
    assert "/" not in survivors[0].name and "\\" not in survivors[0].name
    assert (tmp_path / "10½.dat").exists() is False  # переименован


def test_fs_guillemets_renamed_no_data_loss(tmp_path):
    # Регресс на WinError 123: имя с кавычками-«ёлочками» давало '<<'/'>>' через
    # unidecode, и одиночный '<' в середине ломал переименование на Windows.
    # Теперь запрещённые символы вырезаются, файл нормализуется на месте.
    doc = tmp_path / "Заявление ООО «Печоралифтсервис».docx"
    doc.write_text("ДАННЫЕ")
    fs = FilesystemNormalizer(build_normalizer())
    fs.apply(tmp_path)
    survivors = [p for p in tmp_path.iterdir() if p.is_file() and p.read_text() == "ДАННЫЕ"]
    assert len(survivors) == 1
    name = survivors[0].name
    assert not any(ch in name for ch in '<>:"|?*')
    assert name == "zaiavlenie-ooo-pechoraliftservis.docx"
    assert doc.exists() is False  # переименован


def test_fs_case_collision_no_data_loss(tmp_path):
    # Регистрозависимая ФС: "File.md" нормализуется в "file.md", где уже есть
    # другой файл. Это конфликт — переименование должно пропускаться, а не
    # перезатирать существующий файл.
    (tmp_path / "File.md").write_text("upper")
    (tmp_path / "file.md").write_text("lower")
    if len(list(tmp_path.iterdir())) < 2:
        pytest.skip("регистронезависимая ФС: файлы-двойники не сосуществуют")
    fs = FilesystemNormalizer(build_normalizer())
    renamed, skipped = fs.apply(tmp_path)
    assert renamed == 0
    assert skipped >= 1
    assert (tmp_path / "File.md").read_text() == "upper"
    assert (tmp_path / "file.md").read_text() == "lower"


# --------------------------------------------------------------------------- #
# FsIgnore — матчинг в стиле .gitignore (движок pathspec), относительно корня
# --------------------------------------------------------------------------- #
def _ign(*lines):
    spec = pathspec.PathSpec.from_lines(_FACTORY, lines)
    has_negation = any(p.include is False for p in spec.patterns)
    return FsIgnore(spec, has_negation)


@pytest.mark.parametrize(
    "lines, rel, is_dir, ignored",
    [
        # basename (без '/') совпадает на любой глубине; границы сегмента:
        (["Archive"], "Archive", True, True),
        (["Archive"], "a/b/Archive", True, True),
        (["Archive"], "MyArchive", True, False),
        (["Archive"], "Archive2", True, False),
        # потомки исключённого каталога тоже исключены:
        (["Archive"], "a/Archive/file.txt", False, True),
        # завершающий '/' — только каталог, не одноимённый файл:
        (["build/"], "build", True, True),
        (["build/"], "build", False, False),
        (["build/"], "build/out.o", False, True),
        # '/' в паттерне (ведущий или срединный) — якорь к корню нормализации:
        (["/Archive"], "Archive", True, True),
        (["/Archive"], "a/Archive", True, False),
        (["Home/Components"], "Home/Components", True, True),
        (["Home/Components"], "x/Home/Components", True, False),
        # '*' — в пределах сегмента; '**' — через сегменты (в т.ч. ноль):
        (["*.bak"], "Docs/notes.bak", False, True),
        (["*.bak"], "Docs/notes.txt", False, False),
        (["Projects/*/build"], "Projects/web/build", True, True),
        (["Projects/*/build"], "Projects/build", True, False),
        (["Projects/**/Data"], "Projects/a/b/Data", True, True),
        (["Projects/**/Data"], "Projects/Data", True, True),
        # СМЕНА КОНТРАКТА: '[abc]' — класс, '?' — один символ (активные метасимволы):
        (["file[12]"], "file1", False, True),
        (["file[12]"], "file3", False, False),
        (["a?b"], "axb", False, True),
        (["a?b"], "ab", False, False),
        # Литеральные скобки/'?' — через экранирование '\':
        ([r"Файл \[1\]"], "Файл [1]", True, True),
        ([r"Файл \[1\]"], "Файл 1", True, False),
        # Регистрозависимость (как в git на регистрозависимой ФС):
        (["Archive"], "archive", True, False),
        (["*.txt"], "Notes.TXT", False, False),
        # Комментарии и пустые строки игнорируются:
        (["# комментарий", "", "Archive"], "Archive", True, True),
    ],
)
def test_fsignore_matching(lines, rel, is_dir, ignored):
    assert _ign(*lines).matches(PurePosixPath(rel), is_dir) is ignored


def test_fsignore_empty_never_matches():
    ign = _ign()
    assert ign.matches(PurePosixPath("anything/at/all"), True) is False
    assert ign.has_negation is False


def test_fsignore_negation_last_match_wins():
    # '!' возвращает убранное; выигрывает последняя совпавшая строка.
    ign = _ign("*.log", "!keep.log")
    assert ign.matches(PurePosixPath("a.log"), False) is True
    assert ign.matches(PurePosixPath("keep.log"), False) is False
    assert ign.has_negation is True


def test_fsignore_order_reexclude_after_reinclude():
    # Порядок важен: повторное исключение перекрывает более раннее включение.
    ign = _ign("build/", "!build/keep/", "build/keep/secret")
    assert ign.matches(PurePosixPath("build/keep"), True) is False
    assert ign.matches(PurePosixPath("build/keep/secret"), False) is True


# --------------------------------------------------------------------------- #
# load_fs_ignore — чтение .fs-ignore из корня проекта
# --------------------------------------------------------------------------- #
def test_load_fs_ignore_missing_file(tmp_path):
    # Нет файла -> None (фильтр выключен).
    assert load_fs_ignore(tmp_path) is None


def test_load_fs_ignore_empty_file(tmp_path):
    # Пустой файл -> FsIgnore без правил (ничего не исключает).
    (tmp_path / ".fs-ignore").write_text("")
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    assert ign.matches(PurePosixPath("home/user/Archive"), True) is False
    assert ign.has_negation is False


def test_load_fs_ignore_patterns_comments_negation(tmp_path):
    (tmp_path / ".fs-ignore").write_text(
        "# комментарий\nArchive\n\n*.bak\n!important.bak\n"
    )
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    assert ign.matches(PurePosixPath("x/Archive/y"), False) is True
    assert ign.matches(PurePosixPath("notes.bak"), False) is True
    assert ign.matches(PurePosixPath("important.bak"), False) is False
    assert ign.has_negation is True


def test_load_fs_ignore_does_not_modify_file(tmp_path):
    # Файл при сопоставлении не изменяется: содержимое читается как есть.
    content = "Archive\n*.bak\n"
    f = tmp_path / ".fs-ignore"
    f.write_text(content)
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    ign.matches(PurePosixPath("x/Archive"), True)
    assert f.read_text() == content


def test_load_fs_ignore_utf8_bom(tmp_path):
    # BOM в начале файла не ломает первый паттерн (чтение utf-8-sig).
    (tmp_path / ".fs-ignore").write_text("Archive\n", encoding="utf-8-sig")
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    assert ign.matches(PurePosixPath("Archive"), True) is True


# --------------------------------------------------------------------------- #
# FilesystemNormalizer + .fs-ignore (e2e на временной папке)
# --------------------------------------------------------------------------- #
def test_fs_ignored_dir_not_renamed_or_descended(tmp_path):
    # Исключённый каталог не переименовывается, внутрь не заходим (содержимое
    # тоже не трогаем), при этом видимый сосед нормализуется.
    archive = tmp_path / "Archive"
    archive.mkdir()
    (archive / "Отчёт 2020").write_text("x")  # имя осталось бы ненормализованным
    (tmp_path / "Отчёт 2020").write_text("y")
    fs = FilesystemNormalizer(build_normalizer(), _ign("Archive"))
    fs.apply(tmp_path)
    # Исключённый каталог и его содержимое не тронуты:
    assert (tmp_path / "Archive").is_dir()
    assert (tmp_path / "Archive" / "Отчёт 2020").exists()
    # Сосед нормализован:
    assert (tmp_path / "otchiot_2020-00-00").exists()


def test_fs_ignored_not_counted(tmp_path):
    # Исключённые объекты не попадают в счётчики renamed/skipped.
    archive = tmp_path / "Archive"
    archive.mkdir()
    (archive / "Файл (1).txt").write_text("x")  # был бы переименован
    (tmp_path / "Файл (1).txt").write_text("y")  # сосед -> переименование
    fs = FilesystemNormalizer(build_normalizer(), _ign("Archive"))
    renamed, skipped = fs.apply(tmp_path)
    assert renamed == 1  # только сосед
    assert skipped == 0
    assert (tmp_path / "fail-01.txt").exists()


def test_fs_ignore_file_by_name(tmp_path):
    # Паттерн может совпасть с именем самого файла.
    (tmp_path / "Keep").write_text("x")  # имя нормализуемо, но исключено
    (tmp_path / "Drop me").write_text("y")
    fs = FilesystemNormalizer(build_normalizer(), _ign("Keep"))
    renamed, skipped = fs.apply(tmp_path)
    assert (tmp_path / "Keep").exists()  # не тронут
    assert (tmp_path / "drop-me").exists()  # сосед нормализован
    assert renamed == 1
    assert skipped == 0


def test_fs_without_ignorer_behaves_as_before(tmp_path):
    # ignorer=None (по умолчанию) -> прежнее поведение.
    (tmp_path / "Archive").mkdir()
    (tmp_path / "Archive" / "Отчёт.txt").write_text("x")
    fs = FilesystemNormalizer(build_normalizer())
    fs.apply(tmp_path)
    assert (tmp_path / "Archive" / "otchiot.txt").exists()


def test_fs_ignore_basename_anywhere(tmp_path):
    # Паттерн без '/' (basename) исключает 'notes.txt' в любом месте дерева;
    # прочие файлы нормализуются. Каталоги названы уже нормализованно.
    (tmp_path / "Docs").mkdir()
    (tmp_path / "Deep" / "Inner").mkdir(parents=True)
    (tmp_path / "Docs" / "notes.txt").write_text("1")
    (tmp_path / "Deep" / "Inner" / "notes.txt").write_text("2")
    (tmp_path / "Docs" / "Заметки.txt").write_text("3")
    fs = FilesystemNormalizer(build_normalizer(), _ign("notes.txt"))
    renamed, skipped = fs.apply(tmp_path)
    # notes.txt не тронуты и не посчитаны:
    assert (tmp_path / "Docs" / "notes.txt").exists()
    assert (tmp_path / "Deep" / "Inner" / "notes.txt").exists()
    # Прочий файл нормализован:
    assert (tmp_path / "Docs" / "zametki.txt").exists()
    assert skipped == 0
    assert renamed == 1  # только 'Заметки.txt' менял имя


def test_fs_ignore_anchored_path(tmp_path):
    # Якорный паттерн с '/' ('Sub/notes.txt') действует только в этой цепочке от
    # корня нормализации (не как basename в любом месте).
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Other").mkdir()
    (tmp_path / "Sub" / "notes.txt").write_text("1")
    (tmp_path / "Other" / "notes.txt").write_text("2")
    fs = FilesystemNormalizer(build_normalizer(), _ign("Sub/notes.txt"))
    fs.apply(tmp_path)
    assert (tmp_path / "Sub" / "notes.txt").exists()    # исключён
    # 'Other/notes.txt' не исключён; имя уже нормализовано -> остаётся
    assert (tmp_path / "Other" / "notes.txt").exists()


def test_fs_ignore_case_sensitive(tmp_path):
    # Паттерн Archive не исключает каталог archive (разный регистр).
    upper = tmp_path / "Archive"
    lower = tmp_path / "archive"
    upper.mkdir()
    lower.mkdir()
    (upper / "Файл.txt").write_text("x")
    (lower / "Файл.txt").write_text("y")
    fs = FilesystemNormalizer(build_normalizer(), _ign("Archive"))
    fs.apply(tmp_path)
    assert (upper / "Файл.txt").exists()              # исключён
    assert (lower / "fail.txt").exists()              # нормализован


def test_fs_negation_reincludes_file(tmp_path):
    # '!' возвращает к нормализации убранное; порядок строк важен.
    (tmp_path / "Docs").mkdir()
    (tmp_path / "Docs" / "Черновик.tmp").write_text("x")  # остаётся исключён
    (tmp_path / "Docs" / "Важное.keep").write_text("y")    # возвращён
    ign = _ign("Docs/*", "!Docs/*.keep")
    fs = FilesystemNormalizer(build_normalizer(), ign)
    fs.apply(tmp_path)
    assert (tmp_path / "Docs" / "Черновик.tmp").exists()   # исключён -> не тронут
    assert (tmp_path / "Docs" / "vazhnoe.keep").exists()   # включён -> нормализован


def test_fs_negation_probe_descends_ignored_dir(tmp_path):
    # При наличии '!' обход не обрезает исключённые каталоги (probe): потомок
    # внутри Archive достижим и нормализуется, сам Archive остаётся исключён.
    data = tmp_path / "Archive" / "nested" / "Data"
    (data / "Папка").mkdir(parents=True)
    ign = _ign("Archive", "!**/Data/**")
    assert ign.has_negation is True
    fs = FilesystemNormalizer(build_normalizer(), ign)
    fs.apply(tmp_path)
    assert (data / "Papka").is_dir()       # возвращённый потомок нормализован
    assert (tmp_path / "Archive").is_dir()  # промежуточный Archive не тронут


def test_fs_ignore_bracket_class_active(tmp_path):
    # СМЕНА КОНТРАКТА: '[12]' теперь КЛАСС символов (а не литерал). 'отчёт[12]'
    # исключает 'отчёт1', но не 'отчёт3' (тот нормализуется).
    a = tmp_path / "отчёт1"
    b = tmp_path / "отчёт3"
    a.mkdir()
    b.mkdir()
    (a / "вложение").write_text("x")
    (b / "вложение").write_text("y")
    fs = FilesystemNormalizer(build_normalizer(), _ign("отчёт[12]"))
    fs.apply(tmp_path)
    assert (a / "вложение").exists()  # исключён классом -> не тронут
    survivors = [p for p in tmp_path.rglob("*") if p.is_file() and p.read_text() == "y"]
    assert len(survivors) == 1
    assert survivors[0].name == "vlozhenie"  # 'отчёт3' не исключён -> нормализован


def test_fs_ignore_literal_bracket_escaped(tmp_path):
    # Литеральные скобки экранируются '\': 'Файл \[1\]' исключает ровно такой
    # каталог, а 'Файл 2' — нет (нормализуется).
    a = tmp_path / "Файл [1]"
    b = tmp_path / "Файл 2"
    a.mkdir()
    b.mkdir()
    (a / "вложение").write_text("x")
    (b / "вложение").write_text("y")
    fs = FilesystemNormalizer(build_normalizer(), _ign(r"Файл \[1\]"))
    fs.apply(tmp_path)
    assert (a / "вложение").exists()  # исключён литерально -> не тронут
    survivors = [p for p in tmp_path.rglob("*") if p.is_file() and p.read_text() == "y"]
    assert len(survivors) == 1
    assert survivors[0].name == "vlozhenie"
