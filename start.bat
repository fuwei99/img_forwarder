@echo off
echo Starting Discord Bot...
echo.

:: Check if Python is installed and determine command
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
) else (
    python3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=python3
    ) else (
        echo Python is not installed or not in PATH. Please install Python.
        pause
        exit /b 1
    )
)

:: Check if dependencies are installed
echo Checking dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt

:: Start the bot
echo Starting the bot...
echo The invite link will be shown after the bot has started.
echo.

%PYTHON_CMD% main.py 