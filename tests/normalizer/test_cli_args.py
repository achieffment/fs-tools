"""Тесты общего объявления CLI-флагов normalizer."""
import argparse

from fs_tools.normalizer.cli_args import (
    add_normalizer_argument,
    normalizer_argv_from_namespace,
)


def test_normalizer_argv_with_dry_run() -> None:
    """Проверяет сценарий: normalizer argv with dry run."""
    pars = argparse.ArgumentParser()
    pars.add_argument("path", nargs="?")
    add_normalizer_argument(pars)
    args = pars.parse_args(["/tmp/demo", "--dry-run"])
    assert normalizer_argv_from_namespace(args) == ["/tmp/demo", "--dry-run"]


def test_normalizer_argv_without_flags() -> None:
    """Проверяет сценарий: normalizer argv without flags."""
    pars = argparse.ArgumentParser()
    pars.add_argument("path", nargs="?")
    add_normalizer_argument(pars)
    args = pars.parse_args([])
    assert not normalizer_argv_from_namespace(args)
