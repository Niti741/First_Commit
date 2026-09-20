# Kifayat Local Runner for PowerShell
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Starting Kifayat Context Gateway & Helpdesk (http://127.0.0.1:8000)" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Project root: $projectRoot" -ForegroundColor Gray

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
