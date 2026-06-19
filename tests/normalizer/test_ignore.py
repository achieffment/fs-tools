"""Тесты фильтра .fs-ignore (ignore.py).

Матчинг в стиле .gitignore (движок pathspec) относительно корня нормализации,
чтение `load_fs_ignore` и интеграция фильтра с FsNormalizer (e2e на временной папке).
"""
from pathlib import PurePosixPath

import pathspec
import pytest

from fs_tools.normalizer import (
    FsIgnore,
    FsNormalizer,
    build_normalizer,
    load_fs_ignore,
)
from fs_tools.shared.pathspec_compat import _FACTORY


# --------------------------------------------------------------------------- #
# FsIgnore — матчинг в стиле .gitignore (движок pathspec), относительно корня
# --------------------------------------------------------------------------- #
def _ign(*lines):
    """Вспомогательная функция для теста."""
    spec = pathspec.PathSpec.from_lines(_FACTORY, lines)
    incl = any(p.include is False for p in spec.patterns)
    return FsIgnore(spec, incl)


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
        # Префикс './' НЕ поддерживается ('.' — обычный сегмент): не совпадает,
        # тогда как basename 'Foo' и якорь '/Foo' — совпадают:
        (["./Foo"], "Foo", True, False),
        (["Foo"], "Foo", True, True),
        (["/Foo"], "Foo", True, True),
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
        # Регистронезависимость (как git core.ignorecase=true): совпадает в любом регистре:
        (["Archive"], "archive", True, True),
        (["*.txt"], "Notes.TXT", False, True),
        # Комментарии и пустые строки игнорируются:
        (["# комментарий", "", "Archive"], "Archive", True, True),
    ],
)
def test_fsignore_matching(lines, rel, is_dir, ignored):
    """Проверяет сценарий: fsignore matching."""
    assert _ign(*lines).matches(PurePosixPath(rel), is_dir) is ignored


def test_fsignore_empty_never_matches():
    """Проверяет сценарий: fsignore empty never matches."""
    ign = _ign()
    assert ign.matches(PurePosixPath("anything/at/all"), True) is False
    assert ign.has_overrides() is False


def test_fsignore_negation_last_match_wins():
    # '!' возвращает убранное; выигрывает последняя совпавшая строка.
    """Проверяет сценарий: fsignore negation last match wins."""
    ign = _ign("*.log", "!keep.log")
    assert ign.matches(PurePosixPath("a.log"), False) is True
    assert ign.matches(PurePosixPath("keep.log"), False) is False
    assert ign.has_overrides() is True


def test_fsignore_order_reexclude_after_reinclude():
    # Порядок важен: повторное исключение перекрывает более раннее включение.
    """Проверяет сценарий: fsignore order reexclude after reinclude."""
    ign = _ign("build/", "!build/keep/", "build/keep/secret")
    assert ign.matches(PurePosixPath("build/keep"), True) is False
    assert ign.matches(PurePosixPath("build/keep/secret"), False) is True


# Реальная пользовательская конфигурация: проекты занятий исключены целиком, но
# папки Data внутри них возвращаются на любой глубине (!/Activities/*/Projects/**/Data),
# в т.ч. под исключённым Archive. Проверяем, что затрагиваются ТОЛЬКО папки Data.
_ACTIVITIES_LINES = (
    "Archive",
    "/Activities/*/Projects",
    "!/Activities/*/Projects/**/Data",
    "!/Activities/Video/Projects",
    "/Components",
    "/Resources/Fonts",
)


