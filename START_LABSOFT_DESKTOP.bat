@echo off
rem Kept because the shortcut on the desktop may still point here.
rem
rem It used to run "python main.py" directly. That starts LabSoft with
rem whichever Python happens to be first on PATH -- which on this PC is not
rem always the one that has PyQt6 -- and when that one fails the window shuts
rem before anything can be read. "RUN LabSoft.bat" checks the interpreter
rem first, and shows the reason when something is wrong instead of vanishing.
cd /d "%~dp0"
call "RUN LabSoft.bat" %*
