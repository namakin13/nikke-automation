# nikke_automation.spec
# PyInstaller ビルド仕様
# 使い方: pyinstaller nikke_automation.spec --noconfirm

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# customtkinter のテーマ・フォントを丸ごと収集
ctk_datas = collect_data_files("customtkinter")

# プロジェクト固有のデータ
project_datas = [
    ("config/settings.yaml", "config"),
    ("config/tasks.yaml",    "config"),
    ("assets",               "assets"),
]

# assets/icon.ico が存在する場合のみ追加
import os
icon_path = "assets/icon.ico"
exe_icon = icon_path if os.path.exists(icon_path) else None

a = Analysis(
    ["gui_main.py"],
    pathex=["."],
    binaries=[],
    datas=ctk_datas + project_datas,
    hiddenimports=[
        # pynput は Windows バックエンドを動的 import するため明示
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        # pywin32
        "win32con",
        "win32gui",
        "win32api",
        # customtkinter サブモジュール
        *collect_submodules("customtkinter"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir モード（起動速度と更新容易性のため）
    name="NikkeAutomation",
    icon=exe_icon,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # コンソールウィンドウを非表示
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,   # NIKKE が管理者権限で動作するためフック取得に必要
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NikkeAutomation",  # dist/NikkeAutomation/ に出力
)
