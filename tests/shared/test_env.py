"""Доступ к единому `.env` (shared.env): путь, загрузка в окружение, приоритет, права.

`load_env` идемпотентна и мутирует `os.environ`, поэтому autouse-фикстура сбрасывает
флаг `_loaded` и восстанавливает окружение после каждого теста (переменные, добавленные
`load_dotenv`, monkeypatch сам не откатывает). Отсутствие `python-dotenv` имитируется
подменой `sys.modules["dotenv"]` на None — ленивый импорт тогда падает ImportError.
"""
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from fs_tools.shared import env


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(env, "_loaded", False)
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def test_env_path_uses_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FS_TOOLS_HOME", str(tmp_path))
    assert env.env_path() == tmp_path / ".env"


def test_env_path_falls_back_to_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("FS_TOOLS_HOME", raising=False)
    monkeypatch.chdir(tmp_path)
    assert env.env_path() == tmp_path / ".env"


def test_load_env_populates_environ(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FSCHK_TEST_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FS_TOOLS_HOME", str(tmp_path))
    monkeypatch.delenv("FSCHK_TEST_KEY", raising=False)
    env.load_env()
    assert os.environ.get("FSCHK_TEST_KEY") == "from-file"


def test_load_env_process_overrides_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # override=False: значение из окружения процесса важнее значения из .env.
    (tmp_path / ".env").write_text("FSCHK_TEST_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FS_TOOLS_HOME", str(tmp_path))
    monkeypatch.setenv("FSCHK_TEST_KEY", "from-process")
    env.load_env()
    assert os.environ.get("FSCHK_TEST_KEY") == "from-process"


def test_load_env_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Повторный вызов — no-op: ручную правку окружения load_env не перетирает.
    (tmp_path / ".env").write_text("FSCHK_TEST_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FS_TOOLS_HOME", str(tmp_path))
    monkeypatch.delenv("FSCHK_TEST_KEY", raising=False)
    env.load_env()
    os.environ["FSCHK_TEST_KEY"] = "manual"
    env.load_env()
    assert os.environ.get("FSCHK_TEST_KEY") == "manual"


def test_load_env_without_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FS_TOOLS_HOME", str(tmp_path))
    env.load_env()  # нет файла — тихий no-op без падения


def test_load_env_without_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FSCHK_TEST_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FS_TOOLS_HOME", str(tmp_path))
    monkeypatch.delenv("FSCHK_TEST_KEY", raising=False)
    monkeypatch.setitem(sys.modules, "dotenv", None)
    env.load_env()  # без python-dotenv .env игнорируется
    assert os.environ.get("FSCHK_TEST_KEY") is None


@pytest.mark.skipif(os.name != "posix", reason="права .env упрочняются только на POSIX")
def test_harden_permissions_sets_600(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text("FOO=bar\n", encoding="utf-8")
    path.chmod(0o644)
    env.harden_permissions(path)
    assert (path.stat().st_mode & 0o777) == 0o600
