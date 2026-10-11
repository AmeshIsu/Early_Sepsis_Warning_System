@echo off
echo ========================================================
echo   Starting SepsisWatch: ICU Early Warning System
echo ========================================================
echo.

REM 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM 2. Install backend dependencies if needed
echo [1/3] Checking backend requirements...
python -m pip install -r backend\requirements.txt --quiet

REM 3. Launch Backend in background
echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000...
start "SepsisWatch Backend" cmd /k "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

REM 4. Launch Frontend
echo [3/3] Starting Vite Frontend on http://localhost:5173...
cd frontend
start "SepsisWatch Frontend" cmd /k "npm.cmd run dev -- --host"

echo.
echo ========================================================
echo   SepsisWatch System Launched!
echo   Frontend: http://localhost:5173
echo   Backend API: http://127.0.0.1:8000/docs
echo ========================================================
echo.
