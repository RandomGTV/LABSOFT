@echo off
setlocal
title LabSoft - clear all data
cd /d "%~dp0"

rem Use the interpreter INSTALL.bat recorded, so this runs against the same
rem Python the program itself uses rather than whichever one is first on PATH.
set "PY="
if exist "python_path.txt" set /p PY=<python_path.txt
if not defined PY set "PY=py -3"
if not exist "python_path.txt" (
  where python >nul 2>nul && set "PY=python"
)

"%PY%" reset_data.py
if errorlevel 1 goto done

:done
echo.
pause
endlocal