@pytest.mark.parametrize(
    "rel, ignored",
    [
        # Проект технического занятия и его содержимое исключены...
        ("Activities/Web/Projects", True),
        ("Activities/Web/Projects/Addl", True),
        ("Activities/Web/Projects/Addl/Archive", True),
        ("Activities/Web/Projects/Addl/Archive/example.com", True),
        ("Activities/Web/Projects/Addl/Archive/example.com/Back", True),
        # ...кроме папок Data (на любой глубине, сквозь сегменты, под Archive):
        ("Activities/Web/Projects/Addl/Archive/example.com/Data", False),
        ("Activities/Web/Projects/Addl/Archive/example.com/Data/sub", False),
        ("Activities/Web/Projects/Self/Data", False),
        ("Activities/Web/Projects/Data", False),       # ** = ноль сегментов
        # Сайт-каталог рядом с Archive (НЕ под ним): исключён правилом Projects,
        # т.е. exclude не зависит от вложенности в Archive; его Data всё равно возвращён:
        ("Activities/Web/Projects/Addl/another.com", True),
        ("Activities/Web/Projects/Addl/another.com/Back", True),
        ("Activities/Web/Projects/Addl/another.com/Data", False),
        # Возврат только по ТОЧНОМУ сегменту Data: похожие имена остаются исключены:
        ("Activities/Web/Projects/Addl/Database", True),
        ("Activities/Web/Projects/Addl/DataX", True),
        ("Activities/Web/Projects/Addl/My Data", True),
        # Ресурсы вне Projects не затрагиваются исключением проектов:
        ("Activities/Web/Resources", False),
        # Творческое занятие возвращено целиком (включая не-Data содержимое):
        ("Activities/Video/Projects/Clip/Back", False),
        # Прочие якорные исключения:
        ("Components", True),
        ("Resources/Fonts", True),
    ],
)
def test_fsignore_activities_projects_data(rel, ignored):
    """Проверяет сценарий: fsignore activities projects data."""
    assert _ign(*_ACTIVITIES_LINES).matches(PurePosixPath(rel), True) is ignored


# --------------------------------------------------------------------------- #
# load_fs_ignore — чтение .fs-ignore из выбранного каталога (корня нормализации)
# --------------------------------------------------------------------------- #
def test_load_fs_ignore_missing_file(tmp_path):
    # Нет файла -> None (фильтр выключен).
    """Проверяет сценарий: load fs ignore missing file."""
    assert load_fs_ignore(tmp_path) is None


def test_load_fs_ignore_empty_file(tmp_path):
    # Пустой файл -> FsIgnore без правил (ничего не исключает).
    """Проверяет сценарий: load fs ignore empty file."""
    (tmp_path / ".fs-ignore").write_text("")
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    assert ign.matches(PurePosixPath("home/user/Archive"), True) is False
    assert ign.has_overrides() is False


def test_load_fs_ignore_patterns_comments_negation(tmp_path):
    """Проверяет сценарий: load fs ignore patterns comments negation."""
    (tmp_path / ".fs-ignore").write_text(
        "# комментарий\nArchive\n\n*.bak\n!important.bak\n"
    )
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    assert ign.matches(PurePosixPath("x/Archive/y"), False) is True
    assert ign.matches(PurePosixPath("notes.bak"), False) is True
    assert ign.matches(PurePosixPath("important.bak"), False) is False
    assert ign.has_overrides() is True


def test_load_fs_ignore_does_not_modify_file(tmp_path):
    # Файл при сопоставлении не изменяется: содержимое читается как есть.
    """Проверяет сценарий: load fs ignore does not modify file."""
    cont = "Archive\n*.bak\n"
    f = tmp_path / ".fs-ignore"
    f.write_text(cont)
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    ign.matches(PurePosixPath("x/Archive"), True)
    assert f.read_text() == cont


def test_load_fs_ignore_utf8_bom(tmp_path):
    # BOM в начале файла не ломает первый паттерн (чтение utf-8-sig).
    """Проверяет сценарий: load fs ignore utf8 bom."""
    (tmp_path / ".fs-ignore").write_text("Archive\n", encoding="utf-8-sig")
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    assert ign.matches(PurePosixPath("Archive"), True) is True


