@echo off
:: Change to the directory where this batch file lives
cd /d "%~dp0"

echo ===================================================
echo   Gmail Inbox IMAP Cleaner - Setup Script
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python (and check "Add Python to PATH" during installation).
    echo.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist .venv (
    echo [1/3] Creating virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtual environment (.venv) already exists.
)

:: Install dependencies
echo [2/3] Installing dependencies from requirements.txt...
.venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Setup .env file
echo [3/3] Setting up configuration file (.env)...
if not exist .env (
    if exist .env.txt (
        echo Copying credentials from .env.txt to .env...
        copy .env.txt .env >nul
    ) else if exist .env.example (
        echo Copying template from .env.example to .env...
        copy .env.example .env >nul
    )
) else (
    echo .env file already exists.
)

echo.
echo ===================================================
echo   Setup Completed Successfully!
echo ===================================================
echo.
echo You can run the cleaner by double-clicking 'run.bat'
echo or by running: .venv\Scripts\python cleaner.py
echo.
pause
