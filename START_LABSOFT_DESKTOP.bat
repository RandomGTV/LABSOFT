@echo off
title LabSoft Desktop Workstation
cd /d "%~dp0"

echo Starting LabSoft Desktop Application...
python main.py
if errorlevel 1 (
    echo.
    echo LabSoft encountered an issue starting up.
    echo Please make sure Python and PyQt6 are installed.
    pause
)
