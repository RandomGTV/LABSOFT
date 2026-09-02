@echo off
setlocal enabledelayedexpansion
title LabSoft - retire the duplicate copies of the web page
cd /d "%~dp0"

echo.
echo   Retiring the duplicate copies of the web page
echo   ==========================================================
echo.
echo   The page now lives in one place: web\index.html
echo.
echo   These four are byte-identical copies of it. Keeping them is
echo   what let git serve an old build while this PC had a newer
echo   one -- the sizes matched, so nothing looked wrong.
echo.
echo       index.html
echo       LabSoft-demo.html
echo       LabSoft 2026.dc.html
echo       LabSoft 2026 - standalone.html
echo.
echo   The design canvas folder is not touched. Its own copies
echo   belong to that tool and are written by it.
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo   Git is not on this PC's PATH, so these can only be removed by hand.
  echo.
  pause
  exit /b 1
)

set /p "GO=  Remove the four duplicates?  (Y/N): "
if /i not "!GO!"=="Y" (
  echo.
  echo   Nothing was changed.
  echo.
  pause
  exit /b 0
)

echo.
for %%F in ("index.html" "LabSoft-demo.html" "LabSoft 2026.dc.html" "LabSoft 2026 - standalone.html") do (
  git ls-files --error-unmatch %%F >nul 2>nul
  if not errorlevel 1 (
    git rm -q %%F
    echo   removed  %%~F
  ) else (
    if exist %%F (
      del %%F
      echo   deleted  %%~F  ^(was not in git^)
    )
  )
)

echo.
echo   Done. web\index.html is now the only copy.
echo   Run "PUSH TO GIT.bat" to send this to GitHub and Vercel.
echo.
pause
