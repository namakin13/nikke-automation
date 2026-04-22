"""
tasks/base_task.py
全タスクの基底クラス
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

import numpy as np
import pyautogui

from core.capture import ScreenCapture
from core.controller import GameController
from core.matcher import MatchResult, TemplateMatcher
from core.window import GameWindow
from utils.logger import get_logger

logger = get_logger()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskResult:
    """タスク実行結果。"""

    def __init__(
        self,
        task_id: str,
        status: TaskStatus,
        message: str = "",
        error: Optional[Exception] = None,
    ) -> None:
        self.task_id = task_id
        self.status = status
        self.message = message
        self.error = error

    def __repr__(self) -> str:
        return f"TaskResult(id={self.task_id}, status={self.status.value}, msg={self.message!r})"

    @property
    def succeeded(self) -> bool:
        return self.status == TaskStatus.SUCCESS


class BaseTask(ABC):
    """全タスクの基底クラス。

    サブクラスは execute() を実装する。
    find_and_click() / wait_for() などのユーティリティメソッドを
    自由に使用できる。
    """

    def __init__(
        self,
        task_id: str,
        window: GameWindow,
        capture: ScreenCapture,
        matcher: TemplateMatcher,
        controller: GameController,
        config: dict,
    ) -> None:
        self.task_id = task_id
        self._window = window
        self._capture = capture
        self._matcher = matcher
        self._controller = controller
        self._config = config
        self._status = TaskStatus.PENDING

    # ──────────────────────────────────────────
    # 抽象メソッド（サブクラスで実装）
    # ──────────────────────────────────────────

    @abstractmethod
    def execute(self) -> TaskResult:
        """タスクのメイン処理を実装する。"""

    # ──────────────────────────────────────────
    # 公開API - タスク実行
    # ──────────────────────────────────────────

    def run(self) -> TaskResult:
        """タスクを実行し、結果を返す。例外を安全にハンドルする。"""
        self._status = TaskStatus.RUNNING
        logger.info("[%s] タスク開始", self.task_id)

        try:
            result = self.execute()
            self._status = result.status
            log_fn = logger.info if result.succeeded else logger.warning
            log_fn("[%s] タスク終了: %s - %s", self.task_id, result.status.value, result.message)
            return result

        except pyautogui.FailSafeException:
            # フェールセーフ発動（マウスが左上隅）はプログラム全体を停止させる
            logger.error("[%s] PyAutoGUI フェールセーフ発動 - プログラムを終了します", self.task_id)
            raise
        except Exception as exc:  # noqa: BLE001
            self._status = TaskStatus.FAILED
            logger.exception("[%s] タスク例外: %s", self.task_id, exc)
            self._capture.capture_and_save(prefix=f"error_{self.task_id}")
            return TaskResult(
                task_id=self.task_id,
                status=TaskStatus.FAILED,
                message=f"予期しない例外: {exc}",
                error=exc,
            )

    # ──────────────────────────────────────────
    # ユーティリティメソッド（サブクラスから使用）
    # ──────────────────────────────────────────

    def screenshot(self) -> Optional[np.ndarray]:
        """現在の画面をキャプチャして返す。"""
        img = self._capture.capture()
        if img is None:
            logger.error("[%s] スクリーンキャプチャ失敗", self.task_id)
        return img

    def find(
        self,
        template_path: str,
        threshold: Optional[float] = None,
        screenshot: Optional[np.ndarray] = None,
    ) -> MatchResult:
        """テンプレートを検索する。"""
        img = screenshot if screenshot is not None else self.screenshot()
        if img is None:
            return MatchResult(found=False, template_path=template_path)
        return self._matcher.find(img, template_path, threshold=threshold)

    def find_and_click(
        self,
        template_path: str,
        threshold: Optional[float] = None,
        delay: Optional[float] = None,
    ) -> bool:
        """テンプレートを探してクリックする。見つからなければ False を返す。"""
        match = self.find(template_path, threshold=threshold)
        if not match.found:
            return False
        return self._controller.click_match(match, delay=delay)

    def wait_for(
        self,
        template_path: str,
        timeout: float = 30.0,
        interval: float = 1.5,
        threshold: Optional[float] = None,
    ) -> Optional[MatchResult]:
        """テンプレートが画面に現れるまで待機する。

        Args:
            template_path: 待機するテンプレートのパス
            timeout: タイムアウト秒数
            interval: チェック間隔秒数
            threshold: マッチング閾値

        Returns:
            見つかった場合は MatchResult、タイムアウトした場合は None。
        """
        start = time.time()
        while time.time() - start < timeout:
            match = self.find(template_path, threshold=threshold)
            if match.found:
                logger.debug(
                    "[%s] wait_for 成功: %s (elapsed=%.1fs)",
                    self.task_id,
                    template_path,
                    time.time() - start,
                )
                return match
            time.sleep(interval)

        logger.warning(
            "[%s] wait_for タイムアウト: %s (%.1fs)",
            self.task_id,
            template_path,
            timeout,
        )
        return None

    def wait_and_click(
        self,
        template_path: str,
        timeout: float = 30.0,
        interval: float = 1.5,
        delay: Optional[float] = None,
        threshold: Optional[float] = None,
    ) -> bool:
        """テンプレートが現れるまで待機してクリックする。"""
        match = self.wait_for(template_path, timeout=timeout, interval=interval, threshold=threshold)
        if match is None:
            return False
        return self._controller.click_match(match, delay=delay)

    def assert_exists(
        self,
        template_path: str,
        threshold: Optional[float] = None,
        screenshot: Optional[np.ndarray] = None,
    ) -> bool:
        """テンプレートが存在することをチェックする（失敗時はFalseを返す）。"""
        img = screenshot if screenshot is not None else self.screenshot()
        if img is None:
            return False
        result = self._matcher.assert_exists(img, template_path, threshold=threshold)
        if not result:
            self._capture.capture_and_save(prefix=f"assert_fail_{self.task_id}")
        return result

    def save_error_screenshot(self, prefix: str = "") -> None:
        """エラー時のスクリーンショットを保存する。"""
        pfx = f"error_{self.task_id}" + (f"_{prefix}" if prefix else "")
        self._capture.capture_and_save(prefix=pfx)

    def cfg(self, key: str, default=None):
        """設定値を取得する。"""
        return self._config.get(key, default)

    def success(self, message: str = "") -> TaskResult:
        """成功結果を生成するヘルパー。"""
        return TaskResult(
            task_id=self.task_id,
            status=TaskStatus.SUCCESS,
            message=message,
        )

    def failed(self, message: str = "", error: Optional[Exception] = None) -> TaskResult:
        """失敗結果を生成するヘルパー。"""
        self.save_error_screenshot()
        return TaskResult(
            task_id=self.task_id,
            status=TaskStatus.FAILED,
            message=message,
            error=error,
        )

    def skipped(self, message: str = "") -> TaskResult:
        """スキップ結果を生成するヘルパー。"""
        return TaskResult(
            task_id=self.task_id,
            status=TaskStatus.SKIPPED,
            message=message,
        )
