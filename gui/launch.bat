@echo off
:: tiny11 Builder GUI Launcher
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Install Python 3.8+ from python.org
    pause
    exit /b 1
)

python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing customtkinter...
    pip install customtkinter
)

echo Starting tiny11 Builder GUI...
echo.
python main.py
echo.
echo --- tiny11 Builder GUI 已結束 ---
echo.
pause
