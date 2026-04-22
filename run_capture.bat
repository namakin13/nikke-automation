@echo off
chcp 65001 > /dev/null
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Template capture mode
echo Launch NIKKE, go to the screen you want, then press Enter
echo.
python main.py --capture
pause
