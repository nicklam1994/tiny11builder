@echo off
:: tiny11 Builder GUI Launcher
:: Double-click to run (no admin needed for the GUI itself)

cd /d "%~dp0"

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check Python version
python -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.8+ required!
    python --version
    pause
    exit /b 1
)

:: Install dependencies if needed
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing customtkinter...
    pip install customtkinter
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install customtkinter.
        echo Try running: pip install customtkinter
        pause
        exit /b 1
    )
)

:: Launch GUI
echo Starting tiny11 Builder GUI...
python main.py

:: If we get here, the app exited normally or crashed
if exist error.log (
    echo.
    echo [!] An error occurred. See error.log for details:
    echo.
    type error.log
    del error.log
    echo.
    pause
)
