@echo off
set BASEDIR=%~dp0
cd /d %BASEDIR%

echo ========================================
echo   AI Exam System - Start Script
echo ========================================
echo.

echo [1/3] Starting Backend...
start "AI-Exam Backend" cmd /k "cd /d %BASEDIR%backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/3] Starting AI Service...
start "AI-Exam AI-Service" cmd /k "cd /d %BASEDIR%ai-service && python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

echo [3/3] Starting Frontend...
start "AI-Exam Frontend" cmd /k "cd /d %BASEDIR%frontend && npm run dev"

echo.
echo Waiting 5 seconds for services to start...
timeout /t 5 /nobreak >nul

echo.
echo Opening browser pages...
start "" "http://localhost:3000/candidate"
start "" "http://localhost:3000/login"

echo.
echo ========================================
echo   All services started.
echo   Candidate: http://localhost:3000/candidate
echo   HR      : http://localhost:3000/login
echo   To stop: run stop-system.bat
echo ========================================
echo.

pause
