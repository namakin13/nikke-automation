"""
tasks/task_runner.py
タスクランナー - tasks.yaml を読み込み、有効なタスクを順番に実行する
"""
from __future__ import annotations

import importlib
import time
from pathlib import Path
from typing import Optional

import yaml

from core.capture import ScreenCapture
from core.controller import GameController
from core.matcher import TemplateMatcher
from core.window import GameWindow
from tasks.base_task import BaseTask, TaskResult, TaskStatus
from utils.logger import get_logger

logger = get_logger()


class TaskRunner:
    """tasks.yaml を元にタスクを順番に実行するランナー。"""

    def __init__(
        self,
        window: GameWindow,
        capture: ScreenCapture,
        matcher: TemplateMatcher,
        controller: GameController,
        tasks_config_path: str = "config/tasks.yaml",
        stop_on_failure: bool = False,
    ) -> None:
        self._window = window
        self._capture = capture
        self._matcher = matcher
        self._controller = controller
        self._tasks_config_path = tasks_config_path
        self._stop_on_failure = stop_on_failure
        self._results: list[TaskResult] = []

    # ──────────────────────────────────────────
    # 公開API
    # ──────────────────────────────────────────

    def run_all(self) -> list[TaskResult]:
        """有効な全タスクを実行し、結果リストを返す。"""
        task_defs = self._load_tasks()

        if not task_defs:
            logger.warning("実行可能なタスクがありません（tasks.yaml を確認してください）")
            return []

        logger.info("=" * 50)
        logger.info("NIKKE 日課自動化 開始（タスク数: %d）", len(task_defs))
        logger.info("=" * 50)

        self._results = []

        for task_def in task_defs:
            task_id = task_def.get("id", "unknown")
            task_name = task_def.get("name", task_id)
            logger.info("─" * 40)
            logger.info("▶ タスク開始: %s", task_name)

            task = self._build_task(task_def)
            if task is None:
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    message="タスクのロードに失敗しました",
                )
                self._results.append(result)
                if self._stop_on_failure:
                    break
                continue

            result = task.run()
            self._results.append(result)

            if result.status == TaskStatus.FAILED and self._stop_on_failure:
                logger.error("タスク失敗のため中断します: %s", task_name)
                break

            # タスク間の待機
            time.sleep(1.5)

        self._print_summary()
        return self._results

    def run_task(self, task_id: str) -> Optional[TaskResult]:
        """指定IDのタスクだけを実行する。"""
        task_defs = self._load_tasks(include_disabled=True)
        target = next((t for t in task_defs if t.get("id") == task_id), None)

        if target is None:
            logger.error("タスクID '%s' が tasks.yaml に見つかりません", task_id)
            return None

        task = self._build_task(target)
        if task is None:
            return None

        return task.run()

    @property
    def results(self) -> list[TaskResult]:
        return self._results

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _load_tasks(self, include_disabled: bool = False) -> list[dict]:
        """tasks.yaml からタスク定義を読み込む。"""
        config_path = Path(self._tasks_config_path)
        if not config_path.exists():
            logger.error("tasks.yaml が見つかりません: %s", config_path)
            return []

        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        all_tasks: list[dict] = data.get("tasks", [])

        if not include_disabled:
            all_tasks = [t for t in all_tasks if t.get("enabled", True)]

        # order でソート
        all_tasks.sort(key=lambda t: t.get("order", 999))

        return all_tasks

    def _build_task(self, task_def: dict) -> Optional[BaseTask]:
        """タスク定義からタスクインスタンスを生成する。"""
        task_id = task_def.get("id", "unknown")
        module_path = task_def.get("module")
        class_name = task_def.get("class")
        task_config = task_def.get("config", {})

        if not module_path or not class_name:
            logger.error("[%s] module または class が未定義です", task_id)
            return None

        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
        except (ImportError, AttributeError) as exc:
            logger.error("[%s] タスククラスのロード失敗: %s", task_id, exc)
            return None

        return cls(
            task_id=task_id,
            window=self._window,
            capture=self._capture,
            matcher=self._matcher,
            controller=self._controller,
            config=task_config,
        )

    def _print_summary(self) -> None:
        """実行結果サマリーをログ出力する。"""
        logger.info("=" * 50)
        logger.info("実行結果サマリー")
        logger.info("=" * 50)

        status_icons = {
            TaskStatus.SUCCESS: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.SKIPPED: "→",
            TaskStatus.RUNNING: "?",
            TaskStatus.PENDING: "·",
        }

        for r in self._results:
            icon = status_icons.get(r.status, "?")
            logger.info(
                "  %s [%s] %s",
                icon,
                r.status.value.upper(),
                r.task_id + (f": {r.message}" if r.message else ""),
            )

        total = len(self._results)
        success = sum(1 for r in self._results if r.status == TaskStatus.SUCCESS)
        failed = sum(1 for r in self._results if r.status == TaskStatus.FAILED)
        skipped = sum(1 for r in self._results if r.status == TaskStatus.SKIPPED)

        logger.info("─" * 40)
        logger.info(
            "合計: %d件 | 成功: %d | 失敗: %d | スキップ: %d",
            total, success, failed, skipped,
        )
        logger.info("=" * 50)
