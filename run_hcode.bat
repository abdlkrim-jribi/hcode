@echo off
REM Windows launcher for Hcode AI Assistant

echo ===============================================
echo    Starting Hcode AI Assistant
echo ===============================================
echo.

REM Set UTF-8 encoding for better character support
chcp 65001 > nul 2>&1

REM Set Python encoding
set PYTHONIOENCODING=utf-8

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Run the Hcode interface
echo Loading Hcode interface...
echo.
python hcode.py %*

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start Hcode interface
    echo Please check the error messages above
    pause
)