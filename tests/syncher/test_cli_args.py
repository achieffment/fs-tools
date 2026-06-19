"""Тесты общего объявления и проброса CLI-флагов sync."""
from __future__ import annotations

import argparse

from fs_tools.syncher.cli_args import add_sync_flags, sync_argv_from_namespace


def _parser() -> argparse.ArgumentParser:
    """Вспомогательная функция для теста."""
    pars = argparse.ArgumentParser()
    pars.add_argument("path", nargs="?")
    add_sync_flags(pars)
    return pars


def test_sync_argv_full_flags() -> None:
    """Проверяет сценарий: sync argv full flags."""
    args = _parser().parse_args(
        [
            "/tmp/root",
            "--profile",
            "site",
            "--profile",
            "vault",
            "--all",
            "--dry-run",
            "--force-delete",
            "--verbose",
        ]
    )
    assert sync_argv_from_namespace(args) == [
        "/tmp/root",
        "--profile",
        "site",
        "--profile",
        "vault",
        "--all",
        "--dry-run",
        "--force-delete",
        "--verbose",
    ]


def test_sync_argv_without_path_and_flags() -> None:
    """Проверяет сценарий: sync argv without path and flags."""
    args = _parser().parse_args([])
    assert not sync_argv_from_namespace(args)
