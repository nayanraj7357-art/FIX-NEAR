@echo off
title FixNear Server
echo ============================================
echo    FixNear - Starting Server...
echo ============================================
echo.
echo [1] Waiting for MySQL to be ready...
timeout /t 5 /nobreak > nul

echo [2] Starting Flask Server...
cd /d "d:\FIX NEAR"
python app.py

echo.
echo Server stopped. Press any key to exit.
pause
