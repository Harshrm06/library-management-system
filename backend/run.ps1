<# 
.SYNOPSIS
    Start the Library Management System backend server.
    Creates .env from .env.example if missing, seeds database, starts uvicorn.
#>

param(
    [switch]$Reset
)

$ErrorActionPreference = "Stop"

$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $backendDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Library Management System - Backend Starting..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists, create from .env.example if not
if (-not (Test-Path ".env")) {
    Write-Host "[INFO] .env not found, creating from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[INFO] .env created. Please update JWT_SECRET before production use." -ForegroundColor Yellow
}

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "[ERROR] Virtual environment not found. Run: python -m venv venv && .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

# Seed database
Write-Host "[INFO] Initializing database..." -ForegroundColor Green
$seedArgs = "seed_data.py"
if ($Reset) { $seedArgs = "seed_data.py --reset" }
python $seedArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Database seeding failed" -ForegroundColor Red
    exit 1
}

# Start uvicorn server
Write-Host "" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting API server on http://0.0.0.0:8000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$env:PYTHONPATH = "$backendDir;$env:PYTHONPATH"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload