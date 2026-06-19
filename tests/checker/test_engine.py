"""Тесты разворачивания правил и сбора нарушений (engine)."""
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from fs_tools.checker import FsChecker, load_fs_rule


def _check(root: Path, rule_text: str) -> list[str]:
    """Записывает .fs-check в корень, прогоняет проверку, возвращает отсутствующие пути."""
    (root / ".fs-check").write_text(rule_text, encoding="utf-8")
    return FsChecker(load_fs_rule(root)).check(root).missing


def test_literal_missing_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: literal missing reported."""
    root = make_tree(["Activities/Web/"])
    # Projects отсутствует у Web.
    assert _check(root, "/Activities/Web/Projects\n") == ["Activities/Web/Projects"]


def test_literal_present_not_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: literal present not reported."""
    root = make_tree(["Activities/Web/Projects/"])
    assert not _check(root, "/Activities/Web/Projects\n")


def test_single_segment_anchor_is_root(make_tree: Callable[[Iterable[str]], Path]) -> None:
    # Пустой префикс => якорь = root; отсутствие литерала репортится, glob(".") не вызывается.
    """Проверяет сценарий: single segment anchor is root."""
    root = make_tree(["Media/"])
    assert _check(root, "/Activities\n/Media\n") == ["Activities"]


def test_fixed_chain_missing_link_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    # Отсутствие звена фиксированной цепочки сообщается, а не маскируется.
    """Проверяет сценарий: fixed chain missing link reported."""
    root = make_tree(["Activities/"])
    missing = _check(root, "/Activities\n/Activities/Web\n/Activities/Web/Projects\n")
    assert missing == ["Activities/Web"]  # глубже якоря нет — только ближайшее звено


