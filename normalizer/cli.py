"""CLI: разбор аргументов и сценарий запуска."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .filesystem import FilesystemNormalizer
from .name import build_normalizer


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Нормализатор имён файлов и папок (рекурсивно). Каталог выбирается в диалоге проводника при запуске.")
    return parser.parse_args(argv)


def _prompt_directory(reason: str) -> str:
    """Ввод пути в терминале (для обычного Linux или когда проводник недоступен)."""
    sys.stderr.write(f"{reason}\n")
    sys.stderr.write("Введите путь к каталогу: ")
    sys.stderr.flush()
    try:
        return input().strip()
    except EOFError:
        return ""


def _is_win() -> bool:
    return os.name == "nt"


def _is_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return bool(os.environ.get("WSL_DISTRO_NAME"))


def _win_folder_dialog() -> str | None:
    """Открывает нативный проводник Windows через PowerShell.
    Возвращает выбранный Windows-путь, "" при отмене пользователем или None,
    если PowerShell недоступен либо вызов завершился ошибкой.
    """
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return None
    # UTF-8 на стороне PowerShell — иначе путь с не-ASCII (кириллица) исказится.
    script = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
        "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }"
    )
    try:
        dialog = subprocess.run(
            [powershell, "-NoProfile", "-STA", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return dialog.stdout.strip()  # "" при отмене


def _to_wsl_path(win_path: str) -> str | None:
    """Переводит Windows-путь в путь WSL через wslpath. None при ошибке."""
    wslpath = shutil.which("wslpath")
    if not wslpath:
        return None
    try:
        converted = subprocess.run(
            [wslpath, "-u", win_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return converted.stdout.strip() or None


def _pick_directory() -> str:
    """Windows/WSL — нативный проводник Windows; обычный Linux — ввод в терминале."""
    if _is_win():
        win_path = _win_folder_dialog()
        if win_path is None:
            return _prompt_directory("Проводник Windows недоступен.")
        return win_path  # путь или "" (отмена)
    if _is_wsl():
        win_path = _win_folder_dialog()
        if win_path is None:
            return _prompt_directory("Проводник Windows недоступен.")
        if not win_path:
            return ""  # пользователь отменил выбор
        converted = _to_wsl_path(win_path)
        if converted is None:
            return _prompt_directory("Не удалось преобразовать путь Windows.")
        return converted
    return _prompt_directory("Графический выбор папки доступен только в Windows/WSL.")


def main(argv: list[str] | None = None) -> int:
    _parse_args(argv)
    target = _pick_directory()
    if not target:
        sys.stderr.write("Каталог не выбран.\n")
        return 1
    root = Path(target).expanduser()
    try:
        root = root.resolve(strict=True)
    except OSError:
        sys.stderr.write(f"Ошибка: каталог не найден: {target}\n")
        return 1
    if not root.is_dir():
        sys.stderr.write(f"Ошибка: каталог не является каталогом: {root}\n")
        return 1
    fsnm = FilesystemNormalizer(build_normalizer())
    print(f"Каталог: {root}")
    renamed, skipped = fsnm.apply(root)
    print(f"Готово. Переименовано: {renamed}, пропущено: {skipped}.")
    return 0
