@echo off
chcp 65001 >nul
REM Откат прогона нормализатора по examples/: возвращает дерево к состоянию из git
REM (восстанавливает отслеживаемые файлы и удаляет пустые каталоги-сироты).
setlocal
cd /d "%~dp0.."

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 goto notgit

git restore --staged --worktree -- examples 2>nul
if errorlevel 1 (
    REM Откат для старого git ^(^< 2.23^), где нет команды restore.
    git reset -q -- examples
    git checkout -- examples
)

REM Удаляем неотслеживаемое, включая опустевшие нормализованные каталоги
REM (git не хранит пустые каталоги, поэтому одного checkout недостаточно).
REM Сами reset-скрипты исключаем, чтобы они не удаляли себя до первого коммита.
git clean -fd examples -e reset.sh -e reset.command -e reset.bat

echo examples/ возвращён к состоянию из git.
goto end

:notgit
echo Это не git-репозиторий — откат через git недоступен.

:end
pause
