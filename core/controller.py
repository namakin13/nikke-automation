"""
core/controller.py
マウス・キーボード入力制御モジュール
ウィンドウ相対座標をスクリーン絶対座標に変換してクリック・入力する
"""
from __future__ import annotations

import time
from typing import Optional

import pyautogui

from core.window import GameWindow
from utils.logger import get_logger

logger = get_logger()

# PyAutoGUI のフェールセーフを有効化（マウスを左上隅に移動で緊急停止）
pyautogui.FAILSAFE = True
# デフォルトのアクション間隔
pyautogui.PAUSE = 0.05


class GameController:
    """ゲームへの入力操作を担当するクラス。

    ウィンドウ相対座標で操作を指定すると、
    内部でスクリーン絶対座標に変換してクリック等を実行する。
    """

    def __init__(
        self,
        window: GameWindow,
        after_click_delay: float = 0.8,
        move_duration: float = 0.1,
    ) -> None:
        self._window = window
        self._after_click_delay = after_click_delay
        self._move_duration = move_duration

    # ──────────────────────────────────────────
    # 公開API - クリック系
    # ──────────────────────────────────────────

    def click(
        self,
        rel_x: int,
        rel_y: int,
        delay: Optional[float] = None,
        button: str = "left",
    ) -> bool:
        """ウィンドウ相対座標をクリックする。

        Args:
            rel_x: ウィンドウ左上からの相対X座標
            rel_y: ウィンドウ左上からの相対Y座標
            delay: クリック後の待機秒数（省略時はデフォルト値）
            button: "left" / "right" / "middle"

        Returns:
            成功した場合 True。
        """
        abs_pos = self._to_abs(rel_x, rel_y)
        if abs_pos is None:
            return False

        abs_x, abs_y = abs_pos
        logger.debug("クリック: 相対(%d, %d) → 絶対(%d, %d)", rel_x, rel_y, abs_x, abs_y)

        try:
            pyautogui.click(abs_x, abs_y, button=button, duration=self._move_duration)
            time.sleep(delay if delay is not None else self._after_click_delay)
            return True
        except pyautogui.FailSafeException:
            logger.error("PyAutoGUI フェールセーフ: マウスが画面左上に移動されました")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("クリック失敗 (%d, %d): %s", rel_x, rel_y, exc)
            return False

    def click_match(self, match, delay: Optional[float] = None) -> bool:
        """MatchResult の中心座標をクリックする。

        Args:
            match: core.matcher.MatchResult インスタンス
            delay: クリック後の待機秒数

        Returns:
            成功した場合 True。
        """
        if not match.found:
            logger.warning("click_match: MatchResult.found=False のためスキップ")
            return False
        return self.click(match.center_x, match.center_y, delay=delay)

    def double_click(self, rel_x: int, rel_y: int, delay: Optional[float] = None) -> bool:
        """ウィンドウ相対座標をダブルクリックする。"""
        abs_pos = self._to_abs(rel_x, rel_y)
        if abs_pos is None:
            return False
        try:
            pyautogui.doubleClick(*abs_pos, duration=self._move_duration)
            time.sleep(delay if delay is not None else self._after_click_delay)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("ダブルクリック失敗: %s", exc)
            return False

    def right_click(self, rel_x: int, rel_y: int, delay: Optional[float] = None) -> bool:
        """ウィンドウ相対座標を右クリックする。"""
        return self.click(rel_x, rel_y, delay=delay, button="right")

    def long_press(
        self,
        rel_x: int,
        rel_y: int,
        duration: float = 1.0,
        delay: Optional[float] = None,
    ) -> bool:
        """ウィンドウ相対座標を長押しする。"""
        abs_pos = self._to_abs(rel_x, rel_y)
        if abs_pos is None:
            return False
        try:
            pyautogui.mouseDown(*abs_pos, button="left")
            time.sleep(duration)
            pyautogui.mouseUp(*abs_pos, button="left")
            time.sleep(delay if delay is not None else self._after_click_delay)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("長押し失敗: %s", exc)
            return False

    # ──────────────────────────────────────────
    # 公開API - スワイプ・ドラッグ系
    # ──────────────────────────────────────────

    def swipe(
        self,
        from_rel_x: int,
        from_rel_y: int,
        to_rel_x: int,
        to_rel_y: int,
        duration: float = 0.5,
    ) -> bool:
        """ウィンドウ相対座標でスワイプ（ドラッグ）する。"""
        from_abs = self._to_abs(from_rel_x, from_rel_y)
        to_abs = self._to_abs(to_rel_x, to_rel_y)

        if from_abs is None or to_abs is None:
            return False

        try:
            pyautogui.moveTo(*from_abs, duration=0.1)
            pyautogui.dragTo(*to_abs, duration=duration, button="left")
            time.sleep(self._after_click_delay)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("スワイプ失敗: %s", exc)
            return False

    # ──────────────────────────────────────────
    # 公開API - キーボード系
    # ──────────────────────────────────────────

    def press_key(self, key: str, delay: Optional[float] = None) -> bool:
        """キーを押す（pyautogui キー名）。"""
        try:
            pyautogui.press(key)
            time.sleep(delay if delay is not None else 0.3)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("キー押下失敗 '%s': %s", key, exc)
            return False

    def press_escape(self) -> bool:
        """ESCキーを押す（ダイアログ閉じる等に使用）。"""
        return self.press_key("escape")

    # ──────────────────────────────────────────
    # 公開API - 待機系
    # ──────────────────────────────────────────

    def wait(self, seconds: float) -> None:
        """指定秒数待機する。"""
        logger.debug("待機: %.1f秒", seconds)
        time.sleep(seconds)

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _to_abs(self, rel_x: int, rel_y: int) -> Optional[tuple[int, int]]:
        """ウィンドウ相対座標をスクリーン絶対座標に変換する。"""
        rect = self._window.get_rect()
        if rect is None:
            logger.error("_to_abs(): ウィンドウ矩形を取得できません")
            return None
        return rect.abs_point(rel_x, rel_y)