def test_star_without_subdirs_no_violation(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: star without subdirs no violation."""
    root = make_tree(["Activities/"])  # ни одной подпапки занятия
    assert not _check(root, "/Activities/*/Projects\n")


def test_star_enumerates_multiple(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: star enumerates multiple."""
    root = make_tree(["Activities/3D/Projects/", "Activities/Web/"])
    # Projects есть у 3D, нет у Web -> одно нарушение.
    assert _check(root, "/Activities/*/Projects\n") == ["Activities/Web/Projects"]


def test_double_star_zero_and_many_levels(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: double star zero and many levels."""
    root = make_tree(
        [
            "P/_Archive/proj/Back/",          # ** = 0 уровней (P/_Archive)
            "P/Addl/_Archive/proj2/",         # ** = 1 уровень (P/Addl/_Archive), Back отсутствует
        ]
    )
    missing = _check(root, "/P/**/_Archive/*/Back\n")
    assert missing == ["P/Addl/_Archive/proj2/Back"]


def test_dedup_identical_violations(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: dedup identical violations."""
    root = make_tree(["Activities/Web/"])
    # Два правила требуют один и тот же путь -> в выводе он один раз.
    assert _check(root, "/Activities/Web/Projects\n/Activities/*/Projects\n") == [
        "Activities/Web/Projects"
    ]


def test_hidden_dirs_ignored(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: hidden dirs ignored."""
    root = make_tree(["Activities/.hidden/", "Activities/Web/Projects/"])
    # Скрытый .hidden не обходим: его отсутствие Projects не нарушение.
    assert not _check(root, "/Activities/*/Projects\n")


def test_symlink_not_dereferenced(make_tree: Callable[[Iterable[str]], Path]) -> None:
    # proj без Back; симлинк P/link -> P/real. Если бы ** разыменовывал симлинки,
    # появился бы лишний якорь P/link/_Archive/proj и второе (ложное) нарушение.
    """Проверяет сценарий: symlink not dereferenced."""
    root = make_tree(["P/real/_Archive/proj/"])
    try:
        (root / "P" / "link").symlink_to(root / "P" / "real", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("симлинки недоступны на этой платформе")  # напр. Windows без привилегий
    missing = _check(root, "/P/**/_Archive/*/Back\n")
    assert missing == ["P/real/_Archive/proj/Back"]  # только реальный путь, без link/


def test_file_mandate_missing_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: file mandate missing reported."""
    root = make_tree(["Work/Fabrikam/widgets.example/Data/"])
    assert _check(root, "/Work/*/*/Data/project.md\n") == [
        "Work/Fabrikam/widgets.example/Data/project.md"
    ]


def test_file_mandate_present_not_reported(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: file mandate present not reported."""
    root = make_tree(["Work/Fabrikam/widgets.example/Data/project.md"])
    assert not _check(root, "/Work/*/*/Data/project.md\n")


def test_exists_mandate_satisfied_by_dir(make_tree: Callable[[Iterable[str]], Path]) -> None:
    # Без завершающего `/` мандат — exists(): папка с тем же именем удовлетворяет.
    """Проверяет сценарий: exists mandate satisfied by dir."""
    root = make_tree(["Work/Fabrikam/widgets.example/Data/project.md/"])  # project.md — каталог
    assert not _check(root, "/Work/*/*/Data/project.md\n")


def test_dir_only_not_satisfied_by_file(make_tree: Callable[[Iterable[str]], Path]) -> None:
    # Завершающий `/` => нужен is_dir(); файл с тем же именем не подходит.
    """Проверяет сценарий: dir only not satisfied by file."""
    root = make_tree(["Activities/Web/Projects/Addl"])  # Addl — файл
    assert _check(root, "/Activities/Web/Projects/Addl/\n") == [
        "Activities/Web/Projects/Addl"
    ]


def test_dir_only_satisfied_by_dir(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: dir only satisfied by dir."""
    root = make_tree(["Activities/Web/Projects/Addl/"])
    assert not _check(root, "/Activities/Web/Projects/Addl/\n")


# --------------------------------------------------------------------------- #
# Узкий момент _Archive: прунинг подстановок и проверка литерала
# --------------------------------------------------------------------------- #
def test_archive_pruned_on_leaf_but_literal_checked(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: archive pruned on leaf but literal checked."""
    root = make_tree(
        [
            "Activities/Web/Projects/Addl/crm.example.com/Back/",   # обычный проект, Back есть
            "Activities/Web/Projects/Addl/_Archive/aero.example/",  # архивный проект без Back
        ]
    )
    rule_text = (
        "/Activities/Web/Projects/Addl/*/Back\n"
        "/Activities/Web/Projects/**/_Archive/*/Back\n"
        "!_Archive\n"
    )
    missing = _check(root, rule_text)
    # Addl/_Archive/Back НЕ требуется (прунинг *), но архивный проект проверяется.
    assert "Activities/Web/Projects/Addl/_Archive/Back" not in missing
    assert missing == ["Activities/Web/Projects/Addl/_Archive/aero.example/Back"]


def test_archive_pruned_on_intermediate_star(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: archive pruned on intermediate star."""
    root = make_tree(
        [
            # обычный проект, нет project.md
            "Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/",
            # _Archive на позиции проекта
            "Activities/Web/Projects/Work/Fabrikam/_Archive/acoustic.example/Data/",
        ]
    )
    rule_text = (
        "/Activities/Web/Projects/Work/*/*/Data/project.md\n"
        "!_Archive\n"
    )
    missing = _check(root, rule_text)
    # _Archive на НЕ-листовой *-позиции отсекается: project.md там не требуется.
    assert (
        "Activities/Web/Projects/Work/Fabrikam/_Archive/acoustic.example/Data/project.md"
        not in missing
    )
    # У реального проекта отсутствие project.md репортится.
    assert missing == [
        "Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/project.md"
    ]


# Канонический .fs-check (источник истины для оракула ниже).
_CANONICAL_RULE = (
    "/Activities\n"
    "/Activities/Web\n"
    "/Activities/Web/Projects\n"
    "/Activities/*/Projects\n"
    "/Activities/*/Resources\n"
    "/Activities/Web/Projects/Addl\n"
    "/Activities/Web/Projects/Self\n"
    "/Activities/Web/Projects/Work\n"
    "/Activities/Web/Projects/Addl/*/Back\n"
    "/Activities/Web/Projects/Addl/*/Data\n"
    "/Activities/Web/Projects/Self/*/Back\n"
    "/Activities/Web/Projects/Self/*/Data\n"
    "/Activities/Web/Projects/Work/*/*/Back\n"
    "/Activities/Web/Projects/Work/*/*/Data\n"
    "/Activities/Web/Projects/Work/*/*/Data/project.md\n"
    "/Activities/Web/Projects/**/_Archive/*/Back\n"
    "/Activities/Web/Projects/**/_Archive/*/Data\n"
    "!_Archive\n"
)


def test_canonical_oracle_exactly_four(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    # Минимизированное дерево домена: у aero.example нет Data, у acoustic.example нет
    # ни Back, ни Data. Ожидаемый эталон — ровно 4 нарушения.
    """Проверяет сценарий: canonical oracle exactly four."""
    P = "Activities/Web/Projects/"
    root = make_tree(
        [
            "Activities/3D/Projects/",        # есть Projects, нет Resources -> нарушение
            "Activities/Web/Resources/",
            f"{P}Addl/crm.example.com/Back/",
            f"{P}Addl/crm.example.com/Data/",
            f"{P}Addl/safegrid.example/Back/",
            f"{P}Addl/safegrid.example/Data/",
            f"{P}Addl/shop.example.com/Back/",
            f"{P}Addl/shop.example.com/Data/",
            f"{P}Addl/_Archive/aero.example/Back/",   # нет Data -> нарушение
            f"{P}Addl/_Archive/analytics.example.net/Back/",
            f"{P}Addl/_Archive/analytics.example.net/Data/",
            f"{P}Addl/_Archive/andromeda.example/Back/",
            f"{P}Addl/_Archive/andromeda.example/Data/",
            f"{P}Self/",                       # категория без проектов -> нет якорей
            f"{P}Work/Contoso/",                # организация без проектов -> нет якорей
            # нет ни Back, ни Data -> 2 нарушения
            f"{P}Work/Fabrikam/_Archive/acoustic.example/",
            f"{P}Work/Fabrikam/_Archive/partners.example/Back/",
            f"{P}Work/Fabrikam/_Archive/partners.example/Data/",
            f"{P}Work/Fabrikam/_Archive/studio.example/Back/",
            f"{P}Work/Fabrikam/_Archive/studio.example/Data/",
        ]
    )
    missing = _check(root, _CANONICAL_RULE)
    assert missing == [
        "Activities/3D/Resources",
        "Activities/Web/Projects/Addl/_Archive/aero.example/Data",
        "Activities/Web/Projects/Work/Fabrikam/_Archive/acoustic.example/Back",
        "Activities/Web/Projects/Work/Fabrikam/_Archive/acoustic.example/Data",
    ]


def test_anchors_and_rules_counters(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: anchors and rules counters."""
    root = make_tree(["Activities/3D/Projects/", "Activities/Web/Projects/"])
    (root / ".fs-check").write_text("/Activities/*/Projects\n/Activities\n", encoding="utf-8")
    result = FsChecker(load_fs_rule(root)).check(root)
    assert result.rules_checked == 2
    # Якори: два занятия (3D, Web) для первого правила + сам root для второго.
    assert result.anchors_found == 3
    assert not result.missing
