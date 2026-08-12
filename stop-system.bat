@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   AI Exam System - Stop Script
echo ========================================
echo.

echo This will stop:
echo   - Backend (port 8000)
echo   - AI Service (port 8001)
echo   - Frontend (port 3000)
echo.

set /p confirm=Confirm stop all services? (Y/N): 
if /i not "%confirm%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Stopping services...
echo.

REM Stop Backend
echo [1/3] Stopping Backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo   Found process on port 8000 (PID=%%a)
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Killed PID=%%a
    ) else (
        echo   Failed to kill PID=%%a
    )
)

REM Stop AI Service
echo [2/3] Stopping AI Service...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
    echo   Found process on port 8001 (PID=%%a)
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Killed PID=%%a
    ) else (
        echo   Failed to kill PID=%%a
    )
)

REM Stop Frontend
echo [3/3] Stopping Frontend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo   Found process on port 3000 (PID=%%a)
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Killed PID=%%a
    ) else (
        echo   Failed to kill PID=%%a
    )
)

REM Close any AI-Exam windows
echo.
echo Closing AI-Exam windows...
taskkill /FI "WINDOWTITLE eq AI-Exam*" /F >nul 2>&1

echo.
echo ========================================
echo   AI Exam System Stopped
echo ========================================
echo.
echo   To restart: run start-system.bat
echo.
pause