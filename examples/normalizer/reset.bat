@echo off
chcp 65001 >nul
REM Откат прогона нормализатора к состоянию из git: восстанавливает отслеживаемые
REM файлы и удаляет неотслеживаемые объекты. Выполняется без запроса.
REM
REM Безопасность (см. также раздел в README):
REM  - работает ТОЛЬКО внутри каталога самого скрипта, не трогает файлы вне него.
setlocal
cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 goto notgit

REM Откат с core.ignorecase=false и в порядке reset -> clean -> checkout. На
REM регистронезависимой ФС (Windows, macOS) переименования, отличающиеся ТОЛЬКО
REM регистром (CaseRule: archive -> Archive и т.п.), git обычными командами не
REM возвращает: путь считается тем же, имя не переименовывается. С ignorecase=false
REM мис-кейсовый объект становится неотслеживаемым, удаляется на шаге 2 и
REM пересоздаётся на шаге 3 уже с правильным регистром.

REM 1. Снимаем индекс к HEAD (если переименования были staged) — мис-кейс станет untracked.
git -c core.ignorecase=false reset -q -- .

REM 2. Удаляем неотслеживаемые объекты (мис-кейс, опустевшие нормализованные каталоги и пр.).
git -c core.ignorecase=false clean -fd -- .

REM 2a. Журнал .fs-log игнорируется git (он в .gitignore), поэтому clean -fd его
REM     не трогает — удаляем явно (только в этом каталоге).
del /q .fs-log >nul 2>nul

REM 3. Возвращаем отслеживаемые файлы к версии из git (только в этом каталоге).
git -c core.ignorecase=false checkout -- .

echo Готово: examples/normalizer/ возвращён к состоянию из git.
goto end

:notgit
echo Это не git-репозиторий — откат через git недоступен.

:end
pause
