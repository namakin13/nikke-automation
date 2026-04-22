"""
core/capture.py
スクリーンキャプチャモジュール
mss を使用してゲームウィンドウ領域を高速キャプチャする
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import mss
import numpy as np

from core.window import GameWindow, WindowRect
from utils.logger import get_logger

logger = get_logger()


class ScreenCapture:
    """ゲームウィンドウのスクリーンキャプチャを担当するクラス。"""

    def __init__(
        self,
        window: GameWindow,
        screenshot_dir: str = "logs/screenshots",
    ) -> None:
        self._window = window
        self._screenshot_dir = Path(screenshot_dir)
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────
    # 公開API
    # ──────────────────────────────────────────

    def capture(self) -> Optional[np.ndarray]:
        """現在のゲームウィンドウ領域をキャプチャしてBGR画像を返す。

        Returns:
            BGR形式の numpy 配列。失敗した場合は None。
        """
        rect = self._window.get_rect()
        if rect is None:
            logger.error("capture(): ウィンドウ矩形を取得できませんでした。")
            return None

        return self._capture_rect(rect)

    def capture_region(
        self,
        rel_x: int,
        rel_y: int,
        width: int,
        height: int,
    ) -> Optional[np.ndarray]:
        """ウィンドウ内の指定相対領域をキャプチャする。

        Args:
            rel_x: ウィンドウ左上からの相対X座標
            rel_y: ウィンドウ左上からの相対Y座標
            width: キャプチャ幅
            height: キャプチャ高さ

        Returns:
            BGR形式の numpy 配列。失敗した場合は None。
        """
        rect = self._window.get_rect()
        if rect is None:
            return None

        region = WindowRect(
            left=rect.left + rel_x,
            top=rect.top + rel_y,
            right=rect.left + rel_x + width,
            bottom=rect.top + rel_y + height,
        )
        return self._capture_rect(region)

    def save_screenshot(
        self,
        image: np.ndarray,
        prefix: str = "screenshot",
    ) -> Path:
        """画像をファイルに保存する。

        Args:
            image: 保存するBGR画像
            prefix: ファイル名のプレフィックス

        Returns:
            保存先のパス。
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self._screenshot_dir / f"{prefix}_{ts}.png"
        cv2.imwrite(str(path), image)
        logger.debug("スクリーンショット保存: %s", path)
        return path

    def capture_and_save(self, prefix: str = "capture") -> Optional[Path]:
        """キャプチャして保存し、パスを返す。"""
        img = self.capture()
        if img is None:
            return None
        return self.save_screenshot(img, prefix)

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    @staticmethod
    def _capture_rect(rect: WindowRect) -> Optional[np.ndarray]:
        """指定矩形領域をキャプチャしてBGR画像を返す。"""
        try:
            with mss.mss() as sct:
                shot = sct.grab(rect.to_monitor_dict())
                # BGRA → BGR
                img = np.array(shot)
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as exc:  # noqa: BLE001
            logger.error("スクリーンキャプチャ失敗: %s", exc)
            return None
