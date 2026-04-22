"""
gui_main.py
NIKKE Automation GUI エントリーポイント

PyInstaller バンドル時のパス解決:
  - onefile: sys._MEIPASS に展開された一時ディレクトリ (読み取り専用)
  - onedir : exe ファイルが置かれたディレクトリ
  config/ などの読み込みは _MEIPASS / exe 親ディレクトリを参照し、
  logs/ recordings/ などの書き込みは常に exe 隣のディレクトリに出力する。
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def _setup_paths() -> None:
    frozen = getattr(sys, "frozen", False)
    meipass = getattr(sys, "_MEIPASS", None)

    if frozen:
        # 読み取り専用リソース（config, assets 等）の場所
        read_dir = Path(meipass) if meipass else Path(sys.executable).parent
        # 書き込み可能な場所（logs, recordings）は exe の隣
        write_dir = Path(sys.executable).parent
    else:
        read_dir = Path(__file__).parent
        write_dir = read_dir

    # CWD を読み取りリソースの場所に設定（相対パス参照を統一）
    os.chdir(str(read_dir))

    # 書き込み先を環境変数経由でアプリに伝える
    os.environ["NIKKE_WRITABLE_DIR"] = str(write_dir)


def _set_dpi_awareness() -> None:
    """DPI スケーリングを正しく扱うために設定する。
    mss のスクリーンキャプチャ座標ズレを防ぐ。
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main() -> None:
    _setup_paths()
    _set_dpi_awareness()

    from gui.app import NikkeAutomationApp

    app = NikkeAutomationApp()
    app.mainloop()


if __name__ == "__main__":
    main()
