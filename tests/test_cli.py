"""Тесты выбора каталога и предзаполнения папки по умолчанию (normalizer.cli)."""
import os
import subprocess

import pytest

from normalizer import cli


# --------------------------------------------------------------------------- #
# _prompt_directory
# --------------------------------------------------------------------------- #
def test_prompt_returns_default_on_empty_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda: "")
    assert cli._prompt_directory("причина", default="/tmp/foo") == "/tmp/foo"


def test_prompt_returns_typed_value_over_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda: "  /tmp/bar  ")
    assert cli._prompt_directory("причина", default="/tmp/foo") == "/tmp/bar"


def test_prompt_empty_without_default(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda: "")
    assert cli._prompt_directory("причина") == ""


def test_prompt_returns_empty_on_eof(monkeypatch):
    def _raise():
        raise EOFError

    monkeypatch.setattr("builtins.input", _raise)
    assert cli._prompt_directory("причина", default="/tmp/foo") == ""


# --------------------------------------------------------------------------- #
# _pick_directory (ветка обычного Linux)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def _force_plain_linux(monkeypatch):
    monkeypatch.setattr(cli, "_is_win", lambda: False)
    monkeypatch.setattr(cli, "_is_mac", lambda: False)
    monkeypatch.setattr(cli, "_is_wsl", lambda: False)


def test_pick_directory_linux_defaults_to_cwd(monkeypatch, tmp_path, _force_plain_linux):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda: "")
    assert cli._pick_directory() == os.getcwd()


def test_pick_directory_linux_uses_typed_path(monkeypatch, tmp_path, _force_plain_linux):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", lambda: str(tmp_path / "sub"))
    assert cli._pick_directory() == str(tmp_path / "sub")


# --------------------------------------------------------------------------- #
# _pick_directory (ветка Windows)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def _force_windows(monkeypatch):
    monkeypatch.setattr(cli, "_is_win", lambda: True)
    monkeypatch.setattr(cli, "_is_mac", lambda: False)


def test_pick_directory_windows_uses_cwd_as_initial(monkeypatch, tmp_path, _force_windows):
    monkeypatch.chdir(tmp_path)
    captured: dict[str, str | None] = {}

    def fake_dialog(initial: str | None = None) -> str:
        captured["initial"] = initial
        return "SELECTED"

    monkeypatch.setattr(cli, "_win_folder_dialog", fake_dialog)
    result = cli._pick_directory()
    assert result == "SELECTED"
    assert captured["initial"] == os.getcwd()


# --------------------------------------------------------------------------- #
# _pick_directory (ветка WSL: round-trip конвертации путей)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def _force_wsl(monkeypatch):
    monkeypatch.setattr(cli, "_is_win", lambda: False)
    monkeypatch.setattr(cli, "_is_mac", lambda: False)
    monkeypatch.setattr(cli, "_is_wsl", lambda: True)


def test_pick_directory_wsl_converts_cwd_and_roundtrips(monkeypatch, _force_wsl):
    # Сценарий «всё в WSL»: cwd -> Windows-путь (UNC) для InitialDirectory,
    # результат выбора -> обратно в путь WSL.
    converted_args: list[str] = []

    def fake_to_win(p: str) -> str:
        converted_args.append(p)
        return r"\\wsl.localhost\D\sel"

    monkeypatch.setattr(cli, "_to_win_path", fake_to_win)
    captured: dict[str, str | None] = {}

    def fake_dialog(initial: str | None = None) -> str:
        captured["initial"] = initial
        return r"\\wsl.localhost\D\chosen"

    monkeypatch.setattr(cli, "_win_folder_dialog", fake_dialog)
    monkeypatch.setattr(cli, "_to_wsl_path", lambda p: "/home/user/chosen")

    result = cli._pick_directory()
    assert converted_args == [os.getcwd()]  # стартовая папка диалога = каталог вызова
    assert captured["initial"] == r"\\wsl.localhost\D\sel"
    assert result == "/home/user/chosen"


