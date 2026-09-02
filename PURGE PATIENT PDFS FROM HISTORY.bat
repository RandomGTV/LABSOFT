@echo off
setlocal enabledelayedexpansion
title LabSoft - remove patient reports from the git history
cd /d "%~dp0"

echo.
echo   Remove patient reports from the git history
echo   ==========================================================
echo.
echo   Three real patient reports were committed to this repository
echo   early on:
echo.
echo       47824  SUHARA MANNINGAL .pdf
echo       FARAS M  HBA1C.pdf
echo       RASHUDHEEN C K SEMEN ANALYSIS.pdf
echo.
echo   They are no longer tracked, so new pushes do not carry them.
echo   But every commit made before that still contains them, and
echo   anyone who cloned the repository already has a copy.
echo.
echo   This rewrites every commit to take them out.
echo.
echo   READ THIS FIRST
echo   ---------------
echo   * Every commit gets a new identity. Anyone else working from
echo     this repository must re-clone -- their old clone cannot be
echo     merged back without putting the files right back in.
echo   * It force-pushes. The old history on GitHub is replaced.
echo   * GitHub may keep unreferenced copies for a while. If those
echo     reports matter, ask GitHub Support to purge the cache, and
echo     treat the files as having been public.
echo   * A backup of the whole folder is made first.
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo   Git is not on this PC's PATH. Install it and run this again.
  echo.
  pause
  exit /b 1
)

set "PY="
if exist "python_path.txt" set /p PY=<python_path.txt
if not defined PY set "PY=py -3"
if not exist "python_path.txt" (
  where python >nul 2>nul && set "PY=python"
)

set /p "GO=  Type REWRITE to go ahead: "
if /i not "!GO!"=="REWRITE" (
  echo.
  echo   Nothing was changed.
  echo.
  pause
  exit /b 0
)

echo.
echo   Making a backup copy of the folder first...
for /f "tokens=2 delims==" %%t in ('wmic os get localdatetime /value') do set "T=%%t"
set "STAMP=!T:~0,8!-!T:~8,4!"
robocopy "%CD%" "%CD%\..\lab soft backup !STAMP!" /E /NFL /NDL /NJH /NJS /NP >nul
echo   Saved beside this folder as "lab soft backup !STAMP!"
echo.

echo   Installing git-filter-repo (the tool GitHub recommends)...
"%PY%" -m pip install --quiet git-filter-repo
if errorlevel 1 (
  echo.
  echo   Could not install git-filter-repo. It needs internet access once.
  echo.
  pause
  exit /b 1
)

echo   Rewriting...
"%PY%" -m git_filter_repo --force --invert-paths ^
  --path "labsoft-design-system/project/uploads"
if errorlevel 1 goto failed

rem filter-repo drops the remote on purpose, so it cannot force-push by
rem accident. Put it back, then push deliberately.
git remote add origin https://github.com/RandomGTV/LABSOFT.git 2>nul
echo.
echo   Force-pushing the rewritten history...
git push origin --force --all
if errorlevel 1 goto failed
git push origin --force --tags 2>nul

echo.
echo   ==========================================================
echo   Done. Those reports are no longer in any commit.
echo.
echo   Tell anyone else working from this repository to delete their
echo   clone and clone it again.
echo.
pause
exit /b 0

:failed
echo.
echo   ----------------------------------------------------------
echo   That did not finish. The message above says why.
echo   Your backup copy is beside this folder, untouched.
echo.
pause
exit /b 1
