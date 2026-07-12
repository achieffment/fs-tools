"""Тесты разворачивания правил и сбора нарушений (engine)."""
import os
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from fs_tools.checker import FsChecker, load_fs_rule


def _check(root: Path, rule_text: str) -> list[str]:
    """Записывает .fs-chk в корень, прогоняет проверку, возвращает отсутствующие пути."""
    (root / ".fs-chk").write_text(rule_text, encoding="utf-8")
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


def test_double_star_hidden_branch_ignored(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: double star hidden branch ignored."""
    root = make_tree(
        [
            "P/.hidden/_Archive/proj/",
            "P/Visible/_Archive/proj2/",
        ]
    )
    missing = _check(root, "/P/**/_Archive/*/Back\n")
    assert missing == ["P/Visible/_Archive/proj2/Back"]


@pytest.mark.skipif(os.name != "posix", reason="права каталога проверяются только на POSIX")
def test_double_star_scan_failure_reported_as_errlist(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """OSError при scandir в **-обходе -> errlist, а не тихое «нет якорей»."""
    root = make_tree(["P/Blocked/_Archive/proj/Back/"])
    blocked = root / "P" / "Blocked"
    blocked.chmod(0o000)
    try:
        (root / ".fs-chk").write_text("/P/**/_Archive/*/Back\n", encoding="utf-8")
        result = FsChecker(load_fs_rule(root)).check(root)
    finally:
        blocked.chmod(0o755)  # иначе tmp_path не сможет удалить дерево при уборке
    assert not result.missing  # обход не долез до Back — но это не «якорь не найден»
    assert len(result.errlist) == 1
    assert result.errlist[0].startswith("P/Blocked:")


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
# Узкий момент _Archive: short pathspec-паттерн и его влияние на проверки
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
    # `_Archive` исключён pathspec-паттерном на любой глубине, архивный проект не проверяется.
    assert "Activities/Web/Projects/Addl/_Archive/Back" not in missing
    assert not missing


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


def test_path_negation_pruned_specific_anchor(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: path negation pruned specific anchor."""
    root = make_tree(["Workspace/Code/", "Workspace/Database/"])
    rule_text = (
        "/Workspace/*/Projects\n"
        "!/Workspace/Code/Projects\n"
    )
    missing = _check(root, rule_text)
    assert missing == ["Workspace/Database/Projects"]


def test_negation_short_and_path_together(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: negation short and path together."""
    root = make_tree(
        [
            "Activities/Web/Projects/Addl/_Archive/aero.example/",
            "Activities/Web/Projects/Addl/Code/",
            "Activities/Web/Projects/Addl/Real/",
        ]
    )
    rule_text = (
        "/Activities/Web/Projects/Addl/*/Back\n"
        "!_Archive\n"
        "!/Activities/Web/Projects/Addl/Code\n"
    )
    missing = _check(root, rule_text)
    assert missing == ["Activities/Web/Projects/Addl/Real/Back"]


def test_path_negation_order_last_match_wins_e2e(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: path negation order last match wins e2e."""
    root = make_tree(["Code/PHP/", "Code/Python/"])
    rule_text = (
        "/Code/*/Projects\n"
        "!/Code/**\n"
        "!!/Code/PHP/**\n"
    )
    missing = _check(root, rule_text)
    assert not missing


def test_path_negation_double_bang_equals_single_bang_e2e(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: path negation double bang equals single bang e2e."""
    root = make_tree(["Code/PHP/", "Code/Python/"])
    rule_text1 = (
        "/Code/*/Projects\n"
        "!/Code/PHP/**\n"
    )
    rule_text2 = (
        "/Code/*/Projects\n"
        "!!/Code/PHP/**\n"
    )
    missing1 = _check(root, rule_text1)
    missing2 = _check(root, rule_text2)
    assert missing1 == ["Code/Python/Projects"]
    assert missing2 == ["Code/Python/Projects"]


def test_path_negation_mask_excludes_branch(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    """Проверяет сценарий: path negation mask excludes branch."""
    root = make_tree(
        [
            "Code/PHP/Projects/",
            "Code/PHP/Legacy/",
            "Code/Python/",
        ]
    )
    rule_text = (
        "/Code/*/Projects\n"
        "!/Code/PHP/**\n"
    )
    missing = _check(root, rule_text)
    assert missing == ["Code/Python/Projects"]


# Канонический .fs-chk (источник истины для оракула ниже).
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


def test_canonical_oracle_archive_excluded(
    make_tree: Callable[[Iterable[str]], Path],
) -> None:
    # В canonical-правиле `_Archive` исключён short pathspec-паттерном `!_Archive`,
    # поэтому архивные нарушения не репортятся.
    """Проверяет сценарий: canonical oracle with archive excluded."""
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
    assert missing == ["Activities/3D/Resources"]


def test_anchors_and_rules_counters(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: anchors and rules counters."""
    root = make_tree(["Activities/3D/Projects/", "Activities/Web/Projects/"])
    (root / ".fs-chk").write_text("/Activities/*/Projects\n/Activities\n", encoding="utf-8")
    result = FsChecker(load_fs_rule(root)).check(root)
    assert result.rules_checked == 2
    # Якори: два занятия (3D, Web) для первого правила + сам root для второго.
    assert result.anchors_found == 3
    assert not result.missing


def test_grouped_rules_preserve_anchor_counter(make_tree: Callable[[Iterable[str]], Path]) -> None:
    """Проверяет сценарий: grouped rules preserve anchor counter."""
    root = make_tree(
        [
            "Activities/3D/Projects/",
            "Activities/3D/Resources/",
            "Activities/Web/Projects/",
        ]
    )
    (root / ".fs-chk").write_text(
        "/Activities/*/Projects\n/Activities/*/Resources\n",
        encoding="utf-8",
    )
    result = FsChecker(load_fs_rule(root)).check(root)
    # Для каждого из 2 правил найдено по 2 якоря (3D и Web) => 4.
    assert result.anchors_found == 4
    assert result.missing == ["Activities/Web/Resources"]
