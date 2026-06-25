"""Общие механики журнала .fs-log (shared.log): дата, инструмент, режим, append.

Мод-специфичные строки и текст пустого блока проверяются в мод-тестах
(normalizer: пары `old -> new` и «(изменений нет)»; checker: пути и «(нарушений нет)»).
"""
from datetime import datetime
from pathlib import Path

from fs_tools.shared.log import FS_LOG, append_log


def test_append_log_creates_file_with_timestamp_and_indent(tmp_path: Path) -> None:
    """Проверяет сценарий: append log creates file with timestamp and indent."""
    when = datetime(2026, 6, 14, 9, 0, 0)
    lpath = append_log(tmp_path, ["первая", "вторая"], "(пусто)", when=when)
    assert lpath == tmp_path / FS_LOG
    text = lpath.read_text(encoding="utf-8")
    assert "2026-06-14 09:00:00" in text
    assert "Инструмент: unknown" in text
    assert "Режим: production" in text
    assert "Результат:" in text
    assert "  первая" in text       # строки тела пишутся с отступом
    assert "  вторая" in text


def test_append_log_empty_uses_marker(tmp_path: Path) -> None:
    """Проверяет сценарий: append log empty uses marker."""
    when = datetime(2026, 6, 14, 9, 5, 0)
    lpath = append_log(tmp_path, [], "(пусто)", when=when)
    text = lpath.read_text(encoding="utf-8")
    assert "2026-06-14 09:05:00" in text
    assert "Инструмент: unknown" in text
    assert "Режим: production" in text
    assert "Результат:" in text
    assert "  (пусто)" in text


def test_append_log_uses_explicit_tool_and_mode(tmp_path: Path) -> None:
    """Проверяет сценарий: append log uses explicit tool and mode."""
    lpath = append_log(
        tmp_path,
        [],
        "(пусто)",
        meta=("normalizer", "dry-run"),
        when=datetime(2026, 6, 14, 9, 10, 0),
    )
    text = lpath.read_text(encoding="utf-8")
    assert "Инструмент: normalizer" in text
    assert "Режим: dry-run" in text


def test_append_log_appends_blocks(tmp_path: Path) -> None:
    """Проверяет сценарий: append log appends blocks."""
    append_log(tmp_path, ["a"], "(пусто)", when=datetime(2026, 6, 14, 9, 0, 0))
    lpath = append_log(tmp_path, ["b"], "(пусто)", when=datetime(2026, 6, 14, 10, 0, 0))
    text = lpath.read_text(encoding="utf-8")
    # Оба блока сохранены (дополнение, а не перезапись):
    assert "2026-06-14 09:00:00" in text
    assert "2026-06-14 10:00:00" in text
    assert "  a" in text
    assert "  b" in text
    # Блоки разделены пустой строкой.
    assert "\n\n" in text


def test_append_log_utf8(tmp_path: Path) -> None:
    """Проверяет сценарий: append log utf8."""
    lpath = append_log(tmp_path, ["Отчёт «ёлочки» → café"], "(пусто)")
    # Файл читается как utf-8 без ошибок и сохраняет не-ASCII.
    assert "Отчёт «ёлочки» → café" in lpath.read_text(encoding="utf-8")
