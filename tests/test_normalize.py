import pytest

from normalizer import (
    BracketsRule,
    CaseRule,
    DateRule,
    FilesystemNormalizer,
    LeadingZeroRule,
    SpaceToDashRule,
    TransliterationRule,
    TrimEdgeRule,
    build_normalizer,
)


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
