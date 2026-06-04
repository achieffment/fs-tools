@echo off
REM Тонкая обёртка для Windows: вся логика в normalize_fs.py.
python "%~dp0normalize_fs.py" %*
