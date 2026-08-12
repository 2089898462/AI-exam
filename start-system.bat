@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   AI Exam System - Start Script
echo ========================================
echo.

REM Get script directory
set "BASEDIR=%~dp0"
cd /d "%BASEDIR%"

REM Check directories
if not exist "backend\main.py" (
    echo [ERROR] backend directory not found
    echo Please ensure the script is in the project root directory
    pause
    exit /b 1
)

if not exist "ai-service\main.py" (
    echo [ERROR] ai-service directory not found
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] frontend directory not found
    pause
    exit /b 1
)

REM Clear existing ports
echo [1/4] Checking ports...
for %%p in (8000 8001 3000) do (
    netstat -ano | findstr ":%%p" | findstr "LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p" ^| findstr "LISTENING"') do (
            echo   Terminating process on port %%p (PID=%%a)
            taskkill /PID %%a /F >nul 2>&1
        )
    )
)
echo   Ports cleared.
echo.

REM Start Backend
echo [2/4] Starting Backend (port: 8000)...
start "AI-Exam Backend" cmd /k "cd /d %BASEDIR%backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
echo   Backend starting...
timeout /t 3 /nobreak >nul

REM Start AI Service
echo [3/4] Starting AI Service (port: 8001)...
start "AI-Exam AI-Service" cmd /k "cd /d %BASEDIR%ai-service && python -m uvicorn main:app --host 0.0.0.0 --port 8001"
echo   AI Service starting...
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [4/4] Starting Frontend (port: 3000)...
start "AI-Exam Frontend" cmd /k "cd /d %BASEDIR%frontend && npm run dev"
echo   Frontend starting...
timeout /t 5 /nobreak >nul

REM Done
echo.
rem Get local IP for LAN access
set "LOCAL_IP="
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R "IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do (
        if not defined LOCAL_IP set "LOCAL_IP=%%b"
    )
)

echo ========================================
echo   AI Exam System Started
echo ========================================
echo.
echo   Local Access:
echo     Backend:     http://localhost:8000
echo     AI Service:  http://localhost:8001
echo     Frontend:    http://localhost:3000
echo.
echo   LAN Access (for other computers):
echo     Frontend:    http://%LOCAL_IP%:3000
echo     Admin:       http://%LOCAL_IP%:3000/login
echo     Candidate:   http://%LOCAL_IP%:3000/candidate
echo.
echo   Default: admin / admin123
echo.
echo   To stop: run stop-system.bat
echo ========================================
echo.

REM Try open browsers
timeout /t 2 /nobreak >nul
echo Opening candidate portal...
start http://localhost:3000/candidate

echo Opening admin portal...
start http://localhost:3000/login

echo.
echo Opening browsers...
echo.
pause