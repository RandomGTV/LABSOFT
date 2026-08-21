@echo off
REM ===================================================================
REM  Runs LabSoft with the console VISIBLE and keeps this window open,
REM  so any error can be read instead of flashing past.
REM
REM  If LabSoft will not start, run this and send the whole window to
REM  whoever set it up.
REM ===================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title LabSoft - Diagnose

echo.
echo   ============================================================
echo     LabSoft diagnostic
echo   ============================================================
echo.
echo   Folder:
echo     %~dp0
echo.

REM ---- What Pythons exist on this machine? ---------------------------
echo   Pythons found:
set "FOUND=0"
for %%L in ("py -3" "python" "python3" "pythonw") do (
    for /f "delims=" %%i in ('%%~L -c "import sys;print(sys.executable)" 2^>nul') do (
        set "FOUND=1"
        set "HASQT=no"
        %%~L -c "import PyQt6" >nul 2>nul
        if not errorlevel 1 set "HASQT=YES"
        for /f "delims=" %%v in ('%%~L -c "import sys;print('%%d.%%d.%%d'%%sys.version_info[:3])" 2^>nul') do (
            echo     %%~L  ^-^>  %%i
            echo            version %%v   PyQt6 installed: !HASQT!
        )
    )
)
if "!FOUND!"=="0" (
    echo     NONE.
    echo.
    echo   Python is not installed, or was installed without ticking
    echo   "Add python.exe to PATH".
    echo.
    echo   Install it from https://www.python.org/downloads/ and tick
    echo   that box on the first screen, then run INSTALL.bat.
    echo.
    pause
    exit /b 1
)
echo.

REM ---- Which one has LabSoft been told to use? -----------------------
if exist "python_path.txt" (
    set /p SAVED=<python_path.txt
    echo   Recorded by INSTALL.bat:
    echo     !SAVED!
) else (
    echo   No python_path.txt yet - INSTALL.bat has not completed.
)
echo.

REM ---- Pick the one with PyQt6 --------------------------------------
set "PYEXE="
if exist "python_path.txt" (
    set /p SAVED=<python_path.txt
    if exist "!SAVED!" (
        "!SAVED!" -c "import PyQt6" >nul 2>nul
        if not errorlevel 1 set "PYEXE=!SAVED!"
    )
)
if not defined PYEXE (
    for %%L in ("py -3" "python" "python3") do (
        if not defined PYEXE (
            %%~L -c "import PyQt6" >nul 2>nul
            if not errorlevel 1 (
                for /f "delims=" %%i in ('%%~L -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
            )
        )
    )
)

if not defined PYEXE (
    echo   ------------------------------------------------------------
    echo     PROBLEM FOUND: no Python here has PyQt6 installed.
    echo   ------------------------------------------------------------
    echo.
    echo   Run INSTALL.bat in this folder. It installs into the right
    echo   one and remembers which it was.
    echo.
    pause
    exit /b 1
)

echo   Starting LabSoft with:
echo     !PYEXE!
echo.
echo   ------------------------------------------------------------
echo     Any error appears below. Close LabSoft to return here.
echo   ------------------------------------------------------------
echo.

"!PYEXE!" "%~dp0main.py"

echo.
echo   ------------------------------------------------------------
echo     LabSoft has closed. Exit code: %errorlevel%
echo   ------------------------------------------------------------
if exist "logs\startup_error.txt" (
    echo.
    echo   Startup error recorded:
    type "logs\startup_error.txt"
)
echo.
pause
