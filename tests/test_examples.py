"""Регрессия песочницы: --dry-run на examples/ совпадает с зафиксированным итогом.

Прогон детерминирован (локальные каталоги-приёмники, без сети) и не имеет побочных
эффектов (dry-run ничего не передаёт, не удаляет и не пишет журнал).
"""
from pathlib import Path

import pytest

from syncher.cli import main
from tests.conftest import requires_rsync

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@requires_rsync
def test_examples_dry_run_matches_readme(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(EXAMPLES), "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Профиль «site» (sync): передано 3, удалено 2, выгружено 0, ошибок 0" in out
    assert "Профиль «vault» (backup): передано 3, удалено 0, выгружено 0, ошибок 0" in out
    # dry-run не оставляет следов
    assert not (EXAMPLES / ".fs-log").exists()
