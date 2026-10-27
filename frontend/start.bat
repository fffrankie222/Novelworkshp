@echo off
chcp 65001 >nul 2>nul
title NovelWorkshop Frontend

cd /d "%~dp0"

echo ========================================
echo   NovelWorkshop Frontend (React + Vite)
echo ========================================
echo.

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node.js 18+ first.
    pause
    exit /b 1
)

node --version
echo.
echo Installing deps...
call npm install
echo.
echo Starting dev server at http://localhost:5173
echo.

call npm run dev

pause