# --------------------------------------------------------------------------- #
# FsNormalizer + .fs-ignore (e2e на временной папке)
# --------------------------------------------------------------------------- #
def test_fs_ignored_dir_not_renamed_or_descended(tmp_path):
    # Исключённый каталог не переименовывается, внутрь не заходим (содержимое
    # тоже не трогаем), при этом видимый сосед нормализуется.
    """Проверяет сценарий: fs ignored dir not renamed or descended."""
    backup = tmp_path / "Archive"
    backup.mkdir()
    (backup / "Отчёт 2020").write_text("x")  # имя осталось бы ненормализованным
    (tmp_path / "Отчёт 2020").write_text("y")
    fsnm = FsNormalizer(build_normalizer(), _ign("Archive"))
    fsnm.apply(tmp_path)
    # Исключённый каталог и его содержимое не тронуты:
    assert (tmp_path / "Archive").is_dir()
    assert (tmp_path / "Archive" / "Отчёт 2020").exists()
    # Сосед нормализован:
    assert (tmp_path / "otchiot_2020-00-00").exists()


def test_fs_ignored_not_counted(tmp_path):
    # Исключённые объекты не попадают в счётчики renamed/skipped.
    """Проверяет сценарий: fs ignored not counted."""
    backup = tmp_path / "Archive"
    backup.mkdir()
    (backup / "Файл (1).txt").write_text("x")  # был бы переименован
    (tmp_path / "Файл (1).txt").write_text("y")  # сосед -> переименование
    fsnm = FsNormalizer(build_normalizer(), _ign("Archive"))
    renamed, skipped = fsnm.apply(tmp_path)
    assert renamed == 1  # только сосед
    assert skipped == 0
    assert (tmp_path / "fail-01.txt").exists()


def test_fs_ignore_file_by_name(tmp_path):
    # Паттерн может совпасть с именем самого файла.
    """Проверяет сценарий: fs ignore file by name."""
    (tmp_path / "Keep").write_text("x")  # имя нормализуемо, но исключено
    (tmp_path / "Drop me").write_text("y")
    fsnm = FsNormalizer(build_normalizer(), _ign("Keep"))
    renamed, skipped = fsnm.apply(tmp_path)
    assert (tmp_path / "Keep").exists()  # не тронут
    assert (tmp_path / "drop-me").exists()  # сосед нормализован
    assert renamed == 1
    assert skipped == 0


def test_fs_without_ignorer_behaves_as_before(tmp_path):
    # ignorer=None (по умолчанию) -> прежнее поведение.
    """Проверяет сценарий: fs without ignorer behaves as before."""
    (tmp_path / "Archive").mkdir()
    (tmp_path / "Archive" / "Отчёт.txt").write_text("x")
    fsnm = FsNormalizer(build_normalizer())
    fsnm.apply(tmp_path)
    assert (tmp_path / "Archive" / "otchiot.txt").exists()


def test_fs_ignore_basename_anywhere(tmp_path):
    # Паттерн без '/' (basename) исключает 'notes.txt' в любом месте дерева;
    # прочие файлы нормализуются. Каталоги названы уже нормализованно.
    """Проверяет сценарий: fs ignore basename anywhere."""
    (tmp_path / "Docs").mkdir()
    (tmp_path / "Deep" / "Inner").mkdir(parents=True)
    (tmp_path / "Docs" / "notes.txt").write_text("1")
    (tmp_path / "Deep" / "Inner" / "notes.txt").write_text("2")
    (tmp_path / "Docs" / "Заметки.txt").write_text("3")
    fsnm = FsNormalizer(build_normalizer(), _ign("notes.txt"))
    renamed, skipped = fsnm.apply(tmp_path)
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
    """Проверяет сценарий: fs ignore anchored path."""
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Other").mkdir()
    (tmp_path / "Sub" / "notes.txt").write_text("1")
    (tmp_path / "Other" / "notes.txt").write_text("2")
    fsnm = FsNormalizer(build_normalizer(), _ign("Sub/notes.txt"))
    fsnm.apply(tmp_path)
    assert (tmp_path / "Sub" / "notes.txt").exists()    # исключён
    # 'Other/notes.txt' не исключён; имя уже нормализовано -> остаётся
    assert (tmp_path / "Other" / "notes.txt").exists()


