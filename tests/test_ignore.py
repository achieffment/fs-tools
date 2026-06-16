"""Тесты ignore: трансляция exclude/include в фильтры rsync и авто-исключения."""
from syncher import ARTIFACTS, build_filters, filter_args
from syncher.ignore import auto_exclude_filters


def test_artifacts_constant() -> None:
    assert ARTIFACTS == (".fs-sync.toml", ".fs-log", ".env")


def test_auto_exclude_filters_content() -> None:
    rules = auto_exclude_filters()
    assert rules == ["- /.fs-sync.toml", "- /.fs-log", "- .env"]


def test_build_filters_order() -> None:
    rules = build_filters(exclude=["*.tmp"], include=["keep.tmp"])
    # сперва безусловные артефакты, затем include (+), затем exclude (-)
    assert rules[:3] == auto_exclude_filters()
    assert "+ keep.tmp" in rules
    assert "- *.tmp" in rules
    assert rules.index("+ keep.tmp") < rules.index("- *.tmp")


def test_build_filters_empty() -> None:
    # без пользовательских правил остаются только безусловные артефакты
    assert build_filters(exclude=[], include=[]) == auto_exclude_filters()


def test_artifacts_first_so_not_reincludable() -> None:
    # include артефакта не возвращает: правило-артефакт стоит раньше include
    rules = build_filters(exclude=[], include=[".env"])
    assert rules.index("- .env") < rules.index("+ .env")


def test_filter_args_format() -> None:
    args = filter_args(exclude=["*.tmp"], include=[])
    assert all(a.startswith("--filter=") for a in args)
    assert "--filter=- *.tmp" in args
    assert "--filter=- /.fs-sync.toml" in args
