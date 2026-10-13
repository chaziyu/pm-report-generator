@echo off
title PM Report Generator Launcher
color 0b

echo ========================================================
echo         FortiGate PM Report Generator - Localhost
echo ========================================================
echo.

set ROOT_DIR=%~dp0
cd /d "%ROOT_DIR%"

:: 1. Check Backend Environment
echo [*] Checking Backend Python environment...
if not exist "%ROOT_DIR%backend\venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Setting up backend venv...
    cd /d "%ROOT_DIR%backend"
    python -m venv venv
    echo [*] Installing backend dependencies...
    .\venv\Scripts\pip install -r requirements.txt
    cd /d "%ROOT_DIR%"
)

:: 2. Check Frontend Environment
echo [*] Checking Frontend Node environment...
if not exist "%ROOT_DIR%frontend\node_modules" (
    echo [!] node_modules not found. Running npm install...
    cd /d "%ROOT_DIR%frontend"
    call npm.cmd install
    cd /d "%ROOT_DIR%"
)

echo.
echo [*] Starting Backend API server on http://localhost:8000 ...
start "PM Report Generator - Backend (Port 8000)" cmd /k "cd /d "%ROOT_DIR%backend" && title Backend (8000) && .\venv\Scripts\python.exe run.py"

:: Brief pause to ensure backend is starting
timeout /t 2 /nobreak >nul

echo [*] Starting Frontend UI on http://localhost:5173 ...
start "PM Report Generator - Frontend (Port 5173)" cmd /k "cd /d "%ROOT_DIR%frontend" && title Frontend (5173) && npm.cmd run dev"

:: Wait for Vite to spin up, then open browser
timeout /t 3 /nobreak >nul
echo [*] Launching Web UI in your default browser...
start http://localhost:5173

echo.
echo ========================================================
echo  All services started successfully!
echo   - Web UI:   http://localhost:5173
echo   - Backend:  http://localhost:8000
echo   - Swagger:  http://localhost:8000/docs
echo ========================================================
echo.
echo Leave this window open, or press any key to exit this launcher.
echo (The backend and frontend terminal windows will keep running.)
pause >nul
