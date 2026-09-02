@echo off
setlocal
title LabSoft - default account check
cd /d "%~dp0"

rem Use the interpreter INSTALL.bat recorded, so this reads the same database
rem the program itself opens rather than whichever Python is first on PATH.
set "PY="
if exist "python_path.txt" set /p PY=<python_path.txt
if not defined PY set "PY=py -3"
if not exist "python_path.txt" (
  where python >nul 2>nul && set "PY=python"
)

echo.
echo   Close LabSoft before running this, so the database is not open twice.
echo.
pause

"%PY%" security_check.py
echo.
pause
endlocal
