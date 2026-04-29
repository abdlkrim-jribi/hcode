# Hcode Desktop App — Development Script
# Usage: .\scripts\dev.ps1

Write-Host "⚡ Starting Hcode Desktop in dev mode..." -ForegroundColor Cyan

# Check prerequisites
$checks = @{
    "Node.js" = { node --version 2>$null }
    "Rust"    = { rustc --version 2>$null }
    "Python"  = { python --version 2>$null }
}

foreach ($name in $checks.Keys) {
    $result = & $checks[$name]
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ $name is required but not found!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ $name: $result" -ForegroundColor Green
}

# Start Python daemon in mock mode (background)
Write-Host "`n🐍 Starting mock daemon..." -ForegroundColor Yellow
$daemonProcess = Start-Process python -ArgumentList "$PSScriptRoot\..\hcode-daemon\run_daemon.py", "--mock" -NoNewWindow -PassThru

# Install frontend deps if needed
$nodeModules = "$PSScriptRoot\..\src-ui\node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "`n📦 Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location "$PSScriptRoot\..\src-ui"
    npm install
    Pop-Location
}

# Start Tauri dev (frontend + Rust backend)
Write-Host "`n🚀 Starting Tauri dev server..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\..\src-ui"
npx tauri dev
Pop-Location

# Cleanup
Write-Host "`n🧹 Cleaning up..." -ForegroundColor Yellow
if ($daemonProcess -and -not $daemonProcess.HasExited) {
    Stop-Process $daemonProcess
}

Write-Host "✅ Done!" -ForegroundColor Green
