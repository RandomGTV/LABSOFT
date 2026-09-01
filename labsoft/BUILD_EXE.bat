@echo off
REM ===================================================================
REM  Builds a standalone LabSoft.exe that runs without Python installed.
REM  Only needed if you want to copy LabSoft to a PC that has no Python.
REM  Run this on Windows; the .exe appears in the dist folder.
REM ===================================================================
setlocal
cd /d "%~dp0"
title Building LabSoft.exe

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
    echo Python was not found. Run INSTALL.bat first.
    pause & exit /b 1
)

echo Installing the build tool...
%PY% -m pip install --upgrade pyinstaller --quiet
%PY% -m pip install -r requirements.txt --quiet

echo.
echo Building. This takes a few minutes...
%PY% -m PyInstaller ^
  --noconfirm --clean --windowed --onedir ^
  --name LabSoft ^
  --add-data "assets;assets" ^
  --hidden-import openpyxl ^
  main.py

if errorlevel 1 (
    echo.
    echo The build failed. The messages above say why.
    pause & exit /b 1
)

echo.
echo ===============================================
echo   Done. Your program is in:
echo     dist\LabSoft\LabSoft.exe
echo.
echo   Copy the whole dist\LabSoft folder to the
echo   other computer. Nothing else is needed there.
echo ===============================================
pause
