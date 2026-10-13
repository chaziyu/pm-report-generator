@echo off
title PM Report Generator Stopper
color 0c

echo ========================================================
echo         Stopping PM Report Generator Services
echo ========================================================
echo.

echo [*] Stopping processes on port 8000 (Backend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Stopping processes on port 5173 (Frontend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do (
    echo Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All PM Report Generator services stopped.
timeout /t 2 /nobreak >nul
