@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ================================================
echo  NIKKE Automation - ビルド
echo ================================================
echo.

REM ── 仮想環境 ──
if not exist .venv (
    echo [エラー] .venv が見つかりません。先に setup.bat を実行してください。
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

REM ── 依存パッケージのインストール ──
echo [1/4] ビルド依存パッケージをインストール中...
pip install customtkinter pyinstaller Pillow --quiet
if errorlevel 1 (
    echo [エラー] pip install 失敗
    pause
    exit /b 1
)

REM ── アイコン生成 ──
echo.
echo [2/4] アイコンを生成中...
python create_icon.py
if errorlevel 1 (
    echo [エラー] アイコン生成失敗
    pause
    exit /b 1
)

REM ── PyInstaller でビルド ──
echo.
echo [3/4] PyInstaller でビルド中...
pyinstaller nikke_automation.spec --clean --noconfirm
if errorlevel 1 (
    echo [エラー] PyInstaller ビルド失敗
    pause
    exit /b 1
)

echo.
echo ビルド完了: dist\NikkeAutomation\NikkeAutomation.exe

REM ── ショートカット作成 ──
echo.
echo ショートカットを作成中...
powershell -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $s = $ws.CreateShortcut('%~dp0dist\NIKKE Automation.lnk'); ^
     $s.TargetPath = '%~dp0dist\NikkeAutomation\NikkeAutomation.exe'; ^
     $s.WorkingDirectory = '%~dp0dist\NikkeAutomation'; ^
     $s.IconLocation = '%~dp0dist\NikkeAutomation\NikkeAutomation.exe,0'; ^
     $s.Description = 'NIKKE Automation Tool'; ^
     $s.Save()"
if errorlevel 1 (
    echo [警告] ショートカット作成に失敗しました
) else (
    echo ショートカット作成完了: dist\NIKKE Automation.lnk
)

REM ── Inno Setup でインストーラーを生成（任意） ──
echo.
echo [4/4] Inno Setup でインストーラーを生成中...
set ISCC_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC_PATH% (
    %ISCC_PATH% installer.iss
    if errorlevel 1 (
        echo [警告] Inno Setup でのインストーラー生成に失敗しました
    ) else (
        echo インストーラー生成完了: dist\NikkeAutomation_Setup.exe
    )
) else (
    echo [情報] Inno Setup が見つかりません（インストール不要の場合はスキップ可）
    echo       インストーラーを生成する場合は https://jrsoftware.org/isdl.php から
    echo       Inno Setup 6 をインストールしてください。
)

echo.
echo ================================================
echo  完了！
echo   実行ファイル : dist\NikkeAutomation\NikkeAutomation.exe
echo   インストーラー: dist\NikkeAutomation_Setup.exe (生成された場合)
echo ================================================
echo.
pause
