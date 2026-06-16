@echo off
chcp 65001 >nul
REM Обёртка для Windows: готовит .venv при первом запуске и вызывает fs-nrm.
REM Аргументы пробрасываются как есть (%*).
setlocal
set "here=%~dp0"
for %%I in ("%here%..") do set "root=%%~fI"

call "%here%_bootstrap.bat" "%root%"
if errorlevel 1 goto end

"%FS_TOOLS_VBIN%\fs-nrm.exe" %*

:end
pause
