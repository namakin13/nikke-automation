"""
core/window.py
NIKKEのゲームウィンドウ検出・管理
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import win32con
import win32gui

from utils.logger import get_logger

logger = get_logger()

WINDOW_TITLE_CANDIDATES = [
    "GODDESS OF VICTORY: NIKKE",
    "NIKKE",
]


@dataclass
class WindowRect:
    """ウィンドウの絶対座標領域。"""
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)

    def to_monitor_dict(self) -> dict:
        """mss用のモニター辞書を返す。"""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

    def abs_point(self, rel_x: int, rel_y: int) -> tuple[int, int]:
        """ウィンドウ相対座標 → スクリーン絶対座標に変換。"""
        return (self.left + rel_x, self.top + rel_y)

    def rel_point(self, abs_x: int, abs_y: int) -> tuple[int, int]:
        """スクリーン絶対座標 → ウィンドウ相対座標に変換。"""
        return (abs_x - self.left, abs_y - self.top)


class GameWindow:
    """NIKKEゲームウィンドウの検出・フォーカス管理クラス。"""

    def __init__(self, title_candidates: list[str] | None = None) -> None:
        self._candidates = title_candidates or WINDOW_TITLE_CANDIDATES
        self._hwnd: Optional[int] = None

    # ──────────────────────────────────────────
    # 公開API
    # ──────────────────────────────────────────

    def find(self) -> bool:
        """ゲームウィンドウを探してハンドルを取得する。

        Returns:
            見つかった場合 True。
        """
        for title in self._candidates:
            hwnd = win32gui.FindWindow(None, title)
            if hwnd:
                self._hwnd = hwnd
                logger.info("ウィンドウ検出: '%s' (hwnd=%d)", title, hwnd)
                return True

        # 部分一致検索にフォールバック
        self._hwnd = self._find_partial_match()
        if self._hwnd:
            return True

        logger.error(
            "NIKKEウィンドウが見つかりません。ゲームを起動してください。候補: %s",
            self._candidates,
        )
        return False

    def focus(self) -> bool:
        """ウィンドウを最前面にフォーカスする。

        Returns:
            成功した場合 True。
        """
        if not self._hwnd:
            logger.warning("focus(): ウィンドウハンドルがありません。find() を先に呼んでください。")
            return False
        try:
            if win32gui.IsIconic(self._hwnd):
                win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self._hwnd)
            logger.debug("ウィンドウをフォーカスしました (hwnd=%d)", self._hwnd)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("ウィンドウフォーカス失敗: %s", exc)
            return False

    def get_rect(self) -> Optional[WindowRect]:
        """ウィンドウのクライアント領域をスクリーン座標で返す。

        Returns:
            WindowRect または None（ウィンドウが見つからない場合）。
        """
        if not self._hwnd:
            return None
        try:
            # クライアント領域の左上をスクリーン座標に変換
            client_left, client_top = win32gui.ClientToScreen(self._hwnd, (0, 0))
            client_rect = win32gui.GetClientRect(self._hwnd)
            return WindowRect(
                left=client_left,
                top=client_top,
                right=client_left + client_rect[2],
                bottom=client_top + client_rect[3],
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("ウィンドウ矩形取得失敗: %s", exc)
            return None

    def get_title(self) -> str:
        """現在のウィンドウタイトルを返す。取得できない場合は空文字。"""
        if not self._hwnd:
            return ""
        try:
            return win32gui.GetWindowText(self._hwnd)
        except Exception:  # noqa: BLE001
            return ""

    def is_alive(self) -> bool:
        """ウィンドウがまだ存在しているか確認する。"""
        if not self._hwnd:
            return False
        return bool(win32gui.IsWindow(self._hwnd))

    @property
    def hwnd(self) -> Optional[int]:
        return self._hwnd

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _find_partial_match(self) -> Optional[int]:
        """ウィンドウタイトルの部分一致でハンドルを探す。"""
        found_hwnd: Optional[int] = None

        def _callback(hwnd: int, _: None) -> None:
            nonlocal found_hwnd
            if found_hwnd:
                return
            title = win32gui.GetWindowText(hwnd)
            for candidate in self._candidates:
                if candidate.lower() in title.lower():
                    found_hwnd = hwnd
                    logger.info(
                        "ウィンドウ部分一致検出: '%s' (hwnd=%d)", title, hwnd
                    )
                    return

        win32gui.EnumWindows(_callback, None)
        return found_hwnd