def test_pick_directory_wsl_no_initial_when_conversion_fails(monkeypatch, _force_wsl):
    # Если cwd не конвертируется, диалог открывается без стартовой папки (initial=None).
    monkeypatch.setattr(cli, "_to_win_path", lambda p: None)
    captured: dict[str, str | None] = {}

    def fake_dialog(initial: str | None = None) -> str:
        captured["initial"] = initial
        return r"\\wsl.localhost\D\chosen"

    monkeypatch.setattr(cli, "_win_folder_dialog", fake_dialog)
    monkeypatch.setattr(cli, "_to_wsl_path", lambda p: "/home/user/chosen")

    result = cli._pick_directory()
    assert captured["initial"] is None
    assert result == "/home/user/chosen"


def test_pick_directory_wsl_selects_windows_folder(monkeypatch, _force_wsl):
    # Из-под WSL выбрали Windows-папку: диалог вернул C:\..., путь должен пройти
    # через _to_wsl_path (wslpath -u: C:\Users\me -> /mnt/c/Users/me).
    monkeypatch.setattr(cli, "_to_win_path", lambda p: r"\\wsl.localhost\D\proj")
    monkeypatch.setattr(cli, "_win_folder_dialog", lambda initial=None: r"C:\Users\me")
    seen: dict[str, str] = {}

    def fake_to_wsl(p: str) -> str:
        seen["arg"] = p
        return "/mnt/c/Users/me"

    monkeypatch.setattr(cli, "_to_wsl_path", fake_to_wsl)
    result = cli._pick_directory()
    assert seen["arg"] == r"C:\Users\me"  # именно выбранный Windows-путь
    assert result == "/mnt/c/Users/me"


def test_pick_directory_windows_selects_wsl_folder(monkeypatch, _force_windows):
    # Из-под нативной Windows выбрали папку WSL: UNC-путь возвращается как есть,
    # без конвертации (её делает только ветка WSL).
    unc = r"\\wsl.localhost\Ubuntu-24.04_dev\home\achieffment\proj"
    monkeypatch.setattr(cli, "_win_folder_dialog", lambda initial=None: unc)
    monkeypatch.setattr(
        cli, "_to_wsl_path", lambda p: pytest.fail("конвертация не нужна на Windows")
    )
    assert cli._pick_directory() == unc


# --------------------------------------------------------------------------- #
# _pick_directory (ветка macOS)
# --------------------------------------------------------------------------- #
@pytest.fixture()
def _force_mac(monkeypatch):
    monkeypatch.setattr(cli, "_is_win", lambda: False)
    monkeypatch.setattr(cli, "_is_mac", lambda: True)


def test_pick_directory_mac_uses_cwd_as_initial(monkeypatch, tmp_path, _force_mac):
    monkeypatch.chdir(tmp_path)
    captured: dict[str, str | None] = {}

    def fake_dialog(initial: str | None = None) -> str:
        captured["initial"] = initial
        return "/Users/me/sel"

    monkeypatch.setattr(cli, "_mac_folder_dialog", fake_dialog)
    assert cli._pick_directory() == "/Users/me/sel"
    assert captured["initial"] == os.getcwd()


def test_pick_directory_mac_falls_back_to_prompt(monkeypatch, tmp_path, _force_mac):
    # osascript недоступен (None) -> ввод пути в терминале с дефолтом = cwd.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_mac_folder_dialog", lambda initial=None: None)
    monkeypatch.setattr("builtins.input", lambda: "")
    assert cli._pick_directory() == os.getcwd()


