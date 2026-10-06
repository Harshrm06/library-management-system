@echo off
REM ==========================================================================
REM  Library Management System - start the API and the Vite dev server.
REM
REM  Usage (from anywhere):
REM      run_project.bat            start both servers
REM      run_project.bat --migrate  run "alembic upgrade head" first
REM
REM  Environment overrides:
REM      HOST  interface uvicorn binds to (default 127.0.0.1)
REM      PORT  API port (default 8000)
REM
REM  Prerequisite: MySQL must be running and the schema migrated, otherwise
REM  every endpoint fails at runtime. See backend\.env.example for DATABASE_URL.
REM ==========================================================================
setlocal enabledelayedexpansion

REM Resolve the project root from this script's own location, so the script
REM works regardless of the directory it is launched from.
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "PY=%BACKEND%\.venv\Scripts\python.exe"

set "HOST=%HOST%"
if "%HOST%"=="" set "HOST=127.0.0.1"
set "PORT=%PORT%"
if "%PORT%"=="" set "PORT=8000"

REM --- prerequisite checks -------------------------------------------------
if not exist "%PY%" (
    echo [ERROR] Backend virtual environment not found at:
    echo         %PY%
    echo         Create it first:
    echo             cd backend
    echo             python -m venv .venv
    echo             .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not on PATH. Install Node 18+ and reopen this terminal.
    exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
    echo [WARNING] frontend\node_modules is missing.
    echo          Run "npm install" in %FRONTEND% first.
    echo.
)

if not exist "%BACKEND%\.env" (
    echo [WARNING] backend\.env not found - falling back to built-in defaults.
    echo          JWT_SECRET will be the insecure "change_me_in_production" and
    echo          DATABASE_URL will be the placeholder MySQL URL.
    echo          Copy backend\.env.example to backend\.env to fix this.
    echo.
)

REM --- optional schema migration ------------------------------------------
set "MIGRATE=0"
for %%A in (%*) do (
    if /I "%%~A"=="--migrate" set "MIGRATE=1"
)

if "%MIGRATE%"=="1" (
    echo [INFO] Applying database migrations...
    pushd "%BACKEND%"
    "%PY%" -m alembic upgrade head
    if errorlevel 1 (
        popd
        echo [ERROR] Migration failed. Is MySQL running and reachable?
        exit /b 1
    )
    popd
    echo [INFO] Migrations applied.
    echo.
)

REM --- start both servers --------------------------------------------------
echo [INFO] Starting backend on http://%HOST%:%PORT%
start "Library API" /D "%BACKEND%" cmd /k ""%PY%" -m uvicorn app.main:app --reload --host %HOST% --port %PORT%"

echo [INFO] Starting frontend...
pushd "%FRONTEND%"
start "Library Web" /D "%FRONTEND%" cmd /k "npm run dev"
popd

echo.
echo   Backend:  http://localhost:%PORT%
echo   API docs: http://localhost:%PORT%/docs
echo   Frontend: http://localhost:5173
echo.
echo   Both servers run in their own window. Close those windows to stop.
echo.
pause
