@echo off
setlocal enabledelayedexpansion
title LabSoft - clean out what the program does not use
cd /d "%~dp0"

echo.
echo   LabSoft  -  clean out what the program does not use
echo   ==========================================================
echo.
echo   Nothing the program needs is touched. Not the code, not
echo   assets\, not data\lab.db, not the five newest backups, not
echo   patients\, not reports\, not web\.
echo.
echo   To be removed
echo   -------------
echo.
echo   1  labsoft-design-system\
echo      The Claude Design handoff bundle the screens were drawn
echo      from. The screens are built; the bundle is not read by
echo      anything. It also holds three REAL PATIENT REPORTS in
echo      project\uploads\ -- and the .gitignore did not cover
echo      that folder, so they were being pushed.
echo.
echo   2  LabSoft pathology design system-handoff.zip   (1.9 MB)
echo      LabSoft.zip
echo      The same bundle again, zipped, and an old snapshot.
echo.
echo   3  design-mockup-v1.html, report-template-v2.html,
echo      sample-report.pdf, LabSoft-design-brief.md,
echo      labsoft-design-spec.md
echo      Working drawings. The finished report renderer is
echo      app\output\report.py.
echo.
echo   4  Every __pycache__ folder
echo      Python rebuilds these on the next run.
echo.
echo   5  data\backups\  -  all but the five newest
echo      LabSoft takes a backup every time it starts, so most of
echo      these are copies of each other from the same minute.
echo.
echo   6  git gc, to repack the .git folder
echo      This does NOT remove the patient PDFs already in the
echo      history. PURGE PATIENT PDFS FROM HISTORY.bat does that,
echo      and it rewrites every commit, so it is left to you.
echo.
echo   ==========================================================
echo.
echo   Close LabSoft before running this, so the database is not
echo   open while the backups folder is being tidied.
echo.

set /p GO=  Type YES to go ahead, anything else to stop:
if /i not "%GO%"=="YES" (
  echo.
  echo   Nothing was removed.
  echo.
  pause
  exit /b 0
)

echo.
echo   Working...
echo.

rem ---------------------------------------------------------------
rem  1 and 2 -- the design bundle and its zips
rem ---------------------------------------------------------------
if exist "labsoft-design-system\" (
  rd /s /q "labsoft-design-system"
  echo   removed  labsoft-design-system\
)
for %%F in ("LabSoft pathology design system-handoff.zip" "LabSoft.zip") do (
  if exist "%%~F" ( del /q "%%~F" & echo   removed  %%~F )
)

rem ---------------------------------------------------------------
rem  3 -- the working drawings
rem ---------------------------------------------------------------
for %%F in (
  "design-mockup-v1.html"
  "report-template-v2.html"
  "sample-report.pdf"
  "LabSoft-design-brief.md"
  "labsoft-design-spec.md"
) do (
  if exist "%%~F" ( del /q "%%~F" & echo   removed  %%~F )
)

rem ---------------------------------------------------------------
rem  4 -- compiled Python
rem ---------------------------------------------------------------
rem  Collected first, then removed. Walking with /d /r while deleting the
rem  folders being walked is how a batch file skips half of them.
set PYC=0
for /f "delims=" %%D in ('dir /s /b /ad "__pycache__" 2^>nul') do (
  rd /s /q "%%D" 2>nul
  set /a PYC+=1
)
echo   removed  !PYC! __pycache__ folder^(s^)

rem ---------------------------------------------------------------
rem  5 -- old backups, keeping the five newest
rem
rem  Listed newest first, and the first five are skipped. The live
rem  database is data\lab.db and is never in this folder.
rem ---------------------------------------------------------------
if exist "data\backups\" (
  set N=0
  set OLD=0
  pushd "data\backups"
  for /f "delims=" %%B in ('dir /b /o-d /a-d "lab_*.db" 2^>nul') do (
    set /a N+=1
    if !N! GTR 5 ( del /q "%%B" & set /a OLD+=1 )
  )
  popd
  echo   removed  !OLD! old backup^(s^), kept the 5 newest
)

rem ---------------------------------------------------------------
rem  6 -- repack git
rem ---------------------------------------------------------------
where git >nul 2>nul
if errorlevel 1 (
  echo   skipped  git gc  ^(git is not on this PC's PATH^)
) else (
  if exist ".git\" (
    echo   repacking .git, this can take a minute...
    rem  Not --aggressive: on a repository this size it rewrites every
    rem  delta for several minutes and saves little over a plain repack.
    git gc --prune=now >nul 2>&1
    echo   done     git gc
  )
)

echo.
echo   ==========================================================
echo   Finished.
echo.
echo   Check that LabSoft still starts: RUN LabSoft.bat
echo   The first start will be a moment slower while Python
echo   rebuilds its __pycache__ folders.
echo.
pause
