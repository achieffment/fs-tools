"""Регрессия песочницы: --dry-run на examples/syncher совпадает с зафиксированным итогом.

Прогон детерминирован (локальные каталоги-приёмники, без сети) и не имеет побочных
эффектов (dry-run ничего не передаёт, не удаляет и не пишет журнал).
"""
import shutil
from pathlib import Path

import pytest

from fs_tools.syncher.runner import main

# Пропуск интеграционных тестов, если в системе нет rsync.
requires_rsync = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync не установлен")

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "syncher"


@requires_rsync
def test_examples_dry_run_matches_readme(capsys: pytest.CaptureFixture[str]) -> None:
    """Проверяет сценарий: examples dry run matches readme."""
    code = main([str(EXAMPLES), "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Профиль «site» (sync): передано 3, удалено 2, выгружено 0, ошибок 0" in out
    assert "Профиль «vault» (backup): передано 3, удалено 0, выгружено 0, ошибок 0" in out
    # dry-run не оставляет следов
    assert not (EXAMPLES / ".fs-log").exists()
