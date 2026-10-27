@echo off
chcp 65001 >nul 2>nul
title NovelWorkshop Diagnostic
cd /d "%~dp0"

echo ============================================
echo   NovelWorkshop Diagnostic Tool
echo ============================================
echo.

echo [1/5] Checking Python...
python --version 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo.

echo [2/5] Checking pip dependencies...
cd backend
python -c "import openai; print('openai:', openai.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] openai not installed, installing...
    pip install openai
)
python -c "import fastapi; print('fastapi:', fastapi.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] fastapi not installed, installing...
    pip install fastapi
)
python -c "import uvicorn; print('uvicorn OK')" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] uvicorn not installed, installing...
    pip install uvicorn
)
python -c "import pydantic; print('pydantic:', pydantic.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] pydantic not installed, installing...
    pip install pydantic
)
python -c "import httpx; print('httpx:', httpx.__version__)" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] httpx not installed, installing...
    pip install httpx
)
echo.

echo [3/5] Testing backend import...
python -c "import sys; sys.path.insert(0, '.'); from app.api.router import api_router; print('Backend import OK')" 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Backend import failed!
    echo Please check the error message above.
    pause
    exit /b 1
)
echo.

echo [4/5] Checking port 8000...
netstat -ano | findstr :8000 | findstr LISTENING >nul 2>nul
if %errorlevel% equ 0 (
    echo [WARN] Port 8000 is already in use!
    echo Killing existing process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
        taskkill /PID %%a /F >nul 2>nul
    )
    timeout /t 2 /nobreak >nul
)
echo Port 8000 is available.
echo.

echo [5/5] Starting backend for test (10 seconds)...
start /b python -m uvicorn main:app --host 0.0.0.0 --port 8000
timeout /t 5 /nobreak >nul

echo Testing health check...
curl -s http://localhost:8000/health >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Backend is running correctly!
    curl -s http://localhost:8000/health
) else (
    echo [ERROR] Backend health check failed!
    echo The backend might have crashed. Check the window above for errors.
)

echo.
echo ============================================
echo   Diagnostic complete
echo ============================================
pause
