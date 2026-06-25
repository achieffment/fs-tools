"""Тесты report: маркеры операций журнала и формат отчёта."""
from pathlib import Path

from fs_tools.syncher import ProfileReport, format_header, format_profile, format_report


def test_actions_markers() -> None:
    """Проверяет сценарий: actions markers."""
    report = ProfileReport(
        name="m",
        kind="sync",
        code=0,
        sent=["a.txt"],
        deleted=["old.txt"],
        offload=["x.bin"],
    )
    assert report.actions() == ["+ a.txt", "- old.txt", ">> x.bin"]


def test_format_header_modes(tmp_path: Path) -> None:
    """Проверяет сценарий: format header modes."""
    real = format_header(tmp_path, ["a", "b"], dry_run=False)
    assert "production" in real and "a, b" in real
    dry = format_header(tmp_path, [], dry_run=True)
    assert "dry-run" in dry and "—" in dry


def test_format_profile_counts() -> None:
    """Проверяет сценарий: format profile counts."""
    report = ProfileReport(name="m", kind="sync", code=0, sent=["a", "b"], deleted=["c"])
    text = format_profile(report)
    assert "передано 2" in text and "удалено 1" in text and "выгружено 0" in text


def test_format_profile_blocked() -> None:
    """Проверяет сценарий: format profile blocked."""
    report = ProfileReport(name="m", kind="sync", code=3, deleted=["a", "b"], blocked=True)
    text = format_profile(report)
    assert "защитой" in text and "--force-delete" in text


def test_format_report_lists_all(tmp_path: Path) -> None:
    """Проверяет сценарий: format report lists all."""
    result = [
        ProfileReport(name="a", kind="sync", code=0),
        ProfileReport(name="b", kind="backup", code=2, errlist=["boom"]),
    ]
    text = format_report(tmp_path, result)
    assert "Профиль «a»" in text and "Профиль «b»" in text
