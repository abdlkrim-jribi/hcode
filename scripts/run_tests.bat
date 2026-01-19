@echo off
REM Quick Test Script for Hcode (Windows)
REM Run this to verify basic functionality

echo ============================================
echo Hcode Quick Test Suite (Windows)
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

echo [1/7] Checking Python version...
python --version
echo.

REM Check if API keys are set
echo [2/7] Checking environment variables...
if not defined ANTHROPIC_API_KEY (
    echo WARNING: ANTHROPIC_API_KEY not set
    echo Please set it with: set ANTHROPIC_API_KEY=your-key
    pause
    exit /b 1
)
echo ✓ ANTHROPIC_API_KEY is set
echo.

REM Install dependencies if needed
echo [3/7] Checking installation...
python -c "import hcode" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Hcode...
    pip install -e .
    if %errorlevel% neq 0 (
        echo ERROR: Installation failed
        exit /b 1
    )
)
echo ✓ Hcode is installed
echo.

REM Run Python test script
echo [4/7] Running comprehensive tests...
python quick_test.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Tests failed
    echo See above for details
    pause
    exit /b 1
)
echo.

REM Test CLI command
echo [5/7] Testing CLI command...
hcode --version
if %errorlevel% neq 0 (
    echo ERROR: hcode command not found
    exit /b 1
)
echo ✓ CLI works
echo.

REM Test help
echo [6/7] Testing help command...
hcode --help >nul
if %errorlevel% neq 0 (
    echo ERROR: help command failed
    exit /b 1
)
echo ✓ Help command works
echo.

REM Final message
echo [7/7] All basic tests passed!
echo.
echo ============================================
echo ✓ Hcode is ready to use!
echo ============================================
echo.
echo Next steps:
echo   1. hcode run "Hello, how can you help me?"
echo   2. hcode chat (for interactive mode)
echo   3. See TESTING_GUIDE.md for more tests
echo.
pause