def test_fs_ignore_case_insensitive(tmp_path):
    # Матчинг регистронезависим (как git core.ignorecase=true): паттерн Archive
    # исключает и Archive, и archive — содержимое обоих не трогаем.
    """Проверяет сценарий: fs ignore case insensitive."""
    upper = tmp_path / "Archive"
    lower = tmp_path / "archive"
    upper.mkdir()
    lower.mkdir()
    (upper / "Файл.txt").write_text("x")
    (lower / "Файл.txt").write_text("y")
    fsnm = FsNormalizer(build_normalizer(), _ign("Archive"))
    fsnm.apply(tmp_path)
    assert (upper / "Файл.txt").exists()              # исключён
    assert (lower / "Файл.txt").exists()              # тоже исключён (регистр не важен)


def test_fs_ignore_idempotent_across_runs_with_capitalized_parent(tmp_path):
    # Кросс-прогонная идемпотентность фильтра: вышележащие каталоги (box/inner) не
    # совпадают с паттерном и капитализируются CaseRule (box -> Box, inner -> Inner).
    # На втором прогоне якорь /box/inner/*.bak должен совпасть с Box/Inner/... за
    # счёт регистронезависимости — иначе исключённый файл нормализуется (баг).
    """Проверяет сценарий: fs ignore idempotent across runs with capitalized parent."""
    inner = tmp_path / "box" / "inner"
    inner.mkdir(parents=True)
    (inner / "Секрет.bak").write_text("x")           # был бы нормализован -> sekret.bak
    (tmp_path / ".fs-ignore").write_text("/box/inner/*.bak\n")

    ign1 = load_fs_ignore(tmp_path)
    assert ign1 is not None
    FsNormalizer(build_normalizer(), ign1).apply(tmp_path)
    # После первого прогона родители капитализированы, файл исключён и не тронут:
    assert (tmp_path / "Box" / "Inner" / "Секрет.bak").exists()

    # Второй прогон поверх результата (фильтр перечитывается из того же .fs-ignore):
    ign2 = load_fs_ignore(tmp_path)
    assert ign2 is not None
    renamed, _ = FsNormalizer(build_normalizer(), ign2).apply(tmp_path)
    assert renamed == 0                              # ничего не меняется
    assert (tmp_path / "Box" / "Inner" / "Секрет.bak").exists()
    assert not (tmp_path / "Box" / "Inner" / "sekret.bak").exists()


def test_fs_negation_reincludes_file(tmp_path):
    # '!' возвращает к нормализации убранное; порядок строк важен.
    """Проверяет сценарий: fs negation reincludes file."""
    (tmp_path / "Docs").mkdir()
    (tmp_path / "Docs" / "Черновик.tmp").write_text("x")  # остаётся исключён
    (tmp_path / "Docs" / "Важное.keep").write_text("y")    # возвращён
    ign = _ign("Docs/*", "!Docs/*.keep")
    fsnm = FsNormalizer(build_normalizer(), ign)
    fsnm.apply(tmp_path)
    assert (tmp_path / "Docs" / "Черновик.tmp").exists()   # исключён -> не тронут
    assert (tmp_path / "Docs" / "vazhnoe.keep").exists()   # включён -> нормализован


