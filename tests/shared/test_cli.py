"""Тесты общего CLI-хелпера `shared.cli`."""
from __future__ import annotations

from fs_tools.shared.cli import make_parser


def test_make_parser_defaults() -> None:
    """Проверяет сценарий: make parser defaults."""
    pars = make_parser("desc")
    args = pars.parse_args([])
    assert args.path is None


def test_make_parser_custom_prog_and_path_help() -> None:
    """Проверяет сценарий: make parser custom prog and path help."""
    pars = make_parser(
        "desc",
        prog="fs-syncher",
        path_help="Каталог для синхронизации. Если не задан — выбирается интерактивно.",
    )
    assert pars.prog == "fs-syncher"
    help_text = " ".join(pars.format_help().split())
    assert "Каталог для синхронизации. Если не задан — выбирается интерактивно." in help_text
