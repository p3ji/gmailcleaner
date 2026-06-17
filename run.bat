@echo off
cd /d "%~dp0"
echo Starting Gmail Inbox IMAP Cleaner...
echo.
if not exist ".venv\Scripts\python.exe" goto setup
goto run

:setup
echo Virtual environment not found. Running setup...
echo.
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
if not exist .env if exist .env.txt copy .env.txt .env >nul
echo.

:run
.venv\Scripts\python cleaner.py
echo.
echo Press any key to close this window...
pause >nul
