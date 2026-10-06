<# 
.SYNOPSIS
    Start the Library Management System frontend development server.
    Installs dependencies if needed, starts Vite dev server.
#>

$ErrorActionPreference = "Stop"

$frontendDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $frontendDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Library Management System - Frontend Starting..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if node_modules exists, install if not
if (-not (Test-Path "node_modules")) {
    Write-Host "[INFO] node_modules not found, installing dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] npm install failed" -ForegroundColor Red
        exit 1
    }
}

# Start Vite dev server
Write-Host "" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting Vite dev server on http://localhost:5173" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

npm run dev