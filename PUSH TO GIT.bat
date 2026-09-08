@echo off
setlocal enabledelayedexpansion
title LabSoft - push the code to GitHub
cd /d "%~dp0"

echo.
echo   LabSoft  -  push the code to GitHub
echo   ==========================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo   Git is not on this PC's PATH, so nothing can be pushed.
  echo   Install Git for Windows from git-scm.com and try again.
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

rem ---------------------------------------------------------------
rem  Refuse to push a patient.
rem
rem  .gitignore keeps data\, patients\, reports\, exports\ and logs\
rem  out -- but .gitignore only governs files git is NOT already
rem  tracking. Anything committed before the ignore file existed
rem  stays tracked for ever, and goes on being pushed. This looks at
rem  the index AFTER staging, which is what actually decides.
rem ---------------------------------------------------------------
git add -A
if errorlevel 1 (
  echo   Staging failed. Nothing was committed or pushed.
  pause
  exit /b 1
)
set BAD=0
for /f "delims=" %%F in ('git ls-files 2^>nul') do (
  echo %%F| findstr /i /r "^data/ ^patients/ ^reports/ ^exports/ ^logs/ \.db$ \.pdf$" >nul && (
    if !BAD!==0 (
      echo   STOP. Git is tracking files that belong to patients:
      echo.
    )
    echo       %%F
    set /a BAD+=1
  )
)
if not !BAD!==0 (
  echo.
  echo   !BAD! file^(s^). Putting them in .gitignore is not enough --
  echo   they are already tracked. Untrack them first. This keeps the
  echo   files on this PC and only takes them out of git:
  echo.
  echo       git rm --cached -r data patients reports exports logs
  echo.
  echo   Then run this again. Nothing has been pushed.
  echo.
  pause
  exit /b 1
)
echo   Checked: git is tracking no patient data.
echo.

echo   Changed since the last commit
echo   -----------------------------
git status --short
echo.

git diff --cached --quiet
if not errorlevel 1 (
  echo   Nothing has changed.
  git log --oneline -1
  echo.
  echo   Pushing anyway, in case an earlier commit never reached GitHub.
  echo.
  git push origin HEAD
  echo.
  pause
  exit /b 0
)

echo   ==========================================================
set "MSG=Update LabSoft"
set /p "TYPED=  Describe the change [%MSG%]: "
if not "!TYPED!"=="" set "MSG=!TYPED!"

echo.
set /p "GO=  Type YES to commit and push, anything else to stop: "
if /i not "!GO!"=="YES" (
  git reset >nul 2>&1
  echo.
  echo   Stopped. Nothing was committed; your files are untouched.
  echo.
  pause
  exit /b 0
)

echo.
git commit -m "!MSG!"
if errorlevel 1 (
  echo.
  echo   The commit failed. Nothing was pushed.
  echo.
  pause
  exit /b 1
)

git push origin HEAD
if errorlevel 1 (
  echo.
  echo   The push failed. The commit is saved on this PC, so nothing is
  echo   lost -- run this again once the connection or the GitHub
  echo   sign-in is sorted out.
  echo.
  pause
  exit /b 1
)

echo.
echo   ==========================================================
echo   Pushed.
echo.
git log --oneline -1
echo.
pause
