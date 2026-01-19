# Hcode Quick Start Script for Windows (PowerShell)
# This script helps you get started with Hcode quickly

$ErrorActionPreference = "Stop"

Write-Host "🚀 Hcode Quick Start Script" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "❌ Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

$pythonVersion = & $pythonCmd --version 2>&1
Write-Host "✅ $pythonVersion found" -ForegroundColor Green

# Check if Poetry is installed
Write-Host ""
Write-Host "📦 Checking for Poetry..." -ForegroundColor Yellow

$usePoetry = $false
if (Get-Command poetry -ErrorAction SilentlyContinue) {
    $poetryVersion = poetry --version 2>&1
    Write-Host "✅ $poetryVersion found" -ForegroundColor Green
    $usePoetry = $true
} else {
    Write-Host "⚠️  Poetry not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Would you like to:"
    Write-Host "  1) Install Poetry (recommended)"
    Write-Host "  2) Continue with pip"
    Write-Host ""

    $choice = Read-Host "Enter choice (1 or 2)"

    if ($choice -eq "1") {
        Write-Host ""
        Write-Host "📥 Installing Poetry..." -ForegroundColor Yellow

        try {
            (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | & $pythonCmd -

            # Add Poetry to PATH for this session
            $env:Path += ";$env:APPDATA\Python\Scripts"

            if (Get-Command poetry -ErrorAction SilentlyContinue) {
                Write-Host "✅ Poetry installed successfully" -ForegroundColor Green
                $usePoetry = $true
            } else {
                Write-Host "❌ Poetry installation failed. Falling back to pip." -ForegroundColor Red
                $usePoetry = $false
            }
        } catch {
            Write-Host "❌ Poetry installation failed. Falling back to pip." -ForegroundColor Red
            $usePoetry = $false
        }
    }
}

# Install Hcode
Write-Host ""
Write-Host "📦 Installing Hcode..." -ForegroundColor Yellow

if ($usePoetry) {
    Write-Host "Using Poetry..."
    poetry install

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Hcode installed with Poetry" -ForegroundColor Green
        Write-Host ""
        Write-Host "To activate the environment, run:"
        Write-Host "  poetry shell" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Installation failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Using pip..."

    # Create virtual environment
    & $pythonCmd -m venv venv

    # Activate virtual environment
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    }

    # Install Hcode
    pip install -e .

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Hcode installed with pip" -ForegroundColor Green
        Write-Host ""
        Write-Host "Virtual environment created in .\venv"
        Write-Host "To activate it, run:"
        Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Installation failed" -ForegroundColor Red
        exit 1
    }
}

# Check for .env file
Write-Host ""
Write-Host "🔑 Checking API keys..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env file found" -ForegroundColor Yellow
    Write-Host ""

    $createEnv = Read-Host "Would you like to create .env file now? (y/n)"

    if ($createEnv -eq "y" -or $createEnv -eq "Y") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Created .env file from template" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: Edit .env and add your API keys:" -ForegroundColor Yellow
        Write-Host "   - ANTHROPIC_API_KEY"
        Write-Host "   - OPENAI_API_KEY"
        Write-Host ""

        $openEditor = Read-Host "Open .env in notepad? (y/n)"
        if ($openEditor -eq "y" -or $openEditor -eq "Y") {
            notepad .env
        }
    } else {
        Write-Host "⚠️  Remember to create .env file and add your API keys" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ .env file exists" -ForegroundColor Green
}

# Verify installation
Write-Host ""
Write-Host "🔍 Verifying installation..." -ForegroundColor Yellow

$verifySuccess = $false
if ($usePoetry) {
    try {
        $version = poetry run hcode --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Hcode is working correctly" -ForegroundColor Green
            Write-Host "   $version" -ForegroundColor Gray
            $verifySuccess = $true
        }
    } catch {
        Write-Host "❌ Hcode verification failed" -ForegroundColor Red
    }
} else {
    try {
        $version = hcode --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Hcode is working correctly" -ForegroundColor Green
            Write-Host "   $version" -ForegroundColor Gray
            $verifySuccess = $true
        }
    } catch {
        Write-Host "❌ Hcode verification failed" -ForegroundColor Red
        Write-Host "   Try activating the virtual environment first" -ForegroundColor Yellow
    }
}

if (-not $verifySuccess) {
    exit 1
}

# Success message
Write-Host ""
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host ""
Write-Host "🎉 Hcode is ready to use!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Start Commands:" -ForegroundColor Yellow
Write-Host "  hcode --help                  # Show help"
Write-Host "  hcode run `"your task`"         # Execute a task"
Write-Host "  hcode chat                    # Start interactive chat"
Write-Host "  hcode analyze <file>          # Analyze code"
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Yellow
Write-Host "  README.md          - Main documentation"
Write-Host "  INSTALLATION.md    - Installation guide"
Write-Host "  TOOLS.md           - Tool reference"
Write-Host "  SHORTCUTS.md       - Keyboard shortcuts"
Write-Host ""
Write-Host "💡 Examples:" -ForegroundColor Yellow
Write-Host "  src\hcode\examples\basic_usage.py"
Write-Host "  src\hcode\examples\advanced_features.py"
Write-Host ""
Write-Host "Happy coding! 🚀" -ForegroundColor Cyan
