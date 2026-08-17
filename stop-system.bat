@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   AI Exam System - Stop Script
echo ========================================
echo.

echo This will stop all AI Exam System services:
echo   - Backend       (port 8000)
echo   - AI Service    (port 8001)
echo   - Frontend      (port 3000)
echo.

set /p confirm=Confirm stop all services? (Y/N): 
if /i not "%confirm%"=="Y" (
    echo Cancelled. No services were stopped.
    pause
    exit /b 0
)

echo.
echo ========================================
echo   Stopping all services...
echo ========================================
echo.

set "TOTAL_STOPPED=0"

REM ========== Step 1: Stop Services by Port ==========

echo [8000] Checking port 8000...
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo   - Found PID=%%a on port 8000
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo     [OK] Terminated PID=%%a
        set /a TOTAL_STOPPED+=1
    ) else (
        echo     [WARN] Failed to terminate PID=%%a
    )
)
if "!FOUND!"=="0" echo   - Port 8000 is already free.
echo.

echo [8001] Checking port 8001...
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 " ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo   - Found PID=%%a on port 8001
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo     [OK] Terminated PID=%%a
        set /a TOTAL_STOPPED+=1
    ) else (
        echo     [WARN] Failed to terminate PID=%%a
    )
)
if "!FOUND!"=="0" echo   - Port 8001 is already free.
echo.

echo [3000] Checking port 3000...
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    set "FOUND=1"
    echo   - Found PID=%%a on port 3000
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        echo     [OK] Terminated PID=%%a
        set /a TOTAL_STOPPED+=1
    ) else (
        echo     [WARN] Failed to terminate PID=%%a
    )
)
if "!FOUND!"=="0" echo   - Port 3000 is already free.
echo.

REM ========== Step 2: Close AI-Exam Windows ==========
echo Closing AI-Exam service windows...
taskkill /FI "WINDOWTITLE eq AI-Exam*" /F >nul 2>&1
timeout /t 1 /nobreak >nul
echo   [OK] AI-Exam windows closed.
echo.

REM ========== Step 3: Wait and Verify ==========
echo Waiting for processes to fully terminate...
timeout /t 3 /nobreak >nul

echo Verifying all ports are now free...
set "ALL_CLEAR=1"

netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [WARN] Port 8000 is still in use!
    set "ALL_CLEAR=0"
) else (
    echo   [OK] Port 8000 is free.
)

netstat -ano | findstr ":8001 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [WARN] Port 8001 is still in use!
    set "ALL_CLEAR=0"
) else (
    echo   [OK] Port 8001 is free.
)

netstat -ano | findstr ":3000 " | findstr "LISTENING" >nul 2>&1
if !errorlevel! equ 0 (
    echo   [WARN] Port 3000 is still in use!
    set "ALL_CLEAR=0"
) else (
    echo   [OK] Port 3000 is free.
)

REM ========== Done ==========
echo.
echo ========================================
if "!ALL_CLEAR!"=="1" (
    echo   All services stopped successfully.
) else (
    echo   [WARNING] Some services may still be running.
    echo             Try running this script again or close windows manually.
)
echo ========================================
echo.
echo   Stopped processes: !TOTAL_STOPPED!
echo.
echo   To restart: run start-system.bat
echo.
pause
endlocal