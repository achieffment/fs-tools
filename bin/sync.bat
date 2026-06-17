@echo off
chcp 65001 >nul
REM Обёртка для Windows: готовит .venv при первом запуске и вызывает fs-syncher.
REM rsync под Windows нет нативно — запускайте через WSL или cwrsync.
REM Аргументы пробрасываются как есть (%*).
setlocal
set "here=%~dp0"
for %%I in ("%here%..") do set "root=%%~fI"

call "%here%_bootstrap.bat" "%root%"
if errorlevel 1 goto end

"%FS_TOOLS_VBIN%\fs-syncher.exe" %*

:end
pause