def test_fs_hidden_not_reincluded_by_negation(tmp_path):
    # Скрытые (имя на '.') отсекаются `_hidden` ДО фильтра и внутрь не заходим,
    # поэтому правило-'!' их не возвращает (даже при включённом probe через overrides).
    """Проверяет сценарий: fs hidden not reincluded by negation."""
    (tmp_path / ".keep").write_text("x")            # скрытый файл
    hidden = tmp_path / ".cfg"
    hidden.mkdir()
    (hidden / "Отчёт 2020").write_text("y")          # внутрь скрытой папки не заходим
    ign = _ign("Archive", "!*.keep", "!.cfg/**")    # '!' -> has_overrides() == True
    assert ign.has_overrides() is True
    fsnm = FsNormalizer(build_normalizer(), ign)
    renamed, skipped = fsnm.apply(tmp_path)
    assert (tmp_path / ".keep").exists()             # скрытый файл не тронут
    assert (hidden / "Отчёт 2020").exists()          # содержимое скрытой папки не тронуто
    assert renamed == 0
    assert skipped == 0


def test_fs_negation_probe_descends_ignored_dir(tmp_path):
    # При наличии '!' обход не обрезает исключённые каталоги (probe): потомок
    # внутри Archive достижим и нормализуется, сам Archive остаётся исключён.
    """Проверяет сценарий: fs negation probe descends ignored dir."""
    data = tmp_path / "Archive" / "nested" / "Data"
    (data / "Папка").mkdir(parents=True)
    ign = _ign("Archive", "!**/Data/**")
    assert ign.has_overrides() is True
    fsnm = FsNormalizer(build_normalizer(), ign)
    fsnm.apply(tmp_path)
    assert (data / "Papka").is_dir()       # возвращённый потомок нормализован
    assert (tmp_path / "Archive").is_dir()  # промежуточный Archive не тронут


def test_fs_activities_projects_data_reincluded(tmp_path):
    # Реальный кейс: !/Activities/*/Projects/**/Data возвращает к нормализации
    # ТОЛЬКО папки Data внутри проектов (на любой глубине, под исключённым
    # Archive), а остальное содержимое проекта (Back, промежуточные каталоги,
    # соседний с Archive каталог прямо в Addl) остаётся нетронутым и не попадает
    # в счётчики.
    """Проверяет сценарий: fs activities projects data reincluded."""
    addl = tmp_path / "Activities" / "Web" / "Projects" / "Addl"
    base = addl / "Archive" / "example.com"
    back = base / "Back"
    data = base / "Data"
    back.mkdir(parents=True)
    data.mkdir(parents=True)
    (back / "Старый бэкап").write_text("x")        # под Projects, не Data -> исключён
    (data / "Выгрузка 2021").write_text("y")        # внутри Data -> возвращён
    # Сайт-каталог рядом с Archive (прямо в проекте, НЕ под Archive): exclude от
    # правила Projects не зависит от вложенности в Archive. Его Back исключён,
    # а Data возвращена так же, как у example.com.
    sib = addl / "another.com"
    sib_back = sib / "Back"
    sib_data = sib / "Data"
    sib_back.mkdir(parents=True)
    sib_data.mkdir(parents=True)
    (sib_back / "Прошлый отчёт").write_text("z")   # под Projects, не Data -> исключён
    (sib_data / "Выгрузка 2022").write_text("w")    # внутри Data -> возвращён
    # Сайт прямо в Addl вообще без Data: всё содержимое остаётся нетронутым.
    nodata = addl / "example.com"
    nodata.mkdir(parents=True)
    (nodata / "Резервная копия").write_text("r")   # под Projects, не Data -> исключён
    (tmp_path / ".fs-ignore").write_text(
        "Archive\n/Activities/*/Projects\n!/Activities/*/Projects/**/Data\n"
    )

    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    renamed, skipped = FsNormalizer(build_normalizer(), ign).apply(tmp_path)

    # Содержимое Data нормализовано (дата -> ISO) в обоих сайтах:
    assert (data / "vygruzka_2021-00-00").exists()
    assert (sib_data / "vygruzka_2022-00-00").exists()
    # Соседний Back и промежуточные исключённые каталоги не тронуты:
    assert (back / "Старый бэкап").exists()
    assert back.is_dir()
    assert base.is_dir()                             # example.com не переименован
    # Сайт-каталог рядом с Archive и его Back тоже не тронуты:
    assert (sib_back / "Прошлый отчёт").exists()
    assert sib.is_dir()                              # another.com не переименован
    assert sib_back.is_dir()
    # Сайт без Data полностью не тронут:
    assert (nodata / "Резервная копия").exists()
    assert nodata.is_dir()
    assert (tmp_path / "Activities" / "Web" / "Projects").is_dir()
    # Посчитаны только два возвращённых файла Data; исключённое в счётчики не попало:
    assert renamed == 2
    assert skipped == 0


