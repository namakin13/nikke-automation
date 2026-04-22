@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================
echo  NIKKE Automation - Build
echo ================================================
echo.

if not exist .venv (
    echo [ERROR] .venv not found. Run setup.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

echo [1/4] Installing build dependencies...
pip install customtkinter pyinstaller Pillow --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

echo.
echo [2/4] Generating icon...
python create_icon.py
if errorlevel 1 (
    echo [ERROR] Icon generation failed
    pause
    exit /b 1
)

echo.
echo [3/4] Building with PyInstaller...
pyinstaller nikke_automation.spec --clean --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo Build complete: dist\NikkeAutomation\NikkeAutomation.exe

echo.
echo Creating shortcut...
powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%~dp0dist\NIKKE Automation.lnk'); $s.TargetPath = '%~dp0dist\NikkeAutomation\NikkeAutomation.exe'; $s.WorkingDirectory = '%~dp0dist\NikkeAutomation'; $s.IconLocation = '%~dp0dist\NikkeAutomation\NikkeAutomation.exe,0'; $s.Description = 'NIKKE Automation Tool'; $s.Save()"
if errorlevel 1 (
    echo [WARN] Shortcut creation failed
) else (
    echo Shortcut created: dist\NIKKE Automation.lnk
)

echo.
echo [4/4] Generating installer with Inno Setup...
set ISCC_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC_PATH% (
    %ISCC_PATH% installer.iss
    if errorlevel 1 (
        echo [WARN] Inno Setup installer generation failed
    ) else (
        echo Installer created: dist\NikkeAutomation_Setup.exe
    )
) else (
    echo [INFO] Inno Setup not found. Skipping installer.
    echo       Download from https://jrsoftware.org/isdl.php if needed.
)

echo.
echo ================================================
echo  Done!
echo   Executable : dist\NikkeAutomation\NikkeAutomation.exe
echo   Installer  : dist\NikkeAutomation_Setup.exe (if generated)
echo ================================================
echo.
pause