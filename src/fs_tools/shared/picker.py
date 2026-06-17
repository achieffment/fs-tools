"""Выбор каталога: нативный диалог Windows/WSL, диалог macOS, ввод в терминале.

Заголовок диалога и текст приглашения параметризуются (`pick_directory(title,
prompt)`) — режимы передают свои строки, общий код выбора платформы один.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.resources import as_file, files

_DEFAULT_TITLE = "Выберите каталог"
_DEFAULT_PROMPT = "Укажите каталог."

# Имена переменных окружения для передачи параметров в pick_folder.ps1 и osascript:
# нейтральны к режиму, поэтому общий код выбора каталога не зависит от вызывающего.
_ENV_INITIAL = "FSTOOLS_INITIAL"
_ENV_TITLE = "FSTOOLS_TITLE"


def _pick_folder_ps1() -> str | None:
    """Читает текст pick_folder.ps1 как ресурс пакета (надёжно и в установленном wheel).

    Ресурс ищется через importlib.resources, а не вычислением пути от `__file__`.
    None — если ресурс недоступен (тогда picker откатывается на ввод в терминале).
    """
    try:
        resource = files("fs_tools.shared").joinpath("pick_folder.ps1")
        with as_file(resource) as path:
            return path.read_text(encoding="utf-8")
    except (OSError, ModuleNotFoundError):
        return None


def _prompt_directory(reason: str, default: str = "") -> str:
    """Ввод пути в терминале (обычный Linux или когда диалог недоступен). Пустой ввод -> default."""
    sys.stderr.write(f"{reason}\n")
    if default:
        sys.stderr.write(f"Введите путь к каталогу [{default}]: ")
    else:
        sys.stderr.write("Введите путь к каталогу: ")
    sys.stderr.flush()
    try:
        value = input().strip()
    except EOFError:
        return ""
    return value or default


def _is_win() -> bool:
    return os.name == "nt"


def _is_mac() -> bool:
    return sys.platform == "darwin"


def _is_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return bool(os.environ.get("WSL_DISTRO_NAME"))


def _run(cmd: list[str], env: dict[str, str] | None = None) -> "subprocess.CompletedProcess[str] | None":
    """subprocess.run с общими параметрами (текстовый UTF-8, без исключений по коду).

    Возвращает результат либо None, если процесс не удалось запустить (OSError/
    SubprocessError) — общий откат для всех платформенных вызовов.
    """
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", env=env, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _set_initial(env: dict[str, str], initial: str | None) -> None:
    """Кладёт стартовую папку в переменную окружения или убирает устаревшее значение."""
    if initial:
        env[_ENV_INITIAL] = initial
    else:
        env.pop(_ENV_INITIAL, None)  # не подхватывать устаревшее значение


def _win_folder_dialog(initial: str | None = None, title: str = _DEFAULT_TITLE) -> str | None:
    """Нативный диалог выбора папки Windows (pick_folder.ps1, IFileOpenDialog).

    Стартовая папка и заголовок передаются через env, чтобы не экранировать их в
    команде. Имена переменных добавляются в WSLENV — иначе из-под WSL они не доходят
    до powershell.exe.

    Возвращает выбранный Windows-путь, "" при отмене (скрипт завершается с кодом 0
    и пустым выводом) или None, если powershell.exe/скрипт недоступен либо вызов
    завершился с ненулевым кодом (откат на ввод в терминале).
    """
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return None
    script = _pick_folder_ps1()
    if script is None:
        return None
    env = os.environ.copy()
    env[_ENV_TITLE] = title
    _set_initial(env, initial)
    # В WSL пользовательские переменные окружения не попадают в Windows-процессы
    # (powershell.exe), пока они не перечислены в WSLENV. Без флага значение
    # передаётся как есть — UNC-путь уже в Windows-формате, переводить его не нужно.
    adds = [_ENV_TITLE] + ([_ENV_INITIAL] if initial else [])
    ours = {_ENV_TITLE, _ENV_INITIAL}
    kept = [e for e in env.get("WSLENV", "").split(":") if e and e.split("/", 1)[0] not in ours]
    env["WSLENV"] = ":".join(kept + adds)
    dialog = _run([powershell, "-NoProfile", "-STA", "-Command", script], env=env)
    if dialog is None or dialog.returncode != 0:
        return None  # ошибка скрипта (отмена даёт код 0); откат на терминал
    return dialog.stdout.strip()  # "" при отмене


def _mac_folder_dialog(initial: str | None = None, title: str = _DEFAULT_TITLE) -> str | None:
    """Нативный диалог выбора папки macOS через osascript.

    initial — POSIX-путь предвыбранной папки (передаётся через env, чтобы не
    экранировать путь в строке скрипта). Возвращает POSIX-путь, "" при отмене или
    None, если osascript недоступен/ошибка.
    """
    osascript = shutil.which("osascript")
    if not osascript:
        return None
    script = (
        f'set p to (system attribute "{_ENV_INITIAL}")\n'
        'if p is not "" then\n'
        f'  POSIX path of (choose folder with prompt "{title}" default location (POSIX file p))\n'
        "else\n"
        f'  POSIX path of (choose folder with prompt "{title}")\n'
        "end if"
    )
    env = os.environ.copy()
    _set_initial(env, initial)
    dialog = _run([osascript, "-e", script], env=env)
    if dialog is None:
        return None
    if dialog.returncode != 0:
        return ""  # отмена (-128) или ошибка диалога
    return dialog.stdout.strip()


def _wslpath(flag: str, path: str) -> str | None:
    """Конвертация пути через wslpath (flag: '-w' WSL->Windows, '-u' обратно).

    None при недоступности wslpath, ошибке вызова или пустом выводе.
    """
    wslpath = shutil.which("wslpath")
    if not wslpath:
        return None
    convert = _run([wslpath, flag, path])
    if convert is None:
        return None
    return convert.stdout.strip() or None


def _to_win_path(unix_path: str) -> str | None:
    """Переводит путь WSL в Windows-путь через wslpath. None при ошибке/пустом выводе."""
    return _wslpath("-w", unix_path)


def _to_wsl_path(win_path: str) -> str | None:
    """Переводит Windows-путь в путь WSL через wslpath. None при ошибке."""
    return _wslpath("-u", win_path)


def pick_directory(title: str = _DEFAULT_TITLE, prompt: str = _DEFAULT_PROMPT) -> str:
    """Windows/WSL — нативный проводник Windows (IFileOpenDialog); macOS — osascript;
    обычный Linux — ввод в терминале. Папка по умолчанию везде — рабочий каталог
    (os.getcwd()): для alias/консоли это каталог вызова, для ярлыка/двойного клика
    на .bat — его «Рабочая папка» (обычно каталог проекта). В WSL путь дополнительно
    переводится в Windows-формат (wslpath) для диалога, а выбранный путь — обратно
    в путь WSL.
    """
    cwd = os.getcwd()
    if _is_win():
        path = _win_folder_dialog(cwd, title)
        if path is None:
            return _prompt_directory("Проводник Windows недоступен.", default=cwd)
        return path  # путь или "" (отмена)
    if _is_mac():
        path = _mac_folder_dialog(cwd, title)
        if path is None:
            return _prompt_directory("Стандартный диалог macOS недоступен.", default=cwd)
        return path  # путь или "" (отмена)
    if _is_wsl():
        # Каталог вызова (WSL-путь) -> Windows-путь (UNC) для InitialDirectory диалога.
        # Если конвертация не удалась (None), диалог откроется без стартовой папки.
        win_init = _to_win_path(cwd)
        win_path = _win_folder_dialog(win_init, title)
        if win_path is None:
            return _prompt_directory("Проводник Windows недоступен.", default=cwd)
        if not win_path:
            return ""  # пользователь отменил выбор
        conv = _to_wsl_path(win_path)
        if conv is None:
            return _prompt_directory("Не удалось преобразовать путь Windows.", default=cwd)
        return conv
    # Обычный Linux: ввод пути в терминале с дефолтом = каталог вызова.
    return _prompt_directory(prompt, default=cwd)
