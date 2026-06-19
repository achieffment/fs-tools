@echo off
chcp 65001 >nul
REM Обёртка для Windows: готовит .venv при первом запуске и вызывает fs-syncher.
REM rsync под Windows нет нативно — запускайте через WSL или cwrsync.
REM Аргументы пробрасываются как есть (%*).
setlocal
set "here=%~dp0"
for %%I in ("%here%..") do set "root=%%~fI"

REM Fallback для cwrsync/chocolatey: выставляем cygwin-совместимые HOME/RSYNC_RSH.
if not defined HOME (
    set "home_win=%USERPROFILE%"
    set "home_cyg=%home_win:\=/%"
    if /I "%home_cyg:~1,1%"==":" set "home_cyg=/cygdrive/%home_cyg:~0,1%%home_cyg:~2%"
    set "HOME=%home_cyg%"
)
if not defined RSYNC_RSH (
    if exist "C:\ProgramData\chocolatey\lib\rsync\tools\bin\ssh.exe" (
        set "RSYNC_RSH=/cygdrive/c/ProgramData/chocolatey/lib/rsync/tools/bin/ssh.exe"
    )
)

call "%here%_bootstrap.bat" "%root%"
if errorlevel 1 goto end

"%FS_TOOLS_VBIN%\fs-syncher.exe" %*

:end
pause