def test_fs_ignore_bracket_class_active(tmp_path):
    # СМЕНА КОНТРАКТА: '[12]' теперь КЛАСС символов (а не литерал). 'отчёт[12]'
    # исключает 'отчёт1', но не 'отчёт3' (тот нормализуется).
    """Проверяет сценарий: fs ignore bracket class active."""
    a = tmp_path / "отчёт1"
    b = tmp_path / "отчёт3"
    a.mkdir()
    b.mkdir()
    (a / "вложение").write_text("x")
    (b / "вложение").write_text("y")
    fsnm = FsNormalizer(build_normalizer(), _ign("отчёт[12]"))
    fsnm.apply(tmp_path)
    assert (a / "вложение").exists()  # исключён классом -> не тронут
    survivors = [p for p in tmp_path.rglob("*") if p.is_file() and p.read_text() == "y"]
    assert len(survivors) == 1
    assert survivors[0].name == "vlozhenie"  # 'отчёт3' не исключён -> нормализован


def test_fs_ignore_literal_bracket_escaped(tmp_path):
    # Литеральные скобки экранируются '\': 'Файл \[1\]' исключает ровно такой
    # каталог, а 'Файл 2' — нет (нормализуется).
    """Проверяет сценарий: fs ignore literal bracket escaped."""
    a = tmp_path / "Файл [1]"
    b = tmp_path / "Файл 2"
    a.mkdir()
    b.mkdir()
    (a / "вложение").write_text("x")
    (b / "вложение").write_text("y")
    fsnm = FsNormalizer(build_normalizer(), _ign(r"Файл \[1\]"))
    fsnm.apply(tmp_path)
    assert (a / "вложение").exists()  # исключён литерально -> не тронут
    survivors = [p for p in tmp_path.rglob("*") if p.is_file() and p.read_text() == "y"]
    assert len(survivors) == 1
    assert survivors[0].name == "vlozhenie"


def test_fs_ignore_read_from_normalized_dir(tmp_path):
    # .fs-ignore лежит ВНУТРИ нормализуемого каталога и читается из него
    # (load_fs_ignore(root)); якорь '/' отсчитывается от этой же папки, а сам файл
    # .fs-ignore (имя на '.') обходом пропускается и не переименовывается.
    """Проверяет сценарий: fs ignore read from normalized dir."""
    (tmp_path / ".fs-ignore").write_text("/Sub\n")
    (tmp_path / "Sub").mkdir()
    (tmp_path / "Other").mkdir()
    (tmp_path / "Sub" / "Отчёт 2020").write_text("x")    # исключён якорем /Sub
    (tmp_path / "Other" / "Отчёт 2020").write_text("y")  # сосед нормализуется
    ign = load_fs_ignore(tmp_path)
    assert ign is not None
    fsnm = FsNormalizer(build_normalizer(), ign)
    renamed, skipped = fsnm.apply(tmp_path)
    assert (tmp_path / "Sub" / "Отчёт 2020").exists()            # исключён
    assert (tmp_path / "Other" / "otchiot_2020-00-00").exists()  # нормализован
    assert (tmp_path / ".fs-ignore").is_file()                   # сам файл уцелел
    # Посчитан только переименованный сосед: .fs-ignore не попал в счётчики.
    assert renamed == 1
    assert skipped == 0
