@echo off
title LabSoft 2026 Web Application
echo ===================================================
echo   LabSoft 2026 - Medical Pathology Workstation
echo   Author: RANDOM_GTV
echo ===================================================
echo Opening LabSoft in your browser...
start http://localhost:8000
start index.html
python -m http.server 8000
