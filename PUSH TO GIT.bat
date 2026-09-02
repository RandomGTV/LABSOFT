@echo off
setlocal enabledelayedexpansion
title LabSoft - push the latest to GitHub
cd /d "%~dp0"

echo.
echo   LabSoft - push to GitHub
echo   ==========================================================
echo.

rem Git has to be on PATH. If it is not, say so plainly rather than
rem failing eight lines later with something the reader cannot act on.
where git >nul 2>nul
if errorlevel 1 (
  echo   Git is not installed, or not on this PC's PATH.
  echo.
  echo   Install it from https://git-scm.com/download/win and run this again.
  echo.
  pause
  exit /b 1
)

if not exist ".git" (
  echo   This folder is not a git repository.
  echo   Expected a .git folder in:  %CD%
  echo.
  pause
  exit /b 1
)

for /f "delims=" %%r in ('git config --get remote.origin.url') do set "REMOTE=%%r"
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%b"
echo   Repository : !REMOTE!
echo   Branch     : !BRANCH!
echo.

echo   These files have changed since the last push:
echo.
git status --short
echo.

rem ---------------------------------------------------------------------------
rem Patient reports
rem ---------------------------------------------------------------------------
rem Three real patient reports are tracked in this repository, under
rem labsoft-design-system\project\uploads\. They were uploaded to the design
rem canvas as examples and got committed with everything else. They are named
rem reports for named people, and they go wherever this repository goes.
rem
rem Untracking them stops future pushes carrying them. It does NOT delete the
rem files from this PC, and it does NOT remove them from the commits already
rem pushed -- that needs the history rewritten, which is a separate job.
rem ---------------------------------------------------------------------------
git ls-files --error-unmatch "labsoft-design-system/project/uploads/47824  SUHARA MANNINGAL .pdf" >nul 2>nul
if not errorlevel 1 (
  echo   ------------------------------------------------------------------
  echo   NOTE: three real patient reports are tracked in this repository:
  echo.
  echo       47824  SUHARA MANNINGAL .pdf
  echo       FARAS M  HBA1C.pdf
  echo       RASHUDHEEN C K SEMEN ANALYSIS.pdf
  echo.
  echo   They are design-canvas samples. The web app does not need them.
  echo   Removing them from git leaves them untouched on this PC.
  echo   ------------------------------------------------------------------
  echo.
  set /p "DROP=  Stop sending these to GitHub?  (Y/N): "
  if /i "!DROP!"=="Y" (
    git rm -r --cached "labsoft-design-system/project/uploads" >nul
    findstr /c:"labsoft-design-system/project/uploads/" .gitignore >nul 2>nul
    if errorlevel 1 (
      echo.>> .gitignore
      echo # Patient reports uploaded to the design canvas. Kept on this PC,>> .gitignore
      echo # never sent to GitHub.>> .gitignore
      echo labsoft-design-system/project/uploads/>> .gitignore
    )
    echo   Done - they will not be pushed again.
    echo.
  )
)

set "MSG=Update web app and desktop app to the current build"
set /p "TYPED=  Commit message [%MSG%]: "
if not "!TYPED!"=="" set "MSG=!TYPED!"

echo.
echo   Staging...
git add -A
if errorlevel 1 goto failed

git diff --cached --quiet
if not errorlevel 1 (
  echo.
  echo   Nothing to commit - git already has everything in this folder.
  echo.
  goto pushanyway
)

echo   Committing...
git commit -m "!MSG!"
if errorlevel 1 goto failed

:pushanyway
echo   Pushing to !REMOTE! ...
echo.
git push origin !BRANCH!
if errorlevel 1 goto failed

echo.
echo   ==========================================================
echo   Pushed. GitHub now has what is in this folder.
echo.
echo   If the page the client opens still looks old, that is
echo   GitHub Pages serving its cached build, not this push -
echo   it usually catches up within a minute or two. A refresh
echo   with Ctrl+F5 skips the browser's own cache.
echo.
pause
exit /b 0

:failed
echo.
echo   ----------------------------------------------------------
echo   That did not finish. The message above says why.
echo.
echo   The usual cause is GitHub asking for a sign-in that never
echo   appeared. Run this once, then try again:
echo.
echo       git push origin !BRANCH!
echo.
echo   Nothing has been lost - your files are exactly as they were.
echo.
pause
exit /b 1
