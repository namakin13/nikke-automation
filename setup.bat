@echo off
chcp 65001 > /dev/null
cd /d "%~dp0"

echo ================================
echo  NIKKE Setup
echo ================================

python --version 2>/dev/null
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

echo.
echo [1/3] Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo.
echo [2/3] Installing libraries...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

echo.
echo [3/3] Creating directories...
if not exist logs mkdir logs
if not exist logs\screenshots mkdir logs\screenshots
if not exist assets\templates\login_bonus mkdir assets\templates\login_bonus
if not exist assets\templates\battle mkdir assets\templates\battle
if not exist assets\templates\navigation mkdir assets\templates\navigation
if not exist assets\templates\common mkdir assets\templates\common
if not exist assets\templates\captures mkdir assets\templates\captures

echo.
echo ================================
echo  Setup complete!
echo ================================
echo.
echo Next steps:
echo   1. Launch NIKKE
echo   2. Run run_capture.bat to capture template images
echo   3. Run run.bat to start automation
echo.
pause
