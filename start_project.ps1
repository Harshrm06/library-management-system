<# 
.SYNOPSIS
    Master startup script for Library Management System.
    Starts both backend and frontend in separate windows.
#>

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Library Management System Starting..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend directory exists
if (-not (Test-Path $backendDir)) {
    Write-Host "[ERROR] Backend directory not found: $backendDir" -ForegroundColor Red
    exit 1
}

# Check if frontend directory exists
if (-not (Test-Path $frontendDir)) {
    Write-Host "[ERROR] Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}

# Start backend in new window
Write-Host "[INFO] Starting backend server in new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backendDir'; .\run.ps1" -WindowStyle Normal

# Wait for backend to start
Write-Host "[INFO] Waiting 5 seconds for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Start frontend in new window
Write-Host "[INFO] Starting frontend server in new window..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontendDir'; .\run.ps1" -WindowStyle Normal

# Wait a moment
Start-Sleep -Seconds 2

Write-Host "" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Library Management System is running!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "  Default Credentials:" -ForegroundColor Yellow
Write-Host "    Admin:    admin@library.local / Admin123" -ForegroundColor Yellow
Write-Host "    Member:   member@library.local / Member123" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Press Ctrl+C in each window to stop the servers." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan