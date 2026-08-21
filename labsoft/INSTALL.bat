@echo off
REM ===================================================================
REM  LabSoft - one-time setup
REM
REM  Records the EXACT python.exe it installs into, so the launcher
REM  cannot later start a different Python that has nothing installed.
REM  That mismatch is what makes the window flash and vanish.
REM ===================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title LabSoft Setup

echo.
echo   ==========================================
echo     LabSoft - setting up
echo   ==========================================
echo.

REM ---- 1. Find Python and resolve it to a real path ------------------
set "PYEXE="
for %%L in ("py -3" "python" "python3") do (
    if not defined PYEXE (
        for /f "delims=" %%i in ('%%~L -c "import sys;print(sys.executable)" 2^>nul') do (
            set "PYEXE=%%i"
        )
    )
)

if not defined PYEXE (
    echo   Python is not installed on this computer.
    echo.
    echo   LabSoft needs Python 3.10 or newer.
    echo.
    echo   1. Go to        https://www.python.org/downloads/
    echo   2. Download and run the installer
    echo   3. IMPORTANT: tick "Add python.exe to PATH" on the FIRST screen
    echo   4. Then run this INSTALL file again
    echo.
    pause
    exit /b 1
)

echo   Using Python at:
echo     !PYEXE!
"!PYEXE!" --version
echo.

REM ---- 2. Check the version is new enough ----------------------------
"!PYEXE!" -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)"
if errorlevel 1 (
    echo   This Python is too old for LabSoft. Version 3.10 or newer is
    echo   needed. Please install a newer one from python.org and run
    echo   this INSTALL file again.
    echo.
    pause
    exit /b 1
)

REM ---- 3. Install into THAT interpreter, not whatever is on PATH -----
echo   Installing the parts LabSoft needs. The first time this can take
echo   a few minutes. Please leave this window open.
echo.
"!PYEXE!" -m pip install --upgrade pip --quiet
"!PYEXE!" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo   Something went wrong while installing.
    echo   Check this computer is connected to the internet, then run
    echo   this INSTALL file again.
    echo.
    pause
    exit /b 1
)

REM ---- 4. Prove it actually works before claiming success ------------
echo.
echo   Checking...
"!PYEXE!" -c "import PyQt6, openpyxl; print('   All parts present.')"
if errorlevel 1 (
    echo.
    echo   The parts installed but cannot be loaded. Please send this
    echo   whole window to whoever set LabSoft up.
    echo.
    pause
    exit /b 1
)

REM ---- 5. Remember which Python this was -----------------------------
echo !PYEXE!> python_path.txt
if exist "logs\startup_error.txt" del /q "logs\startup_error.txt" >nul 2>nul

REM ---- 6. Desktop shortcut -------------------------------------------
echo   Creating a Desktop shortcut...
set "TARGET=%~dp0RUN LabSoft.bat"
set "ICON=%~dp0assets\labsoft.ico"
powershell -NoProfile -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\LabSoft.lnk');" ^
  "$s.TargetPath='%TARGET%';" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "if (Test-Path '%ICON%') { $s.IconLocation='%ICON%' };" ^
  "$s.Description='LabSoft - laboratory reporting';" ^
  "$s.Save()" 2>nul

echo.
echo   ==========================================
echo     Setup finished.
echo.
echo     Start LabSoft from the "LabSoft" icon on
echo     your Desktop.
echo.
echo     If it ever refuses to start, run
echo     DIAGNOSE.bat in this folder - it shows
echo     exactly what is wrong.
echo   ==========================================
echo.
pause
