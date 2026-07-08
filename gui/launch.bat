@echo off
:: tiny11 Builder GUI Launcher
:: Double-click to run (no admin needed for the GUI itself)

cd /d "%~dp0"
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
pip show customtkinter >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

:: Launch GUI
python main.py
