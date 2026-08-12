@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   AI Exam System - Firewall Setup
echo   (Run as Administrator)
echo ========================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges.
    echo Please right-click and select "Run as administrator".
    pause
    exit /b 1
)

echo Adding firewall rules for AI Exam System...
echo.

for %%p in (3000 8000 8001) do (
    echo   Port %%p - Adding rule...
    netsh advfirewall firewall add rule name="AI-Exam System Port %%p" dir=in action=allow protocol=TCP localport=%%p profile=any >nul 2>&1
    if !errorlevel! equ 0 (
        echo     [OK] Port %%p opened
    ) else (
        echo     [FAIL] Failed to add rule for port %%p
    )
)

echo.
echo Verifying rules...
echo.

for %%p in (3000 8000 8001) do (
    netsh advfirewall firewall show rule name="AI-Exam System Port %%p" dir=in >nul 2>&1
    if !errorlevel! equ 0 (
        echo   [ACTIVE] Port %%p rule is active
    ) else (
        echo   [MISSING] Port %%p rule not found
    )
)

echo.
echo ========================================
echo   Firewall setup complete!
echo ========================================
echo.
echo   Now run start-system.bat to start all services.
echo.
pause