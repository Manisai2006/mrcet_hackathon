@echo off
title AI Regional-Language Personal Tutor (StudyBuddy AI)
cls

echo ================================================================
echo    AI REGIONAL-LANGUAGE PERSONAL TUTOR (StudyBuddy AI)
echo ================================================================
echo.
echo Starting FastAPI Backend Server on http://127.0.0.1:8000...
echo.

:: Change directory to backend
cd /d "%~dp0backend"

:: Launch default web browser with frontend/index.html after 2 seconds delay
start "" timeout /t 2 >nul & start "" "%~dp0frontend\index.html"

:: Run FastAPI Uvicorn Server
"C:\Users\mani sai reddy\AppData\Local\Python\bin\python.exe" -m uvicorn app.main:app --reload --port 8000

pause
