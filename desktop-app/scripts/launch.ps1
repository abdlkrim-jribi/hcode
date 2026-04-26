#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch Hcode Desktop App in development mode.
    
.DESCRIPTION
    Starts the Vite frontend dev server and the Tauri app binary together.
    The Vite server must be running before the app opens.
#>

$ErrorActionPreference = "Stop"

$cargoPath = "$env:USERPROFILE\.cargo\bin"
$binaryPath = "C:\RustTarget\hcode-desktop\debug\hcode-desktop.exe"
$uiDir = "$PSScriptRoot\..\src-ui"

Write-Host ""
Write-Host "  ⚡ Hcode Desktop — Dev Launcher" -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor DarkGray
Write-Host ""

# Check prerequisites
if (-not (Test-Path $binaryPath)) {
    Write-Host "  ❌ Binary not found. Building first..." -ForegroundColor Yellow
    $env:PATH = "$cargoPath;$env:PATH"
    $env:CARGO_TARGET_DIR = "C:\RustTarget\hcode-desktop"
    Push-Location "$PSScriptRoot\..\src-tauri"
    cargo build 2>&1
    Pop-Location
}

# Kill any existing Vite process on port 1420
$existing = Get-NetTCPConnection -LocalPort 1420 -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "  🌐 Starting Vite frontend server..." -ForegroundColor Green
    $viteJob = Start-Process -FilePath "npm" -ArgumentList "run", "dev" `
        -WorkingDirectory $uiDir -WindowStyle Minimized -PassThru
    Write-Host "  ⏳ Waiting for Vite to be ready..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 3
}
else {
    Write-Host "  ✅ Vite already running on port 1420" -ForegroundColor Green
}

# Launch the desktop app
Write-Host "  🚀 Launching Hcode..." -ForegroundColor Cyan
Write-Host ""
Start-Process -FilePath $binaryPath -WorkingDirectory "$PSScriptRoot\..\src-tauri"

Write-Host "  ✅ Hcode is running!" -ForegroundColor Green
Write-Host "  📁 Binary: $binaryPath" -ForegroundColor DarkGray
Write-Host ""
