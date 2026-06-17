@echo off
REM Общий bootstrap для обёрток Windows: готовит .venv в корне проекта и делает
REM editable-установку со всеми тремя extra. Вызывается обёртками через `call`; задаёт
REM переменные FS_TOOLS_HOME (корень проекта) и FS_TOOLS_VBIN (каталог Scripts
REM виртуального окружения). При сбое подготовки выходит с ненулевым кодом.
set "FS_TOOLS_HOME=%~1"
set "FS_TOOLS_VBIN=%FS_TOOLS_HOME%\.venv\Scripts"
set "pyex=%FS_TOOLS_VBIN%\python.exe"

if not exist "%pyex%" goto setup
"%pyex%" -c "import fs_tools, pathspec, unidecode, requests, dotenv" 1>nul 2>nul
if errorlevel 1 goto setup
exit /b 0

:setup
echo Подготовка окружения (.venv)...
if exist "%FS_TOOLS_HOME%\.venv" rmdir /s /q "%FS_TOOLS_HOME%\.venv"
python -m venv "%FS_TOOLS_HOME%\.venv"
if errorlevel 1 goto venvfail
"%pyex%" -m pip install -e "%FS_TOOLS_HOME%[normalizer,checker,syncher]"
if errorlevel 1 goto pipfail
exit /b 0

:venvfail
echo Не удалось создать .venv (возможно, временный сбой сети). Повторите запуск.
if exist "%FS_TOOLS_HOME%\.venv" rmdir /s /q "%FS_TOOLS_HOME%\.venv"
exit /b 1

:pipfail
echo Не удалось установить зависимости (возможно, временный сбой сети). Повторите запуск.
if exist "%FS_TOOLS_HOME%\.venv" rmdir /s /q "%FS_TOOLS_HOME%\.venv"
exit /b 1
