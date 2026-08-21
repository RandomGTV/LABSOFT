@echo off
REM ===================================================================
REM  Starts LabSoft.
REM
REM  If anything is wrong, this window STAYS OPEN and says what it is,
REM  instead of closing instantly. Never launch with a bare "pythonw":
REM  it has no console, so a missing part fails silently and the window
REM  just disappears.
REM ===================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title LabSoft

if exist "logs\startup_error.txt" del /q "logs\startup_error.txt" >nul 2>nul

set "PYEXE="

REM ---- 1. The interpreter INSTALL.bat verified, if we recorded one ---
if exist "python_path.txt" (
    set /p SAVED=<python_path.txt
    if exist "!SAVED!" (
        "!SAVED!" -c "import PyQt6" >nul 2>nul
        if not errorlevel 1 set "PYEXE=!SAVED!"
    )
)

REM ---- 2. Otherwise find one that genuinely has PyQt6 ----------------
if not defined PYEXE (
    for %%L in ("py -3" "python" "python3") do (
        if not defined PYEXE (
            %%~L -c "import PyQt6" >nul 2>nul
            if not errorlevel 1 (
                for /f "delims=" %%i in ('%%~L -c "import sys;print(sys.executable)" 2^>nul') do (
                    set "PYEXE=%%i"
                )
            )
        )
    )
)

REM ---- 3. Nothing has PyQt6: is Python even here? --------------------
if not defined PYEXE (
    set "ANYPY="
    for %%L in ("py -3" "python" "python3") do (
        if not defined ANYPY (
            for /f "delims=" %%i in ('%%~L -c "import sys;print(sys.executable)" 2^>nul') do (
                set "ANYPY=%%i"
            )
        )
    )
    if not defined ANYPY goto :nopython
    set "PYEXE=!ANYPY!"
    goto :fixmissing
)

:launch
REM ---- 4. Launch windowed, using pythonw from the SAME install -------
set "PYW=%PYEXE:python.exe=pythonw.exe%"
if not exist "%PYW%" set "PYW=%PYEXE%"

echo %PYEXE%> python_path.txt
start "" "%PYW%" "%~dp0main.py"

REM Give it a moment. If it wrote a startup error, show that.
ping -n 4 127.0.0.1 >nul
if exist "logs\startup_error.txt" (
    echo.
    echo   ------------------------------------------------------------
    echo     LabSoft could not start. The reason:
    echo   ------------------------------------------------------------
    type "logs\startup_error.txt"
    echo   ------------------------------------------------------------
    echo.
    pause
)
exit /b 0


:fixmissing
echo.
echo   ============================================================
echo     A required part of LabSoft is missing.
echo   ============================================================
echo.
echo   Python is installed at:
echo     %PYEXE%
echo   but PyQt6 has not been installed for it.
echo.
echo   Installing it now. This needs the internet and takes a
echo   couple of minutes. Please leave this window open.
echo.
"%PYEXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   That did not work.
    echo   Check the internet connection and run INSTALL.bat again.
    echo.
    pause
    exit /b 1
)
echo.
echo   Fixed. Starting LabSoft...
goto :launch


:nopython
echo.
echo   ============================================================
echo     LabSoft cannot start: Python is not installed.
echo   ============================================================
echo.
echo   1. Go to    https://www.python.org/downloads/
echo   2. Download and run the installer
echo   3. On the FIRST screen, tick "Add python.exe to PATH"
echo   4. Finish the install, then run INSTALL.bat in this folder
echo.
pause
exit /b 1
