@echo off
chcp 65001 >nul 2>nul
title NovelWorkshop Backend

cd /d "%~dp0"

echo ========================================
echo   NovelWorkshop Backend Server
echo ========================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

python --version
echo.
echo Installing deps...
pip install -r requirements.txt
echo.
echo Starting server at http://localhost:8000
echo API docs: http://localhost:8000/docs
echo.

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
