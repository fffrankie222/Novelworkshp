@echo off
chcp 65001 >nul 2>nul
title NovelWorkshop Launcher

REM Switch to script directory
cd /d "%~dp0"
echo Current dir: %cd%
echo.

echo ============================================
echo   NovelWorkshop v3.7 Launcher (outline simplified + writing context)
echo ============================================
echo.

REM Check Python
echo [1/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
python --version
echo.

REM Check Node.js
echo [2/5] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found!
    echo Please install Node.js 18+ LTS from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
node --version
echo.

REM Check folder structure
if not exist "backend\main.py" (
    echo [ERROR] backend\main.py not found.
    echo Please make sure the NovelWorkshop folder structure is intact.
    pause
    exit /b 1
)
if not exist "frontend\package.json" (
    echo [ERROR] frontend\package.json not found.
    echo Please make sure the NovelWorkshop folder structure is intact.
    pause
    exit /b 1
)
echo [3/5] Folder structure OK.
echo.

REM Kill any existing processes on port 8000 and 5173
echo [3.5/5] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo Killing process on port 8000 (PID: %%a^)
    taskkill /PID %%a /F >nul 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING 2^>nul') do (
    echo Killing process on port 5173 (PID: %%a^)
    taskkill /PID %%a /F >nul 2>nul
)
timeout /t 1 /nobreak >nul
echo      Ports cleared.
echo.

REM Install backend deps
echo [4/5] Installing backend Python deps...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARN] pip failed, trying python -m pip...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Backend deps install failed.
        cd ..
        pause
        exit /b 1
    )
)
cd ..
echo      Backend deps OK.
echo.

REM Install frontend deps
echo [5/5] Installing frontend Node deps (first time may take a few min)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [WARN] npm install failed, cleaning cache and retrying...
    if exist package-lock.json del package-lock.json
    if exist node_modules rmdir /s /q node_modules
    call npm cache clean --force >nul 2>nul
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Frontend deps install failed after retry.
        cd ..
        pause
        exit /b 1
    )
)
cd ..
echo      Frontend deps OK.
echo.

REM Start services
echo ============================================
echo   Starting services...
echo.

REM Start backend in new window
cd backend
start "NW-Backend" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
cd ..

REM Wait for backend to be ready
echo Waiting for backend to start...
set RETRIES=0
:WAIT_LOOP
timeout /t 2 /nobreak >nul
set /a RETRIES+=1
curl -s http://localhost:8000/health >nul 2>nul
if %errorlevel% equ 0 goto BACKEND_OK
if %RETRIES% lss 10 goto WAIT_LOOP

echo.
echo [ERROR] Backend failed to start within 20 seconds!
echo Please check the NW-Backend window for error messages.
echo Common issues:
echo   - Missing Python dependencies (check NW-Backend window)
echo   - Port 8000 already in use by another program
echo   - Python version incompatibility (need 3.11+)
echo.
echo You can still try opening http://localhost:5173 but it may not work.
echo.
goto START_FRONTEND

:BACKEND_OK
echo   [OK] Backend is running!
echo.

:START_FRONTEND
REM Start frontend in new window
cd frontend
start "NW-Frontend" cmd /k "npm run dev"
cd ..

echo   Backend API:   http://localhost:8000
echo   API Docs:      http://localhost:8000/docs
echo   Frontend:      http://localhost:5173
echo.
echo   Open http://localhost:5173 in your browser.
echo ============================================
echo.
echo Services launched!
echo - Close NW-Backend window to stop backend
echo - Close NW-Frontend window to stop frontend
echo.
pause