# --------------------------------------------------------------------------- #
# _win_folder_dialog (не-GUI части: передача FSNORM_INITIAL через env, вывод)
# --------------------------------------------------------------------------- #
def test_win_folder_dialog_passes_initial_and_title_via_env(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/fake/powershell.exe")
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["env"] = kwargs["env"]
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="C:\\chosen\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = cli._win_folder_dialog(r"C:\Users\me\proj")
    assert result == "C:\\chosen"
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["FSNORM_INITIAL"] == r"C:\Users\me\proj"
    assert env["FSNORM_TITLE"]  # заголовок передаётся в скрипт
    # WSLENV нужен, чтобы переменные дошли до powershell.exe из-под WSL.
    wslenv = env["WSLENV"].split(":")
    assert "FSNORM_INITIAL" in wslenv
    assert "FSNORM_TITLE" in wslenv
    # В команду уходит содержимое pick_folder.ps1 с C#-блоком IFileOpenDialog.
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "IFileOpenDialog" in cmd[-1]


def test_win_folder_dialog_none_when_script_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/fake/powershell.exe")
    monkeypatch.setattr(cli, "_PICK_FOLDER_PS1", tmp_path / "missing.ps1")

    def fail_run(cmd, **kwargs):  # не должен вызываться
        raise AssertionError("subprocess.run не должен запускаться без скрипта")

    monkeypatch.setattr(cli.subprocess, "run", fail_run)
    assert cli._win_folder_dialog(r"C:\Users\me\proj") is None


def test_win_folder_dialog_without_initial_clears_env(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/fake/powershell.exe")
    monkeypatch.setenv("FSNORM_INITIAL", "stale")
    captured: dict[str, dict[str, str]] = {}

    def fake_run(cmd, **kwargs):
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = cli._win_folder_dialog(None)
    assert result == ""  # отмена / пустой вывод
    assert "FSNORM_INITIAL" not in captured["env"]
    # Без стартовой папки в WSLENV остаётся только заголовок.
    wslenv = captured["env"]["WSLENV"].split(":")
    assert "FSNORM_INITIAL" not in wslenv
    assert "FSNORM_TITLE" in wslenv


def test_win_folder_dialog_none_when_no_powershell(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli._win_folder_dialog(r"C:\Users\me\proj") is None


def test_win_folder_dialog_none_on_nonzero_returncode(monkeypatch):
    # Отмена даёт код 0; ненулевой код — ошибка скрипта -> None (откат на терминал),
    # даже если в stdout что-то осталось.
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/fake/powershell.exe")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 3, stdout="C:\\junk\n", stderr="boom")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._win_folder_dialog(r"C:\Users\me\proj") is None


def test_win_folder_dialog_preserves_existing_wslenv(monkeypatch):
    # Уже объявленные в WSLENV переменные не должны теряться при добавлении FSNORM_*.
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/fake/powershell.exe")
    monkeypatch.setenv("WSLENV", "PATH/l:GOPATH/p")
    captured: dict[str, dict[str, str]] = {}

    def fake_run(cmd, **kwargs):
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(cmd, 0, stdout="C:\\x\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    cli._win_folder_dialog(r"C:\Users\me\proj")
    wslenv = captured["env"]["WSLENV"].split(":")
    assert "PATH/l" in wslenv
    assert "GOPATH/p" in wslenv
    assert "FSNORM_INITIAL" in wslenv
    assert "FSNORM_TITLE" in wslenv


# --------------------------------------------------------------------------- #
# _mac_folder_dialog (osascript)
# --------------------------------------------------------------------------- #
def test_mac_folder_dialog_returns_path_and_passes_initial(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/osascript")
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["env"] = kwargs["env"]
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="/Users/me/sel\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = cli._mac_folder_dialog("/Users/me/proj")
    assert result == "/Users/me/sel"
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["FSNORM_INITIAL"] == "/Users/me/proj"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[1] == "-e"  # скрипт передаётся инлайном через -e


def test_mac_folder_dialog_cancel_returns_empty(monkeypatch):
    # osascript при отмене (-128) завершается с ненулевым кодом -> "" (отмена).
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/osascript")

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="User canceled.")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._mac_folder_dialog("/Users/me/proj") == ""


def test_mac_folder_dialog_none_when_no_osascript(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli._mac_folder_dialog("/Users/me/proj") is None


# --------------------------------------------------------------------------- #
# wslpath-конверсии (_to_win_path / _to_wsl_path)
# --------------------------------------------------------------------------- #
def test_to_win_path_converts(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/wslpath")
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="\\\\wsl.localhost\\D\\p\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._to_win_path("/home/u/p") == r"\\wsl.localhost\D\p"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[1] == "-w"  # туда: WSL -> Windows


def test_to_win_path_none_on_empty_output(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/wslpath")
    monkeypatch.setattr(
        cli.subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="err"),
    )
    assert cli._to_win_path("/bad") is None


def test_to_win_path_none_when_no_wslpath(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli._to_win_path("/home/u/p") is None


def test_to_wsl_path_converts(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/wslpath")
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="/mnt/c/Users/me\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli._to_wsl_path(r"C:\Users\me") == "/mnt/c/Users/me"
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[1] == "-u"  # обратно: Windows -> WSL


def test_to_wsl_path_none_when_no_wslpath(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert cli._to_wsl_path(r"C:\Users\me") is None
