@echo off
title LabSoft 2026 - web application
cd /d "%~dp0"

rem The page lives in web\ and nowhere else. It used to sit at the root
rem alongside five copies of itself, which is how the repository ended up
rem serving a build older than this PC's -- same file size, different file.
if not exist "web\index.html" (
  echo.
  echo   web\index.html is missing.
  echo   Run "PUSH TO GIT.bat" is not the fix -- fetch the folder again.
  echo.
  pause
  exit /b 1
)

echo.
echo   LabSoft 2026 - web application
echo   Serving web\ on http://localhost:8000
echo   Close this window to stop.
echo.
start "" http://localhost:8000
python -m http.server 8000 --directory web
