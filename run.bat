@echo off
chcp 65001 > /dev/null
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Starting NIKKE automation...
echo Emergency stop: move mouse to top-left corner
echo.
python main.py %*
pause
