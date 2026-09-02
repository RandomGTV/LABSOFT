@echo off
title LabSoft 2026 - Install Dependencies
cd /d "%~dp0"

echo =======================================================
echo   LabSoft - Automatic Dependency Installer
echo =======================================================
echo.
echo Installing PyQt6 and openpyxl...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed.
    echo Please make sure Python 3.10+ is installed and on your PATH.
    echo.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo   [SUCCESS] All dependencies installed successfully!
echo   Double-click START_LABSOFT_DESKTOP.bat to launch.
echo =======================================================
echo.
pause
