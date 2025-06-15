@echo off
REM --- Check if Python is installed ---
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python and try again.
    pause
    exit /b 1
)

REM --- Optional: Update your script (if you use update.py) ---
if exist update.py (
    echo Running update.py...
    python update.py
)

REM --- Install dependencies if not already installed ---
echo Checking required Python packages...
python -m pip install -r requirements.txt

REM --- Start the main Python application ---
echo Starting application...
python main4.py

REM --- Pause to keep window open after script ends ---
pause
